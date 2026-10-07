"""The reference cases: every registered solver has at least one, and what a case proves is stated by its kind.

LITERATURE cases compare with published numbers, ANALYTIC and LIMIT cases with closed-form results computed in
``independent.py`` (never by calling the solver under test), CONSISTENCY cases only check that a solver behaves like
a physical system (finite, passive, volume as requested) and earn no trust.
"""
from __future__ import annotations

from collections.abc import Callable
from functools import partial
from math import pi, sqrt

import numpy as np

from lautsprecher_konstruktion.acoustics.aperiodic import aperiodic_q
from lautsprecher_konstruktion.acoustics.baffle import simulate_baffle
from lautsprecher_konstruktion.acoustics.bandpass import simulate_bandpass, simulate_bandpass_series
from lautsprecher_konstruktion.acoustics.sealed import solve_sealed
from lautsprecher_konstruktion.acoustics.vented import VentedResponse, simulate_vented
from lautsprecher_konstruktion.acoustics.waveguide import duct_chain, terminated
from lautsprecher_konstruktion.drivers.models import Driver
from lautsprecher_konstruktion.enclosure.isobaric import equivalent_driver
from lautsprecher_konstruktion.enclosure.passive_radiator import design_passive_radiator
from lautsprecher_konstruktion.enclosure.ports import PortDesign, round_port
from lautsprecher_konstruktion.enclosure.registry import registry
from lautsprecher_konstruktion.project.demo import demo_driver
from lautsprecher_konstruktion.validation import independent as ref
from lautsprecher_konstruktion.validation.families import solve_family
from lautsprecher_konstruktion.validation.reference import ReferenceCase, ReferenceExpectation
from lautsprecher_konstruktion.validation.trust import CaseKind

F_GRID = np.geomspace(10.0, 500.0, 400)  # the frequency grid every solver uses


def _exp(metric: str, value: float, unit: str, kind: str, tol: float, source: str, why: str = "") -> ReferenceExpectation:
    return ReferenceExpectation(metric, value, unit, kind, tol, source, why)


def _max_db_diff(a: VentedResponse, b: np.ndarray) -> float:
    return float(np.max(np.abs(a.response_db - b)))


# --- sealed -----------------------------------------------------------------------------------------------------

def _sealed_f3_table() -> dict[str, float]:
    d = demo_driver()
    out: dict[str, float] = {}
    for q in (0.5, 0.7071, 1.0):
        r = solve_sealed(d, q)
        out[f"f3_over_fc_q{q}"] = r.f3_hz / r.resonance_hz
    return out


def _sealed_relations() -> dict[str, float]:
    d = demo_driver()
    assert d.vas_m3 is not None
    r = solve_sealed(d, 0.7071)
    fc, qtc = ref.sealed_system(d.fs_hz, d.qts, d.vas_m3, r.box_volume_m3)
    return {"qtc_from_box_volume": qtc, "fc_from_box_volume": fc / (d.fs_hz * 0.7071 / d.qts)}


# --- vented -----------------------------------------------------------------------------------------------------

def _b4_driver() -> tuple[Driver, float, float]:
    qts, alpha, fb = ref.butterworth_b4(32.0)
    d = demo_driver().model_copy(update={"qts": qts, "qes": None, "qms": None})
    assert d.vas_m3 is not None
    return d, d.vas_m3 / alpha, fb


def _vented_b4() -> dict[str, float]:
    d, vb, fb = _b4_driver()
    r = simulate_vented(d, vb, round_port(box_volume_m3=vb, tuning_hz=fb, diameter_m=0.10), 1.0)
    assert r.f3_hz is not None
    return {"f3_over_fs": r.f3_hz / d.fs_hz, "peak_db": float(np.max(r.response_db))}


def _vented_closed_form() -> dict[str, float]:
    d = demo_driver().model_copy(update={"qes": None, "qms": None})
    assert d.vas_m3 is not None
    vb = 0.045
    port = round_port(box_volume_m3=vb, tuning_hz=35.0, diameter_m=0.08)
    fb = ref.helmholtz_hz(port.area_m2, port.effective_length_m, vb)
    r = simulate_vented(d, vb, port, 1.0)
    return {"max_diff_db": _max_db_diff(r, ref.small_vented_db(d.fs_hz, d.qts, d.vas_m3, vb, fb, F_GRID))}


