"""Baffle step: the on-axis level rises by up to 6 dB when radiation changes from full space (4 pi)
at low frequencies to half space (2 pi) at high frequencies.

The transition frequency follows the common engineering rule f = 115 Hz m / W for the front
baffle width W (Linkwitz). The step is modelled as a first-order shelf. This ignores edge
diffraction ripple, cabinet depth and driver position, and has not been validated against
measurements in this project; treat it as a starting value for a baffle step compensation.
"""
from __future__ import annotations

from math import sqrt

import numpy as np
from numpy.typing import NDArray

BAFFLE_STEP_CONSTANT_HZ_M = 115.0
MAX_STEP_DB = 6.0206  # 20 log10(2): full space to half space


def baffle_step_frequency_hz(baffle_width_m: float) -> float:
    """Frequency at which half of the step (about 3 dB for a 6 dB step) is reached."""
    if baffle_width_m <= 0:
        raise ValueError("baffle width must be positive")
    return BAFFLE_STEP_CONSTANT_HZ_M / baffle_width_m


def baffle_step_db(frequencies_hz: NDArray[np.float64], baffle_width_m: float,
                   step_db: float = MAX_STEP_DB) -> NDArray[np.float64]:
    """Level of the step relative to the high-frequency (half-space) level: 0 dB high, -step_db low."""
    if not 0 < step_db <= MAX_STEP_DB + 1e-9:
        raise ValueError("step_db must be between 0 and 6.02 dB")
    k = 10.0 ** (step_db / 20.0)
    f3 = baffle_step_frequency_hz(baffle_width_m)
    f_zero, f_pole = f3 / sqrt(k), f3 * sqrt(k)
    f = np.asarray(frequencies_hz, dtype=float)
    gain = np.sqrt((1.0 + (f / f_zero) ** 2) / (1.0 + (f / f_pole) ** 2))
    return 20.0 * np.log10(gain / k)
