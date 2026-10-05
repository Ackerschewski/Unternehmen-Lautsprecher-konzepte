from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from lautsprecher_konstruktion.drivers.models import Driver


def sealed_system_parameters(driver: Driver, box_volume_m3: float) -> tuple[float, float]:
    if box_volume_m3 <= 0:
        raise ValueError("box_volume_m3 must be positive")
    if driver.vas_m3 is None:
        raise ValueError("Vas fehlt; geschlossene Gehäuseauslegung nicht möglich")
    alpha = driver.vas_m3 / box_volume_m3
    multiplier = np.sqrt(1.0 + alpha)
    return float(driver.fs_hz * multiplier), float(driver.qts * multiplier)


def sealed_response_db(
    driver: Driver,
    box_volume_m3: float,
    frequencies_hz: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Small-signal normalized sealed-box acoustic high-pass magnitude."""
    fc_hz, qtc = sealed_system_parameters(driver, box_volume_m3)
    if np.any(frequencies_hz <= 0):
        raise ValueError("frequencies must be positive")

    x = frequencies_hz / fc_hz
    magnitude = x**2 / np.sqrt((1.0 - x**2) ** 2 + (x / qtc) ** 2)
    return 20.0 * np.log10(np.maximum(magnitude, 1e-12))
