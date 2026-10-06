"""Closed-form relations for the aperiodic (resistive vent) and passive cardioid families.

An aperiodic box is a closed box whose wall carries a vent filled with a flow-resistive
material (felt, fleece, foam). With the vent mass neglected the vent acts as a leakage
resistance R_ac in parallel with the box compliance C_ab (Small 1973, closed box with
leakage Q_L = w_c C_ab R_ac). It lowers the damping Q and, below 1 / (2 pi R_ac C_ab),
adds a first-order high-pass because the vent flow cancels the cone volume velocity.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import pi, sqrt

from lautsprecher_konstruktion.drivers.models import Driver

RHO_AIR = 1.204
SPEED_OF_SOUND_M_S = 343.0


def box_compliance_m5_n(volume_m3: float) -> float:
    if volume_m3 <= 0:
        raise ValueError("box volume must be positive")
    return volume_m3/(RHO_AIR*SPEED_OF_SOUND_M_S**2)


def default_vent_resistance(driver: Driver, volume_m3: float) -> float:
    """Rule used by the solver: vent resistance equal to the box impedance at Fs (leak corner = Fs)."""
    return 1/(2*pi*driver.fs_hz*box_compliance_m5_n(volume_m3))


def specific_flow_resistance(resistance_pa_s_m3: float, area_m2: float) -> float:
    """Flow resistance of the vent material in Rayl (Pa s/m): R_s = R_ac * A."""
    if resistance_pa_s_m3 <= 0 or area_m2 <= 0:
        raise ValueError("resistance and area must be positive")
    return resistance_pa_s_m3*area_m2


@dataclass(frozen=True)
class AperiodicQ:
    qtc_closed: float
    ql: float
    qtc_effective: float
    leak_corner_hz: float
    resonance_hz: float


def aperiodic_q(driver: Driver, volume_m3: float, resistance_pa_s_m3: float) -> AperiodicQ:
    """Qtc of the closed box, leakage Q_L of the vent and the combined Q (vent mass neglected)."""
    if driver.vas_m3 is None:
        raise ValueError("Vas fehlt")
    if resistance_pa_s_m3 <= 0:
        raise ValueError("resistance must be positive")
    alpha = driver.vas_m3/volume_m3
    qtc = driver.qts*sqrt(1+alpha)
    fc = driver.fs_hz*sqrt(1+alpha)
    cab = box_compliance_m5_n(volume_m3)
    ql = 2*pi*fc*cab*resistance_pa_s_m3
    return AperiodicQ(qtc, ql, 1/(1/qtc+1/ql), 1/(2*pi*resistance_pa_s_m3*cab), fc)


def cardioid_ideal_delay_s(separation_m: float) -> float:
    """Delay of the rear vent for a cancellation behind the box: tau = d / c."""
    if separation_m <= 0:
        raise ValueError("separation must be positive")
    return separation_m/SPEED_OF_SOUND_M_S
