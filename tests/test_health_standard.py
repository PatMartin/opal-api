"""OPAL unified info/health surface — contract conformance suite.

Enforces, for every published module contract discovered recursively under
openapi/ (top-level services plus nested modules such as openapi/engines/,
excluding the shared kernel):

* GET /api/v1/health/ mounted as a bare external $ref to the kernel `health`
  Path Item - the single service information surface (opal_health_get)
* the kernel Path Item carries the canonical `info health` x-opal-cli
  binding - the only `info` command exposed by any module
* retired routes are gone everywhere: /api/v1/info/, /api/v1/info/ping,
  /api/v1/stats/, /api/v1/health/audio_devices (source, resolved, bundle)
* normalized OpalHealthReport: name/version/api_version/status/live/ready/
  details required; status vocabulary ok|degraded|error; named response
  examples (healthy, live-but-unready, EVENT counters, LISTEN audio
  devices, no-extra-diagnostics) validate against the schema
* machine probes /api/v1/health/live + /api/v1/health/ready stay mounted
  where they existed, keep 200/503 OpalHealthProbe bodies, and carry no CLI
  binding
* module-owned diagnostics declared via x-opal-health-details resolve to
  real schemas
* a negative discovery proof: a reintroduced `info live` command or an
  inline copy replacing the kernel $ref is caught
"""
import copy
import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec_util  # noqa: E402
import jsonschema  # noqa: E402

failures = 0


def check(cond, msg):
    global failures
    print(("PASS" if cond else "FAIL"), msg)
    if not cond:
        failures += 1


HEALTH = "/api/v1/health/"
PROBES = ["/api/v1/health/live", "/api/v1/health/ready"]
RETIRED = ["/api/v1/info/", "/api/v1/info/ping", "/api/v1/stats/",
           "/api/v1/health/audio_devices"]
REQUIRED = {"name", "version", "api_version", "status", "live", "ready", "details"}


def kernel_ref(spec_path, item):
    rel = os.path.relpath(spec_util.KERNEL_PATH,
                          os.path.dirname(os.path.abspath(spec_path)))
    return rel.replace(os.sep, "/") + "#/components/pathItems/" + item


def check_source(d, spec_path, name, quiet=False):
    """Source-level: health report mount is a bare kernel $ref; probes are
    bare $refs where present; retired paths absent; no info tag."""
    local = []

    def c(cond, msg):
        if not cond:
            local.append(msg)
        if not quiet:
            check(cond, f"{name}: {msg}")

    paths = d.get("paths", {})
    entry = paths.get(HEALTH) or {}
    want = kernel_ref(spec_path, "health")
    ref = (entry.get("$ref") or "").replace("\\", "/")
    c(set(entry.keys()) == {"$ref"} and ref in (want, "./" + want),
      f"{HEALTH} is a bare $ref to kernel pathItem health")
    for p in PROBES:
        if p in paths:
            e = paths[p]
            ref = (e.get("$ref") or "").replace("\\", "/")
            item = "health_live" if p.endswith("live") else "health_ready"
            want = kernel_ref(spec_path, item)
            c(set(e.keys()) == {"$ref"} and ref in (want, "./" + want),
              f"{p} is a bare $ref to kernel pathItem {item}")
    for p in RETIRED:
        c(p not in paths, f"retired route {p} absent")
    c(not any(t.get("name") == "info" for t in d.get("tags", []) if isinstance(t, dict)),
      "no orphaned 'info' tag")
    return local


def cli_of(op):
    return op.get("x-opal-cli") or {}


def check_resolved(d, name, quiet=False):
    """Resolved/bundled view: exactly one `info` CLI command (info health on
    opal_health_get), probes unbound with 200/503 probe bodies, retired
    routes absent, report schema normalized."""
    local = []

    def c(cond, msg):
        if not cond:
            local.append(msg)
        if not quiet:
            check(cond, f"{name}: {msg}")

    paths = d.get("paths", {})
    info_cmds = []
    for p, item in paths.items():
        for m, op in item.items():
            if m in ("get", "post", "put", "patch", "delete") and isinstance(op, dict):
                cli = cli_of(op)
                if cli.get("group") == "info":
                    info_cmds.append((cli.get("command"), m.upper(), p))
    c(info_cmds == [("health", "GET", HEALTH)],
      f"exactly one info command: 'info health' ({info_cmds})")

    op = paths.get(HEALTH, {}).get("get") or {}
    c(op.get("operationId") == "opal_health_get", "health GET operationId is opal_health_get")
    c("503" in op.get("responses", {}), "health GET declares 503 (report unavailable)")
    c("401" in op.get("responses", {}) and "403" in op.get("responses", {}),
      "health GET keeps 401/403 access rules")

    def deref(node, depth=0):
        if isinstance(node, dict) and "$ref" in node and depth < 6:
            frag = node["$ref"].split("#/components/schemas/")[-1]
            if frag != node["$ref"]:
                return deref(d.get("components", {}).get("schemas", {})
                             .get(frag, node), depth + 1)
        return node

    for p in PROBES:
        if p in paths:
            pop = paths[p].get("get") or {}
            c(not cli_of(pop), f"{p} probe has no CLI binding")
            for code in ("200", "503"):
                sch = deref((pop.get("responses", {}).get(code, {})
                             .get("content", {}).get("application/json", {})
                             .get("schema") or {}))
                req = set(sch.get("required") or [])
                c({"status", "ready"} <= req, f"{p} {code} probe body requires status+ready")

    for p in RETIRED:
        c(p not in paths, f"retired route {p} absent")

    hr = d.get("components", {}).get("schemas", {}).get("OpalHealthReport", {})
    c(REQUIRED <= set(hr.get("required", [])),
      "OpalHealthReport requires name/version/api_version/status/live/ready/details")
    c(set((hr.get("properties", {}).get("status") or {}).get("enum", [])) ==
      {"ok", "degraded", "error"}, "status vocabulary is ok|degraded|error")
    c("info" not in d.get("components", {}).get("pathItems", {})
      and "info_ping" not in d.get("components", {}).get("pathItems", {}),
      "retired info/info_ping pathItems gone")
    return local


