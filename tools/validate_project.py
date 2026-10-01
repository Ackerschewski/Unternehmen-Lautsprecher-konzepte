#!/usr/bin/env python3
"""Technology-neutral quality gate for repositories created from Project-Template."""

from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is required. Install with: python -m pip install pyyaml")
    sys.exit(2)

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "README.md", "AGENTS.md", "VERSION", "CHANGELOG.md", "ROADMAP.md", "CONTRIBUTING.md",
    "docs/specifications/PROJECT_INTAKE.md",
    "docs/specifications/PROJECT_BRIEF.md",
    "docs/specifications/REQUIREMENTS.md",
    "docs/specifications/PRODUCT_SPEC.md",
    "docs/specifications/SCOPE.md",
    "docs/specifications/NON_GOALS.md",
    "docs/specifications/ACCEPTANCE_CRITERIA.md",
    "docs/developer/ARCHITECTURE.md",
    "docs/developer/CODEBASE_MAP.md",
    "docs/developer/DEVELOPER_ONBOARDING.md",
    "docs/developer/TESTING.md",
    "docs/developer/BUILD_AND_RELEASE.md",
    "docs/developer/REPOSITORY_GOVERNANCE.md",
    "docs/developer/AUTOMATION.md",
    "docs/developer/COMPANY_OS_INTEGRATION.md",
    "docs/user/USER_GUIDE.md",
    "coordination/BLACKBOARD.md",
    "coordination/DASHBOARD.md",
    "coordination/PROJECT_STATE.yaml",
    "coordination/AGENT_PROFILE.yaml",
    "coordination/CODE_QUALITY_POLICY.yaml",
    "coordination/GITHUB_WORKFLOW.yaml",
    "coordination/REPOSITORY_METADATA.yaml",
    "coordination/VERSION_LEDGER.yaml",
    "coordination/RELEASE_CHECKLIST.md",
    "coordination/AUTOMATION_POLICY.yaml",
    "coordination/DEFECT_STATE.json",
    "coordination/RELEASE_EVIDENCE.json",
    "coordination/RELEASE_STATE.json",
    "coordination/USER_FEEDBACK_STATE.json",
    "coordination/RUNTIME_EVIDENCE.json",
    "coordination/DEPENDENCY_SECURITY_STATE.json",
    "coordination/QUALITY_METRICS.json",
    "coordination/PROJECT_TEST_MATRIX.yaml",
    "coordination/CI_BUDGET_POLICY.yaml",
    "coordination/SECURITY_DEPENDENCY_BASELINE.yaml",
    "coordination/RESET_DAY_PLAN.yaml",
    "coordination/INTEGRATION_QUEUE.md",
    "coordination/STATUS_VALUES.md",
    "coordination/OWNERSHIP.md",
    "coordination/INTERFACES.md",
    "coordination/OPEN_QUESTIONS.md",
    "coordination/INITIAL_TASK_GRAPH.md",
    "PROJECT_RULES/ARCHITECTURE_RULES.md",
    "PROJECT_RULES/REPOSITORY_RULES.md",
    "PROJECT_RULES/INTEGRATION_RULES.md",
    "PROJECT_RULES/GITHUB_WORKFLOW_RULES.md",
    "PROJECT_RULES/CODE_STRUCTURE_RULES.md",
    "PROJECT_RULES/CODING_RULES.md",
    "PROJECT_RULES/TEST_RULES.md",
    "PROJECT_RULES/AGENT_RULES.md",
    "PROJECT_RULES/DOCUMENTATION_RULES.md",
    "PROJECT_RULES/RELEASE_RULES.md",
    "PROJECT_RULES/SECURITY_RULES.md",
    "PROJECT_RULES/BACKLOG_HYGIENE_RULES.md",
    "quality/DOCUMENTATION_GUARD.yaml",
    "quality/RUNTIME_TEST_PLAN.yaml",
    "quality/DEPENDENCY_WATCH.yaml",
    "agents/AGENT_1_ARCHITECT.md",
    "agents/AGENT_2_FEATURES.md",
    "agents/AGENT_3_UI.md",
    "agents/AGENT_4_INTEGRATION.md",
    "agents/AGENT_5_QA.md",
    "tools/generate_dashboard.py",
    "tools/automation_control.py",
    "tools/defect_control.py",
    "tools/release_control.py",
    "tools/quality_control.py",
    "tools/feedback_control.py",
    "tools/runtime_evidence.py",
    "tools/dependency_watch.py",
    "tools/quality_metrics.py",
    "tools/artifact_manifest.py",
    "tools/ci_budget_check.py",
]

