"""TASK-0029 A1: price status, comparability and the rule behind the "Günstiger" label."""
from __future__ import annotations

import pytest

from lautsprecher_konstruktion.export.bom import BomItem
from lautsprecher_konstruktion.services.price_status import (
    MIN_CHEAPER_SHARE,
    RESERVE_FACTOR,
    PriceStatus,
    cheaper_than,
    price_info,
)


def _item(ref: str, price: float | None, kind: str = "retail", qty: int = 1) -> BomItem:
    return BomItem("Test", ref, f"Teil {ref}", qty, "", "", price, "", kind)


def test_status_is_derived_from_prices_and_kinds() -> None:
    assert price_info(()).status is PriceStatus.UNKNOWN
    assert price_info((_item("a", None), _item("b", None))).status is PriceStatus.UNKNOWN
    assert price_info((_item("a", 10.0), _item("b", None))).status is PriceStatus.PARTIAL
    assert price_info((_item("a", 10.0), _item("b", 5.0, "Planpreis"))).status is PriceStatus.ESTIMATED
    assert price_info((_item("a", 10.0), _item("b", 5.0))).status is PriceStatus.COMPLETE


def test_known_and_estimated_costs_are_kept_apart_and_missing_items_are_named() -> None:
    info = price_info((_item("a", 10.0, qty=2), _item("b", 5.0, "Materialreferenz"), _item("c", None)))
    assert info.known_cost_eur == 20.0 and info.estimated_cost_eur == 5.0 and info.subtotal_eur == 25.0
    assert info.priced_item_count == 2 and info.total_item_count == 3
    assert info.coverage_percent == pytest.approx(66.67, abs=0.01)
    assert info.missing_items == ("c Teil c",)
    assert info.total_with_reserve_eur is None  # no total with reserve for incomplete prices
    assert info.label_de() == "2/3 Positionen bepreist"


def test_complete_prices_give_a_total_with_reserve() -> None:
    info = price_info((_item("a", 100.0),))
    assert info.comparable and info.total_with_reserve_eur == pytest.approx(100.0 * RESERVE_FACTOR)


def test_cheaper_requires_complete_comparable_prices_on_both_sides() -> None:
    cheap = price_info((_item("a", 50.0),))
    dear = price_info((_item("a", 100.0),))
    partial = price_info((_item("a", 10.0), _item("b", None)))  # looks cheap, but half of it is unknown
    assert cheaper_than(cheap, dear)
    assert not cheaper_than(partial, dear)  # the false "Günstiger" of the V3.3 evidence
    assert not cheaper_than(cheap, partial)
    assert not cheaper_than(price_info(()), dear)


def test_a_small_advantage_is_not_labelled_cheaper() -> None:
    base = price_info((_item("a", 100.0),))
    almost = price_info((_item("a", 100.0 * (1 - MIN_CHEAPER_SHARE / 2)),))
    clearly = price_info((_item("a", 100.0 * (1 - MIN_CHEAPER_SHARE * 2)),))
    assert not cheaper_than(almost, base) and cheaper_than(clearly, base)


def test_estimates_are_comparable_but_never_called_retail() -> None:
    info = price_info((_item("a", 10.0, "Planpreis"),))
    assert info.status is PriceStatus.ESTIMATED and info.comparable
    assert "geschätzt" in info.label_de()
