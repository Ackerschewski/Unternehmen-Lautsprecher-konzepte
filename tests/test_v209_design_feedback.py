"""Design feedback of 2026-10-06: dark theme, stale results, line geometry, reduced motion."""
import os

import pytest
from PySide6.QtWidgets import QApplication

from lautsprecher_konstruktion.project.demo import demo_project
from lautsprecher_konstruktion.project.models import CrossoverConfig
from lautsprecher_konstruktion.services.design import calculate_project
from lautsprecher_konstruktion.ui import tokens
from lautsprecher_konstruktion.ui.theme import chart_rc, stylesheet

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])  # type: ignore[return-value]


@pytest.mark.parametrize("area", sorted(tokens.AREAS))
def test_dark_theme_meets_contrast_in_every_area(area: str) -> None:
    tokens.set_area(area)
    try:
        t = tokens.theme("dark")
        assert tokens.contrast(t["textPrimary"], t["background"]) >= 7
        assert tokens.contrast(t["textSecondary"], t["panel"]) >= 4.5
        assert tokens.contrast(t["accent"], t["background"]) >= 4.5
        assert tokens.contrast(t["onAccent"], t["accent"]) >= 4.5
        assert tokens.contrast(t["textPrimary"], t["band"]) >= 4.5
    finally:
        tokens.set_area(tokens.DEFAULT_AREA)


def test_dark_stylesheet_and_charts_use_dark_ground() -> None:
    assert tokens.DARK_PAPER in stylesheet("dark")
    assert chart_rc("dark")["figure.facecolor"] == tokens.DARK_PAPER
    assert chart_rc("light")["figure.facecolor"] == tokens.PAPER


def test_theme_choice_is_remembered_and_applied(app: QApplication) -> None:
    from lautsprecher_konstruktion.ui.assistant_window import AssistantWindow

    window = AssistantWindow()
    window.set_theme_choice("dark")
    assert window.mode == "dark" and tokens.DARK_PAPER in window.styleSheet()
    assert AssistantWindow().theme_choice == "dark"
    window.set_theme_choice("light")
    assert window.mode == "light"
    with pytest.raises(ValueError):
        window.set_theme_choice("sepia")


def test_failure_clears_all_result_views(app: QApplication) -> None:
    from lautsprecher_konstruktion.ui.assistant_window import AssistantWindow

    window = AssistantWindow()
    window.demo_choice.setCurrentIndex(1)
    window._demo()
    window.create_design()
    assert window.worker is not None
    window.worker.wait(120000)
    app.processEvents()
    assert window.designs and window.variant_list.count()
    window._failed("Test")
    assert not window.designs and window.variant_list.count() == 0
    assert window.comparison.rowCount() == 0 and window.details.toPlainText() == ""
    assert not window.export_button.isEnabled() and not window.save_button.isEnabled()
    assert not window.kpi_row.isVisible()


def test_focus_mode_collapses_inputs_and_respects_reduced_motion(app: QApplication) -> None:
    from lautsprecher_konstruktion.ui.assistant_window import AssistantWindow

    window = AssistantWindow()
    window.set_reduced_motion(True)
    window.show()
    window.focus_button.setChecked(True)
    assert not window.wizard_panel.isVisible()
    window.focus_button.setChecked(False)
    assert window.wizard_panel.isVisible()
    assert window.split.sizes()[0] > 300
    window.set_reduced_motion(False)


def test_transmission_line_follows_driver_area_with_chamber_behind_driver() -> None:
    project = demo_project()
    cfg = project.enclosure.model_copy(update={
        "enclosure_type": "transmission_line_open", "target_volume_l": 120.0, "tuning_hz": 60.0,
        "external_height_mm": 1200.0, "external_width_mm": 400.0, "brace_quantity": 0})
    bundle = calculate_project(project.model_copy(update={
        "enclosure": cfg, "front_elements": (), "tweeter_name": "",
        "crossover": CrossoverConfig(enabled=False)}))
    line = bundle.folded_line
    assert line is not None and project.driver.sd_m2
    for area in line.channel_areas_m2[1:]:
        assert 1.0 * project.driver.sd_m2 - 1e-9 <= area <= 1.5 * project.driver.sd_m2 + 1e-9
    assert line.channel_heights_m[0] > 2 * line.channel_heights_m[1]  # driver chamber, narrow line
    assert line.estimated_quarter_wave_hz == pytest.approx(60.0, rel=0.15)
