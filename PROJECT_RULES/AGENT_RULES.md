# Agent Rules

- Canonical persistent roles come from `Ackerschewski/Agent-System` pinned in `coordination/AGENT_PROFILE.yaml`.
- Project role files are overlays only; do not fork the central role definitions.
- Every agent works on a concrete assigned task and respects ownership/module locks.
- Use the central Agent Execution Protocol: discover -> plan -> claim -> implement -> verify -> review -> handoff -> integrate.
- No change outside task scope without a documented reason.
- No silent public-contract or architecture changes.
- No permissions are granted by skill text.
- No release-version change by Agent 1–4.
- Handoff before transfer/integration.
- Record blockers and unresolved decisions rather than guessing.
- A project may tighten central security rules but never relax them.
