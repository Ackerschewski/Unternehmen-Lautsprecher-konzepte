import json
from pathlib import Path

from tools import defect_control as dc


def setup_repo(tmp_path: Path):
    (tmp_path / "coordination" / "defects").mkdir(parents=True)
    (tmp_path / "coordination" / "tasks").mkdir(parents=True)


def test_fingerprint_is_stable():
    a = dc.fingerprint("o/r", "TASK-0001", "unit", "test_x")
    b = dc.fingerprint("o/r", "TASK-0001", "unit", "test_x")
    assert a == b


def test_evidence_strength():
    assert dc.evidence_matches("STATIC", "UNIT")
    assert dc.evidence_matches("UNIT", "INTEGRATION")
    assert not dc.evidence_matches("HOST_RUNTIME", "INTEGRATION")
    assert dc.evidence_matches("HOST_RUNTIME", "HOST_RUNTIME")


def test_state_prioritizes_severity(monkeypatch):
    defects = [
        {
            "id": "D1", "fingerprint": "1", "title": "low",
            "severity": "LOW", "status": "OPEN", "owner_agent": "agent_2",
            "review_agent": "agent_5", "source": {
                "repository": "o/r", "task_id": None, "gate": "unit",
                "check": "a", "evidence_class": "UNIT"
            }, "failure_evidence": [], "occurrences": 1, "fix_attempts": 0,
            "max_fix_attempts": 2, "regression_test": None,
            "retest": {"status": "NOT_RUN", "evidence": []},
            "integration": {"pr": None, "merge_ref": None},
            "automation": {"auto_created": True, "actionable": True,
                           "escalation_required": False},
        },
        {
            "id": "D2", "fingerprint": "2", "title": "critical",
            "severity": "CRITICAL", "status": "OPEN", "owner_agent": "agent_2",
            "review_agent": "agent_5", "source": {
                "repository": "o/r", "task_id": None, "gate": "unit",
                "check": "b", "evidence_class": "UNIT"
            }, "failure_evidence": [], "occurrences": 1, "fix_attempts": 0,
            "max_fix_attempts": 2, "regression_test": None,
            "retest": {"status": "NOT_RUN", "evidence": []},
            "integration": {"pr": None, "merge_ref": None},
            "automation": {"auto_created": True, "actionable": True,
                           "escalation_required": False},
        },
    ]
    monkeypatch.setattr(dc, "load_defects", lambda: defects)
    state = dc.build_state()
    assert state["by_agent"]["agent_2"][0]["id"] == "D2"
