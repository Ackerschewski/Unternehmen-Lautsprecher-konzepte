from __future__ import annotations

import json
from math import pi, sqrt
from pathlib import Path

import numpy as np
import pytest

from lautsprecher_konstruktion.acoustics.alignment import suggest_alignments
from lautsprecher_konstruktion.acoustics.vented import simulate_vented
from lautsprecher_konstruktion.crossover.measurements import (
    load_frd,
    load_zma,
    parse_frd,
    parse_zma,
)
from lautsprecher_konstruktion.crossover.passive import first_order_two_way
from lautsprecher_konstruktion.crossover.simulation import simulate_crossover
from lautsprecher_konstruktion.enclosure.layout import FrontElement, bolt_holes, check_layout
from lautsprecher_konstruktion.enclosure.ports import round_port, slot_port
from lautsprecher_konstruktion.enclosure.rectangular import (
    calculate_net_volume,
    cut_list,
    solve_depth_for_net_volume,
)
from lautsprecher_konstruktion.export.bom import build_bom
from lautsprecher_konstruktion.export.package import export_project_package
from lautsprecher_konstruktion.project.demo import demo_driver, demo_project
from lautsprecher_konstruktion.project.models import SpeakerProject
from lautsprecher_konstruktion.services.design import calculate_project


def test_vented_numerical_reference_and_power_scaling() -> None:
    # Lumped electromechanical/acoustic impedances from docs/MAINTENANCE.md.
    driver=demo_driver()
    port=round_port(box_volume_m3=.045,tuning_hz=35,diameter_m=.08)
    low=simulate_vented(driver,.045,port,10)
    high=simulate_vented(driver,.045,port,100)
    assert low.f3_hz == pytest.approx(32.318,rel=.005)
    assert np.max(low.port_velocity_m_s) == pytest.approx(7.848,rel=.005)
    assert np.max(low.excursion_mm) == pytest.approx(5.470,rel=.005)
    assert np.max(high.port_velocity_m_s)/np.max(low.port_velocity_m_s) == pytest.approx(sqrt(10),rel=1e-6)
    assert np.max(high.excursion_mm)/np.max(low.excursion_mm) == pytest.approx(sqrt(10),rel=1e-6)
    assert np.max(low.group_delay_ms) == pytest.approx(21.84,rel=.02)
    assert np.allclose(low.port_mach,low.port_velocity_m_s/343)


def test_vented_missing_parameters_do_not_invent_absolute_values() -> None:
    d=demo_driver().model_copy(update={'re_ohm':None,'qes':None,'sd_m2':None})
    port=round_port(box_volume_m3=.045,tuning_hz=35,diameter_m=.08)
    r=simulate_vented(d,.045,port)
    assert r.f3_hz is not None
    assert r.excursion_mm is None and r.port_velocity_m_s is None and r.spl_db_1m is None


def test_slot_port_and_alignment_options() -> None:
    slot=slot_port(box_volume_m3=.045,tuning_hz=35,width_m=.2,height_m=.03)
    assert slot.area_m2 == pytest.approx(.006)
    assert slot.physical_length_m > 0
    options=suggest_alignments(demo_driver(),input_power_w=10)
    assert [o.name for o in options] == ['Kompakt','Ausgewogen','Tiefbass']
    assert options[0].volume_l < options[1].volume_l < options[2].volume_l
    assert all(o.port.physical_length_m > 0 for o in options)


def test_frd_zma_parsers_and_rejection() -> None:
    frd=parse_frd('# device: synthetic\nfrequency magnitude phase\n100 0 -10\n200 -3 -20 # note\n',source='test')
    assert frd.frequencies_hz == (100,200)
    assert frd.phase_deg == (-10,-20)
    assert frd.metadata['device'] == 'synthetic'
    zma=parse_zma('* test\n100\t8\t30\n200 9 40\n')
    assert zma.magnitude_ohm == (8,9)
    with pytest.raises(ValueError):
        parse_zma('100 8\n200 9\n')
    with pytest.raises(ValueError):
        parse_frd('100 0\n100 -3\n')
    root=Path(__file__).parents[1]
    assert len(load_frd(root/'data'/'demo_woofer_frd.frd').frequencies_hz) == 80
    assert len(load_zma(root/'data'/'demo_woofer_zma.zma').frequencies_hz) == 80


