"""OPAL unified configuration standard — contract conformance suite.

Enforces, for every published module contract discovered recursively under
openapi/ (top-level services plus nested modules such as openapi/engines/,
excluding the shared kernel):

* all seven canonical configuration operations with exact methods, paths,
  and operationIds
* identical request/response shapes, ETag/If-Match preconditions, auth, and
  error requirements
* the exact CLI subtree `config save|load|validate` + `config setting
  list|show --name|set --name --value|remove --name` with required flags and
  no configuration aliases
* no retired surfaces: no /api/v1/backup/*, no settings-collection PATCH, no
  backup/restore/export/import command groups or operationIds
* the closed snapshot envelope and x-opal-snapshot metadata
* a negative discovery proof: a doctored nonconforming module fails the same
  checks
"""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec_util  # noqa: E402

failures = 0


def check(cond, msg):
    global failures
    print(("PASS" if cond else "FAIL"), msg)
    if not cond:
        failures += 1


OPS = [
    ("post",   "/api/v1/config/save",     "opal_config_save"),
    ("post",   "/api/v1/config/load",     "opal_config_load"),
    ("post",   "/api/v1/config/validate", "opal_config_validate"),
    ("get",    "/api/v1/setting/",        "opal_setting_list"),
    ("get",    "/api/v1/setting/{key}",   "opal_setting_get"),
    ("put",    "/api/v1/setting/{key}",   "opal_setting_put"),
    ("delete", "/api/v1/setting/{key}",   "opal_setting_delete"),
]

CLI = {
    "/api/v1/config/save":     ("config", "save"),
    "/api/v1/config/load":     ("config", "load"),
    "/api/v1/config/validate": ("config", "validate"),
    "/api/v1/setting/":        ("setting", "list"),
    "/api/v1/setting/{key}":   ("setting", None),   # per-method verbs
}
RETIRED_OPIDS = {"opal_setting_patch", "opal_backup_validate_stored"}
LEGACY_VERBS = {"backup", "restore", "export", "import", "download"}


def param_names(op):
    return {p.get("name") for p in (op.get("parameters") or []) if isinstance(p, dict)}


def has_ifmatch(op):
    return "If-Match" in param_names(op)


def cli_of(op):
    return op.get("x-opal-cli") or {}


def opt_flags(cli):
    return {o.get("flag"): o for o in cli.get("options") or []}