def check_details_decl(d, name, quiet=False):
    local = []

    def c(cond, msg):
        if not cond:
            local.append(msg)
        if not quiet:
            check(cond, f"{name}: {msg}")

    ext = d.get("x-opal-health-details") or {}
    c(isinstance(ext.get("members"), dict), "x-opal-health-details declares a members map")
    for member, schema in (ext.get("members") or {}).items():
        if isinstance(schema, dict) and "$ref" in schema:
            frag = schema["$ref"].split("#/components/schemas/")[-1]
            c(frag in d.get("components", {}).get("schemas", {}),
              f"details member '{member}' schema '{frag}' resolves")
        elif isinstance(schema, dict):
            c(schema.get("type") is not None or any(
                isinstance(v, dict) and "$ref" in str(v) for v in schema.values()),
              f"details member '{member}' carries a schema")
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
        check_details_decl(docs[name], name)

    # -- kernel source of truth ------------------------------------------------
    kd = yaml.safe_load(open(spec_util.KERNEL_PATH, encoding="utf-8"))
    kop = kd["components"]["pathItems"]["health"]["get"]
    kcli = kop.get("x-opal-cli") or {}
    check(kcli.get("group") == "info" and kcli.get("command") == "health",
          "kernel health Path Item carries the canonical info health binding")
    check("info" not in kd["components"]["pathItems"]
          and "info_ping" not in kd["components"]["pathItems"],
          "kernel: retired info/info_ping Path Items removed")

    # -- named response examples validate against the schema --------------------
    resolved = docs["opal_say"]
    hr_schema = resolved["components"]["schemas"]["OpalHealthReport"]
    hr_schema = dict(hr_schema)
    hr_schema.setdefault("components", resolved["components"])
    examples = (((resolved["paths"][HEALTH]["get"]["responses"]["200"]
                  ["content"]["application/json"]) or {}).get("examples") or {})
    for ex_name in ("healthy", "live_not_ready", "event_counters",
                    "listen_audio_devices", "minimal"):
        ex = examples.get(ex_name)
        check(ex is not None, f"health 200 example '{ex_name}' present")
        if ex is None:
            continue
        try:
            jsonschema.validate(ex.get("value"), hr_schema)
            check(True, f"health 200 example '{ex_name}' validates against OpalHealthReport")
        except Exception as e:
            check(False, f"health 200 example '{ex_name}' validates ({e})")
    check(examples.get("live_not_ready", {}).get("value", {}).get("ready") is False,
          "live_not_ready example documents HTTP 200 with ready=false")

    # -- generated bundles -------------------------------------------------------
    for name in sorted(spec_paths):
        bpath = os.path.join(spec_util.ROOT, "dist", name + ".yaml")
        if not os.path.exists(bpath):
            check(True, f"{name}: bundle check skipped (run npm run bundle first)")
            continue
        bd = yaml.safe_load(open(bpath, encoding="utf-8"))
        check_resolved(bd, name + " bundle")

    # -- negative discovery proofs ------------------------------------------------
    victim = copy.deepcopy(docs["opal_event"])
    victim["paths"][HEALTH]["get"]["x-opal-cli"] = {"group": "info", "command": "health"}
    victim["paths"]["/api/v1/health/live"]["get"]["x-opal-cli"] = {
        "group": "info", "command": "live"}
    found = check_resolved(victim, "nonconforming-probe", quiet=True)
    check(any("info command" in m or "no CLI binding" in m for m in found),
          "negative discovery: reintroduced legacy 'info live' command is caught")

    victim_src = copy.deepcopy(sources["opal_event"])
    victim_src["paths"][HEALTH] = {
        "get": docs["opal_event"]["paths"][HEALTH]["get"]}
    found = check_source(victim_src, spec_paths["opal_event"], "nonconforming-source", quiet=True)
    check(any("bare $ref" in m for m in found),
          "negative discovery: inline copy replacing the kernel $ref is caught")

    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
