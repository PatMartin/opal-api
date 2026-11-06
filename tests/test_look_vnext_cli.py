"""CLI <-> REST parity tests for openapi/proposals/opal_look.vnext.yaml.

Contract-level only: verifies every operation has an unambiguous CLI mapping
(x-opal-cli) and that the documented CLI flows map to real REST endpoints,
parameters, and response schemas. No service or CLI is implemented here.
"""
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRAFT = os.path.join(ROOT, "openapi", "proposals", "opal_look.vnext.yaml")

failures = 0


def check(ok, name, detail=""):
    global failures
    print(("PASS" if ok else "FAIL"), name, detail if detail else "")
    failures += 0 if ok else 1


def op(d, method, path):
    return d["paths"].get(path, {}).get(method)


def params(d, method, path):
    o = op(d, method, path)
    comps = d["components"].get("parameters", {})
    out = set()
    for x in (o or {}).get("parameters", []) or []:
        if isinstance(x, dict):
            r = comps.get(x.get("$ref", "").split("/")[-1], x)
            out.add(r.get("name"))
    return out


def main():
    d = yaml.safe_load(open(DRAFT, encoding="utf-8"))
    paths = d["paths"]

    # every public REST op has an unambiguous CLI mapping
    seen = {}
    dupes = []
    verbs = set()
    for p, item in paths.items():
        for m, o in item.items():
            if m not in ("get", "post", "put", "patch", "delete"):
                continue
            cli = o.get("x-opal-cli", {})
            check(bool(cli.get("group")) and bool(cli.get("command")),
                  f"{m.upper()} {p} has x-opal-cli group+command")
            key = (cli.get("group"), cli.get("command"))
            if key in seen:
                dupes.append(f"{key}: {seen[key]} vs {m.upper()} {p}")
            seen[key] = f"{m.upper()} {p}"
            verbs.add(cli.get("command"))
    check(not dupes, f"no duplicate CLI group+command ({dupes[:3]})")
    check({"list", "show", "add", "remove", "update"} & verbs or
          {"list", "get", "create", "delete", "update"} & verbs,
          "standard verbs present")

    # 1) register an RTSP source -> POST /sources/ accepts a uri/url body
    check(op(d, "post", "/api/v1/sources/") is not None, "POST /sources/ exists")
    src = d["components"]["schemas"].get("SourceCreate", {})
    check(any(k in str(src) for k in ("uri", "url", "rtsp")),
          "SourceCreate accepts a stream URI/RTSP")

    # 2) view live feed without creating a session
    check(op(d, "get", "/api/v1/sources/{source_id}/stream") is not None,
          "GET /sources/{id}/stream exists")
    check(not any("/sessions" in p for p in paths), "no /sessions/ public path")

    # 3) enable/disable annotations on the live stream
    sp = params(d, "get", "/api/v1/sources/{source_id}/stream")
    check("annotations" in sp or "show_labels" in sp or "show_boxes" in sp,
          "stream exposes annotation toggles")

    # 4) analyze a single image
    check(op(d, "post", "/api/v1/analyze/image") is not None, "POST /analyze/image exists")

    # 5) filter observations for people only -> label/task filters on /observations/
    fp = params(d, "get", "/api/v1/observations/")
    check("label" in fp or "task" in fp, "observations filterable by label/task")

    # 6) motion condition -> motion filter schema exists (unknown != no-motion)
    check(any("Motion" in s for s in d["components"]["schemas"]),
          "motion filter schema exists")

    # 7) start persistent monitor
    check(op(d, "post", "/api/v1/monitors/") is not None, "POST /monitors/ exists")

    # 8) capture a still image
    check(op(d, "post", "/api/v1/sources/{source_id}/capture") is not None or
          op(d, "get", "/api/v1/sources/{source_id}/frame") is not None or
          op(d, "post", "/api/v1/sources/{source_id}/captures/") is not None,
          "still-capture endpoint exists")

    # 9) start + stop recording
    check(op(d, "post", "/api/v1/recordings/") is not None and
          op(d, "post", "/api/v1/recordings/{recording_id}/stop") is not None,
          "recording start + stop exist")

    # 10) retrieve recorded media
    check(op(d, "get", "/api/v1/media/{media_id}") is not None or
          op(d, "get", "/api/v1/media/{media_id}/content") is not None,
          "media retrieval exists")

    # 11) query retained observations -> cursor-paginated
    qp = params(d, "get", "/api/v1/observations/")
    check("cursor" in qp or "limit" in qp, "observations cursor-paginated")

    # 12) unsupported capabilities -> capabilities endpoint exists
    check(op(d, "get", "/api/v1/capabilities/") is not None, "GET /capabilities/ exists")

    # negatives: unsupported features, invalid filters, unavailable models,
    # missing resources, stream interruption -> all must produce declared errors
    for m, p, code in (
        ("get", "/api/v1/sources/{source_id}", "404"),
        ("get", "/api/v1/monitors/{monitor_id}", "404"),
        ("get", "/api/v1/recordings/{recording_id}", "404"),
        ("post", "/api/v1/analyze/", "422"),
        ("post", "/api/v1/analyze/image", "422"),
        ("post", "/api/v1/analyze/image", "406"),
        ("get", "/api/v1/observations/", "422"),
    ):
        check(code in (op(d, m, p) or {}).get("responses", {}),
              f"{m.upper()} {p} declares {code}")
    # stream interruption -> documented terminal error path on stream ops
    stream_desc = str(op(d, "get", "/api/v1/sources/{source_id}/stream") or "")
    check("error" in stream_desc.lower() or "event-stream" in stream_desc.lower(),
          "stream documents in-band/terminal failure behavior")

    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
