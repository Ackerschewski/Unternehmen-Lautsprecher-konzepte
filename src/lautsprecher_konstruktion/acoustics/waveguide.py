"""Plane-wave duct network shared by the folded-line, horn and front-horn solvers.

A duct section of area S and length L with the propagation constant gamma has the transfer matrix
[[cosh(gL), Zc sinh(gL)], [sinh(gL)/Zc, cosh(gL)]] with Zc = rho c / S. Sections are multiplied from the
driver end to the mouth. Everything is plane-wave: cross modes, curvature and fold losses are not modelled.
"""
from __future__ import annotations

from collections.abc import Iterable

import numpy as np

from lautsprecher_konstruktion.arrays import ComplexArray, FloatArray

RHO_AIR = 1.204
SPEED_OF_SOUND_M_S = 343.0


def radiation_load(frequencies_hz: FloatArray, mouth_area_m2: float, equivalent_radius_m: float) -> ComplexArray:
    """Radiation impedance of an unflanged duct end for small ka (Levine and Schwinger 1948): rho c / S (0.25 ka^2 + 0.61 j ka).

    The real part gives the radiated power, the imaginary part is the end correction of 0.61 a. Valid for ka << 1.
    """
    ka = 2 * np.pi * frequencies_hz * equivalent_radius_m / SPEED_OF_SOUND_M_S
    return np.asarray(RHO_AIR * SPEED_OF_SOUND_M_S / mouth_area_m2 * (0.25 * ka**2 + 0.61j * ka), dtype=complex)


def duct_chain(sections: Iterable[tuple[float, float, float]], omega: FloatArray) -> tuple[ComplexArray, ComplexArray, ComplexArray, ComplexArray]:
    """Chain matrix (A, B, C, D) of ``(area_m2, length_m, loss_per_metre_factor)`` sections, driver end first.

    The attenuation constant is ``loss * omega / c`` (so ``loss`` is dimensionless); gamma = (loss + j) omega / c.
    """
    a = np.ones_like(omega, dtype=complex)
    b = np.zeros_like(a)
    c = np.zeros_like(a)
    d = np.ones_like(a)
    for area, length, loss in sections:
        gamma = (loss + 1j) * omega / SPEED_OF_SOUND_M_S
        zc = RHO_AIR * SPEED_OF_SOUND_M_S / area
        ch, sh = np.cosh(gamma * length), np.sinh(gamma * length)
        aa, bb, cc, dd = ch, zc * sh, sh / zc, ch
        a, b, c, d = a * aa + b * cc, a * bb + b * dd, c * aa + d * cc, c * bb + d * dd
    return a, b, c, d


def terminated(chain: tuple[ComplexArray, ComplexArray, ComplexArray, ComplexArray], load: ComplexArray) -> tuple[ComplexArray, ComplexArray]:
    """(input impedance at the driver end, flow factor U_mouth / U_in) for the given mouth load."""
    a, b, c, d = chain
    return (a * load + b) / (c * load + d), 1 / (c * load + d)
