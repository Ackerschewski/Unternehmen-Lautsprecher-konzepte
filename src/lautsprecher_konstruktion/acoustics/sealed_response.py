"""Linear lumped-element response of a sealed box: excursion, impedance, group delay and SPL.

Same driver model as the vented solver; the box is a pure air spring (optionally with leakage
loss Ql) and all radiation comes from the cone. Port-related fields stay None.
"""
from __future__ import annotations

from math import pi, sqrt

import numpy as np

from lautsprecher_konstruktion.acoustics.vented import VentedResponse
from lautsprecher_konstruktion.arrays import ComplexArray, FloatArray
from lautsprecher_konstruktion.drivers.models import Driver


def simulate_sealed(driver: Driver, box_volume_m3: float, power_w: float = 1.0,
                    frequencies_hz: FloatArray | None = None, *, rho_kg_m3: float = 1.204,
                    sound_speed_m_s: float = 343.0, ql: float | None = None) -> VentedResponse:
    """Absolute values need Sd, Re and Qes; without them only the normalized response is returned."""
    if min(box_volume_m3, power_w, rho_kg_m3, sound_speed_m_s) <= 0:
        raise ValueError("box, power and air constants must be positive")
    if ql is not None and ql <= 0:
        raise ValueError("loss Q must be positive")
    f = np.geomspace(10.0, 500.0, 400) if frequencies_hz is None else np.asarray(frequencies_hz, dtype=float)
    if f.ndim != 1 or f.size < 3 or np.any(f <= 0) or np.any(np.diff(f) <= 0):
        raise ValueError("frequencies must be a strictly increasing positive vector")
    w = 2.0 * pi * f
    s = 1j * w
    cb = box_volume_m3 / (rho_kg_m3 * sound_speed_m_s**2)
    admittance = s * cb
    if ql is not None:
        admittance = admittance + 2.0 * pi * driver.fs_hz * cb / ql
    zbox = 1.0 / admittance
    complete = driver.sd_m2 is not None and driver.re_ohm is not None and driver.qes is not None
    sd = driver.sd_m2 if driver.sd_m2 is not None else 1.0
    cs = driver.require_vas_m3() / (rho_kg_m3 * sound_speed_m_s**2 * sd**2)
    ws = 2.0 * pi * driver.fs_hz
    ms = 1.0 / (ws**2 * cs)
    qms = driver.qms if complete and driver.qms is not None else driver.qts
    if complete and driver.qms is None:
        assert driver.qes is not None
        if driver.qes <= driver.qts:
            raise ValueError("Qes must exceed Qts to derive Qms")
        qms = driver.qes * driver.qts / (driver.qes - driver.qts)
    zmech = ws * ms / qms + s * ms + 1.0 / (s * cs) + sd**2 * zbox
    impedance: ComplexArray | None = None
    excursion: FloatArray | None = None
    spl: FloatArray | None = None
    cone_speed: ComplexArray
    if complete:
        assert driver.re_ohm is not None and driver.qes is not None
        bl = sqrt(ws * ms * driver.re_ohm / driver.qes)
        impedance = driver.re_ohm + s * (driver.le_h or 0.0) + bl**2 / zmech
        cone_speed = np.asarray(bl * (sqrt(power_w * driver.re_ohm) / impedance) / zmech, dtype=complex)
        excursion = np.abs(cone_speed / s) * 1000.0
    else:
        cone_speed = np.asarray(1.0 / zmech, dtype=complex)
    pressure = s * rho_kg_m3 * sd * cone_speed / (2.0 * pi)  # half-space monopole, 1 m
    magnitude = np.maximum(np.abs(pressure), np.finfo(float).tiny)
    ref = (f >= min(150.0, f[-1] * 0.6)) & (f <= min(300.0, f[-1]))
    reference = float(np.median(magnitude[ref])) if np.any(ref) else float(magnitude[-1])
    response_db = 20.0 * np.log10(magnitude / reference)
    group_delay = -1000.0 * np.gradient(np.unwrap(np.angle(pressure)), w)
    if complete:
        spl = 20.0 * np.log10(magnitude / 20e-6)
    crossings = np.flatnonzero((response_db[:-1] < -3.0) & (response_db[1:] >= -3.0))
    f3 = None
    if crossings.size:
        i = int(crossings[0])
        a = (-3.0 - response_db[i]) / (response_db[i + 1] - response_db[i])
        f3 = float(np.exp(np.log(f[i]) + a * (np.log(f[i + 1]) - np.log(f[i]))))
    return VentedResponse(f, response_db, excursion, None, None, group_delay, impedance, spl, f3, power_w, complete)
