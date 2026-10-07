"""TASK-0028 visual acceptance: responsive rules, result hero, drawing workspace, sound lab, impossible state."""
import os
import re

import pytest
from PySide6.QtWidgets import QApplication, QPushButton

from lautsprecher_konstruktion.drawings.internal_dimensions_svg import (
    render_internal_dimensions_svg,
)
from lautsprecher_konstruktion.drawings.views import render_view_svg
from lautsprecher_konstruktion.services.automatic import AutomaticDesignResult, Diagnostic
from lautsprecher_konstruktion.ui.assistant_window import AssistantWindow
from lautsprecher_konstruktion.ui.diagnostics_card import DiagnosticCard, describe
from lautsprecher_konstruktion.ui.layout_rules import (
    PlannerLayout,
    planner_layout,
    secondary_plot_count,
    workspace_share,
)
from lautsprecher_konstruktion.ui.result_hero import KpiGrid, comparison_sentences
from lautsprecher_konstruktion.ui.sound_plots import PLOT_KINDS, available_plots

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])  # type: ignore[return-value]


@pytest.fixture(scope="module")
def solved(app: QApplication) -> AssistantWindow:
    window = AssistantWindow()
    window.set_reduced_motion(True)
    window.resize(1280, 720)
    window.show()
    window.demo_choice.setCurrentIndex(1)
    window._demo()
    window.create_design()
    assert window.worker is not None
    window.worker.wait(240000)
    app.processEvents()
    assert window.designs
    return window


# --- pure responsive rules ---------------------------------------------------------------------------

def test_planner_rules_by_state_and_width() -> None:
    start = planner_layout(1280, has_result=False, view="other")
    assert start.open and start.width <= 0.38 * 1280 + 1 and start.width >= 320  # max. 38 % of the width at start
    assert planner_layout(1280, has_result=True, view="other") == PlannerLayout(False, 0)
    assert planner_layout(1599, has_result=True, view="other").open is False
    assert planner_layout(1600, has_result=True, view="other") == PlannerLayout(True, 360)
    assert planner_layout(1920, has_result=True, view="drawings") == PlannerLayout(False, 0)  # drawing workspace
    assert planner_layout(1280, has_result=True, view="other", user_open=True) == PlannerLayout(True, 360)
    assert planner_layout(1920, has_result=True, view="other", user_open=False) == PlannerLayout(False, 0)


@pytest.mark.parametrize("width", [1280, 1366, 1600, 1920])
def test_workspace_gets_at_least_65_percent_after_a_result(width: int) -> None:
    layout = planner_layout(width, has_result=True, view="other")
    assert workspace_share(width, layout) >= 0.65


def test_secondary_plot_count_by_width() -> None:
    assert secondary_plot_count(1280) == 1 and secondary_plot_count(1699) == 1 and secondary_plot_count(1920) == 2


# --- widgets ------------------------------------------------------------------------------------------

def test_kpi_grid_holds_six_cards_with_tooltips(app: QApplication) -> None:
    grid = KpiGrid(("A", "B", "C", "D", "E", "F"))
    grid.set_value("A", "220 mm", "Hinweis")
    assert grid.value("A") == "220 mm" and len(grid.keys()) == 6
    grid.clear()
    assert grid.value("A") == "–"


def test_diagnostic_card_buttons_emit_verified_changes(app: QApplication) -> None:
    card = DiagnosticCard()
    seen: list[tuple[str, float]] = []
    card.apply.connect(lambda field, value: seen.append((field, value)))
    result = AutomaticDesignResult(
        "impossible", (), ("Maximales Brutto-Innenvolumen 14 l.",), ("Klangprofil lockern.",), 10,
        (Diagnostic("depth", "Die Tiefe reicht für das benötigte Volumen nicht", 310.0, 360.0, "mm",
                    "max_depth", 365.0, "Tiefe auf 365 mm setzen"),
         Diagnostic("f3", "Der gewünschte Tiefbass ist nicht erreichbar", 20.0, 54.0, "Hz", "target_f3", 54.0,
                    "Ziel-F3 auf 54 Hz setzen")))
    card.show_result(result)
    assert card.buttons_text() == ["+ Tiefe auf 365 mm setzen", "+ Ziel-F3 auf 54 Hz setzen"]
    assert "verfügbar 310 mm" in card.main.text() and "benötigt 360 mm" in card.main.text()
    card.action_buttons[0].click()
    assert seen == [("max_depth", 365.0)]
    assert describe(result.diagnostics[1]) == ("gewünscht 20 Hz", "erreichbar 54 Hz")


def test_diagnostic_card_without_single_cause_lists_generic_changes(app: QApplication) -> None:
    card = DiagnosticCard()
    card.show_result(AutomaticDesignResult("impossible", (), ("Grund A",), ("Tiefe erhöhen.",), 5))
    assert "Mehrere Vorgaben" in card.main.text() and not card.action_buttons


# --- window integration -------------------------------------------------------------------------------

