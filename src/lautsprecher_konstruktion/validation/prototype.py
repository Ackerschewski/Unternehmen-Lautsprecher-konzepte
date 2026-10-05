"""Compare the simulated design with measurements of a built prototype.

The comparison is deliberately descriptive: it reports deviations and, for
vented types, a port-length correction derived from the measured impedance
minimum. It never changes the project and never claims the model is validated;
validation needs real measurements of several drivers and enclosure types.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Literal

import numpy as np
from scipy.optimize import brentq
from scipy.signal import find_peaks

from lautsprecher_konstruktion.acoustics.response import sealed_response_db
from lautsprecher_konstruktion.acoustics.vented import simulate_vented
from lautsprecher_konstruktion.arrays import ComplexArray, FloatArray
from lautsprecher_konstruktion.crossover.measurements import FrequencyResponseData, ImpedanceData
from lautsprecher_konstruktion.services.design import DesignBundle

# Rating grid (engineering rules of thumb, not a standard).
RMS_GOOD_DB = 1.5
RMS_ACCEPTABLE_DB = 3.0
TUNING_GOOD_PCT = 5.0
TUNING_ACCEPTABLE_PCT = 10.0
CORRECTION_THRESHOLD_PCT = 2.0
DEFAULT_BAND_HZ = (20.0, 300.0)
MIN_BAND_OCTAVES = 1.0


@dataclass(frozen=True)
class FrequencyComparison:
    band_hz: tuple[float, float]
    points: int
    offset_db: float
    rms_db: float
    max_abs_db: float
    f3_sim_hz: float | None
    f3_meas_hz: float | None
    grid_hz: FloatArray = field(repr=False, compare=False)
    sim_db: FloatArray = field(repr=False, compare=False)
    meas_db: FloatArray = field(repr=False, compare=False)

    @property
    def f3_delta_pct(self) -> float | None:
        if self.f3_sim_hz is None or self.f3_meas_hz is None:
            return None
        return 100.0 * (self.f3_meas_hz - self.f3_sim_hz) / self.f3_sim_hz


@dataclass(frozen=True)
class ImpedanceComparison:
    kind: Literal["vented", "sealed"]
    marker_name: str
    sim_marker_hz: float | None
    meas_marker_hz: float | None
    peaks_sim_hz: tuple[float, ...]
    peaks_meas_hz: tuple[float, ...]
    grid_hz: FloatArray = field(repr=False, compare=False)
    sim_ohm: FloatArray | None = field(default=None, repr=False, compare=False)
    meas_ohm: FloatArray | None = field(default=None, repr=False, compare=False)

    @property
    def delta_pct(self) -> float | None:
        if self.sim_marker_hz is None or self.meas_marker_hz is None:
            return None
        return 100.0 * (self.meas_marker_hz - self.sim_marker_hz) / self.sim_marker_hz


@dataclass(frozen=True)
class PortCorrection:
    current_length_mm: float
    suggested_length_mm: float
    change_mm: float
    feasible: bool
    assumption: str
    method: Literal["model", "scaling"] = "model"


@dataclass(frozen=True)
class PrototypeReport:
    project_name: str
    enclosure_type: str
    frequency: FrequencyComparison | None
    impedance: ImpedanceComparison | None
    port_correction: PortCorrection | None
    findings: tuple[str, ...]
    verdict: Literal["gut", "akzeptabel", "abweichend", "nicht bewertbar"]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _first_f3(f: FloatArray, level_db: FloatArray) -> float | None:
    crossings = np.flatnonzero((level_db[:-1] < -3.0) & (level_db[1:] >= -3.0))
    if not crossings.size:
        return None
    i = int(crossings[0])
    a = (-3.0 - level_db[i]) / (level_db[i + 1] - level_db[i])
    return float(np.exp(np.log(f[i]) + a * (np.log(f[i + 1]) - np.log(f[i]))))


def _interp_log(f: FloatArray, xs: tuple[float, ...], ys: tuple[float, ...] | FloatArray) -> FloatArray:
    return np.asarray(np.interp(np.log(f), np.log(np.asarray(xs)), np.asarray(ys, dtype=float)), dtype=float)


def simulated_curves(bundle: DesignBundle) -> tuple[FloatArray, FloatArray, ComplexArray | None]:
    """Frequency grid, relative level in dB and (if modelled) complex impedance."""
    response = bundle.vented_response
    if response is not None:
        return response.frequencies_hz, response.response_db, response.impedance_ohm
    f = np.geomspace(10.0, 500.0, 400)
    return f, sealed_response_db(bundle.acoustic_driver, bundle.target_net_volume_m3, f), None


def _two_peaks(f: FloatArray, z: FloatArray, upper_hz: float) -> tuple[int, ...]:
    zz = z[f <= upper_hz]  # f is sorted, so indices match the full grid
    if zz.size < 5:
        return ()
    span = float(zz.max() - zz.min())
    if span <= 0:
        return ()
    peaks, props = find_peaks(zz, prominence=0.15 * span)
    if peaks.size == 0:
        return ()
    order = np.argsort(props["prominences"])[::-1][:2]
    return tuple(sorted(int(peaks[i]) for i in order))


def _refine_minimum(f: FloatArray, z: FloatArray, index: int) -> float:
    """Parabolic refinement of a minimum on a logarithmic frequency axis."""
    if index <= 0 or index >= len(z) - 1:
        return float(f[index])
    x = np.log(f[index - 1:index + 2])
    y = z[index - 1:index + 2]
    denominator = (x[0] - x[1]) * (x[0] - x[2]) * (x[1] - x[2])
    a = (x[2] * (y[1] - y[0]) + x[1] * (y[0] - y[2]) + x[0] * (y[2] - y[1])) / denominator
    b = (x[2] ** 2 * (y[0] - y[1]) + x[1] ** 2 * (y[2] - y[0]) + x[0] ** 2 * (y[1] - y[2])) / denominator
    if a <= 0:
        return float(f[index])
    return float(np.exp(-b / (2 * a)))


def _vented_marker(f: FloatArray, z: FloatArray, upper_hz: float) -> tuple[float | None, tuple[float, ...]]:
    peaks = _two_peaks(f, z, upper_hz)
    freqs = tuple(float(f[i]) for i in peaks)
    if len(peaks) < 2:
        return None, freqs
    lo, hi = peaks
    minimum = lo + int(np.argmin(z[lo:hi + 1]))
    return _refine_minimum(f, z, minimum), freqs


def _sealed_marker(f: FloatArray, z: FloatArray, upper_hz: float) -> tuple[float | None, tuple[float, ...]]:
    peaks = _two_peaks(f, z, upper_hz)
    if not peaks:
        return None, ()
    best = max(peaks, key=lambda i: float(z[i]))
    return float(f[best]), (float(f[best]),)


# ---------------------------------------------------------------------------
# comparison
# ---------------------------------------------------------------------------

def _compare_frequency(bundle: DesignBundle, measured: FrequencyResponseData,
                       band_hz: tuple[float, float], align: bool,
                       findings: list[str]) -> FrequencyComparison | None:
    sim_f, sim_db, _ = simulated_curves(bundle)
    low = max(band_hz[0], sim_f[0], measured.frequencies_hz[0])
    high = min(band_hz[1], sim_f[-1], measured.frequencies_hz[-1])
    if high <= low or np.log2(high / low) < MIN_BAND_OCTAVES:
        findings.append("Frequenzgang: Messung und Simulation überlappen im gewählten Band um weniger als eine Oktave; "
                        "Vergleich nicht möglich.")
        return None
    mask = (sim_f >= low) & (sim_f <= high)
    grid = sim_f[mask]
    sim = sim_db[mask]
    meas = _interp_log(grid, measured.frequencies_hz, measured.magnitude_db)
    offset = float(np.mean(meas - sim)) if align else 0.0
    meas_aligned = meas - offset
    residual = meas_aligned - sim
    # F3 uses the solver's convention: reference is the median level 150-300 Hz.
    f3_meas = None
    ref_mask = (np.asarray(measured.frequencies_hz) >= 150.0) & (np.asarray(measured.frequencies_hz) <= 300.0)
    if ref_mask.sum() >= 2:
        full = np.geomspace(max(measured.frequencies_hz[0], 10.0), min(measured.frequencies_hz[-1], 500.0), 400)
        level = _interp_log(full, measured.frequencies_hz, measured.magnitude_db)
        reference = float(np.median(level[(full >= 150.0) & (full <= 300.0)]))
        f3_meas = _first_f3(full, level - reference)
    else:
        findings.append("Frequenzgang: Messung deckt 150–300 Hz nicht ab; kein F3 aus der Messung bestimmt.")
    f3_sim = bundle.vented_response.f3_hz if bundle.vented_response is not None else _first_f3(sim_f, sim_db)
    return FrequencyComparison((float(low), float(high)), int(grid.size), offset,
                               float(np.sqrt(np.mean(residual**2))), float(np.max(np.abs(residual))),
                               f3_sim, f3_meas, grid, sim, meas_aligned)


def _compare_impedance(bundle: DesignBundle, measured: ImpedanceData,
                       findings: list[str]) -> ImpedanceComparison | None:
    sim_f, _, sim_z = simulated_curves(bundle)
    vented = bundle.vented_response is not None
    fs = bundle.project.driver.fs_hz
    upper = max(300.0, 6.0 * fs)
    low = max(sim_f[0], measured.frequencies_hz[0])
    high = min(sim_f[-1], measured.frequencies_hz[-1], upper)
    if high <= low:
        findings.append("Impedanz: Messbereich überlappt nicht mit dem Simulationsbereich.")
        return None
    grid = sim_f[(sim_f >= low) & (sim_f <= high)]
    meas_z = _interp_log(grid, measured.frequencies_hz, measured.magnitude_ohm)
    sim_mag = None if sim_z is None else np.abs(sim_z)[(sim_f >= low) & (sim_f <= high)]
    finder = _vented_marker if vented else _sealed_marker
    meas_marker, meas_peaks = finder(grid, meas_z, high)
    sim_marker, sim_peaks = (None, ()) if sim_mag is None else finder(grid, sim_mag, high)
    if not vented:
        sim_marker = bundle.sealed.resonance_hz if bundle.sealed is not None else None
        if sim_marker is None:
            findings.append("Impedanz: für diesen Gehäusetyp liegt kein Referenzwert der Gehäuseresonanz vor.")
    name = "Abstimmfrequenz Fb (Impedanzminimum)" if vented else "Gehäuseresonanz Fc (Impedanzmaximum)"
    if meas_marker is None:
        findings.append("Impedanz: die erwartete Resonanzstruktur ist in der Messung nicht erkennbar "
                        "(bei Bassreflex zwei Spitzen). Messaufbau, Leckage und Portanschluss prüfen.")
    return ImpedanceComparison("vented" if vented else "sealed", name, sim_marker, meas_marker,
                               sim_peaks, meas_peaks, grid, sim_mag, meas_z)


_MODEL_TYPES = frozenset({"bass_reflex", "isobaric_vented"})
_ASSUMPTION = ("Annahme: Der Port wurde wie geplant gebaut und die Abweichung stammt allein vom Port. Gehäusevolumen, "
               "Leckage, Dämmung und Bauteiltoleranzen wirken ähnlich; deshalb in kleinen Schritten korrigieren "
               "und neu messen.")


def _model_marker(bundle: DesignBundle, delta_m: float) -> float | None:
    """Impedance minimum of the model with the port acting delta_m longer (dense grid)."""
    port = bundle.port
    assert port is not None
    cfg = bundle.project.enclosure
    built = replace(port, physical_length_m=port.physical_length_m + delta_m,
                    effective_length_m=port.effective_length_m + delta_m)
    grid = np.geomspace(10.0, 500.0, 6000)
    response = simulate_vented(bundle.acoustic_driver, bundle.target_net_volume_m3, built,
                               cfg.input_power_w, grid, ql=cfg.ql, qa=cfg.qa, qp=cfg.qp)
    if response.impedance_ohm is None:
        return None
    marker, _ = _vented_marker(grid, np.abs(response.impedance_ohm), 500.0)
    return marker


def _port_correction(bundle: DesignBundle, comparison: ImpedanceComparison) -> PortCorrection | None:
    port = bundle.port
    if (comparison.kind != "vented" or port is None or comparison.delta_pct is None
            or comparison.sim_marker_hz is None or comparison.meas_marker_hz is None
            or abs(comparison.delta_pct) < CORRECTION_THRESHOLD_PCT):
        return None
    method: Literal["model", "scaling"] = "scaling"
    delta: float | None = None
    if bundle.project.enclosure.enclosure_type in _MODEL_TYPES:
        # Solve the model for the extra port length that reproduces the measured minimum.
        target = comparison.meas_marker_hz
        try:
            delta = brentq(lambda d: (_model_marker(bundle, d) or np.nan) - target,
                           -0.9 * port.physical_length_m, 0.5, xtol=1e-6)
            method = "model"
        except (ValueError, RuntimeError):
            delta = None
    if delta is None:
        # Fb ~ 1/sqrt(Leff): the built port behaves like Leff_design * (Fb_sim/Fb_meas)^2.
        delta = port.effective_length_m * ((comparison.sim_marker_hz / comparison.meas_marker_hz) ** 2 - 1.0)
    suggested = port.physical_length_m - delta
    return PortCorrection(round(port.physical_length_m * 1000, 1), round(suggested * 1000, 1),
                          round(-delta * 1000, 1), suggested > 0.0, _ASSUMPTION, method)


def compare_prototype(bundle: DesignBundle, *, frd: FrequencyResponseData | None = None,
                      zma: ImpedanceData | None = None,
                      band_hz: tuple[float, float] = DEFAULT_BAND_HZ,
                      align_level: bool = True) -> PrototypeReport:
    """Compare simulation and measurement; at least one measurement is required."""
    if frd is None and zma is None:
        raise ValueError("Für den Prototypvergleich wird eine FRD- oder ZMA-Messung benötigt.")
    findings: list[str] = []
    frequency = _compare_frequency(bundle, frd, band_hz, align_level, findings) if frd is not None else None
    impedance = _compare_impedance(bundle, zma, findings) if zma is not None else None
    correction = _port_correction(bundle, impedance) if impedance is not None else None

    ratings: list[int] = []  # 0 good, 1 acceptable, 2 deviating
    if frequency is not None:
        ratings.append(0 if frequency.rms_db <= RMS_GOOD_DB else 1 if frequency.rms_db <= RMS_ACCEPTABLE_DB else 2)
        findings.append(f"Frequenzgang: RMS-Abweichung {frequency.rms_db:.2f} dB, maximal {frequency.max_abs_db:.2f} dB "
                        f"im Band {frequency.band_hz[0]:.0f}–{frequency.band_hz[1]:.0f} Hz (Pegel um {frequency.offset_db:+.1f} dB angeglichen).")
        if frequency.f3_delta_pct is not None and frequency.f3_sim_hz and frequency.f3_meas_hz:
            findings.append(f"F3: Simulation {frequency.f3_sim_hz:.1f} Hz, Messung {frequency.f3_meas_hz:.1f} Hz "
                            f"({frequency.f3_delta_pct:+.1f} %).")
    if impedance is not None and impedance.delta_pct is not None:
        pct = abs(impedance.delta_pct)
        ratings.append(0 if pct <= TUNING_GOOD_PCT else 1 if pct <= TUNING_ACCEPTABLE_PCT else 2)
        findings.append(f"{impedance.marker_name}: Simulation {impedance.sim_marker_hz:.1f} Hz, "
                        f"Messung {impedance.meas_marker_hz:.1f} Hz ({impedance.delta_pct:+.1f} %).")
    if correction is not None:
        direction = "kürzen" if correction.change_mm < 0 else "verlängern"
        findings.append(f"Port {direction}: von {correction.current_length_mm:.1f} mm auf "
                        f"{correction.suggested_length_mm:.1f} mm ({correction.change_mm:+.1f} mm"
                        f"{', Näherung' if correction.method == 'scaling' else ''})."
                        + ("" if correction.feasible else " Die Länge wäre nicht positiv; Querschnitt oder Volumen ändern."))
    if not ratings:
        verdict: Literal["gut", "akzeptabel", "abweichend", "nicht bewertbar"] = "nicht bewertbar"
    else:
        verdict = ("gut", "akzeptabel", "abweichend")[max(ratings)]
    return PrototypeReport(bundle.project.name, bundle.project.enclosure.enclosure_type,
                           frequency, impedance, correction, tuple(findings), verdict)


def render_report_markdown(report: PrototypeReport) -> str:
    lines = [f"# Prototypvergleich – {report.project_name}", "",
             f"Gehäusetyp: `{report.enclosure_type}` · Gesamtbewertung: **{report.verdict}**", "",
             ("> Die Bewertung ist ein Richtwert (Frequenzgang: RMS ≤ 1,5 dB gut, ≤ 3 dB akzeptabel; "
              "Abstimmung: ≤ 5 % gut, ≤ 10 % akzeptabel). Ein einzelner Prototyp validiert das Modell nicht."), "",
             "## Befunde", ""]
    lines.extend(f"- {item}" for item in report.findings)
    if report.frequency is not None:
        freq = report.frequency
        lines.extend(("", "## Frequenzgang", "", "| Größe | Wert |", "|---|---|",
                      f"| Vergleichsband | {freq.band_hz[0]:.0f}–{freq.band_hz[1]:.0f} Hz |",
                      f"| Punkte | {freq.points} |", f"| Pegelversatz | {freq.offset_db:+.2f} dB |",
                      f"| RMS-Abweichung | {freq.rms_db:.2f} dB |", f"| Maximale Abweichung | {freq.max_abs_db:.2f} dB |"))
    if report.impedance is not None:
        imp = report.impedance
        lines.extend(("", "## Impedanz", "", "| Größe | Simulation | Messung |", "|---|---|---|",
                      f"| {imp.marker_name} | {_fmt(imp.sim_marker_hz)} | {_fmt(imp.meas_marker_hz)} |",
                      (f"| Impedanzspitzen | {', '.join(f'{p:.1f} Hz' for p in imp.peaks_sim_hz) or '–'} | "
                       f"{', '.join(f'{p:.1f} Hz' for p in imp.peaks_meas_hz) or '–'} |")))
    return "\n".join(lines) + "\n"


def _fmt(value: float | None) -> str:
    return "–" if value is None else f"{value:.1f} Hz"
