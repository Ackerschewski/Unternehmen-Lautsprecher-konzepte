from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np

from lautsprecher_konstruktion.acoustics.baffle import simulate_baffle
from lautsprecher_konstruktion.acoustics.baffle_step import baffle_step_frequency_hz
from lautsprecher_konstruktion.acoustics.bandpass import (
    simulate_bandpass,
    simulate_bandpass_series,
)
from lautsprecher_konstruktion.acoustics.folded_line import simulate_folded_line
from lautsprecher_konstruktion.acoustics.front_horn import simulate_front_horn
from lautsprecher_konstruktion.acoustics.limits import DEFAULT_PORT_VELOCITY_LIMITS
from lautsprecher_konstruktion.acoustics.sealed import SealedResult
from lautsprecher_konstruktion.acoustics.tapped_horn import simulate_tapped_horn
from lautsprecher_konstruktion.acoustics.vented import VentedResponse, simulate_vented
from lautsprecher_konstruktion.crossover.passive import (
    CrossoverDesign,
    baffle_step_compensation,
    first_order_two_way,
    l_pad,
    second_order_butterworth_two_way,
    second_order_linkwitz_riley_two_way,
    zobel_from_re_le,
)
from lautsprecher_konstruktion.crossover.simulation import CrossoverResponse, simulate_crossover
from lautsprecher_konstruktion.crossover.standards import round_crossover_to_e12
from lautsprecher_konstruktion.crossover.three_way import simulate_three_way, three_way_network
from lautsprecher_konstruktion.enclosure.bracing import WindowBrace, brace_depths
from lautsprecher_konstruktion.enclosure.folded_line import (
    FOLDED_TYPES,
    REAR_HORN_TYPES,
    FoldedLine,
    baffle_displacement_m3,
    design_folded_line,
)
from lautsprecher_konstruktion.enclosure.front_horn import FrontHorn, design_front_horn
from lautsprecher_konstruktion.enclosure.isobaric import Coupler, equivalent_driver, make_coupler
from lautsprecher_konstruktion.enclosure.layout import FrontElement, check_layout
from lautsprecher_konstruktion.enclosure.passive_radiator import PassiveRadiatorDesign
from lautsprecher_konstruktion.enclosure.ports import PortDesign, round_port
from lautsprecher_konstruktion.enclosure.rectangular import (
    CabinetDimensions,
    CutPanel,
    cut_list,
    solve_depth_for_net_volume,
)
from lautsprecher_konstruktion.enclosure.registry import registry
from lautsprecher_konstruktion.enclosure.strategies import prepare_enclosure
from lautsprecher_konstruktion.enclosure.tapped_horn import (
    TappedHorn,
    design_tapped_horn,
    tapped_baffle_displacement_m3,
)
from lautsprecher_konstruktion.project.models import CrossoverConfig, SpeakerProject
from lautsprecher_konstruktion.warnings import DesignWarning


@dataclass(frozen=True)
class DesignBundle:
    project: SpeakerProject
    target_net_volume_m3: float
    cabinet: CabinetDimensions
    panels: tuple[CutPanel, ...]
    port: PortDesign | None
    brace: WindowBrace | None
    crossover: CrossoverDesign | None
    sealed: SealedResult | None
    total_displacement_m3: float
    warnings: tuple[str, ...]
    issues: tuple[DesignWarning, ...] = ()
    front_elements: tuple[FrontElement, ...] = ()
    vented_response: VentedResponse | None = None
    crossover_response: CrossoverResponse | None = None
    radiator: PassiveRadiatorDesign | None = None
    front_chamber_volume_m3: float | None = None
    rear_chamber_volume_m3: float | None = None
    partition_front_depth_m: float | None = None
    coupler: Coupler | None = None
    brace_depths_m: tuple[float, ...] = ()
    rear_port: PortDesign | None = None
    port_resistance_pa_s_m3: float | None = None
    folded_line: FoldedLine | None = None
    baffle_mode: str | None = None
    baffle_path_m: float | None = None
    baffle_wing_depth_m: float = 0.0
    front_horn: FrontHorn | None = None
    tapped_horn: TappedHorn | None = None

    @property
    def acoustic_driver(self):
        return (equivalent_driver(self.project.driver, self.project.enclosure.isobaric_wiring)
                if self.coupler else self.project.driver)


def _default_layout(project: SpeakerProject, cabinet: CabinetDimensions,
                    port: PortDesign | None,
                    radiator: PassiveRadiatorDesign | None = None,
                    rear_port: PortDesign | None = None) -> tuple[FrontElement, ...]:
    w, h = cabinet.width_m, cabinet.height_m
    result: list[FrontElement] = []
    driver = project.driver
    if driver.cutout_diameter_m:
        layout_type = ("woofer" if driver.driver_type in {"midwoofer", "coaxial_driver"} else
                       "tweeter" if driver.driver_type == "compression_driver" else driver.driver_type)
        result.append(FrontElement(id="W1", type=layout_type,
            surface="partition" if project.enclosure.enclosure_type.startswith("bandpass_") else "front",
            x_m=w/2, y_m=h*(0.50 if project.enclosure.enclosure_type.startswith("isobaric_") or
                            project.enclosure.enclosure_type == "compound_push_pull" else 0.62),
            outer_diameter_m=driver.outer_diameter_m or driver.cutout_diameter_m,
            cutout_diameter_m=driver.cutout_diameter_m,
            mounting_depth_m=driver.mounting_depth_m or 0))
    if port is not None:
        if port.shape == "round" and port.diameter_m:
            result.append(FrontElement(id="BR1", type="port", x_m=w/2,
                surface="back" if project.enclosure.enclosure_type == "cardioid" else "front",
                y_m=max(port.diameter_m/2+(project.enclosure.bottom_thickness_mm or project.enclosure.panel_thickness_mm)/1000+project.enclosure.brace_border_mm/1000+0.005, h*0.12), outer_diameter_m=port.diameter_m,
                cutout_diameter_m=port.diameter_m, mounting_depth_m=port.physical_length_m))
        elif port.width_m and port.height_m:
            result.append(FrontElement(id="BR1", type="port", x_m=w/2,
                y_m=port.height_m/2+(project.enclosure.bottom_thickness_mm or project.enclosure.panel_thickness_mm)/1000+project.enclosure.brace_border_mm/1000+0.005, width_m=port.width_m,
                height_m=port.height_m, mounting_depth_m=port.physical_length_m))
    if radiator is not None:
        result.append(FrontElement(id="PM1", type="passive_radiator", surface="back", x_m=w/2,
            y_m=max(radiator.cutout_diameter_m/2+0.025, h*0.17),
            outer_diameter_m=radiator.cutout_diameter_m*1.1,
            cutout_diameter_m=radiator.cutout_diameter_m,
            mounting_depth_m=radiator.mounting_depth_m))
    if rear_port is not None:
        assert rear_port.diameter_m is not None
        second_surface = ("partition" if project.enclosure.enclosure_type == "bandpass_6_series"
                          else "back")
        result.append(FrontElement(id="BR2", type="port", surface=second_surface, x_m=w/2,
            y_m=max(rear_port.diameter_m/2+0.025, h*0.18),
            outer_diameter_m=rear_port.diameter_m,
            cutout_diameter_m=rear_port.diameter_m,
            mounting_depth_m=rear_port.physical_length_m))
    return tuple(result)