def test_start_state_has_guide_and_live_sketch_but_no_result_frame(app: QApplication) -> None:
    window = AssistantWindow()
    window.resize(1280, 720)
    window.show()
    assert window.start_preview.isVisible() and not window.result_body.isVisible()
    assert not window.planner_button.isVisible() and window.wizard_panel.isVisible()
    window.max_width.setValue(250)
    assert window.start_preview.width_mm == 250.0


def test_result_state_collapses_planner_and_shows_hero(solved: AssistantWindow) -> None:
    w = solved
    assert not w.wizard_panel.isVisible() and w.planner_button.isVisible()
    assert w.result_body.isVisible() and not w.start_preview.isVisible()
    assert w.variant_strip.isVisible() and w.variant_strip.count() == len(w.designs)
    assert set(w.kpi_row.keys()) == {"Maße", "Tiefbass F3", "Max-SPL", "Preis", "Datenqualität", "Warnungen"}
    assert all(w.kpi_row.value(k) != "–" for k in w.kpi_row.keys())  # noqa: SIM118
    assert w.preview.width() >= 420 and w.preview.height() >= 300
    assert w.result_body.width() >= 0.65 * w.width() - 40


def test_variant_strip_switches_variant_and_hero(solved: AssistantWindow) -> None:
    w = solved
    w.variant_strip._buttons[1].click()
    assert w.variant_list.currentRow() == 1
    assert w.selected_title.text() == w.designs[1].label
    assert "Warum besser oder schlechter als A?" in w.variant_why.text()
    w.variant_strip._buttons[0].click()
    assert "Warum empfohlen?" in w.variant_why.text()


def test_variant_cards_show_decision_facts_without_horizontal_scroll(solved: AssistantWindow) -> None:
    w = solved
    texts = [b.text() for b in w.variant_cards._buttons]
    assert all("Max-SPL" in t and "Platten" in t and "Hub" in t and "Datenabdeckung" in t for t in texts)
    assert w.comparison.isHidden()  # the table is the detail mode, not the default
    assert w.variant_cards.width() <= w.tabs.width()


def test_comparison_sentences_name_calculated_differences_only(solved: AssistantWindow) -> None:
    lines = comparison_sentences(solved.designs[2], solved.designs[0])
    assert lines and all(isinstance(line, str) for line in lines)
    assert any(line.startswith(("Tiefbass", "Größe", "Bauart")) for line in lines)
    same = comparison_sentences(solved.designs[0], solved.designs[0])
    assert same == ["Praktisch gleichwertig zur Empfehlung bei den berechneten Kennwerten."]


def test_drawing_workspace_closes_planner_and_offers_simple_toolbar(solved: AssistantWindow) -> None:
    w = solved
    w.planner_button.setChecked(True)  # user opened it on another tab
    index = next(i for i in range(w.tabs.count()) if w.tabs.tabText(i) == "Zeichnungen")
    w.tabs.setCurrentIndex(index)
    assert not w.wizard_panel.isVisible() and not w.state.isVisible()
    labels = [b.text() for b in w.svg.findChildren(QPushButton)]
    assert labels == ["Einpassen", "100 %", "−", "+", "Vollbild"]  # one clear set, no five fit variants
    assert w.svg.zoom_percent.value() > 0
    assert not w.print_sheet.isChecked()
    assert w.drawing_tabs.tabText(3) == "Innenaufbau" and w.drawing_tabs.isTabVisible(3)
    w.tabs.setCurrentIndex(0)
    assert w.state.isVisible()


def test_print_sheet_toggle_switches_drawing_set(solved: AssistantWindow) -> None:
    w = solved
    w.tabs.setCurrentIndex(next(i for i in range(w.tabs.count()) if w.tabs.tabText(i) == "Zeichnungen"))
    w.print_sheet.setChecked(True)
    assert [w.drawing_tabs.tabText(i) for i in (0, 1, 2)] == ["Gesamtblatt", "Maßblatt", "Innenblatt"]
    assert not w.drawing_tabs.isTabVisible(3)
    w.print_sheet.setChecked(False)
    assert [w.drawing_tabs.tabText(i) for i in (0, 1, 2)] == ["Front", "Seite", "Schnitt"]


def test_screen_views_are_tight_and_label_dimensions(solved: AssistantWindow) -> None:
    bundle = solved.designs[0].bundle
    front = render_view_svg(bundle, "front")
    assert re.search(r"\d+ mm</text>", front) and "x " in front and "Material" in front
    vb = [float(v) for v in re.search(r'viewBox="0 0 (\d+) (\d+)"', front).groups()]  # type: ignore[union-attr]
    assert vb[0] < 800  # tight canvas instead of the former fixed 800 x 820 sheet
    screen = render_internal_dimensions_svg(bundle, screen=True)
    printed = render_internal_dimensions_svg(bundle)
    h_screen = float(re.search(r'viewBox="[\d.]+ [\d.]+ [\d.]+ ([\d.]+)"', screen).group(1))  # type: ignore[union-attr]
    h_print = float(re.search(r'viewBox="[\d.]+ [\d.]+ [\d.]+ ([\d.]+)"', printed).group(1))  # type: ignore[union-attr]
    assert h_screen < 0.6 * h_print  # cropped view: tables and the title block lie outside the viewBox
    assert "ACK Studio" in printed


