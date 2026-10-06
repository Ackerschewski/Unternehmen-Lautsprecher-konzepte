"""Sectioned exponential front horn attached to a sealed rear cabinet.

Throat and mouth are rectangles; both side lengths grow exponentially so the area
follows S = S_T e^(m x), m = ln(S_M/S_T)/L and fc = m c / (4 pi), i.e.
L = c ln(S_M/S_T) / (4 pi fc). Flat boards can only realise this as a chain of
frusta: each section is a pyramid frustum whose area between the section borders is
not exactly exponential (the model uses the built area).
"""
from __future__ import annotations

from dataclasses import dataclass
from math import hypot, log, pi

from lautsprecher_konstruktion.drivers.models import Driver
from lautsprecher_konstruktion.enclosure.horn_geometry import olson_min_mouth_area_m2
from lautsprecher_konstruktion.enclosure.rectangular import CabinetDimensions, CutPanel

FRONT_HORN_SECTIONS = 6
C_AIR = 343.0


@dataclass(frozen=True)
class FrontHorn:
    throat_width_m: float
    throat_height_m: float
    mouth_width_m: float
    mouth_height_m: float
    axial_length_m: float
    target_cutoff_hz: float
    panels: tuple[CutPanel, ...]
    section_widths_m: tuple[float, ...] = ()    # width at each section border (throat..mouth)
    section_heights_m: tuple[float, ...] = ()
    section_lengths_m: tuple[float, ...] = ()
    driver_area_m2: float = 0.0

    @property
    def throat_area_m2(self) -> float:
        return self.throat_width_m*self.throat_height_m

    @property
    def mouth_area_m2(self) -> float:
        return self.mouth_width_m*self.mouth_height_m

    @property
    def area_ratio(self) -> float:
        return self.mouth_area_m2/self.throat_area_m2

    @property
    def flare_per_m(self) -> float:
        return log(self.area_ratio)/self.axial_length_m

    @property
    def cutoff_hz(self) -> float:
        return C_AIR*self.flare_per_m/(4*pi)

    @property
    def mouth_min_area_m2(self) -> float:
        return olson_min_mouth_area_m2(self.target_cutoff_hz)

    @property
    def decompression(self) -> float:
        """Throat area relative to the cone area (>1: the cone radiates into a widened throat)."""
        return self.throat_area_m2/self.driver_area_m2 if self.driver_area_m2 else 0.0

    def section_area_m2(self, index: int, fraction: float) -> float:
        """Built (pyramidal) area inside section ``index`` at ``fraction`` 0..1."""
        w = self.section_widths_m[index]+(self.section_widths_m[index+1]-self.section_widths_m[index])*fraction
        h = self.section_heights_m[index]+(self.section_heights_m[index+1]-self.section_heights_m[index])*fraction
        return w*h

    def acoustic_segments(self, slices_per_section: int = 8) -> list[tuple[float, float]]:
        """(area, length) slices of the built horn, throat to mouth."""
        result = []
        for i, length in enumerate(self.section_lengths_m):
            for j in range(slices_per_section):
                result.append((self.section_area_m2(i, (j+0.5)/slices_per_section),
                               length/slices_per_section))
        return result

    def ideal_area_m2(self, x_m: float) -> float:
        fraction = min(max(x_m, 0.0), self.axial_length_m)/self.axial_length_m
        return float(self.throat_area_m2*self.area_ratio**fraction)

    def max_area_deviation(self) -> float:
        worst, x = 0.0, 0.0
        for i, length in enumerate(self.section_lengths_m):
            for j in range(1, 8):
                fraction = j/8
                built = self.section_area_m2(i, fraction)
                ideal = self.ideal_area_m2(x+length*fraction)
                worst = max(worst, abs(built-ideal)/ideal)
            x += length
        return worst


def design_front_horn(cabinet: CabinetDimensions, driver: Driver,
                      cutoff_hz: float, sections: int = FRONT_HORN_SECTIONS) -> FrontHorn:
    outer = driver.outer_diameter_m or driver.cutout_diameter_m
    if outer is None or cutoff_hz <= 0:
        raise ValueError("Front-Horn benötigt Treiber-Außendurchmesser und Grenzfrequenz")
    t = cabinet.panel_thickness_m
    throat = outer+2*t+0.01
    mouth_w, mouth_h = cabinet.width_m, cabinet.height_m
    area_ratio = mouth_w*mouth_h/(throat*throat)
    if area_ratio < 1.5 or min(mouth_w-throat, mouth_h-throat) < 0.025:
        raise ValueError("Front-Horn-Mündung zu klein für Treiber und Hals; Breite/Höhe vergrößern")
    length = C_AIR*log(area_ratio)/(4*pi*cutoff_hz)
    if not 0.12 <= length <= 2.5:
        raise ValueError("Front-Horn-Länge außerhalb 120–2500 mm; Grenzfrequenz/Abmessungen ändern")
    widths = tuple(throat*(mouth_w/throat)**(i/sections) for i in range(sections+1))
    heights = tuple(throat*(mouth_h/throat)**(i/sections) for i in range(sections+1))
    step = length/sections
    panels: list[CutPanel] = []
    for i in range(sections):
        slant_tb = hypot(step, (heights[i+1]-heights[i])/2)
        slant_side = hypot(step, (widths[i+1]-widths[i])/2)
        panels.append(CutPanel(
            f"Horn Abschnitt {i+1} oben/unten Trapez {widths[i]*1000:.1f}→{widths[i+1]*1000:.1f}",
            2, widths[i+1], slant_tb, t))
        panels.append(CutPanel(
            f"Horn Abschnitt {i+1} seitlich Trapez {heights[i]*1000:.1f}→{heights[i+1]*1000:.1f}",
            2, heights[i+1], slant_side, t))
    return FrontHorn(throat, throat, mouth_w, mouth_h, length, cutoff_hz, tuple(panels),
                     widths, heights, (step,)*sections, driver.sd_m2 or 0.0)
