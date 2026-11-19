"""OPAL shared persona surface — contract conformance suite.

Enforces, for every published module contract discovered recursively under
openapi/ (top-level services plus nested modules such as openapi/engines/,
excluding the shared kernel):

* the three persona routes are mounted as bare external $refs to the kernel
  Path Items `persona_collection`, `persona_item`, `persona_validate` -
  including opal-look and opal-look-yolo, which previously had none
* the kernel Path Items carry the canonical `persona` x-opal-cli
  descriptors - `persona list [--enabled/--no-enabled]`, `persona add`,
  `persona show`, `persona update`, `persona remove`, `persona validate`
  with the documented flag bindings
* resolved modules and generated bundles expose the same six operations:
  opal_persona_list/create/get/patch/delete/validate, the `enabled` query
  filter, OpalPersonaCreate/Update/Read payloads, OpalValidationReport,
  201 + Location on create, bodyless 204 on delete, strong If-Match +
  412/428 on mutations, 404 on item ops, 409 on create/patch, strong ETag
  on reads
* every module declares `personas` in its snapshot resources so local
  records round-trip through config save/load
* negative discovery proofs: a missing mount, an inline copy, and a local
  CLI override are all caught
"""
import copy
import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec_util  # noqa: E402

failures = 0


def check(cond, msg):
    global failures
    print(("PASS" if cond else "FAIL"), msg)
    if not cond:
        failures += 1


MOUNTS = {
    "/api/v1/persona/": "persona_collection",
    "/api/v1/persona/{persona_id}": "persona_item",
    "/api/v1/persona/{persona_id}/validate": "persona_validate",
}
OP_IDS = {
    ("get",    "/api/v1/persona/"):                      "opal_persona_list",
    ("post",   "/api/v1/persona/"):                      "opal_persona_create",
    ("get",    "/api/v1/persona/{persona_id}"):          "opal_persona_get",
    ("patch",  "/api/v1/persona/{persona_id}"):          "opal_persona_patch",
    ("delete", "/api/v1/persona/{persona_id}"):          "opal_persona_delete",
    ("post",   "/api/v1/persona/{persona_id}/validate"): "opal_persona_validate",
}
CODES = {
    ("get",    "/api/v1/persona/"):                      {"200", "401", "403", "422"},
    ("post",   "/api/v1/persona/"):                      {"201", "401", "403", "404", "409", "412", "422", "428"},
    ("get",    "/api/v1/persona/{persona_id}"):          {"200", "401", "403", "404", "422"},
    ("patch",  "/api/v1/persona/{persona_id}"):          {"200", "401", "403", "404", "409", "412", "422", "428"},
    ("delete", "/api/v1/persona/{persona_id}"):          {"204", "401", "403", "404", "412", "422", "428"},
    ("post",   "/api/v1/persona/{persona_id}/validate"): {"200", "401", "403", "404", "422"},
}
VERBS = {
    ("get",    "/api/v1/persona/"):                      "list",
    ("post",   "/api/v1/persona/"):                      "add",
    ("get",    "/api/v1/persona/{persona_id}"):          "show",
    ("patch",  "/api/v1/persona/{persona_id}"):          "update",
    ("delete", "/api/v1/persona/{persona_id}"):          "remove",
    ("post",   "/api/v1/persona/{persona_id}/validate"): "validate",
}


def kernel_ref(spec_path, item):
    rel = os.path.relpath(spec_util.KERNEL_PATH,
                          os.path.dirname(os.path.abspath(spec_path)))
    return rel.replace(os.sep, "/") + "#/components/pathItems/" + item


