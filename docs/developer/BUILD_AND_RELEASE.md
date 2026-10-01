# Build and Release

## Channels

### Development
Internal deterministic artifact. No publication authority.

### User Test
Real user/host validation artifact. May be built when the user-test channel is READY.

### Release Candidate
Requires no release-blocking defects, required gates PASS/NOT_REQUIRED, consistent version ledger and current documentation/known limitations/changelog.

### Final
All RC conditions plus explicit project-owner approval.

## Readiness

`tools/release_control.py` derives `coordination/RELEASE_STATE.json`.

## Packaging requirements
- exact source revision in build manifest
- deterministic payload where practical
- hashes recommended
- stale/mixed payload must fail
- artifact version matches repository version

## Publication
A successful build or merge to main is not a final release. Final publication requires the project owner.

## Rollback
Keep the source revision, artifact manifest and known limitations associated with every published release so a prior verified artifact can be restored.
