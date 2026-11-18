"""Bundle every published module spec into dist/.

Discovers specs recursively under openapi/ (top-level services plus nested
module contracts such as openapi/engines/), excluding the shared kernel and
any other non-published contract base. Mirrors `npm run bundle`.
"""
import glob
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def module_specs():
    return sorted(
        p for p in glob.glob(os.path.join(ROOT, "openapi", "**", "*.yaml"), recursive=True)
        if os.sep + "shared" + os.sep not in os.path.normpath(p))


def main():
    os.makedirs(os.path.join(ROOT, "dist"), exist_ok=True)
    specs = module_specs()
    if not specs:
        print("no module specs discovered", file=sys.stderr)
        return 1
    failed = 0
    for spec in specs:
        out = os.path.join(ROOT, "dist", os.path.basename(spec))
        rel = os.path.relpath(spec, ROOT)
        npx = shutil.which("npx") or "npx"
        r = subprocess.run(
            [npx, "redocly", "bundle", rel, "-o", os.path.relpath(out, ROOT)],
            cwd=ROOT, shell=(os.name == "nt"))
        if r.returncode != 0:
            failed = 1
    return failed


if __name__ == "__main__":
    sys.exit(main())