def test_crossover_nominal_and_measured_load() -> None:
    fc=1000.0
    design=first_order_two_way(fc,8,8)
    ideal=simulate_crossover(design,8,8,frequencies_hz=np.array([500.,1000.,2000.]))
    assert abs(ideal.woofer_voltage[1]) == pytest.approx(1/sqrt(2),rel=1e-6)
    assert abs(ideal.tweeter_voltage[1]) == pytest.approx(1/sqrt(2),rel=1e-6)
    from lautsprecher_konstruktion.crossover.measurements import ImpedanceData
    measured=ImpedanceData(frequencies_hz=(500,1000,2000),magnitude_ohm=(4,4,4),phase_deg=(0,0,0))
    real=simulate_crossover(design,8,8,woofer_zma=measured,frequencies_hz=np.array([500.,1000.,2000.]))
    expected=4/sqrt(4**2+(2*pi*fc*design.components[0].value_si)**2)
    assert abs(real.woofer_voltage[1]) == pytest.approx(expected,rel=1e-6)
    assert real.measured_impedance_used


def test_front_layout_collision_and_bolts() -> None:
    a=FrontElement(id='W1',type='woofer',x_m=.15,y_m=.15,outer_diameter_m=.10,
                   bolt_circle_diameter_m=.08,bolt_count=4,hole_diameter_m=.004,clearance_m=0)
    b=FrontElement(id='T1',type='tweeter',x_m=.23,y_m=.15,outer_diameter_m=.08,clearance_m=0)
    warnings=check_layout((a,b),.4,.4,.3)
    collision=next(w for w in warnings if w.code=='FRONT_COLLISION')
    assert collision.value == pytest.approx(10.0)
    holes=bolt_holes(a)
    assert len(holes)==4
    assert holes[0] == pytest.approx((.19,.15,.002))
    assert holes[1] == pytest.approx((.15,.19,.002))


def test_double_front_and_variable_panel_thickness_preserve_net_volume() -> None:
    cab=solve_depth_for_net_volume(external_width_m=.35,external_height_m=.6,
        panel_thickness_m=.018,front_thickness_m=.021,front_layers=2,
        back_thickness_m=.024,top_thickness_m=.015,bottom_thickness_m=.021,
        target_net_volume_m3=.045,displacement_m3=.003)
    assert calculate_net_volume(cab,.003)==pytest.approx(.045,rel=1e-9)
    assert cab.internal_height_m==pytest.approx(.564)
    panels=cut_list(cab)
    front=next(p for p in panels if p.name=='Front')
    assert front.quantity==2 and front.thickness_m==pytest.approx(.021)
    assert sum(p.quantity for p in panels)==7


def test_demo_export_and_v1_project_migration(tmp_path: Path) -> None:
    project=demo_project()
    bundle=calculate_project(project)
    package=export_project_package(bundle,tmp_path)
    for relative in ('project.json','fertigung/fertigungsunterlagen.pdf',
        'fertigung/zuschnittliste.csv','fertigung/stueckliste.csv',
        'zeichnungen/gesamtzeichnung.svg','zeichnungen/frontplatte.svg',
        'zeichnungen/frontplatte.dxf','zeichnungen/schnitt.svg',
        'frequenzweiche/schema.svg','frequenzweiche/stueckliste.csv',
        'simulation/frequenzgang.csv','simulation/membranauslenkung.csv',
        'simulation/portgeschwindigkeit.csv','simulation/gruppenlaufzeit.csv',
        'messdaten/importierte_messdaten.json'):
        assert (package/relative).is_file(),relative
    assert 'DRILL' in (package/'zeichnungen/frontplatte.dxf').read_text(encoding='ascii')
    assert 'CUTOUT_DRIVER' in (package/'zeichnungen/frontplatte.dxf').read_text(encoding='ascii')
    assert sum(i.quantity for i in build_bom(bundle) if i.category=='Schrauben') == 12
    saved=json.loads((package/'project.json').read_text(encoding='utf-8'))
    assert saved['schema_version']==3
    old={key:value for key,value in saved.items() if key not in {'schema_version','front_elements'}}
    migrated=SpeakerProject.model_validate(old)
    assert migrated.schema_version==3
    assert calculate_project(migrated).port is not None


def test_invalid_layout_blocks_manufacturing(tmp_path: Path) -> None:
    p=demo_project()
    bad=p.model_copy(update={'front_elements':(FrontElement(id='W1',type='woofer',x_m=.01,y_m=.01,outer_diameter_m=.26),)})
    bundle=calculate_project(bad)
    assert any(i.code=='FRONT_EDGE' for i in bundle.issues)
    with pytest.raises(ValueError,match='Geometrie'):
        export_project_package(bundle,tmp_path)