def _vented_qb3() -> dict[str, float]:
    d = demo_driver()
    assert d.vas_m3 is not None
    vb, fb = 15.0 * d.qts**2.87 * d.vas_m3, 0.42 * d.qts**-0.96 * d.fs_hz
    r = simulate_vented(d, vb, round_port(box_volume_m3=vb, tuning_hz=fb, diameter_m=0.10), 1.0)
    assert r.f3_hz is not None
    return {"f3_hz": r.f3_hz}


def _port_tuning() -> dict[str, float]:
    vb = 0.045
    port = round_port(box_volume_m3=vb, tuning_hz=35.0, diameter_m=0.08)
    return {"tuning_hz": ref.helmholtz_hz(port.area_m2, port.effective_length_m, vb)}


# --- aperiodic --------------------------------------------------------------------------------------------------

def _aperiodic_leakage() -> dict[str, float]:
    d = demo_driver()
    assert d.vas_m3 is not None
    vb, resistance = 0.040, 3.0e5
    q = aperiodic_q(d, vb, resistance)
    fc, qtc = ref.sealed_system(d.fs_hz, d.qts, d.vas_m3, vb)
    ql, qeff, corner = ref.leakage_q(fc, qtc, vb, resistance)
    return {"ql_ratio": q.ql / ql, "qeff_ratio": q.qtc_effective / qeff, "corner_ratio": q.leak_corner_hz / corner}


def _aperiodic_closed_limit() -> dict[str, float]:
    d = demo_driver()
    assert d.vas_m3 is not None
    q = aperiodic_q(d, 0.040, 1.0e12)  # no leakage at all
    return {"qeff_over_qtc_closed": q.qtc_effective / q.qtc_closed}


def _aperiodic_response() -> dict[str, float]:
    d = demo_driver()
    vb, resistance = 0.040, 3.0e5
    tiny = PortDesign("round", 1e-3, 1e-3, 1e-3, 100.0, diameter_m=0.036)  # vent mass ~ rho L / A = 1.2 kg/m^4: negligible
    r = simulate_vented(d, vb, tiny, 1.0, F_GRID, port_resistance_pa_s_m3=resistance)
    c = ref.driver_circuit(d)
    s = 1j * 2 * pi * F_GRID
    cb = vb / (ref.RHO * ref.C**2)
    zb = resistance / (1 + s * cb * resistance)
    v = ref.cone_velocity(c, s, zb)
    radiated = c.sd * v * (s * cb * resistance / (1 + s * cb * resistance))
    return {"max_diff_db": _max_db_diff(r, ref.level_db(np.asarray(s * ref.RHO * radiated / (2 * pi), dtype=complex), F_GRID, "median"))}


# --- passive radiator -------------------------------------------------------------------------------------------

def _passive_radiator_tuning() -> dict[str, float]:
    sd, m0, fs0, vb = 0.0350, 0.060, 20.0, 0.045
    design = design_passive_radiator(box_volume_m3=vb, tuning_hz=35.0, area_m2=sd, stock_mass_kg=m0, free_air_fs_hz=fs0,
                                     qms=5.0, cutout_diameter_m=0.23, mounting_depth_m=0.06, xmax_m=0.012)
    cap = (1 / ((2 * pi * fs0) ** 2 * m0)) * sd**2
    cab = vb / (ref.RHO * ref.C**2)
    map_total = (m0 + design.added_mass_kg) / sd**2
    fb = 1 / (2 * pi * sqrt(map_total * cab * cap / (cab + cap)))
    return {"tuning_hz": fb}


