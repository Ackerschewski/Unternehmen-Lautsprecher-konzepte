#!/usr/bin/env python3
"""Derive build/release readiness without publishing anything."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "coordination" / "RELEASE_EVIDENCE.json"
STATE = ROOT / "coordination" / "RELEASE_STATE.json"
DEFECT_STATE = ROOT / "coordination" / "DEFECT_STATE.json"
AUTOMATION_STATE = ROOT / "coordination" / "AUTOMATION_STATE.json"
VERSION = ROOT / "VERSION"
LEDGER = ROOT / "coordination" / "VERSION_LEDGER.yaml"

VERSION_RE = re.compile(r"^V-(\d{2})\.(\d{2})\.(\d{2})(?:-RC\d+)?$")
PASS_VALUES = {"PASS", "NOT_REQUIRED"}


class ReleaseError(Exception):
    pass


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReleaseError(f"Missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise ReleaseError(f"Invalid JSON {path.relative_to(ROOT)}: {exc}") from exc


def version_consistent() -> tuple[bool, str]:
    version = VERSION.read_text(encoding="utf-8").strip()
    if not VERSION_RE.fullmatch(version):
        return False, f"invalid VERSION: {version}"
    ledger = LEDGER.read_text(encoding="utf-8")
    major, feature, fix = map(int, VERSION_RE.fullmatch(version).groups())
    expected = (
        f"major: {major}", f"features_since_major: {feature}",
        f"fixes_since_feature: {fix}"
    )
    missing = [marker for marker in expected if marker not in ledger]
    return (not missing, "ledger mismatch: " + ", ".join(missing) if missing else "")


def build_state() -> dict:
    evidence = load_json(EVIDENCE)
    defects = load_json(DEFECT_STATE)
    automation = load_json(AUTOMATION_STATE)
    ok_version, version_problem = version_consistent()

    gates = evidence.get("gates", {})
    incomplete = sorted(
        gate for gate, status in gates.items()
        if str(status).upper() not in PASS_VALUES
    )
    release_blocking = list(defects.get("release_blocking", []))
    automation_fail = automation.get("health") == "FAIL"

    development_blockers = []
    if automation_fail:
        development_blockers.append("automation_state_fail")

    user_test_blockers = list(development_blockers)
    user_test_required = evidence.get(
        "user_test_required_gates",
        ["repository_structure", "automation_control", "defect_control", "unit"],
    )
    user_test_incomplete = sorted(
        gate for gate in user_test_required
        if str(gates.get(gate, "NOT_RUN")).upper() not in PASS_VALUES
    )
    if user_test_incomplete:
        user_test_blockers.append("incomplete_user_test_gates")
    user_test_blockers += [
        item for item in release_blocking
        if item in evidence.get("user_test_blocking_defects", [])
    ]

    rc_blockers = list(development_blockers)
    if release_blocking:
        rc_blockers.append("release_blocking_defects")
    if incomplete:
        rc_blockers.append("incomplete_required_gates")
    if not ok_version:
        rc_blockers.append("version_ledger_mismatch")
    for key in ("documentation_current", "known_limitations_current", "changelog_current"):
        if not evidence.get(key, False):
            rc_blockers.append(key)

    final_blockers = list(rc_blockers)
    if not evidence.get("project_owner_approval", False):
        final_blockers.append("project_owner_approval_required")

    version = VERSION.read_text(encoding="utf-8").strip()
    return {
        "schema_version": 1,
        "derived": True,
        "source_of_truth": [
            "VERSION",
            "coordination/VERSION_LEDGER.yaml",
            "coordination/RELEASE_EVIDENCE.json",
            "coordination/DEFECT_STATE.json",
            "coordination/AUTOMATION_STATE.json",
        ],
        "generated_by": "tools/release_control.py",
        "version": version,
        "version_consistent": ok_version,
        "version_problem": version_problem or None,
        "release_blocking_defects": release_blocking,
        "incomplete_gates": incomplete,
        "incomplete_user_test_gates": user_test_incomplete,
        "channels": {
            "development": {
                "ready": not development_blockers,
                "blockers": development_blockers,
            },
            "user_test": {
                "ready": not user_test_blockers,
                "blockers": user_test_blockers,
            },
            "release_candidate": {
                "ready": not rc_blockers,
                "blockers": rc_blockers,
            },
            "final": {
                "ready": not final_blockers,
                "blockers": final_blockers,
                "explicit_owner_approval_required": True,
            },
        },
        "automatic_final_publish": False,
    }


def text(data) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def snapshot(write: bool) -> int:
    state = build_state()
    expected = text(state)
    if write:
        STATE.write_text(expected, encoding="utf-8")
        print(f"WROTE {STATE.relative_to(ROOT)}")
        return 0
    if not STATE.is_file() or STATE.read_text(encoding="utf-8") != expected:
        print("RELEASE STATE: STALE")
        return 1
    print("RELEASE STATE: CURRENT")
    return 0


def command_check() -> int:
    state = build_state()
    print("RELEASE CONTROL: PASS")
    for channel, value in state["channels"].items():
        print(f"- {channel}: {'READY' if value['ready'] else 'BLOCKED'}")
    return 0


def command_channel(channel: str) -> int:
    state = build_state()
    value = state["channels"][channel]
    print(json.dumps({"channel": channel, **value}, indent=2))
    return 0 if value["ready"] else 3


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check")
    snap = sub.add_parser("snapshot")
    mode = snap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    channel = sub.add_parser("channel")
    channel.add_argument(
        "--name", required=True,
        choices=("development", "user_test", "release_candidate", "final")
    )
    args = parser.parse_args()
    try:
        if args.command == "check":
            return command_check()
        if args.command == "snapshot":
            return snapshot(write=args.write)
        if args.command == "channel":
            return command_channel(args.name)
    except ReleaseError as exc:
        print(f"RELEASE CONTROL: FAIL\n- {exc}")
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
