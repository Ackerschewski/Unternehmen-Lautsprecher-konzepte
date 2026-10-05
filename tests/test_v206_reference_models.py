"""Cross-checks of the solvers against closed-form and literature results.

These tests use textbook relations (Small 1972/73, Thiele 1971) and network theory;
they do not replace validation against measurements of real prototypes.
"""
from math import pi, sqrt

import numpy as np
import pytest
from scipy.optimize import brentq

from lautsprecher_konstruktion.acoustics.response import (
    sealed_response_db,
    sealed_system_parameters,
)
from lautsprecher_konstruktion.acoustics.sealed import solve_sealed
from lautsprecher_konstruktion.acoustics.vented import simulate_vented
from lautsprecher_konstruktion.crossover.passive import (
    first_order_two_way,
    second_order_butterworth_two_way,
    second_order_linkwitz_riley_two_way,
)
from lautsprecher_konstruktion.crossover.simulation import simulate_crossover
from lautsprecher_konstruktion.crossover.standards import round_crossover_to_e12
from lautsprecher_konstruktion.enclosure.ports import round_port
from lautsprecher_konstruktion.project.demo import demo_driver

C = 343.0


def _db(x: np.ndarray) -> np.ndarray:
    return 20 * np.log10(np.abs(x))


# --- sealed box -----------------------------------------------------------

@pytest.mark.parametrize("qtc", [0.5, 0.707, 1.0, 1.2])
def test_sealed_system_follows_small_relations(qtc: float) -> None:
    driver = demo_driver()
    result = solve_sealed(driver, qtc)
    fc, q = sealed_system_parameters(driver, result.box_volume_m3)
    alpha = driver.vas_m3 / result.box_volume_m3
    assert q == pytest.approx(qtc, rel=1e-9)
    assert fc == pytest.approx(driver.fs_hz * sqrt(1 + alpha), rel=1e-9)
    assert fc == pytest.approx(driver.fs_hz * qtc / driver.qts, rel=1e-9)


@pytest.mark.parametrize("qtc,ratio", [(0.5, 1.554), (0.707, 1.0), (1.0, 0.786)])
def test_sealed_f3_over_fc_matches_second_order_highpass_tables(qtc: float, ratio: float) -> None:
    result = solve_sealed(demo_driver(), qtc)
    assert result.f3_hz / result.resonance_hz == pytest.approx(ratio, abs=0.002)


@pytest.mark.parametrize("qtc", [0.5, 0.707, 0.9, 1.1])
def test_sealed_f3_is_the_numerical_minus_3db_point(qtc: float) -> None:
    driver = demo_driver()
    result = solve_sealed(driver, qtc)
    # Level relative to the high-frequency asymptote, found independently by root finding.
    def level(f: float) -> float:
        return float(sealed_response_db(driver, result.box_volume_m3, np.array([f]))[0]) + 3.0103
    assert brentq(level, 5.0, 400.0) == pytest.approx(result.f3_hz, rel=2e-3)


def test_sealed_slopes_are_second_order_and_flat_at_high_frequency() -> None:
    driver = demo_driver()
    volume = solve_sealed(driver, 0.707).box_volume_m3
    f = np.array([1.0, 2.0, 2000.0, 4000.0])
    level = sealed_response_db(driver, volume, f)
    assert level[1] - level[0] == pytest.approx(12.04, abs=0.05)
    assert level[3] - level[2] == pytest.approx(0.0, abs=0.01)


# --- vented box -----------------------------------------------------------

def _qb3() -> tuple[float, float, float]:
    d = demo_driver()
    vb = 15.0 * d.qts**2.87 * d.vas_m3
    fb = 0.42 * d.qts**-0.96 * d.fs_hz
    f3 = 0.26 * d.qts**-1.4 * d.fs_hz
    return vb, fb, f3


def test_port_length_follows_helmholtz_relation() -> None:
    vb, fb, _ = _qb3()
    port = round_port(box_volume_m3=vb, tuning_hz=fb, diameter_m=0.08)
    expected = C**2 * port.area_m2 / ((2 * pi * fb) ** 2 * vb)
    assert port.effective_length_m == pytest.approx(expected, rel=0.01)  # c = 343 m/s in the port module
    assert port.effective_length_m - port.physical_length_m == pytest.approx(1.46 * 0.04, rel=1e-6)


