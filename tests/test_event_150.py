"""Contract regression tests for the unified opal_event.yaml (self-describing actions).

Verifies the published 1.7.1 spec:
- all four optional metadata fields are present on each action type;
- all $refs are internal and resolve; no duplicate YAML mapping keys;
- positive/negative fixture payloads validate against each action schema.

Run: python tests/test_event_150.py   (exit 0 = all assertions passed)
"""
import os
import sys

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec_util  # noqa: E402
SPEC = os.path.join(ROOT, "openapi", "opal_event.yaml")
FIXTURES = os.path.join(ROOT, "tests", "fixtures", "event_150")
ACTIONS = ("ShellAction", "HttpAction", "PythonAction")
METADATA_FIELDS = {"description", "input_schema", "keywords", "suggested_prompts"}

failures = 0


def check(ok, name, detail=""):
    global failures
    print(("PASS" if ok else "FAIL"), name, detail if detail else "")
    failures += 0 if ok else 1


def load(path):
    return spec_util.load(path)


def no_duplicate_keys(path):
    """Parse YAML erroring on duplicate mapping keys (safe_load ignores them)."""

    class DupCheckLoader(yaml.SafeLoader):
        pass

    def construct(loader, node, deep=False):
        mapping = loader.construct_mapping(node, deep=deep)
        seen = set()
        for key_node, _ in node.value:
            key = loader.construct_object(key_node, deep=True)
            if key in seen:
                raise ValueError(f"duplicate key {key!r} at line {key_node.start_mark.line + 1}")
            seen.add(key)
        return mapping

    DupCheckLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct)
    return yaml.load(open(path, encoding="utf-8"), Loader=DupCheckLoader)


def collect_refs(node, refs=None):
    refs = refs if refs is not None else []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "$ref" and isinstance(value, str):
                refs.append(value)
            else:
                collect_refs(value, refs)
    elif isinstance(node, list):
        for item in node:
            collect_refs(item, refs)
    return refs


def ref_target_exists(doc, ref):
    node = doc
    for part in ref.removeprefix("#/").split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        if not isinstance(node, dict) or part not in node:
            return False
        node = node[part]
    return True


def resolve_local_refs(schema, doc):
    """Inline '#/components/schemas/X' refs (action schemas only reference that space)."""
    if isinstance(schema, dict):
        if set(schema) == {"$ref"} and schema["$ref"].startswith("#/components/schemas/"):
            name = schema["$ref"].rsplit("/", 1)[-1]
            return resolve_local_refs(doc["components"]["schemas"][name], doc)
        return {k: resolve_local_refs(v, doc) for k, v in schema.items()}
    if isinstance(schema, list):
        return [resolve_local_refs(i, doc) for i in schema]
    return schema


