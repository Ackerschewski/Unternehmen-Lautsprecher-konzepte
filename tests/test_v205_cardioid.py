from pathlib import Path

import numpy as np

from lautsprecher_konstruktion.enclosure.registry import registry
from lautsprecher_konstruktion.export.bom import build_bom
from lautsprecher_konstruktion.export.package import export_project_package
from lautsprecher_konstruktion.project.demo import demo_project
from lautsprecher_konstruktion.project.models import CrossoverConfig
from lautsprecher_konstruktion.services.design import calculate_project


def _cardioid(delay_ms: float):
    project=demo_project()
    return project.model_copy(update={
        "enclosure":project.enclosure.model_copy(update={
            "enclosure_type":"cardioid","target_volume_l":45.0,
            "aperiodic_resistance_pa_s_m3":15000.0,
            "cardioid_delay_ms":delay_ms,
        }),
        "front_elements":(),"tweeter_name":"",
        "crossover":CrossoverConfig(enabled=False),
    })


def test_cardioid_has_rear_resistive_vent_and_polar_response(tmp_path: Path) -> None:
    assert registry.get("cardioid").status=="SUPPORTED"
    bundle=calculate_project(_cardioid(0.5))
    assert bundle.port_resistance_pa_s_m3==15000.0
    assert [(e.id,e.surface) for e in bundle.front_elements if e.type=="port"]==[("BR1","back")]
    response=bundle.vented_response
    assert response is not None
    assert response.rear_response_db is not None
    assert response.front_to_back_db is not None
    assert np.all(np.isfinite(response.front_to_back_db))
    assert np.max(abs(response.front_to_back_db))>1.0
    assert not any(issue.severity=="error" for issue in bundle.issues)
    assert any(item.reference=="BR1" and item.category=="Kardioid-Rückvent"
               for item in build_bom(bundle))
    package=export_project_package(bundle,tmp_path)
    assert "CUTOUT_PORT" in (package/"zeichnungen/rueckwand.dxf").read_text(encoding="ascii")
    assert "BR1;back" in (package/"zeichnungen/einbaukoordinaten.csv").read_text(
        encoding="utf-8-sig")


def test_cardioid_delay_changes_front_and_rear_response() -> None:
    first=calculate_project(_cardioid(0.2)).vented_response
    second=calculate_project(_cardioid(1.2)).vented_response
    assert first is not None and second is not None
    assert first.rear_response_db is not None and second.rear_response_db is not None
    assert not np.allclose(first.rear_response_db,second.rear_response_db)
    assert not np.allclose(first.response_db,second.response_db)
