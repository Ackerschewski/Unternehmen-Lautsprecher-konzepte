"""Low-frequency infinite-baffle and finite-baffle dipole approximation.

The finite baffle term is the coherent front/rear path difference on axis.
It omits detailed edge diffraction, polar response and room interaction.

Reference model (Olson 1951; Linkwitz "Dipole loudspeakers"): a piston of volume
velocity U radiates front and rear with opposite polarity from two points that
are an effective path length D apart (the shortest way around the baffle edge).
In free space (4 pi) the on-axis pressure is

    p = j w rho U (1 - exp(-j w D / c)) / (4 pi r),   |p| = (w rho U / 4 pi r) 2 |sin(k D / 2)|

so the level relative to the same piston in an infinite baffle (2 pi, U / 2 pi) is
|sin(k D / 2)|: -3 dB at c / (4 D), +/-0 dB maximum at c / (2 D), first null at c / D
and 6 dB per octave fall-off below c / (4 D) (before the driver's own high-pass).
"""
from __future__ import annotations

from math import pi, sqrt

import numpy as np

from lautsprecher_konstruktion.acoustics.vented import VentedResponse
from lautsprecher_konstruktion.arrays import ComplexArray, FloatArray
from lautsprecher_konstruktion.drivers.models import Driver

SPEED_OF_SOUND_M_S = 343.0


def dipole_path_m(width_m: float, height_m: float, driver_x_m: float, driver_y_m: float,
                  wing_depth_m: float = 0.0) -> float:
    """Shortest front-to-rear path around the baffle edges for a driver at (x, y).

    A flat baffle gives twice the distance from the driver axis to the nearest edge
    (a centred driver on a baffle of width W: D = W). H-frame wings of depth d extend
    only the side edges (path 2 (x_edge + d)); the open top and bottom edges are not
    extended, so the nearest of the four edges limits the effective path.
    """
    if min(width_m, height_m) <= 0 or wing_depth_m < 0:
        raise ValueError("baffle dimensions must be positive")
    if not (0 <= driver_x_m <= width_m and 0 <= driver_y_m <= height_m):
        raise ValueError("driver must sit on the baffle")
    side = 2.0 * (min(driver_x_m, width_m - driver_x_m) + wing_depth_m)
    vertical = 2.0 * min(driver_y_m, height_m - driver_y_m)
    return min(side, vertical)


def dipole_frequencies_hz(path_m: float) -> tuple[float, float, float]:
    """(-3 dB corner, level maximum, first cancellation null) of an unequalised dipole."""
    if path_m <= 0:
        raise ValueError("path must be positive")
    c = SPEED_OF_SOUND_M_S
    return c/(4*path_m), c/(2*path_m), c/path_m


def simulate_baffle(driver: Driver, family: str, path_m: float,
                    rear_volume_m3: float | None, power_w: float) -> VentedResponse:
    """Response in dB relative to the same driver in an infinite baffle (mid-band level)."""
    if family not in {"infinite_baffle","open_baffle","dipole"}:
        raise ValueError("Unbekannter Schallwandtyp")
    if driver.vas_m3 is None or path_m <= 0 or power_w <= 0:
        raise ValueError("Vas, Schallweg und Leistung müssen positiv sein")
    f = np.geomspace(10,500,400)
    w = 2*pi*f
    s = 1j*w
    rho,c = 1.204,SPEED_OF_SOUND_M_S
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
    # Infinite baffle: half space (2 pi). Open baffle / dipole: full-space dipole (4 pi)
    # with the rear source delayed by the path D, i.e. |sin(kD/2)| relative to 2 pi.
    wall = np.ones_like(s) if family == "infinite_baffle" else (1-np.exp(-s*path_m/c))/2
    pressure_wall = s*rho*sd*speed/(2*pi)
    pressure = pressure_wall*wall
    magnitude = np.maximum(abs(pressure),np.finfo(float).tiny)
    # Reference: the infinite-baffle (monopole) level in the mid band, never the dipole's own slope.
    reference = float(np.median(abs(pressure_wall)[(f>=150)&(f<=300)]))
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