def _passive_radiator_response() -> dict[str, float]:
    d = demo_driver()
    vb, mp, cp, rp = 0.045, 1.5e3, 6.0e-8, 2.0e3
    port = PortDesign("round", 0.0035, mp * 0.0035 / ref.RHO, mp * 0.0035 / ref.RHO, 25.0, diameter_m=0.067)  # L_eff chosen so rho L / A = mp
    r = simulate_vented(d, vb, port, 1.0, F_GRID, resonator_compliance_m5_n=cp, resonator_resistance_pa_s_m3=rp)
    c = ref.driver_circuit(d)
    s = 1j * 2 * pi * F_GRID
    cb = vb / (ref.RHO * ref.C**2)
    zp = rp + s * mp + 1 / (s * cp)  # radiator branch: resistance, moving mass, suspension compliance in series
    zb = 1 / (s * cb + 1 / zp)
    v = ref.cone_velocity(c, s, zb)
    radiated = c.sd * v * (s * cb * zp / (1 + s * cb * zp))  # U_total = U_cone (1 - Zb/Zp)
    return {"max_diff_db": _max_db_diff(r, ref.level_db(np.asarray(s * ref.RHO * radiated / (2 * pi), dtype=complex), F_GRID, "median"))}


# --- bandpass ---------------------------------------------------------------------------------------------------

def _bandpass4_closed_form() -> dict[str, float]:
    d = demo_driver()
    rear, front = 0.030, 0.045
    port = round_port(box_volume_m3=front, tuning_hz=35.0, diameter_m=0.08)
    r = simulate_bandpass(d, rear, front, port, 1.0)
    c = ref.driver_circuit(d)
    s = 1j * 2 * pi * F_GRID
    cf, cr = front / (ref.RHO * ref.C**2), rear / (ref.RHO * ref.C**2)
    mp = ref.RHO * port.effective_length_m / port.area_m2
    zfront = s * mp / (1 + s**2 * mp * cf)  # port mass in parallel with the front chamber compliance
    v = ref.cone_velocity(c, s, zfront + 1 / (s * cr))
    pressure = s * ref.RHO * (c.sd * v / (1 + s**2 * mp * cf)) / (2 * pi)  # U_port = U_cone / (1 + s^2 Mp Cf)
    return {"max_diff_db": _max_db_diff(r, ref.level_db(pressure, F_GRID, "max"))}


def _bandpass6_parallel_limit() -> dict[str, float]:
    d = demo_driver()
    port = round_port(box_volume_m3=0.045, tuning_hz=35.0, diameter_m=0.08)
    blocked = PortDesign("round", 1e-9, 0.1, 0.1, 50.0, diameter_m=1e-4)  # rear vent closed: sixth order degrades to fourth
    six = simulate_bandpass(d, 0.030, 0.045, port, 1.0, rear_port=blocked)
    four = simulate_bandpass(d, 0.030, 0.045, port, 1.0)
    return {"max_diff_db": float(np.max(np.abs(six.response_db - four.response_db)))}


def _bandpass6_series_limit() -> dict[str, float]:
    d = demo_driver()
    ext = round_port(box_volume_m3=0.045, tuning_hz=35.0, diameter_m=0.08)
    blocked = PortDesign("round", 1e-9, 0.1, 0.1, 30.0, diameter_m=1e-4)  # internal duct closed: rear chamber is a sealed box
    series = simulate_bandpass_series(d, 0.050, 0.045, ext, blocked, 1.0, port_q=1e9)
    four = simulate_bandpass(d, 0.050, 0.045, ext, 1.0)
    return {"max_diff_db": float(np.max(np.abs(series.response_db - four.response_db)))}


# --- isobaric ---------------------------------------------------------------------------------------------------

def _isobaric_equivalence(wiring: str) -> dict[str, float]:
    d = demo_driver()
    assert d.vas_m3 is not None and d.re_ohm is not None
    e = equivalent_driver(d, wiring)
    assert e.vas_m3 is not None and e.re_ohm is not None
    series = wiring == "series"
    # compound pair: cone mass x2, compliance /2 (so Fs is unchanged); series: Re x2, Bl x2; parallel: Re /2, Bl x1
    re_ratio, bl_ratio = (2.0, 2.0) if series else (0.5, 1.0)
    qes_ratio = (2.0 * re_ratio) / bl_ratio**2  # Qes ~ Ms Re / Bl^2 with Ms x2
    return {"vas_ratio": e.vas_m3 / d.vas_m3, "re_ratio": e.re_ohm / d.re_ohm / re_ratio,
            "fs_ratio": e.fs_hz / d.fs_hz, "qts_ratio": e.qts / d.qts, "qes_ratio_expected": qes_ratio}