def _resolve_layout(elements: tuple[FrontElement, ...], port: PortDesign | None,
                    rear_port: PortDesign | None = None) -> tuple[FrontElement, ...]:
    if port is None:
        return elements
    result: list[FrontElement] = []
    for element in elements:
        if element.type != "port":
            result.append(element)
            continue
        selected = rear_port if element.id == "BR2" else port
        if selected is None:
            continue
        data=element.model_dump()
        data["mounting_depth_m"]=selected.physical_length_m
        if selected.shape == "round":
            data.update(outer_diameter_m=selected.diameter_m,cutout_diameter_m=selected.diameter_m,
                        width_m=None,height_m=None)
        else:
            data.update(outer_diameter_m=None,cutout_diameter_m=None,
                        width_m=selected.width_m,height_m=selected.height_m)
        result.append(FrontElement.model_validate(data))
    return tuple(result)


def _simulate_network(design: CrossoverDesign, co: CrossoverConfig) -> CrossoverResponse:
    if design.ways == 3:
        return simulate_three_way(design, co.woofer_impedance_ohm, co.mid_impedance_ohm,
            co.tweeter_impedance_ohm, co.woofer_zma, co.mid_zma, co.tweeter_zma,
            co.woofer_frd, co.mid_frd, co.tweeter_frd)
    return simulate_crossover(design, co.woofer_impedance_ohm, co.tweeter_impedance_ohm,
        co.woofer_zma, co.tweeter_zma, co.woofer_frd, co.tweeter_frd)


def _crossover(project: SpeakerProject) -> tuple[CrossoverDesign | None, list[str]]:
    cfg = project.crossover
    warnings: list[str] = []
    if not cfg.enabled:
        return None, warnings

    if cfg.ways == 3:
        zobel = None
        if cfg.add_woofer_zobel:
            if project.driver.re_ohm and project.driver.le_h:
                zobel = (project.driver.re_ohm, project.driver.le_h)
            else:
                warnings.append("Zobel requested, but woofer Re/Le are incomplete.")
        step = None
        if cfg.baffle_step_compensation_db > 0:
            step = (baffle_step_frequency_hz(project.enclosure.external_width_mm / 1000.0),
                    cfg.baffle_step_compensation_db)
        assert cfg.upper_crossover_hz is not None  # guaranteed by CrossoverConfig for three ways
        network = three_way_network(
            cfg.crossover_hz, cfg.upper_crossover_hz, cfg.woofer_impedance_ohm, cfg.mid_impedance_ohm,
            cfg.tweeter_impedance_ohm, cfg.topology, woofer_re_le=zobel, baffle_step=step,
            mid_attenuation_db=cfg.mid_attenuation_db, tweeter_attenuation_db=cfg.tweeter_attenuation_db)
        return (round_crossover_to_e12(network) if cfg.round_to_standard_values else network), warnings

    if cfg.topology == "first_order":
        design = first_order_two_way(
            cfg.crossover_hz,
            cfg.woofer_impedance_ohm,
            cfg.tweeter_impedance_ohm,
        )
    elif cfg.topology == "butterworth_2":
        design = second_order_butterworth_two_way(
            cfg.crossover_hz,
            cfg.woofer_impedance_ohm,
            cfg.tweeter_impedance_ohm,
        )
    else:
        design = second_order_linkwitz_riley_two_way(
            cfg.crossover_hz,
            cfg.woofer_impedance_ohm,
            cfg.tweeter_impedance_ohm,
        )

    extra = list(design.components)
    notes = list(design.notes)

    if cfg.tweeter_attenuation_db > 0:
        extra.extend(l_pad(cfg.tweeter_impedance_ohm, cfg.tweeter_attenuation_db))
        notes.append(f"Tweeter L-pad target attenuation: {cfg.tweeter_attenuation_db:.1f} dB.")

    if cfg.add_woofer_zobel:
        if project.driver.re_ohm and project.driver.le_h:
            extra.extend(zobel_from_re_le(project.driver.re_ohm, project.driver.le_h))
            notes.append("Woofer Zobel added from Re/Le as a starting approximation.")
        else:
            warnings.append("Zobel requested, but woofer Re/Le are incomplete.")

    if cfg.baffle_step_compensation_db > 0:
        width_m = project.enclosure.external_width_mm / 1000.0
        f_bs = baffle_step_frequency_hz(width_m)
        extra.extend(baffle_step_compensation(f_bs, cfg.woofer_impedance_ohm,
                                              cfg.baffle_step_compensation_db))
        notes.append(f"Schallwandkorrektur {cfg.baffle_step_compensation_db:.1f} dB um {f_bs:.0f} Hz "
                     f"(Schallwandbreite {width_m * 1000:.0f} mm, Näherung; Wechselwirkung mit der Weiche messen).")

    result = replace(design, components=tuple(extra), notes=tuple(notes))
    return (round_crossover_to_e12(result) if cfg.round_to_standard_values else result), warnings


