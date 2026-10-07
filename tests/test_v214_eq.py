"""Smooth target curve and real parametric EQ bands (reference responses, no overshoot)."""
from itertools import pairwise

import numpy as np
import pytest

from lautsprecher_konstruktion.targets.eq import (
    EQBand,
    FilterType,
    band_response_db,
    eq_response_db,
)
from lautsprecher_konstruktion.targets.smooth import (
    RENDER_POINTS,
    render_frequencies,
    smooth_curve_db,
    target_level_db,
)

F = render_frequencies()


def at(values: np.ndarray, f: float) -> float:
    return float(np.interp(np.log10(f), np.log10(F), values))


def test_render_grid_has_600_to_1200_points_on_a_log_axis() -> None:
    assert 600 <= len(F) == RENDER_POINTS <= 1200
    assert F[0] == pytest.approx(20.0) and F[-1] == pytest.approx(20000.0)
    assert np.allclose(np.diff(np.log10(F)), np.diff(np.log10(F))[0])


def test_pchip_hits_control_points_exactly_and_has_no_overshoot() -> None:
    points = [(20, 0.0), (80, 4.0), (250, 4.0), (1000, -3.0), (5000, -3.0), (20000, -6.0)]
    curve = smooth_curve_db(points, F)
    for f, level in points:
        assert at(curve, f) == pytest.approx(level, abs=0.05)
    for (f0, v0), (f1, v1) in pairwise(points):
        segment = curve[(F >= f0) & (F <= f1)]
        assert segment.min() >= min(v0, v1) - 1e-9 and segment.max() <= max(v0, v1) + 1e-9  # monotone per segment


def test_pchip_has_no_polygon_kinks() -> None:
    points = [(20, 0.0), (100, 6.0), (1000, 0.0), (20000, 0.0)]
    curve = smooth_curve_db(points, F)
    slope = np.diff(curve) / np.diff(np.log10(F))
    # a polyline would jump in slope at the control point; PCHIP changes continuously
    i = int(np.argmin(abs(F - 100)))
    assert abs(slope[i + 3] - slope[i - 3]) < 0.5 * (abs(slope[i - 20]) + abs(slope[i + 20]) + 1)
    assert np.max(np.abs(np.diff(slope))) < 60


def test_flat_curve_and_edge_hold() -> None:
    assert np.allclose(smooth_curve_db([], F), 0.0)
    held = smooth_curve_db([(100, 3.0), (1000, -2.0)], F)
    assert held[0] == pytest.approx(3.0) and held[-1] == pytest.approx(-2.0)
    assert np.allclose(smooth_curve_db([(500, 1.5)], F), 1.5)
    with pytest.raises(ValueError):
        smooth_curve_db([(0, 1.0), (10, 2.0)], F)


@pytest.mark.parametrize("gain", [-9.0, 3.5, 12.0])
def test_bell_reaches_its_gain_at_the_centre_and_returns_to_zero(gain: float) -> None:
    band = EQBand(filter_type=FilterType.BELL, frequency_hz=1000, gain_db=gain, q=1.2)
    r = band_response_db(band, F)
    assert at(r, 1000) == pytest.approx(gain, abs=0.1)
    assert abs(at(r, 30)) < 0.2 and abs(at(r, 19000)) < 0.4
    # -3 dB-style bandwidth: half the gain at the geometric band edges f0*(sqrt(1+1/(4Q^2)) +- 1/(2Q))
    q = 1.2
    low = 1000 * (np.sqrt(1 + 1 / (4 * q * q)) - 1 / (2 * q))
    high = 1000 * (np.sqrt(1 + 1 / (4 * q * q)) + 1 / (2 * q))
    assert at(r, low) == pytest.approx(gain / 2, abs=0.35) and at(r, high) == pytest.approx(gain / 2, abs=0.6)


def test_shelves_reach_full_gain_on_their_side_and_half_gain_at_the_corner() -> None:
    low = band_response_db(EQBand(filter_type=FilterType.LOW_SHELF, frequency_hz=200, gain_db=8, q=0.707), F)
    high = band_response_db(EQBand(filter_type=FilterType.HIGH_SHELF, frequency_hz=4000, gain_db=-6, q=0.707), F)
    assert at(low, 20) == pytest.approx(8.0, abs=0.3) and abs(at(low, 15000)) < 0.1
    assert at(low, 200) == pytest.approx(4.0, abs=0.3)
    assert at(high, 20000) == pytest.approx(-6.0, abs=1.2) and abs(at(high, 50)) < 0.05
    assert at(high, 4000) == pytest.approx(-3.0, abs=0.3)


def test_low_and_high_pass_have_minus_3db_corner_and_the_right_slope() -> None:
    lp = band_response_db(EQBand(filter_type=FilterType.LOW_PASS, frequency_hz=500, q=0.70710678), F)
    hp = band_response_db(EQBand(filter_type=FilterType.HIGH_PASS, frequency_hz=500, q=0.70710678), F)
    assert at(lp, 500) == pytest.approx(-3.01, abs=0.1) and at(hp, 500) == pytest.approx(-3.01, abs=0.1)
    assert at(lp, 30) == pytest.approx(0.0, abs=0.05) and at(hp, 19000) == pytest.approx(0.0, abs=0.3)
    assert at(lp, 1000) - at(lp, 2000) == pytest.approx(12.0, abs=1.2)  # 12 dB/oct
    assert at(hp, 125) - at(hp, 250) == pytest.approx(-12.0, abs=1.2)
    lp4 = band_response_db(EQBand(filter_type=FilterType.LOW_PASS, frequency_hz=500, order=4), F)
    assert at(lp4, 500) == pytest.approx(-3.01, abs=0.15)
    assert at(lp4, 1000) - at(lp4, 2000) == pytest.approx(24.0, abs=2.5)  # 24 dB/oct


def test_notch_is_deep_at_the_centre_and_flat_far_away() -> None:
    notch = band_response_db(EQBand(filter_type=FilterType.NOTCH, frequency_hz=2000, q=4), F)
    assert at(notch, 2000) < -25 and abs(at(notch, 100)) < 0.1 and abs(at(notch, 15000)) < 0.5


def test_combined_response_is_the_sum_in_db_and_disabled_bands_are_ignored() -> None:
    a = EQBand(id="a", filter_type=FilterType.BELL, frequency_hz=100, gain_db=4)
    b = EQBand(id="b", filter_type=FilterType.HIGH_SHELF, frequency_hz=5000, gain_db=-3)
    off = EQBand(id="c", enabled=False, filter_type=FilterType.BELL, frequency_hz=300, gain_db=12)
    total = eq_response_db([a, b, off], F)
    assert np.allclose(total, band_response_db(a, F) + band_response_db(b, F))
    assert np.allclose(band_response_db(off, F), 0.0)
    target = target_level_db([(20, 1.0), (20000, 1.0)], [a, b], F)
    assert np.allclose(target, 1.0 + total)


def test_band_limits_are_validated_and_gain_is_ignored_by_pass_filters() -> None:
    with pytest.raises(ValueError):
        EQBand(frequency_hz=5)
    with pytest.raises(ValueError):
        EQBand(gain_db=30)
    lp = EQBand(filter_type=FilterType.LOW_PASS, frequency_hz=500, gain_db=12)
    assert not lp.uses_gain
    assert np.allclose(band_response_db(lp, F),
                       band_response_db(EQBand(filter_type=FilterType.LOW_PASS, frequency_hz=500), F))
