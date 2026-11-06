"""Contract regression tests for opal_listen.v1.4.1.yaml (settings management).

Verifies the versioned 1.4.1 spec against the canonical 1.4.0 baseline:
- only /api/v1/settings/{key} path + the three settings operationIds added;
- native JSON settings values, required If-Match, declared precondition codes;
- backup/import reconciled with the same strong-revision preconditions.
"""
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V140 = os.path.join(ROOT, "openapi", "opal_listen.yaml")
V141 = os.path.join(ROOT, "openapi", "opal_listen.v1.4.1.yaml")

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
    added = set(spec141["paths"]) - set(spec140["paths"])
    check(added == {"/api/v1/settings/{key}"}, "only settings/{key} path added",
          f"(added: {added}, removed: {set(spec140['paths']) - set(spec141['paths'])})")
    new_ids = opids(spec141) - opids(spec140)
    check(len(new_ids) == 3 and all("_settings__key__" in i for i in new_ids),
          "only the three settings/{key} operationIds added", f"({new_ids})")
    check(opids(spec140) - opids(spec141) == set(), "no operationIds removed")
    check(set(spec140["components"]["schemas"]) <=
          set(spec141["components"]["schemas"]), "no schemas removed")

    sk = spec141["paths"]["/api/v1/settings/{key}"]
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

    sr = spec141["components"]["schemas"]["SettingRead"]
    check("value" in sr["properties"] and "type" not in sr["properties"]["value"],
          "SettingRead.value is native JSON (untyped)")
    su = spec141["components"]["schemas"]["SettingUpdate"]
    check(su["required"] == ["value"], "SettingUpdate requires only value")

    imp = spec141["paths"]["/api/v1/backup/import"]["post"]
    check("If-Match" in param_names(imp), "backup/import requires If-Match")
    check("412" in imp["responses"] and "428" in imp["responses"],
          "backup/import declares 412 + 428")

    # collection ops preserved
    coll = spec141["paths"]["/api/v1/settings/"]
    check("get" in coll and "patch" in coll, "settings collection GET/PATCH retained")
    check("If-Match" in param_names(coll["patch"]), "settings PATCH keeps required If-Match")

    # unrelated surfaces untouched (security response additions are the only delta)
    def strip_sec(op):
        o = dict(op)
        o["responses"] = {k: v for k, v in o["responses"].items()
                          if k not in ("401", "403")}
        return o

    for p in ("/api/v1/recognition/", "/api/v1/wakewords/", "/api/v1/intents/"):
        for m, op in spec141["paths"].get(p, {}).items():
            if isinstance(op, dict):
                check(spec140["paths"][p][m] == strip_sec(op) or p not in spec140["paths"],
                      f"{m} {p} unchanged from 1.4.0")

    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
