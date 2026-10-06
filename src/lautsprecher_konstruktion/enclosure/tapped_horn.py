"""Folded tapped horn: constant-width path, driver on a flat septum, both cone sides loaded.

Layout (side view, front on the left): the runs are VERTICAL (length = inner height) and
stacked along the depth, run 1 (closed end at the top) at the back, the last run at the
front baffle. The driver sits on the vertical first septum F1 with its axis along the
depth: its magnet side loads run 1 at the *rear tap*, its cone side loads run 2 at the
*front tap*; between the taps the path is the U-turn around the lower end of F1 (about
twice the run length), which is what a tall folded tapped horn needs for a large tap
spacing. The mouth is a window in the front baffle at the lower end of the last run. The
cross-section is constant (run 1) up to the driver and then expands exponentially to
the mouth. Following Danley/Kolbrek the path should be about one half wavelength at
the design frequency (c/2L) and at least a quarter wavelength at the cutoff.
The heights are given by the area law; the floor closure is distributed over runs
2..n, and the remaining deviation is reported.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from math import exp, log, pi

import numpy as np

from lautsprecher_konstruktion.drivers.models import Driver
from lautsprecher_konstruktion.enclosure.horn_geometry import (
    C_AIR,
    HornDetails,
    RunGeometry,
    SeptumGeometry,
    trace_path,
)
from lautsprecher_konstruktion.enclosure.rectangular import CabinetDimensions, CutPanel

TAPPED_RUN_COUNTS = (3, 5, 7)   # odd: the last (front) run leads down to the mouth window
FACET_COUNTS = (1, 2, 3, 4)
DEVIATION_LIMIT = 0.20


@dataclass(frozen=True)
class TappedHorn:
    upper_height_m: float            # run 1 (magnet side of the driver)
    lower_height_m: float            # mouth channel height (last run, at the mouth)
    turn_gap_m: float                # turn gap at the rear end of F1
    baffle_length_m: float           # F1 length
    driver_depth_from_front_m: float   # driver centre measured along F1 from the closed (top) end
    path_length_m: float
    quarter_wave_hz: float
    mouth_width_m: float
    mouth_height_m: float
    panel: CutPanel                  # F1
    panels: tuple[CutPanel, ...] = ()
    details: HornDetails | None = None
    rear_tap_s_m: float = 0.0
    front_tap_s_m: float = 0.0
    tap_nodes: tuple[int, int] = (0, 0)   # node indices of the taps in details.acoustic_segments
    cutoff_hz: float = 0.0                # exponential flare cutoff of the expanding part
    closed_end_area_m2: float = 0.0

    @property
    def half_wave_hz(self) -> float:
        return C_AIR/(2*self.path_length_m)

    @property
    def tap_spacing_m(self) -> float:
        return self.front_tap_s_m-self.rear_tap_s_m


def _law_factory(closed_area: float, mouth_area: float):
    def factory(length: float, first_end: float):
        span = max(length-first_end, 1e-6)
        rate = log(mouth_area/closed_area)/span

        def area(s: float) -> float:
            return closed_area if s <= first_end else closed_area*exp(rate*(s-first_end))
        return area
    return factory


def _candidate(cabinet: CabinetDimensions, driver: Driver, runs: int, facets: int,
               mouth_area: float):
    """Geometry for a given mouth area; returns (details, tap data, residual, devs) or None."""
    t, w, d, h = (cabinet.panel_thickness_m, cabinet.internal_width_m,
                  cabinet.internal_height_m, cabinet.internal_depth_m)   # d: run length, h: stack
    h1 = (driver.mounting_depth_m or 0.0)+0.025
    closed = w*h1
    path, gaps, length = trace_path(d, w, t, runs, _law_factory(closed, mouth_area), "tapped", None)
    area = _law_factory(closed, mouth_area)(length, path[0].s_end_m)
    grid = [d*j/facets for j in range(facets+1)]

    def node_h(run: RunGeometry, x: float) -> float:
        lo, hi = sorted((run.x_start_m, run.x_end_m))
        xc = min(max(x, lo), hi)
        return max(0.012, area(run.s_start_m+abs(xc-run.x_start_m))/w)

    ideal = [[node_h(r, x) for x in grid] for r in path]
    # closure: h1 + sum(runs 2..n) + (n-1) boards = H at every node of the grid
    residual = []
    built = [[h1]*(facets+1)]
    for j in range(facets+1):
        total = h1+t+sum(ideal[k][j] for k in range(1, runs))+(runs-2)*t
        residual.append(h-total)
    for k in range(1, runs):
        built.append([ideal[k][j]+residual[j]/(runs-1) for j in range(facets+1)])
    return path, gaps, length, area, grid, built, ideal, residual, h1, closed


def _finish(cabinet: CabinetDimensions, driver: Driver, runs: int, facets: int, mouth_area: float):
    t, w, d = cabinet.panel_thickness_m, cabinet.internal_width_m, cabinet.internal_height_m
    path, gaps, length, area, grid, built, _ideal, _res, h1, closed = _candidate(
        cabinet, driver, runs, facets, mouth_area)
    if min(min(row) for row in built) < 0.035:
        return None
    runs_geo = [replace(r, h_nodes_m=tuple(built[k])) for k, r in enumerate(path)]
    # septa top-down; F1 (index 1) is flat and carries the driver
    septa = []
    ys = [h1]*(facets+1)
    for k in range(1, runs):                       # septum k separates run k and k+1
        if k > 1:
            ys = [yp+t+hn for yp, hn in zip(ys, built[k-1], strict=True)]
        gap = gaps[k]
        x1, x2 = (0.0, d-gap) if k % 2 == 1 else (gap, d)
        if k == 1:
            pts = ((x1, h1), (x2, h1))
        else:
            mid = [(x, y) for x, y in zip(grid, ys, strict=True) if x1 < x < x2]
            pts = ((x1, float(np.interp(x1, grid, ys))), *mid, (x2, float(np.interp(x2, grid, ys))))
        septa.append(SeptumGeometry(k, tuple(pts)))
    # driver and taps
    f1 = septa[0]
    f1_length = f1.length_m
    x_d = f1_length/2
    rear_tap = x_d
    front_tap = path[1].s_start_m+(path[1].x_start_m-x_d)
    # acoustic segments with nodes at the taps
    segments: list[tuple[float, float]] = []
    tap_nodes = [0, 0]

    def add_piece(run: RunGeometry, s_a: float, s_b: float, slices: int = 8) -> None:
        for i in range(slices):
            s_mid = s_a+(s_b-s_a)*(i+0.5)/slices
            x = run.x_start_m+(run.x_end_m-run.x_start_m)*(s_mid-run.s_start_m)/(run.s_end_m-run.s_start_m)
            segments.append((w*float(np.interp(x, grid, run.h_nodes_m)), (s_b-s_a)/slices))

    worst_turn = 9.0
    for run in runs_geo:
        if run.index > 1:
            prev = runs_geo[run.index-2]
            tau = (prev.h_end_m+run.h_start_m)/2+t
            turn_area = w*gaps[run.index-1]
            segments.append((turn_area, tau))
            worst_turn = min(worst_turn, turn_area/area((prev.s_end_m+run.s_start_m)/2))
        if run.index == 1:
            add_piece(run, run.s_start_m, rear_tap)
            tap_nodes[0] = len(segments)
            add_piece(run, rear_tap, run.s_end_m)
        elif run.index == 2:
            add_piece(run, run.s_start_m, front_tap)
            tap_nodes[1] = len(segments)
            add_piece(run, front_tap, run.s_end_m)
        else:
            add_piece(run, run.s_start_m, run.s_end_m)
    worst_dev = 0.0
    for k, run in enumerate(runs_geo):
        lo, hi = sorted((run.x_start_m, run.x_end_m))
        for i in range(1, 30):
            x = lo+(hi-lo)*i/30
            ideal_h = area(run.s_start_m+abs(x-run.x_start_m))/w
            worst_dev = max(worst_dev, abs(float(np.interp(x, grid, built[k]))-ideal_h)/ideal_h)
    profile_s = tuple(length*i/60 for i in range(61))
    mouth_built = w*runs_geo[-1].h_end_m
    exp_len = max(length-path[0].s_end_m, 1e-6)
    flare = log(mouth_area/closed)/exp_len
    details = HornDetails(
        "tapped", "Tapped Horn: konstant bis zum Treiber, danach exponentiell", closed, mouth_built,
        C_AIR*flare/(4*pi), length, w, d, tuple(runs_geo), tuple(septa), tuple(gaps),
        h1, h1, w*d*h1, tuple(segments), profile_s, tuple(area(s) for s in profile_s),
        worst_dev, worst_turn, 0.0, 0.0, facets)
    return details, rear_tap, front_tap, (tap_nodes[0], tap_nodes[1]), f1_length, x_d


def design_tapped_horn(cabinet: CabinetDimensions, driver: Driver,
                       target_hz: float | None = None) -> TappedHorn:
    t=cabinet.panel_thickness_m
    diameter=driver.outer_diameter_m or driver.cutout_diameter_m
    cutout=driver.cutout_diameter_m
    if diameter is None or cutout is None:
        raise ValueError('Tapped-Horn benötigt Außen- und Ausschnittdurchmesser des Treibers')
    gap=max(0.035,min(0.07,cabinet.internal_height_m*0.08))
    length=cabinet.internal_height_m-gap
    if length<diameter+0.02 or cabinet.internal_width_m<diameter+0.02:
        raise ValueError('Tapped-Horn: F1 zu kurz oder schmal für Treiber und 10 mm Randabstand')
    bolt_span=(driver.bolt_circle_diameter_m or 0)+(driver.bolt_hole_diameter_m or 0)
    if bolt_span and (bolt_span+0.02>length or bolt_span+0.02>cabinet.internal_width_m):
        raise ValueError('Tapped-Horn: Treiber-Lochkreis liegt zu nah an der F1-Kante')
    w = cabinet.internal_width_m
    best = None
    for runs in TAPPED_RUN_COUNTS:
        h1 = (driver.mounting_depth_m or 0.0)+0.025
        closed = w*h1
        # mouth area such that the stack closes on average (bisection)
        def mean_residual(mouth: float, runs: int = runs) -> float:
            r = _candidate(cabinet, driver, runs, 1, mouth)[7]
            return sum(r)/len(r)
        lo, hi = closed*1.001, closed*8
        if mean_residual(lo) < 0:
            continue                      # even a straight pipe does not fit this many runs
        if mean_residual(hi) > 0:
            mouth = hi
        else:
            for _ in range(40):
                mid = (lo+hi)/2
                if mean_residual(mid) > 0:
                    lo = mid
                else:
                    hi = mid
            mouth = (lo+hi)/2
        result = None
        for facets in FACET_COUNTS:
            result = _finish(cabinet, driver, runs, facets, mouth)
            if result is not None and result[0].max_area_deviation <= 0.06:
                break
        if result is None or result[0].max_area_deviation > DEVIATION_LIMIT:
            continue
        details = result[0]
        if min(r.h_start_m for r in details.runs) < 0.035:
            continue
        half = C_AIR/(2*details.length_m)
        score = (abs(log(half/target_hz)) if target_hz else abs(runs-6)*0.01)
        score += 1.5*max(0.0, details.max_area_deviation-0.08)+max(0.0, 0.9-details.min_turn_area_ratio)
        if best is None or score < best[0]:
            best = (score, result, runs)
    if best is None:
        raise ValueError('Tapped-Horn: Tiefe reicht für Magnet, Treiber-Septum und Hornläufe nicht; '
                         'Tiefe oder Höhe vergrößern')
    details, rear_tap, front_tap, tap_nodes, f1_length, x_d = best[1]
    septa_panels = tuple(
        CutPanel(('Tapped-Horn F1 mit Treiberausschnitt' if s.index == 1 else
                  f"Tapped-Horn F{s.index}{'.'+str(j) if len(s.points_m) > 2 else ''} "
                  f"({'hinten' if s.index % 2 else 'vorn'} offen, geneigt {abs(b[1]-a[1])*1000:.0f} mm)"),
                 1, w, length_i, t)
        for s in details.septa
        for j, (a, b, length_i) in enumerate(zip(s.points_m, s.points_m[1:], s.facet_lengths_m,
                                                  strict=False), start=1))
    mouth_run = details.runs[-1]
    return TappedHorn(
        details.runs[0].h_start_m, mouth_run.h_end_m, details.turn_gaps_m[1], f1_length, x_d,
        details.length_m, C_AIR/(4*details.length_m), max(0.0, w-0.02),
        max(0.0, mouth_run.h_end_m-0.02), septa_panels[0], septa_panels, details,
        rear_tap, front_tap, tap_nodes, details.cutoff_hz, details.throat_area_m2)


def tapped_baffle_displacement_m3(horn: TappedHorn, driver: Driver) -> float:
    assert driver.cutout_diameter_m is not None
    volume = sum(p.width_m*p.height_m*p.thickness_m for p in horn.panels)
    return volume-pi*(driver.cutout_diameter_m/2)**2*horn.panel.thickness_m


def tapped_horn_notes(horn: TappedHorn, target_hz: float | None) -> list[tuple[str | None, str]]:
    details = horn.details
    assert details is not None
    notes: list[tuple[str | None, str]] = [(None, (
        f"Tapped Horn: Weg {horn.path_length_m:.2f} m = {horn.path_length_m/(C_AIR/horn.half_wave_hz/2):.2f}·λ/2 bei "
        f"{horn.half_wave_hz:.1f} Hz (c/2L), λ/4 bei {horn.quarter_wave_hz:.1f} Hz. Treiber auf F1 bei "
        f"s = {horn.rear_tap_s_m*1000:.0f} mm (Magnetseite) und s = {horn.front_tap_s_m*1000:.0f} mm (Membranseite); "
        f"Tap-Abstand {horn.tap_spacing_m*1000:.0f} mm. Querschnitt konstant {horn.closed_end_area_m2*1e4:.0f} cm² "
        f"bis Lauf 1, dann exponentiell auf {details.mouth_area_m2*1e4:.0f} cm² an der Mündung "
        f"(Abweichung gebaut/Gesetz max. {details.max_area_deviation*100:.0f} %). "
        "Plane Wellen; Tap-Lage nach Literaturregel (Danley/Kolbrek) nicht optimiert, in Hornresp/Messung prüfen."))]
    if target_hz and abs(horn.half_wave_hz-target_hz)/target_hz > 0.15:
        notes.append(("TAPPED_LENGTH_TARGET", (
            f"Tapped-Horn-Weg ergibt c/2L = {horn.half_wave_hz:.1f} Hz statt Ziel {target_hz:.1f} Hz; "
            "Volumen, Höhe oder Tiefe anpassen.")))
    if details.min_turn_area_ratio < 0.9:
        notes.append(("HORN_TURN_CONSTRICTION", (
            f"Umlenkspalt engt den Querschnitt bis auf {details.min_turn_area_ratio*100:.0f} % ein; "
            "45°-Umlenkblech oder größere Tiefe einplanen.")))
    return notes
