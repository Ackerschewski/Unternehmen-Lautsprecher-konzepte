"""Prototype comparison. The "measurements" below are synthetic and only exercise the logic."""
from dataclasses import replace

import numpy as np
import pytest

from lautsprecher_konstruktion.acoustics.vented import simulate_vented
from lautsprecher_konstruktion.crossover.measurements import FrequencyResponseData, ImpedanceData
from lautsprecher_konstruktion.project.demo import demo_project
from lautsprecher_konstruktion.project.models import CrossoverConfig
from lautsprecher_konstruktion.services.design import DesignBundle, calculate_project
from lautsprecher_konstruktion.validation import compare_prototype, render_report_markdown

F = tuple(float(x) for x in np.geomspace(10.0, 1000.0, 300))


def _bundle(kind: str = "bass_reflex") -> DesignBundle:
    project = demo_project()
    enclosure = project.enclosure.model_copy(update={"enclosure_type": kind})
    return calculate_project(project.model_copy(update={
        "enclosure": enclosure, "front_elements": (), "tweeter_name": "",
        "crossover": CrossoverConfig(enabled=False)}))


def _synthetic_measurement(bundle: DesignBundle, extra_length_m: float = 0.0,
                           level_offset_db: float = 0.0):
    port = bundle.port
    assert port is not None
    built = replace(port, physical_length_m=port.physical_length_m + extra_length_m,
                    effective_length_m=port.effective_length_m + extra_length_m)
    response = simulate_vented(bundle.project.driver, bundle.target_net_volume_m3, built,
                               bundle.project.enclosure.input_power_w, np.array(F))
    z = response.impedance_ohm
    frd = FrequencyResponseData(frequencies_hz=F, magnitude_db=tuple(response.response_db + level_offset_db),
                                source="synthetic")
    zma = ImpedanceData(frequencies_hz=F, magnitude_ohm=tuple(np.abs(z)),
                        phase_deg=tuple(np.degrees(np.angle(z))), source="synthetic")
    return frd, zma, built


def test_identical_data_is_rated_good_and_needs_no_correction() -> None:
    bundle = _bundle()
    frd, zma, _ = _synthetic_measurement(bundle)
    report = compare_prototype(bundle, frd=frd, zma=zma)
    assert report.verdict == "gut"
    assert report.frequency.rms_db < 0.2
    assert abs(report.impedance.delta_pct) < 1.0
    assert report.port_correction is None


def test_constant_level_offset_is_aligned_and_reported() -> None:
    bundle = _bundle()
    frd, _, _ = _synthetic_measurement(bundle, level_offset_db=6.0)
    report = compare_prototype(bundle, frd=frd)
    assert report.frequency.offset_db == pytest.approx(6.0, abs=0.05)
    assert report.frequency.rms_db < 0.05
    raw = compare_prototype(bundle, frd=frd, align_level=False)
    assert raw.frequency.rms_db == pytest.approx(6.0, abs=0.05)
    assert raw.verdict == "abweichend"


def test_too_long_port_is_detected_and_correction_round_trips() -> None:
    bundle = _bundle()
    assert bundle.port is not None
    frd, zma, _ = _synthetic_measurement(bundle, extra_length_m=0.020)
    report = compare_prototype(bundle, frd=frd, zma=zma)
    assert report.impedance.delta_pct < -2.0  # built tuning is below the simulation
    correction = report.port_correction
    assert correction is not None and correction.feasible
    assert correction.change_mm < 0  # shorten
    assert correction.method == "model"
    assert correction.change_mm == pytest.approx(-20.0, abs=1.0)
    # Apply the suggested length to the "built" port: the tuning deviation must vanish.
    fixed_extra = (correction.suggested_length_mm - correction.current_length_mm) / 1000.0
    _, zma_fixed, _ = _synthetic_measurement(bundle, extra_length_m=0.020 + fixed_extra)
    again = compare_prototype(bundle, zma=zma_fixed)
    assert abs(again.impedance.delta_pct) < 1.0


def test_too_short_port_suggests_lengthening() -> None:
    bundle = _bundle()
    _, zma, _ = _synthetic_measurement(bundle, extra_length_m=-0.015)
    report = compare_prototype(bundle, zma=zma)
    assert report.impedance.delta_pct > 2.0
    assert report.port_correction is not None and report.port_correction.change_mm > 0
    assert "verlängern" in " ".join(report.findings)


