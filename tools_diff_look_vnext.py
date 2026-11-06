"""Automated op-diff between published opal_look.yaml (1.4.0) and the vNext draft."""
import os, sys, yaml
ROOT = os.path.dirname(os.path.abspath(__file__))
pub = yaml.safe_load(open(os.path.join(ROOT,"openapi","opal_look.yaml"),encoding="utf-8"))
dft = yaml.safe_load(open(os.path.join(ROOT,"openapi","proposals","opal_look.vnext.yaml"),encoding="utf-8"))
def ops(d): return {f"{m.upper()} {p}":(m,p,o) for p in d["paths"] for m,o in d["paths"][p].items() if m in("get","post","put","patch","delete")}
P, D = ops(pub), ops(dft)
out = ["# LOOK v1.4.0 vs vNext — automated op diff\n",
       f"common={len(set(P)&set(D))} removed={len(set(P)-set(D))} added={len(set(D)-set(P))}\n",
       "\n## Removed (1.4.0 -> vNext)\n"]
for op in sorted(set(P)-set(D)): out.append(f"- `{op}`\n")
out.append("\n## Added (vNext)\n")
for op in sorted(set(D)-set(P)): out.append(f"- `{op}`\n")
out.append("\n## Schema-level changes on common ops\n")
for k in sorted(set(P)&set(D)):
    m,p,o = P[k]
    d2 = D[k][2]
    if o.get("operationId") != d2.get("operationId"): out.append(f"- `{k}` operationId `{o.get('operationId')}` -> `{d2.get('operationId')}`\n")
open(os.path.join(ROOT,"docs","migrations","opal-look-vnext-diff.md"),"w",encoding="utf-8").writelines(out)
print("diff written")