def test_qb3_alignment_has_symmetric_peaks_minimum_at_fb_and_24db_slope() -> None:
    d = demo_driver()
    vb, fb, f3_literature = _qb3()
    port = round_port(box_volume_m3=vb, tuning_hz=fb, diameter_m=0.10)
    response = simulate_vented(d, vb, port, 1.0)
    f = response.frequencies_hz
    z = np.abs(response.impedance_ohm)
    peaks = [i for i in range(1, len(z) - 1) if z[i] > z[i - 1] and z[i] > z[i + 1]]
    assert len(peaks) == 2
    low, high = peaks
    minimum = low + int(np.argmin(z[low:high + 1]))
    assert f[minimum] == pytest.approx(fb, rel=0.03)  # impedance minimum marks the tuning
    assert z[low] == pytest.approx(z[high], rel=0.05)  # QB3 has equal impedance peaks
    i10, i20 = np.argmin(abs(f - 10)), np.argmin(abs(f - 20))
    assert response.response_db[i20] - response.response_db[i10] == pytest.approx(24.0, abs=2.0)
    # Thiele's QB3 fit is an approximation; require agreement within 10 %.
    assert response.f3_hz == pytest.approx(f3_literature, rel=0.10)


def test_vented_system_is_passive() -> None:
    d = demo_driver()
    vb, fb, _ = _qb3()
    response = simulate_vented(d, vb, round_port(box_volume_m3=vb, tuning_hz=fb, diameter_m=0.08), 1.0)
    assert np.all(response.impedance_ohm.real > 0)
    assert np.all(np.isfinite(response.response_db))


def test_vented_response_converges_to_sealed_when_port_is_very_stiff() -> None:
    """A very narrow, long port blocks the airflow and the box behaves like a sealed box."""
    d = demo_driver()
    vb = solve_sealed(d, 0.707).box_volume_m3
    from dataclasses import replace
    port = round_port(box_volume_m3=vb, tuning_hz=40.0, diameter_m=0.08)
    blocked = replace(port, area_m2=port.area_m2 * 1e-4)
    f = np.geomspace(10.0, 300.0, 200)
    vented = simulate_vented(d, vb, blocked, 1.0, f)
    sealed = sealed_response_db(d, vb, f)
    band = (f > 40) & (f < 150)
    delta = vented.response_db[band] - sealed[band]
    assert np.ptp(delta) < 1.0  # same shape up to a constant level offset


# --- crossover ------------------------------------------------------------

def _responses(design, impedance: float = 8.0):
    f = np.geomspace(50.0, 20000.0, 800)
    return f, simulate_crossover(design, impedance, impedance, frequencies_hz=f)


def _at(f: np.ndarray, values: np.ndarray, target: float) -> complex:
    return values[int(np.argmin(abs(f - target)))]


def test_butterworth_2_is_minus_3db_at_fc_and_power_complementary() -> None:
    f, r = _responses(second_order_butterworth_two_way(2500.0, 8.0, 8.0))
    assert _db(_at(f, r.woofer_voltage, 2500.0)) == pytest.approx(-3.01, abs=0.15)
    assert _db(_at(f, r.tweeter_voltage, 2500.0)) == pytest.approx(-3.01, abs=0.15)
    power = np.abs(r.woofer_voltage) ** 2 + np.abs(r.tweeter_voltage) ** 2
    assert np.allclose(power, 1.0, atol=1e-6)


def test_linkwitz_riley_2_is_minus_6db_at_fc_and_sums_flat_with_inverted_tweeter() -> None:
    f, r = _responses(second_order_linkwitz_riley_two_way(2500.0, 8.0, 8.0))
    assert _db(_at(f, r.woofer_voltage, 2500.0)) == pytest.approx(-6.02, abs=0.15)
    assert np.allclose(np.abs(r.woofer_voltage - r.tweeter_voltage), 1.0, atol=1e-6)


def test_first_order_is_minus_3db_at_fc_and_6db_per_octave() -> None:
    f, r = _responses(first_order_two_way(2500.0, 8.0, 8.0))
    assert _db(_at(f, r.woofer_voltage, 2500.0)) == pytest.approx(-3.01, abs=0.15)
    slope = _db(_at(f, r.woofer_voltage, 20000.0)) - _db(_at(f, r.woofer_voltage, 10000.0))
    assert slope == pytest.approx(-6.0, abs=0.4)


def test_second_order_slope_is_12db_per_octave() -> None:
    f, r = _responses(second_order_butterworth_two_way(1000.0, 8.0, 8.0))
    slope = _db(_at(f, r.woofer_voltage, 16000.0)) - _db(_at(f, r.woofer_voltage, 8000.0))
    assert slope == pytest.approx(-12.0, abs=0.5)


def test_e12_rounding_stays_within_one_series_step() -> None:
    design = second_order_butterworth_two_way(2500.0, 8.0, 8.0)
    rounded = round_crossover_to_e12(design)
    for before, after in zip(design.components, rounded.components, strict=True):
        assert after.value_si / before.value_si == pytest.approx(1.0, abs=0.11)
