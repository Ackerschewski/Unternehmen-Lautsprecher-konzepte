"""Target (desired) frequency curve: a versioned, optional project data model.

The curve is a *goal*, never a measurement. It starts flat and is shaped with EQ-like bands (peak, low shelf,
high shelf; RBJ biquad magnitudes, additive in dB). Only the range covered by real model data may be compared
with a calculated response: the lumped T/S model reaches up to :data:`MODEL_BAND_HZ`; above that no
measured data (FRD/ZMA) exists in a project and nothing is invented.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from math import pi
from typing import Literal

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, Field

FREQ_MIN_HZ = 20.0
FREQ_MAX_HZ = 20000.0
GAIN_LIMIT_DB = 18.0
MODEL_BAND_HZ = (20.0, 500.0)  # range of the T/S low-frequency model
REFERENCE_BAND_HZ = (120.0, 300.0)  # level of both curves is aligned here (responses are relative)
SAMPLE_RATE = 48000.0

BandKind = Literal["peak", "low_shelf", "high_shelf"]
KIND_LABEL: dict[str, str] = {"peak": "Glocke", "low_shelf": "Tiefen-Shelf", "high_shelf": "Höhen-Shelf"}


class TargetBand(BaseModel):
    kind: BandKind = "peak"
    frequency_hz: float = Field(default=1000.0, ge=FREQ_MIN_HZ, le=FREQ_MAX_HZ)
    gain_db: float = Field(default=0.0, ge=-GAIN_LIMIT_DB, le=GAIN_LIMIT_DB)
    q: float = Field(default=1.0, ge=0.3, le=8.0)


class TargetCurve(BaseModel):
    """Versioned optional data model (``version`` changes only with incompatible changes)."""

    version: int = 1
    name: str = "Neutral"
    bands: tuple[TargetBand, ...] = ()

    @property
    def is_neutral(self) -> bool:
        return all(abs(b.gain_db) < 1e-9 for b in self.bands)

    def with_band(self, band: TargetBand) -> TargetCurve:
        return self.model_copy(update={"bands": (*self.bands, band), "name": "Eigene Kurve"})

    def with_moved(self, index: int, frequency_hz: float, gain_db: float) -> TargetCurve:
        band = self.bands[index].model_copy(update={
            "frequency_hz": float(np.clip(frequency_hz, FREQ_MIN_HZ, FREQ_MAX_HZ)),
            "gain_db": float(np.clip(gain_db, -GAIN_LIMIT_DB, GAIN_LIMIT_DB))})
        return self.with_replaced(index, band)

    def with_replaced(self, index: int, band: TargetBand) -> TargetCurve:
        bands = list(self.bands)
        bands[index] = band
        return self.model_copy(update={"bands": tuple(bands), "name": "Eigene Kurve"})

    def without_band(self, index: int) -> TargetCurve:
        return self.model_copy(update={"bands": tuple(b for i, b in enumerate(self.bands) if i != index),
                                       "name": "Eigene Kurve"})

    def level_db(self, frequencies_hz: NDArray[np.float64]) -> NDArray[np.float64]:
        total = np.zeros_like(frequencies_hz, dtype=float)
        for band in self.bands:
            total += _band_db(band, frequencies_hz)
        return total


def _band_db(band: TargetBand, f: NDArray[np.float64]) -> NDArray[np.float64]:
    """Magnitude in dB of an RBJ biquad (peaking / shelving) at frequencies f."""
    if abs(band.gain_db) < 1e-12:
        return np.zeros_like(f, dtype=float)
    a_gain = 10 ** (band.gain_db / 40)
    w0 = 2 * pi * min(band.frequency_hz, SAMPLE_RATE / 2.2) / SAMPLE_RATE
    alpha = np.sin(w0) / (2 * band.q)
    cos = np.cos(w0)
    if band.kind == "peak":
        b = (1 + alpha * a_gain, -2 * cos, 1 - alpha * a_gain)
        a = (1 + alpha / a_gain, -2 * cos, 1 - alpha / a_gain)
    else:
        sign = 1 if band.kind == "low_shelf" else -1
        beta = 2 * np.sqrt(a_gain) * alpha
        if band.kind == "low_shelf":
            b = (a_gain * ((a_gain + 1) - (a_gain - 1) * cos + beta), 2 * a_gain * ((a_gain - 1) - (a_gain + 1) * cos),
                 a_gain * ((a_gain + 1) - (a_gain - 1) * cos - beta))
            a = ((a_gain + 1) + (a_gain - 1) * cos + beta, -2 * ((a_gain - 1) + (a_gain + 1) * cos),
                 (a_gain + 1) + (a_gain - 1) * cos - beta)
        else:
            b = (a_gain * ((a_gain + 1) + (a_gain - 1) * cos + beta), -2 * a_gain * ((a_gain - 1) + (a_gain + 1) * cos),
                 a_gain * ((a_gain + 1) + (a_gain - 1) * cos - beta))
            a = ((a_gain + 1) - (a_gain - 1) * cos + beta, 2 * ((a_gain - 1) - (a_gain + 1) * cos),
                 (a_gain + 1) - (a_gain - 1) * cos - beta)
        del sign
    z = np.exp(-1j * 2 * pi * np.asarray(f, dtype=float) / SAMPLE_RATE)
    num = b[0] + b[1] * z + b[2] * z ** 2
    den = a[0] + a[1] * z + a[2] * z ** 2
    return np.asarray(20 * np.log10(np.abs(num / den)), dtype=float)


PRESETS: dict[str, TargetCurve] = {
    "Neutral": TargetCurve(),
    "Mehr Tiefbass": TargetCurve(name="Mehr Tiefbass",
                                 bands=(TargetBand(kind="low_shelf", frequency_hz=90.0, gain_db=4.0, q=0.7),)),
    "Warm (Höhen leicht abfallend)": TargetCurve(
        name="Warm (Höhen leicht abfallend)",
        bands=(TargetBand(kind="high_shelf", frequency_hz=3000.0, gain_db=-2.5, q=0.7),)),
}


@dataclass(frozen=True)
class Deviation:
    mean_abs_db: float
    max_abs_db: float
    low_hz: float
    high_hz: float
    reference_offset_db: float


def deviation(curve: TargetCurve, frequencies_hz: Sequence[float], response_db: Sequence[float],
              band_hz: tuple[float, float] = MODEL_BAND_HZ) -> Deviation | None:
    """Deviation of a calculated (relative) response from the target inside the range with model data.

    Both curves are aligned at the median level of :data:`REFERENCE_BAND_HZ`, because the low-frequency
    model is a relative response. Returns None when the response does not cover the comparison band.
    """
    f = np.asarray(frequencies_hz, dtype=float)
    r = np.asarray(response_db, dtype=float)
    target = curve.level_db(f)
    ref = (f >= REFERENCE_BAND_HZ[0]) & (f <= REFERENCE_BAND_HZ[1])
    sel = (f >= band_hz[0]) & (f <= band_hz[1])
    if ref.sum() < 2 or sel.sum() < 4:
        return None
    offset = float(np.median(r[ref] - target[ref]))
    diff = (r - offset - target)[sel]
    return Deviation(float(np.mean(np.abs(diff))), float(np.max(np.abs(diff))),
                     float(f[sel].min()), float(f[sel].max()), offset)


def derive_f3_target_hz(curve: TargetCurve) -> float | None:
    """Lowest-frequency -3 dB point of the target relative to its 200 Hz - 2 kHz median, or None if flat."""
    f = np.geomspace(FREQ_MIN_HZ, 2000.0, 400)
    level = curve.level_db(f)
    mid = float(np.median(level[(f >= 200.0)]))
    below = np.where(level[f <= 200.0] <= mid - 3.0)[0]
    if below.size == 0:
        return None
    index = int(below.max())
    return float(f[index])