def test_sound_lab_shows_one_selectable_secondary_plot(solved: AssistantWindow) -> None:
    w = solved
    avail = available_plots(w.designs[0].bundle)
    assert [k for k, _ in PLOT_KINDS] == ["excursion", "port", "impedance", "delay", "crossover", "dsp"]
    assert avail["dsp"][0] is False and "nicht Teil" in avail["dsp"][1]
    w._redraw_simulation()
    assert len(w.figure.axes) == 1
    assert not w.plot_buttons["dsp"].isEnabled() and w.plot_buttons["dsp"].toolTip()
    w.plot_buttons["delay"].click()
    assert w.figure.axes[0].get_title() == "Gruppenlaufzeit"
    assert w.target_curve.maximumHeight() >= 500  # the main graph stays the dominant area


def test_resize_never_starts_a_calculation(solved: AssistantWindow, monkeypatch: pytest.MonkeyPatch,
                                           app: QApplication) -> None:
    calls: list[int] = []
    monkeypatch.setattr(AssistantWindow, "create_design", lambda self: calls.append(1))
    solved.resize(1366, 768)
    solved.resize(1920, 1080)
    app.processEvents()
    solved._resize_timer.timeout.emit()
    assert calls == []
    solved.resize(1280, 720)


def test_suggestion_enters_value_and_recalculates(app: QApplication, monkeypatch: pytest.MonkeyPatch) -> None:
    window = AssistantWindow()
    calls: list[int] = []
    monkeypatch.setattr(AssistantWindow, "create_design", lambda self: calls.append(1))
    window._apply_suggestion("max_depth", 365.0)
    assert window.max_depth.value() == 365.0 and calls == [1]
    window._apply_suggestion("target_f3", 54.0)
    assert window.options.isChecked() and window.target_f3.value() == 54.0
    window._apply_suggestion("unknown_field", 1.0)
    assert calls == [1, 1]


def test_impossible_state_shows_diagnosis_and_disables_result_tabs(app: QApplication) -> None:
    window = AssistantWindow()
    window.resize(1280, 720)
    window.show()
    window.demo_choice.setCurrentIndex(5)
    window._demo()
    window.create_design()
    assert window.worker is not None
    window.worker.wait(240000)
    app.processEvents()
    assert window.diagnostic.isVisible() and not window.result_body.isVisible()
    enabled = {window.tabs.tabText(i): window.tabs.isTabEnabled(i) for i in range(window.tabs.count())}
    assert enabled["Varianten"] is False and enabled["Zeichnungen"] is False and enabled["Fertigung"] is False
    assert enabled["Planen"] is True
    assert window.wizard_panel.isVisible()  # inputs stay reachable to fix the cause
    assert not window.export_button.isEnabled()
    window._failed("Test")
    assert not window.diagnostic.isVisible() and all(
        window.tabs.isTabEnabled(i) for i in range(window.tabs.count()))


def test_error_state_offers_retry_and_diagnosis_copy_without_stale_results(app: QApplication) -> None:
    window = AssistantWindow()
    window.resize(1280, 720)
    window.show()
    window._failed("Rechenkern abgestürzt")
    assert window.error_actions.isVisible() and not window.designs
    assert not window.result_body.isVisible() and not window.variant_strip.isVisible()
    window._copy_diagnosis()
    assert "Rechenkern abgestürzt" in QApplication.clipboard().text()
    window.create_design()  # retry starts a new calculation and hides the error actions
    assert not window.error_actions.isVisible()
    assert window.worker is not None
    window.worker.cancel_event.set()
    window.worker.wait(240000)


def test_drawings_use_longhand_font_properties_because_qt_svg_ignores_the_shorthand() -> None:
    """Qt's SVG renderer silently ignores `font: 13px ...`; every drawing text would render tiny in the viewer."""
    import glob
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[1] / "src" / "lautsprecher_konstruktion"
    offenders = []
    for path in [*glob.glob(str(root / "drawings" / "*.py")), *glob.glob(str(root / "export" / "*.py"))]:
        text = pathlib.Path(path).read_text(encoding="utf-8")
        if re.search(r"[{;\s']font:\s*(bold|\d)", text):
            offenders.append(pathlib.Path(path).name)
    assert not offenders, offenders


def test_front_view_text_is_rendered_at_reading_size(solved: AssistantWindow) -> None:
    from PySide6.QtGui import QColor, QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer

    svg = render_view_svg(solved.designs[0].bundle, "front")
    renderer = QSvgRenderer(svg.encode("utf-8"))
    size = renderer.defaultSize()
    image = QImage(size.width(), size.height(), QImage.Format.Format_RGB32)
    image.fill(QColor("white"))
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()
    # the title is 28 px high text in the top-left corner: it must cover a clearly taller pixel band than 12 px
    rows = [y for y in range(60) if any(image.pixelColor(x, y).lightness() < 120 for x in range(30, 200))]
    assert rows and rows[-1] - rows[0] >= 18
