"""Linear lumped-element model of a vented loudspeaker enclosure.

The cone, box compliance and port are solved as coupled complex impedances.
Radiation is a half-space monopole approximation; see docs/MAINTENANCE.md.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import pi, sqrt

import numpy as np
from numpy.typing import NDArray

from lautsprecher_konstruktion.drivers.models import Driver
from lautsprecher_konstruktion.enclosure.ports import PortDesign


@dataclass(frozen=True)
class VentedResponse:
    frequencies_hz: NDArray[np.float64]
    response_db: NDArray[np.float64]
    excursion_mm: NDArray[np.float64] | None
    port_velocity_m_s: NDArray[np.float64] | None
    port_mach: NDArray[np.float64] | None
    group_delay_ms: NDArray[np.float64]
    impedance_ohm: NDArray[np.complex128] | None
    spl_db_1m: NDArray[np.float64] | None
    f3_hz: float | None
    power_w: float
    absolute_available: bool
    upper_f3_hz: float | None = None


def simulate_vented(
    driver: Driver,
    box_volume_m3: float,
    port: PortDesign,
    power_w: float = 1.0,
    frequencies_hz: NDArray[np.float64] | None = None,
    *,
    rho_kg_m3: float = 1.204,
    sound_speed_m_s: float = 343.0,
    ql: float | None = None,
    qa: float | None = None,
    qp: float | None = None,
    resonator_compliance_m5_n: float | None = None,
    resonator_resistance_pa_s_m3: float | None = None,
) -> VentedResponse:
    """Solve cone motion and vent flow for RMS electrical input power.

    Absolute motion needs Sd, Re and Qes. Without these inputs the response and
    group delay remain relative; excursion, velocity, impedance and SPL are None.
    """
    if min(box_volume_m3, port.area_m2, port.effective_length_m, power_w, rho_kg_m3,
           sound_speed_m_s) <= 0:
        raise ValueError("box, port, power and air constants must be positive")
    if any(q is not None and q <= 0 for q in (ql, qa, qp)):
        raise ValueError("loss Q values must be positive")
    f = np.geomspace(10.0, 500.0, 400) if frequencies_hz is None else np.asarray(frequencies_hz, dtype=float)
    if f.ndim != 1 or f.size < 3 or np.any(f <= 0) or np.any(np.diff(f) <= 0):
        raise ValueError("frequencies must be a strictly increasing positive vector")

    w = 2.0 * pi * f
    s = 1j * w
    cb = box_volume_m3 / (rho_kg_m3 * sound_speed_m_s**2)
    mp = rho_kg_m3 * port.effective_length_m / port.area_m2
    wb = 2.0 * pi * port.tuning_hz
    rp = 0.0 if qp is None else wb * mp / qp
    zp = rp + s * mp
    if resonator_compliance_m5_n is not None:
        if resonator_compliance_m5_n <= 0 or resonator_resistance_pa_s_m3 is None or resonator_resistance_pa_s_m3 < 0:
            raise ValueError("passive radiator compliance/resistance must be valid")
        zp = resonator_resistance_pa_s_m3 + s * mp + 1.0 / (s * resonator_compliance_m5_n)
    box_admittance = s * cb + 1.0 / zp
    for loss_q in (ql, qa):
        if loss_q is not None:
            box_admittance = box_admittance + wb * cb / loss_q
    zb = 1.0 / box_admittance

    # With incomplete electrical data, use Qts as the aggregate mechanical
    # damping. This determines only the normalized transfer function.
    complete = all(v is not None for v in (driver.sd_m2, driver.re_ohm, driver.qes))
    sd = driver.sd_m2 if driver.sd_m2 is not None else 1.0
    cs = driver.vas_m3 / (rho_kg_m3 * sound_speed_m_s**2 * sd**2)
    ws = 2.0 * pi * driver.fs_hz
    ms = 1.0 / (ws**2 * cs)
    qs = driver.qms if complete and driver.qms is not None else driver.qts
    rms = ws * ms / qs
    zm = rms + s * ms + 1.0 / (s * cs)
    zmechanical = zm + sd**2 * zb

    impedance: NDArray[np.complex128] | None = None
    excursion: NDArray[np.float64] | None = None
    velocity: NDArray[np.float64] | None = None
    mach: NDArray[np.float64] | None = None
    spl: NDArray[np.float64] | None = None
    if complete:
        assert driver.re_ohm is not None and driver.qes is not None
        # If Qms was omitted, derive it from the Qts/Qes parallel relation.
        if driver.qms is None:
            if driver.qes <= driver.qts:
                raise ValueError("Qes must exceed Qts to derive Qms")
            qs = driver.qes * driver.qts / (driver.qes - driver.qts)
            rms = ws * ms / qs
            zm = rms + s * ms + 1.0 / (s * cs)
            zmechanical = zm + sd**2 * zb
        bl = sqrt(ws * ms * driver.re_ohm / driver.qes)
        ze = driver.re_ohm + s * (driver.le_h or 0.0)
        impedance = ze + bl**2 / zmechanical
        input_voltage = sqrt(power_w * driver.re_ohm)
        current = input_voltage / impedance
        cone_speed = bl * current / zmechanical
    else:
        cone_speed = 1.0 / zmechanical

    u_cone = sd * cone_speed
    u_port = -u_cone * zb / zp
    u_total = u_cone + u_port
    # 2 pi hemispherical radiation, on-axis at 1 m, no baffle diffraction.
    pressure = s * rho_kg_m3 * u_total / (2.0 * pi)
    magnitude = np.maximum(np.abs(pressure), np.finfo(float).tiny)
    ref_mask = (f >= min(150.0, f[-1] * 0.6)) & (f <= min(300.0, f[-1]))
    reference = float(np.median(magnitude[ref_mask])) if np.any(ref_mask) else float(magnitude[-1])
    response_db = 20.0 * np.log10(magnitude / reference)
    phase = np.unwrap(np.angle(pressure))
    group_delay = -1000.0 * np.gradient(phase, w)

    if complete:
        excursion = np.abs(cone_speed / s) * 1000.0
        velocity = np.abs(u_port) / port.area_m2
        mach = velocity / sound_speed_m_s
        spl = 20.0 * np.log10(magnitude / 20e-6)

    crossings = np.flatnonzero((response_db[:-1] < -3.0) & (response_db[1:] >= -3.0))
    f3 = None
    if crossings.size:
        i = int(crossings[0])
        a = (-3.0 - response_db[i]) / (response_db[i + 1] - response_db[i])
        f3 = float(np.exp(np.log(f[i]) + a * (np.log(f[i + 1]) - np.log(f[i]))))
    return VentedResponse(f, response_db, excursion, velocity, mach, group_delay,
                          impedance, spl, f3, power_w, complete)
