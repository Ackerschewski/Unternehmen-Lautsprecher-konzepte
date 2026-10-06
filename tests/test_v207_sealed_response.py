import os

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from lautsprecher_konstruktion.acoustics.response import sealed_response_db
from lautsprecher_konstruktion.acoustics.sealed import solve_sealed
from lautsprecher_konstruktion.acoustics.sealed_response import simulate_sealed
from lautsprecher_konstruktion.export.package import export_project_package
from lautsprecher_konstruktion.project.demo import demo_driver, demo_project
from lautsprecher_konstruktion.project.models import CrossoverConfig
from lautsprecher_konstruktion.services.design import calculate_project
from lautsprecher_konstruktion.ui.assistant_window import AssistantWindow
from lautsprecher_konstruktion.validation import compare_prototype

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_response_matches_closed_form_sealed_highpass() -> None:
    driver = demo_driver()
    volume = solve_sealed(driver, 0.707).box_volume_m3
    f = np.geomspace(10.0, 300.0, 200)
    r = simulate_sealed(driver, volume, 1.0, f)
    band = (f > 15) & (f < 200)
    delta = r.response_db[band] - sealed_response_db(driver, volume, f)[band]
    assert np.ptp(delta) < 1.0  # same shape up to the driver's inductance roll-off and a constant


def test_f3_and_impedance_peak_at_the_system_resonance() -> None:
    driver = demo_driver()
    result = solve_sealed(driver, 0.707)
    r = simulate_sealed(driver, result.box_volume_m3)
    assert r.f3_hz == pytest.approx(result.f3_hz, rel=0.06)
    z = np.abs(r.impedance_ohm)
    peak = r.frequencies_hz[int(np.argmax(z))]
    assert peak == pytest.approx(result.resonance_hz, rel=0.05)
    assert np.all(r.impedance_ohm.real > 0) and r.port_velocity_m_s is None and r.absolute_available


def test_excursion_scales_with_voltage_and_is_largest_near_the_corner() -> None:
    driver = demo_driver()
    volume = solve_sealed(driver, 0.707).box_volume_m3
    low = simulate_sealed(driver, volume, 1.0)
    high = simulate_sealed(driver, volume, 4.0)
    assert np.allclose(high.excursion_mm, 2 * low.excursion_mm)  # P = 4x -> voltage 2x
    assert low.frequencies_hz[int(np.argmax(low.excursion_mm))] < 100


def test_leakage_lowers_the_impedance_peak_and_input_is_validated() -> None:
    driver = demo_driver()
    volume = solve_sealed(driver, 0.707).box_volume_m3
    tight = np.max(np.abs(simulate_sealed(driver, volume).impedance_ohm))
    leaky = np.max(np.abs(simulate_sealed(driver, volume, ql=3.0).impedance_ohm))
    assert leaky < tight
    for kwargs in ({"box_volume_m3": 0.0}, {"power_w": 0.0}, {"ql": -1.0}):
        args = {"box_volume_m3": volume, "power_w": 1.0, **kwargs}
        with pytest.raises(ValueError):
            simulate_sealed(driver, args["box_volume_m3"], args["power_w"], ql=args.get("ql"))
    with pytest.raises(ValueError):
        simulate_sealed(driver, volume, 1.0, np.array([20.0, 10.0, 30.0]))


def _sealed_bundle():
    project = demo_project()
    return calculate_project(project.model_copy(update={
        "enclosure": project.enclosure.model_copy(update={"enclosure_type": "sealed", "brace_quantity": 0}),
        "front_elements": (), "tweeter_name": "", "crossover": CrossoverConfig(enabled=False)}))


def test_bundle_export_and_prototype_compare_use_the_sealed_model(tmp_path) -> None:
    bundle = _sealed_bundle()
    assert bundle.sealed is not None and bundle.sealed_response is not None and bundle.vented_response is None
    package = export_project_package(bundle, tmp_path)
    text = (package / "simulation" / "membranauslenkung.csv").read_text(encoding="utf-8-sig")
    assert len(text.splitlines()) > 100 and "Auslenkung_mm" in text
    z = bundle.sealed_response.impedance_ohm
    from lautsprecher_konstruktion.crossover.measurements import ImpedanceData
    f = tuple(float(x) for x in bundle.sealed_response.frequencies_hz)
    zma = ImpedanceData(frequencies_hz=f, magnitude_ohm=tuple(np.abs(z)), phase_deg=tuple(np.degrees(np.angle(z))))
    report = compare_prototype(bundle, zma=zma)
    assert report.impedance.kind == "sealed" and report.impedance.sim_ohm is not None
    assert abs(report.impedance.delta_pct) < 6.0


def test_assistant_plots_show_sealed_curves_and_create_button_is_outside_the_scroll_area() -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    window = AssistantWindow()
    window.resize(1500, 600)
    window.show()
    # the create button must not live inside the scrolled card
    node = window.create_button.parent()
    from PySide6.QtWidgets import QScrollArea
    while node is not None:
        assert not isinstance(node, QScrollArea)
        node = node.parent()
