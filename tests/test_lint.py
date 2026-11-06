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
LOOK = os.path.join(ROOT, "openapi", "opal_look.yaml")
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
    op = d["paths"]["/api/v1/models/{model_id}"]["patch"]
    keep = [x for x in op["parameters"]
            if "/IfMatch" not in str(x.get("$ref", ""))
            and not (isinstance(x, dict) and x.get("name") == "If-Match")]
    assert len(keep) < len(op["parameters"])
    op["parameters"] = keep


def m_cursor(d):
    assert "next_cursor" in d["components"]["schemas"]["SessionPage"]["properties"]
    d["components"]["schemas"]["SessionPage"]["properties"].pop("next_cursor")


def m_probe(d):
    d["paths"]["/api/v1/health/live"]["get"]["responses"].pop("503")


def m_metadata(d):
    # Strip metadata from the declared BusEvent envelope -> rule must fire.
    d["x-opal-event-contract"]["envelope"] = "topic frame + JSON body"


def m_corr(d):
    d["paths"]["/api/v1/health/live"]["get"]["responses"]["200"]["headers"].pop(
        "X-Opal-Request-Id")


def m_corr_406(d):
    # The 406 on analyze/image loses its correlation-header block.
    d["paths"]["/api/v1/analyze/image"]["post"]["responses"]["406"].pop("headers")


def m_error_env(d):
    op = d["paths"]["/api/v1/models/{model_id}"]["get"]["responses"]["404"]
    op.pop("$ref", None)
    op["content"] = {"application/json": {"schema": {
        "type": "object", "properties": {"detail": {"type": "string"}}}}}
    op["headers"] = {}


def m_location(d):
    d["paths"]["/api/v1/media/"]["post"]["responses"]["201"]["headers"].pop("Location")


def m_dup_opid(d):
    # Copy an existing operationId onto a second operation -> duplicate.
    d["paths"]["/api/v1/jobs/{job_id}"]["get"]["operationId"] = \
        d["paths"]["/api/v1/jobs/"]["get"]["operationId"]


def m_ifmatch_pattern(d):
    assert "pattern" in d["components"]["parameters"]["IfMatch"]["schema"]
    d["components"]["parameters"]["IfMatch"]["schema"].pop("pattern")


def m_header_req(d):
    d["components"]["headers"]["OpalRequestIdHeader"]["required"] = False


def m_header_cond(d):
    d["components"]["headers"]["OpalSessionIdHeader"]["required"] = True


def m_broken_ref(d):
    d["paths"]["/api/v1/health/live"]["get"]["responses"]["503"] = {
        "$ref": "#/components/responses/DoesNotExist"}


def m_probe_body(d):
    # Probe loses its required 'ready' -- the rule must see through the $ref.
    assert "ready" in d["components"]["schemas"]["Probe"]["required"]
    d["components"]["schemas"]["Probe"]["required"] = ["status", "version"]


def m_precond(d):
    # A required-If-Match config mutation stops declaring 412/428.
    res = d["paths"]["/api/v1/models/{model_id}"]["patch"]["responses"]
    res.pop("412", None)
    res.pop("428", None)


CASES = [
    ("missing If-Match on config mutation", m_ifmatch, "look", "opal-look-config-ifmatch", 0),
    ("cursor page missing next_cursor", m_cursor, "look", "opal-look-cursor-page", 0),
    ("missing 503 probe response", m_probe, "look", "opal-look-health-probe", 0),
    ("If-Match schema without pattern", m_ifmatch_pattern, "look", "opal-look-ifmatch-strong-schema", 0),
    ("request header made optional", m_header_req, "look", "opal-look-header-required-ids", 0),
    ("session header made required", m_header_cond, "look", "opal-look-header-conditional-ids", 0),
    ("probe body missing required ready", m_probe_body, "look", "opal-look-health-probe", 0),
    ("envelope contract without metadata", m_metadata, "look", "opal-look-event-contract", 0),
    ("missing correlation header", m_corr, "opal", "opal-correlation-headers", 0),
    ("406 missing correlation headers", m_corr_406, "opal", "opal-correlation-headers", 0),
    ("nonstandard error envelope", m_error_env, "opal", "opal-standard-error-body", 0),
    ("If-Match op missing 412/428", m_precond, "opal", "opal-ifmatch-precondition-responses", 1),
    ("201 without Location", m_location, "opal", "opal-201-location-header", 0),
    ("duplicate operationId", m_dup_opid, "generic", "operation-operationId-unique", 0),
    ("broken $ref", m_broken_ref, "generic", "invalid-ref", 0),
]


def main():
    failures = 0
    for name, mut, ruleset, expected, sev in CASES:
        tmp, path = mutate(yaml.safe_load(open(LOOK, encoding="utf-8")), mut)
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

    # Referenced-schema positives: /results/ uses $ref ResultQueryPage;
    # /health/* use $ref OpalHealthProbe. Both must be accepted as-is.
    probe = [x for x in look_findings if x.get("code") in
             ("opal-look-cursor-page", "opal-look-health-probe")]
    ok = not probe
    print(("PASS" if ok else "FAIL"),
          "positive: referenced page/probe schemas accepted",
          "" if ok else f"(errors {probe[:3]})")
    failures += 0 if ok else 1

    # Native JSON setting values: no contract may force value into a string wire type.
    talk = yaml.safe_load(open(os.path.join(ROOT, "openapi", "opal_talk.yaml"), encoding="utf-8"))
    lis = yaml.safe_load(open(os.path.join(ROOT, "openapi", "opal_listen.yaml"), encoding="utf-8"))
    native = (
        "type" not in talk["components"]["schemas"]["SettingUpdate"]["properties"]["value"]
        and "type" not in talk["components"]["schemas"]["SettingRead"]["properties"]["value"]
        and "type" not in lis["components"]["schemas"]["SettingUpdate"]["properties"]["value"]
        and lis["paths"]["/api/v1/settings/"]["get"]["responses"]["200"]["content"]
            ["application/json"]["schema"]["additionalProperties"] is True
    )
    print(("PASS" if native else "FAIL"),
          "positive: native JSON setting values (talk+listen)")
    failures += 0 if native else 1

    print(f"\n{len(CASES) + 3 - failures}/{len(CASES) + 3} assertions passed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
