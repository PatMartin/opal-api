"""Regression tests proving OPAL Spectral rules fire on deliberately invalid specs.

Each case mutates a copy of a published contract, lints it with the relevant
ruleset, and asserts the expected rule code appears in the findings.
Nonzero Spectral exits are normal for violations; unparseable output or a
missing executable is an explicit test failure.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec_util  # noqa: E402

LOOK = os.path.join(ROOT, "openapi", "opal_look.yaml")
THINK = os.path.join(ROOT, "openapi", "opal_think.yaml")
KERNEL = os.path.join(ROOT, "openapi", "shared", "opal_kernel.yaml")
DOCS = {"look": LOOK, "think": THINK, "kernel": KERNEL}
RULES = {
    "look": os.path.join(ROOT, ".spectral.opal.look.yaml"),
    "opal": os.path.join(ROOT, ".spectral.opal.yaml"),
    "generic": os.path.join(ROOT, ".spectral.yaml"),
}


def spectral_exe():
    """Resolve the project-pinned Spectral CLI; no network lookup."""
    local = os.path.join(ROOT, "node_modules", ".bin",
                         "spectral.cmd" if os.name == "nt" else "spectral")
    if os.path.exists(local):
        return local
    return shutil.which("spectral") or shutil.which("npx")


EXE = spectral_exe()


def lint(ruleset_key, path):
    """Return parsed findings. Raises RuntimeError on unusable output."""
    if not EXE:
        raise RuntimeError("spectral executable not found")
    r = subprocess.run([EXE, "lint", "-r", RULES[ruleset_key], path, "-f", "json"],
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode not in (0, 1):
        raise RuntimeError(
            f"spectral exited {r.returncode}: {r.stderr.strip() or r.stdout.strip()}")
    try:
        findings = json.loads(r.stdout)
    except json.JSONDecodeError:
        # Spectral appends a human-readable summary after the JSON array when
        # no error-severity findings exist (e.g. "[]No results...").
        try:
            findings = json.loads(r.stdout[: r.stdout.rfind("]") + 1])
        except json.JSONDecodeError:
            raise RuntimeError(
                f"invalid JSON from spectral: {r.stdout[:200]} / {r.stderr[:200]}")
    if not isinstance(findings, list) or any(not isinstance(x, dict) for x in findings):
        raise RuntimeError(f"unexpected spectral output shape: {findings[:1]}")
    return findings


def codes(results):
    return [x.get("code") for x in results]


def mutate(doc, fn):
    fn(doc)
    tmp = tempfile.TemporaryDirectory(prefix="opal-lint-")
    path = os.path.join(tmp.name, "mutated.yaml")
    yaml.safe_dump(doc, open(path, "w", encoding="utf-8"), sort_keys=False)
    return tmp, path


def m_ifmatch(d):
    op = d["paths"]["/api/v1/engine/{engine_id}"]["patch"]
    keep = [x for x in op["parameters"]
            if "/IfMatch" not in str(x.get("$ref", ""))
            and not (isinstance(x, dict) and x.get("name") == "If-Match")]
    assert len(keep) < len(op["parameters"])
    op["parameters"] = keep


def m_probe(d):
    d["paths"]["/api/v1/health/live"]["get"]["responses"].pop("503")


def m_metadata(d):
    # Inject a BusEvent envelope missing metadata -> rule must fire.
    d["x-opal-event-contract"] = {"envelope": "topic frame + JSON body"}


def m_corr(d):
    d["paths"]["/api/v1/health/live"]["get"]["responses"]["200"]["headers"].pop(
        "X-Opal-Request-Id")


def m_corr_413(d):
    # The 413 on predict loses its correlation-header block.
    d["paths"]["/api/v1/predict"]["post"]["responses"]["413"].pop("headers")


def m_error_env(d):
    op = d["paths"]["/api/v1/model/{model_id}"]["get"]["responses"]["404"]
    op.pop("$ref", None)
    op["content"] = {"application/json": {"schema": {
        "type": "object", "properties": {"detail": {"type": "string"}}}}}
    op["headers"] = {}


def m_location(d):
    d["paths"]["/api/v1/profile/"]["post"]["responses"]["201"]["headers"].pop(
        "Location")


def m_dup_opid(d):
    # Copy an existing operationId onto a second operation -> duplicate.
    d["paths"]["/api/v1/stream/{stream_id}"]["get"]["operationId"] = \
        d["paths"]["/api/v1/stream/"]["get"]["operationId"]


def m_ifmatch_pattern(d):
    # Resolved doc: drop the strong-ETag pattern from an inlined If-Match parameter.
    op = d["paths"]["/api/v1/setting/"]["patch"]
    ifm = next(x for x in op["parameters"] if x.get("name") == "If-Match")
    assert "pattern" in ifm["schema"]
    ifm["schema"].pop("pattern")


def m_header_req(d):
    # Kernel doc: request-id header loses its required marker.
    d["components"]["headers"]["OpalRequestIdHeader"]["required"] = False


def m_header_cond(d):
    # Kernel doc: session-id header becomes mandatory.
    d["components"]["headers"]["OpalSessionIdHeader"]["required"] = True


def m_broken_ref(d):
    d["paths"]["/api/v1/health/live"]["get"]["responses"]["503"] = {
        "$ref": "#/components/responses/DoesNotExist"}


def m_probe_body(d):
    # Probe loses its required 'ready' at the inlined kernel pathItem site.
    sch = d["paths"]["/api/v1/health/live"]["get"]["responses"]["200"][
        "content"]["application/json"]["schema"]
    assert "ready" in sch["required"]
    sch["required"] = ["status", "version"]


def m_precond(d):
    # A required-If-Match config mutation stops declaring 412/428.
    res = d["paths"]["/api/v1/engine/{engine_id}"]["patch"]["responses"]
    res.pop("412", None)
    res.pop("428", None)


def m_cli_descriptor(d):
    # Legacy string annotation replaces the structured descriptor.
    op = d["paths"]["/api/v1/task/"]["get"]
    assert op["x-opal-cli"]["command"] == "list"
    op["x-opal-cli"] = "task list"


def m_cli_map(d):
    # Path-level per-method map gains a non-method key.
    item = d["paths"]["/api/v1/profile/"]
    assert item["x-opal-cli"]["get"]["command"] == "list"
    item["x-opal-cli"]["bogus"] = {"command": "list"}


CASES = [
    ("missing If-Match on config mutation", "look", m_ifmatch, "look", "opal-look-config-ifmatch", 0),
    ("missing 503 probe response", "look", m_probe, "look", "opal-look-health-probe", 0),
    ("If-Match schema without pattern", "look", m_ifmatch_pattern, "look", "opal-look-ifmatch-strong-schema", 0),
    ("request header made optional", "kernel", m_header_req, "opal", "opal-header-required-ids", 0),
    ("session header made required", "kernel", m_header_cond, "opal", "opal-header-conditional-ids", 0),
    ("probe body missing required ready", "look", m_probe_body, "look", "opal-look-health-probe", 0),
    ("envelope contract without metadata", "look", m_metadata, "look", "opal-look-event-contract", 0),
    ("missing correlation header", "look", m_corr, "opal", "opal-correlation-headers", 0),
    ("413 missing correlation headers", "look", m_corr_413, "opal", "opal-correlation-headers", 0),
    ("nonstandard error envelope", "look", m_error_env, "opal", "opal-standard-error-body", 0),
    ("If-Match op missing 412/428", "look", m_precond, "opal", "opal-ifmatch-precondition-responses", 1),
    ("201 without Location", "look", m_location, "opal", "opal-201-location-header", 0),
    ("duplicate operationId", "look", m_dup_opid, "generic", "operation-operationId-unique", 0),
    ("broken $ref", "look", m_broken_ref, "generic", "invalid-ref", 0),
    ("legacy string cli annotation", "think", m_cli_descriptor, "opal", "opal-cli-descriptor", 0),
    ("cli method map non-method key", "think", m_cli_map, "opal", "opal-cli-method-map", 0),
]


def main():
    failures = 0
    for name, doc_key, mut, ruleset, expected, sev in CASES:
        tmp, path = mutate(spec_util.load(DOCS[doc_key]), mut)
        try:
            hits = [x for x in lint(ruleset, path)
                    if x.get("code") == expected and x.get("severity") == sev]
            ok = bool(hits)
            print(("PASS" if ok else "FAIL"), name, "->", expected,
                  f"(sev {sev})" if ok else f"(got {codes(lint(ruleset, path))[:6]})")
            failures += 0 if ok else 1
        except RuntimeError as e:
            print("FAIL", name, "->", e)
            failures += 1
        finally:
            tmp.cleanup()

    look_findings = lint("look", LOOK)
    errs = [x for x in look_findings if x.get("severity") == 0]
    ok = not errs
    print(("PASS" if ok else "FAIL"), "positive: opal_look.yaml lint:look clean",
          "" if ok else f"(errors {errs[:3]})")
    failures += 0 if ok else 1

    # Referenced-schema positives: /health/* use $ref OpalHealthProbe —
    # must be accepted as-is.
    probe = [x for x in look_findings if x.get("code") == "opal-look-health-probe"]
    ok = not probe
    print(("PASS" if ok else "FAIL"),
          "positive: referenced page/probe schemas accepted",
          "" if ok else f"(errors {probe[:3]})")
    failures += 0 if ok else 1

    # Native JSON setting values: no contract may force value into a string wire type.
    # Read through the kernel-mounted settings ops (resolved spec).
    say = spec_util.load(os.path.join(ROOT, "openapi", "opal_say.yaml"))
    lis = spec_util.load(os.path.join(ROOT, "openapi", "opal_listen.yaml"))

    def key_op(spec, method):
        return spec["paths"]["/api/v1/setting/{key}"][method]

    upd = lambda spec: key_op(spec, "put")["requestBody"]["content"][
        "application/json"]["schema"]
    rd = lambda spec: key_op(spec, "get")["responses"]["200"]["content"][
        "application/json"]["schema"]
    native = (
        "type" not in upd(say)["properties"]["value"]
        and "type" not in rd(say)["properties"]["value"]
        and "type" not in upd(lis)["properties"]["value"]
        and lis["paths"]["/api/v1/setting/"]["get"]["responses"]["200"]["content"]
            ["application/json"]["schema"]["additionalProperties"] is True
    )
    print(("PASS" if native else "FAIL"),
          "positive: native JSON setting values (say+listen)")
    failures += 0 if native else 1

    print(f"\n{len(CASES) + 3 - failures}/{len(CASES) + 3} assertions passed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