# --- baffles ----------------------------------------------------------------------------------------------------

def _dipole_sine() -> dict[str, float]:
    d = demo_driver()
    path = 0.45
    dipole = simulate_baffle(d, "dipole", path, None, 1.0)
    wall = simulate_baffle(d, "infinite_baffle", path, None, 1.0)  # same driver loading, so only the wall factor differs
    f = dipole.frequencies_hz
    band = (f >= 20) & (f <= 400) & (np.abs(np.sin(pi * f * path / ref.C)) > 0.05)  # keep away from the null at c/D
    delta = dipole.response_db - wall.response_db
    expected = ref.dipole_relative_db(f, path)
    return {"max_diff_db": float(np.max(np.abs(delta[band] - expected[band])))}


def _infinite_baffle_limit() -> dict[str, float]:
    d = demo_driver()
    vb = 0.70
    r = simulate_baffle(d, "infinite_baffle", 0.4, vb, 1.0)
    c = ref.driver_circuit(d)
    s = 1j * 2 * pi * F_GRID
    v = ref.cone_velocity(c, s, 1 / (s * (vb / (ref.RHO * ref.C**2))))
    return {"max_diff_db": _max_db_diff(r, ref.level_db(s * ref.RHO * c.sd * v / (2 * pi), F_GRID, "median"))}


# --- ducts: transmission line and horn families -----------------------------------------------------------------

def _duct_uniform(closed: bool) -> dict[str, float]:
    area, length = 0.012, 0.9
    w = 2 * pi * F_GRID
    chain = duct_chain([(area, length, 0.0)], w)
    load = np.full_like(w, 1e30, dtype=complex) if closed else np.zeros_like(w, dtype=complex)
    zin, _ = terminated(chain, load)
    expected = ref.uniform_duct_input_impedance(area, length, F_GRID, closed)
    keep = np.abs(expected) < 50 * ref.RHO * ref.C / area  # skip the immediate neighbourhood of the poles
    return {"max_rel_error": float(np.max(np.abs(zin[keep] - expected[keep]) / np.abs(expected[keep])))}


def _exponential_horn() -> dict[str, float]:
    s0, length, steps = 0.004, 1.6, 400
    m = 4 * pi * 70.0 / ref.C  # flare constant for fc = 70 Hz: fc = c m / (4 pi)
    fc = ref.C * m / (4 * pi)
    dx = length / steps
    areas = [s0 * np.exp(m * (i + 0.5) * dx) for i in range(steps)]
    f = np.array([140.0, 210.0, 350.0])
    w = 2 * pi * f
    chain = duct_chain([(a, dx, 0.0) for a in areas], w)
    mouth = s0 * np.exp(m * length)
    load = ref.exponential_horn_throat_impedance(f, fc, mouth)  # the infinite horn continues behind the mouth
    zin, _ = terminated(chain, load)
    expected = ref.exponential_horn_throat_impedance(f, fc, s0)
    return {"max_rel_error": float(np.max(np.abs(zin - expected) / np.abs(expected)))}


def _line_recompute(solver_id: str) -> dict[str, float]:
    """The solver's electrical input impedance against an independent re-derivation on the real generated geometry."""
    from lautsprecher_konstruktion.enclosure.folded_line import (
        STUFFING_LOSS,
        mouth_equivalent_radius_m,
    )

    bundle = solve_family(solver_id)
    line, response = bundle.folded_line, bundle.vented_response
    assert line is not None and response is not None and response.impedance_ohm is not None
    sections = [(area, length, STUFFING_LOSS[stuffing]) for area, length, stuffing in line.segments()]
    f = response.frequencies_hz
    area = line.mouth_width_m * line.mouth_height_m
    load = None if line.family == "transmission_line_closed" else ref.unflanged_end_load(f, area, mouth_equivalent_radius_m(line))
    zin = ref.duct_input_impedance(sections, f, load)
    expected = ref.driver_input_impedance(ref.driver_circuit(bundle.project.driver), f, zin)
    return {"max_rel_error": float(np.max(np.abs(response.impedance_ohm - expected) / np.abs(expected)))}


