from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

from lautsprecher_konstruktion.drivers.models import Driver


@dataclass(frozen=True)
class SealedResult:
    target_qtc: float
    box_volume_m3: float
    resonance_hz: float
    f3_hz: float

    @property
    def box_volume_l(self) -> float:
        return self.box_volume_m3 * 1000.0


def _f3_ratio(qtc: float) -> float:
    """Return f3/Fc for a second-order sealed high-pass response."""
    a = 2.0 - (1.0 / (qtc * qtc))
    y = (-a + sqrt(a * a + 4.0)) / 2.0
    return sqrt(y)


def solve_sealed(driver: Driver, target_qtc: float = 0.707) -> SealedResult:
    """Calculate an idealized sealed enclosure from small-signal T/S parameters."""
    if driver.vas_m3 is None:
        raise ValueError("Vas fehlt; geschlossene Gehäuseauslegung nicht möglich")
    if target_qtc <= driver.qts:
        raise ValueError("target_qtc must be greater than driver.qts")

    alpha = (target_qtc / driver.qts) ** 2 - 1.0
    volume_m3 = driver.vas_m3 / alpha
    resonance_hz = driver.fs_hz * (target_qtc / driver.qts)
    f3_hz = resonance_hz * _f3_ratio(target_qtc)

    return SealedResult(
        target_qtc=target_qtc,
        box_volume_m3=volume_m3,
        resonance_hz=resonance_hz,
        f3_hz=f3_hz,
    )