def _calculate_baffle_project(project: SpeakerProject) -> DesignBundle:
    cfg = project.enclosure
    driver = project.driver
    if driver.vas_m3 is None:
        raise ValueError("Für die Schallwandberechnung fehlt Vas")
    t = cfg.panel_thickness_mm/1000
    width,height = cfg.external_width_mm/1000,cfg.external_height_mm/1000
    wing = cfg.baffle_wing_depth_mm/1000 if cfg.enclosure_type == "dipole" else 0.0
    if cfg.enclosure_type == "dipole" and wing < 0.04:
        raise ValueError("Dipol/H-Frame benötigt mindestens 40 mm Flügeltiefe")
    volume = None
    if cfg.enclosure_type == "infinite_baffle":
        volume = (cfg.target_volume_l or 0)/1000
        if volume < 10*driver.vas_m3:
            raise ValueError("Infinite Baffle benötigt einen dichten rückseitigen Raum von mindestens 10 × Vas")
    cabinet = CabinetDimensions(width,height,
        max((driver.mounting_depth_m or 0)+2*t+0.03,wing+2*t),t)
    elements = tuple(e for e in project.front_elements if e.surface == "front" and e.type not in
                     {"port","passive_radiator"})
    if not any(e.id == "W1" for e in elements):
        elements += _default_layout(project,cabinet,None)
    issues = list(check_layout(elements,width,height,cabinet.internal_depth_m))
    if wing and driver.outer_diameter_m and driver.outer_diameter_m+0.02>width-2*t:
        issues.append(DesignWarning(code="DIPOLE_WING_COLLISION",severity="error",
            message="H-Frame-Seitenflügel kollidieren mit dem Treiberflansch."))
    path = width+2*wing
    response = simulate_baffle(driver,cfg.enclosure_type,path,volume,cfg.input_power_w)
    panels = (CutPanel("Schallwand",1,width,height,t),)
    if wing:
        panels += (CutPanel("H-Frame Seitenflügel",2,wing,height,t),)
    crossover,crossover_warnings = _crossover(project)
    crossover_response = None
    if crossover is not None:
        co = project.crossover
        crossover_response = _simulate_network(crossover, co)
    warnings = ["Schallwandmodell: Achsantwort mit vereinfachter Wegdifferenz; Raum, Kantenbeugung und Richtwirkung messen."]
    if volume is not None:
        warnings.append("Infinite Baffle: Rückraum vor Ort luftdicht trennen und Mindestvolumen sicherstellen; keine Gehäuserückwand in der Stückliste.")
    if wing:
        warnings.append("H-Frame: Seitenflügel rückseitig rechtwinklig und luftdicht an die Schallwand setzen; Falt-/Hohlraumresonanzen messen.")
    warnings.extend(crossover_warnings)
    warnings.extend(issue.message for issue in issues)
    return DesignBundle(project.model_copy(update={"front_elements":elements}),
        volume or 0.0,cabinet,panels,None,None,crossover,None,0.0,tuple(warnings),
        issues=tuple(issues),front_elements=elements,vented_response=response,
        crossover_response=crossover_response,baffle_mode=cfg.enclosure_type,
        baffle_path_m=path,baffle_wing_depth_m=wing)


def _calculate_tapped_project(project: SpeakerProject) -> DesignBundle:
    cfg=project.enclosure
    driver=project.driver
    if driver.vas_m3 is None or cfg.target_volume_l is None:
        raise ValueError('Tapped-Horn benötigt Vas und ein Netto-Zielvolumen')
    t=cfg.panel_thickness_mm/1000
    target=cfg.target_volume_l/1000
    displacement=driver.displacement_m3+cfg.additional_displacement_l/1000
    horn=None
    cabinet=None
    for _ in range(8):
        cabinet=solve_depth_for_net_volume(
            external_width_m=cfg.external_width_mm/1000,
            external_height_m=cfg.external_height_mm/1000,
            panel_thickness_m=t,target_net_volume_m3=target,
            displacement_m3=displacement,
            front_thickness_m=cfg.front_thickness_mm/1000 if cfg.front_thickness_mm else None,
            back_thickness_m=cfg.back_thickness_mm/1000 if cfg.back_thickness_mm else None,
            top_thickness_m=cfg.top_thickness_mm/1000 if cfg.top_thickness_mm else None,
            bottom_thickness_m=cfg.bottom_thickness_mm/1000 if cfg.bottom_thickness_mm else None,
            front_layers=cfg.front_layers)
        horn=design_tapped_horn(cabinet,driver)
        updated=(driver.displacement_m3+cfg.additional_displacement_l/1000+
                 tapped_baffle_displacement_m3(horn,driver))
        if abs(updated-displacement)<1e-8:
            break
        displacement=updated
    assert cabinet is not None and horn is not None
    horn=design_tapped_horn(cabinet,driver)
    displacement=(driver.displacement_m3+cfg.additional_displacement_l/1000+
                  tapped_baffle_displacement_m3(horn,driver))
    # A front cutout is the mouth only. W1 is mounted horizontally in F1.
    mouth=FrontElement(id='BR1',type='port',surface='front',
        x_m=cabinet.width_m/2,
        y_m=(cabinet.bottom_thickness_m or t)+horn.lower_height_m/2,
        width_m=horn.mouth_width_m,height_m=horn.mouth_height_m,
        mounting_depth_m=cabinet.effective_front_thickness_m)
    layout=(mouth,)
    issues=list(check_layout(layout,cabinet.width_m,cabinet.height_m,cabinet.internal_depth_m))
    if cfg.tuning_hz and abs(horn.quarter_wave_hz-cfg.tuning_hz)/cfg.tuning_hz>0.15:
        issues.append(DesignWarning(code='TAPPED_LENGTH_TARGET',severity='warning',
            message=f'Tapped-Horn-Linienweg ergibt {horn.quarter_wave_hz:.1f} Hz statt Ziel {cfg.tuning_hz:.1f} Hz; Volumen oder Höhe anpassen.'))
    if project.tweeter_name or project.additional_drivers or project.crossover.enabled:
        issues.append(DesignWarning(code='TAPPED_EXTRA_DRIVER',severity='error',
            message='Tapped-Horn-Fertigung ist ein einzelner Tieftöner; Hochtöner, Zusatztreiber und Weiche entfernen.'))
    response=simulate_tapped_horn(driver,horn,cabinet.internal_width_m,cfg.input_power_w)
    area=horn.mouth_width_m*horn.mouth_height_m
    port=PortDesign('slot',area,cabinet.effective_front_thickness_m,
        cabinet.effective_front_thickness_m+1.46*(area/np.pi)**0.5,
        horn.quarter_wave_hz,width_m=horn.mouth_width_m,height_m=horn.mouth_height_m)
    warnings=['Tapped-Horn: Zweifach-Einspeisung an F1, ebene Wellen und angenäherte Faltungs-/Mündungsverluste. Impedanz und Nahfeld am Prototyp messen.']
    warnings.extend(issue.message for issue in issues)
    return DesignBundle(project.model_copy(update={'front_elements':layout}),target,
        cabinet,cut_list(cabinet)+(horn.panel,),port,None,None,None,displacement,
        tuple(warnings),issues=tuple(issues),front_elements=layout,
        vented_response=response,tapped_horn=horn)


