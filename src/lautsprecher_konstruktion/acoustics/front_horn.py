"""Sectioned exponential horn on the cone front; sealed air volume on its rear.

The transfer matrix uses the built (pyramid-frustum) areas of the sections."""
from __future__ import annotations

from math import pi, sqrt

import numpy as np

from lautsprecher_konstruktion.acoustics.vented import VentedResponse
from lautsprecher_konstruktion.acoustics.waveguide import duct_chain, radiation_load, terminated
from lautsprecher_konstruktion.arrays import ComplexArray
from lautsprecher_konstruktion.drivers.models import Driver
from lautsprecher_konstruktion.enclosure.front_horn import FrontHorn


def simulate_front_horn(driver: Driver, rear_volume_m3: float,
                        horn: FrontHorn, power_w: float) -> VentedResponse:
    if driver.vas_m3 is None or rear_volume_m3 <= 0 or power_w <= 0:
        raise ValueError("Front-Horn benötigt Vas, Rückvolumen und Leistung")
    f=np.geomspace(10,500,400)
    w=2*pi*f
    s=1j*w
    rho,c=1.204,343.0
    chain=duct_chain(((area,length,0.012) for area,length in horn.acoustic_segments()),w)
    radius=sqrt(horn.mouth_area_m2/pi)
    radiation=radiation_load(f,horn.mouth_area_m2,radius)
    zin,flow_factor=terminated(chain,radiation)
    complete=all(v is not None for v in (driver.sd_m2,driver.re_ohm,driver.qes))
    sd=driver.sd_m2 if driver.sd_m2 is not None else 1.0
    cs=driver.vas_m3/(rho*c*c*sd*sd)
    cb=rear_volume_m3/(rho*c*c)
    ws=2*pi*driver.fs_hz
    ms=1/(ws*ws*cs)
    qms=driver.qms if complete and driver.qms is not None else driver.qts
    if complete and driver.qms is None:
        assert driver.qes is not None
        if driver.qes<=driver.qts:
            raise ValueError("Qes muss größer als Qts sein")
        qms=driver.qes*driver.qts/(driver.qes-driver.qts)
    mechanical=ws*ms/qms+s*ms+1/(s*cs)+sd*sd*(zin+1/(s*cb))
    impedance=excursion=velocity=mach=spl=None
    cone_speed: ComplexArray
    if complete:
        assert driver.re_ohm is not None and driver.qes is not None
        bl=sqrt(ws*ms*driver.re_ohm/driver.qes)
        ze=driver.re_ohm+s*(driver.le_h or 0)
        impedance=ze+bl*bl/mechanical
        cone_speed=bl*(sqrt(power_w*driver.re_ohm)/impedance)/mechanical
        excursion=abs(cone_speed/s)*1000
    else:
        cone_speed=np.asarray(1/mechanical,dtype=complex)
    mouth_flow=sd*cone_speed*flow_factor
    pressure=s*rho*mouth_flow/(2*pi)
    magnitude=np.maximum(abs(pressure),np.finfo(float).tiny)
    reference=float(np.max(magnitude[(f>=80)&(f<=400)]))
    response=20*np.log10(magnitude/reference)
    delay=-1000*np.gradient(np.unwrap(np.angle(pressure)),w)
    if complete:
        velocity=abs(mouth_flow)/horn.mouth_area_m2
        mach=velocity/c
        spl=20*np.log10(magnitude/20e-6)
    crossings=np.flatnonzero((response[:-1]<-3)&(response[1:]>=-3))
    f3=None
    if crossings.size:
        i=int(crossings[0])
        fraction=(-3-response[i])/(response[i+1]-response[i])
        f3=float(np.exp(np.log(f[i])+fraction*(np.log(f[i+1])-np.log(f[i]))))
    return VentedResponse(f,response,excursion,velocity,mach,delay,
                          impedance,spl,f3,power_w,complete)
