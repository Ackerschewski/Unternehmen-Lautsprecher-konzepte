"""TASK-0029 workstream H: manufacturing summary, grouped BOM with price badges, export format list."""
from __future__ import annotations

import os

import pytest
from PySide6.QtWidgets import QApplication

from lautsprecher_konstruktion.export.cutting import plan_cutting
from lautsprecher_konstruktion.export.summary import GROUPS, group_of, grouped, summarize
from lautsprecher_konstruktion.library.store import ComponentLibrary
from lautsprecher_konstruktion.services.automatic import (
    AutomaticDesignRequest,
    SpeakerDesign,
    automatic_design,
)
from lautsprecher_konstruktion.ui.manufacturing_view import (
    EXPORT_FORMATS,
    ExportFormatList,
    ManufacturingSummaryView,
)
from lautsprecher_konstruktion.ui.result_text import bom_html
from lautsprecher_konstruktion.ui.tokens import theme

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def design() -> SpeakerDesign:
    result = automatic_design(AutomaticDesignRequest(max_width_m=0.3, max_height_m=0.5, max_depth_m=0.4), ComponentLibrary())
    return result.designs[0]


def test_every_position_belongs_to_exactly_one_known_group(design: SpeakerDesign) -> None:
    groups = grouped(design.bom)
    assert [name for name, _ in groups] == [g for g in GROUPS if g in {n for n, _ in groups}]
    assert sum(len(rows) for _, rows in groups) == len(design.bom)
    assert all(group_of(item) in GROUPS for item in design.bom)
    assert any(name == "Gehäuse" for name, _ in groups) and any(name == "Chassis" for name, _ in groups)


def test_summary_numbers_come_from_bom_plan_and_weight(design: SpeakerDesign) -> None:
    plan = plan_cutting(design.bundle)
    summary = summarize(design, plan)
    assert summary.positions == len(design.bom) and summary.pieces == sum(i.quantity for i in design.bom)
    assert summary.sheets == plan.sheet_count and summary.waste_percent == pytest.approx(plan.waste_percent)
    labels = [r[0] for r in summary.rows()]
    assert labels == ["Bekannte Kosten", "Geschätzte Kosten", "Fehlende Preise", "Materialplatten", "Gehäusegewicht", "Bauteile"]
    unplanned = summarize(design, None)
    assert unplanned.unplaced_parts == 0


def test_summary_with_unpriced_items_states_missing_count(design: SpeakerDesign) -> None:
    from dataclasses import replace
    stripped = replace(design, bom=tuple(replace(i, unit_price_eur=None, price_kind="fehlt") for i in design.bom))
    rows = {r[0]: r for r in summarize(stripped, None).rows()}
    assert rows["Bekannte Kosten"][1] == "–"
    assert rows["Fehlende Preise"][1] == f"{len(design.bom)} von {len(design.bom)}"


def test_bom_html_is_grouped_with_badges_and_no_invented_prices(design: SpeakerDesign) -> None:
    html = bom_html(design, theme("light"))
    for name, _ in grouped(design.bom):
        assert f"<b>{name}</b>" in html
    assert "Preisart" in html and "● " in html
    from dataclasses import replace
    stripped = replace(design, bom=tuple(replace(i, unit_price_eur=None, price_kind="fehlt") for i in design.bom))
    assert "Preis fehlt" in bom_html(stripped, theme("light"))


def test_widgets_render(design: SpeakerDesign) -> None:
    QApplication.instance() or QApplication([])
    view = ManufacturingSummaryView()
    view.update_from(design, plan_cutting(design.bundle))
    assert all(view.value(key) != "–" for key in ("Materialplatten", "Bauteile"))
    view.update_from(None, None)
    assert view.value("Bauteile") == "–"
    formats = ExportFormatList()
    assert len(formats.rows) == len(EXPORT_FORMATS)
    step = next(r for r in formats.rows if r[0].text() == "STEP")
    assert "noch nicht" in step[2].text()  # announced, never faked


def test_component_text_translates_whole_words_only() -> None:
    from lautsprecher_konstruktion.presentation import component_text
    assert component_text("Demo 165 mm Midwoofer") == "Demo 165 mm Midwoofer"
    assert component_text("woofer zobel") == "Tieftöner-Zobel"


def test_key_figure_cards_lead_to_their_explanation() -> None:
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    from lautsprecher_konstruktion.ui.assistant_window import AssistantWindow
    QApplication.instance() or QApplication([])
    window = AssistantWindow()
    window.demo_choice.setCurrentIndex(1)
    window._demo()
    window.create_design()
    window.worker.wait(240000)
    for _ in range(40):
        QApplication.processEvents()
    seen: list[str] = []
    window.kpi_row.activated.connect(seen.append)
    card = window.kpi_row._cards["Preis"]
    QTest.mouseClick(card, Qt.MouseButton.LeftButton)
    assert seen == ["Preis"] and window.tabs.currentIndex() == 4
    window.tabs.setCurrentIndex(0)
    QTest.mouseClick(window.kpi_row._cards["Warnungen"], Qt.MouseButton.LeftButton)
    assert window.details_toggle.isChecked()
    assert window.kpi_row.value("Preis").endswith("bepreist") or "€" in window.kpi_row.value("Preis")
