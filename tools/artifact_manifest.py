#!/usr/bin/env python3
"""Create deterministic SHA-256 artifact manifest. No publishing, network or build execution."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--source-revision",required=True); ap.add_argument("--version",required=True)
    ap.add_argument("--output",required=True); ap.add_argument("artifacts",nargs="+"); a=ap.parse_args()
    items=[]
    for raw in a.artifacts:
        p=Path(raw)
        if not p.is_file(): raise SystemExit(f"missing artifact: {raw}")
        items.append({"path":str(p),"bytes":p.stat().st_size,"sha256":sha(p)})
    data={"schema_version":1,"version":a.version,"source_revision":a.source_revision,"artifacts":items}
    Path(a.output).write_text(json.dumps(data,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(a.output); return 0
if __name__=="__main__": raise SystemExit(main())
