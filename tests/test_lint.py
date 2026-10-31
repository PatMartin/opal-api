"""Regression tests proving OPAL Spectral rules fire on deliberately invalid specs.

Each case mutates a copy of a published contract, lints with the relevant
ruleset, and asserts the expected rule code appears in the findings.
"""
import json, os, subprocess, sys, tempfile

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOOK = os.path.join(ROOT, "openapi", "opal_look.yaml")
RULES = {
    "look": os.path.join(ROOT, ".spectral.opal.look.yaml"),
    "opal": os.path.join(ROOT, ".spectral.opal.yaml"),
    "generic": os.path.join(ROOT, ".spectral.yaml"),
}


def lint(ruleset_key, path):
    r = subprocess.run(
        ["npx", "spectral", "lint", "-r", RULES[ruleset_key], path, "-f", "json"],
        capture_output=True, text=True, cwd=ROOT, shell=True)
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return []


def codes(results):
    return [x.get("code") for x in results]


def mutated_look(fn):
    doc = yaml.safe_load(open(LOOK, encoding="utf-8"))
    fn(doc)
    p = os.path.join(tempfile.mkdtemp(prefix="opal-lint-"), "mutated.yaml")
    yaml.safe_dump(doc, open(p, "w"), sort_keys=False)
    return p


def m_ifmatch(d):
    op = d["paths"]["/api/v1/models/{model_id}"]["patch"]
    op["parameters"] = [x for x in op["parameters"]
                        if not (isinstance(x, dict) and x.get("name") == "If-Match")]


def m_cursor(d):
    d["paths"]["/api/v1/sessions/"]["get"]["responses"]["200"]["content"][
        "application/json"]["schema"]["properties"].pop("next_cursor")


def m_probe(d):
    d["paths"]["/api/v1/health/live"]["get"]["responses"].pop("503")


def m_metadata(d):
    d["components"]["schemas"]["BusEvent"]["required"].append("metadata")


def m_corr(d):
    d["paths"]["/api/v1/health/live"]["get"]["responses"]["200"]["headers"].pop(
        "X-Opal-Request-Id")


def m_error_env(d):
    op = d["paths"]["/api/v1/models/{model_id}"]["get"]["responses"]["404"]
    op.pop("$ref", None)
    op["content"] = {"application/json": {"schema": {
        "type": "object", "properties": {"detail": {"type": "string"}}}}}
    op["headers"] = {}


def m_location(d):
    d["paths"]["/api/v1/media/"]["post"]["responses"]["201"]["headers"].pop("Location")


def m_dup_opid(d):
    d["paths"]["/health"]["get"]["operationId"] = "get_service_info"


def m_broken_ref(d):
    d["paths"]["/api/v1/health/live"]["get"]["responses"]["503"] = {
        "$ref": "#/components/responses/DoesNotExist"}


CASES = [
    ("missing If-Match on config mutation", m_ifmatch, "look", "opal-look-config-ifmatch"),
    ("missing cursor field", m_cursor, "look", "opal-look-cursor-page"),
    ("missing 503 probe response", m_probe, "look", "opal-look-health-probe"),
    ("top-level required metadata", m_metadata, "look", "opal-look-bus-event-envelope"),
    ("missing correlation header", m_corr, "opal", "opal-correlation-headers"),
    ("nonstandard error envelope", m_error_env, "opal", "opal-standard-error-body"),
    ("201 without Location", m_location, "opal", "opal-201-location-header"),
    ("duplicate operationId", m_dup_opid, "generic", "operation-operationId-unique"),
]


def main():
    failures = 0
    for name, mut, ruleset, expected in CASES:
        got = codes(lint(ruleset, mutated_look(mut)))
        ok = expected in got
        print(("PASS" if ok else "FAIL"), name, "->", expected,
              "" if ok else f"(got {got[:6]})")
        failures += 0 if ok else 1

    # positive control: the real contract must stay clean under the look ruleset
    errs = [x for x in lint("look", LOOK) if x.get("severity") == 0]
    ok = not errs
    print(("PASS" if ok else "FAIL"), "positive: opal_look.yaml lint:look clean",
          "" if ok else f"(errors {errs[:3]})")
    failures += 0 if ok else 1

    print(f"\n{len(CASES) + 1 - failures}/{len(CASES) + 1} assertions passed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
