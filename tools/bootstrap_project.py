#!/usr/bin/env python3
"""Initialize a repository created from Project-Template."""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION_RE = re.compile(
    r"^V-(?P<major>\d{2})\.(?P<feature>\d{2})\.(?P<fix>\d{2})$"
)

CATEGORY_INFO = {
    "privat": {
        "canonical": "PRIVAT",
        "prefix": "Privat-",
        "owner": "Ackerschewski",
        "topic": "privat",
    },
    "work": {
        "canonical": "WORK",
        "prefix": "Work-",
        "owner": "Ackerschewski",
        "topic": "work",
    },
    "unternehmen": {
        "canonical": "UNTERNEHMEN",
        "prefix": "Unternehmen-",
        "owner": "Ackerschewski",
        "topic": "unternehmen",
    },
    "basis": {
        "canonical": "BASIS",
        "prefix": "Basis-",
        "owner": "Ackerschewski",
        "topic": "basis",
    },
}


def yaml_string(value: str) -> str:
    """JSON strings are valid YAML strings and safely preserve spaces/special chars."""
    return json.dumps(value, ensure_ascii=False)


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    if not value:
        raise ValueError("Project name does not produce a valid repository slug.")
    return value


def base_slug(value: str) -> str:
    slug = slugify(value)
    for prefix in ("privat-", "work-", "unternehmen-", "basis-"):
        if slug.startswith(prefix):
            slug = slug[len(prefix):]
            break
    if not slug:
        raise ValueError("Project slug is empty after removing classification prefix.")
    return slug


