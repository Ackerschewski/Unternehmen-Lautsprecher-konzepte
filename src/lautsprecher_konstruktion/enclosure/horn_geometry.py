"""Horn area laws and constant-width fold geometry shared by the horn families.

Area laws (S = cross-section area, s = path coordinate from the throat, c = speed of sound):

* exponential (Webster/Olson): S = S_T e^(m s), cutoff fc = m c / (4 pi)
* conical: S = S_T (1 + s/x0)^2, corner frequency fc = c / (2 pi x0)
* hyperbolic (Salmon family): S = S_T (cosh(s/x0) + T sinh(s/x0))^2, fc = c / (2 pi x0)
* tractrix: body of revolution with radius r(x), mouth radius a, fc = c / (2 pi a);
  length from throat radius r_T: x = a ln((a + sqrt(a^2-r^2))/r) - sqrt(a^2-r^2)
* scoop: empirical parabolic area growth S = S_T (1 + (R-1)(s/L)^2). Not a textbook
  law; its cutoff is only the mean exponential equivalent c ln(R) / (4 pi L).

Folded horns are built from constant-width panels, so a channel height is
h(s) = S(s) / W. Septa are straight (inclined) boards; the built profile is the
chord of the law inside each run and the deviation is reported.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from math import cosh, exp, hypot, log, pi, sinh, sqrt

C_AIR = 343.0
HYPEX_T = 0.5
LAW_LABELS = {
    "exponential": "Exponential S=S0·e^(m·s), fc=m·c/4π",
    "conical": "Konisch S=S0·(1+s/x0)², Eckfrequenz c/(2π·x0)",
    "hyperbolic": f"Hyperbolisch (Salmon) T={HYPEX_T}, S=S0·(cosh(s/x0)+T·sinh(s/x0))², fc=c/(2π·x0)",
    "tractrix": "Tractrix r(x), fc=c/(2π·a) mit Mundradius a",
    "scoop": "Scoop: empirisch S=S0·(1+(R-1)·(s/L)²), kein Literaturgesetz (fc nur Näherung)",
}


@dataclass(frozen=True)
class AreaLaw:
    kind: str
    throat_area_m2: float
    mouth_area_m2: float
    length_m: float
    cutoff_hz: float
    parameter: float
    flare_start_m: float = 0.0   # tractrix: straight throat duct of constant area before the flare

    def area(self, s: float) -> float:
        s = min(max(s, 0.0), self.length_m)
        s0, ratio, length = self.throat_area_m2, self.mouth_area_m2/self.throat_area_m2, self.length_m
        if self.kind == "exponential":
            return s0*exp(self.parameter*s)
        if self.kind == "conical":
            return s0*(1+s/self.parameter)**2
        if self.kind == "hyperbolic":
            x0 = self.parameter
            return s0*(cosh(s/x0)+HYPEX_T*sinh(s/x0))**2
        if self.kind == "scoop":
            return s0*(1+(ratio-1)*(s/length)**2)
        if self.kind == "tractrix":
            a = self.parameter
            if s <= self.flare_start_m:
                return s0
            target = (length-s)/a
            lo, hi = sqrt(s0/pi)/a, 1.0
            for _ in range(60):
                mid = (lo+hi)/2
                if _tractrix_axial(mid) > target:
                    lo = mid
                else:
                    hi = mid
            return pi*(a*(lo+hi)/2)**2
        raise ValueError(kind_error(self.kind))


def kind_error(kind: str) -> str:
    return f"Unbekanntes Horngesetz {kind}"


def _tractrix_axial(rho: float) -> float:
    tangent = sqrt(max(0.0, 1-rho*rho))
    return log((1+tangent)/rho)-tangent


def tractrix_length_m(throat_area_m2: float, mouth_radius_m: float) -> float:
    rho = sqrt(throat_area_m2/pi)/mouth_radius_m
    return mouth_radius_m*_tractrix_axial(rho)


def make_law(kind: str, throat_area_m2: float, mouth_area_m2: float, length_m: float) -> AreaLaw:
    """Law with given throat and mouth area over ``length_m``.

    Tractrix: the flare length follows from throat and mouth radius; a shorter flare
    is preceded by a straight throat duct, a too long one is limited to ``length_m``.
    """
    if throat_area_m2 <= 0 or length_m <= 0:
        raise ValueError("Horn braucht positive Halsfläche und Länge")
    if kind == "tractrix":
        r_t = sqrt(throat_area_m2/pi)
        a = sqrt(mouth_area_m2/pi) if mouth_area_m2 > throat_area_m2 else 0.0
        if a <= r_t or tractrix_length_m(throat_area_m2, a) > length_m:
            # mouth too large for the available length: use the longest tractrix that fits
            lo, hi = r_t*1.0000001, r_t*400
            for _ in range(80):
                mid = (lo+hi)/2
                if tractrix_length_m(throat_area_m2, mid) < length_m:
                    lo = mid
                else:
                    hi = mid
            a = (lo+hi)/2
        flare = tractrix_length_m(throat_area_m2, a)
        return AreaLaw(kind, throat_area_m2, pi*a*a, length_m, C_AIR/(2*pi*a), a, length_m-flare)
    if mouth_area_m2 <= throat_area_m2:
        raise ValueError("Mündungsfläche muss größer als Halsfläche sein")
    ratio = mouth_area_m2/throat_area_m2
    if kind == "exponential":
        m = log(ratio)/length_m
        return AreaLaw(kind, throat_area_m2, mouth_area_m2, length_m, C_AIR*m/(4*pi), m)
    if kind == "conical":
        x0 = length_m/(sqrt(ratio)-1)
        return AreaLaw(kind, throat_area_m2, mouth_area_m2, length_m, C_AIR/(2*pi*x0), x0)
    if kind == "hyperbolic":
        target = sqrt(ratio)
        lo, hi = 0.0, 40.0
        for _ in range(80):
            mid = (lo+hi)/2
            if cosh(mid)+HYPEX_T*sinh(mid) < target:
                lo = mid
            else:
                hi = mid
        u = (lo+hi)/2
        x0 = length_m/u
        return AreaLaw(kind, throat_area_m2, mouth_area_m2, length_m, C_AIR/(2*pi*x0), x0)
    if kind == "scoop":
        return AreaLaw(kind, throat_area_m2, mouth_area_m2, length_m,
                       C_AIR*log(ratio)/(4*pi*length_m), 0.0)
    raise ValueError(kind_error(kind))


def olson_min_mouth_area_m2(cutoff_hz: float) -> float:
    """Mouth circumference = wavelength at fc (free-space rule of thumb)."""
    return pi*(C_AIR/(2*pi*cutoff_hz))**2


# --------------------------------------------------------------------------- fold geometry

@dataclass(frozen=True)
class RunGeometry:
    index: int
    x_start_m: float
    x_end_m: float
    h_start_m: float
    h_end_m: float
    s_start_m: float
    s_end_m: float
    h_nodes_m: tuple[float, ...] = ()   # built heights on the common x grid (0..depth)

    @property
    def length_m(self) -> float:
        return abs(self.x_end_m-self.x_start_m)


@dataclass(frozen=True)
class SeptumGeometry:
    """Septum as a polyline of straight facets; y is the depth of its upper face below the inner top."""
    index: int
    points_m: tuple[tuple[float, float], ...]   # (x, y), x ascending

    @property
    def facet_lengths_m(self) -> tuple[float, ...]:
        return tuple(hypot(b[0]-a[0], b[1]-a[1]) for a, b in zip(self.points_m, self.points_m[1:], strict=False))

    @property
    def length_m(self) -> float:
        return sum(self.facet_lengths_m)

    @property
    def rise_m(self) -> float:
        return self.points_m[-1][1]-self.points_m[0][1]

    @property
    def x1_m(self) -> float:
        return self.points_m[0][0]

    @property
    def x2_m(self) -> float:
        return self.points_m[-1][0]

    @property
    def y1_m(self) -> float:
        return self.points_m[0][1]

    @property
    def y2_m(self) -> float:
        return self.points_m[-1][1]


@dataclass(frozen=True)
class HornDetails:
    law_kind: str
    law_label: str
    throat_area_m2: float
    mouth_area_m2: float
    cutoff_hz: float
    length_m: float
    width_m: float
    depth_m: float
    runs: tuple[RunGeometry, ...]
    septa: tuple[SeptumGeometry, ...]
    turn_gaps_m: tuple[float, ...]          # gap before run k (index 0 = throat gap / unused)
    chamber_front_m: float
    chamber_rear_m: float
    chamber_volume_m3: float
    acoustic_segments: tuple[tuple[float, float], ...]
    profile_s_m: tuple[float, ...]
    profile_area_m2: tuple[float, ...]
    max_area_deviation: float
    min_turn_area_ratio: float
    compression_ratio: float
    mouth_min_area_m2: float
    facets_per_septum: int = 1

    @property
    def area_ratio(self) -> float:
        return self.mouth_area_m2/self.throat_area_m2

    @property
    def flare_per_m(self) -> float:
        return 4*pi*self.cutoff_hz/C_AIR


AreaFactory = Callable[[float, float], Callable[[float], float]]


def trace_path(depth: float, width: float, t: float, runs: int, factory: AreaFactory,
               mode: str, throat_gap: float | None = None,
               gap_limits: tuple[float, float] = (0.03, 0.45)) -> tuple[list[RunGeometry], list[float], float]:
    """Centre-line path of a constant-width fold; returns runs, gaps (index k-1) and length.

    ``depth`` is the run extent, ``mode`` is "rear" (run 1 starts at the throat gap
    at the rear, mouth at the front) or "tapped" (run 1 starts at the closed end x=0).
    """
    gmin, gmax = gap_limits[0], gap_limits[1]*depth
    n = runs
    gaps = [throat_gap if throat_gap is not None else 0.0]+[0.1]*(n-1)
    length, first_end = n*depth, depth
    result: list[RunGeometry] = []
    for _ in range(60):
        area = factory(length, first_end)
        xs: list[tuple[float, float]] = []
        for k in range(1, n+1):
            if mode == "rear":
                start = depth-gaps[0]/2 if k == 1 else xs[-1][1]
                forward = k % 2 == 0           # front->rear
            else:
                start = 0.0 if k == 1 else xs[-1][1]
                forward = k % 2 == 1
            if k == n:
                end = depth if forward else 0.0
            elif forward:
                end = depth-gaps[k]/2
            else:
                end = gaps[k]/2
            xs.append((start, end))
        s = 0.0
        new_runs: list[RunGeometry] = []
        new_gaps = list(gaps)
        prev_end_h = 0.0
        for k, (xa, xb) in enumerate(xs, start=1):
            if k > 1:
                # turn between run k-1 and k: path length uses both channel heights
                turn_mid = s+(prev_end_h/2+t/2)
                new_gaps[k-1] = min(max(area(turn_mid)/width, gmin), gmax)
                start_h = area(s+(new_gaps[k-1]+t)/2)/width
                s += (prev_end_h+start_h)/2+t
            else:
                start_h = area(0.0)/width
            s_end = s+abs(xb-xa)
            end_h = area(s_end)/width
            new_runs.append(RunGeometry(k, xa, xb, start_h, end_h, s, s_end))
            prev_end_h, s = end_h, s_end
            if k == 1:
                first_end = s_end
        converged = abs(s-length) < 1e-7 and all(abs(a-b) < 1e-7 for a, b in zip(gaps, new_gaps, strict=True))
        gaps, length, result = new_gaps, s, new_runs
        if converged:
            break
    return result, gaps, length


def height_at(run: RunGeometry, x: float) -> float:
    span = run.x_end_m-run.x_start_m
    if span == 0:
        return run.h_start_m
    f = (x-run.x_start_m)/span
    return max(0.012, run.h_start_m+(run.h_end_m-run.h_start_m)*f)


def chord_deviation(run: RunGeometry, area: Callable[[float], float], width: float) -> float:
    worst = 0.0
    for i in range(1, 12):
        f = i/12
        ideal = area(run.s_start_m+(run.s_end_m-run.s_start_m)*f)/width
        built = run.h_start_m+(run.h_end_m-run.h_start_m)*f
        worst = max(worst, abs(built-ideal)/ideal)
    return worst


def run_slices(run: RunGeometry, width: float, count: int = 10) -> list[tuple[float, float]]:
    ds = (run.s_end_m-run.s_start_m)/count
    return [(width*(run.h_start_m+(run.h_end_m-run.h_start_m)*(i+0.5)/count), ds) for i in range(count)]
