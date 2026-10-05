"""Linear lumped-element model of a vented loudspeaker enclosure.

The cone, box compliance and port are solved as coupled complex impedances.
Radiation is a half-space monopole approximation; see docs/MAINTENANCE.md.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import pi, sqrt

import numpy as np
from numpy.typing import NDArray

from lautsprecher_konstruktion.arrays import ComplexArray, FloatArray
from lautsprecher_konstruktion.drivers.models import Driver
from lautsprecher_konstruktion.enclosure.ports import PortDesign


@dataclass(frozen=True)
class VentedResponse:
    frequencies_hz: FloatArray
    response_db: FloatArray
    excursion_mm: FloatArray | None
    port_velocity_m_s: FloatArray | None
    port_mach: FloatArray | None
    group_delay_ms: FloatArray
    impedance_ohm: ComplexArray | None
    spl_db_1m: FloatArray | None
    f3_hz: float | None
    power_w: float
    absolute_available: bool
    upper_f3_hz: float | None = None
    front_port_velocity_m_s: FloatArray | None = None
    rear_port_velocity_m_s: FloatArray | None = None
    rear_response_db: FloatArray | None = None
    front_to_back_db: FloatArray | None = None


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
    port_resistance_pa_s_m3: float | None = None,
    rear_port_separation_m: float | None = None,
    rear_port_delay_s: float = 0.0,
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
    if port_resistance_pa_s_m3 is not None and port_resistance_pa_s_m3 <= 0:
        raise ValueError("port resistance must be positive")
    f = np.geomspace(10.0, 500.0, 400) if frequencies_hz is None else np.asarray(frequencies_hz, dtype=float)
    if f.ndim != 1 or f.size < 3 or np.any(f <= 0) or np.any(np.diff(f) <= 0):
        raise ValueError("frequencies must be a strictly increasing positive vector")

    w = 2.0 * pi * f
    s = 1j * w
    cb = box_volume_m3 / (rho_kg_m3 * sound_speed_m_s**2)
    mp = rho_kg_m3 * port.effective_length_m / port.area_m2
    wb = 2.0 * pi * port.tuning_hz
    rp = (port_resistance_pa_s_m3 if port_resistance_pa_s_m3 is not None else
          0.0 if qp is None else wb * mp / qp)
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
    cs = driver.require_vas_m3() / (rho_kg_m3 * sound_speed_m_s**2 * sd**2)
    ws = 2.0 * pi * driver.fs_hz
    ms = 1.0 / (ws**2 * cs)
    qs = driver.qms if complete and driver.qms is not None else driver.qts
    rms = ws * ms / qs
    zm = rms + s * ms + 1.0 / (s * cs)
    zmechanical = zm + sd**2 * zb

    impedance: ComplexArray | None = None
    excursion: FloatArray | None = None
    velocity: FloatArray | None = None
    mach: FloatArray | None = None
    spl: FloatArray | None = None
    cone_speed: ComplexArray
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
        cone_speed = np.asarray(1.0 / zmechanical, dtype=complex)

    u_cone = sd * cone_speed
    u_port = -u_cone * zb / zp
    rear_pressure = None
    if rear_port_separation_m is not None:
        if rear_port_separation_m <= 0 or rear_port_delay_s < 0:
            raise ValueError("rear port separation/delay must be valid")
        # Two spatially separated monopoles: the rear source is delayed by
        # the resistive path. The second axis has the opposite travel phase.
        phase_front = np.exp(-1j*w*(rear_port_delay_s+rear_port_separation_m/sound_speed_m_s))
        phase_back = np.exp(-1j*w*(rear_port_delay_s-rear_port_separation_m/sound_speed_m_s))
        u_total = u_cone + u_port*phase_front
        rear_pressure = s*rho_kg_m3*(u_cone+u_port*phase_back)/(2*pi)
    else:
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
    rear_db = front_back = None
    if rear_pressure is not None:
        rear_magnitude = np.maximum(abs(rear_pressure),np.finfo(float).tiny)
        rear_db = 20*np.log10(rear_magnitude/reference)
        front_back = response_db-rear_db
    return VentedResponse(f, response_db, excursion, velocity, mach, group_delay,
                          impedance, spl, f3, power_w, complete,
                          rear_response_db=rear_db,front_to_back_db=front_back)
