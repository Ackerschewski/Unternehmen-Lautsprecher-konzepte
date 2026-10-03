"""Four-panel exponential front horn attached to a sealed rear cabinet."""
from __future__ import annotations

from dataclasses import dataclass
from math import log, pi, sqrt

from lautsprecher_konstruktion.drivers.models import Driver
from lautsprecher_konstruktion.enclosure.rectangular import CabinetDimensions, CutPanel


@dataclass(frozen=True)
class FrontHorn:
    throat_width_m: float
    throat_height_m: float
    mouth_width_m: float
    mouth_height_m: float
    axial_length_m: float
    target_cutoff_hz: float
    panels: tuple[CutPanel, ...]

    @property
    def throat_area_m2(self) -> float:
        return self.throat_width_m*self.throat_height_m

    @property
    def mouth_area_m2(self) -> float:
        return self.mouth_width_m*self.mouth_height_m


def design_front_horn(cabinet: CabinetDimensions, driver: Driver,
                      cutoff_hz: float) -> FrontHorn:
    outer = driver.outer_diameter_m or driver.cutout_diameter_m
    if outer is None or cutoff_hz <= 0:
        raise ValueError("Front-Horn benötigt Treiber-Außendurchmesser und Grenzfrequenz")
    t = cabinet.panel_thickness_m
    throat = outer+2*t+0.01
    mouth_w,mouth_h = cabinet.width_m,cabinet.height_m
    area_ratio = mouth_w*mouth_h/(throat*throat)
    if area_ratio < 1.5 or min(mouth_w-throat,mouth_h-throat)<0.025:
        raise ValueError("Front-Horn-Mündung zu klein für Treiber und Hals; Breite/Höhe vergrößern")
    length = 343*log(area_ratio)/(2*pi*cutoff_hz)
    if not 0.12<=length<=2.5:
        raise ValueError("Front-Horn-Länge außerhalb 120–2500 mm; Grenzfrequenz/Abmessungen ändern")
    top_slant = sqrt(length*length+((mouth_h-throat)/2)**2)
    side_slant = sqrt(length*length+((mouth_w-throat)/2)**2)
    panels = (
        CutPanel(f"Horn oben/unten Trapez Hals {throat*1000:.1f} Mündung {mouth_w*1000:.1f}",
                 2,mouth_w,top_slant,t),
        CutPanel(f"Horn seitlich Trapez Hals {throat*1000:.1f} Mündung {mouth_h*1000:.1f}",
                 2,mouth_h,side_slant,t),
    )
    return FrontHorn(throat,throat,mouth_w,mouth_h,length,cutoff_hz,panels)
