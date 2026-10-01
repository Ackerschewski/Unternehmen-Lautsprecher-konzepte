#!/usr/bin/env python3
"""Read-only CI-budget policy check. Stdlib only; does not call GitHub or execute workflows."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REQ=[
 "coordination/CI_POLICY.yaml",
 "coordination/CI_BUDGET_POLICY.yaml",
 "coordination/PROJECT_TEST_MATRIX.yaml",
 "coordination/SECURITY_DEPENDENCY_BASELINE.yaml",
 "coordination/RESET_DAY_PLAN.yaml",
]
FORBIDDEN_MARKERS=(
 "no_auto_enable_after_reset: false",
 "cloud_ci_not_run_is_not_pass: false",
 "no_global_push_ci_enable: false",
)

def main()->int:
    errors=[]
    for rel in REQ:
        p=ROOT/rel
        if not p.is_file(): errors.append(f"missing: {rel}")
    for rel in ("coordination/CI_BUDGET_POLICY.yaml","coordination/RESET_DAY_PLAN.yaml"):
        p=ROOT/rel
        if not p.is_file(): continue
        txt=p.read_text(encoding="utf-8",errors="replace")
        for marker in FORBIDDEN_MARKERS:
            if marker in txt: errors.append(f"unsafe marker in {rel}: {marker}")
    if errors:
        print("CI BUDGET CHECK: FAIL")
        for e in errors: print("-",e)
        return 1
    print("CI BUDGET CHECK: PASS")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
