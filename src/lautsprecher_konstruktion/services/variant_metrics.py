"""Decision metrics per variant: chips for the cards and normalised values for the mini comparison.

Everything is computed from the solved design. A metric that cannot be derived is ``None`` and shows as
unknown; it is never replaced by a plausible-looking number, and a price ranking needs complete prices.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from lautsprecher_konstruktion.services.automatic import SpeakerDesign
from lautsprecher_konstruktion.services.price_status import PriceInfo, cheaper_than, price_info


class Tone(StrEnum):
    OK = "ok"
    WARN = "warn"
    BAD = "bad"
    MUTED = "muted"


@dataclass(frozen=True)
class Chip:
    key: str
    text: str
    tone: Tone = Tone.MUTED


@dataclass(frozen=True)
class VariantMetrics:
    f3_hz: float | None
    volume_l: float
    spl_db: float | None
    price: PriceInfo
    coverage_percent: int
    effort_panels: int
    warning_count: int
    error_count: int


def f3_of(design: SpeakerDesign) -> float | None:
    b = design.bundle
    return b.sealed.f3_hz if b.sealed else (b.vented_response.f3_hz if b.vented_response else None)


def data_coverage_percent(design: SpeakerDesign, price: PriceInfo) -> int:
    """Mean of three defined shares: T/S fields, measurement files for the crossover, priced BOM positions."""
    w = design.woofer
    ts = all(getattr(w, name) is not None for name in ("fs_hz", "qts", "vas_m3", "sd_m2"))
    cross = design.bundle.project.crossover
    needs_measurements = design.tweeter is not None
    measured = (cross.woofer_frd is not None and cross.woofer_zma is not None
                and (not needs_measurements or (cross.tweeter_frd is not None and cross.tweeter_zma is not None)))
    shares = [100.0 if ts else 0.0, 100.0 if measured else 0.0, price.coverage_percent]
    return round(sum(shares) / len(shares))


def metrics_of(design: SpeakerDesign) -> VariantMetrics:
    cab = design.bundle.cabinet
    price = price_info(design.bom)
    issues = design.bundle.issues
    return VariantMetrics(
        f3_of(design), cab.width_m * cab.height_m * cab.depth_m * 1000, design.spl_limit_db, price,
        data_coverage_percent(design, price), sum(p.quantity for p in design.bundle.panels),
        sum(1 for i in issues if i.severity == "warning"), sum(1 for i in issues if i.severity == "error"))


def chips_for(design: SpeakerDesign, baseline: SpeakerDesign | None = None) -> tuple[Chip, ...]:
    m = metrics_of(design)
    cab = design.bundle.cabinet
    codes = {i.code for i in design.bundle.issues}
    chips = [
        Chip("size", f"{cab.width_m*1000:.0f} × {cab.height_m*1000:.0f} × {cab.depth_m*1000:.0f} mm"),
        Chip("f3", f"F3 {m.f3_hz:.0f} Hz" if m.f3_hz is not None else "F3 offen", Tone.MUTED if m.f3_hz is not None else Tone.WARN),
        Chip("spl", f"Max-SPL {m.spl_db:.0f} dB" if m.spl_db is not None else "Max-SPL unbekannt",
             Tone.MUTED if m.spl_db is not None else Tone.WARN),
    ]
    excursion_bad = bool(codes & {"XMAX_EXCEEDED", "RADIATOR_XMAX"})
    chips.append(Chip("hub", "Hub ⚠" if excursion_bad else "Hub ✓", Tone.WARN if excursion_bad else Tone.OK))
    if design.bundle.port is not None:
        port_bad = "PORT_VELOCITY_HIGH" in codes
        chips.append(Chip("port", "Port ⚠" if port_bad else "Port ✓", Tone.WARN if port_bad else Tone.OK))
    chips.append(Chip("price", f"{m.price.priced_item_count}/{m.price.total_item_count} bepreist" if not m.price.comparable
                      else f"{m.price.total_with_reserve_eur:.0f} € inkl. Reserve",
                      Tone.OK if m.price.comparable else Tone.WARN))
    chips.append(Chip("coverage", f"Datenabdeckung {m.coverage_percent} %",
                      Tone.OK if m.coverage_percent >= 80 else Tone.WARN if m.coverage_percent >= 40 else Tone.BAD))
    chips.append(Chip("effort", f"{m.effort_panels} Platten"))
    if m.error_count:
        chips.append(Chip("warnings", f"✕ {m.error_count} Fehler", Tone.BAD))
    elif m.warning_count:
        chips.append(Chip("warnings", f"⚠ {m.warning_count} Hinweise", Tone.WARN))
    else:
        chips.append(Chip("warnings", "✓ keine Warnungen", Tone.OK))
    if baseline is not None and baseline is not design and cheaper_than(m.price, price_info(baseline.bom)):
        chips.insert(0, Chip("cheaper", "Günstiger als A", Tone.OK))
    return tuple(chips)


@dataclass(frozen=True)
class BarRow:
    key: str
    label: str
    values: tuple[float | None, ...]  # 0..1, larger is better; None = unknown
    texts: tuple[str, ...]
    disabled_reason: str = ""


def _scale(raw: list[float | None], higher_is_better: bool) -> tuple[float | None, ...]:
    known = [v for v in raw if v is not None]
    if not known:
        return tuple(None for _ in raw)
    lo, hi = min(known), max(known)
    out: list[float | None] = []
    for v in raw:
        if v is None:
            out.append(None)
        elif hi == lo:
            out.append(1.0)
        else:
            share = (v - lo) / (hi - lo)
            out.append(0.15 + 0.85 * (share if higher_is_better else 1 - share))
    return tuple(out)


def comparison_rows(designs: tuple[SpeakerDesign, ...]) -> tuple[BarRow, ...]:
    """One row per decision metric. Price is disabled unless every variant has comparable prices."""
    ms = [metrics_of(d) for d in designs]
    price_ok = all(m.price.comparable for m in ms)
    rows = [
        BarRow("bass", "Tiefbass", _scale([m.f3_hz for m in ms], False),
               tuple(f"F3 {m.f3_hz:.0f} Hz" if m.f3_hz is not None else "offen" for m in ms)),
        BarRow("compact", "Kompaktheit", _scale([m.volume_l for m in ms], False), tuple(f"{m.volume_l:.0f} l außen" for m in ms)),
        BarRow("spl", "Pegel", _scale([m.spl_db for m in ms], True),
               tuple(f"{m.spl_db:.0f} dB" if m.spl_db is not None else "unbekannt" for m in ms)),
        BarRow("price", "Preis", _scale([m.price.subtotal_eur if price_ok else None for m in ms], False),
               tuple(f"{m.price.total_with_reserve_eur:.0f} €" if price_ok and m.price.total_with_reserve_eur is not None
                     else f"{m.price.priced_item_count}/{m.price.total_item_count} bepreist" for m in ms),
               "" if price_ok else "Preisranking nicht möglich: nicht alle Varianten sind vollständig bepreist."),
        BarRow("data", "Datenabdeckung", _scale([float(m.coverage_percent) for m in ms], True), tuple(f"{m.coverage_percent} %" for m in ms)),
        BarRow("effort", "Bauaufwand", _scale([float(m.effort_panels) for m in ms], False), tuple(f"{m.effort_panels} Platten" for m in ms)),
    ]
    return tuple(rows)
