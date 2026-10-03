"""Passive-radiator tuning from measured free-air T/S data.

The radiator suspension and moving mass act as a series acoustic compliance
and mass. Added mass changes only the mass, not the suspension or losses.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import pi


@dataclass(frozen=True)
class PassiveRadiatorDesign:
    area_m2: float
    cutout_diameter_m: float
    mounting_depth_m: float
    stock_mass_kg: float
    added_mass_kg: float
    acoustic_mass_kg_m4: float
    acoustic_compliance_m5_n: float
    acoustic_resistance_pa_s_m3: float
    tuning_hz: float
    xmax_m: float

    @property
    def total_mass_kg(self) -> float:
        return self.stock_mass_kg + self.added_mass_kg

    @property
    def displacement_m3(self) -> float:
        return self.area_m2 * self.mounting_depth_m


def design_passive_radiator(
    *, box_volume_m3: float, tuning_hz: float, area_m2: float,
    stock_mass_kg: float, free_air_fs_hz: float, qms: float,
    cutout_diameter_m: float, mounting_depth_m: float, xmax_m: float,
    rho_kg_m3: float = 1.204, sound_speed_m_s: float = 343.0,
) -> PassiveRadiatorDesign:
    if min(box_volume_m3, tuning_hz, area_m2, stock_mass_kg, free_air_fs_hz,
           qms, cutout_diameter_m, mounting_depth_m, xmax_m) <= 0:
        raise ValueError("Passivmembran-Daten und Gehäusevolumen müssen positiv sein")
    cb = box_volume_m3 / (rho_kg_m3 * sound_speed_m_s**2)
    stock_acoustic_mass = stock_mass_kg / area_m2**2
    compliance = 1.0 / ((2*pi*free_air_fs_hz)**2 * stock_acoustic_mass)
    required_acoustic_mass = (1/cb + 1/compliance) / (2*pi*tuning_hz)**2
    added = (required_acoustic_mass - stock_acoustic_mass) * area_m2**2
    if added < -1e-9:
        raise ValueError("Fb mit dieser Passivmembran nicht erreichbar: Grundmasse ist bereits zu hoch")
    resistance = 2*pi*free_air_fs_hz * stock_acoustic_mass / qms
    return PassiveRadiatorDesign(
        area_m2=area_m2, cutout_diameter_m=cutout_diameter_m,
        mounting_depth_m=mounting_depth_m, stock_mass_kg=stock_mass_kg,
        added_mass_kg=max(0.0, added), acoustic_mass_kg_m4=required_acoustic_mass,
        acoustic_compliance_m5_n=compliance,
        acoustic_resistance_pa_s_m3=resistance, tuning_hz=tuning_hz, xmax_m=xmax_m,
    )