VERSION_RE = re.compile(
    r"^V-(?P<major>\d{2})\.(?P<feature>\d{2})\.(?P<fix>\d{2})(?:-RC(?P<rc>\d+))?$"
)
TASK_FILE_RE = re.compile(r"^TASK-\d{4}\.md$")
TRACKED_TODO_RE = re.compile(r"\bTODO\s+(?:TASK|BUG|TECHDEBT|REG)-\d{4}\b", re.I)
ANY_TODO_RE = re.compile(r"\bTODO\b", re.I)

PROJECT_STATUSES = {
    "PLANNING", "ACTIVE", "BLOCKED", "RELEASE_CANDIDATE",
    "RELEASED", "MAINTENANCE", "ARCHIVED",
}
AGENT_STATUSES = {
    "READY", "CLAIMED", "IN_PROGRESS", "BLOCKED",
    "REVIEW_READY", "IN_REVIEW", "DONE", "OFFLINE",
}
TASK_STATUSES = {
    "PLANNED", "READY", "CLAIMED", "IN_PROGRESS", "BLOCKED",
    "REVIEW_READY", "IN_REVIEW", "USER_TEST_REQUIRED", "USER_TEST_FAILED",
    "USER_TEST_PASSED", "DONE", "DEPRECATED",
}
TASK_TYPES = {"FEATURE", "FIX", "REFACTOR", "DOCS", "TEST", "INFRA"}

CATEGORY_RULES = {
    "PRIVAT": {
        "prefix": "Privat-",
        "owner": "Ackerschewski",
        "topic": "privat",
    },
    "WORK": {
        "prefix": "Work-",
        "owner": "Ackerschewski",
        "topic": "work",
    },
    "UNTERNEHMEN": {
        "prefix": "Unternehmen-",
        "owner": "Ackerschewski",
        "topic": "unternehmen",
    },
    "BASIS": {
        "prefix": "Basis-",
        "owner": "Ackerschewski",
        "topic": "basis",
    },
}
LEGACY_CATEGORY_ALIASES = {
    "PRIVATE": "PRIVAT",
    "SELF_EMPLOYED": "UNTERNEHMEN",
    "INFRA": "BASIS",
    "TEMPLATE": "BASIS",
}
PROJECT_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
REPOSITORY_NAME_RE = re.compile(r"^(Privat|Work|Unternehmen|Basis)-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*$")
REQUIRED_TASK_HEADINGS = [
    "## Type", "## Goal", "## Owner", "## Status", "## Affected Modules",
    "## Depends On", "## Allowed Files", "## Do Not Modify",
    "## Acceptance Criteria", "## Tests", "## Change Impact",
    "## Documentation Changes", "## Handoff",
]


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


def read_yaml(path: Path, report: Report):
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        report.error(f"{path.relative_to(ROOT)}: invalid YAML: {exc}")
        return None


def validate_required_files(report: Report) -> None:
    for rel in REQUIRED_FILES:
        if not (ROOT / rel).is_file():
            report.error(f"Missing required file: {rel}")


def validate_version(report: Report):
    path = ROOT / "VERSION"
    if not path.is_file():
        return None, None

    version = path.read_text(encoding="utf-8").strip()
    match = VERSION_RE.fullmatch(version)
    if not match:
        report.error(
            f"VERSION must match V-01.00.00 or V-01.00.00-RC1, got: {version!r}"
        )
    return version, match