def _front_horn_recompute() -> dict[str, float]:
    bundle = solve_family("horn_front")
    horn, response = bundle.front_horn, bundle.vented_response
    assert horn is not None and response is not None and response.impedance_ohm is not None
    f = response.frequencies_hz
    sections = [(area, length, 0.012) for area, length in horn.acoustic_segments()]
    zin = ref.duct_input_impedance(sections, f, ref.unflanged_end_load(f, horn.mouth_area_m2, sqrt(horn.mouth_area_m2 / pi)))
    s = 1j * 2 * pi * f
    cb = bundle.target_net_volume_m3 / (ref.RHO * ref.C**2)  # sealed air volume behind the cone
    expected = ref.driver_input_impedance(ref.driver_circuit(bundle.project.driver), f, np.asarray(zin + 1 / (s * cb), dtype=complex))
    return {"max_rel_error": float(np.max(np.abs(response.impedance_ohm - expected) / np.abs(expected)))}


def _finite_check(solver_id: str) -> dict[str, float]:
    """Behaviour of any solver through the real design pipeline: finite output, passive impedance, volume as asked."""
    bundle = solve_family(solver_id)
    r = bundle.vented_response or bundle.sealed_response
    out: dict[str, float] = {"response_finite": 1.0 if r is not None and bool(np.all(np.isfinite(r.response_db))) else 0.0}
    if r is not None and r.impedance_ohm is not None:
        out["impedance_passive"] = 1.0 if bool(np.all(np.isfinite(r.impedance_ohm)) and np.all(r.impedance_ohm.real > 0)) else 0.0
    return out


def _consistency_case(solver_id: str) -> ReferenceCase:
    expectations = [_exp("response_finite", 1.0, "", "abs", 0.0, "Konsistenzprüfung: Antwort endlich (kein NaN/Inf)")]
    return ReferenceCase(f"consistency.{solver_id}", solver_id, f"{solver_id}: Berechnung durch die Entwurfskette liefert endliche Werte",
                         CaseKind.CONSISTENCY, partial(_finite_check, solver_id), tuple(expectations))


# --- registry of cases ------------------------------------------------------------------------------------------

def _literature(case_id: str, solver: str, title: str, kind: CaseKind, compute: Callable[[], dict[str, float]],
                *exps: ReferenceExpectation, slow: bool = False) -> ReferenceCase:
    return ReferenceCase(case_id, solver, title, kind, compute, tuple(exps), slow)


SMALL72 = "Small (1972), Closed-Box Loudspeaker Systems, J. Audio Eng. Soc. 20"
SMALL73 = "Small (1973), Vented-Box Loudspeaker Systems, J. Audio Eng. Soc. 21"
THIELE71 = "Thiele (1971), Loudspeakers in Vented Boxes, J. Audio Eng. Soc. 19"
OLSON51 = "Olson (1951), Elements of Acoustical Engineering"


