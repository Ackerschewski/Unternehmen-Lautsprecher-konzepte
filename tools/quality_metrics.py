#!/usr/bin/env python3
"""Derive local quality metrics for engineering review/Company OS. No authority over gates."""
from __future__ import annotations
import argparse, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/"coordination/QUALITY_METRICS.json"
SRC_EXT={".py",".js",".ts",".tsx",".jsx",".cs",".java",".kt",".cpp",".c",".h",".hpp",".rs",".go"}
SKIP={".git","node_modules","vendor","dist","build",".venv","venv","__pycache__"}
REQ=["README.md","docs/developer/ARCHITECTURE.md","docs/developer/CODEBASE_MAP.md","docs/developer/DEVELOPER_ONBOARDING.md","docs/developer/TESTING.md","docs/user/USER_GUIDE.md"]
def load(rel,default):
    p=ROOT/rel
    try:return json.loads(p.read_text(encoding="utf-8"))
    except Exception:return default
def build():
    files=over500=over800=tests=0
    for p in ROOT.rglob("*"):
        if not p.is_file() or any(x in SKIP for x in p.parts): continue
        if p.suffix.lower() in SRC_EXT:
            files+=1; n=sum(1 for _ in p.open("r",encoding="utf-8",errors="replace"))
            over500+=n>500; over800+=n>800
        if "test" in p.name.lower() and p.suffix.lower() in SRC_EXT: tests+=1
    defects=load("coordination/DEFECT_STATE.json",{}).get("counts",{})
    ev=load("coordination/RELEASE_EVIDENCE.json",{}).get("gates",{})
    c={"pass":0,"fail":0,"not_run":0,"not_required":0}
    for v in ev.values():
        k=str(v).lower()
        if k in c:c[k]+=1
    blocking=bool(c["fail"])
    docs=sum((ROOT/x).is_file() for x in REQ)
    # Conservative index: descriptive only, never gate authority.
    denom=max(1,sum(c.values())); gate_ratio=(c["pass"]+c["not_required"])/denom
    index=round(100*(0.45*gate_ratio+0.2*(docs/len(REQ))+0.2*(1-min(1,(over800/max(1,files))))+0.15*(1 if not defects.get("release_blocking",0) else 0)))
    return {"schema_version":1,"derived":True,"generated_by":"tools/quality_metrics.py",
            "derived_quality_index":index,"blocking_gate_failure":blocking,
            "structure":{"handwritten_source_files":files,"over_500_lines":over500,"over_800_lines":over800},
            "tests":{"discovered_test_files":tests},
            "defects":{"active":defects.get("active",0),"release_blocking":defects.get("release_blocking",0),"escalated":defects.get("escalated",0)},
            "documentation":{"required_docs_present":docs,"required_docs_total":len(REQ)},
            "gates":c}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--write",action="store_true"); ap.add_argument("--check",action="store_true"); a=ap.parse_args()
    s=json.dumps(build(),indent=2,ensure_ascii=False,sort_keys=True)+"\n"
    if a.write: OUT.write_text(s,encoding="utf-8"); print("WROTE",OUT.relative_to(ROOT)); return 0
    if a.check:
        ok=OUT.is_file() and OUT.read_text(encoding="utf-8")==s; print("QUALITY METRICS:","CURRENT" if ok else "STALE"); return 0 if ok else 1
    print(s); return 0
if __name__=="__main__": raise SystemExit(main())
