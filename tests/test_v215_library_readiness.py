"""TASK-0029 workstream C: derived library readiness, coverage and honest data-quality text."""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from lautsprecher_konstruktion.drivers.models import Driver
from lautsprecher_konstruktion.library.coverage import coverage_markdown
from lautsprecher_konstruktion.library.readiness import Readiness, assess
from lautsprecher_konstruktion.library.store import ComponentLibrary, LibraryEntry
from lautsprecher_konstruktion.ui.library_dialog import readiness_html

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _driver(**extra: object) -> Driver:
    base: dict[str, object] = {"manufacturer": "X", "model": "Y", "fs_hz": 40, "qts": 0.4, "vas_m3": 0.05, "sd_m2": 0.012}
    base.update(extra)
    return Driver.model_validate(base)


def _entry(driver: Driver | None, **extra: object) -> LibraryEntry:
    return LibraryEntry.model_validate({"id": "t:1", "category": "drivers", "model": "Y", "driver": driver,
                                        "source": "Datenblatt", **extra})


def test_readiness_is_derived_from_the_record() -> None:
    bare = assess(_entry(_driver()))
    assert bare.ready(Readiness.ENCLOSURE)
    assert not bare.ready(Readiness.MANUFACTURING) and not bare.ready(Readiness.THREE_D)
    assert not bare.ready(Readiness.CROSSOVER) and not bare.ready(Readiness.FULLRANGE)

    mounted = assess(_entry(_driver(outer_diameter_m=0.19, cutout_diameter_m=0.15, mounting_depth_m=0.07)))
    assert mounted.ready(Readiness.MANUFACTURING) and mounted.ready(Readiness.THREE_D)


def test_crossover_and_fullrange_need_measurement_files_and_band() -> None:
    narrow = assess(_entry(_driver(), frd_file="a.frd", zma_file="a.zma"))
    assert narrow.ready(Readiness.CROSSOVER) and not narrow.ready(Readiness.FULLRANGE)
    wide = assess(_entry(_driver(min_frequency_hz=40, max_frequency_hz=18000), frd_file="a.frd", zma_file="a.zma"))
    assert wide.ready(Readiness.FULLRANGE)
    only_frd = assess(_entry(_driver(min_frequency_hz=40, max_frequency_hz=18000), frd_file="a.frd"))
    assert not only_frd.ready(Readiness.CROSSOVER) and not only_frd.ready(Readiness.FULLRANGE)


def test_pricing_ready_requires_price_and_check_date() -> None:
    assert not assess(_entry(None, price_eur=10.0)).ready(Readiness.PRICING)
    assert assess(_entry(None, price_eur=10.0, price_checked_on=date(2026, 10, 2))).ready(Readiness.PRICING)


def test_coverage_percent_counts_defined_fields_only() -> None:
    empty = assess(_entry(None))
    assert empty.coverage_percent == round(100 / 7)  # only the source is present
    full = assess(_entry(_driver(outer_diameter_m=0.19, cutout_diameter_m=0.15, mounting_depth_m=0.07),
                         frd_file="a.frd", zma_file="a.zma", price_eur=10.0, price_checked_on=date(2026, 10, 2)))
    assert full.coverage_percent == 100 and full.missing == ()


def test_bundled_library_has_no_invented_measurements() -> None:
    entries = ComponentLibrary(user_root=Path("/nonexistent")).entries("drivers")
    assert entries
    assert not any(assess(e).ready(Readiness.CROSSOVER) for e in entries)  # no bundled FRD/ZMA, so none is claimed


def test_coverage_report_separates_demo_data_and_matches_committed_file() -> None:
    text = coverage_markdown(ComponentLibrary(user_root=Path("/nonexistent")))
    assert "Reale Herstellerdaten" in text and "Demo-/Testdaten" in text
    committed = (Path(__file__).resolve().parents[1] / "docs/application/LIBRARY_COVERAGE.md").read_text(encoding="utf-8")
    assert committed == text, "LIBRARY_COVERAGE.md is stale: run python -m lautsprecher_konstruktion.library.coverage"


def test_dialog_text_shows_coverage_and_missing_fields() -> None:
    html = readiness_html(_entry(_driver(), is_test_data=True))
    assert "Datenabdeckung" in html and "TESTDATEN" in html and "Frequenzgang (FRD)" in html


def test_data_quality_text_is_honest_without_frd() -> None:
    from lautsprecher_konstruktion.services.automatic import (
        AutomaticDesignRequest,
        automatic_design,
    )
    from lautsprecher_konstruktion.ui.result_text import data_quality

    QApplication.instance() or QApplication([])
    result = automatic_design(AutomaticDesignRequest(max_width_m=0.3, max_height_m=0.5, max_depth_m=0.4), ComponentLibrary())
    assert result.designs
    value, hint = data_quality(result.designs[0])
    assert "%" in value and "Datenabdeckung" in hint and "Modellstatus" in hint
    assert "keine FRD" in hint  # the model status names what is missing, kept apart from the coverage headline


@pytest.mark.parametrize("kind", list(Readiness))
def test_every_readiness_has_a_german_label(kind: Readiness) -> None:
    from lautsprecher_konstruktion.library.readiness import READINESS_LABELS_DE
    assert READINESS_LABELS_DE[kind]
