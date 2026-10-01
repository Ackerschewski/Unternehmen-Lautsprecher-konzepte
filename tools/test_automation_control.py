#!/usr/bin/env python3
"""Regression tests for tools/automation_control.py."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import automation_control as ac


POLICIES = {
    "coordination/AUTOMATION_POLICY.yaml": """schema_version: 1
principles:
  repository_is_canonical: true
security:
  automatic_permission_expansion: forbidden
  cross_repo_write_requires_authorized_router: true
""",
    "quality/QUALITY_GATES.yaml": """schema_version: 1
principles:
  not_run_is_not_pass: true
  release_requires_all_blocking_gates: true
""",
    "quality/SECURITY_POLICY.yaml": """schema_version: 1
security:
  secrets_in_repository: forbidden
  external_code_execution_default: deny
""",
    "quality/ARCHITECTURE_RULES.yaml": """schema_version: 1
architecture:
  domain_imports_ui: forbidden
  circular_dependencies: forbidden
""",
}


def task_text(task_id, title, task_type="FEATURE", status="READY",
              priority="MEDIUM", owner="", depends_on="", modules=""):
    return f"""# {task_id} – {title}

## Type
{task_type}

## Goal
Implement the requested behavior.

## User / System Value
Useful.

## Owner
{owner}

## Status
{status}

## Priority
{priority}

## GitHub Execution

## User Test
Required: NO

## Affected Modules
{modules}

## Depends On
{depends_on}

## Blocks

## Provides

## Allowed Files

## Do Not Modify

## Required Interfaces

## Module Locks Required
NO

## Implementation Notes

## Change Budget

## Acceptance Criteria
- [ ] done

## Tests
- [ ] Unit

## Change Impact

## Documentation Changes
- [ ] Not required, with reason

## Known Risks / Limitations

## Handoff
"""


class AutomationControlTests(unittest.TestCase):
    def make_repo(self):
        tmp = tempfile.TemporaryDirectory(prefix="automation-control-test-")
        root = Path(tmp.name)
        (root / "coordination" / "tasks").mkdir(parents=True)
        (root / "quality").mkdir()
        for rel, content in POLICIES.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        return tmp, root

    def write_task(self, root, task_id, **kwargs):
        (root / "coordination" / "tasks" / f"{task_id}.md").write_text(
            task_text(task_id=task_id, **kwargs),
            encoding="utf-8",
        )

    def test_feature_routes_to_agent_2(self):
        tmp, root = self.make_repo()
        self.addCleanup(tmp.cleanup)
        self.write_task(root, "TASK-0001", title="Ring generator")
        queue, _ = ac.build_snapshot(root)
        self.assertEqual(queue["items"][0]["recommended_agent"], "agent_2")

    def test_ui_hint_routes_to_agent_3_without_build_false_positive(self):
        tmp, root = self.make_repo()
        self.addCleanup(tmp.cleanup)
        self.write_task(root, "TASK-0001", title="Build ring generator")
        self.write_task(root, "TASK-0002", title="Improve UI panel", priority="HIGH")
        queue, _ = ac.build_snapshot(root)
        by_id = {item["task_id"]: item for item in queue["items"]}
        self.assertEqual(by_id["TASK-0001"]["recommended_agent"], "agent_2")
        self.assertEqual(by_id["TASK-0002"]["recommended_agent"], "agent_3")

    def test_dependency_blocks_ready_task(self):
        tmp, root = self.make_repo()
        self.addCleanup(tmp.cleanup)
        self.write_task(
            root, "TASK-0001", title="Base contract",
            task_type="REFACTOR", status="IN_PROGRESS",
        )
        self.write_task(
            root, "TASK-0002", title="Feature on contract",
            depends_on="TASK-0001",
        )
        queue, state = ac.build_snapshot(root)
        self.assertEqual(queue["items"], [])
        self.assertEqual(state["blocked_by_dependency"], ["TASK-0002"])

    def test_priority_orders_queue(self):
        tmp, root = self.make_repo()
        self.addCleanup(tmp.cleanup)
        self.write_task(root, "TASK-0001", title="Low", priority="LOW")
        self.write_task(root, "TASK-0002", title="Critical", priority="CRITICAL")
        queue, _ = ac.build_snapshot(root)
        self.assertEqual(
            [item["task_id"] for item in queue["items"]],
            ["TASK-0002", "TASK-0001"],
        )

    def test_snapshot_roundtrip(self):
        tmp, root = self.make_repo()
        self.addCleanup(tmp.cleanup)
        self.write_task(root, "TASK-0001", title="Feature")
        ac.write_snapshot(root)
        self.assertEqual(ac.check_snapshot(root), [])

    def test_unknown_dependency_is_rejected(self):
        tmp, root = self.make_repo()
        self.addCleanup(tmp.cleanup)
        self.write_task(root, "TASK-0001", title="Feature", depends_on="TASK-9999")
        with self.assertRaises(ac.ValidationError):
            ac.build_snapshot(root)


if __name__ == "__main__":
    unittest.main()