def validate_version_ledger(report: Report, version_match) -> None:
    path = ROOT / "coordination/VERSION_LEDGER.yaml"
    if not path.is_file() or version_match is None:
        return

    data = read_yaml(path, report)
    if not isinstance(data, dict) or not isinstance(data.get("version"), dict):
        report.error("VERSION_LEDGER.yaml requires a 'version' mapping.")
        return

    v = data["version"]
    expected = {
        "major": int(version_match.group("major")),
        "features_since_major": int(version_match.group("feature")),
        "fixes_since_feature": int(version_match.group("fix")),
    }
    for key, expected_value in expected.items():
        actual = v.get(key)
        if actual != expected_value:
            report.error(
                f"VERSION_LEDGER {key}={actual!r} does not match VERSION "
                f"component {expected_value}."
            )

    rc = version_match.group("rc")
    ledger_rc = v.get("release_candidate")
    expected_rc = int(rc) if rc is not None else None
    if ledger_rc != expected_rc:
        report.error(
            f"VERSION_LEDGER release_candidate={ledger_rc!r} does not match "
            f"VERSION release candidate {expected_rc!r}."
        )

    rules = data.get("rules")
    if not isinstance(rules, dict):
        report.error("VERSION_LEDGER.yaml requires a 'rules' mapping.")
    else:
        if rules.get("feature_resets_fixes") is not True:
            report.error("VERSION_LEDGER rule feature_resets_fixes must be true.")
        if rules.get("major_resets_features_and_fixes") is not True:
            report.error(
                "VERSION_LEDGER rule major_resets_features_and_fixes must be true."
            )

    if not isinstance(data.get("history"), list):
        report.error("VERSION_LEDGER.yaml field history must be a list.")


