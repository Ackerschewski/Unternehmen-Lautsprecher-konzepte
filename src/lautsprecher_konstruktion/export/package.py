from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from lautsprecher_konstruktion.acoustics.response import sealed_response_db
from lautsprecher_konstruktion.drawings.assembly_svg import render_assembly_svg
from lautsprecher_konstruktion.drawings.crossover_svg import render_crossover_svg
from lautsprecher_konstruktion.drawings.dimension_svg import dimension_rows, render_dimension_svg
from lautsprecher_konstruktion.drawings.front_dxf import (
    render_coupler_ring_dxf,
    render_front_panel_dxf,
)
from lautsprecher_konstruktion.drawings.horn_panels_dxf import render_horn_trapezoid_dxf
from lautsprecher_konstruktion.drawings.internal_dimensions_svg import (
    render_internal_dimensions_svg,
)
from lautsprecher_konstruktion.drawings.master_sheet_svg import render_master_sheet_svg
from lautsprecher_konstruktion.drawings.panel_sheet_svg import (
    panel_sheet_surfaces,
    render_panel_sheet_svg,
)
from lautsprecher_konstruktion.drawings.tapped_horn_dxf import render_tapped_f1_dxf
from lautsprecher_konstruktion.drawings.views import render_view_svg
from lautsprecher_konstruktion.export.assembly_guide import write_assembly_guide
from lautsprecher_konstruktion.export.bom import (
    build_bom,
    write_bom_csv,
    write_crossover_bom_csv,
    write_cutlist_csv,
)
from lautsprecher_konstruktion.export.cutting import (
    CuttingPlan,
    CuttingSettings,
    plan_cutting,
    render_cutting_svg,
    summary_lines,
    write_cutting_csv,
    write_cutting_pdf,
)
from lautsprecher_konstruktion.export.pdf_report import write_pdf_report
from lautsprecher_konstruktion.export.weight import estimate_weight
from lautsprecher_konstruktion.services.design import DesignBundle


def _csv(path: Path, header: tuple[str, ...], rows: list[tuple[object, ...]]) -> None:
    with path.open('w', newline='', encoding='utf-8-sig') as handle:
        writer = csv.writer(handle, delimiter=';')
        writer.writerow(header)
        writer.writerows(rows)


def _simulation_files(folder: Path, bundle: DesignBundle) -> None:
    r = bundle.vented_response
    if r:
        f = r.frequencies_hz
        _csv(folder/'frequenzgang.csv', ('Frequenz_Hz','Relativer_Pegel_dB','SPL_dB_1m'),
             [(float(hz), float(level), float(r.spl_db_1m[i]) if r.spl_db_1m is not None else '')
              for i,(hz,level) in enumerate(zip(f,r.response_db,strict=True))])
        _csv(folder/'membranauslenkung.csv', ('Frequenz_Hz','Auslenkung_mm','Xmax_mm'),
             [(float(hz), float(r.excursion_mm[i]) if r.excursion_mm is not None else '',
               bundle.project.driver.xmax_mm or '') for i,hz in enumerate(f)])
        if bundle.rear_port:
            _csv(folder/'portgeschwindigkeit.csv',
                 ('Frequenz_Hz','BR1_m_s','BR2_m_s','Maximum_m_s','Mach_Maximum'),
                 [(float(hz),float(r.front_port_velocity_m_s[i]) if r.front_port_velocity_m_s is not None else '',
                   float(r.rear_port_velocity_m_s[i]) if r.rear_port_velocity_m_s is not None else '',
                   float(r.port_velocity_m_s[i]) if r.port_velocity_m_s is not None else '',
                   float(r.port_mach[i]) if r.port_mach is not None else '') for i,hz in enumerate(f)])
        else:
            velocity_name = 'Passivmembran_Geschwindigkeit_m_s' if bundle.radiator else 'Port_Geschwindigkeit_m_s'
            _csv(folder/'portgeschwindigkeit.csv', ('Frequenz_Hz',velocity_name,'Mach'),
                 [(float(hz), float(r.port_velocity_m_s[i]) if r.port_velocity_m_s is not None else '',
                   float(r.port_mach[i]) if r.port_mach is not None else '') for i,hz in enumerate(f)])
        if bundle.radiator and r.port_velocity_m_s is not None:
            _csv(folder/'passivmembran.csv',('Frequenz_Hz','Auslenkung_mm','Xmax_mm'),
                 [(float(hz),float(r.port_velocity_m_s[i]/(2*np.pi*hz)*1000),
                   bundle.radiator.xmax_m*1000) for i,hz in enumerate(f)])
        _csv(folder/'gruppenlaufzeit.csv', ('Frequenz_Hz','Gruppenlaufzeit_ms'),
             [(float(hz),float(r.group_delay_ms[i])) for i,hz in enumerate(f)])
    else:
        f = np.geomspace(10.0,500.0,400)
        level = sealed_response_db(bundle.acoustic_driver,bundle.target_net_volume_m3,f)
        _csv(folder/'frequenzgang.csv', ('Frequenz_Hz','Relativer_Pegel_dB'),
             [(float(hz),float(db)) for hz,db in zip(f,level,strict=True)])
        for filename,metric in [('membranauslenkung.csv','Auslenkung_mm'),
                                ('portgeschwindigkeit.csv','Geschwindigkeit_m_s'),
                                ('gruppenlaufzeit.csv','Gruppenlaufzeit_ms')]:
            _csv(folder/filename,('Frequenz_Hz',metric),[])


