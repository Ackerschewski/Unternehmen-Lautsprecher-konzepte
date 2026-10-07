"""Impossible requests report measured misses and suggestions that were verified by the solver."""
import pytest

from lautsprecher_konstruktion.library.store import ComponentLibrary
from lautsprecher_konstruktion.services.automatic import (
    AutomaticDesignRequest,
    Diagnostic,
    _diagnostics,
    automatic_design,
)


def _request(**kw: object) -> AutomaticDesignRequest:
    base: dict[str, object] = {"max_width_m": 0.23, "max_height_m": 0.42, "max_depth_m": 0.31}
    base.update(kw)
    return AutomaticDesignRequest(**base)  # type: ignore[arg-type]


def test_diagnostic_delta_and_ordering_by_relative_miss() -> None:
    request = _request(max_depth_m=0.10, target_f3_hz=30.0, budget=100.0)
    items = _diagnostics(request, {"depth": 0.1432, "f3": 55.0, "budget": 150.0}, None)
    assert [d.key for d in items] == ["f3", "budget", "depth"]  # 83 % > 50 % > 43 % relative miss
    depth = next(d for d in items if d.key == "depth")
    assert depth.suggested == 145.0 and depth.field == "max_depth" and depth.delta == pytest.approx(43.2)
    assert depth.action == "Tiefe auf 145 mm setzen"


def test_spl_miss_is_rounded_down_and_stored_negated() -> None:
    request = _request(target_spl_db=120.0)
    (item,) = _diagnostics(request, {"spl": -97.4}, None)
    assert item.key == "spl" and item.needed == pytest.approx(97.4) and item.suggested == 97.0


def test_no_diagnostics_without_a_single_violation_candidate() -> None:
    assert _diagnostics(_request(), {}, None) == ()


@pytest.fixture(scope="module")
def library() -> ComponentLibrary:
    return ComponentLibrary()


def test_depth_suggestion_makes_the_request_feasible(library: ComponentLibrary) -> None:
    result = automatic_design(_request(max_depth_m=0.10), library)
    assert result.status == "impossible" and result.diagnostics
    main = result.diagnostics[0]
    assert main.key == "depth" and main.available == pytest.approx(100.0) and main.needed > 100.0
    assert main.suggested is not None and main.suggested >= main.needed
    fixed = automatic_design(_request(max_depth_m=main.suggested / 1000), library)
    assert fixed.status == "ok" and fixed.designs


def test_budget_suggestion_is_measured_not_guessed(library: ComponentLibrary) -> None:
    result = automatic_design(_request(budget=50.0), library)
    assert result.status == "impossible"
    budget = next(d for d in result.diagnostics if d.key == "budget")
    assert isinstance(budget, Diagnostic) and budget.available == 50.0 and budget.needed > 50.0
    assert budget.suggested is not None and budget.suggested >= budget.needed
