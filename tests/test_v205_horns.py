from __future__ import annotations

import os

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from lautsprecher_konstruktion.drawings.front_horn_svg import render_front_horn_svg
from lautsprecher_konstruktion.drawings.tapped_horn_svg import render_tapped_horn_svg
from lautsprecher_konstruktion.enclosure.registry import registry
from lautsprecher_konstruktion.export.bom import build_bom
from lautsprecher_konstruktion.export.package import export_project_package
from lautsprecher_konstruktion.library.store import ComponentLibrary
from lautsprecher_konstruktion.project.demo import demo_project
from lautsprecher_konstruktion.project.models import CrossoverConfig
from lautsprecher_konstruktion.services.automatic import AutomaticDesignRequest, automatic_design
from lautsprecher_konstruktion.services.design import calculate_project
from lautsprecher_konstruktion.ui.main_window import MainWindow


def _horn_project(kind: str):
    base=demo_project()
    if kind=='horn_front':
        config=base.enclosure.model_copy(update={
            'enclosure_type':kind,'tuning_hz':150,'external_width_mm':450,
            'external_height_mm':750,'target_qtc':0.5,'brace_quantity':0})
    else:
        config=base.enclosure.model_copy(update={
            'enclosure_type':kind,'target_volume_l':200,'tuning_hz':60,
            'external_width_mm':450,'external_height_mm':1200,'brace_quantity':0})
    return base.model_copy(update={'enclosure':config,'front_elements':(),
                                   'tweeter_name':'','crossover':CrossoverConfig(enabled=False)})


def test_all_registered_enclosures_are_available():
    assert len(registry.all())==29
    assert all(entry.status=='SUPPORTED' for entry in registry.all())


def test_front_horn_changes_response_and_exports_its_patterns(tmp_path):
    project=_horn_project('horn_front')
    bundle=calculate_project(project)
    assert bundle.front_horn is not None
    assert not [issue for issue in bundle.issues if issue.severity=='error']
    assert bundle.vented_response is not None
    assert bundle.vented_response.f3_hz is not None
    assert np.isfinite(bundle.vented_response.response_db).all()
    assert 'Horn-Trapezplatten' in render_front_horn_svg(bundle)
    package=export_project_package(bundle,tmp_path)
    assert (package/'zeichnungen'/'horn_trapez_top_bottom.dxf').exists()
    assert (package/'zeichnungen'/'horn_trapez_sides.dxf').exists()
    assert (package/'fertigung'/'fertigungsunterlagen.pdf').stat().st_size>1000
    assert any('Trapez' in item.name for item in bundle.panels)


def test_front_horn_rejects_obstructed_front(tmp_path):
    project=_horn_project('horn_front')
    original=demo_project().front_elements
    bundle=calculate_project(project.model_copy(update={'front_elements':original}))
    assert any(issue.code=='FRONT_HORN_OBSTRUCTION' for issue in bundle.issues)
    with pytest.raises(ValueError,match='Geometrie'):
        export_project_package(bundle,tmp_path)


def test_tapped_horn_has_internal_driver_and_distinct_response(tmp_path):
    project=_horn_project('horn_tapped')
    bundle=calculate_project(project)
    horn=bundle.tapped_horn
    assert horn is not None
    assert not [issue for issue in bundle.issues if issue.severity=='error']
    assert len(bundle.front_elements)==1 and bundle.front_elements[0].id=='BR1'
    assert horn.baffle_length_m>(project.driver.outer_diameter_m or 0)
    assert horn.quarter_wave_hz==pytest.approx(63.6,rel=.03)
    assert bundle.vented_response is not None
    assert np.isfinite(bundle.vented_response.response_db).all()
    assert bundle.vented_response.f3_hz is not None
    assert 'F1 Draufsicht' in render_tapped_horn_svg(bundle)
    assert any(item.reference=='W1' for item in build_bom(bundle))
    package=export_project_package(bundle,tmp_path)
    assert (package/'zeichnungen'/'tapped_horn_f1.dxf').exists()
    assert 'CUTOUT_DRIVER' in (package/'zeichnungen'/'tapped_horn_f1.dxf').read_text(encoding='ascii')
    assert (package/'fertigung'/'fertigungsunterlagen.pdf').stat().st_size>1000


def test_tapped_horn_rejects_short_internal_panel():
    project=_horn_project('horn_tapped')
    config=project.enclosure.model_copy(update={'target_volume_l':65})
    with pytest.raises(ValueError,match='F1 zu kurz'):
        calculate_project(project.model_copy(update={'enclosure':config}))


@pytest.mark.parametrize('family,width,height',[
    ('horn_front',.65,.85),('horn_tapped',.55,1.5)])
def test_automatic_horn_selection_reaches_a_buildable_result(
        family: str,width: float,height: float,tmp_path) -> None:
    result=automatic_design(AutomaticDesignRequest(
        speaker_type='PA-Subwoofer',way_count=1,enclosure_preference=family,
        max_width_m=width,max_height_m=height,max_depth_m=.75,
        amplifier_power_w=1),ComponentLibrary(user_root=tmp_path/'library'))
    assert result.status=='ok'
    assert result.designs
    assert all(design.project.enclosure.enclosure_type==family for design in result.designs)


@pytest.mark.parametrize('family',['horn_front','horn_tapped'])
def test_expert_mode_switch_from_demo_makes_single_driver_horn(family: str) -> None:
    app=QApplication.instance() or QApplication([])
    window=MainWindow()
    window.enclosure_type.setCurrentIndex(window.enclosure_type.findData(family))
    window.calculate()
    app.processEvents()
    assert window._bundle is not None
    assert window._bundle.project.enclosure.enclosure_type==family
    assert not [issue for issue in window._bundle.issues if issue.severity=='error']
    assert window._bundle.project.tweeter_name==''
    assert not window._bundle.project.crossover.enabled
    window.close()
