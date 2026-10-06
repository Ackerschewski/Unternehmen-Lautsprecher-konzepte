"""Dimensioned, constant-depth folds for quarter-wave enclosures.

The acoustic line uses the centre path through the alternating end gaps.
Manufacturing panels are shorter than the inner depth by exactly ``turn_gap_m``.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise
from math import atan, cosh, exp, log, pi, sqrt, tan

from lautsprecher_konstruktion.enclosure.horn_geometry import HornDetails
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


STUFFING_LOSS = {"none": 0.01, "light": 0.022, "medium": 0.035, "heavy": 0.05}
STUFFING_LABELS = {"none": "ohne", "light": "leicht", "medium": "mittel", "heavy": "dicht"}
LINE_AREA_RATIOS = (1.0, 1.1, 1.2, 1.3, 1.4, 1.5)  # line area / driver Sd (TL practice 1.0-1.5)
TQWT_TAPERS = (2.0, 3.0, 4.0)                       # driver-end area / mouth area (Voigt-type TQWT)
MLTL_PORT_RATIO_RANGE = (0.15, 1.0)                 # port area / line area, rule of thumb only


@dataclass(frozen=True)
class FoldedLine:
    """Folded duct: channel 0 is the driver chamber/first duct section behind the driver.

    Partitions are horizontal shelves; ``turn_gaps_m[i]`` is the depth of the opening
    between channel i and i+1 (even i: at the back wall, odd i: at the front baffle),
    so the mouth of an even channel count lies on the front baffle.
    """
    family: str
    channel_heights_m: tuple[float, ...]
    channel_areas_m2: tuple[float, ...]
    turn_gap_m: float
    path_length_m: float
    estimated_quarter_wave_hz: float
    baffle_panels: tuple[CutPanel, ...]
    mouth_width_m: float
    mouth_height_m: float
    turn_gaps_m: tuple[float, ...] = ()
    straight_lengths_m: tuple[float, ...] = ()
    turn_lengths_m: tuple[float, ...] = ()
    stuffing: tuple[str, ...] = ()
    inner_depth_m: float = 0.0
    mltl_port_ratio: float | None = None
    horn: HornDetails | None = None   # physical area law and inclined septa of rear horns

    @property
    def fold_count(self) -> int:
        return len(self.channel_heights_m)-1

    def gap_m(self, fold_index: int) -> float:
        return self.turn_gaps_m[fold_index] if self.turn_gaps_m else self.turn_gap_m

    def segments(self) -> list[tuple[float, float, str]]:
        """Acoustic segments (area, length, stuffing) in driver-to-mouth order.

        Shared by the transfer-matrix model so the simulation uses the drawn geometry.
        """
        if self.horn is not None:
            return [(a, length, "light") for a, length in self.horn.acoustic_segments]
        count = len(self.channel_areas_m2)
        stuffing = self.stuffing or ("light",)*count
        result: list[tuple[float, float, str]] = []
        for i, area in enumerate(self.channel_areas_m2):
            result.append((area, self.straight_lengths_m[i], stuffing[i]))
            if i < count-1:
                nxt = self.channel_areas_m2[i+1]
                result.append((sqrt(area*nxt), self.turn_lengths_m[i], stuffing[i]))
        return result

    @property
    def min_turn_opening_ratio(self) -> float:
        """Smallest turn-opening area relative to the smaller adjacent channel (1.0 = no constriction)."""
        width = self.channel_areas_m2[0]/self.channel_heights_m[0]
        return min(self.gap_m(i)*width/min(self.channel_areas_m2[i], self.channel_areas_m2[i+1])
                   for i in range(self.fold_count))

    @property
    def driver_chamber_volume_m3(self) -> float:
        return self.channel_areas_m2[0]*self.inner_depth_m


def mltl_loaded_path_m(target_hz: float, line_area_m2: float, port_area_m2: float,
                       port_leff_m: float, c: float = 343.0) -> float:
    """Closed line of length L loaded by a port mass: pole where tan(kL)=Zc/(wM)."""
    w = 2*pi*target_hz
    return float(c/w*atan(c*port_area_m2/(w*line_area_m2*port_leff_m)))


def mltl_loaded_resonance_hz(path_m: float, line_area_m2: float, port_area_m2: float,
                             port_leff_m: float, c: float = 343.0) -> float:
    lo, hi = 1.0, c/(4*path_m)
    for _ in range(60):
        f = (lo+hi)/2
        w = 2*pi*f
        if tan(w*path_m/c) < c*port_area_m2/(w*line_area_m2*port_leff_m):
            lo = f
        else:
            hi = f
    return (lo+hi)/2


def stuffing_levels(family: str, count: int) -> tuple[str, ...]:
    """Qualitative stuffing zones (rule of thumb after Bradbury/Augspurger/Olson).

    Densest near the driver (closed end), none at the mouth; the labyrinth is stuffed
    over its whole length. These are guidelines, not measured data.
    """
    levels: list[str] = []
    for i in range(count):
        u = i/max(count-1, 1)
        if family == "labyrinth":
            levels.append("heavy" if i < count-1 else "medium")
        elif family == "transmission_line_closed":
            levels.append("light" if i == 0 else "medium")
        elif family in ("mltl", "tqwt"):
            levels.append("light" if u <= 0.5 else "none")
        elif family in LINE_TYPES:  # open and tapered line
            levels.append("light" if i == 0 else "medium" if u < 0.5 else
                          "light" if u < 0.75 else "none")
        else:
            levels.append("light")
    return tuple(levels)


def _weights(family: str, count: int) -> list[float]:
    if family == "transmission_line_tapered":
        return [1.5-1.05*i/(count-1) for i in range(count)]
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


def _line_heights(family: str, count: int, free_h: float, driver_diameter_m: float,
                  driver_area_m2: float | None, width_m: float, shape: float) -> tuple[float, ...] | None:
    """Channel heights; ``shape`` is the area ratio (TL) or the taper ratio (TQWT)."""
    if family == "tqwt":
        # Voigt/Bailey TQWT: widest at the driver end, narrowing towards the mouth.
        weights = [1-(1-1/shape)*i/(count-1) for i in range(count)]
        return tuple(free_h*x/sum(weights) for x in weights)
    if family in AREA_FOLLOWING_TYPES and driver_area_m2:
        base = shape*driver_area_m2/width_m
        line_weights = [1.0]*(count-1) if family != "transmission_line_tapered" else [
            1.3-0.6*i/max(count-2, 1) for i in range(count-1)]
        line_heights = [base*x for x in line_weights]
        plenum = free_h-sum(line_heights)
        if plenum < driver_diameter_m+0.016:
            return None
        return (plenum, *line_heights)
    weights = _weights(family, count)
    return tuple(free_h*x/sum(weights) for x in weights)


def _candidate(cabinet: CabinetDimensions, family: str, count: int,
               driver_diameter_m: float, driver_area_m2: float | None = None,
               shape: float = 1.2, port: tuple[float, float] | None = None) -> FoldedLine | None:
    t = cabinet.panel_thickness_m
    h = cabinet.internal_height_m
    d = cabinet.internal_depth_m
    w = cabinet.internal_width_m
    free_h = h-(count-1)*t
    if free_h <= 0 or d <= 0 or count < 2:
        return None
    heights = _line_heights(family, count, free_h, driver_diameter_m, driver_area_m2, w, shape)
    if heights is None or heights[0] < driver_diameter_m+0.016 or min(heights) < 0.028:
        return None
    if family == "mltl" and port is not None and heights[-1] < 2*sqrt(port[0]/pi)+0.02:
        return None  # round port must fit into the last channel with 10 mm margin
    legacy = family in REAR_HORN_TYPES
    if legacy:
        gaps = (min(0.055, max(0.028, min(heights)*0.7)),)*(count-1)
    else:
        # The turn opening should be about as large as the duct it connects: depth of the
        # slot = height of the smaller neighbouring channel (equal area at equal width).
        # Capped at half the depth so every partition keeps at least half the depth.
        gaps = tuple(min(a, b, 0.5*d) for a, b in pairwise(heights))
    if d < max(gaps)+0.06:
        return None
    turns = tuple((a+b)/2 for a, b in pairwise(heights))
    if legacy:
        straight_run = d-gaps[0]
        straights = tuple(straight_run*(0.5 if i in (0, count-1) else 1.0) for i in range(count))
    else:
        # Centre path: driver (front) -> centre of rear gap -> ... -> mouth at the front baffle.
        straights = tuple(
            d-gaps[0]/2 if i == 0 else d-gaps[-1]/2 if i == count-1
            else d-(gaps[i-1]+gaps[i])/2 for i in range(count))
    path = sum(straights)+sum(turns)
    if path <= 0 or min(straights) <= 0.02:
        return None
    panels = tuple(CutPanel(f"Linienfaltung F{i+1} ({'hinten' if i%2 == 0 else 'vorn'} offen)",
                             1, w, d-gaps[i], t) for i in range(count-1))
    mouth_w = max(0.0, w-0.02)
    mouth_h = max(0.0, heights[-1]-0.02)
    areas = tuple(w*x for x in heights)
    estimated = 343/(4*path)
    ratio: float | None = None
    if family == "mltl" and port is not None:
        line_area = _mean_line_area(areas, straights)
        estimated = mltl_loaded_resonance_hz(path, line_area, port[0], port[1])
        ratio = port[0]/line_area
    return FoldedLine(family, heights, areas, max(gaps), path, estimated, panels,
                      mouth_w, mouth_h, gaps, straights, turns,
                      stuffing_levels(family, count), d, ratio)


def _mean_line_area(areas: tuple[float, ...], straights: tuple[float, ...]) -> float:
    """Length-weighted mean duct area without the driver chamber (channel 0)."""
    lengths = straights[1:]
    return sum(a*x for a, x in zip(areas[1:], lengths, strict=True))/sum(lengths)


def design_folded_line(cabinet: CabinetDimensions, family: str,
                       target_hz: float, driver_diameter_m: float,
                       driver_area_m2: float | None = None,
                       mltl_port: tuple[float, float] | None = None,
                       driver_vas_m3: float | None = None) -> FoldedLine:
    """``mltl_port`` = (port area, effective port length) for the mass-loaded line."""
    if family not in FOLDED_TYPES or target_hz <= 0 or driver_diameter_m <= 0:
        raise ValueError("Ungültiger Linienentwurf oder fehlender Treiberdurchmesser")
    if family in REAR_HORN_TYPES:
        from lautsprecher_konstruktion.enclosure.rear_horn import design_rear_horn
        return design_rear_horn(cabinet, family, target_hz, driver_diameter_m,
                                driver_area_m2, driver_vas_m3)
    if family in LINE_TYPES:
        counts: tuple[int, ...] = (2, 4, 6, 8, 10, 12, 14)  # even: mouth on the front baffle
    else:
        counts = (4, 6, 8, 10)
    if family == "tqwt":
        shapes: tuple[float, ...] = TQWT_TAPERS
        counts = (4, 6, 8, 10, 12)
    elif family in AREA_FOLLOWING_TYPES and driver_area_m2:
        shapes = LINE_AREA_RATIOS
    else:
        shapes = (1.0,)
    best: tuple[float, FoldedLine] | None = None
    for count in counts:
        for shape in shapes:
            line = _candidate(cabinet, family, count, driver_diameter_m, driver_area_m2, shape,
                              mltl_port if family == "mltl" else None)
            if line is None:
                continue
            if family == "mltl" and mltl_port is not None:
                target = mltl_loaded_path_m(
                    target_hz, _mean_line_area(line.channel_areas_m2, line.straight_lengths_m),
                    mltl_port[0], mltl_port[1])
            else:
                target = 343/(4*target_hz)
            score = abs(line.path_length_m-target)/target
            if family in LINE_TYPES:
                score += 0.3*max(0.0, 0.9-line.min_turn_opening_ratio)
            if family in AREA_FOLLOWING_TYPES and driver_area_m2:
                # Keep the driver chamber compact (a large plenum is a lumped volume, not a line).
                score += 0.3*max(0.0, line.channel_heights_m[0]/(1.6*driver_diameter_m)-1)
            if best is None or score < best[0]:
                best = (score, line)
    if best is None:
        raise ValueError("Kein faltbarer Kanal: Höhe/Tiefe für Treiber und mindestens einen Umlenkspalt vergrößern")
    return best[1]


def baffle_displacement_m3(line: FoldedLine) -> float:
    return sum(p.width_m*p.height_m*p.thickness_m for p in line.baffle_panels)


def mouth_equivalent_radius_m(line: FoldedLine) -> float:
    return float((line.mouth_width_m*line.mouth_height_m/pi)**0.5)
