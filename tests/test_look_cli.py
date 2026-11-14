"""CLI <-> REST parity tests for the published openapi/opal_look.yaml.

Contract-level only: verifies every operation has an unambiguous CLI mapping
(x-opal-cli, including path-level maps hoisted onto kernel-mounted Path
Items), that the MVP Plus stream/predict surface is declared correctly, and
that the standard kernel-mounted routes are present. No service or CLI is
implemented here.
"""
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec_util  # noqa: E402
SPEC = os.path.join(ROOT, "openapi", "opal_look.yaml")

failures = 0
METHODS = ("get", "post", "put", "patch", "delete")
CTX_HEADERS = (
    "X-Opal-Session-Id",
    "X-Opal-Transaction-Id",
    "X-Opal-Request-Id",
    "X-Opal-Causation-Id",
)


def check(ok, name, detail=""):
    global failures
    print(("PASS" if ok else "FAIL"), name, detail if detail else "")
    failures += 0 if ok else 1


def op(d, method, path):
    return d["paths"].get(path, {}).get(method)


def param_names(d, method, path):
    item = d["paths"].get(path, {})
    o = item.get(method) or {}
    out = set()
    for x in (item.get("parameters", []) or []) + (o.get("parameters", []) or []):
        if isinstance(x, dict):
            out.add(x.get("name"))
    return out


def body_schema(d, method, path):
    o = op(d, method, path) or {}
    return (((o.get("requestBody") or {}).get("content") or {})
            .get("application/json") or {}).get("schema") or {}


