"""Smooth, shape-preserving target curve through control points (PCHIP in log-frequency).

PCHIP keeps the control points exact and never overshoots between them, so a free curve has no polygon
kinks and no invented peaks. Outside the first/last point the curve is held at the end value.
"""
from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from numpy.typing import NDArray
from scipy.interpolate import PchipInterpolator

from lautsprecher_konstruktion.targets.eq import EQBand, eq_response_db

Float = NDArray[np.float64]
RENDER_POINTS = 900  # 600-1200 points keep the curve visually smooth


def render_frequencies(count: int = RENDER_POINTS, low: float = 20.0, high: float = 20_000.0) -> Float:
    return np.asarray(np.geomspace(low, high, count), dtype=float)


def smooth_curve_db(points: Sequence[tuple[float, float]], frequencies_hz: Float) -> Float:
    """PCHIP through (frequency_hz, level_db) points on a log-frequency axis."""
    f = np.asarray(frequencies_hz, dtype=float)
    if not points:
        return np.zeros_like(f)
    data = np.asarray(sorted(points), dtype=float)
    if data.ndim != 2 or data.shape[1] != 2 or np.any(data[:, 0] <= 0):
        raise ValueError("control points must be (frequency_hz > 0, level_db)")
    if len(data) == 1:
        return np.full_like(f, data[0, 1])
    unique, index = np.unique(data[:, 0], return_index=True)
    if len(unique) != len(data):
        data = data[index]  # duplicate frequencies: keep the first value
    interpolator = PchipInterpolator(np.log10(data[:, 0]), data[:, 1], extrapolate=False)
    values = np.asarray(interpolator(np.log10(f)), dtype=float)
    values = np.where(f < data[0, 0], data[0, 1], values)
    return np.asarray(np.where(f > data[-1, 0], data[-1, 1], values), dtype=float)


def target_level_db(points: Sequence[tuple[float, float]], bands: Sequence[EQBand],
                    frequencies_hz: Float) -> Float:
    """Target = smooth base curve plus the real filter responses of all enabled EQ bands."""
    f = np.asarray(frequencies_hz, dtype=float)
    return smooth_curve_db(points, f) + eq_response_db(list(bands), f)