def calculate_project(project: SpeakerProject) -> DesignBundle:
    cfg = project.enclosure
    entry = registry.get(cfg.enclosure_type)
    if entry.status != "SUPPORTED":
        raise ValueError(f"{entry.label} ist {entry.status}; kein belastbarer Solver vorhanden.")
    if cfg.enclosure_type in {"infinite_baffle","open_baffle","dipole"}:
        return _calculate_baffle_project(project)
    if cfg.enclosure_type == 'horn_tapped':
        return _calculate_tapped_project(project)
    if project.driver.vas_m3 is None:
        raise ValueError("Vas des Tieftöners fehlt; Gehäuseauslegung nicht möglich.")
    warnings: list[str] = []
    issues: list[DesignWarning] = []
    prepared = prepare_enclosure(cfg, project.driver)
    sealed_result = prepared.sealed
    port = prepared.port
    rear_port = prepared.rear_port
    port_resistance = prepared.port_resistance_pa_s_m3
    if rear_port is not None:
        issues.append(DesignWarning(code="BANDPASS6_MODEL_LIMIT", severity="info",
            message="Bandpass 6: ideales Modell; Portabstand, Leckage und Kanalmoden am Prototyp messen."))
    radiator = prepared.radiator
    resonator = prepared.resonator
    front_volume = prepared.front_volume_m3
    rear_volume = prepared.rear_volume_m3
    target_net_volume_m3 = prepared.target_net_volume_m3
    recommended = project.driver.recommended_volume_m3
    if recommended and not cfg.enclosure_type.startswith("isobaric_"):
        deviation = abs(target_net_volume_m3-recommended)/recommended
        if deviation > 0.25:
            issues.append(DesignWarning(code="MANUFACTURER_VOLUME", severity="info",
                message=f"Netto {target_net_volume_m3*1000:.1f} l weicht {deviation*100:.0f} % von der veröffentlichten Hersteller-Beispielabstimmung {recommended*1000:.1f} l ab; Gehäuseprinzip und Messdaten vergleichen."))
    recommended_fb = project.driver.recommended_tuning_hz
    if recommended_fb and cfg.tuning_hz and not cfg.enclosure_type.startswith("isobaric_"):
        deviation_fb = abs(cfg.tuning_hz-recommended_fb)/recommended_fb
        if deviation_fb > 0.15:
            issues.append(DesignWarning(code="MANUFACTURER_TUNING", severity="info",
                message=f"Fb {cfg.tuning_hz:.1f} Hz weicht {deviation_fb*100:.0f} % von der Hersteller-Beispielabstimmung {recommended_fb:.1f} Hz ab."))
    isobaric = cfg.enclosure_type in {"isobaric_sealed", "isobaric_vented", "compound_push_pull"}
    pair_driver = equivalent_driver(project.driver, cfg.isobaric_wiring) if isobaric else project.driver

    t = cfg.panel_thickness_mm / 1000.0
    inner_w = cfg.external_width_mm / 1000.0 - 2 * t
    inner_h = cfg.external_height_mm / 1000.0 - ((cfg.top_thickness_mm or cfg.panel_thickness_mm)+(cfg.bottom_thickness_mm or cfg.panel_thickness_mm))/1000
    if inner_w <= 0 or inner_h <= 0:
        raise ValueError("cabinet width/height are incompatible with panel thickness")
    coupler = (make_coupler(project.driver, t, cfg.isobaric_gap_mm/1000)
               if isobaric else None)
    if coupler is not None and coupler.outer_diameter_m + 0.01 > min(inner_w, inner_h):
        raise ValueError("Isobarik-Koppelkammer passt nicht in die innere Breite/Höhe (10 mm Mindestabstand).")
    slot_wall_displacement = 0.0
    slot_panels: tuple[CutPanel, ...] = ()
    if port is not None and port.shape == "slot":
        assert port.width_m is not None and port.height_m is not None
        if port.width_m+2*t > inner_w or port.height_m+2*t > inner_h:
            raise ValueError("Slot-Port mit Kanalwänden passt nicht in die innere Breite/Höhe")
        length=port.physical_length_m
        slot_panels=(
            CutPanel("Slotkanal Deckel/Boden",2,port.width_m+2*t,length,t),
            CutPanel("Slotkanal Seiten",2,port.height_m,length,t),
        )
        slot_wall_displacement=sum(p.quantity*p.width_m*p.height_m*p.thickness_m
                                   for p in slot_panels)

    brace: WindowBrace | None = None
    if cfg.brace_quantity and cfg.enclosure_type not in FOLDED_TYPES:
        brace = WindowBrace(
            outer_width_m=inner_w,
            outer_height_m=inner_h,
            thickness_m=t,
            border_m=cfg.brace_border_mm / 1000.0,
            quantity=cfg.brace_quantity,
        )

    partition_displacement = inner_w*inner_h*t if rear_volume is not None else 0.0
    total_displacement = (
        project.driver.displacement_m3
        + cfg.additional_displacement_l / 1000.0
        + (port.displacement_m3 if port and cfg.enclosure_type not in {"aperiodic","cardioid"} else 0.0)
        + (rear_port.displacement_m3 if rear_port else 0.0)
        + (brace.total_displacement_m3 if brace else 0.0)
        + (radiator.displacement_m3 if radiator else 0.0)
        + partition_displacement
        + slot_wall_displacement
        + (coupler.displaced_volume_m3 if coupler else 0.0)
    )

    cabinet = solve_depth_for_net_volume(
        external_width_m=cfg.external_width_mm / 1000.0,
        external_height_m=cfg.external_height_mm / 1000.0,
        panel_thickness_m=t,
        target_net_volume_m3=target_net_volume_m3,
        displacement_m3=total_displacement,
        front_thickness_m=cfg.front_thickness_mm/1000 if cfg.front_thickness_mm else None,
        back_thickness_m=cfg.back_thickness_mm/1000 if cfg.back_thickness_mm else None,
        top_thickness_m=cfg.top_thickness_mm/1000 if cfg.top_thickness_mm else None,
        bottom_thickness_m=cfg.bottom_thickness_mm/1000 if cfg.bottom_thickness_mm else None,
        front_layers=cfg.front_layers,
    )
    folded_line: FoldedLine | None = None
    front_horn: FrontHorn | None = None
    if cfg.enclosure_type in FOLDED_TYPES:
        assert cfg.tuning_hz is not None
        diameter = project.driver.outer_diameter_m or project.driver.cutout_diameter_m
        assert diameter is not None
        # The extra panels displace air, so resolve cabinet depth and folds together.
        for _ in range(5):
            folded_line = design_folded_line(cabinet,cfg.enclosure_type,cfg.tuning_hz,diameter)
            new_displacement = total_displacement+baffle_displacement_m3(folded_line)
            updated = solve_depth_for_net_volume(
                external_width_m=cfg.external_width_mm/1000,
                external_height_m=cfg.external_height_mm/1000,
                panel_thickness_m=t,target_net_volume_m3=target_net_volume_m3,
                displacement_m3=new_displacement,
                front_thickness_m=cfg.front_thickness_mm/1000 if cfg.front_thickness_mm else None,
                back_thickness_m=cfg.back_thickness_mm/1000 if cfg.back_thickness_mm else None,
                top_thickness_m=cfg.top_thickness_mm/1000 if cfg.top_thickness_mm else None,
                bottom_thickness_m=cfg.bottom_thickness_mm/1000 if cfg.bottom_thickness_mm else None,
                front_layers=cfg.front_layers)
            if abs(updated.depth_m-cabinet.depth_m)<0.00001:
                cabinet=updated
                break
            cabinet=updated
        folded_line = design_folded_line(cabinet,cfg.enclosure_type,cfg.tuning_hz,diameter)
        total_displacement += baffle_displacement_m3(folded_line)
        if ((project.driver.mounting_depth_m or 0) >
                cabinet.internal_depth_m-folded_line.turn_gap_m-0.005):
            issues.append(DesignWarning(code="LINE_DRIVER_TURN",severity="error",
                message="Treibermagnet ragt in die erste Kanalumlenkung; Tiefe oder Kanalhöhe ändern."))
        if cfg.enclosure_type == "mltl":
            port = round_port(box_volume_m3=target_net_volume_m3,
                              tuning_hz=cfg.tuning_hz*0.7,
                              diameter_m=cfg.port_diameter_mm/1000)
        elif cfg.enclosure_type != "transmission_line_closed":
            area = folded_line.mouth_width_m*folded_line.mouth_height_m
            port = PortDesign("slot",area,cabinet.effective_front_thickness_m,
                              cabinet.effective_front_thickness_m+
                              1.46*(area/np.pi)**0.5,
                              folded_line.estimated_quarter_wave_hz,
                              width_m=folded_line.mouth_width_m,
                              height_m=folded_line.mouth_height_m)
        if (cfg.enclosure_type == "mltl" and port is not None and port.diameter_m is not None
                and port.diameter_m > folded_line.channel_heights_m[-1]-0.02):
            issues.append(DesignWarning(code="LINE_PORT_HEIGHT",severity="error",
                message="MLTL-Portdurchmesser passt nicht in den letzten Kanal mit 10 mm Randabstand."))
        delta = abs(folded_line.estimated_quarter_wave_hz-cfg.tuning_hz)/cfg.tuning_hz
        if delta>0.15:
            issues.append(DesignWarning(code="LINE_LENGTH_TARGET",severity="warning",
                message=f"Gefaltete Linie: rechnerisch {folded_line.estimated_quarter_wave_hz:.1f} Hz statt Ziel {cfg.tuning_hz:.1f} Hz; Breite/Höhe/Volumen anpassen."))
        warnings.append("Linien-/Hornmodell: segmentierter Querschnitt, plane Wellen und angenäherte Faltungs-, Dämm- und Mündungsverluste. Prototyp mit Impedanz- und Nahfeldmessung abstimmen.")
        if cfg.enclosure_type in REAR_HORN_TYPES:
            warnings.append("Horn: gestufte Rechteckkanäle bilden das Profil näherungsweise ab; kein glattes Horn und keine vollständige Richtwirkungsberechnung.")
    if cfg.enclosure_type == "horn_front":
        assert cfg.tuning_hz is not None
        front_horn=design_front_horn(cabinet,project.driver,cfg.tuning_hz)
        warnings.append("Front-Horn: exponentielles Flächenprofil in 24 akustischen Abschnitten; Richtwirkung, Halsübergang und Mundlast am Prototyp messen.")

    if project.driver.cutout_diameter_m and project.driver.cutout_diameter_m > inner_w:
        warnings.append("Driver cutout is wider than the available internal cabinet width.")
    if project.driver.mounting_depth_m and project.driver.mounting_depth_m > cabinet.internal_depth_m:
        warnings.append("Driver mounting depth exceeds the available internal cabinet depth.")
    if coupler is not None and project.driver.mounting_depth_m is not None:
        tandem_depth = coupler.length_m + coupler.ring_thickness_m + project.driver.mounting_depth_m
        if tandem_depth + 0.01 > cabinet.internal_depth_m:
            issues.append(DesignWarning(code="ISOBARIC_DEPTH", severity="error",
                message=f"Isobarik-Paar benötigt {tandem_depth*1000:.1f} mm Einbautiefe plus 10 mm Rückwandabstand; verfügbar {cabinet.internal_depth_m*1000:.1f} mm."))
    front_chamber_depth = None
    if front_volume is not None and rear_volume is not None:
        front_gross = front_volume + (port.displacement_m3 if port else 0.0) + slot_wall_displacement
        front_chamber_depth = front_gross/(cabinet.internal_width_m*cabinet.internal_height_m)
        if front_chamber_depth + t >= cabinet.internal_depth_m:
            raise ValueError("Bandpass: kein Platz für die hintere Kammer")
        if rear_port is not None:
            rear_gross = (rear_volume + rear_port.displacement_m3 +
                          project.driver.displacement_m3 + cfg.additional_displacement_l/1000)
            if brace is not None:
                rear_gross += brace.total_displacement_m3
            available_rear = cabinet.internal_depth_m-front_chamber_depth-t
            if rear_gross/(cabinet.internal_width_m*cabinet.internal_height_m) > available_rear+0.0001:
                raise ValueError("Rückkammer mit Port und Verdrängung passt nicht in das Gehäuse")
    available_port_depth = front_chamber_depth or cabinet.internal_depth_m
    if port and port.physical_length_m > available_port_depth:
        warnings.append("Port ist länger als seine Kammer; Faltung oder anderes Gehäuse nötig.")
        issues.append(DesignWarning(code="PORT_BACK_WALL",severity="error",
            message=f"Port passt nicht in seine Kammer; Überstand {(port.physical_length_m-available_port_depth)*1000:.1f} mm."))
    if rear_port is not None and front_chamber_depth is not None:
        rear_depth = cabinet.internal_depth_m-front_chamber_depth-t
        if rear_port.physical_length_m > rear_depth:
            issues.append(DesignWarning(code="REAR_PORT_BACK_WALL", severity="error",
                message=f"BR2 passt nicht in die Rückkammer; Überstand {(rear_port.physical_length_m-rear_depth)*1000:.1f} mm."))
    source_layout = project.front_elements
    if folded_line is not None:
        top = cabinet.height_m-(cabinet.top_thickness_m or t)-folded_line.channel_heights_m[0]/2
        driver = project.driver
        woofer = FrontElement(id="W1",type="woofer" if driver.driver_type == "midwoofer" else driver.driver_type,
            surface="front",x_m=cabinet.width_m/2,y_m=top,
            outer_diameter_m=driver.outer_diameter_m or driver.cutout_diameter_m,
            cutout_diameter_m=driver.cutout_diameter_m,
            mounting_depth_m=driver.mounting_depth_m or 0)
        line_elements = [woofer]
        if port is not None:
            if cfg.enclosure_type == "mltl":
                assert port.diameter_m is not None
                mouth = FrontElement(id="BR1",type="port",surface="front",
                    x_m=cabinet.width_m/2,
                    y_m=(cabinet.bottom_thickness_m or t)+folded_line.channel_heights_m[-1]/2,
                    outer_diameter_m=port.diameter_m,cutout_diameter_m=port.diameter_m,
                    mounting_depth_m=port.physical_length_m)
            else:
                mouth = FrontElement(id="BR1",type="port",surface="front",
                    x_m=cabinet.width_m/2,
                    y_m=(cabinet.bottom_thickness_m or t)+folded_line.channel_heights_m[-1]/2,
                    width_m=port.width_m,height_m=port.height_m,
                    mounting_depth_m=port.physical_length_m)
            line_elements.append(mouth)
        source_layout = tuple(line_elements)
    elif front_horn is not None and not source_layout:
        source_layout = tuple(e.model_copy(update={"y_m":cabinet.height_m/2})
                              for e in _default_layout(project,cabinet,None))
    elif cfg.enclosure_type == "cardioid":
        source_layout = tuple(e.model_copy(update={"surface":"back"}) if e.type == "port"
                              else e for e in source_layout)
    if cfg.enclosure_type.startswith("bandpass_"):
        source_layout = tuple(e.model_copy(update={"surface": "partition"}) if e.type in
                              {"woofer", "midrange", "fullrange", "subwoofer"} else e
                              for e in source_layout)
    else:
        source_layout = tuple(e.model_copy(update={"surface": "front"}) if e.surface == "partition" else e
                              for e in source_layout)
    if radiator is not None:
        source_layout = tuple(e for e in source_layout if e.type != "port")
    else:
        source_layout = tuple(e for e in source_layout if e.type != "passive_radiator")
    if port is None:
        source_layout = tuple(e for e in source_layout if e.type != "port")
    if rear_port is None:
        source_layout = tuple(e for e in source_layout if e.id != "BR2")
    elif cfg.enclosure_type == "bandpass_6_series":
        source_layout = tuple(e.model_copy(update={"surface":"partition"}) if e.id == "BR2" else e
                              for e in source_layout)
    else:
        source_layout = tuple(e.model_copy(update={"surface":"back"}) if e.id == "BR2" else e
                              for e in source_layout)
    layout = _resolve_layout(source_layout or _default_layout(project, cabinet, port, radiator, rear_port), port, rear_port)
    if front_horn is not None:
        woofer = next((e for e in layout if e.id == "W1" and e.surface == "front"),None)
        if woofer is None:
            issues.append(DesignWarning(code="FRONT_HORN_DRIVER",severity="error",
                message="Front-Horn benötigt W1 mittig auf der Frontplatte."))
        elif abs(woofer.x_m-cabinet.width_m/2)>0.005 or abs(woofer.y_m-cabinet.height_m/2)>0.005:
            issues.append(DesignWarning(code="FRONT_HORN_DRIVER",severity="error",
                message="W1 muss für den geraden Front-Hornhals mittig auf der Frontplatte sitzen."))
        if any(e.id!="W1" and e.surface=="front" for e in layout):
            issues.append(DesignWarning(code="FRONT_HORN_OBSTRUCTION",severity="error",
                message="Die Hornmündung belegt die Front; weitere Frontchassis entfernen oder separat montieren."))
    if port is not None and not any(e.id == "BR1" for e in layout):
        layout += tuple(e for e in _default_layout(project, cabinet, port)
                        if e.id == "BR1")
    if rear_port is not None and not any(e.id == "BR2" for e in layout):
        layout += tuple(e for e in _default_layout(project, cabinet, port, rear_port=rear_port)
                        if e.id == "BR2")
    if radiator is not None and not any(e.type == "passive_radiator" for e in layout):
        layout += tuple(e for e in _default_layout(project, cabinet, None, radiator)
                        if e.type == "passive_radiator")
    if port is not None and not any(e.type == "port" for e in layout):
        issues.append(DesignWarning(code="PORT_NOT_ON_FRONT",severity="warning",
            message="Port ist berechnet, aber im Frontlayout nicht platziert."))
    issues.extend(check_layout(layout, cabinet.width_m, cabinet.height_m,
        cabinet.internal_depth_m, partition_inset_m=t,
        partition_top_m=cabinet.top_thickness_m or t,
        partition_bottom_m=cabinet.bottom_thickness_m or t))
    if coupler is not None:
        woofer = next((e for e in layout if e.id == "W1" and e.surface == "front"), None)
        if woofer is None:
            issues.append(DesignWarning(code="ISOBARIC_DRIVER", severity="error",
                message="Für Isobarik muss W1 auf der Front sitzen."))
        else:
            margin = min(woofer.x_m-t, cabinet.width_m-t-woofer.x_m,
                         woofer.y_m-(cabinet.bottom_thickness_m or t),
                         cabinet.height_m-(cabinet.top_thickness_m or t)-woofer.y_m)
            if margin < coupler.outer_diameter_m/2+0.005:
                issues.append(DesignWarning(code="ISOBARIC_WALL", severity="error",
                    message="Koppelkammer berührt eine Gehäusewand; Mittelpunkt oder Breite/Höhe ändern."))
            for e in layout:
                if e is woofer or e.surface != "front":
                    continue
                clearance = np.hypot(e.x_m-woofer.x_m, e.y_m-woofer.y_m)
                other_radius = (e.outer_diameter_m/2 if e.outer_diameter_m else
                                np.hypot(e.width,e.height)/2)
                if clearance < coupler.outer_diameter_m/2 + other_radius + 0.005:
                    issues.append(DesignWarning(code="ISOBARIC_COLLISION", severity="error",
                        message=f"Koppelkammer kollidiert mit {e.id} im Innenraum."))
    if front_chamber_depth is not None:
        rear_chamber_depth=cabinet.internal_depth_m-front_chamber_depth-t
        for e in layout:
            available=(front_chamber_depth if e.surface == "front" else rear_chamber_depth)
            if e.mounting_depth_m > available:
                issues.append(DesignWarning(code="CHAMBER_DEPTH",severity="error",
                    message=f"{e.id}: Einbautiefe {e.mounting_depth_m*1000:.1f} mm überschreitet die Kammer um {(e.mounting_depth_m-available)*1000:.1f} mm."))
    brace_start = ((front_chamber_depth+t) if front_chamber_depth is not None else
                   (coupler.length_m+coupler.ring_thickness_m+(project.driver.mounting_depth_m or 0)+0.01)
                   if coupler else (project.driver.mounting_depth_m or 0)+0.01
                   if front_horn else 0.0)
    try:
        brace_positions = brace_depths(cabinet.internal_depth_m, brace, start_m=brace_start)
    except ValueError as exc:
        brace_positions = ()
        issues.append(DesignWarning(code="BRACE_SPACE", severity="error", message=str(exc)))
    if brace is not None:
        for index, depth_from_front in enumerate(brace_positions, start=1):
            plane=cabinet.effective_front_thickness_m+depth_from_front
            for e in layout:
                if e.surface != "front":
                    continue
                if e.mounting_depth_m <= plane:
                    continue
                edge_gap=min(e.x_m-e.width/2-t,cabinet.width_m-t-e.x_m-e.width/2,
                             e.y_m-e.height/2-(cabinet.bottom_thickness_m or t),
                             cabinet.height_m-(cabinet.top_thickness_m or t)-e.y_m-e.height/2)
                if edge_gap < brace.border_m:
                    overlap=(brace.border_m-edge_gap)*1000
                    issues.append(DesignWarning(code="BRACE_COLLISION",severity="error",
                        message=f"{e.id} kollidiert mit Strebe B{index} um {overlap:.1f} mm.",value=overlap))

    response: VentedResponse | None = None
    if resonator is not None or folded_line is not None or front_horn is not None:
        if front_horn is not None:
            response = simulate_front_horn(project.driver,target_net_volume_m3,
                                           front_horn,cfg.input_power_w)
        elif folded_line is not None:
            response = simulate_folded_line(project.driver,folded_line,
                                            cfg.input_power_w,port)
        elif rear_volume is not None:
            assert front_volume is not None and port is not None
            if cfg.enclosure_type == "bandpass_6_series":
                assert rear_port is not None
                response = simulate_bandpass_series(project.driver, rear_volume, front_volume,
                                                    port, rear_port, power_w=cfg.input_power_w)
            else:
                response = simulate_bandpass(project.driver, rear_volume, front_volume,
                                             port, power_w=cfg.input_power_w, rear_port=rear_port)
        else:
            response = simulate_vented(pair_driver, target_net_volume_m3,
                resonator, power_w=cfg.input_power_w, ql=cfg.ql, qa=cfg.qa, qp=cfg.qp,
                resonator_compliance_m5_n=(radiator.acoustic_compliance_m5_n if radiator else None),
                resonator_resistance_pa_s_m3=(radiator.acoustic_resistance_pa_s_m3 if radiator else None),
                port_resistance_pa_s_m3=port_resistance,
                rear_port_separation_m=cabinet.depth_m if cfg.enclosure_type == "cardioid" else None,
                rear_port_delay_s=cfg.cardioid_delay_ms/1000 if cfg.enclosure_type == "cardioid" else 0)
        if not response.absolute_available:
            issues.append(DesignWarning(code="SIMULATION_DATA_MISSING", severity="info",
                message="Absolute Auslenkung, Portgeschwindigkeit und SPL benötigen Sd, Re und Qes."))
        else:
            if response.port_velocity_m_s is not None and port is not None:
                i = int(np.argmax(response.port_velocity_m_s))
                speed = float(response.port_velocity_m_s[i])
                port_name = ("BR2" if response.rear_port_velocity_m_s is not None and
                             response.front_port_velocity_m_s is not None and
                             response.rear_port_velocity_m_s[i] > response.front_port_velocity_m_s[i]
                             else "BR1") if rear_port is not None else "Port"
                limits=DEFAULT_PORT_VELOCITY_LIMITS
                if speed > limits.caution_m_s:
                    issues.append(DesignWarning(code="PORT_VELOCITY_HIGH",
                        severity="error" if speed > limits.high_m_s else "warning",
                        message=f"{port_name}: Portgeschwindigkeit {speed:.1f} m/s bei {response.frequencies_hz[i]:.1f} Hz; Strömungsgeräusche möglich.",
                        frequency_hz=float(response.frequencies_hz[i]), value=speed, limit=limits.caution_m_s))
            if radiator is not None and response.port_velocity_m_s is not None:
                radiator_excursion = response.port_velocity_m_s/(2*np.pi*response.frequencies_hz)
                i = int(np.argmax(radiator_excursion))
                if radiator_excursion[i] > radiator.xmax_m:
                    issues.append(DesignWarning(code="RADIATOR_XMAX", severity="warning",
                        message=f"Passivmembran Xmax bei {response.frequencies_hz[i]:.1f} Hz überschritten: {radiator_excursion[i]*1000:.1f} mm."))
            if response.excursion_mm is not None and project.driver.xmax_mm is not None:
                i = int(np.argmax(response.excursion_mm))
                xmax = float(response.excursion_mm[i])
                if xmax > project.driver.xmax_mm:
                    issues.append(DesignWarning(code="XMAX_EXCEEDED", severity="warning",
                        message=f"Xmax bei {response.frequencies_hz[i]:.1f} Hz überschritten: {xmax:.1f} mm.",
                        frequency_hz=float(response.frequencies_hz[i]), value=xmax,
                        limit=project.driver.xmax_mm))
        if project.driver.power_rms_w is not None and cfg.input_power_w > project.driver.power_rms_w:
            issues.append(DesignWarning(code="POWER_RATING", severity="warning",
                message="Simulationsleistung über der Treiber-Nennbelastbarkeit.",
                value=cfg.input_power_w, limit=project.driver.power_rms_w))

    crossover, crossover_warnings = _crossover(project)
    warnings.extend(crossover_warnings)
    if (coupler and project.crossover.enabled and pair_driver.nominal_impedance_ohm and
            abs(project.crossover.woofer_impedance_ohm-pair_driver.nominal_impedance_ohm) > 0.5):
        issues.append(DesignWarning(code="ISOBARIC_CROSSOVER_IMPEDANCE", severity="warning",
            message=f"Weiche ist auf {project.crossover.woofer_impedance_ohm:g} Ω ausgelegt; das isobarische Paar hat nominell {pair_driver.nominal_impedance_ohm:g} Ω. Weiche neu berechnen und messen."))
    crossover_response = None
    if crossover is not None:
        co = project.crossover
        crossover_response = _simulate_network(crossover, co)
        all_frd = co.woofer_frd is not None and co.tweeter_frd is not None and (
            crossover.ways == 2 or co.mid_frd is not None)
        if all_frd and not crossover_response.phase_complete:
            issues.append(DesignWarning(code="FRD_PHASE_MISSING", severity="info",
                message="FRD ohne vollständige Phase: akustische Summe nur als Magnituden-Näherung."))
        if rear_volume is not None and co.woofer_frd is not None:
            issues.append(DesignWarning(code="BANDPASS_FRD", severity="info",
                message="Bandpass-Weichensumme nur mit am fertigen Gehäuse gemessenen FRD-Daten gültig."))

    warnings.extend(issue.message for issue in issues)
    if coupler is not None:
        warnings.append("Isobarik: ideal gekoppeltes identisches Treiberpaar; endliches Koppelvolumen und Verluste sind nicht im Frequenzgang modelliert. Polung nach Verschaltung prüfen.")
    if cfg.enclosure_type == "compound_push_pull":
        warnings.append("Push-Pull: W2 mechanisch umgedreht montieren und elektrisch gegensinnig polen, damit beide Membranen gleichgerichtet arbeiten. Verzerrungsreduktion wird nicht simuliert.")
    if port_resistance is not None:
        prefix = "Kardioid-Rückvent" if cfg.enclosure_type == "cardioid" else "Aperiodischer Vent"
        warnings.append(f"{prefix}widerstand Soll {port_resistance:.0f} Pa·s/m³; Dämpfungseinsatz durch Impedanzmessung am Prototyp abstimmen.")
    if cfg.enclosure_type == "cardioid":
        issues.append(DesignWarning(code="CARDIOID_MODEL_LIMIT",severity="info",
            message="Kardioid: polares Zweiquellenmodell mit festem Dämpfungsverzug; Richtwirkung und Verzögerung am Prototyp messen."))

    return DesignBundle(
        project=project.model_copy(update={"front_elements":layout}),
        target_net_volume_m3=target_net_volume_m3,
        cabinet=cabinet,
        panels=cut_list(cabinet) + slot_panels + (folded_line.baffle_panels if folded_line else ()) + (front_horn.panels if front_horn else ()) + ((CutPanel("Isobarik-Montagering", 1,
            coupler.outer_diameter_m, coupler.outer_diameter_m, t),) if coupler else ()) + ((CutPanel("Partition mit Treiberausschnitt", 1,
            cabinet.internal_width_m, cabinet.internal_height_m, t),) if rear_volume is not None else ()),
        port=port,
        rear_port=rear_port,
        port_resistance_pa_s_m3=port_resistance,
        brace=brace,
        crossover=crossover,
        sealed=sealed_result,
        total_displacement_m3=total_displacement,
        warnings=tuple(warnings),
        issues=tuple(issues),
        front_elements=layout,
        vented_response=response,
        crossover_response=crossover_response,
        radiator=radiator,
        front_chamber_volume_m3=front_volume if rear_volume is not None else None,
        rear_chamber_volume_m3=rear_volume,
        partition_front_depth_m=front_chamber_depth,
        coupler=coupler,
        brace_depths_m=brace_positions,
        folded_line=folded_line,
        front_horn=front_horn,
    )
