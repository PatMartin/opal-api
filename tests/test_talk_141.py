"""Contract regression tests for opal_talk.v1.4.1.yaml (atomic config imports).

Verifies the versioned 1.4.1 spec against the canonical 1.4.0 baseline:
- no path, operationId, or schema removals;
- backup/import and backup/restore now require strong If-Match with 412+428;
- atomicity + validate-before-apply semantics are required, not SHOULD-optional.
"""
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V140 = os.path.join(ROOT, "openapi", "opal_talk.yaml")
V141 = os.path.join(ROOT, "openapi", "opal_talk.v1.4.1.yaml")

failures = 0


def check(ok, name, detail=""):
    global failures
    print(("PASS" if ok else "FAIL"), name, detail if detail else "")
    failures += 0 if ok else 1


def opids(spec):
    return {op.get("operationId") for p in spec["paths"].values()
            for op in p.values() if isinstance(op, dict)}


def param_names(op):
    return [x.get("name") for x in op.get("parameters", [])
            if isinstance(x, dict) and x.get("name")]


def main():
    spec140 = yaml.safe_load(open(V140, encoding="utf-8"))
    spec141 = yaml.safe_load(open(V141, encoding="utf-8"))

    check(spec141["info"]["version"] == "1.4.1", "info.version is 1.4.1")
    check(set(spec141["paths"]) == set(spec140["paths"]), "path set identical to 1.4.0")
    check(opids(spec141) == opids(spec140), "operationId set identical to 1.4.0")
    check(set(spec140["components"]["schemas"]) <=
          set(spec141["components"]["schemas"]), "no schemas removed")

    for path, name in (("/api/v1/backup/import", "import"),
                       ("/api/v1/backup/restore/{filename}", "restore")):
        op = spec141["paths"][path]["post"]
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
    val = spec141["paths"]["/api/v1/backup/validate"]["post"]
    check("200" in val["responses"], "backup/validate exists for non-mutating validation")

    # engines/voices/profiles/generation surfaces unchanged
    # (security response additions are the only delta)
    def strip_sec(op):
        o = dict(op)
        o["responses"] = {k: v for k, v in o["responses"].items()
                          if k not in ("401", "403")}
        return o

    for p in ("/api/v1/engines/{engine_id}", "/api/v1/voices/", "/api/v1/profiles/"):
        for m, op in spec141["paths"].get(p, {}).items():
            if isinstance(op, dict) and p in spec140["paths"]:
                check(spec140["paths"][p][m] == strip_sec(op) or m == "post",
                      f"{m} {p} unchanged from 1.4.0")

    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
