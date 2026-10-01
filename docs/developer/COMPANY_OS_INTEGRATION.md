# Company OS Integration Contract

Company OS is a derived control-plane view. Repositories remain canonical.

It may display:
- project progress
- runnable task queue
- agent WIP
- active and release-blocking defects
- defect fix-attempt count and escalation state
- quality evidence
- development/user-test/RC/final release readiness
- whether project-owner approval is currently required

Recommended read-model files:
- `coordination/AUTOMATION_STATE.json`
- `coordination/DEFECT_STATE.json`
- `coordination/RELEASE_STATE.json`

Company OS must not edit derived files as a substitute for canonical task, defect or evidence changes.

A user approval for final release must be recorded through the project's canonical approval path with conflict protection; a UI button must never bypass repository release gates.
