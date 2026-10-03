from pathlib import Path

import numpy as np
import pytest

from lautsprecher_konstruktion.enclosure.registry import registry
from lautsprecher_konstruktion.export.bom import build_bom
from lautsprecher_konstruktion.export.package import export_project_package
from lautsprecher_konstruktion.project.demo import demo_project
from lautsprecher_konstruktion.project.models import CrossoverConfig
from lautsprecher_konstruktion.services.design import calculate_project


def _project(internal_tuning_hz: float = 30.0):
    project = demo_project()
    return project.model_copy(update={
        "front_elements": (), "tweeter_name": "", "crossover": CrossoverConfig(enabled=False),
        "enclosure": project.enclosure.model_copy(update={
            "enclosure_type": "bandpass_6_series", "rear_volume_l": 50.0,
            "rear_tuning_hz": internal_tuning_hz, "rear_port_diameter_mm": 75.0,
        }),
    })


def test_series_bandpass_has_internal_and_external_ducts(tmp_path: Path) -> None:
    assert registry.get("bandpass_6_series").status == "SUPPORTED"
    bundle = calculate_project(_project())
    assert {(e.id, e.surface) for e in bundle.front_elements if e.type == "port"} == {
        ("BR1", "front"), ("BR2", "partition")}
    assert {item.reference for item in build_bom(bundle) if item.category == "Ports"} == {
        "BR1", "BR2"}
    response = bundle.vented_response
    assert response is not None
    assert response.f3_hz is not None and response.upper_f3_hz is not None
    assert response.f3_hz < response.upper_f3_hz
    assert np.all(np.isfinite(response.response_db))
    assert response.front_port_velocity_m_s is not None
    assert response.rear_port_velocity_m_s is not None
    package = export_project_package(bundle, tmp_path)
    assert "CUTOUT_PORT" in (package / "zeichnungen/trennwand.dxf").read_text(encoding="ascii")
    assert "BR2;partition" in (package / "zeichnungen/einbaukoordinaten.csv").read_text(encoding="utf-8-sig")
    assert "BR2" in (package / "zeichnungen/schnitt.svg").read_text(encoding="utf-8")
    assert "BR2_m_s" in (package / "simulation/portgeschwindigkeit.csv").read_text(encoding="utf-8-sig")


def test_internal_tuning_changes_transfer_and_long_duct_blocks_export(tmp_path: Path) -> None:
    a = calculate_project(_project(28.0))
    b = calculate_project(_project(38.0))
    assert a.vented_response is not None and b.vented_response is not None
    assert not np.allclose(a.vented_response.response_db, b.vented_response.response_db)
    project = _project()
    oversized = project.model_copy(update={"enclosure": project.enclosure.model_copy(
        update={"rear_port_diameter_mm": 160.0})})
    bundle = calculate_project(oversized)
    assert any(issue.code == "REAR_PORT_BACK_WALL" for issue in bundle.issues)
    with pytest.raises(ValueError, match="Geometrie"):
        export_project_package(bundle, tmp_path)


def test_compound_push_pull_exports_two_drivers_and_mounting_note(tmp_path: Path) -> None:
    assert registry.get("compound_push_pull").status == "SUPPORTED"
    project = demo_project()
    cfg = project.enclosure.model_copy(update={
        "enclosure_type": "compound_push_pull", "target_qtc": 0.5,
        "external_width_mm": 400.0, "external_height_mm": 450.0,
    })
    bundle = calculate_project(project.model_copy(update={
        "enclosure": cfg, "front_elements": (), "tweeter_name": "",
        "crossover": CrossoverConfig(enabled=False),
    }))
    assert bundle.coupler is not None
    assert not any(issue.severity == "error" for issue in bundle.issues)
    assert any(item.reference == "W1" and item.quantity == 2 for item in build_bom(bundle))
    assert any("gegensinnig polen" in item.notes for item in build_bom(bundle))
    package = export_project_package(bundle, tmp_path)
    assert (package / "zeichnungen/isobarik_montagering.dxf").is_file()


def test_aperiodic_vent_changes_response_and_is_documented(tmp_path: Path) -> None:
    assert registry.get("aperiodic").status == "SUPPORTED"
    base = demo_project()
    base = base.model_copy(update={
        "front_elements": (), "tweeter_name": "", "crossover": CrossoverConfig(enabled=False),
        "enclosure": base.enclosure.model_copy(update={
            "enclosure_type": "aperiodic", "target_volume_l": 45.0,
            "aperiodic_resistance_pa_s_m3": 8000.0,
        }),
    })
    first = calculate_project(base)
    second = calculate_project(base.model_copy(update={"enclosure": base.enclosure.model_copy(
        update={"aperiodic_resistance_pa_s_m3": 32000.0})}))
    assert first.port_resistance_pa_s_m3 == 8000.0
    assert first.port is not None and first.port.shape == "round"
    assert first.vented_response is not None and second.vented_response is not None
    assert not np.allclose(first.vented_response.response_db,
                           second.vented_response.response_db)
    assert not any(issue.severity == "error" for issue in first.issues)
    assert any(item.reference == "BR1" and item.category == "Aperiodischer Vent"
               for item in build_bom(first))
    package = export_project_package(first, tmp_path)
    assert "Sollwiderstand" in (package / "zeichnungen/gesamtzeichnung.svg").read_text(encoding="utf-8")
    assert "8000" in (package / "zeichnungen/schnitt.svg").read_text(encoding="utf-8")
