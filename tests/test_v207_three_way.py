import os

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from lautsprecher_konstruktion.crossover.measurements import FrequencyResponseData
from lautsprecher_konstruktion.crossover.passive import second_order_butterworth_two_way
from lautsprecher_konstruktion.crossover.simulation import simulate_crossover
from lautsprecher_konstruktion.crossover.three_way import simulate_three_way, three_way_network
from lautsprecher_konstruktion.drawings.crossover_svg import render_crossover_svg
from lautsprecher_konstruktion.export.bom import build_bom
from lautsprecher_konstruktion.export.package import export_project_package
from lautsprecher_konstruktion.project.demo import demo_project
from lautsprecher_konstruktion.project.models import CrossoverConfig
from lautsprecher_konstruktion.services.design import calculate_project
from lautsprecher_konstruktion.ui.main_window import MainWindow

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
F = np.geomspace(20.0, 20000.0, 1200)


def _db(x: np.ndarray) -> np.ndarray:
    return 20 * np.log10(np.abs(x))


def _at(values: np.ndarray, hz: float) -> complex:
    return values[int(np.argmin(abs(F - hz)))]


def test_woofer_and_tweeter_branches_match_their_two_way_counterparts() -> None:
    """With a far-apart midrange band the outer branches behave like the 2-way sections."""
    three = three_way_network(300.0, 5000.0, 8.0, 8.0, 8.0, "butterworth_2")
    response = simulate_three_way(three, 8.0, 8.0, 8.0, frequencies_hz=F)
    two = second_order_butterworth_two_way(300.0, 8.0, 8.0)
    reference = simulate_crossover(two, 8.0, 8.0, frequencies_hz=F)
    assert np.allclose(response.woofer_voltage, reference.woofer_voltage, atol=1e-9)
    upper = simulate_crossover(second_order_butterworth_two_way(5000.0, 8.0, 8.0), 8.0, 8.0, frequencies_hz=F)
    assert np.allclose(response.tweeter_voltage, upper.tweeter_voltage, atol=1e-9)


def test_crossover_points_and_asymptotes_of_the_bands() -> None:
    design = three_way_network(500.0, 4000.0, 8.0, 8.0, 8.0, "butterworth_2")
    r = simulate_three_way(design, 8.0, 8.0, 8.0, frequencies_hz=F)
    assert _db(_at(r.woofer_voltage, 500.0)) == pytest.approx(-3.0, abs=0.4)
    assert _db(_at(r.tweeter_voltage, 4000.0)) == pytest.approx(-3.0, abs=0.4)
    assert _db(_at(r.midrange_voltage, 1500.0)) > -3.0  # inside the pass band
    assert _db(_at(r.midrange_voltage, 30.0)) < -30 and _db(_at(r.midrange_voltage, 19000.0)) < -20
    assert _db(_at(r.woofer_voltage, 30.0)) == pytest.approx(0.0, abs=0.5)
    assert _db(_at(r.tweeter_voltage, 19000.0)) == pytest.approx(0.0, abs=0.5)


def test_first_order_three_way_component_count_and_values() -> None:
    design = three_way_network(400.0, 3000.0, 8.0, 6.0, 4.0, "first_order")
    assert [c.reference for c in design.components] == ["L1", "C2", "L3", "C4"]
    values = {c.reference: c.value_si for c in design.components}
    assert values["L1"] == pytest.approx(8.0 / (2 * np.pi * 400.0))
    assert values["C4"] == pytest.approx(1 / (2 * np.pi * 3000.0 * 4.0))
    assert design.slope_db_oct == 6 and design.ways == 3


def test_pads_zobel_and_baffle_step_are_ordered_and_effective() -> None:
    plain = three_way_network(500.0, 4000.0, 8.0, 8.0, 8.0, "linkwitz_riley_2")
    full = three_way_network(500.0, 4000.0, 8.0, 8.0, 8.0, "linkwitz_riley_2", woofer_re_le=(5.8, 0.0011),
                             baffle_step=(350.0, 6.0), mid_attenuation_db=3.0, tweeter_attenuation_db=6.0)
    refs = {c.reference for c in full.components}
    assert {"Lbs", "Rbs", "Rz", "Cz", "Rpad-M-S", "Rpad-M-P", "Rpad-T-S", "Rpad-T-P"} <= refs
    a = simulate_three_way(plain, 8.0, 8.0, 8.0, frequencies_hz=F)
    b = simulate_three_way(full, 8.0, 8.0, 8.0, frequencies_hz=F)
    assert _db(_at(b.tweeter_voltage, 15000.0)) - _db(_at(a.tweeter_voltage, 15000.0)) == pytest.approx(-6.0, abs=0.7)
    assert _db(_at(b.midrange_voltage, 1500.0)) - _db(_at(a.midrange_voltage, 1500.0)) == pytest.approx(-3.0, abs=0.7)
    assert _db(_at(b.woofer_voltage, 40.0)) - _db(_at(a.woofer_voltage, 40.0)) == pytest.approx(0.0, abs=0.4)


