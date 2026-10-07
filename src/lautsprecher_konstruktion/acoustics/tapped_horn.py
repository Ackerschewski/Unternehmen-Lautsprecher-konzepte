"""Plane-wave two-tap network on the folded path: cone sides inject at separate path nodes."""
from __future__ import annotations

from math import pi, sqrt

import numpy as np

from lautsprecher_konstruktion.acoustics.vented import VentedResponse
from lautsprecher_konstruktion.acoustics.waveguide import radiation_load
from lautsprecher_konstruktion.arrays import ComplexArray, FloatArray
from lautsprecher_konstruktion.drivers.models import Driver
from lautsprecher_konstruktion.enclosure.tapped_horn import TappedHorn


def simulate_tapped_horn(driver: Driver, horn: TappedHorn,
                         internal_width_m: float, power_w: float) -> VentedResponse:
    if driver.vas_m3 is None or power_w<=0:
        raise ValueError('Tapped-Horn benötigt Vas und positive Eingangsleistung')
    f=np.geomspace(10,500,400)
    w=2*pi*f
    s=1j*w
    rho,c=1.204,343.0
    details=horn.details
    if details is None:
        raise ValueError('Tapped-Horn ohne Pfadgeometrie')
    segments=details.acoustic_segments
    nodes=len(segments)+1
    # Pressure nodes between the path segments: node 0 is the closed end, the last
    # node radiates into the room; the cone sides inject at the two tap nodes.
    admittance=np.zeros((len(f),nodes,nodes),dtype=complex)
    gamma=(0.025+1j)*w/c
    for index,(area,length) in enumerate(segments):
        left,right=index,index+1
        zc=rho*c/area
        sh=np.sinh(gamma*length)
        ch=np.cosh(gamma*length)
        admittance[:,left,left]+=ch/(zc*sh)
        admittance[:,right,right]+=ch/(zc*sh)
        admittance[:,left,right]+=-1/(zc*sh)
        admittance[:,right,left]+=-1/(zc*sh)
    mouth_area=horn.mouth_width_m*horn.mouth_height_m
    radius=sqrt(mouth_area/pi)
    radiation=radiation_load(f,mouth_area,radius)
    admittance[:,nodes-1,nodes-1]+=1/radiation
    rear,front=horn.tap_nodes
    injection=np.zeros((len(f),nodes),dtype=complex)
    injection[:,rear]=1
    injection[:,front]=-1
    pressure_per_flow=np.linalg.solve(admittance,injection[...,None])[...,0]
    differential=pressure_per_flow[:,rear]-pressure_per_flow[:,front]
    mouth_factor=pressure_per_flow[:,nodes-1]/radiation
    complete=all(v is not None for v in (driver.sd_m2,driver.re_ohm,driver.qes))
    sd=driver.sd_m2 if driver.sd_m2 is not None else 1.0
    compliance=driver.vas_m3/(rho*c*c*sd*sd)
    ws=2*pi*driver.fs_hz
    mass=1/(ws*ws*compliance)
    qms=driver.qms if complete and driver.qms is not None else driver.qts
    if complete and driver.qms is None:
        assert driver.qes is not None
        if driver.qes<=driver.qts:
            raise ValueError('Qes muss größer als Qts sein')
        qms=driver.qes*driver.qts/(driver.qes-driver.qts)
    mechanical=ws*mass/qms+s*mass+1/(s*compliance)+sd*sd*differential
    impedance: ComplexArray | None = None
    excursion: FloatArray | None = None
    velocity: FloatArray | None = None
    mach: FloatArray | None = None
    spl: FloatArray | None = None
    cone_speed: ComplexArray
    if complete:
        assert driver.re_ohm is not None and driver.qes is not None
        bl=sqrt(ws*mass*driver.re_ohm/driver.qes)
        ze=driver.re_ohm+s*(driver.le_h or 0)
        impedance=ze+bl*bl/mechanical
        cone_speed=bl*(sqrt(power_w*driver.re_ohm)/impedance)/mechanical
        excursion=abs(cone_speed/s)*1000
    else:
        cone_speed=np.asarray(1/mechanical,dtype=complex)
    mouth_flow=sd*cone_speed*mouth_factor
    pressure=s*rho*mouth_flow/(2*pi)
    magnitude=np.maximum(abs(pressure),np.finfo(float).tiny)
    reference=float(np.max(magnitude[(f>=80)&(f<=400)]))
    response=20*np.log10(magnitude/reference)
    delay=-1000*np.gradient(np.unwrap(np.angle(pressure)),w)
    if complete:
        velocity=abs(mouth_flow)/mouth_area
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
