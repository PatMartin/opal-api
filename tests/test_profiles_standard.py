"""OPAL namespaced profile standard — contract conformance suite.

Enforces, for every published module contract discovered recursively under
openapi/ (top-level services plus nested modules such as openapi/engines/,
excluding the shared kernel):

* the six canonical profile operations mounted at the suite paths with the
  shared operationIds, If-Match on mutations, ETag on reads, 401/403
* the uniform CLI subtree `profile list|add|show|update|remove|activate`
  with per-method descriptors and structured file-input options
* the closed namespaced envelope: OpalProfile requires
  {id, name, is_active, shared, modules}; OpalProfileCreate requires only
  `name`; OpalProfilePatch is closed with minProperties 1
* the compartment catalog keys equal the canonical module identities, every
  declared compartment schema is reachable, and unrecognized namespaces
  carry objects only
* jsonschema-2020-12 behavior on resolved specs: multi-module examples
  validate; wrong types, misspelled fields in recognized compartments,
  non-object namespaces, flat envelope fields and missing shared/modules
  are rejected
* each module declares x-opal-profile-namespace whose compartment key equals
  its x-opal-snapshot.module identity; `profiles` appears in every module's
  snapshot resource sections; x-opal-profile-fields is retired everywhere
* a negative discovery proof: a doctored nonconforming module fails the
  same checks
"""
import copy
import os
import sys

import jsonschema

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec_util  # noqa: E402

failures = 0

MODULES = ["opal-event", "opal-listen", "opal-look", "opal-look-yolo",
           "opal-say", "opal-think"]
PROFILE_OPS = [
    ("get",    "/api/v1/profile/",                          "opal_profile_list"),
    ("post",   "/api/v1/profile/",                          "opal_profile_create"),
    ("get",    "/api/v1/profile/{profile_id}",              "opal_profile_get"),
    ("patch",  "/api/v1/profile/{profile_id}",              "opal_profile_patch"),
    ("delete", "/api/v1/profile/{profile_id}",              "opal_profile_delete"),
    ("post",   "/api/v1/profile/{profile_id}/activate",     "opal_profile_activate"),
]
MUTATING = {("post", "/api/v1/profile/"),
            ("patch", "/api/v1/profile/{profile_id}"),
            ("delete", "/api/v1/profile/{profile_id}"),
            ("post", "/api/v1/profile/{profile_id}/activate")}
CLI_VERBS = {
    ("get", "/api/v1/profile/"): "list",
    ("post", "/api/v1/profile/"): "add",
    ("get", "/api/v1/profile/{profile_id}"): "show",
    ("patch", "/api/v1/profile/{profile_id}"): "update",
    ("delete", "/api/v1/profile/{profile_id}"): "remove",
    ("post", "/api/v1/profile/{profile_id}/activate"): "activate",
}


def check(cond, msg):
    global failures
    print(("PASS" if cond else "FAIL"), msg)
    if not cond:
        failures += 1


def param_names(op):
    return {p.get("name") for p in (op.get("parameters") or []) if isinstance(p, dict)}


def cli_of(op):
    return op.get("x-opal-cli") or {}


def opt_flags(cli):
    return {o.get("flag"): o for o in cli.get("options") or []}


def deref(node, root):
    """Resolve '#/...' refs inside a resolved spec doc."""
    if isinstance(node, dict):
        if "$ref" in node and str(node["$ref"]).startswith("#/"):
            tgt = root
            for part in node["$ref"].lstrip("#/").split("/"):
                tgt = tgt[part]
            merged = {k: v for k, v in node.items() if k != "$ref"}
            merged.update(copy.deepcopy(tgt))
            return deref(merged, root)
        return {k: deref(v, root) for k, v in node.items()}
    if isinstance(node, list):
        return [deref(v, root) for v in node]
    return node


def valid(schema, doc, label, c=check):
    try:
        jsonschema.validate(doc, schema)
        c(True, label)
        return True
    except jsonschema.ValidationError as e:
        c(False, f"{label} (unexpected rejection: {e.message[:80]})")
        return False


def invalid(schema, doc, label, c=check):
    try:
        jsonschema.validate(doc, schema)
        c(False, f"{label} (unexpectedly accepted)")
    except jsonschema.ValidationError:
        c(True, label)


