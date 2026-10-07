"""Parametric EQ bands with real biquad responses (RBJ cookbook), independent of any UI.

A band is a *design objective* in the target curve (or a DSP filter that is applied later); its frequency
response is the magnitude of a digital biquad (or a cascade for 4th-order low/high-pass), not a Gaussian.
Responses add in dB.
"""
from __future__ import annotations

from enum import StrEnum
from math import cos, pi, sin, sqrt

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, Field

SAMPLE_RATE_HZ = 48_000.0
FREQ_MIN_HZ = 20.0
FREQ_MAX_HZ = 20_000.0
GAIN_LIMIT_DB = 18.0
Float = NDArray[np.float64]


class FilterType(StrEnum):
    BELL = "bell"
    LOW_SHELF = "low_shelf"
    HIGH_SHELF = "high_shelf"
    LOW_PASS = "low_pass"
    HIGH_PASS = "high_pass"
    NOTCH = "notch"


FILTER_LABELS: dict[FilterType, str] = {
    FilterType.BELL: "Glocke", FilterType.LOW_SHELF: "Tiefen-Shelf", FilterType.HIGH_SHELF: "Höhen-Shelf",
    FilterType.LOW_PASS: "Tiefpass", FilterType.HIGH_PASS: "Hochpass", FilterType.NOTCH: "Kerbfilter",
}
GAIN_TYPES = frozenset({FilterType.BELL, FilterType.LOW_SHELF, FilterType.HIGH_SHELF})
# Butterworth section Q values for a 4th-order cascade
_BUTTERWORTH_4 = (0.5411961, 1.3065630)


class EQBand(BaseModel):
    id: str = "band"
    enabled: bool = True
    filter_type: FilterType = FilterType.BELL
    frequency_hz: float = Field(default=1000.0, ge=FREQ_MIN_HZ, le=FREQ_MAX_HZ)
    gain_db: float = Field(default=0.0, ge=-GAIN_LIMIT_DB, le=GAIN_LIMIT_DB)
    q: float = Field(default=1.0, ge=0.2, le=10.0)
    order: int = Field(default=2, description="2 or 4; only used by low/high-pass")

    @property
    def uses_gain(self) -> bool:
        return self.filter_type in GAIN_TYPES


def _biquad(kind: FilterType, f0: float, gain_db: float, q: float) -> tuple[tuple[float, ...], tuple[float, ...]]:
    a_gain = 10 ** (gain_db / 40)
    w0 = 2 * pi * min(f0, SAMPLE_RATE_HZ / 2.2) / SAMPLE_RATE_HZ
    alpha = sin(w0) / (2 * q)
    c = cos(w0)
    if kind is FilterType.BELL:
        return ((1 + alpha * a_gain, -2 * c, 1 - alpha * a_gain), (1 + alpha / a_gain, -2 * c, 1 - alpha / a_gain))
    if kind in (FilterType.LOW_SHELF, FilterType.HIGH_SHELF):
        beta = 2 * sqrt(a_gain) * alpha
        if kind is FilterType.LOW_SHELF:
            return ((a_gain * ((a_gain + 1) - (a_gain - 1) * c + beta), 2 * a_gain * ((a_gain - 1) - (a_gain + 1) * c),
                     a_gain * ((a_gain + 1) - (a_gain - 1) * c - beta)),
                    ((a_gain + 1) + (a_gain - 1) * c + beta, -2 * ((a_gain - 1) + (a_gain + 1) * c),
                     (a_gain + 1) + (a_gain - 1) * c - beta))
        return ((a_gain * ((a_gain + 1) + (a_gain - 1) * c + beta), -2 * a_gain * ((a_gain - 1) + (a_gain + 1) * c),
                 a_gain * ((a_gain + 1) + (a_gain - 1) * c - beta)),
                ((a_gain + 1) - (a_gain - 1) * c + beta, 2 * ((a_gain - 1) - (a_gain + 1) * c),
                 (a_gain + 1) - (a_gain - 1) * c - beta))
    if kind is FilterType.LOW_PASS:
        return (((1 - c) / 2, 1 - c, (1 - c) / 2), (1 + alpha, -2 * c, 1 - alpha))
    if kind is FilterType.HIGH_PASS:
        return (((1 + c) / 2, -(1 + c), (1 + c) / 2), (1 + alpha, -2 * c, 1 - alpha))
    return ((1.0, -2 * c, 1.0), (1 + alpha, -2 * c, 1 - alpha))  # notch


def _magnitude_db(b: tuple[float, ...], a: tuple[float, ...], f: Float) -> Float:
    z = np.exp(-1j * 2 * pi * f / SAMPLE_RATE_HZ)
    num = b[0] + b[1] * z + b[2] * z ** 2
    den = a[0] + a[1] * z + a[2] * z ** 2
    return np.asarray(20 * np.log10(np.maximum(np.abs(num / den), 1e-12)), dtype=float)


def band_response_db(band: EQBand, frequencies_hz: Float) -> Float:
    """Magnitude response of one band in dB (zeros when disabled)."""
    f = np.asarray(frequencies_hz, dtype=float)
    if not band.enabled:
        return np.zeros_like(f)
    kind = band.filter_type
    gain = band.gain_db if band.uses_gain else 0.0
    if kind in (FilterType.BELL, FilterType.LOW_SHELF, FilterType.HIGH_SHELF) and abs(gain) < 1e-12:
        return np.zeros_like(f)
    if kind in (FilterType.LOW_PASS, FilterType.HIGH_PASS) and band.order == 4:
        return sum((_magnitude_db(*_biquad(kind, band.frequency_hz, 0.0, q), f) for q in _BUTTERWORTH_4),
                   np.zeros_like(f))
    return _magnitude_db(*_biquad(kind, band.frequency_hz, gain, band.q), f)


def eq_response_db(bands: tuple[EQBand, ...] | list[EQBand], frequencies_hz: Float) -> Float:
    """Combined response of all enabled bands (sum in dB)."""
    f = np.asarray(frequencies_hz, dtype=float)
    total = np.zeros_like(f)
    for band in bands:
        total = total + band_response_db(band, f)
    return total
