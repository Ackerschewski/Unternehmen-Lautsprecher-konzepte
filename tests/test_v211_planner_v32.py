"""Regression tests for the V3.2 planner information architecture and sound lab."""
from __future__ import annotations

import os
import re
from pathlib import Path

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from lautsprecher_konstruktion.project.demo import demo_project
from lautsprecher_konstruktion.project.models import SpeakerProject
from lautsprecher_konstruktion.services.automatic import _target_curve_fit
from lautsprecher_konstruktion.ui.assistant_window import AssistantWindow
from lautsprecher_konstruktion.ui.target_curve import TargetCurveEditor

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])  # type: ignore[return-value]


def test_planner_has_decision_first_navigation(app: QApplication) -> None:
    window = AssistantWindow()
    assert [window.tabs.tabText(i) for i in range(window.tabs.count())] == [
        "Planen", "Varianten", "Klang", "Zeichnungen", "Fertigung"
    ]
    assert window.save_button.isHidden() and window.load_button.isHidden()
    assert window.comparison.isHidden()
    assert window.empty_guide.isVisible() is False or window.empty_guide.text()
    assert window.method_cards.value() == "classic"
    assert window.speaker_cards.value() == "Regallautsprecher"
    assert window.profile_cards.value() == "neutral"


def test_visual_cards_drive_the_existing_request_model(app: QApplication) -> None:
    window = AssistantWindow()
    window._set_speaker_type_value("Standlautsprecher")
    window._set_profile_value("deep_bass")
    window._set_design_method_value("target_curve")
    request = window._request()
    assert request.speaker_type == "Standlautsprecher"
    assert request.sound_profile == "deep_bass"
    assert request.target_curve_points is not None
    assert window.design_method.currentData() == "target_curve"


def test_target_presets_parametric_band_and_modes(app: QApplication) -> None:
    editor = TargetCurveEditor()
    editor.preset.setCurrentIndex(editor.preset.findData("house"))
    assert editor.points()[0][1] > editor.points()[-1][1]

    before = dict(editor.points())
    editor.band_frequency.setValue(1000)
    editor.band_gain.setValue(3)
    editor.band_q.setValue(1)
    editor.apply_parametric_band()
    after = dict(editor.points())
    assert after[1000.0] > before[1000.0]
    assert editor.preset_id() == "custom"

    editor.set_analysis_mode("influence")
    assert editor.analysis_mode() == "influence"


def test_target_curve_candidate_envelope_marks_unreachable_target(app: QApplication) -> None:
    editor = TargetCurveEditor()
    frequencies = np.geomspace(20, 500, 200)
    editor.set_candidate_curves((
        (frequencies, np.zeros_like(frequencies)),
        (frequencies, np.full_like(frequencies, 2.0)),
    ))
    editor.set_points(((20.0, 0.0), (50.0, 8.0), (500.0, 0.0)))
    outside = editor.outside_envelope()
    assert outside is not None
    assert outside[0] == pytest.approx(50.0, rel=0.05)
    assert outside[1] > 0


def test_target_curve_project_state_round_trips() -> None:
    original = demo_project().model_copy(update={
        "target_curve_points": ((20.0, 3.0), (100.0, 0.0), (20000.0, -1.5)),
        "target_curve_preset": "custom",
        "target_curve_mode": "influence",
    })
    restored = SpeakerProject.model_validate_json(original.model_dump_json())
    assert restored.target_curve_points == original.target_curve_points
    assert restored.target_curve_preset == "custom"
    assert restored.target_curve_mode == "influence"
    assert restored.target_curve_schema_version == 1


def test_target_curve_fit_ignores_nan_frd_regions() -> None:
    frequencies = np.geomspace(20, 20000, 500)
    response = np.zeros_like(frequencies)
    response[frequencies < 60] = np.nan
    response[frequencies > 15000] = np.nan
    target = ((20.0, 0.0), (100.0, 0.0), (20000.0, 0.0))
    fit = _target_curve_fit(frequencies, response, target, max_hz=20000)
    assert fit is not None
    assert fit[0] == pytest.approx(100.0)
    assert fit[2] <= 15000


def test_all_svg_brand_colours_live_in_shared_drawing_style() -> None:
    colour = re.compile(r"#[0-9a-fA-F]{6}\b")
    drawings = ROOT / "src/lautsprecher_konstruktion/drawings"
    offenders = []
    for path in drawings.glob("*.py"):
        if path.name == "style.py":
            continue
        if colour.search(path.read_text(encoding="utf-8")):
            offenders.append(path.name)
    assert offenders == []
