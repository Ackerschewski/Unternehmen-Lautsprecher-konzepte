"""Linear two-chamber bandpass model with one or two external vents.

The driver sees the acoustic impedances of both chambers; only the front
chamber vent radiates for fourth order; both vents radiate for parallel sixth
order. Losses and higher cavity/duct modes are omitted.
"""
from __future__ import annotations

from math import pi, sqrt

import numpy as np

from lautsprecher_konstruktion.acoustics.vented import VentedResponse
from lautsprecher_konstruktion.arrays import ComplexArray, FloatArray
from lautsprecher_konstruktion.drivers.models import Driver
from lautsprecher_konstruktion.enclosure.ports import PortDesign


def simulate_bandpass(
    driver: Driver, rear_volume_m3: float, front_volume_m3: float,
    port: PortDesign, power_w: float = 1.0,
    *, rear_port: PortDesign | None = None, rear_port_path_m: float = 0.0,
    rho_kg_m3: float = 1.204, sound_speed_m_s: float = 343.0,
) -> VentedResponse:
    """Fourth-order (rear port None) or parallel sixth-order bandpass.

    ``rear_port_path_m`` is the extra acoustic path of the rear-chamber port to a
    listener on the front axis, e.g. the cabinet depth if it exits through the
    back wall; it delays the rear port's contribution.
    """
    if min(rear_volume_m3, front_volume_m3, power_w, port.area_m2,
           port.effective_length_m) <= 0:
        raise ValueError("Bandpass-Volumen, Port und Leistung müssen positiv sein")
    if rear_port is not None and min(rear_port.area_m2, rear_port.effective_length_m) <= 0:
        raise ValueError("Der zweite Port muss eine positive Fläche und Länge haben")
    f = np.geomspace(10.0, 500.0, 400)
    w = 2*pi*f
    s = 1j*w
    cf = front_volume_m3/(rho_kg_m3*sound_speed_m_s**2)
    cr = rear_volume_m3/(rho_kg_m3*sound_speed_m_s**2)
    zp = s*rho_kg_m3*port.effective_length_m/port.area_m2
    zfront = 1/(s*cf + 1/zp)
    zrp = (s*rho_kg_m3*rear_port.effective_length_m/rear_port.area_m2
           if rear_port is not None else None)
    zrear = 1/(s*cr + (1/zrp if zrp is not None else 0))

    complete = all(v is not None for v in (driver.sd_m2, driver.re_ohm, driver.qes))
    sd = driver.sd_m2 if driver.sd_m2 is not None else 1.0
    cs = driver.require_vas_m3()/(rho_kg_m3*sound_speed_m_s**2*sd**2)
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
    impedance: ComplexArray | None = None
    excursion: FloatArray | None = None
    speed: FloatArray | None = None
    cone_speed: ComplexArray
    front_speed = None
    rear_speed = None
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
        cone_speed = np.asarray(1/ztotal, dtype=complex)

    u_port = -sd*cone_speed*zfront/zp
    # Rear-chamber volume velocity has the opposite sign at the diaphragm.
    # Coherent summation assumes colocated port outlets in the far field.
    u_rear = sd*cone_speed*zrear/zrp if zrp is not None else None
    if u_rear is not None and rear_port_path_m > 0:
        u_rear = u_rear*np.exp(-1j*w*rear_port_path_m/sound_speed_m_s)
    pressure = s*rho_kg_m3*(u_port + (u_rear if u_rear is not None else 0))/(2*pi)
    magnitude = np.maximum(np.abs(pressure), np.finfo(float).tiny)
    # A bandpass is normalized to its peak, not to a high-frequency shelf.
    reference = float(np.max(magnitude))
    response_db = 20*np.log10(magnitude/reference)
    phase = np.unwrap(np.angle(pressure))
    delay = -1000*np.gradient(phase,w)
    if complete:
        front_speed = np.abs(u_port)/port.area_m2
        speed = front_speed
        if rear_port is not None and u_rear is not None:
            rear_speed = np.abs(u_rear)/rear_port.area_m2
            speed = np.maximum(speed, rear_speed)
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
                          impedance, spl, f3, power_w, complete, upper_f3,
                          front_speed, rear_speed)


