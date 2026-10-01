#!/usr/bin/env python3
"""Runtime evidence registry. Does not launch hosts, shell commands, packages or network."""
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/"coordination/runtime-tests"; STATE=ROOT/"coordination/RUNTIME_EVIDENCE.json"
RESULTS={"PASS","FAIL","NOT_RUN"}; CLASSES={"HOST_RUNTIME","USER_TEST","PHYSICAL"}
def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
def dump(x): return json.dumps(x,indent=2,ensure_ascii=False,sort_keys=True)+"\n"
def files(): return [p for p in sorted(DIR.glob("RT-*.json"))]
def snapshot(write):
    cases=[json.loads(p.read_text(encoding="utf-8")) for p in files()]
    counts={"planned":len(cases),"pass":0,"fail":0,"not_run":0}
    for x in cases: counts[x["result"].lower()]+=1
    s=dump({"schema_version":1,"derived":True,"source_of_truth":"coordination/runtime-tests/*.json",
            "generated_by":"tools/runtime_evidence.py","counts":counts,
            "cases":[{k:x.get(k) for k in ("id","runtime_name","runtime_version","test_case","evidence_class","result","source_revision")} for x in cases]})
    if write: STATE.write_text(s,encoding="utf-8"); print("WROTE",STATE.relative_to(ROOT)); return 0
    ok=STATE.is_file() and STATE.read_text(encoding="utf-8")==s
    print("RUNTIME EVIDENCE:","CURRENT" if ok else "STALE"); return 0 if ok else 1
def create(a):
    DIR.mkdir(parents=True,exist_ok=True); p=DIR/f"{a.id}.json"
    if p.exists(): raise SystemExit("case exists")
    ec=a.evidence_class.upper()
    if ec not in CLASSES: raise SystemExit("invalid evidence class")
    obj={"schema_version":1,"id":a.id,"project":a.project,"source_revision":a.source_revision,
         "runtime_name":a.runtime_name,"runtime_version":a.runtime_version,"test_case":a.test_case,
         "evidence_class":ec,"result":"NOT_RUN","evidence":[],"performed_by":None,"updated_at":now()}
    p.write_text(dump(obj),encoding="utf-8"); return 0
def record(a):
    p=DIR/f"{a.id}.json"; obj=json.loads(p.read_text(encoding="utf-8"))
    res=a.result.upper()
    if res not in RESULTS: raise SystemExit("invalid result")
    if res in {"PASS","FAIL"} and (not a.evidence or not a.performed_by): raise SystemExit("PASS/FAIL require evidence and performed-by")
    obj["result"]=res; obj["performed_by"]=a.performed_by or None
    if a.evidence: obj["evidence"].append(a.evidence)
    obj["updated_at"]=now(); p.write_text(dump(obj),encoding="utf-8"); return 0
def main():
    ap=argparse.ArgumentParser(description=__doc__); sp=ap.add_subparsers(dest="cmd",required=True)
    c=sp.add_parser("create")
    for x in ("id","project","source_revision","runtime_name","runtime_version","test_case","evidence_class"): c.add_argument("--"+x.replace("_","-"),dest=x,required=True)
    r=sp.add_parser("record"); r.add_argument("--id",required=True); r.add_argument("--result",required=True); r.add_argument("--evidence"); r.add_argument("--performed-by")
    s=sp.add_parser("snapshot"); g=s.add_mutually_exclusive_group(required=True); g.add_argument("--write",action="store_true"); g.add_argument("--check",action="store_true")
    a=ap.parse_args()
    return create(a) if a.cmd=="create" else record(a) if a.cmd=="record" else snapshot(a.write)
if __name__=="__main__": raise SystemExit(main())
