"""Manufacturing summary and BOM grouping shared by the UI, the PDF and tests (pure functions)."""
from __future__ import annotations

from dataclasses import dataclass

from lautsprecher_konstruktion.export.bom import BomItem
from lautsprecher_konstruktion.export.cutting import CuttingPlan
from lautsprecher_konstruktion.export.weight import estimate_weight
from lautsprecher_konstruktion.services.automatic import SpeakerDesign
from lautsprecher_konstruktion.services.price_status import PriceInfo, price_info

GROUPS = ("Gehäuse", "Chassis", "Frequenzweiche", "Anschlüsse", "Dämmung", "Hardware")


def group_of(item: BomItem) -> str:
    """BOM group of a position, derived from its category and reference."""
    category, reference = item.category.casefold(), item.reference.upper()
    if category in {"gehäuseplatten", "versteifungen", "ports", "passivmembran"}:
        return "Gehäuse"
    if category == "treiber":
        return "Chassis"
    if category == "frequenzweichenkomponenten":
        return "Frequenzweiche"
    if category == "dämmung" or reference.startswith("DÄMM"):
        return "Dämmung"
    if reference.startswith(("TERM", "KABEL")):
        return "Anschlüsse"
    return "Hardware"


def grouped(items: tuple[BomItem, ...]) -> tuple[tuple[str, tuple[BomItem, ...]], ...]:
    buckets: dict[str, list[BomItem]] = {name: [] for name in GROUPS}
    for item in items:
        buckets[group_of(item)].append(item)
    return tuple((name, tuple(rows)) for name, rows in buckets.items() if rows)


@dataclass(frozen=True)
class ManufacturingSummary:
    price: PriceInfo
    sheets: int | None
    waste_percent: float | None
    weight_text: str
    positions: int
    pieces: int
    unplaced_parts: int

    def rows(self) -> tuple[tuple[str, str, str], ...]:
        """(label, value, hint) for the summary cards."""
        p = self.price
        known = f"{p.known_cost_eur:.2f} €" if p.priced_item_count else "–"
        estimated = f"{p.estimated_cost_eur:.2f} €" if p.estimated_cost_eur else "–"
        missing = f"{len(p.missing_items)} von {p.total_item_count}"
        sheets = ("nicht planbar" if self.sheets is None else f"{self.sheets} Platte{'n' if self.sheets != 1 else ''}"
                  + (f" · {self.waste_percent:.0f} % Verschnitt" if self.waste_percent is not None else ""))
        return (
            ("Bekannte Kosten", known, "Positionen mit Händler- oder Herstellerpreis"),
            ("Geschätzte Kosten", estimated, "Plan- und Materialreferenzpreise; vor dem Einkauf prüfen"),
            ("Fehlende Preise", missing, "; ".join(p.missing_items[:6]) or "Alle Positionen haben einen Preis"),
            ("Materialplatten", sheets, "Aus dem Zuschnittplan; Standardplatte des Materials"),
            ("Gehäusegewicht", self.weight_text, "Richtdichte; ohne Chassis, Weiche und Dämmung"),
            ("Bauteile", f"{self.positions} Positionen · {self.pieces} Stück", "Stückliste, ohne Verschnitt"),
        )


def summarize(design: SpeakerDesign, plan: CuttingPlan | None) -> ManufacturingSummary:
    weight = estimate_weight(design.bundle)
    weight_text = f"{weight.low_kg:.1f}–{weight.high_kg:.1f} kg" if weight.low_kg is not None and weight.high_kg is not None else "nicht berechenbar"
    return ManufacturingSummary(
        price_info(design.bom), plan.sheet_count if plan is not None and plan.feasible else None,
        plan.waste_percent if plan is not None and plan.feasible else None, weight_text,
        len(design.bom), sum(item.quantity for item in design.bom), len(plan.unplaced) if plan is not None else 0)