def replace_once(text: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.M)
    if count != 1:
        raise RuntimeError(f"Could not update {label}; expected one match, got {count}.")
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Initialize a repository created from Project-Template."
    )
    parser.add_argument("--name", required=True, help="Human-readable project name")
    parser.add_argument(
        "--category",
        required=True,
        choices=sorted(CATEGORY_INFO),
        help="Repository classification",
    )
    parser.add_argument(
        "--slug",
        help="Optional base repository slug without category prefix; derived from --name if omitted",
    )
    parser.add_argument("--version", default="V-01.00.00")
    parser.add_argument("--platform", default="TBD")
    parser.add_argument("--host", default="Standalone")
    parser.add_argument("--host-version", default="TBD")
    args = parser.parse_args()

    match = VERSION_RE.fullmatch(args.version)
    if not match:
        parser.error("--version must match V-01.00.00")

    info = CATEGORY_INFO[args.category]
    project_slug = base_slug(args.slug or args.name)
    repository_name = info["prefix"] + project_slug
    expected_full_name = f'{info["owner"]}/{repository_name}'

    # PROJECT_STATE.yaml
    state_path = ROOT / "coordination/PROJECT_STATE.yaml"
    state = state_path.read_text(encoding="utf-8")
    state = replace_once(
        state, r"^template_mode:\s*true\s*$", "template_mode: false", "template_mode"
    )
    state = replace_once(
        state, r"^  name:\s*.*$", f"  name: {yaml_string(args.name)}", "project.name"
    )
    state = replace_once(
        state, r"^  version:\s*.*$", f"  version: {args.version}", "project.version"
    )
    state = replace_once(
        state, r"^  platform:\s*.*$",
        f"  platform: {yaml_string(args.platform)}",
        "project.platform",
    )
    state = replace_once(
        state, r"^  host:\s*.*$",
        f"  host: {yaml_string(args.host)}",
        "project.host",
    )
    state = replace_once(
        state, r"^  host_version:\s*.*$",
        f"  host_version: {yaml_string(args.host_version)}",
        "project.host_version",
    )
    state = replace_once(
        state, r"^  category:\s*.*$",
        f"  category: {info['canonical']}",
        "repository.category",
    )
    state = replace_once(
        state, r"^  repository_name:\s*.*$",
        f"  repository_name: {repository_name}",
        "repository.repository_name",
    )
    state = replace_once(
        state, r"^  target_owner:\s*.*$",
        f"  target_owner: {info['owner']}",
        "repository.target_owner",
    )
    state_path.write_text(state, encoding="utf-8")

    # VERSION
    (ROOT / "VERSION").write_text(args.version + "\n", encoding="utf-8")

    # VERSION_LEDGER.yaml
    ledger = f"""version:
  major: {int(match.group("major"))}
  features_since_major: {int(match.group("feature"))}
  fixes_since_feature: {int(match.group("fix"))}
  release_candidate: null

rules:
  feature_resets_fixes: true
  major_resets_features_and_fixes: true
  managed_by: agent_5

history: []
"""
    (ROOT / "coordination/VERSION_LEDGER.yaml").write_text(ledger, encoding="utf-8")

    # REPOSITORY_METADATA.yaml
    metadata = f"""repository:
  category: {info["canonical"]}
  prefix: {info["prefix"]}
  project_slug: {project_slug}
  repository_name: {repository_name}
  target_owner: {info["owner"]}
  expected_full_name: {expected_full_name}
  classification_topic: {info["topic"]}

naming:
  repository_contains_version: false
  artifact_pattern: "<repository-name>_V-XX.XX.XX"
  slug_style: kebab-case

topics:
  required:
    - {info["topic"]}
  technical: []
"""
    (ROOT / "coordination/REPOSITORY_METADATA.yaml").write_text(
        metadata, encoding="utf-8"
    )

    # AGENT_PROFILE.yaml
    agent_profile_path = ROOT / "coordination/AGENT_PROFILE.yaml"
    agent_profile = agent_profile_path.read_text(encoding="utf-8")
    agent_profile = replace_once(
        agent_profile,
        r"^  repository:\s*CHANGE_ME\s*$",
        f"  repository: {expected_full_name}",
        "agent_profile.project.repository",
    )
    agent_profile_path.write_text(agent_profile, encoding="utf-8")

    # PROJECT_BRIEF.md
    brief_path = ROOT / "docs/specifications/PROJECT_BRIEF.md"
    brief = brief_path.read_text(encoding="utf-8")
    brief = brief.replace("## Project Name\n", f"## Project Name\n{args.name}\n", 1)
    brief = brief.replace(
        "## Target Platform / Version\n",
        "## Target Platform / Version\n"
        f"- Platform: {args.platform}\n"
        f"- Host: {args.host}\n"
        f"- Host version: {args.host_version}\n",
        1,
    )
    brief_path.write_text(brief, encoding="utf-8")

    # ACCEPTANCE_CRITERIA.md
    acceptance_path = ROOT / "docs/specifications/ACCEPTANCE_CRITERIA.md"
    acceptance = acceptance_path.read_text(encoding="utf-8")
    acceptance = acceptance.replace(
        "Repositoryname_V-01.00.00",
        f"{repository_name}_{args.version}",
    )
    acceptance_path.write_text(acceptance, encoding="utf-8")

    print(f"Initialized project: {args.name}")
    print(f"Category: {info['canonical']}")
    print(f"Expected repository: {expected_full_name}")
    print(f"Initial release artifact: {repository_name}_{args.version}")
    print()
    print("IMPORTANT:")
    print("Create/rename/transfer the GitHub repository so its full name matches:")
    print(f"  {expected_full_name}")
    print()
    print("Next:")
    print("1. Complete docs/specifications/PROJECT_INTAKE.md")
    print("2. Complete REQUIREMENTS / PRODUCT_SPEC / SCOPE / NON_GOALS")
    print("3. Define architecture, dependency direction, ownership and interfaces")
    print("4. Complete docs/developer/CODEBASE_MAP.md and DEVELOPER_ONBOARDING.md")
    print("5. Review coordination/AGENT_PROFILE.yaml")
    print("6. Add GitHub topics from coordination/REPOSITORY_METADATA.yaml")
    print("7. Create the initial task graph")
    print("8. Run: python tools/validate_project.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