def github_remote_full_name() -> str | None:
    """Return owner/repository from a github.com origin remote when available."""
    import subprocess

    try:
        remote = subprocess.check_output(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return None

    patterns = (
        r"^https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?$",
        r"^git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$",
    )
    for pattern in patterns:
        match = re.fullmatch(pattern, remote)
        if match:
            return f"{match.group(1)}/{match.group(2)}"
    return None


def validate_repository_metadata(
    report: Report, template_mode: bool, state: dict
) -> None:
    path = ROOT / "coordination/REPOSITORY_METADATA.yaml"
    if not path.is_file():
        return

    data = read_yaml(path, report)
    if not isinstance(data, dict):
        report.error("REPOSITORY_METADATA.yaml must contain a YAML mapping.")
        return

    repository = data.get("repository")
    naming = data.get("naming")
    topics = data.get("topics")

    if not isinstance(repository, dict):
        report.error("REPOSITORY_METADATA.yaml requires mapping: repository")
        return
    if not isinstance(naming, dict):
        report.error("REPOSITORY_METADATA.yaml requires mapping: naming")
        return
    if not isinstance(topics, dict):
        report.error("REPOSITORY_METADATA.yaml requires mapping: topics")
        return

    required_repo_fields = (
        "category", "project_slug", "repository_name", "target_owner",
        "expected_full_name", "classification_topic",
    )
    for key in required_repo_fields:
        if key not in repository:
            report.error(f"REPOSITORY_METADATA repository.{key} is required.")

    if naming.get("repository_contains_version") is not False:
        report.error(
            "Repository names must not contain release versions; "
            "naming.repository_contains_version must be false."
        )
    if naming.get("artifact_pattern") != "<repository-name>_V-XX.XX.XX":
        report.error(
            "REPOSITORY_METADATA naming.artifact_pattern must be "
            "'<repository-name>_V-XX.XX.XX'."
        )

    if template_mode:
        template_category = LEGACY_CATEGORY_ALIASES.get(str(repository.get("category", "")), str(repository.get("category", "")))
        if template_category != "BASIS":
            report.warn("Template mode normally uses repository.category BASIS.")
        return

    category = str(repository.get("category", ""))
    canonical_category = LEGACY_CATEGORY_ALIASES.get(category, category)
    if canonical_category != category:
        report.warn(
            f"Legacy repository category {category!r}; migrate metadata to {canonical_category!r}."
        )
    category = canonical_category
    rule = CATEGORY_RULES.get(category)
    if rule is None:
        report.error(
            f"Invalid repository category {category!r}; "
            f"allowed: {sorted(CATEGORY_RULES)}"
        )
        return

    repository_name = str(repository.get("repository_name", ""))
    project_slug = str(repository.get("project_slug", ""))
    expected_name = rule["prefix"] + project_slug
    expected_full_name = f'{rule["owner"]}/{expected_name}'

    if not PROJECT_SLUG_RE.fullmatch(project_slug):
        report.error(
            f"project_slug {project_slug!r} must use lowercase kebab-case."
        )
    if repository_name != expected_name:
        report.error(
            f"repository_name {repository_name!r} does not match category naming "
            f"rule; expected {expected_name!r}."
        )
    if repository.get("prefix") != rule["prefix"]:
        report.error(
            f"repository.prefix must be {rule['prefix']!r} for {category}."
        )
    if repository.get("target_owner") != rule["owner"]:
        report.error(
            f"repository.target_owner must be {rule['owner']!r} for {category}."
        )
    if repository.get("classification_topic") != rule["topic"]:
        report.error(
            f"repository.classification_topic must be {rule['topic']!r} for {category}."
        )
    if repository.get("expected_full_name") != expected_full_name:
        report.error(
            f"repository.expected_full_name must be {expected_full_name!r}."
        )

    required_topics = topics.get("required")
    if not isinstance(required_topics, list) or rule["topic"] not in required_topics:
        report.error(
            f"topics.required must contain classification topic {rule['topic']!r}."
        )

    state_repo = state.get("repository")
    if not isinstance(state_repo, dict):
        report.error("PROJECT_STATE.yaml requires mapping: repository")
    else:
        state_category = str(state_repo.get("category", ""))
        state_category = LEGACY_CATEGORY_ALIASES.get(state_category, state_category)
        if state_category != category:
            report.error(
                "PROJECT_STATE.repository.category does not match "
                "REPOSITORY_METADATA.repository.category."
            )
        if state_repo.get("repository_name") != repository_name:
            report.error(
                "PROJECT_STATE.repository.repository_name does not match metadata."
            )
        if state_repo.get("target_owner") != rule["owner"]:
            report.error(
                "PROJECT_STATE.repository.target_owner does not match metadata."
            )

    if "_V-" in repository_name or re.search(r"V-\d{2}\.\d{2}\.\d{2}", repository_name):
        report.error("Repository name must never contain the release version.")

    actual_full_name = github_remote_full_name()
    if actual_full_name and actual_full_name != expected_full_name:
        report.error(
            f"Git remote points to {actual_full_name!r}, but repository governance "
            f"expects {expected_full_name!r}. Rename/transfer the repository or "
            "correct the classification metadata."
        )


def validate_state(report: Report, version: str | None):
    path = ROOT / "coordination/PROJECT_STATE.yaml"
    if not path.is_file():
        return True, {}

    state = read_yaml(path, report)
    if not isinstance(state, dict):
        report.error("PROJECT_STATE.yaml must contain a YAML mapping.")
        return True, {}

    template_mode = state.get("template_mode")
    if not isinstance(template_mode, bool):
        report.error("PROJECT_STATE.yaml requires boolean field: template_mode")
        template_mode = True

    project = state.get("project")
    if not isinstance(project, dict):
        report.error("PROJECT_STATE.yaml requires mapping: project")
        return template_mode, state

    for key in ("name", "version", "milestone", "status"):
        if key not in project:
            report.error(f"PROJECT_STATE.yaml project.{key} is required.")

    project_version = str(project.get("version", ""))
    if version and project_version != version:
        report.error(
            f"PROJECT_STATE project.version ({project_version}) != VERSION ({version})"
        )

    project_status = str(project.get("status", ""))
    if project_status not in PROJECT_STATUSES:
        report.error(
            f"Invalid project.status {project_status!r}; allowed: {sorted(PROJECT_STATUSES)}"
        )

    if not template_mode:
        name = str(project.get("name", "")).strip()
        if not name or name == "CHANGE_ME":
            report.error("Project mode requires a real project.name, not CHANGE_ME.")

    agents = state.get("agents")
    if not isinstance(agents, dict):
        report.error("PROJECT_STATE.yaml requires mapping: agents")
    else:
        expected = {f"agent_{i}" for i in range(1, 6)}
        missing = expected - set(agents)
        if missing:
            report.error(f"Missing standard agents: {sorted(missing)}")
        for agent_id, data in agents.items():
            if not isinstance(data, dict):
                report.error(f"{agent_id} must be a mapping.")
                continue
            status = str(data.get("status", ""))
            if status not in AGENT_STATUSES:
                report.error(
                    f"{agent_id}.status {status!r} invalid; allowed: {sorted(AGENT_STATUSES)}"
                )
            if "role" not in data:
                report.error(f"{agent_id}.role is required.")

    tasks = state.get("tasks")
    if not isinstance(tasks, dict):
        report.error("PROJECT_STATE.yaml field tasks must be a mapping.")

    for list_key in ("blockers", "interface_requests", "decision_requests", "integration_queue"):
        if not isinstance(state.get(list_key), list):
            report.error(f"PROJECT_STATE.yaml field {list_key} must be a list.")

    return template_mode, state


def extract_section_value(text: str, heading: str) -> str | None:
    match = re.search(
        rf"^{re.escape(heading)}\s*\n+([^\n#]+?)\s*$",
        text,
        re.M,
    )
    return match.group(1).strip() if match else None


def validate_tasks(report: Report, state: dict, template_mode: bool) -> None:
    task_dir = ROOT / "coordination/tasks"
    if not task_dir.is_dir():
        report.error("Missing directory: coordination/tasks")
        return

    real_task_ids: set[str] = set()

    for path in sorted(task_dir.glob("*.md")):
        if path.name == "TASK_TEMPLATE.md":
            continue
        if not TASK_FILE_RE.fullmatch(path.name):
            report.error(f"Invalid task filename: {path.relative_to(ROOT)}")
            continue

        task_id = path.stem
        real_task_ids.add(task_id)
        text = path.read_text(encoding="utf-8")

        for heading in REQUIRED_TASK_HEADINGS:
            if heading not in text:
                report.error(f"{path.name}: missing heading {heading!r}")

        status = extract_section_value(text, "## Status")
        if status not in TASK_STATUSES:
            report.error(
                f"{path.name}: invalid or missing status {status!r}; "
                f"allowed: {sorted(TASK_STATUSES)}"
            )

        task_type = extract_section_value(text, "## Type")
        if task_type not in TASK_TYPES:
            report.error(
                f"{path.name}: invalid or missing type {task_type!r}; "
                f"allowed: {sorted(TASK_TYPES)}"
            )

    if not template_mode:
        state_tasks = state.get("tasks", {})
        if isinstance(state_tasks, dict):
            state_ids = set(state_tasks.keys())
            missing_in_state = real_task_ids - state_ids
            unknown_in_state = state_ids - real_task_ids
            if missing_in_state:
                report.error(
                    f"Task files missing from PROJECT_STATE.tasks: {sorted(missing_in_state)}"
                )
            if unknown_in_state:
                report.error(
                    f"PROJECT_STATE.tasks entries without task files: {sorted(unknown_in_state)}"
                )


def validate_todos(report: Report) -> None:
    src = ROOT / "src"
    if not src.exists():
        return

    text_exts = {
        ".py", ".cs", ".vb", ".vbs", ".js", ".ts", ".tsx", ".jsx",
        ".cpp", ".c", ".h", ".hpp", ".java", ".kt", ".rs", ".go",
        ".md", ".txt",
    }
    for path in src.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in text_exts:
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for no, line in enumerate(lines, 1):
            if ANY_TODO_RE.search(line) and not TRACKED_TODO_RE.search(line):
                report.error(
                    f"Anonymous TODO in {path.relative_to(ROOT)}:{no}; "
                    "use TODO TASK-0001 / BUG-0001 / TECHDEBT-0001 / REG-0001."
                )


def validate_module_locks(report: Report) -> None:
    path = ROOT / "coordination/MODULE_LOCKS.yaml"
    if not path.is_file():
        report.warn("MODULE_LOCKS.yaml is missing.")
        return

    data = read_yaml(path, report)
    if not isinstance(data, dict) or not isinstance(data.get("locks"), list):
        report.error("MODULE_LOCKS.yaml must contain a list named 'locks'.")
        return

    for i, lock in enumerate(data["locks"], 1):
        if not isinstance(lock, dict):
            report.error(f"MODULE_LOCKS lock #{i} must be a mapping.")
            continue
        for key in ("module", "owner", "reason", "task"):
            if not lock.get(key):
                report.error(f"MODULE_LOCKS lock #{i} missing {key!r}.")


def validate_agent_profile(report: Report, template_mode: bool) -> None:
    path = ROOT / "coordination/AGENT_PROFILE.yaml"
    if not path.is_file():
        return

    data = read_yaml(path, report)
    if not isinstance(data, dict):
        report.error("AGENT_PROFILE.yaml must contain a YAML mapping.")
        return

    agent_system = data.get("agent_system")
    project = data.get("project")
    routing = data.get("routing")
    security = data.get("security")

    if not isinstance(agent_system, dict):
        report.error("AGENT_PROFILE.yaml requires mapping: agent_system")
    else:
        if agent_system.get("repository") != "Ackerschewski/Basis-Agent-System":
            report.error("AGENT_PROFILE agent_system.repository must be Ackerschewski/Basis-Agent-System.")
        version = str(agent_system.get("version", ""))
        if not VERSION_RE.fullmatch(version):
            report.error(
                "AGENT_PROFILE agent_system.version must pin an exact V-XX.XX.XX version."
            )

    if not isinstance(project, dict):
        report.error("AGENT_PROFILE.yaml requires mapping: project")
    else:
        enabled = project.get("enabled_agents")
        if not isinstance(enabled, list) or not enabled:
            report.error("AGENT_PROFILE project.enabled_agents must be a non-empty list.")
        else:
            allowed = {f"agent_{i}" for i in range(1, 6)}
            invalid = set(enabled) - allowed
            if invalid:
                report.error(f"AGENT_PROFILE contains invalid agents: {sorted(invalid)}")

        repository = str(project.get("repository", "")).strip()
        if not template_mode and (not repository or repository == "CHANGE_ME"):
            report.error("Project mode requires AGENT_PROFILE project.repository to be set.")

    if not isinstance(routing, dict) or not routing.get("authority"):
        report.error("AGENT_PROFILE requires routing.authority.")

    if not isinstance(security, dict):
        report.error("AGENT_PROFILE requires mapping: security")
    elif security.get("may_relax_agent_system_policy") is not False:
        report.error(
            "AGENT_PROFILE security.may_relax_agent_system_policy must be false."
        )


def validate_code_quality_policy(report: Report, template_mode: bool) -> None:
    path = ROOT / "coordination/CODE_QUALITY_POLICY.yaml"
    if not path.is_file():
        return

    data = read_yaml(path, report)
    if not isinstance(data, dict):
        report.error("CODE_QUALITY_POLICY.yaml must contain a YAML mapping.")
        return

    human = data.get("human_readability")
    architecture = data.get("architecture")
    code = data.get("code")

    if not isinstance(human, dict) or human.get("required") is not True:
        report.error("CODE_QUALITY_POLICY human_readability.required must be true.")
    if not isinstance(human, dict) or human.get("chat_history_required_to_understand_code") is not False:
        report.error(
            "CODE_QUALITY_POLICY must forbid requiring chat history to understand code."
        )

    if not isinstance(architecture, dict):
        report.error("CODE_QUALITY_POLICY requires architecture mapping.")
    else:
        for key in ("ui_contains_domain_logic", "domain_imports_ui", "domain_imports_host_api", "circular_dependencies"):
            if architecture.get(key) != "forbidden":
                report.error(f"CODE_QUALITY_POLICY architecture.{key} must be forbidden.")

    if not isinstance(code, dict):
        report.error("CODE_QUALITY_POLICY requires code mapping.")
    else:
        for key in ("duplicate_implementations", "silent_fallbacks", "anonymous_todos", "magic_domain_constants", "hidden_side_effects"):
            if code.get(key) != "forbidden":
                report.error(f"CODE_QUALITY_POLICY code.{key} must be forbidden.")

    if template_mode:
        return

    for rel in (
        "docs/developer/ARCHITECTURE.md",
        "docs/developer/CODEBASE_MAP.md",
        "docs/developer/DEVELOPER_ONBOARDING.md",
    ):
        p = ROOT / rel
        if p.is_file():
            body = p.read_text(encoding="utf-8")
            if "TBD" in body or "CHANGE_ME" in body:
                report.error(
                    f"Project mode: unresolved human-onboarding placeholder in {rel}."
                )


def validate_source_file_sizes(report: Report) -> None:
    src = ROOT / "src"
    if not src.is_dir():
        return

    text_exts = {
        ".py", ".cs", ".vb", ".vbs", ".js", ".ts", ".tsx", ".jsx",
        ".cpp", ".c", ".h", ".hpp", ".java", ".kt", ".rs", ".go",
    }
    for path in src.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in text_exts:
            continue
        try:
            line_count = len(path.read_text(encoding="utf-8").splitlines())
        except UnicodeDecodeError:
            continue

        rel = path.relative_to(ROOT)
        if line_count > 1500:
            report.error(
                f"{rel}: {line_count} lines exceeds the 1500-line handwritten source hard limit."
            )
        elif line_count > 800:
            report.warn(
                f"{rel}: {line_count} lines exceeds the 800-line split threshold; "
                "document justification or split responsibilities."
            )
        elif line_count > 500:
            report.warn(
                f"{rel}: {line_count} lines exceeds the 500-line responsibility-review threshold."
            )


def validate_project_mode(report: Report, template_mode: bool) -> None:
    if template_mode:
        report.warn("Template mode is ON: project-specific placeholder checks are relaxed.")
        return

    critical = [
        ROOT / "docs/specifications/PROJECT_BRIEF.md",
        ROOT / "docs/specifications/REQUIREMENTS.md",
        ROOT / "docs/specifications/PRODUCT_SPEC.md",
        ROOT / "docs/specifications/ACCEPTANCE_CRITERIA.md",
        ROOT / "docs/developer/ARCHITECTURE.md",
        ROOT / "docs/developer/CODEBASE_MAP.md",
        ROOT / "docs/developer/DEVELOPER_ONBOARDING.md",
    ]
    placeholder_patterns = ("CHANGE_ME", "Repositoryname_V-01.00.00")
    for path in critical:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for placeholder in placeholder_patterns:
            if placeholder in text:
                report.error(
                    f"Project mode: unresolved placeholder {placeholder!r} in "
                    f"{path.relative_to(ROOT)}"
                )


def main() -> int:
    report = Report()

    validate_required_files(report)
    version, version_match = validate_version(report)
    validate_version_ledger(report, version_match)
    template_mode, state = validate_state(report, version)
    validate_repository_metadata(report, template_mode, state)
    validate_agent_profile(report, template_mode)
    validate_code_quality_policy(report, template_mode)
    validate_tasks(report, state, template_mode)
    validate_todos(report)
    validate_source_file_sizes(report)
    validate_module_locks(report)
    validate_project_mode(report, template_mode)

    print("=== Project Template Quality Gate ===")
    for warning in report.warnings:
        print(f"WARNING: {warning}")
    for error in report.errors:
        print(f"ERROR: {error}")

    if report.errors:
        print(f"\nFAILED: {len(report.errors)} error(s), {len(report.warnings)} warning(s).")
        return 1

    print(f"\nPASS: 0 errors, {len(report.warnings)} warning(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
