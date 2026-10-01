#!/usr/bin/env python3
"""Read-only local code/documentation quality gate. Stdlib only; no network or subprocess."""
from __future__ import annotations
import argparse, json, re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE_EXT={".py",".js",".ts",".tsx",".jsx",".cs",".java",".kt",".cpp",".c",".h",".hpp",".rs",".go"}
SKIP={".git","node_modules","vendor","dist","build",".venv","venv","__pycache__"}
REQ=[
 "README.md","docs/developer/ARCHITECTURE.md","docs/developer/CODEBASE_MAP.md",
 "docs/developer/DEVELOPER_ONBOARDING.md","docs/developer/TESTING.md","docs/user/USER_GUIDE.md"
]
PLACEHOLDERS=("TBD","CHANGE_ME","TODO_FILL")

def project_mode():
    p=ROOT/"coordination/PROJECT_STATE.yaml"
    return p.is_file() and "template_mode: false" in p.read_text(encoding="utf-8",errors="replace")

def scan():
    errors=[]; warnings=[]; files=0; over500=[]; over800=[]; over1500=[]
    for rel in REQ:
        if not (ROOT/rel).is_file(): errors.append(f"missing required doc: {rel}")
    if project_mode():
        for rel in REQ:
            p=ROOT/rel
            if p.is_file():
                txt=p.read_text(encoding="utf-8",errors="replace")
                for token in PLACEHOLDERS:
                    if re.search(rf"\b{re.escape(token)}\b",txt):
                        errors.append(f"unresolved placeholder {token}: {rel}")
                        break
    for p in ROOT.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in SOURCE_EXT or any(x in SKIP for x in p.parts):
            continue
        files+=1
        n=sum(1 for _ in p.open("r",encoding="utf-8",errors="replace"))
        rel=str(p.relative_to(ROOT))
        if n>1500: over1500.append(rel); errors.append(f"source >1500 lines: {rel} ({n})")
        elif n>800: over800.append(rel); warnings.append(f"source >800 lines; split/ADR review: {rel} ({n})")
        elif n>500: over500.append(rel); warnings.append(f"source >500 lines; responsibility review: {rel} ({n})")
    return {"result":"FAIL" if errors else "PASS","errors":errors,"warnings":warnings,
            "metrics":{"handwritten_source_files":files,"over_500_lines":len(over500)+len(over800)+len(over1500),
                       "over_800_lines":len(over800)+len(over1500),"over_1500_lines":len(over1500)}}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--json",action="store_true"); a=ap.parse_args()
    r=scan()
    if a.json: print(json.dumps(r,indent=2,ensure_ascii=False))
    else:
        print("QUALITY CONTROL:",r["result"])
        for x in r["errors"]: print("-",x)
        for x in r["warnings"]: print("WARN:",x)
    return 1 if r["errors"] else 0
if __name__=="__main__": raise SystemExit(main())
