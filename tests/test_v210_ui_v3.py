import os
from pathlib import Path

import pytest
from pydantic import ValidationError
from PySide6.QtWidgets import QApplication

from lautsprecher_konstruktion.services.automatic import AutomaticDesignRequest
from lautsprecher_konstruktion.ui.assistant_window import AssistantWindow
from lautsprecher_konstruktion.ui.cabinet_preview import CabinetPreview
from lautsprecher_konstruktion.ui.collapsible import Collapsible
from lautsprecher_konstruktion.ui.variant_cards import CardData, VariantCards
from lautsprecher_konstruktion.ui.zoom_svg import ZoomableSvgView

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])  # type: ignore[return-value]


@pytest.fixture(scope="module")
def solved(app: QApplication) -> AssistantWindow:
    window = AssistantWindow()
    window.set_reduced_motion(True)
    window.resize(1500, 920)
    window.show()
    window._load_example()
    window.create_design()
    assert window.worker is not None
    window.worker.wait(180000)
    app.processEvents()
    return window


def test_start_page_has_steps_and_live_sketch_and_no_result_frame(app: QApplication) -> None:
    window = AssistantWindow()
    window.show()
    assert window.result_stack.currentIndex() == 0 and not window.actions_bar.isVisible()
    window.max_width.setValue(280)
    window.max_height.setValue(600)
    assert window.start_preview._size_mm == (280.0, 600.0, window.max_depth.value())
    assert not window.load_button.isVisible()
    window.close()


def test_result_view_shows_preview_key_figures_cards_and_collapsed_details(solved: AssistantWindow) -> None:
    w = solved
    assert w.result_stack.currentIndex() == 1 and w.actions_bar.isVisible()
    assert w.variant_cards.count() == len(w.designs) >= 2
    assert w.preview.element_count() >= 2 and w.kpi_row.isVisible()
    assert set(w.kpis) == {"Maße", "Tiefbass F3", "Preisstatus", "Datenqualität", "Prüfstatus"}
    assert all(value.text() for value, _ in w.kpis.values())
    assert not w.why_section.is_expanded() and not w.details_section.is_expanded()
    w.why_section.button.setChecked(True)
    assert w.why_section.is_expanded() and w.why.isVisible() and "Warum empfohlen" in w.why.toPlainText()
    w.why_section.button.setChecked(False)
    assert not w.why.isVisible()


def test_cards_select_variants_and_never_call_unknown_prices_cheap(solved: AssistantWindow) -> None:
    w = solved
    w.variant_cards._cards[1].clicked.emit(1)
    assert w.variant_list.currentRow() == 1
    assert w.variant_cards._cards[1].property("selected") is True
    unknown = [d for d in w.designs if d.total_price_eur is None]
    if unknown:
        assert "nicht vergleichbar" in " ".join(
            label.text() for card in w.variant_cards._cards for label in card.findChildren(type(w.state)))
        assert "nicht als günstiger" in w.why.toPlainText() or w.variant_list.currentRow() != w.designs.index(unknown[0])


def test_score_is_marked_as_partial_and_lists_unrated_criteria(solved: AssistantWindow) -> None:
    solved.variant_list.setCurrentRow(0)
    text = solved.why.toPlainText()
    assert "Teilbewertung" in text and "Keine Qualitätsfreigabe" in text


def test_input_errors_are_tied_to_fields_and_cleared_on_edit(app: QApplication) -> None:
    window = AssistantWindow()
    with pytest.raises(ValidationError) as caught:
        AutomaticDesignRequest(max_width_m=-1)
    window._show_input_errors(caught.value)
    assert window.max_width.property("invalid") is True
    assert "Breite" in window.state.text() and "Bitte Eingaben prüfen" in window.state.text()
    window.max_width.setValue(310)
    assert window.max_width.property("invalid") is False


def test_reading_mode_zoom_percent_and_focus_mode(app: QApplication, solved: AssistantWindow) -> None:
    w = solved
    w.reading_button.setChecked(True)
    assert all(v._reading for v in (w.svg, w.dimension_svg, w.internal_svg, w.panel_svg))
    w.svg.zoom_percent.setValue(75)
    assert abs(w.svg._scale - 0.75) < 1e-9 and not w.svg._reading
    w.reading_button.setChecked(False)
    assert w.svg._fit and "Einpassen" in w.svg.zoom_label.text()
    w.focus_button.setChecked(True)
    assert w.reading_button.isChecked() and not w.wizard_panel.isVisible()
    w.focus_button.setChecked(False)
    assert "×" in w.dimension_strip.text() and "Innen" in w.dimension_strip.text()


def test_toast_confirms_with_path_and_open_action(solved: AssistantWindow, tmp_path: Path) -> None:
    solved._show_toast("Projekt gespeichert", tmp_path / "x.json")
    assert solved.toast.isVisible() and solved.toast_open.isVisible()
    assert solved.toast_label.text().startswith("✓")


def test_failure_after_success_returns_to_start_and_locks_export(app: QApplication) -> None:
    window = AssistantWindow()
    window.show()
    window._load_example()
    window.create_design()
    assert window.worker is not None
    window.worker.wait(180000)
    app.processEvents()
    assert window.result_stack.currentIndex() == 1
    window._failed("Test")
    assert window.result_stack.currentIndex() == 0 and window.variant_cards.count() == 0
    assert not window.export_button.isEnabled() and not window.preview.element_count()
    window.close()


def test_preview_cards_collapsible_units(app: QApplication) -> None:
    preview = CabinetPreview()
    preview.resize(300, 300)
    assert preview.grab().width() == 300  # paints without data
    preview.set_limits(300, 500, 400)
    assert preview.grab().width() == 300
    cards = VariantCards()
    cards.set_cards([CardData("A", "Geschlossen", "200 × 300 × 150", 60.0, None, "✓ keine Hinweise", "–", "X")])
    assert cards.count() == 1
    cards.select(0)
    cards.clear()
    assert cards.count() == 0
    from PySide6.QtWidgets import QLabel
    body = QLabel("x")
    box = Collapsible("Titel", body, reduced_motion=lambda: True)
    box.show()
    assert not body.isVisible()
    box.button.setChecked(True)
    assert body.isVisible() and box.button.text().startswith("▾")
    view = ZoomableSvgView()
    assert view.zoom_percent.maximum() == 500