def simulate_bandpass_series(
    driver: Driver, rear_volume_m3: float, front_volume_m3: float,
    external_port: PortDesign, internal_port: PortDesign, power_w: float = 1.0,
    *, port_q: float = 7.0, rho_kg_m3: float = 1.204,
    sound_speed_m_s: float = 343.0,
) -> VentedResponse:
    """Two coupled cavities: rear -> internal duct -> front -> external duct.

    Pressures at the two cavity nodes are solved from their admittance matrix.
    Only the external duct radiates; the internal duct supplies a second tuning.
    """
    if min(rear_volume_m3, front_volume_m3, power_w, external_port.area_m2,
           external_port.effective_length_m, internal_port.area_m2,
           internal_port.effective_length_m, port_q) <= 0:
        raise ValueError("Bandpass-Volumina, beide Ports und Leistung müssen positiv sein")
    f = np.geomspace(10.0, 500.0, 400)
    w = 2*pi*f
    s = 1j*w
    cf = front_volume_m3/(rho_kg_m3*sound_speed_m_s**2)
    cr = rear_volume_m3/(rho_kg_m3*sound_speed_m_s**2)
    mext = rho_kg_m3*external_port.effective_length_m/external_port.area_m2
    mint = rho_kg_m3*internal_port.effective_length_m/internal_port.area_m2
    zext = 2*pi*external_port.tuning_hz*mext/port_q+s*mext
    zint = 2*pi*internal_port.tuning_hz*mint/port_q+s*mint
    yint = 1/zint
    a = s*cf + 1/zext + yint
    d = s*cr + yint
    b = -yint
    determinant = a*d-b*b
    # Unit diaphragm volume velocity enters the front and leaves the rear.
    pfront_per_u = (d+b)/determinant
    prear_per_u = -(a+b)/determinant
    acoustic_load = pfront_per_u-prear_per_u

    complete = all(v is not None for v in (driver.sd_m2, driver.re_ohm, driver.qes))
    sd = driver.sd_m2 if driver.sd_m2 is not None else 1.0
    cs = driver.require_vas_m3()/(rho_kg_m3*sound_speed_m_s**2*sd**2)
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
    ztotal = zm + sd**2*acoustic_load
    impedance: ComplexArray | None = None
    excursion: FloatArray | None = None
    spl: FloatArray | None = None
    front_speed: FloatArray | None = None
    rear_speed: FloatArray | None = None
    speed: FloatArray | None = None
    mach: FloatArray | None = None
    if complete:
        assert driver.re_ohm is not None and driver.qes is not None
        bl = sqrt(ws*ms*driver.re_ohm/driver.qes)
        ze = driver.re_ohm+s*(driver.le_h or 0.0)
        impedance = ze+bl**2/ztotal
        current = sqrt(power_w*driver.re_ohm)/impedance
        cone_speed = bl*current/ztotal
        excursion = np.abs(cone_speed/s)*1000
    else:
        cone_speed = 1/ztotal
    u = sd*cone_speed
    u_external = u*pfront_per_u/zext
    u_internal = u*(prear_per_u-pfront_per_u)/zint
    pressure = s*rho_kg_m3*u_external/(2*pi)
    magnitude = np.maximum(np.abs(pressure),np.finfo(float).tiny)
    response_db = 20*np.log10(magnitude/float(np.max(magnitude)))
    phase = np.unwrap(np.angle(pressure))
    delay = -1000*np.gradient(phase,w)
    if complete:
        front_speed = np.abs(u_external)/external_port.area_m2
        rear_speed = np.abs(u_internal)/internal_port.area_m2
        speed = np.maximum(front_speed,rear_speed)
        mach = speed/sound_speed_m_s
        spl = 20*np.log10(magnitude/20e-6)
    lower = np.flatnonzero((response_db[:-1] < -3) & (response_db[1:] >= -3))
    upper = np.flatnonzero((response_db[:-1] >= -3) & (response_db[1:] < -3))

    def crossing(index: int | None) -> float | None:
        if index is None:
            return None
        alpha = (-3-response_db[index])/(response_db[index+1]-response_db[index])
        return float(np.exp(np.log(f[index])+alpha*(np.log(f[index+1])-np.log(f[index]))))

    return VentedResponse(f,response_db,excursion,speed,mach,delay,impedance,spl,
                          crossing(int(lower[0])) if lower.size else None,
                          power_w,complete,crossing(int(upper[-1])) if upper.size else None,
                          front_speed,rear_speed)
