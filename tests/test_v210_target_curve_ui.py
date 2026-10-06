"""Regression tests for TASK-0026: software theme and target-curve workflow."""
from __future__ import annotations

import os

import pytest
from PySide6.QtWidgets import QApplication

from lautsprecher_konstruktion.drawings.style import (
    dimension_css,
    internal_css,
    master_css,
    panel_css,
)
from lautsprecher_konstruktion.ui import tokens
from lautsprecher_konstruktion.ui.assistant_window import AssistantWindow
from lautsprecher_konstruktion.ui.target_curve import TargetCurveEditor

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])  # type: ignore[return-value]


def test_software_is_default_product_world() -> None:
    tokens.set_area(tokens.DEFAULT_AREA)
    assert tokens.DEFAULT_AREA == "software"
    assert tokens.theme("light")["accent"] == "#172d46"
    dark = tokens.theme("dark")
    assert dark["accent"] == "#adcadb"
    assert dark["background"] != dark["surface"] != dark["panel"]
    assert dark["constructionAccent"] != dark["accent"]


def test_target_curve_editor_starts_neutral_and_supports_numeric_edit(app: QApplication) -> None:
    editor = TargetCurveEditor("light")
    points = editor.points()
    assert points[0] == (20.0, 0.0)
    assert points[-1] == (20000.0, 0.0)
    assert all(level == 0.0 for _, level in points)

    editor.point.setCurrentIndex(2)
    editor.level.setValue(4.5)
    assert editor.points()[2] == (50.0, 4.5)
    editor.undo()
    assert editor.points()[2] == (50.0, 0.0)


def test_assistant_can_use_target_curve_as_design_request(app: QApplication) -> None:
    window = AssistantWindow()
    window.design_method.setCurrentIndex(window.design_method.findData("target_curve"))
    window.target_curve.point.setCurrentIndex(1)
    window.target_curve.level.setValue(3.0)
    request = window._request()
    assert request.target_curve_points is not None
    assert request.target_curve_points[1] == (31.5, 3.0)
    assert window.tabs.currentWidget() is window.sound_tab
    assert "Zielkurve" in window.create_button.text()


def test_drawing_css_uses_one_ack_studio_palette() -> None:
    css = "\n".join((master_css(), dimension_css(), internal_css(), panel_css()))
    assert "#172d46" in css
    assert "#4c6a83" in css
    assert "#471b28" in css
    for obsolete in ("#193448", "#007fa5", "#bf503a", "#16749a", "#0879a6"):
        assert obsolete not in css
