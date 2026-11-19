"""OPAL shared service lifecycle surface — contract conformance suite.

Enforces, for every published module contract discovered recursively under
openapi/ (top-level services plus nested modules such as openapi/engines/,
excluding the shared kernel):

* the three service routes are mounted as bare external $refs to the kernel
  Path Items `service_start`, `service_stop`, `service_log` - including
  standalone engines such as opal-look-yolo
* the kernel Path Items carry the canonical `service` x-opal-cli
  descriptors - the single source of truth for `service start [--append]`,
  `service stop`, and `service log [--lines N]`
* resolved modules and generated bundles expose the same methods, operation
  IDs, schemas, response codes, and CLI bindings: opal_service_start /
  opal_service_stop / opal_service_log, OpalServiceStartOptions(append),
  ServiceLogLines(lines 1-1000 default 10), OpalServiceStatus and
  OpalServiceLogTail payloads, standard authorization and correlation
  headers
* negative discovery proofs: a missing mount and a copied local binding are
  both caught
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
    "/api/v1/service/start": "service_start",
    "/api/v1/service/stop": "service_stop",
    "/api/v1/service/log": "service_log",
}
OP_IDS = {
    ("/api/v1/service/start", "post"): "opal_service_start",
    ("/api/v1/service/stop", "post"): "opal_service_stop",
    ("/api/v1/service/log", "get"): "opal_service_log",
}
CODES = {
    ("/api/v1/service/start", "post"): {"200", "401", "403", "422", "500"},
    ("/api/v1/service/stop", "post"): {"200", "401", "403", "422", "500"},
    ("/api/v1/service/log", "get"): {"200", "401", "403", "404", "422"},
}


def kernel_ref(spec_path, item):
    rel = os.path.relpath(spec_util.KERNEL_PATH,
                          os.path.dirname(os.path.abspath(spec_path)))
    return rel.replace(os.sep, "/") + "#/components/pathItems/" + item


def check_source(d, spec_path, name, quiet=False):
    """Source-level: exactly the three canonical service mounts, each a bare
    $ref to the correct kernel Path Item with no local override."""
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
    extra = [p for p in paths if p.startswith("/api/v1/service/")
             and p not in MOUNTS]
    c(ok == len(MOUNTS), f"{ok}/3 service mounts are canonical kernel $refs")
    c(not extra, f"no unexpected /api/v1/service/* paths ({extra})")
    return local


def check_resolved(d, name, quiet=False):
    """Resolved/bundled view: operations, IDs, schemas, codes, CLI bindings."""
    local = []

    def c(cond, msg):
        if not cond:
            local.append(msg)
        if not quiet:
            check(cond, f"{name}: {msg}")

    def deref(node, depth=0):
        if isinstance(node, dict) and "$ref" in node and depth < 6:
            frag = node["$ref"].split("#/components/schemas/")[-1]
            if frag != node["$ref"]:
                return deref(d.get("components", {}).get("schemas", {})
                             .get(frag, node), depth + 1)
        return node

    paths = d.get("paths", {})
    for (p, m), opid in OP_IDS.items():
        op = paths.get(p, {}).get(m) or {}
        c(bool(op), f"{m.upper()} {p} exists")
        c(op.get("operationId") == opid, f"{m.upper()} {p} operationId is {opid}")
        have = set(op.get("responses", {}))
        c(CODES[(p, m)] <= have,
          f"{opid} declares {sorted(CODES[(p, m)])}")
        cli = op.get("x-opal-cli") or {}
        verb = {"service_start": "start", "service_stop": "stop",
                "service_log": "log"}[MOUNTS[p]]
        c(cli.get("group") == "service" and cli.get("command") == verb,
          f"{opid} CLI binding is 'service {verb}'")

    start = paths.get("/api/v1/service/start", {}).get("post") or {}
    body = deref(((start.get("requestBody") or {}).get("content", {})
                  .get("application/json", {}) or {}).get("schema") or {})
    c("append" in (body.get("properties") or {}),
      "start request body carries append")
    append_opt = [o for o in (start.get("x-opal-cli") or {}).get("options", [])
                  if o.get("flag") == "--append"]
    c(len(append_opt) == 1 and
      (append_opt[0].get("binds") or {}).get("kind") == "body" and
      (append_opt[0].get("binds") or {}).get("target") == "append",
      "service start --append binds body.append")

    log = paths.get("/api/v1/service/log", {}).get("get") or {}
    lines_param = None
    for prm in log.get("parameters", []):
        prm = deref(prm) if isinstance(prm, dict) else prm
        if isinstance(prm, dict) and prm.get("name") == "lines":
            lines_param = prm
    # parameters may be component $refs handled above; fall back to scan
    if lines_param is None:
        for comp in (d.get("components", {}).get("parameters", {}) or {}).values():
            if isinstance(comp, dict) and comp.get("name") == "lines" \
                    and comp.get("in") == "query":
                lines_param = comp
    sch = (lines_param or {}).get("schema") or {}
    c(sch.get("minimum") == 1 and sch.get("maximum") == 1000
      and sch.get("default") == 10,
      "log --lines is query 'lines' 1-1000 default 10")
    lines_opt = [o for o in (log.get("x-opal-cli") or {}).get("options", [])
                 if o.get("flag") == "--lines"]
    c(len(lines_opt) == 1 and
      (lines_opt[0].get("binds") or {}).get("kind") == "query" and
      (lines_opt[0].get("binds") or {}).get("target") == "lines",
      "service log --lines binds query.lines")

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
    for item, verb in (("service_start", "start"), ("service_stop", "stop"),
                       ("service_log", "log")):
        ops = {m: o for m, o in kd["components"]["pathItems"][item].items()
               if m in ("get", "post", "put", "patch", "delete")}
        cli = next(iter(ops.values())).get("x-opal-cli") or {}
        check(cli.get("group") == "service" and cli.get("command") == verb,
              f"kernel {item} carries canonical 'service {verb}' binding")

    # -- generated bundles ------------------------------------------------------
    for name in sorted(spec_paths):
        bpath = os.path.join(spec_util.ROOT, "dist", name + ".yaml")
        if not os.path.exists(bpath):
            check(True, f"{name}: bundle check skipped (run npm run bundle first)")
            continue
        bd = yaml.safe_load(open(bpath, encoding="utf-8"))
        check_resolved(bd, name + " bundle")

    # -- negative discovery proofs ------------------------------------------------
    victim = copy.deepcopy(sources["opal_event"])
    del victim["paths"]["/api/v1/service/stop"]
    found = check_source(victim, spec_paths["opal_event"], "nonconforming-missing", quiet=True)
    check(any("service/stop" in m or "3 service mounts" in m for m in found),
          "negative discovery: a missing service mount is caught")

    victim2 = copy.deepcopy(sources["opal_event"])
    victim2["paths"]["/api/v1/service/start"]["x-opal-cli"] = {
        "post": {"group": "service", "command": "start"}}
    found = check_source(victim2, spec_paths["opal_event"], "nonconforming-copy", quiet=True)
    check(any("bare $ref" in m for m in found),
          "negative discovery: a copied local CLI binding is caught")

    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
