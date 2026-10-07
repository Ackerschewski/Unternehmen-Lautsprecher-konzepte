"""TASK-0030: solver registry, trust levels, reference cases, harness policy, baseline, matrix and UI."""
from __future__ import annotations

import json
import math
import os
from dataclasses import replace
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from lautsprecher_konstruktion.enclosure.registry import registry
from lautsprecher_konstruktion.export.package import export_project_package
from lautsprecher_konstruktion.library.store import ComponentLibrary
from lautsprecher_konstruktion.services.automatic import AutomaticDesignRequest, automatic_design
from lautsprecher_konstruktion.validation.cases import build_cases
from lautsprecher_konstruktion.validation.families import solve_family
from lautsprecher_konstruktion.validation.matrix import matrix_data, matrix_markdown
from lautsprecher_konstruktion.validation.reference import (
    Outcome,
    ReferenceCase,
    ReferenceExpectation,
    accept_baseline,
    baseline_from,
    load_baseline,
    render_diff,
    run_cases,
    run_to_json,
)
from lautsprecher_konstruktion.validation.reference_cli import BASELINE_PATH, main
from lautsprecher_konstruktion.validation.solvers import SOLVER_DESCRIPTORS, descriptor, trust_of
from lautsprecher_konstruktion.validation.trust import CaseKind, TrustLevel, earned_trust

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def cases() -> tuple[ReferenceCase, ...]:
    return build_cases()


@pytest.fixture(scope="module")
def run(cases: tuple[ReferenceCase, ...]):  # type: ignore[no-untyped-def]
    return run_cases(cases, load_baseline(BASELINE_PATH))


# --- registry and descriptors --------------------------------------------------------------------------------------

def test_every_registered_solver_has_a_descriptor_with_sources_and_limits() -> None:
    supported = {e.id for e in registry.supported()}
    assert set(SOLVER_DESCRIPTORS) == supported and len(supported) == 29
    for d in SOLVER_DESCRIPTORS.values():
        assert d.sources and d.limitations and d.equations and d.conventions and d.model_version
        assert d.main_limitation is not None


def test_every_supported_solver_has_at_least_one_reference_case(cases: tuple[ReferenceCase, ...]) -> None:
    covered = {c.solver_id for c in cases}
    assert covered >= {e.id for e in registry.supported()}


def test_granted_trust_never_exceeds_what_the_cases_earn(run) -> None:  # type: ignore[no-untyped-def]
    for solver_id, d in SOLVER_DESCRIPTORS.items():
        assert d.trust <= run.earned_trust(solver_id), f"{solver_id}: vergeben {d.trust.name}, belegt {run.earned_trust(solver_id).name}"
    assert not any(d.trust is TrustLevel.PROTOTYPE_VALIDATED for d in SOLVER_DESCRIPTORS.values())  # no prototype data exists


def test_known_levels_and_the_experimental_set() -> None:
    assert trust_of("sealed") is TrustLevel.REFERENCE_VERIFIED and trust_of("bass_reflex") is TrustLevel.REFERENCE_VERIFIED
    for experimental in ("transmission_line_open", "tqwt", "horn_exponential", "horn_tapped", "cardioid", "bandpass_6_parallel", "mltl"):
        assert trust_of(experimental) is TrustLevel.EXPERIMENTAL
    assert descriptor("sealed").solver_id == "sealed"


def test_consistency_cases_earn_nothing() -> None:
    assert earned_trust([CaseKind.CONSISTENCY]) is TrustLevel.EXPERIMENTAL
    assert earned_trust([]) is TrustLevel.EXPERIMENTAL
    assert earned_trust([CaseKind.ANALYTIC, CaseKind.CONSISTENCY]) is TrustLevel.FORMULA_VERIFIED
    assert earned_trust([CaseKind.LITERATURE]) is TrustLevel.REFERENCE_VERIFIED
    assert earned_trust([CaseKind.PROTOTYPE]) is TrustLevel.PROTOTYPE_VALIDATED  # a level of its own


# --- the reference suite ------------------------------------------------------------------------------------------

def test_all_reference_cases_pass_and_nothing_drifted(run) -> None:  # type: ignore[no-untyped-def]
    assert run.ok, render_diff(run)
    assert not run.errors and not run.regressions


def test_expectations_carry_source_unit_and_a_justified_tolerance(cases: tuple[ReferenceCase, ...]) -> None:
    for case in cases:
        assert case.expectations
        for e in case.expectations:
            assert e.source and e.tolerance_kind in {"abs", "rel"} and e.tolerance >= 0
            if case.kind is not CaseKind.CONSISTENCY:
                assert e.justification, f"{case.case_id}/{e.metric}: Toleranz ohne technische Begründung"


