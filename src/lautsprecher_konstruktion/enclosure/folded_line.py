"""Dimensioned, constant-depth folds for quarter-wave enclosures.

The acoustic line uses the centre path through the alternating end gaps.
Manufacturing panels are shorter than the inner depth by exactly ``turn_gap_m``.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise
from math import cosh, exp, log, pi, sqrt

from lautsprecher_konstruktion.enclosure.rectangular import CabinetDimensions, CutPanel

LINE_TYPES = {
    "transmission_line_closed", "transmission_line_open",
    "transmission_line_tapered", "mltl", "tqwt", "labyrinth",
}
REAR_HORN_TYPES = {
    "horn_rear", "horn_folded", "horn_scoop", "horn_exponential",
    "horn_tractrix", "horn_conical", "horn_hyperbolic",
}
FOLDED_TYPES = LINE_TYPES | REAR_HORN_TYPES


@dataclass(frozen=True)
class FoldedLine:
    family: str
    channel_heights_m: tuple[float, ...]
    channel_areas_m2: tuple[float, ...]
    turn_gap_m: float
    path_length_m: float
    estimated_quarter_wave_hz: float
    baffle_panels: tuple[CutPanel, ...]
    mouth_width_m: float
    mouth_height_m: float

    @property
    def fold_count(self) -> int:
        return len(self.channel_heights_m)-1


def _weights(family: str, count: int) -> list[float]:
    if family == "transmission_line_tapered":
        return [1.5-1.05*i/(count-1) for i in range(count)]
    if family == "tqwt":
        # The first enlarged segment is the physical driver plenum; the
        # following segments expand from the narrow throat to the mouth.
        return [1.8]+[0.6+1.8*i/max(count-2,1) for i in range(count-1)]
    if family in REAR_HORN_TYPES:
        result = [1.8]  # Enlarged physical driver chamber before the throat.
        horn_segments = count-1
        for i in range(horn_segments):
            u = i/max(horn_segments-1,1)
            if family == "horn_conical":
                area = (sqrt(0.45)+(sqrt(2.5)-sqrt(0.45))*u)**2
            elif family == "horn_hyperbolic":
                area = 0.45+2.05*(cosh(2*u)-1)/(cosh(2)-1)
            elif family == "horn_scoop":
                area = 0.45+2.05*u**2
            elif family == "horn_folded":
                area = 0.35*exp(log(2.7/0.35)*u)
            elif family == "horn_rear":
                area = 0.6*exp(log(2.3/0.6)*u)
            elif family == "horn_tractrix":
                # Tractrix axial coordinate, normalized mouth radius = 1.
                def axial(radius: float) -> float:
                    tangent = sqrt(1-radius*radius)
                    return log((1+tangent)/radius)-tangent
                throat = sqrt(0.45/2.5)
                target = axial(throat)*(1-u)
                lo,hi = throat,1.0
                for _ in range(35):
                    middle = (lo+hi)/2
                    if axial(middle)>target:
                        lo=middle
                    else:
                        hi=middle
                area = 2.5*((lo+hi)/2)**2
            else:
                area = 0.45*exp(log(2.5/0.45)*u)
            result.append(area)
        return result
    return [1.0]*count


AREA_FOLLOWING_TYPES = LINE_TYPES - {"tqwt"}
LINE_AREA_RATIO = 1.2  # line cross-section relative to the driver area (typical TL practice 1.0-1.5)


def _candidate(cabinet: CabinetDimensions, family: str, count: int,
               driver_diameter_m: float, driver_area_m2: float | None = None) -> FoldedLine | None:
    t = cabinet.panel_thickness_m
    h = cabinet.internal_height_m
    d = cabinet.internal_depth_m
    w = cabinet.internal_width_m
    free_h = h-(count-1)*t
    if free_h <= 0 or d <= 0:
        return None
    weights = _weights(family, count)
    heights = tuple(free_h*weight/sum(weights) for weight in weights)
    if family in AREA_FOLLOWING_TYPES and driver_area_m2:
        # A real line keeps a cross-section close to the driver area; the remaining height becomes
        # the driver chamber (first segment), as in folded lines built with a plenum behind the driver.
        base = LINE_AREA_RATIO*driver_area_m2/w
        line_weights = [1.0]*(count-1) if family != "transmission_line_tapered" else [
            1.3-0.6*i/max(count-2, 1) for i in range(count-1)]
        line_heights = [base*x for x in line_weights]
        plenum = free_h-sum(line_heights)
        if plenum < driver_diameter_m+0.016:
            return None
        heights = (plenum, *line_heights)
    if heights[0] < driver_diameter_m+0.016 or min(heights) < 0.028:
        return None
    gap = min(0.055, max(0.028, min(heights)*0.7))
    if d < gap+0.06:
        return None
    # Straight runs end at a gap centre; each turn connects adjacent channel centres.
    path = (count-1)*(d-gap)+sum((a+b)/2 for a,b in pairwise(heights))
    if path <= 0:
        return None
    panels = tuple(CutPanel(f"Linienfaltung F{i+1} ({'hinten' if i%2 == 0 else 'vorn'} offen)",
                             1, w, d-gap, t) for i in range(count-1))
    mouth_w = max(0.0,w-0.02)
    mouth_h = max(0.0,heights[-1]-0.02)
    return FoldedLine(family, heights, tuple(w*x for x in heights), gap, path,
                      343/(4*path), panels, mouth_w, mouth_h)


def design_folded_line(cabinet: CabinetDimensions, family: str,
                       target_hz: float, driver_diameter_m: float,
                       driver_area_m2: float | None = None) -> FoldedLine:
    if family not in FOLDED_TYPES or target_hz <= 0 or driver_diameter_m <= 0:
        raise ValueError("Ungültiger Linienentwurf oder fehlender Treiberdurchmesser")
    counts = ((4,6,8,10) if family == "tqwt" or family in REAR_HORN_TYPES
              else (2,3,4,5,6,7,8,9,10,12) if driver_area_m2 else (2,4,6,8,10))
    candidates = [line for count in counts if
                  (line := _candidate(cabinet,family,count,driver_diameter_m,driver_area_m2)) is not None]
    if not candidates:
        raise ValueError("Kein faltbarer Kanal: Höhe/Tiefe für Treiber und mindestens einen Umlenkspalt vergrößern")
    target_length = 343/(4*target_hz)
    return min(candidates, key=lambda line: abs(line.path_length_m-target_length)/target_length)


def baffle_displacement_m3(line: FoldedLine) -> float:
    return sum(p.width_m*p.height_m*p.thickness_m for p in line.baffle_panels)


def mouth_equivalent_radius_m(line: FoldedLine) -> float:
    return float((line.mouth_width_m*line.mouth_height_m/pi)**0.5)
