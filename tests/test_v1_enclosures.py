from pathlib import Path

import numpy as np
import pytest

from lautsprecher_konstruktion.drawings.assembly_svg import render_assembly_svg
from lautsprecher_konstruktion.enclosure.passive_radiator import design_passive_radiator
from lautsprecher_konstruktion.export.bom import build_bom
from lautsprecher_konstruktion.export.package import export_project_package
from lautsprecher_konstruktion.project.demo import demo_project
from lautsprecher_konstruktion.services.design import calculate_project


def _variant(kind: str):
    project=demo_project()
    return project.model_copy(update={"enclosure":project.enclosure.model_copy(
        update={"enclosure_type":kind,"rear_volume_l":25.0})})


def test_passive_radiator_tuning_and_back_panel_export(tmp_path: Path) -> None:
    bundle=calculate_project(_variant("passive_radiator"))
    radiator=bundle.radiator
    assert radiator is not None
    assert radiator.added_mass_kg > 0
    assert bundle.port is None
    assert any(item.category=="Passivmembran" for item in build_bom(bundle))
    assert any(e.surface=="back" and e.type=="passive_radiator" for e in bundle.front_elements)
    response=bundle.vented_response
    assert response is not None and response.f3_hz is not None
    assert np.all(np.isfinite(response.response_db))
    package=export_project_package(bundle,tmp_path)
    assert (package/'zeichnungen/rueckwand.dxf').is_file()
    assert (package/'simulation/passivmembran.csv').is_file()
    assert 'Rückwand' in render_assembly_svg(bundle)


def test_bandpass_two_chambers_partition_and_passband(tmp_path: Path) -> None:
    bundle=calculate_project(_variant("bandpass_4"))
    assert bundle.front_chamber_volume_m3 == 0.045
    assert bundle.rear_chamber_volume_m3 == 0.025
    assert np.isclose(bundle.target_net_volume_m3,0.07)
    assert any(panel.name.startswith("Partition") for panel in bundle.panels)
    assert any(e.type=="woofer" and e.surface=="partition" for e in bundle.front_elements)
    response=bundle.vented_response
    assert response is not None
    assert response.f3_hz is not None and response.upper_f3_hz is not None
    assert response.upper_f3_hz > response.f3_hz
    assert response.response_db[0] < -10 and response.response_db[-1] < -10
    package=export_project_package(bundle,tmp_path)
    assert 'CUTOUT_DRIVER' in (package/'zeichnungen/trennwand.dxf').read_text(encoding='ascii')
    assert '\n40\n115.0\n' not in (package/'zeichnungen/frontplatte.dxf').read_text(encoding='ascii')
    svg=(package/'zeichnungen/schnitt.svg').read_text(encoding='utf-8')
    assert 'Rückkammer' in svg and 'Frontkammer' in svg


def test_invalid_radiator_mass_and_shallow_rear_chamber_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Grundmasse"):
        design_passive_radiator(box_volume_m3=.045,tuning_hz=35,area_m2=.035,
            stock_mass_kg=2,free_air_fs_hz=20,qms=5,
            cutout_diameter_m=.23,mounting_depth_m=.06,xmax_m=.012)
    project=_variant("bandpass_4")
    project=project.model_copy(update={"enclosure":project.enclosure.model_copy(
        update={"rear_volume_l":3.0})})
    bundle=calculate_project(project)
    assert any(issue.code=="CHAMBER_DEPTH" for issue in bundle.issues)
    with pytest.raises(ValueError,match="Geometrie"):
        export_project_package(bundle,tmp_path)


def test_slot_duct_walls_affect_volume_and_cut_list() -> None:
    project=demo_project()
    slot=project.model_copy(update={"enclosure":project.enclosure.model_copy(
        update={"port_type":"slot","slot_width_mm":200,"slot_height_mm":30})})
    round_bundle=calculate_project(project)
    slot_bundle=calculate_project(slot)
    assert any(panel.name=="Slotkanal Deckel/Boden" for panel in slot_bundle.panels)
    assert any(panel.name=="Slotkanal Seiten" for panel in slot_bundle.panels)
    assert slot_bundle.total_displacement_m3 > round_bundle.total_displacement_m3