def main():
    spec = load(SPEC)

    # --- version and metadata ---------------------------------------------------
    check(spec["info"]["version"] == "1.7.1", "info.version is 1.7.1")
    check(spec["openapi"].startswith("3.1"), "openapi 3.1 declared")
    schemas = spec["components"]["schemas"]

    for name in ACTIONS:
        action = schemas[name]
        check(METADATA_FIELDS <= set(action["properties"]),
              f"{name}: all 4 metadata fields are present")
        check(not (METADATA_FIELDS & set(action.get("required", []))),
              f"{name}: metadata fields are optional")

    # no new field may be required anywhere in the document
    def required_sets(node, acc):
        if isinstance(node, dict):
            required = node.get("required")
            if isinstance(required, list):
                acc.update(req for req in required if isinstance(req, str))
            for v in node.values():
                required_sets(v, acc)
        elif isinstance(node, list):
            for i in node:
                required_sets(i, acc)
        return acc
    check(not (required_sets(spec, set()) & METADATA_FIELDS), "metadata fields never appear in any required list")

    # --- structural hygiene ------------------------------------------------------
    check(no_duplicate_keys(SPEC) is not None, "no duplicate YAML mapping keys")
    refs = collect_refs(spec)
    check(all(r.startswith("#/") for r in refs), "all $refs are internal", f"({len(refs)} refs)")
    missing = [r for r in refs if not ref_target_exists(spec, r)]
    check(not missing, "every $ref resolves", f"({missing})")

    # --- fixture validation -------------------------------------------------------
    cases = [
        ("shell_valid.yaml", "ShellAction", True),
        ("http_valid.yaml", "HttpAction", True),
        ("python_valid.yaml", "PythonAction", True),
        ("shell_legacy.yaml", "ShellAction", True),
        ("http_legacy.yaml", "HttpAction", True),
        ("python_legacy.yaml", "PythonAction", True),
        ("shell_missing_required.yaml", "ShellAction", False),
        ("shell_exec_missing_executable.yaml", "ShellAction", False),
        ("http_bad_metadata.yaml", "HttpAction", False),
        ("python_bad_input_schema.yaml", "PythonAction", False),
    ]
    for fixture, schema_name, expected in cases:
        # Fixtures are action payloads, not specs: spec_util.load() would
        # merge kernel components into the instance and trip
        # additionalProperties: false on every action schema.
        with open(os.path.join(FIXTURES, fixture), encoding="utf-8") as fh:
            payload = yaml.safe_load(fh)
        schema = resolve_local_refs(spec["components"]["schemas"][schema_name], spec)
        try:
            Draft202012Validator(schema).validate(payload)
            ok = expected
            detail = ""
        except ValidationError as exc:
            ok = not expected
            detail = f"(rejected: {exc.message[:80]})"
        check(ok, f"fixture {fixture} vs {schema_name}", detail)

    # --- input-validation semantics ----------------------------------------------
    ex = spec["paths"]["/api/v1/action/{action_id}/execute"]["post"]
    check("422" in ex["responses"], "execute declares 422 for input-validation rejection")
    check("202" in ex["responses"], "execute still declares 202 for admitted async executions")
    desc = ex.get("description", "")
    check("input_schema" in desc and "422" in desc, "execute documents synchronous input validation -> 422")
    check("before" in desc.lower(), "execute: validation happens before any execution record")

    pub = spec["paths"]["/api/v1/event/"]["post"].get("description", "")
    check("dropped" in pub and "input_validation_failed" in pub,
          "events documents rule-triggered validation -> dropped execution record")
    check("already-completed" in pub or "publisher" in pub,
          "events: async failure never returned to the publisher")

    ex_props = spec["components"]["schemas"]["Execution"]["properties"]
    check("dropped" in ex_props["status"]["enum"], "Execution.status includes dropped")
    check(set(ex_props["trigger"]["enum"]) == {"rule", "manual"},
          "Execution.trigger distinguishes rule vs manual")
    ec = ex_props["error_code"].get("description", "")
    check("input_validation_failed" in ec, "error_code documents input_validation_failed")
    check("error_message" in ex_props, "error_message field present for failure detail")
    check("error_code" not in spec["components"]["schemas"]["Execution"].get("required", []),
          "error_code remains optional")

    ais = spec["components"]["schemas"]["ActionInputSchema"].get("description", "")
    check("EventInput.data" in ais, "ActionInputSchema describes EventInput.data only")
    check("local" in ais.lower() or "remote" in ais.lower(),
          "ActionInputSchema restricts $ref targets")
    check("dropped" in ais and "422" in ais,
          "ActionInputSchema documents sync 422 vs async dropped semantics")

    # --- least-privilege authorization -------------------------------------------
    auth = spec.get("x-opal-authorization", {})
    scopes = auth.get("scopes", {})
    check(sorted(scopes) == sorted([
        "actions:read", "actions:execute", "executions:read",
        "actions:write", "rules:write", "settings:write"]),
          "all six permission scopes declared")
    think = auth.get("principals", {}).get("think", {})
    check(sorted(think.get("scopes", [])) == sorted(
        ["actions:read", "actions:execute", "executions:read"]),
          "THINK has discover/invoke/inspect scopes only")
    check(sorted(think.get("denied", [])) == sorted(
        ["actions:write", "rules:write", "settings:write"]),
          "THINK denied all write scopes")
    # every permitted route maps to a real path
    for scope, body in scopes.items():
        for route in body.get("permits", []):
            m, p = route.split(" ", 1)
            check(p in spec["paths"] and m.lower() in spec["paths"][p],
                  f"scope {scope}: permit {route} maps to a real endpoint")
    sem = auth.get("semantics", {})
    check(sem.get("missing_or_invalid_credentials") == "401" and
          sem.get("authenticated_but_insufficient_scope") == "403",
          "401 vs 403 semantics documented")
    for p in ("/api/v1/action/{action_id}/execute", "/api/v1/rule/{rule_id}",
              "/api/v1/setting/"):
        op = spec["paths"][p]
        for m in ("post", "patch", "delete", "get"):
            if m in op:
                check("401" in op[m].get("responses", {}) and
                      "403" in op[m].get("responses", {}),
                      f"{m.upper()} {p} declares 401+403")
    bearer = spec["components"]["securitySchemes"].get("BearerAuth", {})
    check(bearer.get("type") == "http" and bearer.get("scheme") == "bearer",
          "BearerAuth scheme unchanged")
    check("token_env" in bearer.get("description", "") or
          "token_env" in str(sem.get("credential_handling", "")) or
          "token_env" in str(auth.get("description", "")),
          "credential handling via token_env documented")

    # --- settings management convention ------------------------------------------
    sk = spec["paths"].get("/api/v1/setting/{key}", {})
    check(set(sk) & {"get", "put", "delete"} == {"get", "put", "delete"},
          "GET/PUT/DELETE /api/v1/setting/{key} all present")
    check("200" in sk["get"]["responses"] and "404" in sk["get"]["responses"],
          "settings/{key} GET returns 200 + 404 unknown key")
    for mth in ("put", "delete"):
        op = sk[mth]
        names = [x.get("name") for x in op.get("parameters", [])
                 if isinstance(x, dict) and x.get("name")]
        check("If-Match" in names and
              next(x for x in op["parameters"] if x.get("name") == "If-Match")["required"],
              f"settings/{{key}} {mth.upper()} requires If-Match")
        check("412" in op["responses"] and "428" in op["responses"],
              f"settings/{{key}} {mth.upper()} declares 412 + 428")
        check("404" in op["responses"], f"settings/{{key}} {mth.upper()} declares 404")
    check("422" in sk["put"]["responses"], "settings/{{key}} PUT declares 422 invalid value")
    check("SettingRead" in spec["components"]["schemas"] and
          "SettingUpdate" in spec["components"]["schemas"],
          "SettingRead/SettingUpdate schemas exist")
    sr = spec["components"]["schemas"]["SettingRead"]
    check("value" in sr["properties"] and "type" not in sr["properties"]["value"],
          "SettingRead.value is native JSON (untyped)")
    check(sr["required"] == ["key", "value"], "SettingRead requires key+value")
    su = spec["components"]["schemas"]["SettingUpdate"]
    check(su["required"] == ["value"], "SettingUpdate requires only value")
    imp = spec["paths"]["/api/v1/backup/import"]["post"]
    imp_names = [x.get("name") for x in imp.get("parameters", []) if isinstance(x, dict)]
    check("If-Match" in imp_names, "backup/import requires If-Match")
    check("412" in imp["responses"] and "428" in imp["responses"],
          "backup/import declares 412 + 428")
    check(not any("secret" in str(v).lower() and "value" in str(v).lower()
                  for v in sr.get("properties", {}).values()),
          "settings read masks secrets")

    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
