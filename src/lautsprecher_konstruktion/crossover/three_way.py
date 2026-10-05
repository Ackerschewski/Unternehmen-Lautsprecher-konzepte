"""Passive three-way network: woofer low-pass, midrange band-pass, tweeter high-pass.

The component values are electrical starting values for nominal resistive loads. The
simulation then solves every branch as an exact ladder against the complex driver load
(measured ZMA if available), so the interaction of the midrange high- and low-pass is
visible. Acoustic offsets between drivers, baffle step and driver roll-off are not
compensated; final values need measurements.
"""
from __future__ import annotations

from dataclasses import replace
from math import pi, sqrt

import numpy as np

from lautsprecher_konstruktion.arrays import ComplexArray, FloatArray
from lautsprecher_konstruktion.crossover.measurements import FrequencyResponseData, ImpedanceData
from lautsprecher_konstruktion.crossover.passive import (
    CrossoverDesign,
    PassiveComponent,
    baffle_step_compensation,
    l_pad,
    zobel_from_re_le,
)
from lautsprecher_konstruktion.crossover.simulation import (
    CrossoverResponse,
    _acoustic,
    _load,
    _parallel,
)

Q_BY_TOPOLOGY = {"butterworth_2": 1.0 / sqrt(2.0), "linkwitz_riley_2": 0.5}
NAMES = {"first_order": "Butterworth 1st order", "butterworth_2": "Butterworth 2nd order",
         "linkwitz_riley_2": "Linkwitz-Riley 2nd order approximation"}


def _inductor(ref: str, henry: float, connection: str, branch: str) -> PassiveComponent:
    return PassiveComponent(ref, "inductor", henry, "H", connection, branch)


def _capacitor(ref: str, farad: float, connection: str, branch: str) -> PassiveComponent:
    return PassiveComponent(ref, "capacitor", farad, "F", connection, branch)


def _pad(prefix: str, load_ohm: float, attenuation_db: float, family: str) -> list[PassiveComponent]:
    series, shunt = l_pad(load_ohm, attenuation_db)
    return [replace(series, reference=f"Rpad-{prefix}-S", branch=f"{family} attenuation"),
            replace(shunt, reference=f"Rpad-{prefix}-P", branch=f"{family} attenuation")]


def three_way_network(
    lower_hz: float, upper_hz: float, woofer_ohm: float, mid_ohm: float, tweeter_ohm: float,
    topology: str = "butterworth_2", *, woofer_re_le: tuple[float, float] | None = None,
    baffle_step: tuple[float, float] | None = None, mid_attenuation_db: float = 0.0,
    tweeter_attenuation_db: float = 0.0,
) -> CrossoverDesign:
    """Components in source-to-load order per branch.

    baffle_step is (transition Hz, step dB) for the woofer; woofer_re_le adds a Zobel.
    """
    if min(lower_hz, upper_hz, woofer_ohm, mid_ohm, tweeter_ohm) <= 0:
        raise ValueError("frequencies and impedances must be positive")
    if upper_hz < 1.5 * lower_hz:
        raise ValueError("upper crossover must be at least 1.5 times the lower crossover")
    if topology not in NAMES:
        raise ValueError(f"unknown topology: {topology}")
    w1, w2 = 2.0 * pi * lower_hz, 2.0 * pi * upper_hz
    parts: list[PassiveComponent] = []
    if topology == "first_order":
        parts += [_inductor("L1", woofer_ohm / w1, "series", "woofer low-pass")]
        parts += [_capacitor("C2", 1.0 / (w1 * mid_ohm), "series", "midrange high-pass"),
                  _inductor("L3", mid_ohm / w2, "series", "midrange low-pass")]
        parts += [_capacitor("C4", 1.0 / (w2 * tweeter_ohm), "series", "tweeter high-pass")]
        slope = 6
    else:
        q = Q_BY_TOPOLOGY[topology]
        parts += [_inductor("L1", woofer_ohm / (q * w1), "series", "woofer low-pass"),
                  _capacitor("C1", q / (w1 * woofer_ohm), "shunt", "woofer low-pass")]
        parts += [_capacitor("C2", q / (w1 * mid_ohm), "series", "midrange high-pass"),
                  _inductor("L2", mid_ohm / (q * w1), "shunt", "midrange high-pass"),
                  _inductor("L3", mid_ohm / (q * w2), "series", "midrange low-pass"),
                  _capacitor("C3", q / (w2 * mid_ohm), "shunt", "midrange low-pass")]
        parts += [_capacitor("C4", q / (w2 * tweeter_ohm), "series", "tweeter high-pass"),
                  _inductor("L4", tweeter_ohm / (q * w2), "shunt", "tweeter high-pass")]
        slope = 12
    notes = [("Elektrischer Startentwurf für nominale resistive Lasten; die Mittel-Bandpass-Abschnitte beeinflussen sich, "
              "die Simulation löst jeden Zweig exakt gegen die komplexe Last."),
             "Schallzentren, Laufzeitunterschiede, Treiberpegel und Polung am Prototyp messen."]
    if baffle_step is not None:
        inductor, resistor = baffle_step_compensation(baffle_step[0], woofer_ohm, baffle_step[1])
        parts += [replace(inductor, branch="woofer baffle step"), replace(resistor, branch="woofer baffle step")]
        notes.append(f"Schallwandkorrektur {baffle_step[1]:.1f} dB um {baffle_step[0]:.0f} Hz (Näherung).")
    if woofer_re_le is not None:
        resistor, capacitor = zobel_from_re_le(*woofer_re_le)
        parts += [replace(resistor, branch="woofer zobel"), replace(capacitor, branch="woofer zobel")]
        notes.append("Woofer-Zobel aus Re/Le als Startwert.")
    if mid_attenuation_db > 0:
        parts += _pad("M", mid_ohm, mid_attenuation_db, "midrange")
        notes.append(f"Mitteltöner-L-Pad {mid_attenuation_db:.1f} dB.")
    if tweeter_attenuation_db > 0:
        parts += _pad("T", tweeter_ohm, tweeter_attenuation_db, "tweeter")
        notes.append(f"Hochtöner-L-Pad {tweeter_attenuation_db:.1f} dB.")
    return CrossoverDesign(NAMES[topology] + " (3-Wege)", lower_hz, slope, tuple(parts), tuple(notes),
                           ways=3, upper_crossover_hz=upper_hz)


