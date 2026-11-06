"""Contract regression tests for the unified opal_talk.yaml (atomic config imports).

Verifies the published 1.4.1 spec:
- backup/import and backup/restore now require strong If-Match with 412+428;
- atomicity + validate-before-apply semantics are required, not SHOULD-optional.
"""
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = os.path.join(ROOT, "openapi", "opal_talk.yaml")

failures = 0


def check(ok, name, detail=""):
    global failures
    print(("PASS" if ok else "FAIL"), name, detail if detail else "")
    failures += 0 if ok else 1


def param_names(op):
    return [x.get("name") for x in op.get("parameters", [])
            if isinstance(x, dict) and x.get("name")]


def main():
    spec = yaml.safe_load(open(SPEC, encoding="utf-8"))

    check(spec["info"]["version"] == "1.4.1", "info.version is 1.4.1")

    for path, name in (("/api/v1/backup/import", "import"),
                       ("/api/v1/backup/restore/{filename}", "restore")):
        op = spec["paths"][path]["post"]
        names = param_names(op)
        check("If-Match" in names and
              next(x for x in op["parameters"] if x.get("name") == "If-Match")["required"],
              f"backup/{name} requires If-Match")
        check("412" in op["responses"] and "428" in op["responses"],
              f"backup/{name} declares 412 + 428")
        check("422" in op["responses"], f"backup/{name} keeps 422 invalid config")
        desc = op.get("description", "")
        check("atomically" in desc or "atomic" in desc,
              f"backup/{name} documents atomic application")
        check("intact" in desc, f"backup/{name}: failed import leaves previous config intact")
        check("428" in desc and "412" in desc, f"backup/{name} documents precondition codes")

    # validate-before-apply exists as a non-mutating endpoint
    val = spec["paths"]["/api/v1/backup/validate"]["post"]
    check("200" in val["responses"], "backup/validate exists for non-mutating validation")

    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