def test_baseline_is_versioned_matches_the_definitions_and_records_a_reason(cases: tuple[ReferenceCase, ...]) -> None:
    baseline = load_baseline(BASELINE_PATH)
    assert baseline is not None
    assert baseline["definition_hash"] == run_cases(cases).definition_hash, "Fall-Definitionen geändert: Review und --accept-baseline nötig"
    assert baseline["history"] and all(len(h["reason"]) >= 15 and h["reviewer"] for h in baseline["history"])


def test_physical_literature_values_are_what_the_cases_say(run) -> None:  # type: ignore[no-untyped-def]
    by = {(d.case_id, d.metric): d for d in run.differences}
    assert by[("sealed.f3_over_fc_table", "f3_over_fc_q0.7071")].actual == pytest.approx(1.0, abs=0.002)
    assert by[("bass_reflex.b4_alignment", "peak_db")].actual == pytest.approx(0.0, abs=0.05)
    assert by[("baffle.dipole_sine", "max_diff_db")].actual == pytest.approx(0.0, abs=0.01)


# --- harness policy -----------------------------------------------------------------------------------------------

def _case(compute, *exps: ReferenceExpectation) -> ReferenceCase:  # type: ignore[no-untyped-def]
    return ReferenceCase("t.case", "sealed", "Test", CaseKind.ANALYTIC, compute, tuple(exps))


_EXP = ReferenceExpectation("x", 1.0, "m", "abs", 0.01, "Testquelle", "Testtoleranz")


def test_nan_inf_missing_and_crash_are_failures_never_skips() -> None:
    nan = run_cases((_case(lambda: {"x": math.nan}, _EXP),))
    assert nan.differences[0].outcome is Outcome.NOT_FINITE and not nan.ok
    inf = run_cases((_case(lambda: {"x": math.inf}, _EXP),))
    assert inf.differences[0].outcome is Outcome.NOT_FINITE
    missing = run_cases((_case(dict, _EXP),))
    assert missing.differences[0].outcome is Outcome.MISSING  # a missing output is a failure, not zero

    def boom() -> dict[str, float]:
        raise ValueError("kaputt")
    crash = run_cases((_case(boom, _EXP),))
    assert "t.case" in crash.errors and not crash.ok and crash.differences[0].outcome is Outcome.MISSING


def test_diff_is_quantitative_and_flags_drift_against_the_baseline() -> None:
    good = run_cases((_case(lambda: {"x": 1.0}, _EXP),))
    baseline = baseline_from(good)
    drifted = run_cases((_case(lambda: {"x": 1.004}, _EXP),), baseline)  # inside tolerance, but moved
    assert drifted.differences[0].outcome is Outcome.PASS and drifted.differences[0].regression and not drifted.ok
    assert "DRIFT" in render_diff(drifted) and "+0.004" in render_diff(drifted)
    failed = run_cases((_case(lambda: {"x": 1.5}, _EXP),))
    text = render_diff(failed)
    assert "FAIL" in text and "erwartet 1 m" in text and "1.5" in text
    assert run_to_json(failed)["ok"] is False


def test_baseline_cannot_be_regenerated_silently(tmp_path: Path) -> None:
    path = tmp_path / "baseline.json"
    ok = run_cases((_case(lambda: {"x": 1.0}, _EXP),))
    with pytest.raises(ValueError):
        accept_baseline(ok, path, reason="ok", reviewer="x")  # no real reason
    with pytest.raises(ValueError):
        accept_baseline(ok, path, reason="Technische Begründung ausreichend lang", reviewer="")  # no name
    failed = run_cases((_case(lambda: {"x": 2.0}, _EXP),))
    with pytest.raises(ValueError):
        accept_baseline(failed, path, reason="Technische Begründung ausreichend lang", reviewer="Name")  # never to turn red green
    assert not path.exists()
    accept_baseline(ok, path, reason="Technische Begründung ausreichend lang", reviewer="Name")
    accept_baseline(ok, path, reason="Zweite Begründung ausreichend lang", reviewer="Name")
    assert len(json.loads(path.read_text(encoding="utf-8"))["history"]) == 2


def test_the_cases_have_teeth_a_broken_solver_is_caught() -> None:
    from lautsprecher_konstruktion.acoustics import waveguide
    from lautsprecher_konstruktion.validation.families import _solve_cached
    subset = tuple(c for c in build_cases() if c.case_id.startswith(("duct.", "line.recompute.transmission_line_open")))
    _solve_cached.cache_clear()
    try:
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(waveguide, "SPEED_OF_SOUND_M_S", 340.0)  # a plausible-looking wrong constant inside the duct core
            broken = run_cases(subset)
    finally:
        _solve_cached.cache_clear()  # never leave results of the broken solver in the shared cache
    assert not broken.ok and broken.failed, "Eine falsche Schallgeschwindigkeit im Kanalkern muss auffallen"
    assert run_cases(subset).ok


