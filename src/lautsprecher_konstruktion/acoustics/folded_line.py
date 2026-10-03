"""Linear plane-wave transfer-matrix model for a segmented folded line.

The model resolves axial standing waves and mouth radiation below 500 Hz.
Fold losses, stuffing and outlet radiation are approximations; use measured
impedance/response to trim a physical prototype.
"""
from __future__ import annotations

from math import pi, sqrt

import numpy as np

from lautsprecher_konstruktion.acoustics.vented import VentedResponse
from lautsprecher_konstruktion.drivers.models import Driver
from lautsprecher_konstruktion.enclosure.folded_line import FoldedLine, mouth_equivalent_radius_m
from lautsprecher_konstruktion.enclosure.ports import PortDesign


def simulate_folded_line(driver: Driver, line: FoldedLine, power_w: float,
                         outlet: PortDesign | None = None) -> VentedResponse:
    if driver.vas_m3 is None or power_w <= 0:
        raise ValueError("Vas und positive Eingangsleistung erforderlich")
    f = np.geomspace(10.0,500.0,400)
    w = 2*pi*f
    s = 1j*w
    rho,c = 1.204,343.0
    count = len(line.channel_areas_m2)
    turns = [(a+b)/2 for a,b in zip(line.channel_heights_m,
                                      line.channel_heights_m[1:])]
    straight = (line.path_length_m-sum(turns))/(count-1)
    segments: list[tuple[float,float]] = []
    for i, area in enumerate(line.channel_areas_m2):
        segments.append((area,straight*(0.5 if i in (0,count-1) else 1.0)))
        if i < count-1:
            segments.append((sqrt(area*line.channel_areas_m2[i+1]),turns[i]))
    a = np.ones_like(f,dtype=complex)
    b = np.zeros_like(a)
    cc = np.zeros_like(a)
    d = np.ones_like(a)
    loss = 0.04 if line.family == "labyrinth" else 0.022
    gamma = (loss+1j)*w/c
    for area,length in segments:
        zc = rho*c/area
        ch = np.cosh(gamma*length)
        sh = np.sinh(gamma*length)
        aa,bb,ccc,dd = ch,zc*sh,sh/zc,ch
        a,b,cc,d = a*aa+b*ccc,a*bb+b*dd,cc*aa+d*ccc,cc*bb+d*dd
    closed = line.family == "transmission_line_closed"
    if closed:
        zin = a/cc
        flow_factor = np.zeros_like(a)
        outlet_area = None
    else:
        if outlet is not None and line.family == "mltl":
            outlet_area = outlet.area_m2
            mass = rho*outlet.effective_length_m/outlet.area_m2
            load = (2*pi*outlet.tuning_hz*mass/7+s*mass+
                    rho*c/outlet.area_m2*0.08)
        else:
            outlet_area = line.mouth_width_m*line.mouth_height_m
            radius = mouth_equivalent_radius_m(line)
            ka = w*radius/c
            load = rho*c/outlet_area*(0.25*ka**2+0.61j*ka)
        zin = (a*load+b)/(cc*load+d)
        flow_factor = 1/(cc*load+d)

    complete = all(v is not None for v in (driver.sd_m2,driver.re_ohm,driver.qes))
    sd = driver.sd_m2 if driver.sd_m2 is not None else 1.0
    compliance = driver.vas_m3/(rho*c*c*sd*sd)
    ws = 2*pi*driver.fs_hz
    mass = 1/(ws*ws*compliance)
    qms = (driver.qms if complete and driver.qms is not None else driver.qts)
    if complete and driver.qms is None:
        assert driver.qes is not None
        if driver.qes <= driver.qts:
            raise ValueError("Qes muss größer als Qts sein")
        qms = driver.qes*driver.qts/(driver.qes-driver.qts)
    zm = ws*mass/qms+s*mass+1/(s*compliance)
    ztotal = zm+sd*sd*zin
    impedance = None
    excursion = velocity = mach = spl = None
    if complete:
        assert driver.re_ohm is not None and driver.qes is not None
        bl = sqrt(ws*mass*driver.re_ohm/driver.qes)
        ze = driver.re_ohm+s*(driver.le_h or 0.0)
        impedance = ze+bl*bl/ztotal
        cone_speed = bl*(sqrt(power_w*driver.re_ohm)/impedance)/ztotal
    else:
        cone_speed = 1/ztotal
    ucone = sd*cone_speed
    umouth = -ucone*flow_factor
    pressure = s*rho*(ucone+umouth)/(2*pi)
    magnitude = np.maximum(abs(pressure),np.finfo(float).tiny)
    reference = float(np.median(magnitude[(f>=150)&(f<=300)]))
    response_db = 20*np.log10(magnitude/reference)
    phase = np.unwrap(np.angle(pressure))
    delay = -1000*np.gradient(phase,w)
    if complete:
        excursion = abs(cone_speed/s)*1000
        if outlet_area is not None:
            velocity = abs(umouth)/outlet_area
            mach = velocity/c
        spl = 20*np.log10(magnitude/20e-6)
    crossings = np.flatnonzero((response_db[:-1]<-3)&(response_db[1:]>=-3))
    f3 = None
    if crossings.size:
        i = int(crossings[0])
        alpha = (-3-response_db[i])/(response_db[i+1]-response_db[i])
        f3 = float(np.exp(np.log(f[i])+alpha*(np.log(f[i+1])-np.log(f[i]))))
    return VentedResponse(f,response_db,excursion,velocity,mach,delay,
                          impedance,spl,f3,power_w,complete)