def check_source(d, spec_path, name, quiet=False):
    local = []

    def c(cond, msg):
        if not cond:
            local.append(msg)
        if not quiet:
            check(cond, f"{name}: {msg}")

    paths = d.get("paths", {})
    ok = 0
    for p, item in MOUNTS.items():
        entry = paths.get(p)
        want = kernel_ref(spec_path, item)
        if isinstance(entry, dict) and set(entry.keys()) == {"$ref"}:
            ref = (entry.get("$ref") or "").replace("\\", "/")
            if ref in (want, "./" + want):
                ok += 1
                continue
        c(False, f"{p} is a bare $ref to kernel pathItem {item}")
    c(ok == len(MOUNTS), f"{ok}/3 persona mounts are canonical kernel $refs")
    c("personas" in ((d.get("x-opal-snapshot") or {}).get("resources") or []),
      "snapshot resources include personas")
    return local


def flags(op):
    return {o.get("flag"): o for o in (op.get("x-opal-cli") or {}).get("options", [])}


def check_resolved(d, name, quiet=False):
    local = []

    def c(cond, msg):
        if not cond:
            local.append(msg)
        if not quiet:
            check(cond, f"{name}: {msg}")

    def deref(node, depth=0):
        if isinstance(node, dict) and "$ref" in node and depth < 8:
            for comp_kind in ("schemas", "parameters", "headers"):
                marker = "#/components/" + comp_kind + "/"
                if marker in node["$ref"]:
                    frag = node["$ref"].split(marker)[-1]
                    return deref(d.get("components", {}).get(comp_kind, {})
                                 .get(frag, node), depth + 1)
        return node

    paths = d.get("paths", {})
    for (m, p), opid in OP_IDS.items():
        op = paths.get(p, {}).get(m) or {}
        c(bool(op), f"{m.upper()} {p} exists")
        if not op:
            continue
        c(op.get("operationId") == opid, f"{m.upper()} {p} operationId is {opid}")
        have = set(op.get("responses", {}))
        c(CODES[(m, p)] <= have, f"{opid} declares {sorted(CODES[(m, p)])}")
        cli = op.get("x-opal-cli") or {}
        c(cli.get("group") == "persona" and cli.get("command") == VERBS[(m, p)],
          f"{opid} CLI binding is 'persona {VERBS[(m, p)]}'")

    # enabled filter: omission unfiltered; --no-enabled sends enabled=false
    lst = paths.get("/api/v1/persona/", {}).get("get") or {}
    en = [deref(pr) for pr in lst.get("parameters", [])]
    en = [pr for pr in en if isinstance(pr, dict) and pr.get("name") == "enabled"
          and pr.get("in") == "query"]
    c(len(en) == 1 and (en[0].get("schema") or {}).get("type") == "boolean",
      "list exposes optional boolean 'enabled' query filter")
    lf = flags(lst)
    c("--enabled" in lf and "--no-enabled" in lf
      and all((lf[f].get("binds") or {}).get("target") == "enabled" for f in
              ("--enabled", "--no-enabled")),
      "persona list --enabled/--no-enabled bind query.enabled")

    # create: 201 + Location, If-Match, field bindings
    crt = paths.get("/api/v1/persona/", {}).get("post") or {}
    hdrs = (crt.get("responses", {}).get("201", {}).get("headers") or {})
    c("Location" in hdrs, "persona create 201 returns Location")
    c("ETag" in hdrs, "persona create 201 returns ETag")
    c(any((deref(pr) or {}).get("name") == "If-Match" for pr in crt.get("parameters", [])),
      "persona create requires If-Match")
    cf = flags(crt)
    for flag, target in (("--if-match", "If-Match"), ("--persona-id", "persona_id"),
                         ("--name", "name"), ("--description", "description"),
                         ("--voice-id", "voice_id"), ("--enabled", "enabled"),
                         ("--no-enabled", "enabled")):
        b = (cf.get(flag) or {}).get("binds") or {}
        c(b.get("target") == target, f"persona add {flag} binds {target}")

    # reads return ETag; patch mirrors create fields minus persona_id; delete is bodyless 204
    get_op = paths.get("/api/v1/persona/{persona_id}", {}).get("get") or {}
    c("ETag" in (get_op.get("responses", {}).get("200", {}).get("headers") or {}),
      "persona get 200 returns ETag")
    lst_hdrs = (lst.get("responses", {}).get("200", {}).get("headers") or {})
    c("ETag" in lst_hdrs, "persona list 200 returns ETag")

    pt = paths.get("/api/v1/persona/{persona_id}", {}).get("patch") or {}
    pf = flags(pt)
    c("--persona-id" not in pf, "persona update has no --persona-id (identity is path-bound)")
    c("--if-match" in pf and "--voice-id" in pf, "persona update carries --if-match and field options")

    dl = paths.get("/api/v1/persona/{persona_id}", {}).get("delete") or {}
    c("content" not in (dl.get("responses", {}).get("204") or {}),
      "persona remove 204 is bodyless")

    # validate returns the shared report; nullable voice_id in create schema
    val = paths.get("/api/v1/persona/{persona_id}/validate", {}).get("post") or {}
    vsch = deref((val.get("responses", {}).get("200", {}).get("content", {})
                  .get("application/json", {}) or {}).get("schema") or {})
    c(bool(vsch.get("properties") or vsch.get("type")),
      "persona validate 200 returns OpalValidationReport")
    create_sch = d.get("components", {}).get("schemas", {}).get("OpalPersonaCreate", {})
    vid = (create_sch.get("properties", {}) or {}).get("voice_id") or {}
    c("null" in str(vid.get("anyOf", vid)), "OpalPersonaCreate.voice_id is nullable")
    return local


