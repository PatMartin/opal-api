"""Load an OPAL OpenAPI spec with $refs fully resolved.

Service specs mount shared Path Items and reference shared components in
openapi/shared/opal_kernel.yaml via external $refs. Tests assert against
the effective (resolved) contract, so this helper inlines external refs and
then dereferences internal '#/components/...' refs as well.

External refs are resolved relative to the document that contains them, so a
spec may consume any number of shared contract bases. Inlined fragments have
their inner refs rebased to the document they came from, which keeps '#/...'
and './...' targets correct no matter where the fragment is mounted.
"""
import copy
import os

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KERNEL_PATH = os.path.join(ROOT, "openapi", "shared", "opal_kernel.yaml")


def _pointer(doc, frag):
    node = doc
    for part in frag.lstrip("#/").split("/"):
        node = node[part.replace("~1", "/").replace("~0", "~")]
    return node


def _doc_path(base_path, ref):
    """Absolute path of the document a $ref written in `base_path` targets."""
    filepart = ref.split("#", 1)[0]
    if not filepart:
        return base_path
    return os.path.normpath(os.path.join(os.path.dirname(base_path), filepart))


def _rebase(node, base_path):
    """Rewrite refs inside a fragment inlined from `base_path` so they stay
    resolvable in the host document: '#/x' becomes '<base_path>#/x' and
    './rel.yaml#/x' becomes its path-normalized absolute form."""
    if isinstance(node, dict):
        if "$ref" in node and isinstance(node["$ref"], str):
            ref = node["$ref"]
            node = dict(node)
            if ref.startswith("#"):
                node["$ref"] = base_path + ref
            else:
                node["$ref"] = _doc_path(base_path, ref) + "#" + ref.split("#", 1)[1]
        return {k: _rebase(v, base_path) for k, v in node.items()}
    if isinstance(node, list):
        return [_rebase(v, base_path) for v in node]
    return node


def _deref(node, doc_path, docs, depth=0):
    if depth > 25:
        return node
    if isinstance(node, dict):
        if "$ref" in node:
            ref = node["$ref"]
            src_path = _doc_path(doc_path, ref)
            if src_path not in docs:
                docs[src_path] = yaml.safe_load(open(src_path, encoding="utf-8"))
            src = docs[src_path]
            frag = ref.split("#", 1)[1]
            target = _rebase(copy.deepcopy(_pointer(src, frag)), src_path)
            merged = {k: v for k, v in node.items() if k != "$ref"}
            merged.update(target if isinstance(target, dict) else {"value": target})
            return _deref(merged, doc_path, docs, depth + 1)
        return {k: _deref(v, doc_path, docs, depth) for k, v in node.items()}
    if isinstance(node, list):
        return [_deref(v, doc_path, docs, depth) for v in node]
    return node


_METHODS = ("get", "post", "put", "patch", "delete")


def _hoist_cli(spec):
    """Module-declared bindings on mounted Path Items may carry per-op
    x-opal-cli metadata as a path-level {method: value} map (an extension
    beside $ref cannot inject into operations defined in another document).
    Kernel-owned Path Items carry per-operation descriptors natively and need
    no hoisting. For the resolved view, copy each map entry onto the operation
    it describes."""
    for item in (spec.get("paths") or {}).values():
        if not isinstance(item, dict):
            continue
        cli = item.get("x-opal-cli")
        if isinstance(cli, dict) and any(m in cli for m in _METHODS):
            for m in _METHODS:
                if m in cli and isinstance(item.get(m), dict):
                    item[m].setdefault("x-opal-cli", cli[m])
    return spec


def _internalize(node):
    """After external components are merged into the resolved document,
    rewrite any '<file>#/X' refs to internal '#/X' refs so the document is
    self-contained (and mutates cleanly to a temp file)."""
    if isinstance(node, dict):
        if "$ref" in node and isinstance(node["$ref"], str) and "#" in node["$ref"]:
            filepart, _, frag = node["$ref"].partition("#")
            if filepart:
                node = dict(node)
                node["$ref"] = "#" + frag
        return {k: _internalize(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_internalize(v) for v in node]
    return node


def _resolve_module_key(spec):
    """Kernel-owned CLI descriptors use `modules.<module-key>` as the binds
    target for `--module FILE`; each receiving module substitutes its own
    compartment key (declared via `x-opal-profile-namespace.compartment`)."""
    comp = (spec.get("x-opal-profile-namespace") or {}).get("compartment")
    if not comp:
        return spec

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if isinstance(v, str) and "<module-key>" in v:
                    node[k] = v.replace("<module-key>", comp)
                else:
                    walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    for item in (spec.get("paths") or {}).values():
        if isinstance(item, dict):
            for op in item.values():
                if isinstance(op, dict) and "x-opal-cli" in op:
                    walk(op["x-opal-cli"])
    return spec


def load(path):
    """Return the spec at `path` with all $refs resolved.

    Components of every externally referenced document are also merged into
    `components` and all file-qualified refs are internalized, so the result
    mirrors the bundled (self-contained) document a consumer would see.
    Kernel-owned `modules.<module-key>` binds targets are substituted with
    the receiving module's declared compartment key."""
    ap = os.path.normpath(os.path.abspath(path))
    docs = {ap: yaml.safe_load(open(ap, encoding="utf-8"))}
    resolved = _hoist_cli(_deref(docs[ap], ap, docs))
    comps = resolved.setdefault("components", {})
    for p, doc in docs.items():
        if p == ap:
            continue
        for kind, entries in (doc.get("components") or {}).items():
            target = comps.setdefault(kind, {})
            for name, val in entries.items():
                target.setdefault(name, copy.deepcopy(val))
    return _resolve_module_key(_internalize(resolved))


def module_specs():
    """All published module contracts: recursive glob under openapi/ minus the
    shared kernel directory and other non-module support files."""
    import glob as _glob
    out = []
    for p in _glob.glob(os.path.join(ROOT, "openapi", "**", "*.yaml"), recursive=True):
        norm = os.path.normpath(p)
        if os.sep + "shared" + os.sep in norm:
            continue
        out.append(norm)
    return sorted(out)
