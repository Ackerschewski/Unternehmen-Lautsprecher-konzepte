"""Transparent material budget for a single cabinet, with quoted and planning prices.

Only retail product prices are labelled retail. Generic components are cost
allowances, not vendor offers. Unknown driver prices remain unknown.
"""
from __future__ import annotations

from dataclasses import replace
from math import pi

from lautsprecher_konstruktion.export.bom import BomItem, priced_subtotal
from lautsprecher_konstruktion.services.design import DesignBundle

PRICE_DATE = "2026-10-02"
RESERVE_FACTOR = 1.15
PANEL_RATES = {
    "Birke Multiplex": (62.50, "https://www.bauhaus.info/zuschnittplatten/multiplexplatte-nach-mass-i/p/20083841"),
    "MDF": (19.65, "https://www.bauhaus.info/zuschnittplatten/mdf-platte-nach-mass-i/p/20770268"),
    "Spanplatte": (24.20, "https://www.bauhaus.info/zuschnittplatten/spanplatte-nach-mass/p/14490135"),
}


def _panel_unit(area_m2: float, thickness_m: float, material: str) -> tuple[float, str]:
    rate, source = PANEL_RATES.get(material, PANEL_RATES["Birke Multiplex"])
    # BAUHAUS reference sheets are 18 mm (19 mm for chipboard). Other thicknesses are scaled estimates.
    reference_m = .019 if material == "Spanplatte" else .018
    return max(.50, round(area_m2 * rate * thickness_m/reference_m, 2)), source


def price_bom(bundle: DesignBundle, items: tuple[BomItem, ...]) -> tuple[BomItem, ...]:
    """Assign a positive planning price to every non-driver construction line."""
    panel_prices = {}
    for panel in bundle.panels:
        panel_prices[panel.name] = _panel_unit(
            panel.width_m * panel.height_m, panel.thickness_m, bundle.project.material)
    if bundle.brace:
        brace = bundle.brace
        panel_prices["Brace"] = _panel_unit(
            brace.outer_width_m * brace.outer_height_m, brace.thickness_m,
            bundle.project.material)
    result = []
    for item in items:
        if item.unit_price_eur is not None:
            result.append(item)
            continue
        if item.category == "Treiber":
            result.append(replace(item, price_kind="fehlt"))
            continue
        source = ""
        if item.reference in panel_prices:
            price, source = panel_prices[item.reference]
            kind = "Materialreferenz"
        elif item.reference == "K1" and bundle.coupler:
            k = bundle.coupler
            shell_area = pi * k.outer_diameter_m * k.length_m
            ring_area = pi * (k.outer_diameter_m/2)**2
            price, source = _panel_unit(shell_area + ring_area, k.ring_thickness_m,
                                        bundle.project.material)
            price = max(12.0, price)
            kind = "Planpreis"
        else:
            category = item.category.casefold()
            reference = item.reference.upper()
            if category == "frequenzweichenkomponenten":
                desc = item.description.casefold()
                price = 12.0 if "induct" in desc or "spule" in desc else (
                    6.0 if "capac" in desc or "kondens" in desc else 3.0)
            elif category == "ports":
                price = 15.0
            elif category == "passivmembran":
                price = 90.0
            elif reference in {"MONTAGE", "HOLZSCHR"}:
                price = .10
            elif reference == "KABEL":
                price = 2.50
            elif reference == "LEIM":
                price = 8.0
            elif reference == "TERM1":
                price = 10.0
            else:
                price = 10.0
            kind = "Planpreis"
        result.append(replace(item, unit_price_eur=price, price_source_url=source,
                              price_kind=kind, notes=(item.notes + "; " if item.notes else "")+
                              f"{kind} {PRICE_DATE}; vor Einkauf prüfen"))
    return tuple(result)


def budget_cost(items: tuple[BomItem, ...]) -> float | None:
    """Full planned material cost incl. 15% reserve; None when any line lacks a price."""
    subtotal, missing = priced_subtotal(items)
    return None if missing else round(subtotal * RESERVE_FACTOR, 2)