def main():
    d = spec_util.load(SPEC)
    paths = d["paths"]

    # Every resolved operation (including kernel-mounted Path Items, whose
    # path-level per-method x-opal-cli maps are hoisted by spec_util.load)
    # has an unambiguous CLI binding and no two ops share (group, command).
    seen = {}
    dupes = []
    verbs = set()
    missing = []
    for p, item in paths.items():
        for m, o in item.items():
            if m not in METHODS or not isinstance(o, dict):
                continue
            cli = o.get("x-opal-cli", {})
            if not (cli.get("group") and cli.get("command")):
                missing.append(f"{m.upper()} {p}")
            key = (cli.get("group"), cli.get("command"))
            if key in seen:
                dupes.append(f"{key}: {seen[key]} vs {m.upper()} {p}")
            seen[key] = f"{m.upper()} {p}"
            verbs.add(cli.get("command"))
    check(not missing, f"all operations have x-opal-cli group+command ({missing[:4]})")
    check(not dupes, f"no duplicate CLI group+command ({dupes[:3]})")
    check({"list", "show", "add", "remove", "update"} & verbs or
          {"list", "get", "create", "delete", "update"} & verbs,
          "standard verbs present")

    # Kernel-mounted standard surface is present.
    for m, p in (
        ("get", "/api/v1/info/"),
        ("get", "/api/v1/info/ping"),
        ("get", "/api/v1/health/"),
        ("get", "/api/v1/health/live"),
        ("get", "/api/v1/health/ready"),
        ("get", "/api/v1/setting/"),
        ("patch", "/api/v1/setting/"),
        ("get", "/api/v1/setting/{key}"),
        ("put", "/api/v1/setting/{key}"),
        ("delete", "/api/v1/setting/{key}"),
        ("get", "/api/v1/profile/"),
        ("post", "/api/v1/profile/"),
        ("post", "/api/v1/profile/{profile_id}/activate"),
        ("post", "/api/v1/backup/create"),
        ("post", "/api/v1/backup/import"),
        ("post", "/api/v1/service/start"),
        ("post", "/api/v1/service/stop"),
        ("get", "/api/v1/service/log"),
    ):
        check(op(d, m, p) is not None, f"{m.upper()} {p} exists")

    # Health probes return status+ready on 200 and 503.
    for p in ("/api/v1/health/live", "/api/v1/health/ready"):
        for code in ("200", "503"):
            sch = (((op(d, "get", p) or {}).get("responses", {})
                    .get(code, {}).get("content", {})
                    .get("application/json", {}) or {}).get("schema") or {})
            req = set(sch.get("required") or [])
            check({"status", "ready"} <= req,
                  f"GET {p} {code} requires status+ready")

    # Engines: kernel collection/item mount plus look-specific ops.
    check(op(d, "get", "/api/v1/engine/") is not None, "GET /engine/ exists")
    check(op(d, "patch", "/api/v1/engine/{engine_id}") is not None,
          "PATCH /engine/{id} exists")
    check(op(d, "post", "/api/v1/engine/discover") is not None,
          "POST /engine/discover exists")
    check(op(d, "get", "/api/v1/engine/{engine_id}/capabilities") is not None,
          "GET /engine/{id}/capabilities exists")

    # Config mutations require a strong If-Match (resolved kernel mounts).
    for m, p in (
        ("patch", "/api/v1/setting/"),
        ("put", "/api/v1/setting/{key}"),
        ("delete", "/api/v1/setting/{key}"),
        ("patch", "/api/v1/engine/{engine_id}"),
        ("patch", "/api/v1/profile/{profile_id}"),
        ("delete", "/api/v1/profile/{profile_id}"),
        ("post", "/api/v1/profile/{profile_id}/activate"),
    ):
        names = param_names(d, m, p)
        check("If-Match" in names, f"{m.upper()} {p} requires If-Match")

    # Stream lifecycle: admission is 202+Location honoring Idempotency-Key.
    start = op(d, "post", "/api/v1/stream/") or {}
    check("202" in start.get("responses", {}), "POST /stream/ admits with 202")
    check("Location" in (start.get("responses", {})
          .get("202", {}).get("headers", {}) or {}),
          "POST /stream/ 202 declares Location")
    check("Idempotency-Key" in param_names(d, "post", "/api/v1/stream/"),
          "POST /stream/ honors Idempotency-Key")

    # StreamStartRequest: video mode is the default; engine implies model.
    ssr = d["components"]["schemas"].get("StreamStartRequest", {})
    check(set(ssr.get("required") or []) == {"source"},
          "StreamStartRequest requires only source")
    check(ssr.get("additionalProperties") is False,
          "StreamStartRequest is closed")
    eng = (ssr.get("properties") or {}).get("engine_id", {})
    check("null" in str(eng.get("type")), "engine_id is nullable (video mode)")

    # Stream read surface and media types.
    check("text/event-stream" in ((op(d, "get", "/api/v1/stream/{stream_id}/events")
          or {}).get("responses", {}).get("200", {})
          .get("content", {}) or {}), "events endpoint is SSE")
    check("multipart/x-mixed-replace" in ((op(d, "get", "/api/v1/stream/{stream_id}/video")
          or {}).get("responses", {}).get("200", {})
          .get("content", {}) or {}), "video endpoint is MJPEG")
    check("image/jpeg" in ((op(d, "get", "/api/v1/stream/{stream_id}/snapshot")
          or {}).get("responses", {}).get("200", {})
          .get("content", {}) or {}), "snapshot returns JPEG")
    check(op(d, "get", "/api/v1/stream/{stream_id}/metrics") is not None,
          "stream metrics endpoint exists")
    check(op(d, "post", "/api/v1/stream/{stream_id}/stop") is not None,
          "stream stop endpoint exists")

    # Predict: requires engine_id + model_id + source; declares failure modes.
    req = body_schema(d, "post", "/api/v1/predict")
    check({"engine_id", "model_id", "source"} <= set(req.get("required") or []),
          "PredictRequest requires engine_id+model_id+source")
    for code in ("404", "422", "413", "429"):
        check(code in (op(d, "post", "/api/v1/predict") or {})
              .get("responses", {}), f"POST /predict declares {code}")

    # Every operation on a parameterized path declares 404.
    missing404 = []
    for p, item in paths.items():
        if "{" not in p:
            continue
        for m, o in item.items():
            if m in METHODS and isinstance(o, dict) and \
                    "404" not in o.get("responses", {}):
                missing404.append(f"{m.upper()} {p}")
    check(not missing404,
          f"parameterized-path ops declare 404 ({missing404[:4]})")

    # Every declared response carries the four correlation headers.
    missing_headers = []
    for p, item in paths.items():
        for m, o in item.items():
            if m not in METHODS or not isinstance(o, dict):
                continue
            for code, r in (o.get("responses") or {}).items():
                hdrs = set((r.get("headers") or {}).keys())
                if not set(CTX_HEADERS) <= hdrs:
                    missing_headers.append(f"{m.upper()} {p} {code}")
    check(not missing_headers,
          f"all responses declare correlation headers ({missing_headers[:4]})")

    # Source security: RTSP-only sources, credentials never echoed.
    check("^rtsps?://" in str(ssr.get("properties", {})
          .get("source", {}).get("pattern", "")),
          "stream source constrained to RTSP/RTSPS")
    status = d["components"]["schemas"].get("StreamStatus", {})
    check("source_redacted" in (status.get("required") or []),
          "StreamStatus requires source_redacted")

    # MVP Plus scope guards: personas, event bus, sources/observations/recording
    # are out of scope.
    forbidden = [p for p in paths if any(
        p.startswith(f"/api/v1{s}") for s in (
            "/persona", "/event", "/observation", "/recording", "/source",
            "/monitor", "/pipeline", "/job", "/media", "/capture",
            "/artifact", "/zone", "/rule", "/session"))]
    check(not forbidden, f"out-of-scope paths absent ({forbidden[:4]})")

    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
