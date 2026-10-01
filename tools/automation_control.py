#!/usr/bin/env python3
"""Deterministic local automation control for projects created from Project-Template.

No network access. No GitHub writes. Canonical task files are never mutated.
The tool validates task metadata, derives queue/state snapshots and recommends
the next runnable task for one of the five shared agents.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TASK_FILE_RE = re.compile(r"^(?P<id>(?:TASK|BUG|TECHDEBT|REG)-\d{4,})\.md$")
SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.M)
ID_RE = re.compile(r"\b(?:TASK|BUG|TECHDEBT|REG)-\d{4,}\b")

TASK_STATUSES = {
    "PLANNED", "READY", "CLAIMED", "IN_PROGRESS", "BLOCKED",
    "REVIEW_READY", "IN_REVIEW", "USER_TEST_REQUIRED", "USER_TEST_FAILED",
    "USER_TEST_PASSED", "DONE", "DEPRECATED",
}
TASK_TYPES = {"FEATURE", "FIX", "REFACTOR", "DOCS", "TEST", "INFRA"}
PRIORITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
PRIORITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
AGENTS = {f"agent_{i}" for i in range(1, 6)}
ACTIVE_STATUSES = {
    "CLAIMED", "IN_PROGRESS", "REVIEW_READY", "IN_REVIEW",
    "USER_TEST_REQUIRED",
}
DEPENDENCY_SATISFIED = {"DONE", "USER_TEST_PASSED", "DEPRECATED"}

UI_HINTS = ("ui", "ux", "panel", "dialog", "screen", "layout", "view", "widget")
INTEGRATION_HINTS = (
    "integration", "adapter", "host", "api", "import", "export",
    "packaging", "installer", "platform",
)
ARCHITECTURE_HINTS = (
    "architecture", "contract", "interface", "schema", "dependency",
    "refactor", "module boundary",
)


class ValidationError(Exception):
    pass


def split_sections(text):
    matches = list(SECTION_RE.finditer(text))
    sections = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group(1).strip()] = text[start:end].strip()
    return sections


def first_value(sections, name):
    for line in sections.get(name, "").splitlines():
        if line.strip():
            return line.strip()
    return ""


def parse_ids(value):
    return sorted(set(ID_RE.findall(value)))


def normalize_owner(value):
    token = value.strip().lower().replace("-", "_").replace(" ", "_")
    return token if token in AGENTS else None


def contains_hint(text, hints):
    return any(
        re.search(rf"(?<![a-z0-9]){re.escape(hint)}(?![a-z0-9])", text)
        is not None
        for hint in hints
    )


def parse_task(path, root):
    match = TASK_FILE_RE.fullmatch(path.name)
    if not match:
        raise ValidationError(f"Invalid task filename: {path.name}")

    task_id = match.group("id")
    text = path.read_text(encoding="utf-8")
    sections = split_sections(text)

    status = first_value(sections, "Status").upper()
    task_type = first_value(sections, "Type").upper()
    priority = first_value(sections, "Priority").upper()
    raw_owner = first_value(sections, "Owner")
    owner = normalize_owner(raw_owner)

    errors = []
    if status not in TASK_STATUSES:
        errors.append(f"{task_id}: invalid Status {status!r}")
    if task_type not in TASK_TYPES:
        errors.append(f"{task_id}: invalid Type {task_type!r}")
    if priority not in PRIORITIES:
        errors.append(f"{task_id}: invalid Priority {priority!r}")
    if raw_owner.strip() and owner is None:
        errors.append(f"{task_id}: Owner must be agent_1..agent_5 or empty")
    if errors:
        raise ValidationError("; ".join(errors))

    title_match = re.search(
        r"^#\s+(?:TASK|BUG|TECHDEBT|REG)-\d{4,}\s+[–-]\s*(.+?)\s*$",
        text,
        re.M,
    )
    title = title_match.group(1).strip() if title_match else task_id
    affected_modules = [
        line.lstrip("-* ").strip()
        for line in sections.get("Affected Modules", "").splitlines()
        if line.strip()
    ]
    search_text = " ".join(
        [
            title,
            sections.get("Goal", ""),
            sections.get("Affected Modules", ""),
            sections.get("Required Interfaces", ""),
        ]
    ).lower()

    return {
        "task_id": task_id,
        "title": title,
        "type": task_type,
        "status": status,
        "priority": priority,
        "owner": owner,
        "depends_on": parse_ids(sections.get("Depends On", "")),
        "affected_modules": affected_modules,
        "search_text": search_text,
        "path": path.relative_to(root).as_posix(),
    }


def recommend_agent(task):
    if task["owner"] in AGENTS:
        return task["owner"]
    if contains_hint(task["search_text"], UI_HINTS):
        return "agent_3"
    if contains_hint(task["search_text"], INTEGRATION_HINTS):
        return "agent_4"
    if task["type"] == "REFACTOR" or contains_hint(
        task["search_text"], ARCHITECTURE_HINTS
    ):
        return "agent_1"
    if task["type"] in {"TEST", "DOCS"}:
        return "agent_5"
    if task["type"] == "INFRA":
        return "agent_4"
    return "agent_2"


def review_partner(primary):
    return "agent_1" if primary == "agent_5" else "agent_5"


def load_tasks(root):
    task_dir = root / "coordination" / "tasks"
    if not task_dir.is_dir():
        raise ValidationError("Missing directory: coordination/tasks")

    tasks = []
    for path in sorted(task_dir.glob("*.md")):
        if path.name == "TASK_TEMPLATE.md":
            continue
        tasks.append(parse_task(path, root))

    ids = [task["task_id"] for task in tasks]
    if len(ids) != len(set(ids)):
        raise ValidationError("Duplicate task IDs found")
    return tasks


def validate_dependencies(tasks):
    by_id = {task["task_id"]: task for task in tasks}
    errors = []
    for task in tasks:
        for dep in task["depends_on"]:
            if dep == task["task_id"]:
                errors.append(f"{task['task_id']}: task cannot depend on itself")
            elif dep not in by_id:
                errors.append(f"{task['task_id']}: unknown dependency {dep}")
    if errors:
        raise ValidationError("; ".join(errors))
    return by_id


def dependency_state(task, by_id):
    waiting = [
        dep
        for dep in task["depends_on"]
        if dep not in by_id or by_id[dep]["status"] not in DEPENDENCY_SATISFIED
    ]
    return not waiting, waiting


def build_snapshot(root):
    tasks = load_tasks(root)
    by_id = validate_dependencies(tasks)

    public = []
    for task in tasks:
        dependencies_ready, waiting_on = dependency_state(task, by_id)
        primary = recommend_agent(task)
        public.append(
            {
                "task_id": task["task_id"],
                "title": task["title"],
                "type": task["type"],
                "status": task["status"],
                "priority": task["priority"],
                "owner": task["owner"],
                "recommended_agent": primary,
                "review_partner": review_partner(primary),
                "depends_on": task["depends_on"],
                "dependencies_ready": dependencies_ready,
                "waiting_on": waiting_on,
                "affected_modules": task["affected_modules"],
                "source": task["path"],
            }
        )

    public.sort(key=lambda item: (PRIORITY_ORDER[item["priority"]], item["task_id"]))
    runnable = [
        item
        for item in public
        if item["status"] == "READY" and item["dependencies_ready"]
    ]
    blocked_by_dependency = [
        item["task_id"]
        for item in public
        if item["status"] == "READY" and not item["dependencies_ready"]
    ]

    active_by_agent = {agent: [] for agent in sorted(AGENTS)}
    for item in public:
        if item["status"] in ACTIVE_STATUSES:
            agent = item["owner"] or item["recommended_agent"]
            active_by_agent[agent].append(item["task_id"])

    queue = {
        "schema_version": 1,
        "derived": True,
        "source_of_truth": "coordination/tasks/*.md",
        "generated_by": "tools/automation_control.py",
        "items": runnable,
    }
    try:
        try:
            from defect_control import build_state as build_defect_state
        except ImportError:
            from tools.defect_control import build_state as build_defect_state
        defect_state = build_defect_state()
    except Exception:
        defect_state = {
            "counts": {"active": 0, "release_blocking": 0, "escalated": 0, "total": 0},
            "by_agent": {agent: [] for agent in sorted(AGENTS)},
            "release_blocking": [],
        }

    state = {
        "schema_version": 1,
        "derived": True,
        "source_of_truth": "repository",
        "generated_by": "tools/automation_control.py",
        "health": "READY" if not blocked_by_dependency else "ATTENTION",
        "task_counts": {
            "total": len(public),
            "runnable": len(runnable),
            "blocked_by_dependency": len(blocked_by_dependency),
        },
        "blocked_by_dependency": blocked_by_dependency,
        "active_by_agent": active_by_agent,
        "wip_limit_default": 1,
        "defects": {
            "counts": defect_state.get("counts", {}),
            "release_blocking": defect_state.get("release_blocking", []),
        },
        "notes": [
            "This file is derived. Do not use it as the canonical task specification.",
            "No task claim, GitHub write, network call, or permission change is performed by this tool.",
        ],
    }
    return queue, state


def json_text(data):
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def snapshot_paths(root):
    return (
        root / "coordination" / "TASK_QUEUE.json",
        root / "coordination" / "AUTOMATION_STATE.json",
    )


def write_snapshot(root):
    queue, state = build_snapshot(root)
    queue_path, state_path = snapshot_paths(root)
    queue_path.write_text(json_text(queue), encoding="utf-8")
    state_path.write_text(json_text(state), encoding="utf-8")
    print(f"WROTE {queue_path.relative_to(root)}")
    print(f"WROTE {state_path.relative_to(root)}")


def check_snapshot(root):
    queue, state = build_snapshot(root)
    expected = dict(
        zip(snapshot_paths(root), (json_text(queue), json_text(state)))
    )
    errors = []
    for path, content in expected.items():
        if not path.is_file():
            errors.append(f"Missing derived file: {path.relative_to(root)}")
        elif path.read_text(encoding="utf-8") != content:
            errors.append(
                f"Derived file is stale: {path.relative_to(root)}; "
                "run python tools/automation_control.py snapshot --write"
            )
    return errors


def validate_policy_files(root):
    required = {
        root / "coordination" / "AUTOMATION_POLICY.yaml": (
            "repository_is_canonical: true",
            "automatic_permission_expansion: forbidden",
            "cross_repo_write_requires_authorized_router: true",
        ),
        root / "quality" / "QUALITY_GATES.yaml": (
            "not_run_is_not_pass: true",
            "release_requires_all_blocking_gates: true",
        ),
        root / "quality" / "SECURITY_POLICY.yaml": (
            "secrets_in_repository: forbidden",
            "external_code_execution_default: deny",
        ),
        root / "quality" / "ARCHITECTURE_RULES.yaml": (
            "domain_imports_ui: forbidden",
            "circular_dependencies: forbidden",
        ),
    }
    errors = []
    for path, markers in required.items():
        if not path.is_file():
            errors.append(f"Missing policy file: {path.relative_to(root)}")
            continue
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                errors.append(f"{path.relative_to(root)} missing marker: {marker}")
    return errors


def validate_wip(state):
    errors = []
    limit = int(state["wip_limit_default"])
    for agent, task_ids in state["active_by_agent"].items():
        if len(task_ids) > limit:
            errors.append(
                f"{agent} exceeds default WIP limit {limit}: {', '.join(task_ids)}"
            )
    return errors


def command_check(root):
    errors = validate_policy_files(root)
    try:
        _, state = build_snapshot(root)
        errors.extend(validate_wip(state))
    except ValidationError as exc:
        errors.append(str(exc))

    if errors:
        print("AUTOMATION CONTROL: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("AUTOMATION CONTROL: PASS")
    return 0


def command_next(root, agent):
    if agent not in AGENTS:
        print(f"ERROR: invalid agent {agent!r}; expected agent_1..agent_5")
        return 2

    queue, state = build_snapshot(root)
    if state["active_by_agent"][agent]:
        print(
            json.dumps(
                {
                    "agent": agent,
                    "status": "WIP_LIMIT_REACHED",
                    "active_tasks": state["active_by_agent"][agent],
                },
                indent=2,
            )
        )
        return 0

    try:
        try:
            from defect_control import build_state as build_defect_state
        except ImportError:
            from tools.defect_control import build_state as build_defect_state
        defects = build_defect_state().get("by_agent", {}).get(agent, [])
    except Exception:
        defects = []

    urgent = [item for item in defects if item.get("urgent")]
    if urgent:
        print(
            json.dumps(
                {
                    "agent": agent,
                    "status": "URGENT_DEFECT_AVAILABLE",
                    "defect": urgent[0],
                    "task": None,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    matches = [
        item for item in queue["items"] if item["recommended_agent"] == agent
    ]
    print(
        json.dumps(
            {
                "agent": agent,
                "status": "TASK_AVAILABLE" if matches else "NO_TASK",
                "task": matches[0] if matches else None,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check")

    snapshot = sub.add_parser("snapshot")
    mode = snapshot.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")

    next_parser = sub.add_parser("next")
    next_parser.add_argument("--agent", required=True)

    args = parser.parse_args()
    root = args.root.resolve()

    try:
        if args.command == "check":
            return command_check(root)
        if args.command == "snapshot":
            if args.write:
                write_snapshot(root)
                return 0
            errors = check_snapshot(root)
            if errors:
                print("AUTOMATION SNAPSHOT: STALE")
                for error in errors:
                    print(f"- {error}")
                return 1
            print("AUTOMATION SNAPSHOT: CURRENT")
            return 0
        if args.command == "next":
            return command_next(root, args.agent)
    except ValidationError as exc:
        print(f"AUTOMATION CONTROL: FAIL\n- {exc}")
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
