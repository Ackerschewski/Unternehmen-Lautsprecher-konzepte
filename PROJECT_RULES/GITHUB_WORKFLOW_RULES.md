# GitHub Workflow Rules V2

## Purpose

GitHub is the execution surface for repository work. The repository remains the canonical project truth.

## Canonical chain

`TASK file -> GitHub Issue -> work branch -> Pull Request -> review/user test -> merge -> release`

The GitHub Issue mirrors the task. It must not become a second independent specification.

## Branch model

Default:
- `main`: stable integrated state.
- `agent-N/TASK-ID-short-description`: agent work.
- `feature/TASK-ID-short-description`: non-agent feature work.
- `fix/TASK-ID-short-description`: fixes.
- `infra/TASK-ID-short-description`: infrastructure/governance.

For high-concurrency projects an additional long-lived `integration/current` branch is allowed. In that mode:
`task branch -> integration/current -> user validation -> main`.

Do not create sequential rescue names such as `rebase2`, `rebase3`, `final2` or `latest` as a normal workflow. Reconcile into the canonical task branch or create a documented replacement branch and close the superseded one.

## Pull Requests

- Open PRs early as Draft.
- Draft PRs are the normal implementation state.
- Move to Ready for review only when local validation is green and the change is coherent.
- PR body must reference the canonical task and issue.
- Do not merge unresolved critical blockers.
- Delete merged short-lived branches when safe.

## Task / Issue bridge

Every material task may have one GitHub Issue. The task file is authoritative for scope, acceptance criteria, interfaces, ownership and handoff.

The task records:
- GitHub issue number
- work branch
- PR number
- integration target
- user-test requirement

The issue should link back to the task path.

## User-test gate

Use these task states when host/UI/hardware/manual validation is required:
- `USER_TEST_REQUIRED`
- `USER_TEST_FAILED`
- `USER_TEST_PASSED`

A user-tested task is not `DONE` until required user validation passed.

## CI budget

`coordination/CI_POLICY.yaml` controls runner usage.

When `mode: manual_only`:
- no new automatic push/PR runner triggers,
- do not mark PRs Ready solely to trigger CI,
- local validation is mandatory,
- heavy build/runtime/package workflows stay manual,
- documentation/coordination-only work must not consume cloud runners.

## Releases

A release is distinct from a commit and from `main`.
Release evidence should include:
- version/tag
- changelog
- test/validation evidence
- known limitations
- build manifest
- distributable artifact(s), when applicable

## Company OS

Company OS may read and present repository status, tasks, issues, PRs, validation state and releases. It is a view/orchestration layer, not a second source of truth. Conflict resolution always favors canonical repository files unless a documented integration rule says otherwise.
