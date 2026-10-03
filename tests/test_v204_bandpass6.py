from pathlib import Path

import numpy as np
import pytest

from lautsprecher_konstruktion.enclosure.registry import registry
from lautsprecher_konstruktion.export.bom import build_bom
from lautsprecher_konstruktion.export.package import export_project_package
from lautsprecher_konstruktion.project.demo import demo_project
from lautsprecher_konstruktion.project.models import CrossoverConfig
from lautsprecher_konstruktion.services.design import calculate_project


def _project(rear_tuning: float = 30.0):
    project = demo_project()
    return project.model_copy(update={
        "front_elements": (), "tweeter_name": "", "crossover": CrossoverConfig(enabled=False),
        "enclosure": project.enclosure.model_copy(update={
            "enclosure_type": "bandpass_6_parallel", "rear_volume_l": 50.0,
            "rear_tuning_hz": rear_tuning, "rear_port_diameter_mm": 75.0,
        }),
    })


def test_parallel_bandpass_two_ports_reach_manufacturing_package(tmp_path: Path) -> None:
    assert registry.get("bandpass_6_parallel").status == "SUPPORTED"
    bundle = calculate_project(_project())
    assert bundle.port is not None and bundle.rear_port is not None
    assert bundle.rear_chamber_volume_m3 == pytest.approx(0.05)
    assert {(e.id, e.surface) for e in bundle.front_elements if e.type == "port"} == {
        ("BR1", "front"), ("BR2", "back")}
    assert {item.reference for item in build_bom(bundle) if item.category == "Ports"} == {"BR1", "BR2"}
    response = bundle.vented_response
    assert response is not None
    assert response.f3_hz is not None and response.upper_f3_hz is not None
    assert np.all(np.isfinite(response.response_db))
    assert response.front_port_velocity_m_s is not None
    assert response.rear_port_velocity_m_s is not None
    package = export_project_package(bundle, tmp_path)
    assert (package / "zeichnungen/rueckwand.dxf").is_file()
    assert "BR2" in (package / "zeichnungen/schnitt.svg").read_text(encoding="utf-8")
    assert "BR2_m_s" in (package / "simulation/portgeschwindigkeit.csv").read_text(encoding="utf-8-sig")


def test_rear_tuning_changes_response_and_invalid_geometry_is_blocked(tmp_path: Path) -> None:
    low = calculate_project(_project(28.0))
    high = calculate_project(_project(38.0))
    assert low.vented_response is not None and high.vented_response is not None
    assert not np.allclose(low.vented_response.response_db, high.vented_response.response_db)
    oversized = _project().model_copy(update={"enclosure": _project().enclosure.model_copy(
        update={"rear_port_diameter_mm": 160.0})})
    bundle = calculate_project(oversized)
    assert any(issue.code == "REAR_PORT_BACK_WALL" for issue in bundle.issues)
    with pytest.raises(ValueError, match="Geometrie"):
        export_project_package(bundle, tmp_path)