def check_module(d, name, quiet=False):
    """Run the profile conformance checklist against a resolved spec doc."""
    global failures
    local = []

    def c(cond, msg):
        nonlocal local
        if not cond:
            local.append(msg)
        if not quiet:
            check(cond, f"{name}: {msg}")

    paths = d.get("paths", {})
    comps = d.get("components", {}).get("schemas", {})
    own = (d.get("x-opal-snapshot") or {}).get("module")
    xns = d.get("x-opal-profile-namespace") or {}

    # -- canonical operations --------------------------------------------
    opids = set()
    for method, path, opid in PROFILE_OPS:
        op = paths.get(path, {}).get(method)
        c(op is not None, f"{method.upper()} {path} exists")
        if not op:
            continue
        c(op.get("operationId") == opid, f"{method.upper()} {path} operationId is {opid}")
        c("401" in op.get("responses", {}), f"{opid} declares 401")
        c("403" in op.get("responses", {}), f"{opid} declares 403")
        opids.add(op.get("operationId"))
        if (method, path) in MUTATING:
            c("If-Match" in param_names(op), f"{opid} requires If-Match")
            for code in ("412", "428"):
                c(code in op.get("responses", {}), f"{opid} declares {code}")
        if method in ("get", "patch"):
            c("ETag" in (op.get("responses", {}).get("200", {}).get("headers") or {}),
              f"{opid} 200 returns ETag")

    # unique operationIds across the whole API (kernel-mounted + local)
    seen = set()
    dup = []
    for item in paths.values():
        for m, op in item.items():
            if isinstance(op, dict) and m in ("get", "post", "put", "patch", "delete"):
                oid = op.get("operationId")
                if oid in seen:
                    dup.append(oid)
                seen.add(oid)
    c(not dup, f"operationIds unique within API (dupes: {sorted(set(dup))})")

    # -- uniform CLI subtree ----------------------------------------------
    for (method, path), verb in CLI_VERBS.items():
        cli = cli_of(paths.get(path, {}).get(method) or {})
        c(cli.get("group") == "profile", f"{method.upper()} {path} cli group is 'profile'")
        c(cli.get("command") == verb, f"{method.upper()} {path} cli command is '{verb}'")
    post_cli = cli_of(paths.get("/api/v1/profile/", {}).get("post") or {})
    patch_cli = cli_of(paths.get("/api/v1/profile/{profile_id}", {}).get("patch") or {})
    for label, cli in (("add", post_cli), ("update", patch_cli)):
        fl = opt_flags(cli)
        c(fl.get("--in", {}).get("binds", {}).get("kind") == "local_in"
          and fl["--in"]["binds"].get("parse") == "yaml_or_json_file",
          f"profile {label} --in binds local_in body (yaml_or_json_file)")
        c(fl.get("--shared", {}).get("binds", {}).get("kind") == "local_in"
          and fl["--shared"]["binds"].get("target") == "shared",
          f"profile {label} --shared binds local_in shared")
        c(fl.get("--module", {}).get("binds", {}).get("kind") == "local_in"
          and fl["--module"]["binds"].get("target") == f"modules.{own}",
          f"profile {label} --module binds local_in modules.{own}")

    # -- closed namespaced envelope ----------------------------------------
    prof = comps.get("OpalProfile", {})
    c(set(prof.get("required", [])) == {"id", "name", "is_active", "shared", "modules"},
      "OpalProfile requires id+name+is_active+shared+modules")
    c(prof.get("additionalProperties") is False, "OpalProfile envelope is closed")
    props = set(prof.get("properties", {}))
    flat = {"voice_id", "speed", "volume", "output_format", "sample_rate",
            "engine_options", "wakeword_names", "confidence_thresholds",
            "vad_settings", "enabled_intents", "enabled_slots", "model_paths",
            "pipeline_id", "inference", "retention"}
    c(not (props & flat), "no v2 flat operational fields in OpalProfile")
    for ro in ("id", "created_at", "updated_at"):
        c(prof.get("properties", {}).get(ro, {}).get("readOnly") is True,
          f"OpalProfile.{ro} is readOnly")
    isa = prof.get("properties", {}).get("is_active", {})
    c("local" in (isa.get("description") or "").lower(),
      "is_active documented as local projection")

    create = comps.get("OpalProfileCreate", {})
    c(set(create.get("required", [])) == {"name"}, "OpalProfileCreate requires only name")
    c(create.get("additionalProperties") is False, "OpalProfileCreate envelope is closed")
    c("shared" in create.get("properties", {}) and "modules" in create.get("properties", {}),
      "OpalProfileCreate accepts shared+modules (portable document ingestion)")

    patch = comps.get("OpalProfilePatch", {})
    c(patch.get("minProperties") == 1, "OpalProfilePatch requires >= 1 property")
    c(patch.get("additionalProperties") is False, "OpalProfilePatch envelope is closed")
    c("id" not in patch.get("properties", {}), "OpalProfilePatch cannot set id")
    pdesc = patch.get("description") or ""
    c("422" in pdesc and "atomic" in pdesc.lower(),
      "patch documents foreign-compartment 422 + atomicity (implementation obligation)")

    # -- compartment catalog -------------------------------------------------
    mods = deref(prof.get("properties", {}).get("modules", {}), d)
    keys = set(mods.get("properties", {}).keys())
    c(keys == set(MODULES), f"catalog keys == canonical module ids ({sorted(keys)})")
    c((mods.get("additionalProperties") or {}).get("type") == "object",
      "unrecognized namespaces must be objects (forward portability)")
    for mod in keys:
        c(bool(mods["properties"][mod]), f"catalog compartment '{mod}' resolves to a schema")

    # -- module namespace declaration + snapshot ------------------------------
    c(xns.get("compartment") == own,
      f"x-opal-profile-namespace compartment == module id ({own})")
    c("profiles" in ((d.get("x-opal-snapshot") or {}).get("resources") or []),
      "x-opal-snapshot.resources includes profiles")
    c("x-opal-profile-fields" not in d, "x-opal-profile-fields retired")

    # -- resolved-schema behavior ---------------------------------------------
    prof_r = deref(copy.deepcopy(prof), d)
    base = {"id": "p1", "name": "P", "is_active": True, "shared": {}, "modules": {}}
    valid(prof_r, copy.deepcopy(base), "empty shared+modules record validates", c)
    rec = copy.deepcopy(base)
    rec["modules"] = {
        "opal-say": {"voice_id": "v1", "speed": 1.1, "sample_rate": None},
        "opal-listen": {"wakeword_names": ["hey_opal"]},
        "opal-look": {},
        "opal-future-thing": {"arbitrary": [1, 2]},
    }
    valid(prof_r, rec, "multi-module record incl. empty + unrecognized compartments validates", c)
    bad = copy.deepcopy(rec); bad["modules"]["opal-say"] = {"speed": 99.0}
    invalid(prof_r, bad, "out-of-bounds value in recognized compartment rejected", c)
    bad = copy.deepcopy(rec); bad["modules"]["opal-look"] = {"nope": 1}
    invalid(prof_r, bad, "undeclared field in empty compartment rejected", c)
    bad = copy.deepcopy(rec); bad["modules"]["opal-future-thing"] = "str"
    invalid(prof_r, bad, "non-object unrecognized namespace rejected", c)
    bad = copy.deepcopy(rec); bad["voice_id"] = "x"
    invalid(prof_r, bad, "flat field in profile envelope rejected", c)
    bad = copy.deepcopy(rec); del bad["shared"]
    invalid(prof_r, bad, "record missing shared rejected", c)
    bad = copy.deepcopy(rec); bad["modules"] = None
    invalid(prof_r, bad, "non-object modules rejected", c)

    patch_r = deref(copy.deepcopy(patch), d)
    p_good = {"modules": {own: {}}}
    if own == "opal-say":
        p_good["modules"][own] = {"speed": 1.25, "voice_id": None}
    elif own == "opal-listen":
        p_good["modules"][own] = {"enabled_slots": ["city"], "vad_settings": None}
    valid(patch_r, copy.deepcopy(p_good), "patch with own compartment validates", c)
    invalid(patch_r, {}, "empty patch document rejected (minProperties)", c)
    invalid(patch_r, {"modules": {own: None}}, "null compartment rejected", c)
    if own == "opal-say":
        invalid(patch_r, {"modules": {"opal-say": {"speed": "fast"}}},
                "wrong field type in patch compartment rejected", c)
    return local


def main():
    specs = spec_util.module_specs()
    docs = {}
    for path in specs:
        name = os.path.splitext(os.path.basename(path))[0]
        docs[name] = spec_util.load(path)
        check_module(docs[name], name)

    # every owned namespace schema is reachable from operation-bound payloads
    for name, d in docs.items():
        comps = d.get("components", {}).get("schemas", {})
        mods = deref(comps.get("OpalProfile", {}).get("properties", {})
                     .get("modules", {}), d)
        for mod, ns in mods.get("properties", {}).items():
            check(bool(ns.get("type") == "object" or ns.get("properties") is not None
                       or "additionalProperties" in ns or "allOf" in ns),
                  f"{name}: compartment '{mod}' is a concrete schema")

    # -- negative discovery proof -------------------------------------------
    victim = copy.deepcopy(docs["opal_event"])
    victim["paths"].pop("/api/v1/profile/", None)
    victim["components"]["schemas"]["OpalProfile"]["required"] = ["id"]
    victim["x-opal-profile-namespace"] = {"compartment": "opal-event"}
    found = check_module(victim, "nonconforming-probe", quiet=True)
    check(any("profile/" in m or "OpalProfile" in m for m in found),
          "negative discovery: doctored nonconforming module is caught")

    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
