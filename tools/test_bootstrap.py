#!/usr/bin/env python3
"""Smoke-test the project bootstrap for all repository categories."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CASES = [
    (
        "private",
        "Bearing Visualizer",
        "Ackerschewski/private-bearing-visualizer",
        "PRIVATE",
    ),
    (
        "work",
        "Inventor Drawing Automation",
        "Ackerschewski-Work/work-inventor-drawing-automation",
        "WORK",
    ),
    (
        "self-employed",
        "Furniture Generator",
        "Ackerschewski-Code/ac-furniture-generator",
        "SELF_EMPLOYED",
    ),
]


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def main() -> int:
    failures: list[str] = []

    for category, name, expected_full_name, canonical_category in CASES:
        with tempfile.TemporaryDirectory(prefix="project-template-test-") as tmp:
            target = Path(tmp) / "repo"
            shutil.copytree(
                ROOT,
                target,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )

            bootstrap = run(
                [
                    sys.executable,
                    "tools/bootstrap_project.py",
                    "--name",
                    name,
                    "--category",
                    category,
                    "--platform",
                    "Windows",
                    "--host",
                    "TestHost",
                    "--host-version",
                    "1.0",
                ],
                target,
            )
            if bootstrap.returncode != 0:
                failures.append(
                    f"{category}: bootstrap failed\n{bootstrap.stdout}"
                )
                continue

            metadata = (target / "coordination/REPOSITORY_METADATA.yaml").read_text(
                encoding="utf-8"
            )
            state = (target / "coordination/PROJECT_STATE.yaml").read_text(
                encoding="utf-8"
            )

            expected_fragments = [
                f"expected_full_name: {expected_full_name}",
                f"category: {canonical_category}",
                "template_mode: false",
            ]
            for fragment in expected_fragments:
                if fragment not in metadata and fragment not in state:
                    failures.append(
                        f"{category}: expected generated fragment missing: {fragment}"
                    )

            validate = run(
                [sys.executable, "tools/validate_project.py"],
                target,
            )
            if validate.returncode != 0:
                failures.append(
                    f"{category}: generated project failed validation\n{validate.stdout}"
                )

    if failures:
        print("=== Bootstrap Smoke Test FAILED ===")
        for failure in failures:
            print(f"\n{failure}")
        return 1

    print("=== Bootstrap Smoke Test PASS ===")
    for category, _, expected, _ in CASES:
        print(f"PASS: {category} -> {expected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
