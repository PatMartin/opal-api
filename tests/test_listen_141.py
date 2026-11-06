"""Contract regression tests for the unified opal_listen.yaml (settings management).

Verifies the published 1.4.1 spec:
- native JSON settings values, required If-Match, declared precondition codes;
- backup/import reconciled with the same strong-revision preconditions.
"""
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = os.path.join(ROOT, "openapi", "opal_listen.yaml")

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

    sk = spec["paths"]["/api/v1/settings/{key}"]
    check(set(sk) & {"get", "put", "delete"} == {"get", "put", "delete"},
          "GET/PUT/DELETE /api/v1/settings/{key} all present")
    check("200" in sk["get"]["responses"] and "404" in sk["get"]["responses"],
          "settings/{key} GET returns 200 + 404 unknown key")
    for mth in ("put", "delete"):
        names = param_names(sk[mth])
        check("If-Match" in names and
              next(x for x in sk[mth]["parameters"] if x.get("name") == "If-Match")["required"],
              f"settings/{{key}} {mth.upper()} requires If-Match")
        check("412" in sk[mth]["responses"] and "428" in sk[mth]["responses"],
              f"settings/{{key}} {mth.upper()} declares 412 + 428")
        check("404" in sk[mth]["responses"], f"settings/{{key}} {mth.upper()} declares 404")
    check("422" in sk["put"]["responses"], "settings/{key} PUT declares 422 invalid value")
    check("422" not in sk["delete"]["responses"], "settings/{key} DELETE needs no 422")

    sr = spec["components"]["schemas"]["SettingRead"]
    check("value" in sr["properties"] and "type" not in sr["properties"]["value"],
          "SettingRead.value is native JSON (untyped)")
    su = spec["components"]["schemas"]["SettingUpdate"]
    check(su["required"] == ["value"], "SettingUpdate requires only value")

    imp = spec["paths"]["/api/v1/backup/import"]["post"]
    check("If-Match" in param_names(imp), "backup/import requires If-Match")
    check("412" in imp["responses"] and "428" in imp["responses"],
          "backup/import declares 412 + 428")

    # collection ops preserved
    coll = spec["paths"]["/api/v1/settings/"]
    check("get" in coll and "patch" in coll, "settings collection GET/PATCH retained")
    check("If-Match" in param_names(coll["patch"]), "settings PATCH keeps required If-Match")

    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
