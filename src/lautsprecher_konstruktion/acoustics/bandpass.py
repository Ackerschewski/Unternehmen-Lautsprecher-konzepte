"""Linear two-chamber, single-tuned fourth-order bandpass model.

The driver sees the acoustic impedances of both chambers; only the front
chamber vent radiates. Losses and higher cavity/duct modes are omitted.
"""
from __future__ import annotations

from math import pi, sqrt

import numpy as np

from lautsprecher_konstruktion.acoustics.vented import VentedResponse
from lautsprecher_konstruktion.drivers.models import Driver
from lautsprecher_konstruktion.enclosure.ports import PortDesign


def simulate_bandpass(
    driver: Driver, rear_volume_m3: float, front_volume_m3: float,
    port: PortDesign, power_w: float = 1.0,
    *, rho_kg_m3: float = 1.204, sound_speed_m_s: float = 343.0,
) -> VentedResponse:
    if min(rear_volume_m3, front_volume_m3, power_w, port.area_m2,
           port.effective_length_m) <= 0:
        raise ValueError("Bandpass-Volumen, Port und Leistung müssen positiv sein")
    f = np.geomspace(10.0, 500.0, 400)
    w = 2*pi*f
    s = 1j*w
    cf = front_volume_m3/(rho_kg_m3*sound_speed_m_s**2)
    cr = rear_volume_m3/(rho_kg_m3*sound_speed_m_s**2)
    zp = s*rho_kg_m3*port.effective_length_m/port.area_m2
    zfront = 1/(s*cf + 1/zp)
    zrear = 1/(s*cr)

    complete = all(v is not None for v in (driver.sd_m2, driver.re_ohm, driver.qes))
    sd = driver.sd_m2 if driver.sd_m2 is not None else 1.0
    cs = driver.vas_m3/(rho_kg_m3*sound_speed_m_s**2*sd**2)
    ws = 2*pi*driver.fs_hz
    ms = 1/(ws**2*cs)
    if complete and driver.qms is not None:
        qms = driver.qms
    elif complete:
        assert driver.qes is not None
        if driver.qes <= driver.qts:
            raise ValueError("Qes muss größer als Qts sein")
        qms = driver.qes*driver.qts/(driver.qes-driver.qts)
    else:
        qms = driver.qts
    zm = ws*ms/qms + s*ms + 1/(s*cs)
    ztotal = zm + sd**2*(zfront+zrear)
    impedance = None
    excursion = None
    speed = None
    mach = None
    spl = None
    if complete:
        assert driver.re_ohm is not None and driver.qes is not None
        bl = sqrt(ws*ms*driver.re_ohm/driver.qes)
        ze = driver.re_ohm + s*(driver.le_h or 0.0)
        impedance = ze + bl**2/ztotal
        current = sqrt(power_w*driver.re_ohm)/impedance
        cone_speed = bl*current/ztotal
        excursion = np.abs(cone_speed/s)*1000
    else:
        cone_speed = 1/ztotal

    u_port = -sd*cone_speed*zfront/zp
    pressure = s*rho_kg_m3*u_port/(2*pi)
    magnitude = np.maximum(np.abs(pressure), np.finfo(float).tiny)
    # A bandpass is normalized to its peak, not to a high-frequency shelf.
    reference = float(np.max(magnitude))
    response_db = 20*np.log10(magnitude/reference)
    phase = np.unwrap(np.angle(pressure))
    delay = -1000*np.gradient(phase,w)
    if complete:
        speed = np.abs(u_port)/port.area_m2
        mach = speed/sound_speed_m_s
        spl = 20*np.log10(magnitude/20e-6)
    crossings = np.flatnonzero((response_db[:-1] < -3) & (response_db[1:] >= -3))
    f3 = None
    if crossings.size:
        i = int(crossings[0])
        alpha = (-3-response_db[i])/(response_db[i+1]-response_db[i])
        f3 = float(np.exp(np.log(f[i])+alpha*(np.log(f[i+1])-np.log(f[i]))))
    upper_crossings = np.flatnonzero((response_db[:-1] >= -3) & (response_db[1:] < -3))
    upper_f3 = None
    if upper_crossings.size:
        i = int(upper_crossings[-1])
        alpha = (-3-response_db[i])/(response_db[i+1]-response_db[i])
        upper_f3 = float(np.exp(np.log(f[i])+alpha*(np.log(f[i+1])-np.log(f[i]))))
    return VentedResponse(f, response_db, excursion, speed, mach, delay,
                          impedance, spl, f3, power_w, complete, upper_f3)
