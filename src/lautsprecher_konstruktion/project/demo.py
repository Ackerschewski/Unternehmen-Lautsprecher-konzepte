"""Synthetic demonstration data. No values represent a commercial driver."""
from __future__ import annotations

from math import atan, log10, pi, sqrt

from lautsprecher_konstruktion.crossover.measurements import FrequencyResponseData, ImpedanceData
from lautsprecher_konstruktion.drivers.models import Driver
from lautsprecher_konstruktion.enclosure.layout import FrontElement
from lautsprecher_konstruktion.project.models import (
    CrossoverConfig,
    EnclosureConfig,
    SpeakerProject,
)


def demo_driver() -> Driver:
    return Driver(manufacturer="TESTDATEN", model="Demo Woofer - keine Herstellerdaten",
        fs_hz=32, qts=0.36, qes=0.4, qms=3.6, vas_m3=0.058,
        re_ohm=5.8, le_h=0.0011, sd_m2=0.035, xmax_m=0.006,
        power_rms_w=100, displacement_m3=0.0018, nominal_impedance_ohm=8,
        outer_diameter_m=0.26, cutout_diameter_m=0.23, mounting_depth_m=0.115,
        source_name="Synthetische Testdaten",source_document="Nur Funktionsprüfung; nicht für Fertigung freigegeben")


def demo_project() -> SpeakerProject:
    f=tuple(20*1000**(i/79) for i in range(80))
    woofer_mag=tuple(-10*log10(1+(hz/3000)**4) for hz in f)
    tweeter_mag=tuple(-10*log10(1+(900/hz)**4) for hz in f)
    woofer_phase=tuple(-2*atan((hz/3000)**2)*180/pi for hz in f)
    tweeter_phase=tuple(2*atan((900/hz)**2)*180/pi for hz in f)
    woofer_z=tuple(sqrt(5.8**2+(2*pi*hz*.0011)**2) for hz in f)
    tweeter_z=tuple(sqrt(6.2**2+(2*pi*hz*.00005)**2) for hz in f)
    woofer_zphase=tuple(atan(2*pi*hz*.0011/5.8)*180/pi for hz in f)
    tweeter_zphase=tuple(atan(2*pi*hz*.00005/6.2)*180/pi for hz in f)
    metadata={"Hinweis":"Synthetische Testkurve; keine Messung"}
    return SpeakerProject(name="Demo 2-Wege Bassreflex - TESTDATEN",
        material="Birke Multiplex",driver=demo_driver(),tweeter_name="Demo Tweeter - TESTDATEN",
        enclosure=EnclosureConfig(enclosure_type="bass_reflex",target_volume_l=45,
            tuning_hz=35,port_type="round",port_diameter_mm=80,external_width_mm=340,
            external_height_mm=560,panel_thickness_mm=18,brace_quantity=1,
            input_power_w=10),
        crossover=CrossoverConfig(enabled=True,topology="butterworth_2",crossover_hz=2500,
            woofer_impedance_ohm=8,tweeter_impedance_ohm=8,tweeter_attenuation_db=2,
            add_woofer_zobel=True,
            woofer_frd=FrequencyResponseData(frequencies_hz=f,magnitude_db=woofer_mag,
                phase_deg=woofer_phase,source="synthetic-demo",metadata=metadata),
            tweeter_frd=FrequencyResponseData(frequencies_hz=f,magnitude_db=tweeter_mag,
                phase_deg=tweeter_phase,source="synthetic-demo",metadata=metadata),
            woofer_zma=ImpedanceData(frequencies_hz=f,magnitude_ohm=woofer_z,
                phase_deg=woofer_zphase,source="synthetic-demo",metadata=metadata),
            tweeter_zma=ImpedanceData(frequencies_hz=f,magnitude_ohm=tweeter_z,
                phase_deg=tweeter_zphase,source="synthetic-demo",metadata=metadata)),
        front_elements=(
            FrontElement(id="W1",type="woofer",x_m=.17,y_m=.29,outer_diameter_m=.26,
                cutout_diameter_m=.23,mounting_depth_m=.115,
                bolt_circle_diameter_m=.245,bolt_count=8),
            FrontElement(id="T1",type="tweeter",x_m=.17,y_m=.475,outer_diameter_m=.10,
                cutout_diameter_m=.075,mounting_depth_m=.05,
                bolt_circle_diameter_m=.088,bolt_count=4),
            FrontElement(id="BR1",type="port",x_m=.17,y_m=.10,outer_diameter_m=.08,
                cutout_diameter_m=.08,mounting_depth_m=.20),
        ),notes="Alle Treiber-, FRD- und ZMA-Werte sind ausschließlich synthetische Testdaten.")
