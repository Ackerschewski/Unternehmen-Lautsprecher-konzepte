# Ackerschewski Development Standard

This document is the compact entry point for the common development standard. Detailed rules remain in `PROJECT_RULES/` and the developer documentation. Project-specific `AGENTS.md` files may add stricter rules, but must not silently weaken this baseline.

## 1. Source of Truth

Priority:
1. canonical files in the project repository,
2. integrated code and tests on the canonical branch,
3. GitHub issue/PR mirrors,
4. Linear and Company OS as planning/view layers,
5. local or chat-only notes.

Conflicts are resolved in favor of the canonical repository state unless a documented integration contract explicitly says otherwise.

## 2. Repository identity

Every repository has exactly one category: PRIVAT, WORK, UNTERNEHMEN or BASIS, using the prefixes `Privat-`, `Work-`, `Unternehmen-` or `Basis-`.

Repository names do not contain release versions. Release artifacts follow:
`<repository-name>_V-XX.XX.XX`.

## 3. Versioning

Version format: `V-AA.BB.CC`.
- AA: major release.
- BB: features since the major release.
- CC: fixes since the current feature version.
- A feature increment resets CC.
- A major increment resets BB and CC.

Each project must have one unambiguous version source, either a `VERSION` file or a documented technology-native equivalent. Version changes must be reflected in the project ledger/changelog where those files exist.

## 4. Branches, tasks and pull requests

Material work starts from a canonical task or defect.

Default branch names:
- `agent-N/TASK-ID-short-description`
- `feature/TASK-ID-short-description`
- `fix/TASK-ID-short-description`
- `infra/TASK-ID-short-description`

Open PRs early as drafts. A PR becomes Ready only after local validation is green and the change is coherent. Avoid rescue-branch chains such as `final2`, `rebase3` or `latest`.

The task/issue must identify:
- goal and scope,
- source of truth,
- acceptance criteria,
- required tests/evidence,
- Definition of Done,
- protected interfaces/areas.

## 5. Commit and integration rules

Commits should be reviewable, scoped and reproducible. Shared contracts must not change silently. Architecture or public-interface changes require documentation and, where appropriate, an ADR/decision record.

Do not merge unresolved blocking defects. Do not publish a final release merely because CI or a build succeeded.

## 6. Function status and change protection

Every product repository maintains a function matrix. Minimum columns:
- function/module,
- description,
- implementation status,
- change protection,
- acceptance criteria,
- test/evidence status,
- last confirmed version/commit,
- related issue,
- known limitations.

Allowed implementation states:
`planned`, `implemented`, `to_test`, `tested`, `stable`.

Allowed protection states:
`changeable`, `stable`, `frozen/approval_required`.

A function is never marked stable solely because it builds. Unknown test status is `to_test`, not guessed.

## 7. Architecture and code structure

Business/domain logic, application orchestration, UI and host/external adapters must be separated where the technology allows it. UI code must not become the canonical implementation of business rules.

Shared functionality is grouped by responsibility. Large modules require a local README or codebase-map entry. Generated/build/cache/IDE artifacts stay out of version control unless deliberately versioned as deterministic evidence.

## 8. Error handling and logging

Errors must fail visibly and preserve actionable context. Do not silently convert unknown/blocked/conflict states into success.

Logs:
- use clear severity,
- include operation/context identifiers where useful,
- avoid secrets and sensitive content,
- distinguish user errors, recoverable technical failures and blocking integrity failures,
- preserve evidence required for reproducibility.

## 9. Test levels

Evidence levels are not interchangeable:
- Unit/Core: deterministic logic.
- Smoke: basic startup/import/build path.
- Integration: subsystem interfaces.
- Host runtime: Blender/Inventor/Unreal/Windows behavior.
- Practice/User test: real workflow acceptance.
- Regression: previously failing behavior remains fixed.
- Physical/Manufacturing evidence: required where software output depends on real fabrication.

`NOT_RUN` is never `PASS`.

Manual host tests must record application/version, source revision, steps, outcome and relevant artifact/log references.

## 10. CI and cloud-cost policy

Local deterministic checks are the primary feedback loop. Cloud CI is an integration gate.

Default:
- no unbounded CI on every agent push,
- draft PRs do not consume CI by default,
- scoped Ready-for-review/main validation is allowed,
- expensive host/runtime/package jobs remain manual or explicitly queued,
- schedules require separate review,
- obsolete runs are cancelled when possible,
- CI budget reset never automatically enables all workflows.

Project-specific `coordination/CI_POLICY.yaml` is authoritative.

## 11. Security and dependencies

Secrets must not be committed. Automation may not widen permissions, add external execution surfaces, install/upgrade dependencies automatically, write cross-repository without authorized routing, silently merge or publish final releases.

Dependency changes require origin/license/security review appropriate to project risk.

## 12. Releases and changelog

A release requires:
- consistent version,
- acceptance criteria met,
- required evidence current,
- release-blocking defects resolved or explicitly accepted,
- changelog/known limitations current,
- reproducible artifact/build manifest where applicable.

Final publication requires explicit project-owner approval.

## 13. Documentation

Every project maintains:
- user-facing operating documentation appropriate to the product,
- developer/maintenance documentation explaining architecture, data flow, modules and extension points.

Architecture changes update the relevant documentation in the same work item.

## 14. Definition of Done

A work item is Done only when:
- implementation is integrated,
- required tests/evidence are complete,
- regression coverage exists for reproducible fixes,
- docs/contracts/version state are updated where affected,
- no required handoff is missing,
- user/host/physical validation has passed when the task requires it.

## 15. Company OS and Linear

Company OS may aggregate progress, tasks and evidence. Linear may mirror planning and assignments. Neither replaces project-repository truth.

Repository renames must be propagated to Company OS, Linear, agent routing, CI/deployment, docs and external integrations.