# ---------------------------------------------------------------------------
# simulation: exact ladder per branch
# ---------------------------------------------------------------------------

def _elements(design: CrossoverDesign, family: str,
              s: ComplexArray) -> list[tuple[str, ComplexArray | complex]]:
    """Ordered (kind, impedance) elements of one branch; kind is 'series' or 'shunt'."""
    parts = [c for c in design.components if c.branch.split()[0] == family]
    by_ref = {c.reference: c for c in parts}
    elements: list[tuple[str, ComplexArray | complex]] = []
    done: set[str] = set()
    for c in parts:
        if c.reference in done:
            continue
        ref = c.reference
        if ref in {"Lbs", "Rbs"}:
            elements.append(("series", _parallel(complex(by_ref["Rbs"].value_si), s * by_ref["Lbs"].value_si)))
            done |= {"Lbs", "Rbs"}
        elif ref in {"Rz", "Cz"}:
            elements.append(("shunt", by_ref["Rz"].value_si + 1.0 / (s * by_ref["Cz"].value_si)))
            done |= {"Rz", "Cz"}
        elif ref.startswith("Rpad-"):
            elements.append(("series" if ref.endswith("-S") else "shunt", complex(c.value_si)))
            done.add(ref)
        elif c.kind == "inductor":
            elements.append((c.connection, s * c.value_si))
        elif c.kind == "capacitor":
            elements.append((c.connection, 1.0 / (s * c.value_si)))
        else:
            raise ValueError(f"unsupported component {ref}")
    return elements


def _ladder(elements: list[tuple[str, ComplexArray | complex]],
            load: ComplexArray) -> tuple[ComplexArray, ComplexArray]:
    """Voltage transfer to the load and input impedance, walking from the load to the source."""
    z_down = load
    transfer = np.ones_like(load)
    for kind, z in reversed(elements):
        if kind == "shunt":
            z_down = _parallel(z_down, z)
        else:
            transfer = transfer * z_down / (z + z_down)
            z_down = z + z_down
    return transfer, z_down


def simulate_three_way(
    design: CrossoverDesign, woofer_ohm: float, mid_ohm: float, tweeter_ohm: float,
    woofer_zma: ImpedanceData | None = None, mid_zma: ImpedanceData | None = None,
    tweeter_zma: ImpedanceData | None = None, woofer_frd: FrequencyResponseData | None = None,
    mid_frd: FrequencyResponseData | None = None, tweeter_frd: FrequencyResponseData | None = None,
    frequencies_hz: FloatArray | None = None,
) -> CrossoverResponse:
    if design.ways != 3:
        raise ValueError("simulate_three_way needs a three-way design")
    if min(woofer_ohm, mid_ohm, tweeter_ohm) <= 0:
        raise ValueError("nominal impedances must be positive")
    f = np.geomspace(20.0, 20_000.0, 500) if frequencies_hz is None else np.asarray(frequencies_hz, dtype=float)
    if f.ndim != 1 or np.any(f <= 0) or np.any(np.diff(f) <= 0):
        raise ValueError("frequencies must increase strictly")
    s = 2j * pi * f
    results = {}
    for family, nominal, zma in (("woofer", woofer_ohm, woofer_zma), ("midrange", mid_ohm, mid_zma),
                                 ("tweeter", tweeter_ohm, tweeter_zma)):
        results[family] = _ladder(_elements(design, family, s), _load(zma, nominal, f))
    total = _parallel(results["woofer"][1], results["midrange"][1], results["tweeter"][1])
    voltages = {name: results[name][0] for name in results}
    sum_db = woofer_db = mid_db = tweeter_db = None
    phase_complete = False
    if woofer_frd is not None and mid_frd is not None and tweeter_frd is not None:
        terms = [voltages["woofer"] * _acoustic(woofer_frd, f), voltages["midrange"] * _acoustic(mid_frd, f),
                 voltages["tweeter"] * _acoustic(tweeter_frd, f)]
        phase_complete = all(d.phase_deg is not None for d in (woofer_frd, mid_frd, tweeter_frd))
        woofer_db, mid_db, tweeter_db = (20 * np.log10(np.maximum(np.abs(t), 1e-15)) for t in terms)
        total_field = sum(terms) if phase_complete else sum(np.abs(t) for t in terms)
        sum_db = 20 * np.log10(np.maximum(np.abs(total_field), 1e-15))
    return CrossoverResponse(f, voltages["woofer"], voltages["tweeter"], total, woofer_db, tweeter_db, sum_db,
                             phase_complete, any(z is not None for z in (woofer_zma, mid_zma, tweeter_zma)),
                             midrange_voltage=voltages["midrange"], midrange_acoustic_db=mid_db)