def build_cases() -> tuple[ReferenceCase, ...]:
    cases: list[ReferenceCase] = [
        _literature("sealed.f3_over_fc_table", "sealed", "Geschlossen: F3/Fc gegen veröffentlichte Tabelle", CaseKind.LITERATURE, _sealed_f3_table,
                    _exp("f3_over_fc_q0.5", 1.554, "", "abs", 0.002, f"{SMALL72}, Tabelle f3/f0 über Qtc", "Tabelle auf drei Stellen gerundet; F3 aus 400-Punkte-Gitter interpoliert (Fehler < 0,05 %)"),
                    _exp("f3_over_fc_q0.7071", 1.0, "", "abs", 0.002, f"{SMALL72}: Butterworth-Ausrichtung, F3 = Fc", "wie oben: Gitterauflösung und Interpolation"),
                    _exp("f3_over_fc_q1.0", 0.786, "", "abs", 0.002, f"{SMALL72}, Tabelle f3/f0 über Qtc", "wie oben: Tabelle auf drei Stellen, Gitterauflösung")),
        _literature("sealed.small_relations", "sealed", "Geschlossen: Fc und Qtc aus Boxvolumen", CaseKind.ANALYTIC, _sealed_relations,
                    _exp("qtc_from_box_volume", 0.7071, "", "rel", 1e-6, f"{SMALL72}: Qtc = Qts sqrt(1 + Vas/Vb)", "algebraische Identität"),
                    _exp("fc_from_box_volume", 1.0, "", "rel", 1e-9, f"{SMALL72}: Fc = Fs sqrt(1 + Vas/Vb)", "algebraische Identität")),
        _literature("bass_reflex.b4_alignment", "bass_reflex", "Bassreflex: maximal flache B4-Ausrichtung (Butterworth)", CaseKind.LITERATURE, _vented_b4,
                    _exp("f3_over_fs", 1.0, "", "abs", 0.01, f"{THIELE71}, {SMALL73}: B4 hat F3 = Fs; Parameter aus dem Butterworth-Polynom 4. Ordnung (Qts 0,383, Vas/Vb = 1,414, Fb = Fs)",
                         "verlustfrei gerechnet; ±1 % für Gitterauflösung und Interpolation"),
                    _exp("peak_db", 0.0, "dB", "abs", 0.05, f"{THIELE71}: maximal flach, kein Überschwingen", "Butterworth ist exakt flach; 0,05 dB Rechengenauigkeit")),
        _literature("bass_reflex.small_polynomial", "bass_reflex", "Bassreflex: Frequenzgang gegen Small-Gleichung (Polynom 4. Ordnung)", CaseKind.ANALYTIC, _vented_closed_form,
                    _exp("max_diff_db", 0.0, "dB", "abs", 0.01, f"{SMALL73}: G(s) = s^4 Ts^2 Tb^2 / (...)", "geschlossene Formel gegen numerische Lösung des Netzwerks; 0,01 dB Rundungsfehler")),
        _literature("bass_reflex.qb3_fit", "bass_reflex", "Bassreflex: QB3-Näherungsformeln nach Small", CaseKind.LITERATURE, _vented_qb3,
                    _exp("f3_hz", 0.26 * demo_driver().qts**-1.4 * 32.0, "Hz", "rel", 0.10, f"{SMALL73}: Vb = 15 Qts^2,87 Vas, Fb = 0,42 Qts^-0,96 Fs, F3 = 0,26 Qts^-1,4 Fs",
                         "Smalls Formeln sind Kurvenanpassungen der Tabellenwerte; die Veröffentlichung gibt Abweichungen bis etwa 10 % an")),
        _literature("bass_reflex.helmholtz_port", "bass_reflex", "Bassreflex: Port-Abstimmung nach Helmholtz", CaseKind.ANALYTIC, _port_tuning,
                    _exp("tuning_hz", 35.0, "Hz", "rel", 0.005, "Helmholtz-Resonator: Fb = c/(2 pi) sqrt(S/(L_eff Vb))", "Portlänge wird auf 0,1 mm gerundet")),
        _literature("aperiodic.leakage_q", "aperiodic", "Aperiodisch: Leckage-Q und Eckfrequenz des Vents", CaseKind.ANALYTIC, _aperiodic_leakage,
                    _exp("ql_ratio", 1.0, "", "rel", 1e-9, f"{SMALL73}: QL = wc Cab Rac", "algebraische Identität"),
                    _exp("qeff_ratio", 1.0, "", "rel", 1e-9, f"{SMALL73}: 1/Qeff = 1/Qtc + 1/QL", "algebraische Identität"),
                    _exp("corner_ratio", 1.0, "", "rel", 1e-9, f"{SMALL73}: f = 1/(2 pi Rac Cab)", "algebraische Identität")),
        _literature("aperiodic.closed_limit", "aperiodic", "Aperiodisch: ohne Leckage wird es ein geschlossenes Gehäuse", CaseKind.LIMIT, _aperiodic_closed_limit,
                    _exp("qeff_over_qtc_closed", 1.0, "", "rel", 1e-6, f"{SMALL72}: Grenzfall R_ac gegen unendlich", "1e12 Pa s/m^3 als praktisch unendlich")),
        _literature("aperiodic.response_closed_form", "aperiodic", "Aperiodisch: Frequenzgang gegen geschlossene Formel (Vent-Masse vernachlässigt)", CaseKind.ANALYTIC, _aperiodic_response,
                    _exp("max_diff_db", 0.0, "dB", "abs", 0.05, f"{SMALL73}: U_total = U_cone s Cab Rac/(1 + s Cab Rac)", "Vent-Masse im Solver nicht exakt null (1,2 kg/m^4): bis 0,05 dB")),
        _literature("passive_radiator.tuning_roundtrip", "passive_radiator", "Passivmembran: Abstimmung aus Masse, Nachgiebigkeit und Boxvolumen", CaseKind.ANALYTIC, _passive_radiator_tuning,
                    _exp("tuning_hz", 35.0, "Hz", "rel", 1e-6, "Olson (1951)/Small (1974): fb = 1/(2 pi sqrt(Map Ceq)), Ceq = Cab Cap/(Cab + Cap)", "algebraische Identität")),
        _literature("passive_radiator.response_closed_form", "passive_radiator", "Passivmembran: Frequenzgang gegen geschlossene Formel (Reihenzweig Rp, Mp, Cp)", CaseKind.ANALYTIC, _passive_radiator_response,
                    _exp("max_diff_db", 0.0, "dB", "abs", 0.01, "Olson (1951)/Small (1974): U_total = U_cone s Cab Zp/(1 + s Cab Zp)", "algebraische Vereinfachung des Netzwerks")),
        _literature("bandpass_4.closed_form", "bandpass_4", "Bandpass 4. Ordnung: Frequenzgang gegen geschlossene Formel", CaseKind.ANALYTIC, _bandpass4_closed_form,
                    _exp("max_diff_db", 0.0, "dB", "abs", 0.01, "Geddes (1989)/Small: P ~ s U_cone / (1 + s^2 Mp Cf), Rückkammer als Nachgiebigkeit", "algebraische Vereinfachung des Netzwerks")),
        _literature("bandpass_6_parallel.limit_blocked_vent", "bandpass_6_parallel", "Bandpass 6. Ordnung parallel: geschlossener Rückvent ergibt 4. Ordnung", CaseKind.LIMIT, _bandpass6_parallel_limit,
                    _exp("max_diff_db", 0.0, "dB", "abs", 0.01, "Grenzfall: Rückvent-Fläche gegen null", "rest-Leckfluss durch 1e-9 m^2")),
        _literature("bandpass_6_series.limit_blocked_duct", "bandpass_6_series", "Bandpass 6. Ordnung seriell: geschlossener Innenkanal ergibt 4. Ordnung", CaseKind.LIMIT, _bandpass6_series_limit,
                    _exp("max_diff_db", 0.0, "dB", "abs", 0.01, "Grenzfall: Innenkanal-Fläche gegen null, verlustfrei", "rest-Leckfluss durch 1e-9 m^2")),
        _literature("baffle.dipole_sine", "dipole", "Dipol: Pegel gegen Unendlich-Schallwand = |sin(kD/2)|", CaseKind.ANALYTIC, _dipole_sine,
                    _exp("max_diff_db", 0.0, "dB", "abs", 0.01, f"{OLSON51}: p ~ 1 - exp(-jkD)", "geschlossene Formel; 0,01 dB")),
        _literature("baffle.open_baffle_sine", "open_baffle", "Offene Schallwand: gleiche Dipolformel", CaseKind.ANALYTIC, _dipole_sine,
                    _exp("max_diff_db", 0.0, "dB", "abs", 0.01, f"{OLSON51}: p ~ 1 - exp(-jkD)", "geschlossene Formel; 0,01 dB")),
        _literature("baffle.infinite_closed_limit", "infinite_baffle", "Unendliche Schallwand: großer Rückraum wirkt wie geschlossene Box", CaseKind.LIMIT, _infinite_baffle_limit,
                    _exp("max_diff_db", 0.0, "dB", "abs", 0.01, f"{SMALL72}: Rückraum als reine Nachgiebigkeit", "algebraische Identität")),
        _literature("duct.uniform_open", "transmission_line_open", "Kanalkern: gleichförmiger Kanal, offenes Ende: Zin = j Zc tan(kL)", CaseKind.ANALYTIC, lambda: _duct_uniform(False),
                    _exp("max_rel_error", 0.0, "", "abs", 1e-9, "Olson (1951): ebene Welle im Rohr; Beranek (1954)", "verlustfreie geschlossene Formel; Rundungsfehler")),
        _literature("duct.uniform_closed", "transmission_line_closed", "Kanalkern: gleichförmiger Kanal, starres Ende: Zin = -j Zc cot(kL)", CaseKind.ANALYTIC, lambda: _duct_uniform(True),
                    _exp("max_rel_error", 0.0, "", "abs", 1e-9, "Olson (1951): ebene Welle im Rohr; Beranek (1954)", "verlustfreie geschlossene Formel; Rundungsfehler")),
        _literature("duct.exponential_horn", "horn_exponential", "Kanalkern: Exponentialhorn gegen Olson-Halsimpedanz", CaseKind.ANALYTIC, _exponential_horn,
                    _exp("max_rel_error", 0.0, "", "abs", 0.02, f"{OLSON51}: Z = (rho c/S0)(sqrt(1 - (fc/f)^2) + j fc/f)", "Treppenstufen-Näherung des Horns mit 400 Abschnitten: Fehler < 2 %")),
    ]
    line_families = ("transmission_line_closed", "transmission_line_open", "transmission_line_tapered", "tqwt", "labyrinth",
                     "horn_rear", "horn_folded", "horn_scoop", "horn_exponential", "horn_tractrix", "horn_conical", "horn_hyperbolic")
    for solver in line_families:
        cases.append(_literature(
            f"line.recompute.{solver}", solver, f"{solver}: Eingangsimpedanz gegen unabhängige Neuberechnung auf der erzeugten Geometrie", CaseKind.ANALYTIC,
            partial(_line_recompute, solver),
            _exp("max_rel_error", 0.0, "", "abs", 1e-9, "Olson (1951), Beranek (1954): Kettenmatrix ebener Wellen, Mundlast nach Levine/Schwinger (1948)",
                 "gleiche Gleichungen, unabhängig gerechnet (2x2-Matrizenprodukte); Rundungsfehler")))
    cases.append(_literature(
        "line.recompute.horn_front", "horn_front", "Frontlasthorn: Eingangsimpedanz gegen unabhängige Neuberechnung auf der erzeugten Geometrie", CaseKind.ANALYTIC, _front_horn_recompute,
        _exp("max_rel_error", 0.0, "", "abs", 1e-9, "Olson (1951): Horn als Kette von Abschnitten, Mundlast nach Levine/Schwinger (1948), geschlossenes Rückvolumen",
             "gleiche Gleichungen, unabhängig gerechnet; Rundungsfehler")))
    for wiring, solver in (("series", "isobaric_sealed"), ("parallel", "compound_push_pull"), ("series", "isobaric_vented")):
        qes_expected = (2.0 * (2.0 if wiring == "series" else 0.5)) / ((2.0 if wiring == "series" else 1.0) ** 2)
        cases.append(_literature(
            f"isobaric.equivalent_{wiring}.{solver}", solver, f"Isobarik ({wiring}): Ersatztreiber aus zwei gleichen Chassis", CaseKind.ANALYTIC,
            partial(_isobaric_equivalence, wiring),
            _exp("vas_ratio", 0.5, "", "rel", 1e-9, "Olson (1951)/Small: Zwei Chassis in Isobarik, Vas halbiert", "algebraische Identität"),
            _exp("re_ratio", 1.0, "", "rel", 1e-9, f"Olson: Re {'verdoppelt' if wiring == 'series' else 'halbiert'} bei {wiring}er Schaltung", "algebraische Identität"),
            _exp("fs_ratio", 1.0, "", "rel", 1e-9, "doppelte Masse, halbe Nachgiebigkeit: Fs unverändert", "algebraische Identität"),
            _exp("qts_ratio", 1.0, "", "rel", 1e-9, "Qes und Qms unverändert, damit Qts unverändert", "algebraische Identität"),
            _exp("qes_ratio_expected", 1.0, "", "rel", 1e-9, f"Qes ~ Ms Re / Bl^2 mit Ms x2 ({wiring}) bleibt gleich", f"erwartet intern {qes_expected:g} vor Normierung")))
    for entry in registry.supported():
        cases.append(_consistency_case(entry.solver_id or entry.id))
    return tuple(cases)
