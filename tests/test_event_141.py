"""Contract regression tests for opal_event.v1.4.1.yaml (self-describing actions).

Verifies the versioned 1.4.1 spec against the canonical 1.4.0 baseline:
- identical paths and operationIds; only the three action schemas changed,
  plus the new ActionInputSchema; required lists and discriminator unchanged;
- exactly four optional metadata fields added per action type;
- all $refs are internal and resolve; no duplicate YAML mapping keys;
- positive/negative fixture payloads validate against each action schema
  (legacy fixtures also validate against 1.4.0, proving metadata is optional).

Run: python tests/test_event_141.py   (exit 0 = all assertions passed)
"""
import os
import sys

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V140 = os.path.join(ROOT, "openapi", "opal_event.yaml")
V141 = os.path.join(ROOT, "openapi", "opal_event.v1.4.1.yaml")
FIXTURES = os.path.join(ROOT, "tests", "fixtures", "event_141")
ACTIONS = ("ShellAction", "HttpAction", "PythonAction")
METADATA_FIELDS = {"description", "input_schema", "keywords", "suggested_prompts"}

failures = 0


def check(ok, name, detail=""):
    global failures
    print(("PASS" if ok else "FAIL"), name, detail if detail else "")
    failures += 0 if ok else 1


def load(path):
    return yaml.safe_load(open(path, encoding="utf-8"))


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


def opids(spec):
    return {op.get("operationId") for p in spec["paths"].values()
            for op in p.values() if isinstance(op, dict)}


def main():
    spec140, spec141 = load(V140), load(V141)

    # --- version / parity -------------------------------------------------------
    check(spec141["info"]["version"] == "1.4.1", "info.version is 1.4.1")
    check(spec141["openapi"].startswith("3.1"), "openapi 3.1 declared")
    check(set(spec141["paths"]) == set(spec140["paths"]), "path set identical to 1.4.0")
    check(opids(spec141) == opids(spec140), "operationId set identical to 1.4.0")
    schemas140, schemas141 = spec140["components"]["schemas"], spec141["components"]["schemas"]
    check(set(schemas141) - set(schemas140) == {"ActionInputSchema"}, "only ActionInputSchema added",
          f"(added: {set(schemas141) - set(schemas140)}, removed: {set(schemas140) - set(schemas141)})")
    changed = [k for k in set(schemas140) & set(schemas141) if schemas140[k] != schemas141[k]]
    check(sorted(changed) == sorted(ACTIONS), "only the three action schemas changed", f"({changed})")

    for name in ACTIONS:
        old, new = schemas140[name], schemas141[name]
        added = set(new["properties"]) - set(old["properties"])
        check(added == METADATA_FIELDS, f"{name}: exactly the 4 optional metadata fields added", f"({added})")
        check(new.get("required") == old.get("required"), f"{name}: required fields unchanged")
        check(set(old["properties"]) - set(new["properties"]) == set(), f"{name}: no properties removed")
    check(spec141["components"]["schemas"]["Action"]["discriminator"]
          == spec140["components"]["schemas"]["Action"]["discriminator"], "Action discriminator unchanged")

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
    check(not (required_sets(spec141, set()) & METADATA_FIELDS), "metadata fields never appear in any required list")

    # --- structural hygiene ------------------------------------------------------
    check(no_duplicate_keys(V141) is not None, "no duplicate YAML mapping keys")
    refs = collect_refs(spec141)
    check(all(r.startswith("#/") for r in refs), "all $refs are internal", f"({len(refs)} refs)")
    missing = [r for r in refs if not ref_target_exists(spec141, r)]
    check(not missing, "every $ref resolves", f"({missing})")

    # --- fixture validation -------------------------------------------------------
    cases = [
        # (fixture, schema, valid_against_140_too, expected)
        ("shell_valid.yaml", "ShellAction", False, True),
        ("http_valid.yaml", "HttpAction", False, True),
        ("python_valid.yaml", "PythonAction", False, True),
        ("shell_legacy.yaml", "ShellAction", True, True),
        ("http_legacy.yaml", "HttpAction", True, True),
        ("python_legacy.yaml", "PythonAction", True, True),
        ("shell_missing_required.yaml", "ShellAction", False, False),
        ("shell_exec_missing_executable.yaml", "ShellAction", False, False),
        ("http_bad_metadata.yaml", "HttpAction", False, False),
        ("python_bad_input_schema.yaml", "PythonAction", False, False),
    ]
    for fixture, schema_name, also_140, expected in cases:
        payload = load(os.path.join(FIXTURES, fixture))
        for label, spec in (("1.4.1", spec141),) + ((("1.4.0", spec140),) if also_140 else ()):
            schema = resolve_local_refs(spec["components"]["schemas"][schema_name], spec)
            try:
                Draft202012Validator(schema).validate(payload)
                ok = expected
                detail = ""
            except ValidationError as exc:
                ok = not expected
                detail = f"(rejected: {exc.message[:80]})"
            check(ok, f"fixture {fixture} vs {schema_name} [{label}]", detail)

    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
