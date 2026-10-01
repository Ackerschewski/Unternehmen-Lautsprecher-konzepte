# CI Budget Reset Runbook

Use this runbook when GitHub Actions minutes or another cloud-runner budget becomes available again.

## Before reset day

1. Finish local STATIC / UNIT / INTEGRATION gates for the candidate revision.
2. Run backlog hygiene and resolve stale claims.
3. Confirm the project test matrix.
4. Confirm the CI budget profile.
5. Review dependency/security baseline for new permissions, secrets, actions or runtimes.
6. Build a reset-day queue; do not rely on memory.

## Reset-day sequence

Run the cheapest meaningful cloud validation first.

```
local gates
   ↓
cheap cloud validation
   ↓
one host/platform runtime
   ↓
packaging
   ↓
release-candidate evidence
```

Stop on the first blocking failure.

## Prohibited reset behavior

- do not enable global push CI;
- do not enable all scheduled workflows;
- do not run every repository at once;
- do not treat unused budget as a reason to add matrix jobs;
- do not automatically publish a final release;
- do not auto-install dependency upgrades discovered during the run.

## Recording

For each cloud run record:
- repository,
- workflow,
- source revision,
- run ID,
- evidence class,
- result,
- cost class,
- whether it blocks release.

## After reset-day validation

Keep the normal development loop local-first. Cloud CI remains an integration/runtime gate, not the primary feedback loop.