def test_total_impedance_is_passive_and_single_branch_at_the_extremes() -> None:
    r = simulate_three_way(three_way_network(500.0, 4000.0, 8.0, 8.0, 8.0), 8.0, 8.0, 8.0, frequencies_hz=F)
    assert np.all(r.total_impedance.real > 0)
    assert abs(_at(r.total_impedance, 25.0)) == pytest.approx(8.0, abs=1.0)  # only the woofer branch conducts
    assert abs(_at(r.total_impedance, 19000.0)) == pytest.approx(8.0, abs=1.0)  # only the tweeter branch


def test_power_conservation_of_lossless_network() -> None:
    """A lossless network cannot deliver more power to the loads than it receives."""
    design = three_way_network(500.0, 4000.0, 8.0, 8.0, 8.0, "butterworth_2")
    r = simulate_three_way(design, 8.0, 8.0, 8.0, frequencies_hz=F)
    delivered = (np.abs(r.woofer_voltage) ** 2 + np.abs(r.midrange_voltage) ** 2 + np.abs(r.tweeter_voltage) ** 2) / 8.0
    received = (1.0 / r.total_impedance).real
    assert np.allclose(delivered, received, rtol=1e-6)


def test_acoustic_sum_needs_all_three_frd() -> None:
    design = three_way_network(500.0, 4000.0, 8.0, 8.0, 8.0)
    frd = FrequencyResponseData(frequencies_hz=(10.0, 30000.0), magnitude_db=(0.0, 0.0), phase_deg=(0.0, 0.0))
    partial = simulate_three_way(design, 8.0, 8.0, 8.0, woofer_frd=frd, tweeter_frd=frd, frequencies_hz=F)
    assert partial.sum_acoustic_db is None
    full = simulate_three_way(design, 8.0, 8.0, 8.0, woofer_frd=frd, mid_frd=frd, tweeter_frd=frd, frequencies_hz=F)
    assert full.sum_acoustic_db is not None and full.phase_complete and full.midrange_acoustic_db is not None


def test_invalid_inputs_are_rejected() -> None:
    with pytest.raises(ValueError):
        three_way_network(500.0, 600.0, 8.0, 8.0, 8.0)
    with pytest.raises(ValueError):
        three_way_network(500.0, 4000.0, 0.0, 8.0, 8.0)
    with pytest.raises(ValueError):
        three_way_network(500.0, 4000.0, 8.0, 8.0, 8.0, "nope")
    with pytest.raises(ValueError):
        CrossoverConfig(ways=3)
    with pytest.raises(ValueError):
        CrossoverConfig(ways=3, crossover_hz=1000.0, upper_crossover_hz=1200.0)
    with pytest.raises(ValueError):
        simulate_three_way(second_order_butterworth_two_way(1000.0, 8.0, 8.0), 8.0, 8.0, 8.0)


def _three_way_project(**extra):
    project = demo_project()
    crossover = CrossoverConfig(ways=3, crossover_hz=450.0, upper_crossover_hz=3500.0, topology="linkwitz_riley_2",
                                add_woofer_zobel=True, baffle_step_compensation_db=3.0, mid_attenuation_db=2.0,
                                tweeter_attenuation_db=3.0, **extra)
    return project.model_copy(update={"crossover": crossover})


def test_project_integration_bom_schematic_and_export(tmp_path) -> None:
    bundle = calculate_project(_three_way_project())
    assert bundle.crossover.ways == 3 and bundle.crossover_response.midrange_voltage is not None
    items = build_bom(bundle)
    assert any(item.reference == "M1" for item in items)
    assert {"L3", "C3", "Lbs", "Rz", "Rpad-M-S"} <= {item.reference for item in items}
    svg = render_crossover_svg(bundle.crossover)
    assert "Mitteltöner / Bandpass" in svg and "450 Hz / 3500 Hz" in svg
    package = export_project_package(bundle, tmp_path)
    assert "Mitteltöner / Bandpass" in (package / "frequenzweiche" / "schema.svg").read_text(encoding="utf-8")
    assert "Rpad-M-P" in (package / "frequenzweiche" / "stueckliste.csv").read_text(encoding="utf-8-sig")


def test_e12_rounding_keeps_three_way_structure() -> None:
    bundle = calculate_project(_three_way_project(round_to_standard_values=True))
    assert bundle.crossover.ways == 3 and bundle.crossover.upper_crossover_hz == 3500.0
    assert all(c.target_value_si is not None for c in bundle.crossover.components
               if c.kind in {"inductor", "capacitor", "resistor"})


def test_expert_window_three_way_round_trip() -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    window = MainWindow()
    window._apply_project(_three_way_project())
    assert window.crossover_ways.currentData() == 3 and window.upper_frequency.value() == 3500.0
    project = window._project_from_form()
    assert project.crossover.ways == 3 and project.crossover.upper_crossover_hz == 3500.0
    window.calculate()
    assert window._bundle is not None and window._bundle.crossover.ways == 3
    assert any(line.get_label() == "Mitteltöner elektrisch" for ax in window.crossover_figure.axes
               for line in ax.get_lines())
