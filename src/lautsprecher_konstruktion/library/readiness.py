"""Derived library readiness and data coverage.

Everything here is computed from the stored record. Nothing is maintained by hand, and a missing
field is never filled in to improve a percentage.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from lautsprecher_konstruktion.library.store import LibraryEntry


class Readiness(StrEnum):
    ENCLOSURE = "enclosure_ready"
    CROSSOVER = "crossover_ready"
    MANUFACTURING = "manufacturing_ready"
    FULLRANGE = "fullrange_ready"
    PRICING = "pricing_ready"
    THREE_D = "three_d_ready"


READINESS_LABELS_DE = {
    Readiness.ENCLOSURE: "Gehäuseberechnung",
    Readiness.CROSSOVER: "Weichenentwurf",
    Readiness.MANUFACTURING: "Fertigungsmaße",
    Readiness.FULLRANGE: "Breitbandaussage 20 Hz–20 kHz",
    Readiness.PRICING: "Preis geprüft",
    Readiness.THREE_D: "3D-Hülle",
}

# Required fields per readiness: (driver attribute | entry attribute) names.
_ENCLOSURE = ("fs_hz", "qts", "vas_m3", "sd_m2")  # Xmax only limits headroom, it is not needed for the box volume
_MANUFACTURING = ("outer_diameter_m", "cutout_diameter_m", "mounting_depth_m")
_FULLRANGE_BAND_HZ = (50.0, 15000.0)

# Fields that make up the coverage percentage, with a German label for the detail view.
COVERAGE_FIELDS: tuple[tuple[str, str], ...] = (
    ("ts", "T/S-Parameter"),
    ("frd", "Frequenzgang (FRD)"),
    ("zma", "Impedanz (ZMA)"),
    ("mount", "Montagemaße"),
    ("price", "Preis mit Prüfdatum"),
    ("shape3d", "3D-Hülle"),
    ("source", "Quelle"),
)


@dataclass(frozen=True)
class ReadinessReport:
    flags: dict[Readiness, bool]
    coverage: dict[str, bool]
    missing: tuple[str, ...]

    @property
    def coverage_percent(self) -> int:
        return round(100 * sum(self.coverage.values()) / len(self.coverage))

    def ready(self, kind: Readiness) -> bool:
        return self.flags[kind]


def _has(driver: object, names: tuple[str, ...]) -> bool:
    return all(getattr(driver, name, None) is not None for name in names)


def assess(entry: LibraryEntry) -> ReadinessReport:
    """Readiness flags and coverage for one entry; non-driver categories are judged on price and source only."""
    driver = entry.driver
    has_ts = driver is not None and _has(driver, _ENCLOSURE)
    has_mount = driver is not None and _has(driver, _MANUFACTURING)
    has_frd, has_zma = entry.frd_file is not None, entry.zma_file is not None
    has_price = entry.price_eur is not None and entry.price_checked_on is not None
    span_known = (driver is not None and driver.min_frequency_hz is not None
                  and driver.max_frequency_hz is not None
                  and driver.min_frequency_hz <= _FULLRANGE_BAND_HZ[0]
                  and driver.max_frequency_hz >= _FULLRANGE_BAND_HZ[1])
    flags = {
        Readiness.ENCLOSURE: has_ts,
        Readiness.CROSSOVER: has_frd and has_zma,
        Readiness.MANUFACTURING: has_mount,
        Readiness.FULLRANGE: has_frd and has_zma and span_known,
        Readiness.PRICING: has_price,
        Readiness.THREE_D: has_mount,
    }
    coverage = {"ts": has_ts, "frd": has_frd, "zma": has_zma, "mount": has_mount,
                "price": has_price, "shape3d": has_mount, "source": bool(entry.source)}
    labels = dict(COVERAGE_FIELDS)
    missing = tuple(labels[key] for key, ok in coverage.items() if not ok)
    return ReadinessReport(flags, coverage, missing)