def check_module(d, name, quiet=False):
    """Run the full conformance checklist against a resolved spec doc."""
    global failures
    local = []

    def c(cond, msg):
        nonlocal local
        if not cond:
            local.append(msg)
        if not quiet:
            check(cond, f"{name}: {msg}")

    paths = d.get("paths", {})

    # -- seven canonical operations --------------------------------------
    for method, path, opid in OPS:
        op = paths.get(path, {}).get(method)
        c(op is not None, f"{method.upper()} {path} exists")
        if op:
            c(op.get("operationId") == opid, f"{method.upper()} {path} operationId is {opid}")
            c("401" in op.get("responses", {}), f"{opid} declares 401")
            c("403" in op.get("responses", {}), f"{opid} declares 403")

    # -- no retired REST surfaces ----------------------------------------
    c(not any("/backup" in p for p in paths), "no /api/v1/backup/* paths")
    c(not any(m in (paths.get("/api/v1/setting/") or {})
              for m in ("patch", "put", "post", "delete")),
      "settings collection is GET-only")
    c(not any(op.get("operationId", "").startswith("opal_backup")
              or op.get("operationId") in RETIRED_OPIDS
              for item in paths.values() for m, op in item.items()
              if isinstance(op, dict) and m in ("get", "post", "put", "patch", "delete")),
      "no retired opal_backup_*/opal_setting_patch operationIds")

    # -- exact CLI subtree -------------------------------------------------
    cli_cmds = []
    for item in paths.values():
        for m, op in item.items():
            if isinstance(op, dict) and m in ("get", "post", "put", "patch", "delete"):
                cli_cmds.append(cli_of(op))
    for pth, (grp, cmd) in CLI.items():
        for m, op in paths.get(pth, {}).items():
            if m not in ("get", "post", "put", "patch", "delete") or not isinstance(op, dict):
                continue
            cli = cli_of(op)
            c(cli.get("group") == grp, f"{m.upper()} {pth} cli group is '{grp}'")
            c(cli.get("parent") in (None, "config"), f"{m.upper()} {pth} cli parent")
            if cmd:
                c(cli.get("command") == cmd, f"{m.upper()} {pth} cli command is '{cmd}'")
            c(not cli.get("aliases"), f"{m.upper()} {pth} has no CLI aliases")
    sk = paths.get("/api/v1/setting/{key}", {})
    for m, verb in (("get", "show"), ("put", "set"), ("delete", "remove")):
        op = sk.get(m)
        if not op:
            continue
        cli = cli_of(op)
        c(cli.get("command") == verb, f"setting {m} cli verb is '{verb}'")
        fl = opt_flags(cli)
        nm = fl.get("--name")
        c(nm and nm.get("required") is True and
          nm.get("binds", {}).get("kind") == "path" and
          nm.get("binds", {}).get("target") == "key",
          f"setting {m} requires --name NAME bound to path key")
        if m == "put":
            vl = fl.get("--value")
            c(vl and vl.get("required") is True and
              vl.get("binds", {}).get("kind") == "body" and
              vl.get("binds", {}).get("target") == "value" and
              vl.get("binds", {}).get("parse") == "json_or_string",
              "setting set requires --value VALUE bound to body value (json_or_string)")
    save_cli = cli_of((paths.get("/api/v1/config/save") or {}).get("post") or {})
    c(opt_flags(save_cli).get("--out", {}).get("binds", {}).get("kind") == "local_out",
      "config save --out binds local_out:snapshot")
    for pth in ("/api/v1/config/load", "/api/v1/config/validate"):
        fl = opt_flags(cli_of((paths.get(pth) or {}).get("post") or {}))
        c(fl.get("--in", {}).get("binds", {}).get("kind") == "local_in"
          and fl["--in"]["binds"].get("target") == "snapshot"
          and fl["--in"]["binds"].get("parse") == "yaml_or_json_file",
          f"{pth} --in binds local_in:snapshot (yaml_or_json_file)")
    c(not any(c2.get("group") in LEGACY_VERBS or c2.get("command") in
              {"restore", "export", "import", "download", "patch"} and
              c2.get("group") in ("backup", "setting")
              for c2 in cli_cmds),
      "no legacy backup/setting CLI verbs")

    # -- ETag / If-Match semantics ------------------------------------------
    load_op = paths.get("/api/v1/config/load", {}).get("post") or {}
    c(has_ifmatch(load_op), "config load requires If-Match")
    for code in ("412", "428"):
        c(code in load_op.get("responses", {}), f"config load declares {code}")
    c("404" in load_op.get("responses", {}), "config load declares 404 (no managed snapshot)")
    c("ETag" in (load_op.get("responses", {}).get("200", {}).get("headers") or {}),
      "config load 200 returns ETag (new revision)")
    for pth, m in (("/api/v1/config/save", "post"), ("/api/v1/config/validate", "post")):
        op = paths.get(pth, {}).get(m) or {}
        c(not has_ifmatch(op), f"{m.upper()} {pth} takes no If-Match")
    c("ETag" in ((paths.get("/api/v1/config/save", {}).get("post") or {})
                 .get("responses", {}).get("200", {}).get("headers") or {}),
      "config save 200 returns ETag (captured revision)")
    for m in ("put", "delete"):
        op = sk.get(m) or {}
        c(has_ifmatch(op), f"setting {m.upper()} requires If-Match")
        c("412" in op.get("responses", {}) and "428" in op.get("responses", {}),
          f"setting {m.upper()} declares 412 + 428")
    c("ETag" in (sk.get("put", {}).get("responses", {}).get("200", {}).get("headers") or {}),
      "setting PUT 200 returns ETag")
    c("ETag" in (sk.get("delete", {}).get("responses", {}).get("204", {}).get("headers") or {}),
      "setting DELETE 204 returns ETag")
    c("ETag" in (sk.get("get", {}).get("responses", {}).get("200", {}).get("headers") or {}),
      "setting GET 200 returns ETag")
    c("ETag" in ((paths.get("/api/v1/setting/", {}).get("get") or {})
                 .get("responses", {}).get("200", {}).get("headers") or {}),
      "setting list 200 returns ETag")

    # -- request/response shapes -------------------------------------------
    comps = d.get("components", {}).get("schemas", {})
    snap = comps.get("OpalConfigSnapshot", {})
    c(snap.get("additionalProperties") is False, "snapshot envelope is closed")
    c(set(snap.get("required", [])) ==
      {"format_version", "module", "created_at", "settings", "resources"},
      "snapshot requires format_version/module/created_at/settings/resources")
    fv = (snap.get("properties", {}).get("format_version") or {})
    c(fv.get("type") == "string", "format_version is a string (not a union)")
    save_req = comps.get("OpalConfigSaveRequest", {})
    dst = save_req.get("properties", {}).get("destination", {})
    c(set(dst.get("enum", [])) == {"managed", "response"} and dst.get("default") == "managed",
      "save request destination: managed|response, default managed")
    save_res = comps.get("OpalConfigSaveResult", {})
    c({"snapshot", "managed"} <= set(save_res.get("required", [])),
      "save result requires snapshot + managed")
    load_res = comps.get("OpalConfigLoadResult", {})
    c(load_res.get("properties", {}).get("applied", {}).get("const") is True,
      "load result applied is const true")
    c("pending_restart_fields" in load_res.get("properties", {}),
      "load result carries pending_restart_fields")
    c("warnings" in load_res.get("properties", {}), "load result carries warnings")
    val_res = comps.get("OpalConfigValidation", {})
    c({"valid", "errors", "warnings"} <= set(val_res.get("required", [])),
      "validate result requires valid + errors + warnings")
    issue = comps.get("OpalValidationIssue", {})
    c({"code", "path", "message"} <= set(issue.get("required", [])),
      "validation issues carry code + path + message")
    sr = comps.get("SettingRead", {})
    c({"key", "value", "configured_value", "default", "has_override", "is_default",
       "source", "restart_required", "pending_restart"} <= set(sr.get("required", [])),
      "SettingRead requires the full provenance contract")
    c(set(sr.get("properties", {}).get("source", {}).get("enum", [])) ==
      {"default", "persisted", "dotenv", "environment"},
      "SettingRead.source enum is default|persisted|dotenv|environment")
    vreq = comps.get("OpalConfigValidateRequest", {})
    vsnap = (vreq.get("properties", {}).get("snapshot") or {})
    c(vsnap.get("type") == "object" and "enum" not in vsnap and "$ref" not in vsnap,
      "validate accepts a loosely-typed candidate snapshot object")

    # -- module identity + snapshot resources -------------------------------
    xsnap = d.get("x-opal-snapshot") or {}
    c(bool(xsnap.get("module")), "x-opal-snapshot declares canonical module id")
    c(bool(xsnap.get("resources")), "x-opal-snapshot declares resource sections")
    return local


def main():
    specs = spec_util.module_specs()
    names = {os.path.splitext(os.path.basename(p))[0] for p in specs}
    expected = {"opal_event", "opal_listen", "opal_look", "opal_say", "opal_think",
                "opal_look_yolo"}
    check(len(specs) >= len(expected),
          f"recursive discovery finds all published modules ({len(specs)})")
    check(expected <= names,
          f"all known runtime modules have contracts (missing: {sorted(expected - names)})")

    docs = {}
    for path in specs:
        name = os.path.splitext(os.path.basename(path))[0]
        docs[name] = spec_util.load(path)
        check_module(docs[name], name)

    # -- negative discovery proof -------------------------------------------
    victim = copy.deepcopy(docs["opal_event"])
    victim["paths"].pop("/api/v1/config/save", None)
    victim["paths"]["/api/v1/backup/import"] = {"post": {"operationId": "opal_backup_import"}}
    found = check_module(victim, "nonconforming-probe", quiet=True)
    check(any("config/save" in m or "backup" in m for m in found),
          "negative discovery: doctored nonconforming module is caught")

    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
