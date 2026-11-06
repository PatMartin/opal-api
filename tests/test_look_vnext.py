"""Draft validation for openapi/proposals/opal_look.vnext.yaml.

Checks parsing, local $ref resolution, unique operationIds, and required
correlation headers on every response — contract-only, no runtime behavior.
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


def collect_refs(node, refs=None):
    refs = refs if refs is not None else []
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "$ref" and isinstance(v, str):
                refs.append(v)
            else:
                collect_refs(v, refs)
    elif isinstance(node, list):
        for i in node:
            collect_refs(i, refs)
    return refs


def ref_exists(doc, ref):
    node = doc
    for part in ref.removeprefix("#/").split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        if not isinstance(node, dict) or part not in node:
            return False
        node = node[part]
    return True


def main():
    d = yaml.safe_load(open(DRAFT, encoding="utf-8"))
    check(d["info"]["version"] != "1.4.0", "draft is not versioned as the published 1.4.0")
    check("draft" in d["info"]["version"].lower() or d.get("x-opal-stage") == "draft",
          "draft is clearly identified as a draft")
    check(d.get("x-opal-stage") == "draft", "x-opal-stage: draft marker present")

    refs = collect_refs(d)
    external = [r for r in refs if not r.startswith("#/")]
    check(not external, f"no external $refs ({external[:3]})")
    missing = [r for r in set(refs) if not ref_exists(d, r)]
    check(not missing, f"every $ref resolves ({missing[:5]})")

    opids = [op.get("operationId") for p in d["paths"].values()
             for op in p.values() if isinstance(op, dict) and op.get("operationId")]
    check(len(opids) == len(set(opids)), "all operationIds unique")

    def resolve(node):
        if isinstance(node, dict):
            if set(node) == {"$ref"} and node["$ref"].startswith("#/components/responses/"):
                name = node["$ref"].rsplit("/", 1)[-1]
                return resolve(d["components"]["responses"].get(name, {}))
            return {k: resolve(v) for k, v in node.items()}
        if isinstance(node, list):
            return [resolve(i) for i in node]
        return node

    for p, item in d["paths"].items():
        for m, op in item.items():
            if not isinstance(op, dict):
                continue
            for code, r in op.get("responses", {}).items():
                text = str(resolve(r))
                for h in ("X-Opal-Session-Id", "X-Opal-Transaction-Id",
                          "X-Opal-Request-Id", "X-Opal-Causation-Id"):
                    comp = "Opal" + h.split("-")[2].title() + "IdHeader"
                    if h not in text and comp not in text:
                        check(False, f"{m.upper()} {p} {code} missing {h}")

    # simplified architecture invariants
    paths = set(d["paths"])
    check(not any("/zones/" in p or p.rstrip("/").endswith("/zones") for p in paths),
          "zones live under sources, not a top-level resource")
    check(any("/pipelines" in p for p in paths), "pipelines exist as a resource")
    check(any("/monitors" in p for p in paths), "monitors exist as a resource")
    check(not any(p.rstrip("/").endswith("/sessions") or "/sessions/" in p for p in paths),
          "no public session management")
    check(any("/media/" == p.rstrip("/") or p == "/api/v1/media/" for p in paths),
          "media unifies the artifact surface")
    check(any("/recordings" in p for p in paths), "recordings remain explicit")

    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