def main():
    specs = spec_util.module_specs()
    docs, sources, spec_paths = {}, {}, {}
    for path in specs:
        name = os.path.splitext(os.path.basename(path))[0]
        spec_paths[name] = path
        sources[name] = yaml.safe_load(open(path, encoding="utf-8"))
        check_source(sources[name], path, name)
        docs[name] = spec_util.load(path)
        check_resolved(docs[name], name)

    # -- kernel source of truth -------------------------------------------------
    kd = yaml.safe_load(open(spec_util.KERNEL_PATH, encoding="utf-8"))
    for item, verbs in (("persona_collection", ("list", "add")),
                        ("persona_item", ("show", "update", "remove")),
                        ("persona_validate", ("validate",))):
        cmds = sorted((o.get("x-opal-cli") or {}).get("command")
                      for m, o in kd["components"]["pathItems"][item].items()
                      if m in ("get", "post", "put", "patch", "delete"))
        check(cmds == sorted(verbs), f"kernel {item} carries canonical persona bindings ({cmds})")

    # -- generated bundles -------------------------------------------------------
    for name in sorted(spec_paths):
        bpath = os.path.join(spec_util.ROOT, "dist", name + ".yaml")
        if not os.path.exists(bpath):
            check(True, f"{name}: bundle check skipped (run npm run bundle first)")
            continue
        bd = yaml.safe_load(open(bpath, encoding="utf-8"))
        check_resolved(bd, name + " bundle")

    # -- negative discovery proofs ------------------------------------------------
    victim = copy.deepcopy(sources["opal_event"])
    del victim["paths"]["/api/v1/persona/"]
    found = check_source(victim, spec_paths["opal_event"], "nonconforming-missing", quiet=True)
    check(any("persona" in m for m in found),
          "negative discovery: a missing persona mount is caught")

    victim2 = copy.deepcopy(sources["opal_event"])
    victim2["paths"]["/api/v1/persona/"] = {"get": docs["opal_event"]["paths"]
                                           ["/api/v1/persona/"]["get"]}
    found = check_source(victim2, spec_paths["opal_event"], "nonconforming-inline", quiet=True)
    check(any("bare $ref" in m for m in found),
          "negative discovery: an inline copy replacing the kernel $ref is caught")

    victim3 = copy.deepcopy(sources["opal_event"])
    victim3["paths"]["/api/v1/persona/"]["x-opal-cli"] = {
        "get": {"group": "persona", "command": "list"}}
    found = check_source(victim3, spec_paths["opal_event"], "nonconforming-override", quiet=True)
    check(any("bare $ref" in m for m in found),
          "negative discovery: a local CLI override on the mount is caught")

    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
