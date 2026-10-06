"""Rear-loaded folded horns with a physical area law and inclined septa.

Layout (side view, front on the left): driver on the front baffle in the top
chamber; the throat is the gap at the rear end of septum F1 (S_T = W * gap);
runs alternate rear->front / front->rear, the heights follow the chosen area
law S(s)/W, and the mouth is the exit of the last run at the front baffle.
The chamber above F1 takes the height that remains, so the stack closes exactly.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from itertools import pairwise
from math import log, pi
from typing import TYPE_CHECKING, NamedTuple

import numpy as np

from lautsprecher_konstruktion.enclosure.horn_geometry import (
    LAW_LABELS,
    AreaLaw,
    HornDetails,
    RunGeometry,
    SeptumGeometry,
    make_law,
    olson_min_mouth_area_m2,
    trace_path,
)
from lautsprecher_konstruktion.enclosure.rectangular import CabinetDimensions, CutPanel

if TYPE_CHECKING:
    from lautsprecher_konstruktion.enclosure.folded_line import FoldedLine

# family -> (area law, throat area as fraction of the cone area Sd)
# Throat fractions are design defaults, not manufacturer data: rear/folded horns
# use moderate compression (Sd/S_T 1.7 .. 2.9) in front of a compression chamber.
HORN_FAMILIES: dict[str, tuple[str, float]] = {
    "horn_rear": ("exponential", 0.6),
    "horn_folded": ("exponential", 0.35),
    "horn_exponential": ("exponential", 0.5),
    "horn_conical": ("conical", 0.5),
    "horn_hyperbolic": ("hyperbolic", 0.5),
    "horn_tractrix": ("tractrix", 0.5),
    "horn_scoop": ("scoop", 0.5),
}
FACET_COUNTS = (1, 2, 3, 4, 6)   # straight boards per septum (kinks on a common depth grid)
DEVIATION_GOAL = 0.06
DEVIATION_LIMIT = 0.15
RUN_COUNTS = (3, 5, 7, 9)   # odd: the last run ends at the front baffle


def _chamber_target(width: float, depth: float, height: float, driver_diameter: float,
                    vas_m3: float | None) -> float:
    minimum = driver_diameter+0.036
    preferred = 0.5*vas_m3/(width*depth) if vas_m3 else minimum
    return min(max(minimum, preferred), 0.45*height)


class _Build(NamedTuple):
    w: float
    d: float
    h: float
    t: float
    path: list[RunGeometry]
    gaps: list[float]
    length: float
    law: AreaLaw


def _build(cabinet: CabinetDimensions, kind: str, runs: int, throat: float, mouth: float) -> _Build:
    w, d, h, t = (cabinet.internal_width_m, cabinet.internal_depth_m,
                  cabinet.internal_height_m, cabinet.panel_thickness_m)
    cache: dict[float, AreaLaw] = {}

    def factory(length: float, _first_end: float) -> Callable[[float], float]:
        key = round(length, 9)
        if key not in cache:
            cache.clear()
            cache[key] = make_law(kind, throat, mouth, length)
        return cache[key].area

    path, gaps, length = trace_path(d, w, t, runs, factory, "rear", throat/w)
    return _Build(w, d, h, t, path, gaps, length, make_law(kind, throat, mouth, length))


def _chamber_front(cabinet: CabinetDimensions, kind: str, runs: int, throat: float, mouth: float) -> float:
    b = _build(cabinet, kind, runs, throat, mouth)
    return b.h-sum(_edge_height(r, b.law, b.w, 0.0)+b.t for r in b.path)


def _edge_height(run: RunGeometry, law: AreaLaw, w: float, x: float) -> float:
    lo, hi = sorted((run.x_start_m, run.x_end_m))
    xc = min(max(x, lo), hi)
    return max(0.012, law.area(run.s_start_m+abs(xc-run.x_start_m))/w)


def _details(cabinet: CabinetDimensions, kind: str, runs: int, throat: float, mouth: float,
             driver_area: float, facets: int) -> HornDetails:
    w, d, h, t, path, gaps, length, law = _build(cabinet, kind, runs, throat, mouth)
    grid = [d*j/facets for j in range(facets+1)]
    built = [replace(r, h_nodes_m=tuple(_edge_height(r, law, w, x) for x in grid)) for r in path]
    floor = [h]*(facets+1)
    tops: list[list[float]] = []
    for run in reversed(built):
        floor = [y-hn-t for y, hn in zip(floor, run.h_nodes_m, strict=True)]
        tops.append(floor)
    tops.reverse()
    septa = []
    for k, ys in enumerate(tops, start=1):
        g = gaps[k-1]
        x1, x2 = (0.0, d-g) if k % 2 == 1 else (g, d)
        pts = [(x1, float(np.interp(x1, grid, ys)))]
        pts += [(x, y) for x, y in zip(grid, ys, strict=True) if x1 < x < x2]
        pts.append((x2, float(np.interp(x2, grid, ys))))
        septa.append(SeptumGeometry(k, tuple(pts)))
    chamber_f, chamber_r = tops[0][0], tops[0][-1]
    segments: list[tuple[float, float]] = [(w*(chamber_f+chamber_r)/2, d-gaps[0]/2)]
    worst_dev, worst_turn = 0.0, 9.0
    for run in built:
        lo, hi = sorted((run.x_start_m, run.x_end_m))
        ds = (hi-lo)/10
        for i in range(10):
            x = lo+(i+0.5)*ds
            segments_x = float(np.interp(x, grid, run.h_nodes_m))
            segments.append((w*segments_x, ds))
        for i in range(1, 40):
            x = lo+(hi-lo)*i/40
            ideal = law.area(run.s_start_m+abs(x-run.x_start_m))/w
            worst_dev = max(worst_dev, abs(float(np.interp(x, grid, run.h_nodes_m))-ideal)/ideal)
    # turns: insert in path order (turn k sits before run k)
    ordered: list[tuple[float, float]] = [segments[0]]
    for run in built:
        if run.index > 1:
            prev = built[run.index-2]
            tau = (prev.h_end_m+run.h_start_m)/2+t
            turn_area = w*gaps[run.index-1]
            ordered.append((turn_area, tau))
            worst_turn = min(worst_turn, turn_area/law.area((prev.s_end_m+run.s_start_m)/2))
        ordered.extend(segments[1+10*(run.index-1):1+10*run.index])
    profile_s = tuple(length*i/60 for i in range(61))
    mouth_built = w*built[-1].h_end_m
    return HornDetails(
        kind, LAW_LABELS[kind], throat, mouth_built, law.cutoff_hz, length, w, d,
        tuple(built), tuple(septa), tuple(gaps), chamber_f, chamber_r,
        w*d*(chamber_f+chamber_r)/2, tuple(ordered), profile_s,
        tuple(law.area(s) for s in profile_s), worst_dev, worst_turn,
        driver_area/throat, olson_min_mouth_area_m2(law.cutoff_hz), facets)


def _solve_candidate(cabinet: CabinetDimensions, family: str, runs: int, driver_diameter: float,
                     driver_area: float, vas_m3: float | None) -> HornDetails | None:
    kind, fraction = HORN_FAMILIES[family]
    w, d, h = cabinet.internal_width_m, cabinet.internal_depth_m, cabinet.internal_height_m
    throat = min(max(fraction*driver_area, w*0.03), w*0.45*d)
    minimum = driver_diameter+0.016
    target = _chamber_target(w, d, h, driver_diameter, vas_m3)

    def chamber(mouth: float) -> float:
        return _chamber_front(cabinet, kind, runs, throat, mouth)

    lo, hi = throat*1.05, throat*30
    if chamber(lo) < minimum:
        return None
    if chamber(hi) > target:
        mouth = hi
    else:
        for _ in range(40):
            mid = (lo+hi)/2
            if chamber(mid) > target:
                lo = mid
            else:
                hi = mid
        mouth = (lo+hi)/2

    def deviation(candidate_mouth: float) -> float:
        try:
            return _details(cabinet, kind, runs, throat, candidate_mouth, driver_area,
                            FACET_COUNTS[-1]).max_area_deviation
        except ValueError:
            return 9.0

    if deviation(mouth) > DEVIATION_LIMIT:
        # strongly curved laws (tractrix flare) cannot be built from few straight boards:
        # shrink the mouth until the built profile follows the law
        lo, hi = throat*1.05, mouth
        if deviation(lo) > DEVIATION_LIMIT:
            return None
        for _ in range(18):
            mid = (lo+hi)/2
            if deviation(mid) > DEVIATION_LIMIT:
                hi = mid
            else:
                lo = mid
        mouth = lo
    best: HornDetails | None = None
    for facets in FACET_COUNTS:
        try:
            details = _details(cabinet, kind, runs, throat, mouth, driver_area, facets)
        except ValueError:
            return None
        best = details
        if details.max_area_deviation <= DEVIATION_GOAL:
            break
    assert best is not None
    if best.chamber_front_m < minimum or best.chamber_rear_m < 0.02:
        return None
    if min(min(r.h_start_m, r.h_end_m) for r in best.runs) < 0.028:
        return None
    return best


def design_rear_horn(cabinet: CabinetDimensions, family: str, target_hz: float,
                     driver_diameter_m: float, driver_area_m2: float | None,
                     vas_m3: float | None = None) -> FoldedLine:
    """Pick the run count whose cutoff is closest to ``target_hz``."""
    from lautsprecher_konstruktion.enclosure.folded_line import FoldedLine as _FoldedLine
    if family not in HORN_FAMILIES:
        raise ValueError("Unbekannte Horn-Familie")
    area = driver_area_m2 or pi*(0.8*driver_diameter_m/2)**2
    best: tuple[float, HornDetails] | None = None
    for runs in RUN_COUNTS:
        details = _solve_candidate(cabinet, family, runs, driver_diameter_m, area, vas_m3)
        if details is None:
            continue
        # cutoff closeness, built-vs-ideal profile error and fold constrictions
        score = (abs(log(details.cutoff_hz/target_hz))+1.5*max(0.0, details.max_area_deviation-0.08)
                 +max(0.0, 0.9-details.min_turn_area_ratio))
        if best is None or score < best[0]:
            best = (score, details)
    if best is None:
        raise ValueError("Kein faltbares Horn: Höhe/Tiefe für Treiberkammer, Hals und Umlenkspalte vergrößern")
    details = best[1]
    t = cabinet.panel_thickness_m
    w = cabinet.internal_width_m
    heights = [details.chamber_front_m]
    heights += [(r.h_start_m+r.h_end_m)/2 for r in details.runs[:-1]]
    heights.append(details.runs[-1].h_end_m)
    panels = tuple(
        CutPanel(f"Linienfaltung F{sep.index}{'.'+str(j) if len(sep.points_m) > 2 else ''} "
                 f"({'hinten' if sep.index % 2 else 'vorn'} offen, geneigt {abs(b[1]-a[1])*1000:.0f} mm)",
                 1, w, length, t)
        for sep in details.septa
        for j, (a, b, length) in enumerate(zip(sep.points_m, sep.points_m[1:], sep.facet_lengths_m,
                                                strict=False), start=1))
    straights = (cabinet.internal_depth_m-details.turn_gaps_m[0]/2,
                 *(r.length_m for r in details.runs))
    turns = (0.0, *((a.h_end_m+b.h_start_m)/2+t for a, b in pairwise(details.runs)))
    return _FoldedLine(
        family, tuple(heights), tuple(w*x for x in heights), details.turn_gaps_m[0],
        details.length_m, 343/(4*details.length_m), panels, max(0.0, w-0.02),
        max(0.0, details.runs[-1].h_end_m-0.02), details.turn_gaps_m, straights, turns,
        ("light",)*len(heights), cabinet.internal_depth_m, None, details)


def rear_horn_notes(line: FoldedLine, target_hz: float, vas_m3: float | None) -> list[tuple[str | None, str]]:
    """(issue code or None, message) hints for a designed rear horn."""
    horn = line.horn
    assert horn is not None
    notes: list[tuple[str | None, str]] = []
    notes.append((None, (
        f"Horn {horn.law_label}: Hals {horn.throat_area_m2*1e4:.0f} cm², Mündung "
        f"{horn.mouth_area_m2*1e4:.0f} cm² (Verhältnis {horn.area_ratio:.2f}), Weg {horn.length_m:.2f} m, "
        f"fc {horn.cutoff_hz:.1f} Hz. Kanalhöhen folgen dem Flächengesetz; die geraden, geneigten "
        f"Zwischenböden bilden es je Lauf als Sehne ab (max. Abweichung {horn.max_area_deviation*100:.0f} %). "
        "Ebene Wellen, keine Richtwirkung, Mündung als Kolben in der Frontwand.")))
    if abs(horn.cutoff_hz-target_hz)/target_hz > 0.15:
        notes.append(("HORN_CUTOFF_TARGET",
                      (f"Horn-Grenzfrequenz {horn.cutoff_hz:.1f} Hz statt Ziel {target_hz:.1f} Hz "
                       "(Hals, Länge und Mündung folgen aus Gehäusemaßen); Breite/Höhe/Volumen anpassen.")))
    if horn.mouth_area_m2 < 0.5*horn.mouth_min_area_m2:
        notes.append((None, (
            f"Mündung {horn.mouth_area_m2*1e4:.0f} cm² ist nur {horn.mouth_area_m2/horn.mouth_min_area_m2*100:.0f} % "
            f"der freien Mindestfläche {horn.mouth_min_area_m2*1e4:.0f} cm² für fc (Umfang = Wellenlänge); "
            "Wand-/Eckaufstellung hilft, die Basserweiterung unterhalb der Mündungsgrenze bleibt begrenzt.")))
    if horn.min_turn_area_ratio < 0.9:
        notes.append(("HORN_TURN_CONSTRICTION",
                      (f"Umlenkspalt engt den Horn-Querschnitt bis auf {horn.min_turn_area_ratio*100:.0f} % ein; "
                       "45°-Umlenkblech oder größere Tiefe einplanen.")))
    if horn.max_area_deviation > 0.12:
        notes.append((None, "Sehnenabweichung zum Flächengesetz > 12 %; mehr Läufe oder Gehrungsleisten verwenden."))
    if horn.law_kind == "scoop":
        notes.append((None, "Scoop: empirischer, parabolischer Flächenverlauf (kein Literaturgesetz); fc nur Näherung."))
    if horn.law_kind == "tractrix":
        notes.append((None, (
            "Tractrix: fc = c/(2π·a) folgt aus dem Mündungsradius a; die Mündung wird durch Gehäusegröße und "
            "baubare Brettabweichung begrenzt, ein Tiefbass-fc braucht eine Mündung von mehreren m² "
            f"(hier fc {horn.cutoff_hz:.0f} Hz).")))
    if vas_m3:
        notes.append((None, (
            f"Kompressionskammer {horn.chamber_volume_m3*1000:.0f} l (Vas {vas_m3*1000:.0f} l), "
            f"Kompressionsverhältnis Sd/Hals {horn.compression_ratio:.1f}.")))
    return notes
