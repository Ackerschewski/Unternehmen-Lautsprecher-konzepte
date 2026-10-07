"""TASK-0029 workstream F: variant metrics, chips and mini comparison with price truth."""
from __future__ import annotations

import os
from dataclasses import replace

import pytest
from PySide6.QtWidgets import QApplication

from lautsprecher_konstruktion.library.store import ComponentLibrary
from lautsprecher_konstruktion.services.automatic import (
    AutomaticDesignRequest,
    SpeakerDesign,
    automatic_design,
)
from lautsprecher_konstruktion.services.variant_metrics import (
    Tone,
    chips_for,
    comparison_rows,
    data_coverage_percent,
    metrics_of,
)
from lautsprecher_konstruktion.ui.variant_view import ComparisonBars, VariantCards, variant_tag

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])  # type: ignore[return-value]


@pytest.fixture(scope="module")
def designs() -> tuple[SpeakerDesign, ...]:
    result = automatic_design(AutomaticDesignRequest(max_width_m=0.3, max_height_m=0.5, max_depth_m=0.4), ComponentLibrary())
    assert len(result.designs) >= 2
    return result.designs


def _unpriced(design: SpeakerDesign) -> SpeakerDesign:
    return replace(design, bom=tuple(replace(i, unit_price_eur=None, price_kind="fehlt") for i in design.bom))


def test_chips_cover_all_decision_metrics(designs: tuple[SpeakerDesign, ...]) -> None:
    keys = [c.key for c in chips_for(designs[0])]
    for needed in ("size", "f3", "spl", "hub", "price", "coverage", "effort", "warnings"):
        assert needed in keys


def test_coverage_is_the_mean_of_three_defined_shares(designs: tuple[SpeakerDesign, ...]) -> None:
    d = designs[0]
    m = metrics_of(d)
    assert 0 <= m.coverage_percent <= 100
    assert data_coverage_percent(d, m.price) == m.coverage_percent
    stripped = _unpriced(d)
    assert metrics_of(stripped).coverage_percent < m.coverage_percent or m.price.coverage_percent == 0


def test_unpriced_variant_gets_no_price_ranking_and_no_cheaper_chip(designs: tuple[SpeakerDesign, ...]) -> None:
    mixed = (designs[0], _unpriced(designs[1]))
    price_row = next(r for r in comparison_rows(mixed) if r.key == "price")
    assert price_row.disabled_reason and all(v is None for v in price_row.values)
    assert "Günstiger als A" not in [c.text for c in chips_for(mixed[1], mixed[0])]
    assert variant_tag(1, mixed[1], mixed[0]) != "Günstiger"
    chip = next(c for c in chips_for(mixed[1]) if c.key == "price")
    assert chip.tone is Tone.WARN and "bepreist" in chip.text or "Preis unbekannt" in chip.text


def test_bars_are_normalised_and_best_value_is_longest(designs: tuple[SpeakerDesign, ...]) -> None:
    rows = comparison_rows(designs)
    for row in rows:
        known = [v for v in row.values if v is not None]
        assert all(0.0 < v <= 1.0 for v in known)
    compact = next(r for r in rows if r.key == "compact")
    volumes = [metrics_of(d).volume_l for d in designs]
    assert compact.values.index(max(v for v in compact.values if v is not None)) == volumes.index(min(volumes))


def test_cards_and_bars_render_for_all_variants(app: QApplication, designs: tuple[SpeakerDesign, ...]) -> None:
    cards = VariantCards()
    cards.resize(1000, 300)
    cards.set_designs(designs)
    assert len(cards._buttons) == len(designs)
    emitted: list[int] = []
    cards.selected.connect(emitted.append)
    cards._buttons[1].clicked.emit()
    assert emitted == [1]
    assert all("Datenabdeckung" in b.text() for b in cards._buttons)
    bars = ComparisonBars()
    bars.resize(700, 260)
    bars.set_designs(designs)
    bars.select(1)
    assert bars.grab().width() == 700


def test_recommendation_note_explains_a_favourite_with_more_warnings(designs: tuple[SpeakerDesign, ...]) -> None:
    from lautsprecher_konstruktion.services.variant_metrics import (
        coverage_label,
        recommendation_note,
    )
    assert coverage_label(95) == "vollständig" and coverage_label(75) == "gut"
    assert coverage_label(50) == "eingeschränkt" and coverage_label(10) == "unvollständig"
    first = designs[0]
    noisy = replace(first, bundle=replace(first.bundle, warnings=("a", "b")))
    calm = replace(designs[1], bundle=replace(designs[1].bundle, warnings=()))
    note = recommendation_note((noisy, calm))
    assert note is not None and "2 Hinweis" in note and noisy.label in note
    assert recommendation_note((calm, noisy)) is None  # a calmer favourite needs no excuse
