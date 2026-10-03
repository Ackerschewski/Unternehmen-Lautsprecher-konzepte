"""Electrical two-way network against measured or nominal complex driver loads."""
from __future__ import annotations

from dataclasses import dataclass
from math import pi

import numpy as np
from numpy.typing import NDArray

from lautsprecher_konstruktion.crossover.measurements import FrequencyResponseData, ImpedanceData
from lautsprecher_konstruktion.crossover.passive import CrossoverDesign


@dataclass(frozen=True)
class CrossoverResponse:
    frequencies_hz: NDArray[np.float64]
    woofer_voltage: NDArray[np.complex128]
    tweeter_voltage: NDArray[np.complex128]
    total_impedance: NDArray[np.complex128]
    woofer_acoustic_db: NDArray[np.float64] | None
    tweeter_acoustic_db: NDArray[np.float64] | None
    sum_acoustic_db: NDArray[np.float64] | None
    phase_complete: bool
    measured_impedance_used: bool


def _parallel(*impedances: NDArray[np.complex128] | complex) -> NDArray[np.complex128]:
    return 1.0 / sum(1.0 / z for z in impedances)


def _load(data: ImpedanceData | None, nominal: float, f: NDArray[np.float64]) -> NDArray[np.complex128]:
    if data is None:
        return np.full(f.shape, complex(nominal), dtype=np.complex128)
    x = np.log(np.asarray(data.frequencies_hz))
    magnitude = np.interp(np.log(f), x, data.magnitude_ohm)
    phase = np.interp(np.log(f), x, np.unwrap(np.deg2rad(data.phase_deg)))
    result = magnitude * np.exp(1j * phase)
    result[(f < data.frequencies_hz[0]) | (f > data.frequencies_hz[-1])] = np.nan
    return result


def _acoustic(data: FrequencyResponseData, f: NDArray[np.float64]) -> NDArray[np.complex128]:
    x = np.log(np.asarray(data.frequencies_hz))
    mag = 10.0 ** (np.interp(np.log(f), x, data.magnitude_db) / 20.0)
    phase = (np.interp(np.log(f), x, np.unwrap(np.deg2rad(data.phase_deg)))
             if data.phase_deg is not None else np.zeros_like(f))
    result = mag * np.exp(1j * phase)
    result[(f < data.frequencies_hz[0]) | (f > data.frequencies_hz[-1])] = np.nan
    return result


def simulate_crossover(
    design: CrossoverDesign,
    woofer_nominal_ohm: float,
    tweeter_nominal_ohm: float,
    woofer_zma: ImpedanceData | None = None,
    tweeter_zma: ImpedanceData | None = None,
    woofer_frd: FrequencyResponseData | None = None,
    tweeter_frd: FrequencyResponseData | None = None,
    frequencies_hz: NDArray[np.float64] | None = None,
) -> CrossoverResponse:
    if min(woofer_nominal_ohm, tweeter_nominal_ohm) <= 0:
        raise ValueError("nominal impedances must be positive")
    f = np.geomspace(20.0, 20_000.0, 500) if frequencies_hz is None else np.asarray(frequencies_hz, dtype=float)
    if f.ndim != 1 or np.any(f <= 0) or np.any(np.diff(f) <= 0):
        raise ValueError("frequencies must increase strictly")
    s = 2j * pi * f
    wload = _load(woofer_zma, woofer_nominal_ohm, f)
    tload = _load(tweeter_zma, tweeter_nominal_ohm, f)
    parts = {c.reference: c for c in design.components}

    wz = wload
    if "Rz" in parts and "Cz" in parts:
        zobel = parts["Rz"].value_si + 1.0 / (s * parts["Cz"].value_si)
        wz = _parallel(wz, zobel)
    if "C1" in parts and parts["C1"].connection == "shunt":
        wz = _parallel(wz, 1.0 / (s * parts["C1"].value_si))
    wl = s * parts["L1"].value_si
    winput = wl + wz
    wvoltage = wz / winput

    pad_parallel = tload
    if "Rpad-P" in parts:
        pad_parallel = _parallel(tload, complex(parts["Rpad-P"].value_si))
    pad_input = pad_parallel + (parts["Rpad-S"].value_si if "Rpad-S" in parts else 0.0)
    tz = pad_input
    if "L2" in parts:
        tz = _parallel(tz, s * parts["L2"].value_si)
    tc_ref = "C2" if "C2" in parts else "C1"
    tinput = 1.0 / (s * parts[tc_ref].value_si) + tz
    tvoltage = tz / tinput * pad_parallel / pad_input
    total = _parallel(winput, tinput)

    wa = ta = summed = None
    phase_complete = False
    if woofer_frd is not None and tweeter_frd is not None:
        wc = wvoltage * _acoustic(woofer_frd, f)
        tc = tvoltage * _acoustic(tweeter_frd, f)
        wa = 20 * np.log10(np.maximum(np.abs(wc), 1e-15))
        ta = 20 * np.log10(np.maximum(np.abs(tc), 1e-15))
        phase_complete = woofer_frd.phase_deg is not None and tweeter_frd.phase_deg is not None
        summed = 20 * np.log10(np.maximum(np.abs(wc + tc) if phase_complete else
                                      np.abs(wc) + np.abs(tc), 1e-15))
    return CrossoverResponse(f, wvoltage, tvoltage, total, wa, ta, summed,
                             phase_complete, woofer_zma is not None or tweeter_zma is not None)