def test_large_deviation_gets_deviating_verdict() -> None:
    bundle = _bundle()
    _, zma, _ = _synthetic_measurement(bundle, extra_length_m=0.15)
    assert compare_prototype(bundle, zma=zma).verdict == "abweichend"


def test_sealed_enclosure_compares_resonance_peak() -> None:
    bundle = _bundle("sealed")
    assert bundle.sealed is not None
    fc = bundle.sealed.resonance_hz
    f = np.array(F)
    z = 6.0 + 40.0 / (1 + ((f - fc * 1.03) / (fc * 0.18)) ** 2)  # synthetic single peak 3 % above Fc
    zma = ImpedanceData(frequencies_hz=F, magnitude_ohm=tuple(z), phase_deg=tuple(0.0 for _ in F))
    report = compare_prototype(bundle, zma=zma)
    assert report.impedance.kind == "sealed"
    assert report.impedance.delta_pct == pytest.approx(3.0, abs=1.5)
    assert report.port_correction is None


def test_missing_double_peak_is_called_out() -> None:
    bundle = _bundle()
    zma = ImpedanceData(frequencies_hz=F, magnitude_ohm=tuple(6.0 + 0 * np.array(F)),
                        phase_deg=tuple(0.0 for _ in F))
    report = compare_prototype(bundle, zma=zma)
    assert report.impedance.meas_marker_hz is None
    assert any("nicht erkennbar" in item for item in report.findings)
    assert report.verdict == "nicht bewertbar"


def test_measurement_outside_band_is_rejected_with_reason() -> None:
    bundle = _bundle()
    frd = FrequencyResponseData(frequencies_hz=(1000.0, 5000.0, 10000.0), magnitude_db=(0.0, 0.0, 0.0))
    report = compare_prototype(bundle, frd=frd)
    assert report.frequency is None and report.verdict == "nicht bewertbar"
    assert any("überlappen" in item for item in report.findings)


def test_input_required_and_markdown_report() -> None:
    bundle = _bundle()
    with pytest.raises(ValueError):
        compare_prototype(bundle)
    frd, zma, _ = _synthetic_measurement(bundle, extra_length_m=0.01)
    text = render_report_markdown(compare_prototype(bundle, frd=frd, zma=zma))
    assert text.startswith("# Prototypvergleich") and "## Impedanz" in text and "## Frequenzgang" in text


def test_other_vented_types_use_the_scaling_estimate() -> None:
    bundle = _bundle("bandpass_4")
    response = bundle.vented_response
    assert response is not None and response.impedance_ohm is not None
    shifted = ImpedanceData(frequencies_hz=tuple(float(x) * 0.93 for x in response.frequencies_hz),
                            magnitude_ohm=tuple(np.abs(response.impedance_ohm)),
                            phase_deg=tuple(np.degrees(np.angle(response.impedance_ohm))))
    report = compare_prototype(bundle, zma=shifted)
    assert report.port_correction is not None
    assert report.port_correction.method == "scaling"
    assert report.port_correction.change_mm < 0
    assert "Näherung" in " ".join(report.findings)


def test_command_line_report(tmp_path) -> None:
    from lautsprecher_konstruktion.crossover.measurements import load_frd, load_zma  # noqa: F401
    from lautsprecher_konstruktion.validation.__main__ import main

    bundle = _bundle()
    frd, zma, _ = _synthetic_measurement(bundle, extra_length_m=0.01)
    project_file = tmp_path / "p.json"
    project_file.write_text(bundle.project.model_dump_json(), encoding="utf-8")
    frd_file, zma_file = tmp_path / "m.frd", tmp_path / "m.zma"
    frd_file.write_text("\n".join(f"{f} {m}" for f, m in zip(frd.frequencies_hz, frd.magnitude_db, strict=True)),
                        encoding="utf-8")
    zma_file.write_text("\n".join(f"{f} {m} {p}" for f, m, p in zip(
        zma.frequencies_hz, zma.magnitude_ohm, zma.phase_deg, strict=True)), encoding="utf-8")
    out = tmp_path / "report.md"
    code = main([str(project_file), "--frd", str(frd_file), "--zma", str(zma_file), "--out", str(out)])
    assert code == 0 and out.read_text(encoding="utf-8").startswith("# Prototypvergleich")
    assert main([str(project_file)]) == 2  # no measurement given
    assert main([str(tmp_path / "missing.json"), "--frd", str(frd_file)]) == 2
