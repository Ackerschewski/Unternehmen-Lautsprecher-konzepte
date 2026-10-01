#!/usr/bin/env python3
"""Canonical defect lifecycle and bounded repair control.

The tool is local-only: no network, GitHub API, subprocess or package install.
It may write only canonical defect JSON files and the derived defect snapshot.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DEFECT_DIR = ROOT / "coordination" / "defects"
STATE_PATH = ROOT / "coordination" / "DEFECT_STATE.json"
TASK_DIR = ROOT / "coordination" / "tasks"

SEVERITIES = ("BLOCKER", "CRITICAL", "HIGH", "MEDIUM", "LOW")
SEVERITY_RANK = {value: index for index, value in enumerate(SEVERITIES)}
STATUSES = {
    "OPEN", "CLAIMED", "IN_PROGRESS", "RETEST_REQUIRED",
    "VERIFIED", "ESCALATED", "CLOSED", "WONT_FIX",
}
ACTIVE = {"OPEN", "CLAIMED", "IN_PROGRESS", "RETEST_REQUIRED", "ESCALATED"}
RELEASE_BLOCKING = {"BLOCKER", "CRITICAL", "HIGH"}
URGENT = {"BLOCKER", "CRITICAL"}
AGENTS = {f"agent_{i}" for i in range(1, 6)}
MAX_FIX_ATTEMPTS = 2

ALLOWED = {
    "OPEN": {"CLAIMED", "IN_PROGRESS", "WONT_FIX"},
    "CLAIMED": {"IN_PROGRESS", "OPEN"},
    "IN_PROGRESS": {"RETEST_REQUIRED", "ESCALATED", "OPEN"},
    "RETEST_REQUIRED": {"VERIFIED", "OPEN", "ESCALATED"},
    "VERIFIED": {"CLOSED", "OPEN"},
    "ESCALATED": {"IN_PROGRESS", "WONT_FIX"},
    "CLOSED": {"OPEN"},
    "WONT_FIX": {"OPEN"},
}

GATE_OWNER = {
    "architecture": "agent_1",
    "domain": "agent_2",
    "unit": "agent_2",
    "ui": "agent_3",
    "ux": "agent_3",
    "host_runtime": "agent_4",
    "integration": "agent_4",
    "packaging": "agent_4",
    "security": "agent_5",
    "qa": "agent_5",
    "release": "agent_5",
}

EVIDENCE_RANK = {"STATIC": 0, "UNIT": 1, "INTEGRATION": 2}
SPECIAL_EVIDENCE = {"HOST_RUNTIME", "USER_TEST", "PHYSICAL"}


class DefectError(Exception):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def json_text(value) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def normalize(value: str | None) -> str:
    return (value or "").strip()


def fingerprint(repository: str, task_id: str, gate: str, check: str) -> str:
    payload = "|".join([
        repository.strip().lower(),
        task_id.strip().upper() or "NONE",
        gate.strip().lower(),
        check.strip().lower(),
    ])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def defect_path(defect_id: str) -> Path:
    return DEFECT_DIR / f"{defect_id}.json"


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DefectError(f"Missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise DefectError(f"Invalid JSON {path.relative_to(ROOT)}: {exc}") from exc


def task_owner(task_id: str) -> str | None:
    if not task_id:
        return None
    path = TASK_DIR / f"{task_id}.md"
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    match = re.search(r"^## Owner\s*\n([^\n]*)", text, re.M)
    if not match:
        return None
    token = match.group(1).strip().lower().replace("-", "_").replace(" ", "_")
    return token if token in AGENTS else None


def resolve_owner(task_id: str, gate: str, explicit: str | None) -> str:
    if explicit:
        token = explicit.strip().lower().replace("-", "_").replace(" ", "_")
        if token not in AGENTS:
            raise DefectError("owner must be agent_1..agent_5")
        return token
    owner = task_owner(task_id)
    if owner:
        return owner
    return GATE_OWNER.get(gate.strip().lower(), "agent_5")


def reviewer_for(owner: str) -> str:
    return "agent_1" if owner == "agent_5" else "agent_5"


def validate_defect(data: dict, path: Path | None = None) -> list[str]:
    errors: list[str] = []
    label = path.name if path else str(data.get("id", "defect"))
    required = (
        "id", "fingerprint", "title", "severity", "status", "owner_agent",
        "review_agent", "source", "occurrences", "fix_attempts",
        "max_fix_attempts", "retest", "automation",
    )
    for key in required:
        if key not in data:
            errors.append(f"{label}: missing {key}")
    if data.get("severity") not in SEVERITIES:
        errors.append(f"{label}: invalid severity")
    if data.get("status") not in STATUSES:
        errors.append(f"{label}: invalid status")
    if data.get("owner_agent") not in AGENTS:
        errors.append(f"{label}: invalid owner_agent")
    if data.get("review_agent") not in AGENTS:
        errors.append(f"{label}: invalid review_agent")
    if not isinstance(data.get("occurrences"), int) or data.get("occurrences", 0) < 1:
        errors.append(f"{label}: occurrences must be >= 1")
    if not isinstance(data.get("fix_attempts"), int) or data.get("fix_attempts", -1) < 0:
        errors.append(f"{label}: fix_attempts must be >= 0")
    if data.get("max_fix_attempts") != MAX_FIX_ATTEMPTS:
        errors.append(f"{label}: max_fix_attempts must be {MAX_FIX_ATTEMPTS}")
    source = data.get("source", {})
    for key in ("repository", "task_id", "gate", "check", "evidence_class"):
        if key not in source:
            errors.append(f"{label}: source missing {key}")
    return errors


def load_defects() -> list[dict]:
    DEFECT_DIR.mkdir(parents=True, exist_ok=True)
    result = []
    fingerprints: set[str] = set()
    for path in sorted(DEFECT_DIR.glob("*.json")):
        if path.name == "DEFECT_TEMPLATE.json":
            continue
        data = load_json(path)
        errors = validate_defect(data, path)
        if errors:
            raise DefectError("; ".join(errors))
        fp = data["fingerprint"]
        if fp in fingerprints:
            raise DefectError(f"Duplicate defect fingerprint: {fp}")
        fingerprints.add(fp)
        result.append(data)
    return result


def build_state() -> dict:
    defects = load_defects()
    active = [d for d in defects if d["status"] in ACTIVE]
    active.sort(key=lambda d: (SEVERITY_RANK[d["severity"]], d["id"]))
    by_agent = {agent: [] for agent in sorted(AGENTS)}
    for defect in active:
        by_agent[defect["owner_agent"]].append({
            "id": defect["id"],
            "severity": defect["severity"],
            "status": defect["status"],
            "title": defect["title"],
            "fix_attempts": defect["fix_attempts"],
            "max_fix_attempts": defect["max_fix_attempts"],
            "urgent": defect["severity"] in URGENT,
        })
    release_blocking = [
        d["id"] for d in active if d["severity"] in RELEASE_BLOCKING
    ]
    return {
        "schema_version": 1,
        "derived": True,
        "source_of_truth": "coordination/defects/*.json",
        "generated_by": "tools/defect_control.py",
        "counts": {
            "total": len(defects),
            "active": len(active),
            "release_blocking": len(release_blocking),
            "escalated": sum(d["status"] == "ESCALATED" for d in defects),
        },
        "release_blocking": release_blocking,
        "by_agent": by_agent,
    }


def snapshot(write: bool) -> int:
    state = build_state()
    expected = json_text(state)
    if write:
        STATE_PATH.write_text(expected, encoding="utf-8")
        print(f"WROTE {STATE_PATH.relative_to(ROOT)}")
        return 0
    if not STATE_PATH.is_file() or STATE_PATH.read_text(encoding="utf-8") != expected:
        print("DEFECT SNAPSHOT: STALE")
        return 1
    print("DEFECT SNAPSHOT: CURRENT")
    return 0


def record_failure(args) -> int:
    severity = args.severity.upper()
    if severity not in SEVERITIES:
        raise DefectError(f"severity must be one of {', '.join(SEVERITIES)}")
    evidence_class = args.evidence_class.upper()
    if evidence_class not in set(EVIDENCE_RANK) | SPECIAL_EVIDENCE:
        raise DefectError("invalid evidence class")

    repository = args.repository or ROOT.name
    task_id = normalize(args.task)
    fp = fingerprint(repository, task_id, args.gate, args.check)
    existing = next((d for d in load_defects() if d["fingerprint"] == fp), None)
    stamp = now_iso()

    if existing:
        existing["occurrences"] += 1
        existing["last_seen_at"] = stamp
        if args.evidence and args.evidence not in existing["failure_evidence"]:
            existing["failure_evidence"].append(args.evidence)
        if existing["status"] in {"VERIFIED", "CLOSED"}:
            existing["status"] = "OPEN"
            existing["retest"] = {"status": "NOT_RUN", "evidence": []}
            existing["integration"] = {"pr": None, "merge_ref": None}
        path = defect_path(existing["id"])
        path.write_text(json_text(existing), encoding="utf-8")
        print(json.dumps({"status": "DEDUPLICATED", "defect_id": existing["id"]}))
        return 0

    owner = resolve_owner(task_id, args.gate, args.owner)
    defect_id = f"BUG-AUTO-{fp[:10].upper()}"
    data = {
        "schema_version": 1,
        "id": defect_id,
        "fingerprint": fp,
        "title": args.summary.strip(),
        "severity": severity,
        "status": "OPEN",
        "owner_agent": owner,
        "review_agent": reviewer_for(owner),
        "source": {
            "repository": repository,
            "task_id": task_id or None,
            "gate": args.gate.strip(),
            "check": args.check.strip(),
            "evidence_class": evidence_class,
        },
        "failure_evidence": [args.evidence] if args.evidence else [],
        "occurrences": 1,
        "fix_attempts": 0,
        "max_fix_attempts": MAX_FIX_ATTEMPTS,
        "regression_test": None,
        "retest": {"status": "NOT_RUN", "evidence": []},
        "integration": {"pr": None, "merge_ref": None},
        "automation": {
            "auto_created": True,
            "actionable": True,
            "escalation_required": False,
        },
        "created_at": stamp,
        "last_seen_at": stamp,
    }
    DEFECT_DIR.mkdir(parents=True, exist_ok=True)
    defect_path(defect_id).write_text(json_text(data), encoding="utf-8")
    print(json.dumps({"status": "CREATED", "defect_id": defect_id, "owner": owner}))
    return 0


def get_defect(defect_id: str) -> tuple[Path, dict]:
    path = defect_path(defect_id)
    data = load_json(path)
    errors = validate_defect(data, path)
    if errors:
        raise DefectError("; ".join(errors))
    return path, data


def evidence_matches(required: str, supplied: str) -> bool:
    required = required.upper()
    supplied = supplied.upper()
    if required in SPECIAL_EVIDENCE:
        return supplied == required
    if supplied in SPECIAL_EVIDENCE:
        return True
    return EVIDENCE_RANK.get(supplied, -1) >= EVIDENCE_RANK.get(required, 999)


def command_start(defect_id: str) -> int:
    path, data = get_defect(defect_id)
    if data["status"] not in {"OPEN", "CLAIMED", "ESCALATED"}:
        raise DefectError(f"cannot start from {data['status']}")
    data["status"] = "IN_PROGRESS"
    path.write_text(json_text(data), encoding="utf-8")
    return 0


def command_fix_ready(args) -> int:
    path, data = get_defect(args.id)
    if data["status"] != "IN_PROGRESS":
        raise DefectError("fix-ready requires IN_PROGRESS")
    if data["fix_attempts"] >= data["max_fix_attempts"]:
        data["status"] = "ESCALATED"
        data["automation"]["actionable"] = False
        data["automation"]["escalation_required"] = True
        path.write_text(json_text(data), encoding="utf-8")
        print("DEFECT ESCALATED: automatic fix limit reached")
        return 2
    if not args.regression_test:
        raise DefectError("fix-ready requires --regression-test")
    if not args.pr:
        raise DefectError("fix-ready requires --pr")
    data["fix_attempts"] += 1
    data["regression_test"] = args.regression_test
    data["integration"]["pr"] = args.pr
    data["status"] = "RETEST_REQUIRED"
    data["retest"] = {"status": "NOT_RUN", "evidence": []}
    path.write_text(json_text(data), encoding="utf-8")
    return 0


def command_retest(args) -> int:
    path, data = get_defect(args.id)
    if data["status"] != "RETEST_REQUIRED":
        raise DefectError("retest requires RETEST_REQUIRED")
    if not args.evidence:
        raise DefectError("retest requires --evidence")
    supplied = args.evidence_class.upper()
    required = data["source"]["evidence_class"].upper()
    if args.result == "PASS":
        if not evidence_matches(required, supplied):
            raise DefectError(
                f"{supplied} evidence cannot verify original {required} failure"
            )
        data["retest"] = {
            "status": "PASS",
            "evidence_class": supplied,
            "evidence": [args.evidence],
        }
        data["status"] = "VERIFIED"
    else:
        data["retest"] = {
            "status": "FAIL",
            "evidence_class": supplied,
            "evidence": [args.evidence],
        }
        if data["fix_attempts"] >= data["max_fix_attempts"]:
            data["status"] = "ESCALATED"
            data["automation"]["actionable"] = False
            data["automation"]["escalation_required"] = True
        else:
            data["status"] = "OPEN"
    path.write_text(json_text(data), encoding="utf-8")
    return 0


def command_close(args) -> int:
    path, data = get_defect(args.id)
    if data["status"] != "VERIFIED":
        raise DefectError("close requires VERIFIED")
    if not args.integration_ref:
        raise DefectError("close requires --integration-ref")
    data["integration"]["merge_ref"] = args.integration_ref
    data["status"] = "CLOSED"
    data["automation"]["actionable"] = False
    path.write_text(json_text(data), encoding="utf-8")
    return 0


def command_next(agent: str) -> int:
    if agent not in AGENTS:
        raise DefectError("agent must be agent_1..agent_5")
    items = build_state()["by_agent"][agent]
    print(json.dumps({
        "agent": agent,
        "status": "DEFECT_AVAILABLE" if items else "NO_DEFECT",
        "defect": items[0] if items else None,
    }, indent=2))
    return 0


def command_check() -> int:
    try:
        state = build_state()
    except DefectError as exc:
        print(f"DEFECT CONTROL: FAIL\n- {exc}")
        return 1
    print(
        "DEFECT CONTROL: PASS "
        f"({state['counts']['active']} active, "
        f"{state['counts']['release_blocking']} release-blocking)"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check")

    snap = sub.add_parser("snapshot")
    mode = snap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")

    record = sub.add_parser("record-failure")
    record.add_argument("--repository")
    record.add_argument("--task", default="")
    record.add_argument("--gate", required=True)
    record.add_argument("--check", required=True)
    record.add_argument("--summary", required=True)
    record.add_argument("--severity", required=True)
    record.add_argument("--evidence", default="")
    record.add_argument("--evidence-class", default="STATIC")
    record.add_argument("--owner")

    start = sub.add_parser("start")
    start.add_argument("--id", required=True)

    fix = sub.add_parser("fix-ready")
    fix.add_argument("--id", required=True)
    fix.add_argument("--regression-test", required=True)
    fix.add_argument("--pr", required=True)

    retest = sub.add_parser("retest")
    retest.add_argument("--id", required=True)
    retest.add_argument("--result", required=True, choices=("PASS", "FAIL"))
    retest.add_argument("--evidence", required=True)
    retest.add_argument("--evidence-class", default="STATIC")

    close = sub.add_parser("close")
    close.add_argument("--id", required=True)
    close.add_argument("--integration-ref", required=True)

    nxt = sub.add_parser("next")
    nxt.add_argument("--agent", required=True)

    args = parser.parse_args()
    try:
        if args.command == "check":
            return command_check()
        if args.command == "snapshot":
            return snapshot(write=args.write)
        if args.command == "record-failure":
            return record_failure(args)
        if args.command == "start":
            return command_start(args.id)
        if args.command == "fix-ready":
            return command_fix_ready(args)
        if args.command == "retest":
            return command_retest(args)
        if args.command == "close":
            return command_close(args)
        if args.command == "next":
            return command_next(args.agent)
    except DefectError as exc:
        print(f"DEFECT CONTROL: FAIL\n- {exc}")
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
