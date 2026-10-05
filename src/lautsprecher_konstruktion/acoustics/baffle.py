"""Low-frequency infinite-baffle and finite-baffle dipole approximation.

The finite baffle term is the coherent front/rear path difference on axis.
It omits detailed edge diffraction, polar response and room interaction.
"""
from __future__ import annotations

from math import pi, sqrt

import numpy as np

from lautsprecher_konstruktion.acoustics.vented import VentedResponse
from lautsprecher_konstruktion.arrays import ComplexArray, FloatArray
from lautsprecher_konstruktion.drivers.models import Driver


def simulate_baffle(driver: Driver, family: str, path_m: float,
                    rear_volume_m3: float | None, power_w: float) -> VentedResponse:
    if family not in {"infinite_baffle","open_baffle","dipole"}:
        raise ValueError("Unbekannter Schallwandtyp")
    if driver.vas_m3 is None or path_m <= 0 or power_w <= 0:
        raise ValueError("Vas, Schallweg und Leistung müssen positiv sein")
    f = np.geomspace(10,500,400)
    w = 2*pi*f
    s = 1j*w
    rho,c = 1.204,343.0
    complete = all(v is not None for v in (driver.sd_m2,driver.re_ohm,driver.qes))
    sd = driver.sd_m2 if driver.sd_m2 is not None else 1.0
    cs = driver.vas_m3/(rho*c*c*sd*sd)
    ws = 2*pi*driver.fs_hz
    ms = 1/(ws*ws*cs)
    qms = driver.qms if complete and driver.qms is not None else driver.qts
    if complete and driver.qms is None:
        assert driver.qes is not None
        if driver.qes <= driver.qts:
            raise ValueError("Qes muss größer als Qts sein")
        qms = driver.qes*driver.qts/(driver.qes-driver.qts)
    zmechanical = ws*ms/qms+s*ms+1/(s*cs)
    if rear_volume_m3 is not None:
        cb = rear_volume_m3/(rho*c*c)
        zmechanical += sd*sd/(s*cb)
    impedance: ComplexArray | None = None
    excursion: FloatArray | None = None
    spl: FloatArray | None = None
    if complete:
        assert driver.re_ohm is not None and driver.qes is not None
        bl = sqrt(ws*ms*driver.re_ohm/driver.qes)
        ze = driver.re_ohm+s*(driver.le_h or 0.0)
        impedance = ze+bl*bl/zmechanical
        speed = bl*(sqrt(power_w*driver.re_ohm)/impedance)/zmechanical
        excursion = abs(speed/s)*1000
    else:
        speed = np.asarray(1/zmechanical, dtype=complex)
    cancellation = (np.ones_like(s) if family == "infinite_baffle" else
                    1-np.exp(-s*path_m/c))
    pressure = s*rho*sd*speed*cancellation/(2*pi)
    magnitude = np.maximum(abs(pressure),np.finfo(float).tiny)
    reference = float(np.median(magnitude[(f>=150)&(f<=300)]))
    response = 20*np.log10(magnitude/reference)
    delay = -1000*np.gradient(np.unwrap(np.angle(pressure)),w)
    if complete:
        spl = 20*np.log10(magnitude/20e-6)
    crossings = np.flatnonzero((response[:-1]<-3)&(response[1:]>=-3))
    f3 = None
    if crossings.size:
        i = int(crossings[0])
        fraction = (-3-response[i])/(response[i+1]-response[i])
        f3 = float(np.exp(np.log(f[i])+fraction*(np.log(f[i+1])-np.log(f[i]))))
    return VentedResponse(f,response,excursion,None,None,delay,
                          impedance,spl,f3,power_w,complete)