# --- command line, matrix, export ---------------------------------------------------------------------------------

def test_cli_runs_everything_and_writes_machine_readable_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "run.json"
    assert main(["--json", str(out)]) == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["ok"] is True and len(data["results"]) > 60
    assert {r["solver"] for r in data["results"]} >= {e.id for e in registry.supported()}
    assert "bestanden" in capsys.readouterr().out
    missing_reason = main(["--accept-baseline", "--baseline", str(tmp_path / "b.json")])
    assert missing_reason == 2


def test_validation_matrix_files_are_current(run) -> None:  # type: ignore[no-untyped-def]
    docs = ROOT / "docs" / "application"
    assert (docs / "VALIDATION_MATRIX.md").read_text(encoding="utf-8") == matrix_markdown(run)
    assert json.loads((docs / "VALIDATION_MATRIX.json").read_text(encoding="utf-8")) == json.loads(json.dumps(matrix_data(run)))


def test_experimental_models_never_take_the_favourite_spot(tmp_path: Path) -> None:
    library = ComponentLibrary()
    result = automatic_design(AutomaticDesignRequest(max_width_m=0.3, max_height_m=0.5, max_depth_m=0.4), library)
    assert result.designs and trust_of(result.designs[0].project.enclosure.enclosure_type) is not TrustLevel.EXPERIMENTAL
    for design in result.designs:
        experimental = trust_of(design.project.enclosure.enclosure_type) is TrustLevel.EXPERIMENTAL
        assert experimental == ("experimentell" in design.label)  # never silent


def test_export_carries_the_trust_status(tmp_path: Path) -> None:
    bundle = solve_family("transmission_line_open")
    package = export_project_package(bundle, tmp_path)
    record = json.loads((package / "modellvertrauen.json").read_text(encoding="utf-8"))
    assert record["trust"] == "EXPERIMENTAL" and record["limitations"] and record["sources"]
    assert "Modellvertrauen: Experimentell" in (package / "projektzusammenfassung.txt").read_text(encoding="utf-8")


def test_project_without_solver_metadata_still_loads() -> None:
    from lautsprecher_konstruktion.project.demo import demo_project
    from lautsprecher_konstruktion.project.models import SpeakerProject
    data = json.loads(demo_project().model_dump_json())
    assert "solver" not in " ".join(data)  # nothing about solvers is stored in projects, so old files stay valid
    assert SpeakerProject.model_validate(data).enclosure.enclosure_type


# --- UI -----------------------------------------------------------------------------------------------------------

def test_chips_and_banner_warn_about_experimental_models_only() -> None:
    from lautsprecher_konstruktion.services.variant_metrics import chips_for
    from lautsprecher_konstruktion.ui.status_banner import banner
    result = automatic_design(AutomaticDesignRequest(max_width_m=0.3, max_height_m=0.5, max_depth_m=0.4), ComponentLibrary())
    solid = result.designs[0]
    assert "Experimentelles Modell" not in [c.text for c in chips_for(solid)]
    assert "experimentell" not in banner(solid)[1]
    shaky = replace(solid, project=solid.project.model_copy(update={"enclosure": solid.project.enclosure.model_copy(
        update={"enclosure_type": "horn_exponential"})}))
    assert "Experimentelles Modell" in [c.text for c in chips_for(shaky)]
    role, text = banner(shaky)
    assert "experimentelles Modell" in text and role == "warning"


def test_trust_dialog_lists_all_solvers_and_runs_on_request() -> None:
    from lautsprecher_konstruktion.ui.trust_dialog import TrustDialog, solver_detail_html
    QApplication.instance() or QApplication([])
    dialog = TrustDialog()
    assert dialog.table.rowCount() == 29 and dialog.run is None
    assert "nicht geprüft" in dialog.table.item(0, 3).text()
    html = solver_detail_html(SOLVER_DESCRIPTORS["horn_tapped"], dialog.cases, None)
    for needed in ("Experimentell", "Quellen", "Bekannte Grenzen", "Referenzfälle"):
        assert needed in html
    dialog._finished(run_cases(dialog.cases))
    assert dialog.run is not None and "bestanden" in dialog.table.item(0, 3).text()
    assert dialog.status.text().startswith("Alle Referenzfälle bestanden")


def test_details_text_names_the_trust_level() -> None:
    from lautsprecher_konstruktion.ui.result_text import details_html
    result = automatic_design(AutomaticDesignRequest(max_width_m=0.3, max_height_m=0.5, max_depth_m=0.4), ComponentLibrary())
    html = details_html(result.designs[0], 0.0)
    assert "Modellvertrauen" in html and "Wichtigste Grenze" in html
