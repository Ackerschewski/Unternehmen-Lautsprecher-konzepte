from pathlib import Path

import numpy as np
import pytest

from lautsprecher_konstruktion.enclosure.registry import registry
from lautsprecher_konstruktion.export.bom import build_bom
from lautsprecher_konstruktion.export.package import export_project_package
from lautsprecher_konstruktion.project.demo import demo_project
from lautsprecher_konstruktion.project.models import CrossoverConfig
from lautsprecher_konstruktion.services.design import calculate_project


@pytest.mark.parametrize("family", ["infinite_baffle","open_baffle","dipole"])
def test_baffle_modes_use_plate_drawing_and_no_box_cutlist(family: str,
                                                             tmp_path: Path) -> None:
    assert registry.get(family).status == "SUPPORTED"
    project=demo_project()
    cfg=project.enclosure.model_copy(update={
        "enclosure_type":family,"target_volume_l":1000.0,
        "baffle_wing_depth_mm":150.0,"brace_quantity":0,
    })
    bundle=calculate_project(project.model_copy(update={
        "enclosure":cfg,"front_elements":(),"tweeter_name":"",
        "crossover":CrossoverConfig(enabled=False),
    }))
    assert bundle.baffle_mode==family
    assert bundle.vented_response is not None
    assert np.all(np.isfinite(bundle.vented_response.response_db))
    assert not any(issue.severity=="error" for issue in bundle.issues)
    assert {panel.name for panel in bundle.panels} == (
        {"Schallwand","H-Frame Seitenflügel"} if family=="dipole" else {"Schallwand"})
    assert not any(panel.name=="Back" for panel in bundle.panels)
    assert all(item.unit_price_eur is not None for item in build_bom(bundle)
               if item.category != "Treiber")
    package=export_project_package(bundle,tmp_path)
    sheet=(package/"zeichnungen/gesamtzeichnung.svg").read_text(encoding="utf-8")
    assert "Schallwand-Fertigungsblatt" in sheet
    assert "Wirksamer Umweg" in sheet or "wirksamer Umweg" in sheet
    assert (package/"fertigung/fertigungsunterlagen.pdf").stat().st_size>1000
    summary=(package/"projektzusammenfassung.txt").read_text(encoding="utf-8")
    assert "Schallwand:" in summary and "Außen:" not in summary


def test_dipole_wings_change_low_frequency_response_and_infinite_requires_room() -> None:
    project=demo_project()
    cfg=project.enclosure.model_copy(update={"enclosure_type":"dipole",
                                      "baffle_wing_depth_mm":100.0})
    first=calculate_project(project.model_copy(update={"enclosure":cfg,
                                                 "front_elements":()}))
    second=calculate_project(project.model_copy(update={"enclosure":cfg.model_copy(
        update={"baffle_wing_depth_mm":300.0}),"front_elements":()}))
    assert first.vented_response is not None and second.vented_response is not None
    assert not np.allclose(first.vented_response.response_db,
                           second.vented_response.response_db)
    invalid=cfg.model_copy(update={"enclosure_type":"infinite_baffle",
                                   "target_volume_l":100.0})
    with pytest.raises(ValueError,match="10 × Vas"):
        calculate_project(project.model_copy(update={"enclosure":invalid}))
