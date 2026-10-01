# Project Automation

## Three control loops

### Task loop
`READY task -> route -> claim -> implement -> verify -> integrate`

### Defect loop
`failed gate -> fingerprint -> defect -> owner -> fix -> PR -> retest -> verify -> integrate`

Commands:
```bash
python tools/defect_control.py record-failure ...
python tools/defect_control.py start --id BUG-AUTO-...
python tools/defect_control.py fix-ready --id BUG-AUTO-... --regression-test ... --pr ...
python tools/defect_control.py retest --id BUG-AUTO-... --result PASS --evidence ... --evidence-class UNIT
python tools/defect_control.py close --id BUG-AUTO-... --integration-ref ...
```

The same normalized failure fingerprint updates the same defect. Two unsuccessful automatic repair cycles escalate.

### Release loop
`derive readiness -> build permitted channel -> validate -> RC -> owner approval -> final`

```bash
python tools/release_control.py channel --name user_test
python tools/release_control.py channel --name release_candidate
python tools/release_control.py channel --name final
```

## Derived files
- `coordination/TASK_QUEUE.json`
- `coordination/AUTOMATION_STATE.json`
- `coordination/DEFECT_STATE.json`
- `coordination/RELEASE_STATE.json`

They are views. Canonical truth remains in task files, defect JSON files, evidence and version/release files.

## CI
Cloud workflows remain subordinate to `coordination/CI_POLICY.yaml`. Manual-only mode means no automatic cloud dispatch.
