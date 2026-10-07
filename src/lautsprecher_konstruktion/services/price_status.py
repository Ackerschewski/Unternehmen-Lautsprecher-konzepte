"""Price truth: what is known about the cost of a design, and when two designs may be compared.

A relative price claim ("günstiger") is only allowed when both designs have a complete price coverage.
Planning prices (Planpreis, Materialreferenz) count as estimates, never as retail prices.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from lautsprecher_konstruktion.export.bom import BomItem

ESTIMATE_KINDS = frozenset({"Planpreis", "Materialreferenz"})
RESERVE_FACTOR = 1.15
MIN_CHEAPER_SHARE = 0.03  # a price advantage below 3 % is not worth a label


class PriceStatus(StrEnum):
    COMPLETE = "COMPLETE"    # every position has a retail/manufacturer price
    ESTIMATED = "ESTIMATED"  # every position has a price, some only as planning/reference estimate
    PARTIAL = "PARTIAL"      # some positions have no price at all
    UNKNOWN = "UNKNOWN"      # no position has a price


@dataclass(frozen=True)
class PriceInfo:
    status: PriceStatus
    known_cost_eur: float       # sum of positions with retail/manufacturer prices
    estimated_cost_eur: float   # sum of positions with planning/reference prices
    missing_items: tuple[str, ...]
    priced_item_count: int
    total_item_count: int

    @property
    def coverage_percent(self) -> float:
        return 100.0 * self.priced_item_count / self.total_item_count if self.total_item_count else 0.0

    @property
    def subtotal_eur(self) -> float:
        return self.known_cost_eur + self.estimated_cost_eur

    @property
    def total_with_reserve_eur(self) -> float | None:
        """Planned cost incl. reserve; only for a complete coverage."""
        if self.status in (PriceStatus.COMPLETE, PriceStatus.ESTIMATED):
            return round(self.subtotal_eur * RESERVE_FACTOR, 2)
        return None

    @property
    def comparable(self) -> bool:
        return self.status in (PriceStatus.COMPLETE, PriceStatus.ESTIMATED)

    def label_de(self) -> str:
        """Short user text, e.g. "47/63 Positionen bepreist"."""
        if self.status is PriceStatus.UNKNOWN:
            return "Preis unbekannt"
        if self.comparable:
            kind = "geschätzt" if self.status is PriceStatus.ESTIMATED else "vollständig"
            return f"{self.priced_item_count}/{self.total_item_count} Positionen bepreist · {kind}"
        return f"{self.priced_item_count}/{self.total_item_count} Positionen bepreist"


def price_info(items: tuple[BomItem, ...]) -> PriceInfo:
    known = estimated = 0.0
    missing: list[str] = []
    priced = 0
    for item in items:
        total = item.line_total_eur
        if total is None:
            missing.append(f"{item.reference} {item.description}".strip())
            continue
        priced += 1
        if item.price_kind in ESTIMATE_KINDS:
            estimated += total
        else:
            known += total
    if not items or priced == 0:
        status = PriceStatus.UNKNOWN
    elif missing:
        status = PriceStatus.PARTIAL
    elif estimated > 0:
        status = PriceStatus.ESTIMATED
    else:
        status = PriceStatus.COMPLETE
    return PriceInfo(status, round(known, 2), round(estimated, 2), tuple(missing), priced, len(items))


def cheaper_than(candidate: PriceInfo, baseline: PriceInfo) -> bool:
    """True only when both prices are comparable and the candidate is clearly cheaper."""
    if not (candidate.comparable and baseline.comparable):
        return False
    return candidate.subtotal_eur < baseline.subtotal_eur * (1 - MIN_CHEAPER_SHARE)
