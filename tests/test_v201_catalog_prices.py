from __future__ import annotations

import csv

from lautsprecher_konstruktion.export.bom import BomItem, priced_subtotal, write_bom_csv
from lautsprecher_konstruktion.export.pricing import budget_cost
from lautsprecher_konstruktion.library.store import ComponentLibrary
from lautsprecher_konstruktion.services.automatic import AutomaticDesignRequest, automatic_design


def test_thomann_catalog_separates_price_from_design_data(tmp_path):
    library = ComponentLibrary(user_root=tmp_path / "user")
    catalog = [entry for entry in library.entries("drivers") if entry.id.startswith("thomann:")]
    assert len(catalog) >= 70
    assert all(entry.price_eur is not None and entry.price_checked_on and entry.product_url
               for entry in catalog)
    incomplete = next(entry for entry in catalog if entry.model == "8PR200 8 Ohms")
    assert incomplete.driver is None
    assert all(driver.model != incomplete.model for driver in library.drivers())
    complete = next(entry for entry in catalog if entry.model == "6FE200 8 Ohms")
    assert complete.driver.price == 39 and complete.driver.currency == "EUR"


def test_verified_real_drivers_have_price_sources(tmp_path):
    library = ComponentLibrary(user_root=tmp_path / "user")
    real_drivers = [entry for entry in library.entries("drivers")
                    if entry.driver is not None and not entry.is_test_data]
    assert real_drivers
    assert all(entry.price_eur is not None and entry.price_eur > 0
               and entry.price_checked_on and entry.product_url
               for entry in real_drivers)
    dayton = next(entry for entry in real_drivers if entry.id == "dayton:dc28f-8")
    assert dayton.driver.price == 31.45


def test_exact_chassis_filter_and_priced_bom(tmp_path):
    library = ComponentLibrary(user_root=tmp_path / "user")
    result = automatic_design(AutomaticDesignRequest(
        speaker_type="Breitbandlautsprecher", way_count=1,
        preferred_driver="Visaton B 200 - 6 Ohm",
        max_width_m=.45, max_height_m=.8, max_depth_m=.7), library)
    assert result.status == "ok", result.rejection_reasons
    design = result.designs[0]
    assert design.woofer.model == "B 200 - 6 Ohm"
    driver_row = next(item for item in design.bom if item.reference == "W1")
    assert driver_row.unit_price_eur == 183
    assert driver_row.line_total_eur == driver_row.quantity * 183
    assert design.price == driver_row.line_total_eur
    assert design.total_price_eur == budget_cost(design.bom)
    assert design.total_price_eur > design.price
    assert all(item.unit_price_eur is not None for item in design.bom)

    path = tmp_path / "bom.csv"
    write_bom_csv(path, design.bom)
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.reader(stream, delimiter=";"))
    assert rows[0][-4:] == ["Einzelpreis_EUR", "Positionspreis_EUR", "Preisquelle", "Preisart"]
    assert any(row[1] == "W1" and row[-3] == f"{driver_row.line_total_eur:.2f}"
               for row in rows[1:])


def test_unknown_prices_are_not_counted_as_full_total():
    items = (BomItem("Treiber", "W1", "Chassis", 2, "8 Ohm", unit_price_eur=39),
             BomItem("Holz", "P1", "Platte", 1, "MDF"))
    assert priced_subtotal(items) == (78, 1)
    assert budget_cost(items) is None


def test_budget_checks_whole_cabinet_not_only_chassis(tmp_path):
    library = ComponentLibrary(user_root=tmp_path / "user")
    base = {"speaker_type": "Breitbandlautsprecher", "way_count": 1,
                "preferred_driver": "Visaton B 200 - 6 Ohm",
                "max_width_m": .45, "max_height_m": .8, "max_depth_m": .7}
    too_low = automatic_design(AutomaticDesignRequest(**base, budget=300), library)
    assert too_low.status == "impossible"
    assert any("Budget" in reason for reason in too_low.rejection_reasons)
    affordable = automatic_design(AutomaticDesignRequest(**base, budget=500), library)
    assert affordable.status == "ok"
    assert all(design.total_price_eur <= 500 for design in affordable.designs)
