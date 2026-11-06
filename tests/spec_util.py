"""Load an OPAL OpenAPI spec with $refs fully resolved.

Service specs mount shared Path Items and reference shared components in
openapi/shared/opal_kernel.yaml via external $refs. Tests assert against the
effective (resolved) contract, so this helper inlines external refs and then
dereferences internal '#/components/...' refs as well.
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


def _qualify(node):
    """Rewrite bare '#/...' refs inside a kernel fragment to kernel-qualified
    refs so they resolve against the kernel after inlining."""
    if isinstance(node, dict):
        if "$ref" in node and isinstance(node["$ref"], str) \
                and node["$ref"].startswith("#/"):
            node = dict(node)
            node["$ref"] = "./shared/opal_kernel.yaml" + node["$ref"]
        return {k: _qualify(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_qualify(v) for v in node]
    return node


def _deref(node, local_doc, kernel_doc, depth=0):
    if depth > 25:
        return node
    if isinstance(node, dict):
        if "$ref" in node:
            ref = node["$ref"]
            if ref.startswith("./") or ref.startswith("../"):
                src, frag = kernel_doc, ref.split("#", 1)[1]
            else:
                src, frag = local_doc, ref.lstrip("#")
            target = copy.deepcopy(_pointer(src, frag))
            if src is kernel_doc:
                target = _qualify(target)
            merged = {k: v for k, v in node.items() if k != "$ref"}
            merged.update(target if isinstance(target, dict) else {"value": target})
            return _deref(merged, local_doc, kernel_doc, depth + 1)
        return {k: _deref(v, local_doc, kernel_doc, depth) for k, v in node.items()}
    if isinstance(node, list):
        return [_deref(v, local_doc, kernel_doc, depth) for v in node]
    return node


_METHODS = ("get", "post", "put", "patch", "delete")


def _hoist_cli(spec):
    """Mounted kernel Path Items carry per-op x-opal-cli metadata as a
    path-level {method: value} map sibling of the $ref (extensions cannot
    inject into referenced operations). For the resolved view, copy each
    entry onto the operation it describes."""
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
    """After kernel components are merged into the resolved document,
    rewrite './shared/opal_kernel.yaml#/X' refs to internal '#/X' refs so
    the document is self-contained (and mutates cleanly to a temp file)."""
    if isinstance(node, dict):
        if "$ref" in node and isinstance(node["$ref"], str) \
                and node["$ref"].startswith("./shared/opal_kernel.yaml#/"):
            node = dict(node)
            node["$ref"] = node["$ref"].split("#", 1)[1]
            node["$ref"] = "#" + node["$ref"].lstrip("#")
        return {k: _internalize(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_internalize(v) for v in node]
    return node


def load(path):
    """Return the spec at `path` with all $refs resolved.

    Kernel components are also merged into `components` and all
    kernel-qualified refs are internalized, so the result mirrors the
    bundled (self-contained) document a consumer would see."""
    spec = yaml.safe_load(open(path, encoding="utf-8"))
    kernel = yaml.safe_load(open(KERNEL_PATH, encoding="utf-8"))
    resolved = _hoist_cli(_deref(spec, spec, kernel))
    comps = resolved.setdefault("components", {})
    for kind, entries in (kernel.get("components") or {}).items():
        target = comps.setdefault(kind, {})
        for name, val in entries.items():
            target.setdefault(name, copy.deepcopy(val))
    return _internalize(resolved)