def _cutting_files(folder: Path, bundle: DesignBundle,
                   settings: CuttingSettings | None) -> CuttingPlan:
    plan = plan_cutting(bundle, settings)
    write_cutting_csv(folder/'zuschnittplan.csv', plan)
    write_cutting_pdf(folder/'zuschnittplan.pdf', plan, bundle.project.name)
    sheets = folder/'zuschnittplan'; sheets.mkdir(exist_ok=True)
    for g_index, group in enumerate(plan.groups):
        for s_index, sheet in enumerate(group.sheets):
            (sheets/f'platte_{group.thickness_mm:.0f}mm_{sheet.index}.svg').write_text(
                render_cutting_svg(plan, g_index, s_index), encoding='utf-8')
    return plan


def export_project_package(bundle: DesignBundle, directory: str | Path,
                           cutting_settings: CuttingSettings | None = None) -> Path:
    geometry_errors=[issue.message for issue in bundle.issues if issue.severity == 'error'
                     and issue.code in {'FRONT_EDGE','FRONT_COLLISION','BACK_WALL','PORT_BACK_WALL','REAR_PORT_BACK_WALL','BRACE_COLLISION','BRACE_SPACE','DRILL_CUTOUT','DUPLICATE_ID','CHAMBER_DEPTH','ISOBARIC_DEPTH','ISOBARIC_WALL','ISOBARIC_COLLISION','ISOBARIC_DRIVER','LINE_DRIVER_TURN','LINE_PORT_HEIGHT','FRONT_HORN_DRIVER','FRONT_HORN_OBSTRUCTION','TAPPED_EXTRA_DRIVER'}]
    if geometry_errors:
        raise ValueError('Geometrie nicht fertigungstauglich: '+'; '.join(geometry_errors))
    out = Path(directory)
    out.mkdir(parents=True, exist_ok=True)
    project = bundle.project
    safe_name = ''.join(ch if ch.isalnum() or ch in '-_ ' else '_' for ch in project.name).strip(' _')
    package = out / (safe_name or 'Lautsprecherprojekt')
    package.mkdir(parents=True, exist_ok=True)
    manufacturing = package/'fertigung'; manufacturing.mkdir(exist_ok=True)
    drawings = package/'zeichnungen'; drawings.mkdir(exist_ok=True)
    crossover = package/'frequenzweiche'; crossover.mkdir(exist_ok=True)
    simulation = package/'simulation'; simulation.mkdir(exist_ok=True)

    (package/'project.json').write_text(project.model_dump_json(indent=2),encoding='utf-8')
    svg = render_master_sheet_svg(bundle)
    dxf = render_front_panel_dxf(bundle.cabinet,
        driver_cutout_diameter_m=project.driver.cutout_diameter_m,
        port=bundle.port, front_elements=bundle.front_elements)
    (drawings/'gesamtzeichnung.svg').write_text(svg,encoding='utf-8')
    (drawings/'massblatt.svg').write_text(render_dimension_svg(bundle),encoding='utf-8')
    (drawings/'innenaufbau_massblatt.svg').write_text(
        render_internal_dimensions_svg(bundle),encoding='utf-8')
    for surface in panel_sheet_surfaces(bundle):
        (drawings/f'einzelteil_{surface}.svg').write_text(
            render_panel_sheet_svg(bundle, surface), encoding='utf-8')
    _csv(drawings/'einbaukoordinaten.csv',
         ('ID','Fläche','X_Mitte_mm','Y_Mitte_mm','Ausschnitt_mm','Einbautiefe_mm'),
         list(dimension_rows(bundle)))
    (drawings/'frontplatte.svg').write_text(render_view_svg(bundle,'front'),encoding='utf-8')
    (drawings/'seitenansicht.svg').write_text(render_view_svg(bundle,'side'),encoding='utf-8')
    (drawings/'schnitt.svg').write_text(render_assembly_svg(bundle),encoding='utf-8')
    (drawings/'frontplatte.dxf').write_text(dxf,encoding='ascii')
    if bundle.coupler:
        (drawings/'isobarik_montagering.dxf').write_text(
            render_coupler_ring_dxf(bundle.coupler),encoding='ascii')
    if bundle.front_horn:
        for kind in ('top_bottom','sides'):
            (drawings/f'horn_trapez_{kind}.dxf').write_text(
                render_horn_trapezoid_dxf(bundle.front_horn,kind),encoding='ascii')
    if bundle.tapped_horn:
        (drawings/'tapped_horn_f1.dxf').write_text(
            render_tapped_f1_dxf(bundle.tapped_horn,project.driver),encoding='ascii')
    if any(e.surface == 'back' for e in bundle.front_elements):
        (drawings/'rueckwand.svg').write_text(render_view_svg(bundle,'back'),encoding='utf-8')
        (drawings/'rueckwand.dxf').write_text(render_front_panel_dxf(bundle.cabinet,
            front_elements=bundle.front_elements,surface='back'),encoding='ascii')
    if any(e.surface == 'partition' for e in bundle.front_elements):
        (drawings/'trennwand.svg').write_text(render_view_svg(bundle,'partition'),encoding='utf-8')
        (drawings/'trennwand.dxf').write_text(render_front_panel_dxf(bundle.cabinet,
            front_elements=bundle.front_elements,surface='partition'),encoding='ascii')

    if bundle.crossover:
        scheme = render_crossover_svg(bundle.crossover)
        (crossover/'schema.svg').write_text(scheme,encoding='utf-8')
        (package/'frequenzweiche_schema.svg').write_text(scheme,encoding='utf-8')
    write_crossover_bom_csv(crossover/'stueckliste.csv',bundle)
    bom=build_bom(bundle)
    write_bom_csv(manufacturing/'stueckliste.csv',bom)
    write_cutlist_csv(manufacturing/'zuschnittliste.csv',bundle)
    write_pdf_report(manufacturing/'fertigungsunterlagen.pdf',bundle,bom)
    _simulation_files(simulation,bundle)
    cutting_plan = _cutting_files(manufacturing, bundle, cutting_settings)
    write_assembly_guide(manufacturing, bundle, cutting_plan)

    # Retain the V-00.02 flat names for existing downstream users.
    (package/'gehaeuse_zeichnung.svg').write_text(svg,encoding='utf-8')
    (package/'frontplatte.dxf').write_text(dxf,encoding='ascii')
    write_bom_csv(package/'stueckliste.csv',bom)
    write_cutlist_csv(package/'zuschnittliste.csv',bundle)
    write_pdf_report(package/'fertigungsunterlagen.pdf',bundle,bom)

    measured={name:data.model_dump() for name,data in {
        'woofer_frd':project.crossover.woofer_frd,
        'tweeter_frd':project.crossover.tweeter_frd,
        'woofer_zma':project.crossover.woofer_zma,
        'tweeter_zma':project.crossover.tweeter_zma,
    }.items() if data is not None}
    if measured:
        folder=package/'messdaten';folder.mkdir(exist_ok=True)
        (folder/'importierte_messdaten.json').write_text(json.dumps(measured,indent=2,ensure_ascii=False),encoding='utf-8')

    summary=[project.name,f'Revision: {project.revision}',f'Gehäuse: {project.enclosure.enclosure_type}']
    if bundle.baffle_mode:
        summary.extend(((f'Schallwand: {bundle.cabinet.width_m*1000:.1f} x '
                        f'{bundle.cabinet.height_m*1000:.1f} x '
                        f'{bundle.cabinet.panel_thickness_m*1000:.1f} mm'),
                        f'Front/Rück-Schallweg: {(bundle.baffle_path_m or 0)*1000:.1f} mm'))
        if bundle.baffle_mode == 'infinite_baffle':
            summary.append(f'Rückraum mindestens: {bundle.target_net_volume_m3*1000:.1f} l')
    else:
        summary.extend((f'Netto: {bundle.target_net_volume_m3*1000:.2f} l',
                        (f'Außen: {bundle.cabinet.width_m*1000:.1f} x '
                        f'{bundle.cabinet.height_m*1000:.1f} x '
                        f'{bundle.cabinet.depth_m*1000:.1f} mm')))
    summary.extend(('', 'Zuschnitt:', *summary_lines(cutting_plan), estimate_weight(bundle).describe()))
    summary.extend(('', 'Warnungen:', *(f'- {w}' for w in bundle.warnings)))
    if bundle.radiator:
        summary.insert(4,f'Passivmembran-Zusatzmasse: {bundle.radiator.added_mass_kg*1000:.1f} g')
    if bundle.front_chamber_volume_m3 is not None and bundle.rear_chamber_volume_m3 is not None:
        summary.insert(4,f'Front-/Rückkammer: {bundle.front_chamber_volume_m3*1000:.1f}/{bundle.rear_chamber_volume_m3*1000:.1f} l')
    (package/'projektzusammenfassung.txt').write_text('\n'.join(summary),encoding='utf-8')
    return package
