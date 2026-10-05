from math import pi, sqrt

import numpy as np
import pytest

from lautsprecher_konstruktion.acoustics.baffle_step import (
    MAX_STEP_DB,
    baffle_step_db,
    baffle_step_frequency_hz,
)
from lautsprecher_konstruktion.crossover.passive import (
    baffle_step_compensation,
    second_order_butterworth_two_way,
)
from lautsprecher_konstruktion.crossover.simulation import simulate_crossover
from lautsprecher_konstruktion.export.bom import build_bom
from lautsprecher_konstruktion.project.demo import demo_project
from lautsprecher_konstruktion.services.design import calculate_project


def test_transition_frequency_follows_width_rule() -> None:
    assert baffle_step_frequency_hz(0.30) == pytest.approx(383.33, rel=1e-3)
    assert baffle_step_frequency_hz(0.60) == pytest.approx(baffle_step_frequency_hz(0.30) / 2)
    with pytest.raises(ValueError):
        baffle_step_frequency_hz(0.0)


def test_step_shape_is_six_db_with_half_step_at_transition() -> None:
    f = np.array([1.0, baffle_step_frequency_hz(0.34), 1e6])
    low, mid, high = baffle_step_db(f, 0.34)
    assert low == pytest.approx(-MAX_STEP_DB, abs=0.01)
    assert mid == pytest.approx(-MAX_STEP_DB / 2, abs=0.01)
    assert high == pytest.approx(0.0, abs=0.01)
    smaller = baffle_step_db(f, 0.34, 3.0)
    assert smaller[0] == pytest.approx(-3.0, abs=0.01) and smaller[1] == pytest.approx(-1.5, abs=0.02)
    assert np.all(np.diff(baffle_step_db(np.geomspace(20, 20000, 100), 0.34)) >= 0)
    with pytest.raises(ValueError):
        baffle_step_db(f, 0.34, 7.0)


def test_compensation_network_values() -> None:
    inductor, resistor = baffle_step_compensation(400.0, 8.0, 6.0206)
    assert resistor.value_si == pytest.approx(8.0, rel=1e-3)  # k = 2 -> Rs = R
    assert inductor.value_si == pytest.approx(8.0 / (2 * pi * 400.0 * sqrt(2)), rel=1e-3)
    with pytest.raises(ValueError):
        baffle_step_compensation(400.0, 8.0, 0.0)


def test_network_attenuates_the_woofer_by_the_step_above_the_transition() -> None:
    plain = second_order_butterworth_two_way(2500.0, 8.0, 8.0)
    inductor, resistor = baffle_step_compensation(340.0, 8.0, 6.0206)
    from dataclasses import replace
    compensated = replace(plain, components=plain.components + (inductor, resistor))
    f = np.array([30.0, 340.0, 1000.0])
    base = simulate_crossover(plain, 8.0, 8.0, frequencies_hz=f).woofer_voltage
    comp = simulate_crossover(compensated, 8.0, 8.0, frequencies_hz=f).woofer_voltage
    diff = 20 * np.log10(np.abs(comp) / np.abs(base))
    assert diff[0] == pytest.approx(0.0, abs=0.3)
    assert diff[1] == pytest.approx(-3.0, abs=0.6)
    assert diff[2] == pytest.approx(-5.5, abs=0.8)


def test_project_integration_adds_components_and_bom_lines() -> None:
    project = demo_project()
    base = calculate_project(project)
    assert not any(c.reference == "Lbs" for c in base.crossover.components)
    enabled = project.model_copy(update={"crossover": project.crossover.model_copy(
        update={"baffle_step_compensation_db": 4.0})})
    bundle = calculate_project(enabled)
    refs = {c.reference for c in bundle.crossover.components}
    assert {"Lbs", "Rbs"} <= refs
    assert any("Schallwandkorrektur" in note for note in bundle.crossover.notes)
    assert {"Lbs", "Rbs"} <= {item.reference for item in build_bom(bundle)}
    f = np.array([40.0, 2000.0])
    a = np.abs(base.crossover_response.woofer_voltage[[np.argmin(abs(base.crossover_response.frequencies_hz - x)) for x in f]])
    b = np.abs(bundle.crossover_response.woofer_voltage[[np.argmin(abs(bundle.crossover_response.frequencies_hz - x)) for x in f]])
    assert 20 * np.log10(b[0] / a[0]) > -1.0  # low frequencies stay put


def test_config_rejects_more_than_six_db() -> None:
    project = demo_project()
    with pytest.raises(ValueError):
        type(project.crossover)(baffle_step_compensation_db=7.0)
