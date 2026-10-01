#!/usr/bin/env python3
"""Offline dependency inventory/advisory matcher. Never installs or updates packages."""
from __future__ import annotations
import argparse, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/"coordination/DEPENDENCY_SECURITY_STATE.json"; ADV=ROOT/"coordination/advisories"
MANIFESTS=("requirements.txt","pyproject.toml","package.json","package-lock.json","pnpm-lock.yaml","yarn.lock")
def dump(x): return json.dumps(x,indent=2,ensure_ascii=False,sort_keys=True)+"\n"
def inventory():
    manifests=[]; packages=[]
    for name in MANIFESTS:
        p=ROOT/name
        if not p.is_file(): continue
        manifests.append(name)
        if name=="requirements.txt":
            for line in p.read_text(encoding="utf-8",errors="replace").splitlines():
                line=line.strip()
                if not line or line.startswith("#"): continue
                m=re.match(r"([A-Za-z0-9_.-]+)(?:==|>=|<=|~=|>|<)?(.*)",line)
                if m: packages.append({"name":m.group(1).lower(),"version":m.group(2).strip() or None,"source":name})
        elif name=="package.json":
            j=json.loads(p.read_text(encoding="utf-8"))
            for sec in ("dependencies","devDependencies","peerDependencies"):
                for n,v in (j.get(sec) or {}).items(): packages.append({"name":n.lower(),"version":v,"source":f"{name}:{sec}"})
    return manifests,packages
def advisories():
    out=[]; ADV.mkdir(parents=True,exist_ok=True)
    for p in sorted(ADV.glob("*.json")):
        try: out.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception: out.append({"id":p.name,"invalid":True})
    return out
def build():
    manifests,packages=inventory(); ads=advisories(); findings=[]
    names={p["name"] for p in packages}
    for a in ads:
        if a.get("invalid"): findings.append({"id":a["id"],"status":"INVALID_ADVISORY"}); continue
        pkg=str(a.get("package","")).lower()
        if pkg and pkg in names:
            findings.append({"id":a.get("id"),"package":pkg,"severity":str(a.get("severity","UNKNOWN")).upper(),
                             "source":a.get("source"),"status":"REVIEW_REQUIRED"})
    high=sum(f.get("severity") in {"HIGH","CRITICAL"} for f in findings)
    return {"schema_version":1,"derived":True,"generated_by":"tools/dependency_watch.py",
            "inventory":{"manifests":manifests,"packages":packages},"findings":findings,
            "counts":{"packages":len(packages),"findings":len(findings),"high_or_critical":high}}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("mode",choices=["check","snapshot"]); ap.add_argument("--write",action="store_true"); a=ap.parse_args()
    s=dump(build())
    if a.mode=="snapshot" and a.write: STATE.write_text(s,encoding="utf-8"); print("WROTE",STATE.relative_to(ROOT)); return 0
    if a.mode=="snapshot":
        ok=STATE.is_file() and STATE.read_text(encoding="utf-8")==s; print("DEPENDENCY STATE:","CURRENT" if ok else "STALE"); return 0 if ok else 1
    d=json.loads(s); print(json.dumps(d,indent=2)); return 2 if d["counts"]["high_or_critical"] else 0
if __name__=="__main__": raise SystemExit(main())
