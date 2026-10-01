# AGENTS.md

This project consumes **Ackerschewski/Basis-Agent-System V-01.05.00**.

## Startup

Read:
1. central Security and Agent Execution Protocol
2. central Automation, Defect, Release, Quality, Feedback, Runtime-Evidence and Dependency-Security policies
3. own central agent profile
4. local `coordination/AGENT_PROFILE.yaml`
5. project requirements/architecture/codebase map
6. `coordination/AUTOMATION_POLICY.yaml`
7. `coordination/DEFECT_STATE.json`
8. derived feedback/runtime/dependency/quality state files
9. `coordination/RELEASE_STATE.json`
10. local quality/security/architecture gates
11. `coordination/PROJECT_TEST_MATRIX.yaml`
12. `coordination/CI_BUDGET_POLICY.yaml`
13. `coordination/SECURITY_DEPENDENCY_BASELINE.yaml`
14. `coordination/RESET_DAY_PLAN.yaml`
15. concrete task, defect or feedback item

## Normal work

`discover -> plan -> claim -> implement -> verify -> review -> handoff -> integrate`

Default WIP is one material work item per agent.

## Defect work

Urgent BLOCKER/CRITICAL defects may preempt normal READY tasks when the agent has no active claim.

`OPEN -> IN_PROGRESS -> RETEST_REQUIRED -> VERIFIED -> CLOSED`

A reproducible fix needs a regression test. Fix-ready requires a PR reference. Verification strength must match the original failing gate. Two failed fix cycles escalate.

## Release work

Release state is derived. An allowed build is not a final release. Final publication requires explicit project-owner approval.

## Evidence

NOT_RUN is not PASS. Static tests do not replace host runtime, user or physical evidence.

## Security

Automation cannot widen permissions, write cross-repository without authorized routing, silently merge, or publish a final release.
