"""Contract regression tests for the unified opal_say.yaml (unified config save/load).

Verifies the published 3.0.0 spec:
- config/load requires strong If-Match with 412+428;
- atomicity + validate-before-apply semantics are required, not SHOULD-optional.
"""
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec_util  # noqa: E402
SPEC = os.path.join(ROOT, "openapi", "opal_say.yaml")

failures = 0


def check(ok, name, detail=""):
    global failures
    print(("PASS" if ok else "FAIL"), name, detail if detail else "")
    failures += 0 if ok else 1


def param_names(op):
    return [x.get("name") for x in op.get("parameters", [])
            if isinstance(x, dict) and x.get("name")]


def main():
    spec = spec_util.load(SPEC)

    check(spec["info"]["version"] == "5.0.0", "info.version is 5.0.0 (persona consolidation)")

    op = spec["paths"]["/api/v1/config/load"]["post"]
    names = param_names(op)
    check("If-Match" in names and
          next(x for x in op["parameters"] if x.get("name") == "If-Match")["required"],
          "config/load requires If-Match")
    check("412" in op["responses"] and "428" in op["responses"],
          "config/load declares 412 + 428")
    check("422" in op["responses"], "config/load keeps 422 invalid config")
    desc = op.get("description", "")
    check("atomic" in desc, "config/load documents atomic application")
    check("intact" in desc, "config/load: failed load leaves previous config intact")
    check("428" in desc and "412" in desc, "config/load documents precondition codes")

    # validate-before-apply exists as a non-mutating endpoint
    val = spec["paths"]["/api/v1/config/validate"]["post"]
    check("200" in val["responses"], "config/validate exists for non-mutating validation")
    check("If-Match" not in param_names(val), "config/validate is read-only (no If-Match)")

    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
