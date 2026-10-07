"""Closed-form and re-derived reference calculations, written without calling the solvers under test.

Everything here uses only textbook relations (Small 1972/1973, Thiele 1971, Olson 1951, Beranek 1954) and plain
circuit algebra. If a solver and these functions disagree, one of them is wrong; the reference case decides which
by the cited relation, never by copying solver output.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import pi, sqrt

import numpy as np

from lautsprecher_konstruktion.arrays import ComplexArray as Cplx
from lautsprecher_konstruktion.arrays import FloatArray as Real
from lautsprecher_konstruktion.drivers.models import Driver

RHO = 1.204
C = 343.0


@dataclass(frozen=True)
class DriverCircuit:
    sd: float
    cs: float   # acoustic-side mechanical compliance referred to the cone [m/N]
    ms: float   # moving mass [kg]
    rms: float  # mechanical resistance [N s/m]
    bl: float
    re: float
    le: float


def driver_circuit(d: Driver) -> DriverCircuit:
    """Lumped T/S circuit of a driver with complete electrical data (Small 1972)."""
    assert d.vas_m3 is not None and d.sd_m2 is not None and d.re_ohm is not None and d.qes is not None
    sd = d.sd_m2
    cs = d.vas_m3 / (RHO * C**2 * sd**2)
    ws = 2 * pi * d.fs_hz
    ms = 1 / (ws**2 * cs)
    qms = d.qms if d.qms is not None else d.qes * d.qts / (d.qes - d.qts)
    return DriverCircuit(sd, cs, ms, ws * ms / qms, sqrt(ws * ms * d.re_ohm / d.qes), d.re_ohm, d.le_h or 0.0)


def cone_velocity(c: DriverCircuit, s: Cplx, acoustic_load: Cplx, volts: float = 1.0) -> Cplx:
    """Cone velocity for a voltage drive: v = Bl V / (Ze Zm + Bl^2) with Zm = Zms + Sd^2 Z_load."""
    zm = c.rms + s * c.ms + 1 / (s * c.cs) + c.sd**2 * acoustic_load
    ze = c.re + s * c.le
    return np.asarray(c.bl * volts / (ze * zm + c.bl**2), dtype=complex)


def level_db(pressure: Cplx, f: Real, how: str) -> Real:
    """Level relative to a reference chosen like the solver documents it: band median 150-300 Hz, or the maximum."""
    magnitude = np.maximum(np.abs(pressure), np.finfo(float).tiny)
    ref = float(np.median(magnitude[(f >= 150) & (f <= 300)])) if how == "median" else float(np.max(magnitude))
    return np.asarray(20 * np.log10(magnitude / ref), dtype=float)


# --- sealed box ------------------------------------------------------------------------------------------------

def sealed_f3_over_fc(q: float) -> float:
    """-3 dB point of a second-order high-pass: f3/fc = sqrt((x + sqrt(x^2 + 4)) / 2), x = 1/Q^2 - 2."""
    x = 1 / q**2 - 2
    return sqrt((x + sqrt(x * x + 4)) / 2)


def sealed_system(fs: float, qts: float, vas: float, vb: float) -> tuple[float, float]:
    """(fc, Qtc) of a closed box: both scale with sqrt(1 + Vas/Vb) (Small 1972)."""
    k = sqrt(1 + vas / vb)
    return fs * k, qts * k


# --- vented box ------------------------------------------------------------------------------------------------

def small_vented_db(fs: float, qts: float, vas: float, vb: float, fb: float, f: Real) -> Real:
    """Lossless vented-box response: Small (1973) fourth-order high-pass in the time constants Ts, Tb.

    Derived from the circuit (cone, box compliance Cab, port mass Mp): the denominator is
    s^4 Ts^2 Tb^2 + s^3 Ts Tb^2 / Qts + s^2 (Ts^2 + (1 + alpha) Tb^2) + s Ts / Qts + 1 with Ts^2 = Mas Cas,
    Tb^2 = Mp Cab, alpha = Cas / Cab = Vas / Vb. In Small's normalisation (T0^2 = Ts Tb, h = Fb/Fs) the s^2 term is
    h + (1 + alpha)/h.
    """
    ts, tb, alpha = 1 / (2 * pi * fs), 1 / (2 * pi * fb), vas / vb
    s = 1j * 2 * pi * f
    num = s**4 * ts**2 * tb**2
    den = s**4 * ts**2 * tb**2 + s**3 * ts * tb**2 / qts + s**2 * (ts**2 + (alpha + 1) * tb**2) + s * ts / qts + 1
    return level_db(np.asarray(num / den, dtype=complex), f, "median")


def butterworth_b4(fs: float) -> tuple[float, float, float]:
    """(Qts, Vas/Vb, Fb) of the maximally flat fourth-order alignment B4.

    Matching s^4 + (1/Q) s^3 + (alpha + 2) s^2 + (1/Q) s + 1 (h = 1) with the Butterworth polynomial
    s^4 + 2.6131 s^3 + 3.4142 s^2 + 2.6131 s + 1 gives Q = 1/2.6131 = 0.3827 and alpha = 1.4142.
    """
    return 1 / 2.6131259, sqrt(2.0), fs


def helmholtz_hz(area: float, effective_length: float, volume: float) -> float:
    return C / (2 * pi) * sqrt(area / (effective_length * volume))


# --- aperiodic -------------------------------------------------------------------------------------------------

def leakage_q(fc: float, qtc: float, vb: float, resistance: float) -> tuple[float, float, float]:
    """(QL, Qeff, leak corner) of a closed box with a resistive vent, vent mass neglected (Small 1973)."""
    cab = vb / (RHO * C**2)
    ql = 2 * pi * fc * cab * resistance
    return ql, 1 / (1 / qtc + 1 / ql), 1 / (2 * pi * resistance * cab)


# --- baffles ---------------------------------------------------------------------------------------------------

def dipole_relative_db(f: Real, path: float) -> Real:
    """Dipole on-axis level against the same piston in an infinite baffle: |sin(k D / 2)| (Olson 1951)."""
    k = 2 * pi * f / C
    return np.asarray(20 * np.log10(np.abs(np.sin(k * path / 2))), dtype=float)


# --- ducts -----------------------------------------------------------------------------------------------------

def uniform_duct_input_impedance(area: float, length: float, f: Real, closed_end: bool) -> Cplx:
    """Lossless uniform duct: open end Zin = j Zc tan(kL), rigid end Zin = -j Zc cot(kL), Zc = rho c / S."""
    zc = RHO * C / area
    kl = 2 * pi * f / C * length
    return np.asarray(1j * zc * np.tan(kl) if not closed_end else -1j * zc / np.tan(kl), dtype=complex)


def exponential_horn_throat_impedance(f: Real, fc: float, throat_area: float) -> Cplx:
    """Throat impedance of an infinite exponential horn: (rho c / S0) [sqrt(1 - (fc/f)^2) + j fc/f] for f > fc (Olson)."""
    zc = RHO * C / throat_area
    ratio = fc / f
    return np.asarray(zc * (np.sqrt(1 - ratio**2 + 0j) + 1j * ratio), dtype=complex)


def unflanged_end_load(f: Real, area: float, radius: float) -> Cplx:
    """Unflanged duct end, small ka (Levine and Schwinger 1948; Beranek 1954): rho c / S (0.25 ka^2 + 0.61 j ka)."""
    ka = 2 * pi * f / C * radius
    return np.asarray(RHO * C / area * (0.25 * ka**2 + 0.61j * ka), dtype=complex)


def duct_input_impedance(sections: list[tuple[float, float, float]], f: Real, load: Cplx | None) -> Cplx:
    """Input impedance of ducts in series via (N, 2, 2) matrix products; ``load`` None means a rigid closed end.

    ``sections`` are (area, length, attenuation factor) with gamma = (attenuation + j) w / c, driver end first.
    """
    w = 2 * pi * f
    total = np.broadcast_to(np.eye(2, dtype=complex), (f.size, 2, 2)).copy()
    for area, length, attenuation in sections:
        gamma = (attenuation + 1j) * w / C
        zc = RHO * C / area
        m = np.empty((f.size, 2, 2), dtype=complex)
        m[:, 0, 0] = np.cosh(gamma * length)
        m[:, 0, 1] = zc * np.sinh(gamma * length)
        m[:, 1, 0] = np.sinh(gamma * length) / zc
        m[:, 1, 1] = m[:, 0, 0]
        total = np.matmul(total, m)
    a, b, c, d = total[:, 0, 0], total[:, 0, 1], total[:, 1, 0], total[:, 1, 1]
    if load is None:
        return np.asarray(a / c, dtype=complex)
    return np.asarray((a * load + b) / (c * load + d), dtype=complex)


def driver_input_impedance(c: DriverCircuit, f: Real, acoustic_load: Cplx) -> Cplx:
    """Electrical input impedance Ze + Bl^2 / Zm with Zm = Zms + Sd^2 Z_load."""
    s = 1j * 2 * pi * f
    zm = c.rms + s * c.ms + 1 / (s * c.cs) + c.sd**2 * acoustic_load
    return np.asarray(c.re + s * c.le + c.bl**2 / zm, dtype=complex)
