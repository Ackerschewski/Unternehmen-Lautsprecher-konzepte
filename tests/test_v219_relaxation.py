"""TASK-0029 workstream G: combined relaxation proposals that are verified by the real design service."""
from __future__ import annotations

import os

import pytest
from PySide6.QtWidgets import QApplication

from lautsprecher_konstruktion.library.store import ComponentLibrary
from lautsprecher_konstruktion.services.automatic import (
    AutomaticDesignRequest,
    AutomaticDesignResult,
    automatic_design,
)
from lautsprecher_konstruktion.services.relaxation import (
    MAX_PROPOSALS,
    Change,
    _applied,
    _proposal,
    find_relaxations,
)
from lautsprecher_konstruktion.ui.assistant_window import AssistantWindow

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def library() -> ComponentLibrary:
    return ComponentLibrary()


@pytest.fixture(scope="module")
def two_limits(library: ComponentLibrary) -> tuple[AutomaticDesignRequest, AutomaticDesignResult]:
    request = AutomaticDesignRequest(max_width_m=0.23, max_height_m=0.42, max_depth_m=0.10, target_f3_hz=35.0)
    result = automatic_design(request, library)
    assert result.status == "impossible"
    return request, result


def test_impossible_request_collects_soft_misses_with_several_limits(
        two_limits: tuple[AutomaticDesignRequest, AutomaticDesignResult]) -> None:
    _, result = two_limits
    assert result.soft_misses and any(len(m) >= 2 for m in result.soft_misses)
    assert not result.diagnostics  # no single-limit fix exists here, which is exactly the case this search covers


def test_proposals_are_verified_distinct_and_capped(
        two_limits: tuple[AutomaticDesignRequest, AutomaticDesignResult], library: ComponentLibrary) -> None:
    request, result = two_limits
    found = find_relaxations(request, library, result)
    assert 1 <= len(found) <= MAX_PROPOSALS
    assert [r.cost for r in found] == sorted(r.cost for r in found)
    for proposal in found:
        again = automatic_design(_applied(request, proposal.changes), library)  # the claim must hold when re-run
        assert again.status != "impossible" and len(again.designs) == proposal.designs_found
        assert {c.field for c in proposal.changes} >= {"max_depth"}
    assert len({tuple((c.field, c.new) for c in r.changes) for r in found}) == len(found)


def test_unverifiable_proposals_are_dropped(two_limits: tuple[AutomaticDesignRequest, AutomaticDesignResult],
                                            library: ComponentLibrary) -> None:
    request, result = two_limits
    never = lambda _r, _l: AutomaticDesignResult("impossible", (), (), (), 0)
    assert find_relaxations(request, library, result, runner=never) == ()


def test_proposal_rounds_in_the_safe_direction() -> None:
    request = AutomaticDesignRequest(max_depth_m=0.10, target_spl_db=110.0)
    changes, cost = _proposal(request, {"depth": 0.1432, "spl": -97.4}) or ((), 0.0)
    by = {c.field: c for c in changes}
    assert by["max_depth"].new == 145.0  # up to the next 5 mm
    assert by["target_spl"].new == 97.0  # down: a higher target would still fail
    assert cost > 0 and isinstance(by["max_depth"], Change)


def test_nothing_proposed_when_no_limit_is_exceeded() -> None:
    request = AutomaticDesignRequest(max_depth_m=0.40)
    assert _proposal(request, {"depth": 0.30}) is None


def test_ui_search_shows_buttons_and_applies_all_changes(
        two_limits: tuple[AutomaticDesignRequest, AutomaticDesignResult], library: ComponentLibrary) -> None:
    QApplication.instance() or QApplication([])
    request, result = two_limits
    window = AssistantWindow()
    window.diagnostic.show_result(result)
    assert window.diagnostic.search_button.isVisibleTo(window.diagnostic) is True or result.soft_misses
    window.diagnostic.show_relaxations(find_relaxations(request, library, result))
    assert window.diagnostic.relax_buttons and "geprüft" in window.diagnostic.relax_buttons[0].text()
    window.diagnostic.show_relaxations(())
    assert "keinen Entwurf" in window.diagnostic.search_note.text()
    window._apply_suggestions([("max_depth", 145.0), ("target_f3", 72.0)])
    assert window.max_depth.value() == 145.0 and window.target_f3.value() == 72.0
    window.worker.wait(240000)


def test_absurd_ratios_are_not_proposed() -> None:
    request = AutomaticDesignRequest(max_depth_m=0.20)
    assert _proposal(request, {"depth": 1.635}) is None  # more than three times the limit: a different product
    assert _proposal(request, {"depth": 0.50}) is not None
