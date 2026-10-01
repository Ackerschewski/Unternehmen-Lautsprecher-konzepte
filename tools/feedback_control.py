#!/usr/bin/env python3
"""Local feedback intake/deduplication. Writes only coordination/feedback and derived state."""
from __future__ import annotations
import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/"coordination/feedback"; STATE=ROOT/"coordination/USER_FEEDBACK_STATE.json"
SOURCES={"USER_TEST","HOST_RUNTIME","PHYSICAL","SUPPORT","MANUAL_QA"}
STATUSES={"NEEDS_TRIAGE","TRIAGED","DEFECT_CREATED","CLOSED"}

def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
def dump(x): return json.dumps(x,indent=2,ensure_ascii=False,sort_keys=True)+"\n"
def load_items():
    out=[]
    DIR.mkdir(parents=True,exist_ok=True)
    for p in sorted(DIR.glob("FB-*.json")):
        out.append(json.loads(p.read_text(encoding="utf-8")))
    return out
def fingerprint(repo,component,symptom,evidence):
    return hashlib.sha256("|".join([repo.lower(),component.lower(),symptom.lower(),evidence.upper()]).encode()).hexdigest()
def state():
    items=load_items()
    return {"schema_version":1,"derived":True,"source_of_truth":"coordination/feedback/*.json",
            "generated_by":"tools/feedback_control.py",
            "counts":{"total":len(items),"needs_triage":sum(i["status"]=="NEEDS_TRIAGE" for i in items),
                      "defect_created":sum(i["status"]=="DEFECT_CREATED" for i in items),
                      "closed":sum(i["status"]=="CLOSED" for i in items)},
            "items":[{"id":i["id"],"status":i["status"],"source":i["source"],"summary":i["summary"],"occurrences":i["occurrences"]} for i in items]}
def snapshot(write):
    s=dump(state())
    if write: STATE.write_text(s,encoding="utf-8"); print("WROTE",STATE.relative_to(ROOT)); return 0
    ok=STATE.is_file() and STATE.read_text(encoding="utf-8")==s
    print("FEEDBACK STATE:","CURRENT" if ok else "STALE"); return 0 if ok else 1
def record(a):
    src=a.source.upper()
    if src not in SOURCES: raise SystemExit("invalid source")
    fp=fingerprint(a.repository,a.component,a.symptom_class,a.evidence_class)
    for item in load_items():
        if item["fingerprint"]==fp:
            item["occurrences"]+=1; item["last_seen_at"]=now()
            item["raw_feedback"].append(a.text)
            p=DIR/f'{item["id"]}.json'; p.write_text(dump(item),encoding="utf-8")
            print(json.dumps({"status":"DEDUPLICATED","id":item["id"]})); return 0
    fid="FB-"+fp[:10].upper()
    item={"schema_version":1,"id":fid,"fingerprint":fp,"status":"NEEDS_TRIAGE","source":src,
          "repository":a.repository,"component":a.component,"symptom_class":a.symptom_class,
          "evidence_class":a.evidence_class.upper(),"summary":a.summary,"raw_feedback":[a.text],
          "evidence_reference":a.evidence or None,"severity":None,"defect_id":None,
          "occurrences":1,"created_at":now(),"last_seen_at":now()}
    (DIR/f"{fid}.json").write_text(dump(item),encoding="utf-8")
    print(json.dumps({"status":"CREATED","id":fid})); return 0
def triage(a):
    p=DIR/f"{a.id}.json"; item=json.loads(p.read_text(encoding="utf-8"))
    if item["status"] not in {"NEEDS_TRIAGE","TRIAGED"}: raise SystemExit("feedback not triageable")
    item["status"]="TRIAGED"; item["severity"]=a.severity.upper()
    item["triage_note"]=a.note; p.write_text(dump(item),encoding="utf-8")
    print(json.dumps({"status":"TRIAGED","id":a.id,"severity":item["severity"]})); return 0
def link(a):
    p=DIR/f"{a.id}.json"; item=json.loads(p.read_text(encoding="utf-8"))
    item["status"]="DEFECT_CREATED"; item["defect_id"]=a.defect_id
    p.write_text(dump(item),encoding="utf-8"); return 0
def main():
    ap=argparse.ArgumentParser(); sp=ap.add_subparsers(dest="cmd",required=True)
    r=sp.add_parser("record")
    for x in ("repository","component","symptom_class","evidence_class","summary","text"): r.add_argument("--"+x.replace("_","-"),dest=x,required=True)
    r.add_argument("--source",required=True); r.add_argument("--evidence")
    t=sp.add_parser("triage"); t.add_argument("--id",required=True); t.add_argument("--severity",required=True); t.add_argument("--note",required=True)
    l=sp.add_parser("link-defect"); l.add_argument("--id",required=True); l.add_argument("--defect-id",required=True)
    s=sp.add_parser("snapshot"); g=s.add_mutually_exclusive_group(required=True); g.add_argument("--write",action="store_true"); g.add_argument("--check",action="store_true")
    a=ap.parse_args()
    if a.cmd=="record": return record(a)
    if a.cmd=="triage": return triage(a)
    if a.cmd=="link-defect": return link(a)
    return snapshot(a.write)
if __name__=="__main__": raise SystemExit(main())
