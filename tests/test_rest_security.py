"""Suite-wide REST security contract assertions.

Every OPAL contract declares BearerAuth + the shared authorization semantics;
every operation declares 401 + 403. EVENT keeps its stronger scoped model.
"""
import glob
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = sorted(glob.glob(os.path.join(ROOT, "openapi", "opal_*.yaml"))
               + glob.glob(os.path.join(ROOT, "openapi", "proposals", "*.yaml")))

# Published 1.4.0 LISTEN/TALK are superseded by their v1.4.1 proposals, which
# carry the reconciled declarations; the frozen published files predate the
# suite security standard and are exempt until they are superseded.
FROZEN = {"opal_listen.yaml", "opal_talk.yaml"}
FILES = [f for f in FILES if os.path.basename(f) not in FROZEN]

failures = 0


def check(ok, name, detail=""):
    global failures
    print(("PASS" if ok else "FAIL"), name, detail if detail else "")
    failures += 0 if ok else 1


def main():
    for f in FILES:
        short = os.path.basename(f)
        d = yaml.safe_load(open(f, encoding="utf-8"))
        ss = d.get("components", {}).get("securitySchemes", {})
        check("BearerAuth" in ss, f"{short}: BearerAuth declared")
        check(ss.get("BearerAuth", {}).get("scheme") == "bearer",
              f"{short}: BearerAuth is http/bearer")
        check(d.get("security") == [{"BearerAuth": []}],
              f"{short}: top-level security requires BearerAuth")
        desc = ss.get("BearerAuth", {}).get("description", "")
        check("loopback" in desc.lower(), f"{short}: loopback semantics documented")
        check("credential" in desc.lower() or "token_env" in desc,
              f"{short}: credential handling documented")

        nops = 0
        n401 = n403 = 0
        for p, item in d["paths"].items():
            for m, op in item.items():
                if not isinstance(op, dict) or "responses" not in op:
                    continue
                nops += 1
                r = op["responses"]
                if "401" in r:
                    n401 += 1
                if "403" in r:
                    n403 += 1
        check(n401 == nops, f"{short}: 401 on every op ({n401}/{nops})")
        check(n403 == nops, f"{short}: 403 on every op ({n403}/{nops})")

        auth = d.get("x-opal-authorization", {})
        sem = auth.get("semantics", {})
        check(bool(auth), f"{short}: x-opal-authorization extension present")
        check(sem.get("missing_or_invalid_credentials") == "401",
              f"{short}: 401 semantics declared")
        check(sem.get("authenticated_but_not_permitted") == "403",
              f"{short}: 403 semantics declared")
        check("secret" in str(sem.get("secrets", "")).lower(),
              f"{short}: secrets never exposed documented")
        check("correlation" in str(sem.get("credentials", "")).lower() or
              "correlation" in str(sem).lower(),
              f"{short}: correlation headers not credentials documented")

    # EVENT keeps the stronger scoped model
    ev = yaml.safe_load(open(os.path.join(ROOT, "openapi", "opal_event.v1.4.1.yaml"),
                             encoding="utf-8"))
    ea = ev.get("x-opal-authorization", {})
    check(bool(ea.get("scopes")), "event: scoped authorization model preserved")
    check(bool(ea.get("principals", {}).get("think")),
          "event: THINK principal preserved")

    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
