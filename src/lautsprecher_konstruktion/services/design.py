from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, cast

import numpy as np

from lautsprecher_konstruktion.acoustics.aperiodic import (
    aperiodic_q,
    cardioid_ideal_delay_s,
    specific_flow_resistance,
)
from lautsprecher_konstruktion.acoustics.baffle import (
    dipole_frequencies_hz,
    dipole_path_m,
    simulate_baffle,
)
from lautsprecher_konstruktion.acoustics.baffle_step import baffle_step_frequency_hz
from lautsprecher_konstruktion.acoustics.bandpass import (
    simulate_bandpass,
    simulate_bandpass_series,
)
from lautsprecher_konstruktion.acoustics.folded_line import simulate_folded_line
from lautsprecher_konstruktion.acoustics.front_horn import simulate_front_horn
from lautsprecher_konstruktion.acoustics.limits import DEFAULT_PORT_VELOCITY_LIMITS
from lautsprecher_konstruktion.acoustics.sealed import SealedResult
from lautsprecher_konstruktion.acoustics.sealed_response import simulate_sealed
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
from lautsprecher_konstruktion.drivers.models import Driver
from lautsprecher_konstruktion.enclosure.bracing import WindowBrace, brace_depths
from lautsprecher_konstruktion.enclosure.damping import VentDamper, WallLining, plan_wall_lining
from lautsprecher_konstruktion.enclosure.folded_line import (
    FOLDED_TYPES,
    LINE_TYPES,
    REAR_HORN_TYPES,
    STUFFING_LABELS,
    FoldedLine,
    baffle_displacement_m3,
    design_folded_line,
)
from lautsprecher_konstruktion.enclosure.front_horn import FrontHorn, design_front_horn
from lautsprecher_konstruktion.enclosure.interior import (
    InteriorGeometry,
    check_interior,
    inside_displacement_m3,
    port_protrusion_m,
)
from lautsprecher_konstruktion.enclosure.isobaric import Coupler, equivalent_driver, make_coupler
from lautsprecher_konstruktion.enclosure.layout import FrontElement, check_layout
from lautsprecher_konstruktion.enclosure.passive_radiator import PassiveRadiatorDesign
from lautsprecher_konstruktion.enclosure.ports import PortDesign, round_port_diameter_for_length_m
from lautsprecher_konstruktion.enclosure.rear_horn import rear_horn_notes
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
    tapped_horn_notes,
)
from lautsprecher_konstruktion.enclosure.treatment import (
    AcousticTreatment,
    check_treatments,
    derived_treatments,
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
    sealed_response: VentedResponse | None = None
    damping: WallLining | None = None
    vent_damper: VentDamper | None = None
    treatments: tuple[AcousticTreatment, ...] = ()  # planner defaults plus the project's own damping objects

    @property
    def acoustic_driver(self) -> Driver:
        return (equivalent_driver(self.project.driver, self.project.enclosure.isobaric_wiring)
                if self.coupler else self.project.driver)


# Closed-type families whose interior is lined with damping material.
LINED_FAMILIES = frozenset({"sealed", "aperiodic"})
MIN_DRIVER_REAR_CLEARANCE_M = 0.02
MIN_DEPTH_TO_SIDE_RATIO = 0.2


def _body_size(element: FrontElement) -> tuple[float, float]:
    """Extent behind the baffle: a front-mounted chassis has to pass through its cutout."""
    if element.cutout_diameter_m is not None:
        return element.cutout_diameter_m, element.cutout_diameter_m
    return element.width, element.height


def _wall_gap(element: FrontElement, cabinet: CabinetDimensions, t: float) -> float:
    """Smallest distance between the element body and the inner cabinet walls (can be negative)."""
    body_w, body_h = _body_size(element)
    if element.type == "port" and element.cutout_diameter_m is None:
        body_w, body_h = body_w+2*t, body_h+2*t  # slot duct: channel walls add one panel per side
    return min(element.x_m-body_w/2-t, cabinet.width_m-t-element.x_m-body_w/2,
               element.y_m-body_h/2-(cabinet.bottom_thickness_m or t),
               cabinet.height_m-(cabinet.top_thickness_m or t)-element.y_m-body_h/2)


def _proportion_issues(cabinet: CabinetDimensions, driver: Driver) -> list[DesignWarning]:
    """Plausibility of the solved depth: it is only a result of net volume / (inner width x height)."""
    issues: list[DesignWarning] = []
    mounting = driver.mounting_depth_m or 0.0
    spare = cabinet.internal_depth_m-mounting
    if mounting and 0 <= spare < MIN_DRIVER_REAR_CLEARANCE_M:
        issues.append(DesignWarning(code="DRIVER_REAR_CLEARANCE", severity="warning",
            message=(f"Zwischen Treiberrückseite und Rückwand bleiben nur {spare*1000:.0f} mm "
                     f"(Faustregel ≥ {MIN_DRIVER_REAR_CLEARANCE_M*1000:.0f} mm für Magnetbelüftung, Dämmung "
                     "und Kabel); Breite/Höhe verkleinern."),
            value=spare*1000, limit=MIN_DRIVER_REAR_CLEARANCE_M*1000))
    side = min(cabinet.width_m, cabinet.height_m)
    if cabinet.depth_m < MIN_DEPTH_TO_SIDE_RATIO*side:
        issues.append(DesignWarning(code="CABINET_PROPORTION", severity="warning",
            message=(f"Unplausible Proportion: Außentiefe {cabinet.depth_m*1000:.0f} mm bei "
                     f"{cabinet.width_m*1000:.0f} × {cabinet.height_m*1000:.0f} mm. Die Tiefe ergibt sich nur "
                     "aus Netto-Volumen / (Innenbreite × Innenhöhe); Front und Rückwand wären große, "
                     "schwingende Flächen. Breite oder Höhe verkleinern."),
            value=cabinet.depth_m*1000, limit=MIN_DEPTH_TO_SIDE_RATIO*side*1000))
    return issues


def _default_layout(project: SpeakerProject, cabinet: CabinetDimensions,
                    port: PortDesign | None,
                    radiator: PassiveRadiatorDesign | None = None,
                    rear_port: PortDesign | None = None) -> tuple[FrontElement, ...]:
    w, h = cabinet.width_m, cabinet.height_m
    result: list[FrontElement] = []
    driver = project.driver
    cfg = project.enclosure

    def floor_y(radius_m: float, fraction: float) -> float:
        # Keep the opening clear of the floor and of the window brace's lower border.
        clear = ((cfg.bottom_thickness_mm or cfg.panel_thickness_mm)/1000 +
                 (cfg.brace_border_mm/1000 if cfg.brace_quantity else 0.0) + 0.005)
        return max(radius_m + clear, radius_m + 0.025, h*fraction)

    if driver.cutout_diameter_m:
        layout_type = ("woofer" if driver.driver_type in {"midwoofer", "coaxial_driver"} else
                       "tweeter" if driver.driver_type == "compression_driver" else driver.driver_type)
        result.append(FrontElement(id="W1", type=cast(Any, layout_type),
            surface="partition" if project.enclosure.enclosure_type.startswith("bandpass_") else "front",
            x_m=w/2, y_m=h*(0.50 if project.enclosure.enclosure_type.startswith("isobaric_") or
                            project.enclosure.enclosure_type in {"compound_push_pull","open_baffle","dipole",
                                                                 "infinite_baffle"} else 0.62),
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
                # lower channel wall (one panel) has to clear the brace border as well
                y_m=port.height_m/2+project.enclosure.panel_thickness_mm/1000+(project.enclosure.bottom_thickness_mm or project.enclosure.panel_thickness_mm)/1000+project.enclosure.brace_border_mm/1000+0.005, width_m=port.width_m,
                height_m=port.height_m, mounting_depth_m=port.physical_length_m))
    if radiator is not None:
        result.append(FrontElement(id="PM1", type="passive_radiator", surface="back", x_m=w/2,
            y_m=floor_y(radiator.cutout_diameter_m*1.1/2, 0.17),
            outer_diameter_m=radiator.cutout_diameter_m*1.1,
            cutout_diameter_m=radiator.cutout_diameter_m,
            mounting_depth_m=radiator.mounting_depth_m))
    if rear_port is not None:
        assert rear_port.diameter_m is not None
        second_surface = ("partition" if project.enclosure.enclosure_type == "bandpass_6_series"
                          else "back")
        result.append(FrontElement(id="BR2", type="port", surface=cast(Any, second_surface), x_m=w/2,
            y_m=floor_y(rear_port.diameter_m/2, 0.18),
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
        # Small (1973): Vb >= 10 Vas keeps the Qtc rise below 5 % (Qtc = Qts sqrt(1 + Vas/Vb)).
        volume = (cfg.target_volume_l or 0)/1000
        minimum = 10*driver.vas_m3
        if volume < minimum*(1-1e-9):
            raise ValueError(
                "Infinite Baffle benötigt einen dichten rückseitigen Raum von mindestens 10 × Vas "
                f"= {minimum*1000:.0f} l (eingestellt: {volume*1000:.0f} l)")
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
    woofer = next((e for e in elements if e.id == "W1"), None)
    driver_x = woofer.x_m if woofer else width/2
    driver_y = woofer.y_m if woofer else height/2
    path: float | None = None
    if cfg.enclosure_type != "infinite_baffle":
        path = dipole_path_m(width,height,driver_x,driver_y,wing)
    response = simulate_baffle(driver,cfg.enclosure_type,path or width,volume,cfg.input_power_w)
    panels: tuple[CutPanel, ...] = (CutPanel("Schallwand",1,width,height,t),)
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
    if path is not None:
        f_corner,f_peak,f_null = dipole_frequencies_hz(path)
        issues.append(DesignWarning(code="DIPOLE_PATH",severity="info",
            message=(f"Dipol: wirksamer Umweg {path*1000:.0f} mm (kürzester Weg um die Schallwandkante, "
                     f"Treiber bei X {driver_x*1000:.0f} / Y {driver_y*1000:.0f} mm). Ohne Entzerrung "
                     f"fällt der Pegel unterhalb {f_corner:.0f} Hz mit 6 dB/Okt, Maximum bei "
                     f"{f_peak:.0f} Hz, erste Auslöschung bei {f_null:.0f} Hz."),
            frequency_hz=f_corner,value=path*1000))
        if wing:
            side_path = 2*(min(driver_x,width-driver_x)+wing)
            if path < side_path-1e-9:
                issues.append(DesignWarning(code="DIPOLE_HEIGHT_LIMIT",severity="warning",
                    message=(f"Der Umweg über Ober-/Unterkante ({path*1000:.0f} mm) ist kürzer als über die "
                             f"Seitenflügel ({side_path*1000:.0f} mm); Flügel allein verlängern den Weg nicht. "
                             "Treiber mittig setzen oder Schallwand höher bauen."),value=path*1000))
        fs = driver.fs_hz
        at_fs = float(np.interp(fs,response.frequencies_hz,response.response_db))
        if at_fs < -3:
            issues.append(DesignWarning(code="DIPOLE_EQ_NEEDED",
                severity="warning" if at_fs < -12 else "info",
                message=(f"Pegel bei Fs ({fs:.0f} Hz) {-at_fs:.1f} dB unter dem Mittelband; "
                         "Dipol-Anhebung (aktive Entzerrung, z. B. Linkwitz-Transformation) nötig, "
                         "die Membranauslenkung steigt entsprechend"
                         + ("; über 12 dB kaum beherrschbar, größere Schallwand/Flügel wählen." if at_fs < -12
                            else ".")),
                frequency_hz=fs,value=-at_fs))
        warnings.append("Open Baffle/Dipol: freien Rückraum lassen (typisch ≥ 0,5 m, besser ~1 m Abstand "
                        "zur Rückwand) und Standfestigkeit prüfen.")
    if project.crossover.enabled and project.crossover.baffle_step_compensation_db > 0:
        issues.append(DesignWarning(code="BAFFLE_STEP_NOT_APPLICABLE",severity="warning",
            message=("Schallwandstufen-Korrektur gilt für Boxen mit Halbraum-Abstrahlung. "
                     + ("Wandeinbau hat keine Baffle-Step; Korrektur entfernen."
                        if path is None else
                        "Open Baffle/Dipol haben keine Baffle-Step, sondern einen 6-dB/Okt-Dipolabfall; "
                        "Korrektur entfernen und die Dipolanhebung über die Weiche/DSP lösen."))))
    if response.excursion_mm is not None and driver.xmax_mm is not None:
        i = int(np.argmax(response.excursion_mm))
        peak = float(response.excursion_mm[i])
        if peak > driver.xmax_mm:
            issues.append(DesignWarning(code="XMAX_EXCEEDED",severity="warning",
                message=f"Xmax bei {response.frequencies_hz[i]:.1f} Hz überschritten: {peak:.1f} mm.",
                frequency_hz=float(response.frequencies_hz[i]),value=peak,limit=driver.xmax_mm))
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
        horn=design_tapped_horn(cabinet,driver,cfg.tuning_hz)
        updated=(driver.displacement_m3+cfg.additional_displacement_l/1000+
                 tapped_baffle_displacement_m3(horn,driver))
        if abs(updated-displacement)<1e-8:
            break
        displacement=updated
    assert cabinet is not None and horn is not None
    horn=design_tapped_horn(cabinet,driver,cfg.tuning_hz)
    displacement=(driver.displacement_m3+cfg.additional_displacement_l/1000+
                  tapped_baffle_displacement_m3(horn,driver))
    # A front cutout is the mouth only. W1 is mounted horizontally in F1.
    mouth=FrontElement(id='BR1',type='port',surface='front',
        x_m=cabinet.width_m/2,
        y_m=horn.mouth_center_y_m(cabinet),
        width_m=horn.mouth_width_m,height_m=horn.mouth_height_m,
        mounting_depth_m=cabinet.effective_front_thickness_m)
    layout=(mouth,)
    issues=list(check_layout(layout,cabinet.width_m,cabinet.height_m,cabinet.internal_depth_m))
    tapped_notes=tapped_horn_notes(horn,cfg.tuning_hz)
    for code,message in tapped_notes:
        if code:
            issues.append(DesignWarning(code=code,severity='warning',message=message))
    if project.tweeter_name or project.additional_drivers or project.crossover.enabled:
        issues.append(DesignWarning(code='TAPPED_EXTRA_DRIVER',severity='error',
            message='Tapped-Horn-Fertigung ist ein einzelner Tieftöner; Hochtöner, Zusatztreiber und Weiche entfernen.'))
    response=simulate_tapped_horn(driver,horn,cabinet.internal_width_m,cfg.input_power_w)
    area=horn.mouth_width_m*horn.mouth_height_m
    port=PortDesign('slot',area,cabinet.effective_front_thickness_m,
        cabinet.effective_front_thickness_m+1.46*(area/np.pi)**0.5,
        horn.quarter_wave_hz,width_m=horn.mouth_width_m,height_m=horn.mouth_height_m)
    warnings=['Tapped-Horn: Zweifach-Einspeisung an F1, ebene Wellen und angenäherte Faltungs-/Mündungsverluste. Impedanz und Nahfeld am Prototyp messen.']
    warnings.extend(message for code,message in tapped_notes if code is None)
    warnings.extend(issue.message for issue in issues)
    return DesignBundle(project.model_copy(update={'front_elements':layout}),target,
        cabinet,cut_list(cabinet, cfg.joint_style)+horn.panels,port,None,None,None,displacement,
        tuple(warnings),issues=tuple(issues),front_elements=layout,treatments=project.treatments,
        vented_response=response,tapped_horn=horn)


def _line_notes(line: FoldedLine, family: str, sd_m2: float | None,
                issues: list[DesignWarning]) -> list[str]:
    """Plausibility notes for transmission-line families (rules of thumb, not measured data)."""
    notes: list[str] = []
    areas = line.channel_areas_m2
    if family == "tqwt":
        taper = areas[0]/areas[-1]
        notes.append(f"TQWT: Querschnitt verjüngt sich vom Treiberende ({areas[0]*1e4:.0f} cm²) zur Mündung "
                     f"({areas[-1]*1e4:.0f} cm², Verhältnis {taper:.1f}:1; Literaturrichtwert etwa 2–4:1). "
                     "Gestufte Rechteckkanäle nähern die kontinuierliche Verjüngung an.")
    elif sd_m2:
        notes.append(f"Linienquerschnitt {min(areas[1:])*1e4:.0f}–{max(areas[1:])*1e4:.0f} cm² = "
                     f"{min(areas[1:])/sd_m2:.2f}–{max(areas[1:])/sd_m2:.2f} × Sd "
                     "(Praxisrichtwert 1,0–1,5 × Sd); Treiberkammer "
                     f"{line.driver_chamber_volume_m3*1000:.1f} l hinter dem Treiber.")
        if line.driver_chamber_volume_m3 > 0.45*sum(a*line.inner_depth_m for a in areas):
            issues.append(DesignWarning(code="LINE_PLENUM_LARGE",severity="warning",
                message="Treiberkammer ist ungewöhnlich groß gegenüber dem Linienvolumen; "
                        "Höhe/Breite oder Abstimmfrequenz anpassen."))
    if family == "mltl" and line.mltl_port_ratio is not None:
        notes.append(f"MLTL: Port am Leitungsende, Portfläche = {line.mltl_port_ratio:.2f} × Leitungsquerschnitt; "
                     f"Leitung kürzer als λ/4, Resonanz der massebelasteten Leitung {line.estimated_quarter_wave_hz:.1f} Hz (Näherung).")
        if not 0.15 <= line.mltl_port_ratio <= 1.0:
            issues.append(DesignWarning(code="MLTL_PORT_RATIO",severity="warning",
                message=f"MLTL-Portfläche/Leitungsquerschnitt = {line.mltl_port_ratio:.2f}; "
                        "Richtwert 0,15–1,0 (Quellen uneinheitlich), Portdurchmesser prüfen."))
    if family == "labyrinth":
        notes.append("Labyrinth: gefalteter, über die gesamte Länge gedämmter Kanal; Dämpfung stärker als bei der Linie.")
    opening = line.min_turn_opening_ratio
    notes.append(f"Umlenkspalte: Öffnungsfläche mindestens {opening:.2f} × Kanalquerschnitt (1,0 = ohne Verengung).")
    if opening < 0.75:
        issues.append(DesignWarning(code="LINE_TURN_CONSTRICTED",severity="warning",
            message=f"Umlenköffnung nur {opening:.2f} × Kanalquerschnitt; Verengung wirkt wie Massebelastung. "
                    "Tiefe vergrößern oder Kanäle niedriger wählen."))
    zones = ", ".join(f"K{i+1} {STUFFING_LABELS[x]}" for i,x in enumerate(line.stuffing))
    notes.append(f"Dämmung (Richtwert, dichteste Füllung treibernah): {zones}. Dämmung senkt die Schallgeschwindigkeit "
                 "(Bradbury-Effekt, nicht modelliert) und verschiebt die Abstimmung nach unten; Menge am Prototyp trimmen.")
    return notes


def _port_fit_hint(port: PortDesign, chamber_volume_m3: float, max_length_m: float) -> str:
    """German remedy for a port that is longer than the room its chamber offers."""
    tail = ("Alternativen: Gehäuse schmaler/niedriger (tieferer Raum), Abstimmfrequenz erhöhen, "
            "Slot-Port oder zusätzlichen Port.")
    if port.shape == "round" and chamber_volume_m3 > 0 and max_length_m > 0:
        d_max = round_port_diameter_for_length_m(box_volume_m3=chamber_volume_m3, tuning_hz=port.tuning_hz,
                                                 length_m=max_length_m)
        if d_max < (port.diameter_m or 0.0):
            return (f"Rund-Ø höchstens {d_max*1000:.0f} mm würde passen (Portgeschwindigkeit prüfen). "
                    + tail)
    return tail


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
    if radiator is not None and project.driver.sd_m2 and project.driver.xmax_m:
        driver_vd = project.driver.sd_m2*project.driver.xmax_m
        radiator_vd = radiator.area_m2*radiator.xmax_m
        if radiator_vd < 2*driver_vd:
            issues.append(DesignWarning(code="RADIATOR_DISPLACEMENT", severity="warning",
                message=(f"Passivmembran-Hubvolumen {radiator_vd*1e6:.0f} cm³ (Sd × Xmax) ist kleiner als das "
                         f"Doppelte des Treibers ({2*driver_vd*1e6:.0f} cm³); Richtwert nach Small (1973): "
                         "mindestens 2 × Treiber-Hubvolumen, sonst begrenzt die Passivmembran den Pegel "
                         "(mechanischer Anschlag)."),
                value=radiator_vd*1e6, limit=2*driver_vd*1e6))
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
    front_wall = (cfg.front_thickness_mm or cfg.panel_thickness_mm)*cfg.front_layers/1000
    back_wall = (cfg.back_thickness_mm or cfg.panel_thickness_mm)/1000
    rear_port_wall = t if cfg.enclosure_type == "bandpass_6_series" else back_wall
    coupler = (make_coupler(project.driver, t, cfg.isobaric_gap_mm/1000,
                            reversed_w2=cfg.enclosure_type == "compound_push_pull")
               if isobaric else None)
    if coupler is not None and coupler.outer_diameter_m + 0.01 > min(inner_w, inner_h):
        raise ValueError(
            f"Isobarik-Koppelkammer (außen Ø {coupler.outer_diameter_m*1000:.0f} mm) passt nicht in die innere "
            f"Breite/Höhe ({inner_w*1000:.0f} × {inner_h*1000:.0f} mm; 10 mm Mindestabstand): "
            f"Gehäuse mindestens {(coupler.outer_diameter_m+0.01+2*t)*1000:.0f} mm breit und hoch wählen.")
    slot_wall_displacement = 0.0
    slot_panels: tuple[CutPanel, ...] = ()
    if port is not None and port.shape == "slot":
        assert port.width_m is not None and port.height_m is not None
        if port.width_m+2*t > inner_w or port.height_m+2*t > inner_h:
            raise ValueError("Slot-Port mit Kanalwänden passt nicht in die innere Breite/Höhe")
        # The duct starts at the outer face of the front panel; the panel itself forms the first
        # front_wall of its length, the slot walls inside the box supply the rest.
        length=max(port.physical_length_m-front_wall,0.0)
        slot_panels=(
            CutPanel("Slotkanal Deckel/Boden",2,port.width_m+2*t,length,t),
            CutPanel("Slotkanal Seiten",2,port.height_m,length,t),
        ) if length > 0 else ()
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
        # Magnet-to-magnet pair: both motors sit inside the coupler envelope counted below.
        (0.0 if coupler is not None and coupler.w2_reversed else project.driver.displacement_m3)
        + cfg.additional_displacement_l / 1000.0
        + (inside_displacement_m3(port, front_wall) if port and cfg.enclosure_type not in {"aperiodic","cardioid"} else 0.0)
        + inside_displacement_m3(rear_port, rear_port_wall)
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
        mltl_port: tuple[float, float] | None = None
        if cfg.enclosure_type == "mltl":
            # Port = hole through the front baffle at the line end (mass load, effective length
            # = panel thickness + end corrections), not a Helmholtz port of the whole box volume.
            mltl_radius = cfg.port_diameter_mm/2000
            mltl_port = (np.pi*mltl_radius**2,
                         cabinet.effective_front_thickness_m+1.46*mltl_radius)
        # The extra panels displace air, so resolve cabinet depth and folds together.
        for _ in range(5):
            folded_line = design_folded_line(cabinet,cfg.enclosure_type,cfg.tuning_hz,diameter,
                                             project.driver.sd_m2,mltl_port,project.driver.vas_m3)
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
        folded_line = design_folded_line(cabinet,cfg.enclosure_type,cfg.tuning_hz,diameter,
                                         project.driver.sd_m2,mltl_port,project.driver.vas_m3)
        total_displacement += baffle_displacement_m3(folded_line)
        magnet_depth = project.driver.mounting_depth_m or 0
        if magnet_depth > cabinet.internal_depth_m-0.03:
            issues.append(DesignWarning(code="LINE_DRIVER_TURN",severity="error",
                message="Treibermagnet reicht bis zur Rückwand und blockiert die erste Kanalumlenkung; Tiefe ändern."))
        elif magnet_depth > cabinet.internal_depth_m-folded_line.gap_m(0)-0.005:
            issues.append(DesignWarning(code="LINE_DRIVER_TURN_NEAR",severity="warning",
                message="Treibermagnet liegt in der Tiefe des ersten Umlenkspalts; "
                        "Strömung geht darunter/darum herum, Magnet bleibt innerhalb der Treiberkammerhöhe."))
        if cfg.enclosure_type == "mltl":
            assert mltl_port is not None
            port = PortDesign("round",mltl_port[0],cabinet.effective_front_thickness_m,
                              mltl_port[1],folded_line.estimated_quarter_wave_hz,
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
        if folded_line.horn is not None:
            delta = 0.0  # horns are judged by their cutoff (see rear_horn_notes), not by c/4L
        if delta>0.15:
            issues.append(DesignWarning(code="LINE_LENGTH_TARGET",severity="warning",
                message=f"Gefaltete Linie: rechnerisch {folded_line.estimated_quarter_wave_hz:.1f} Hz statt Ziel {cfg.tuning_hz:.1f} Hz; Breite/Höhe/Volumen anpassen."))
        if cfg.enclosure_type in LINE_TYPES:
            warnings.extend(_line_notes(folded_line,cfg.enclosure_type,project.driver.sd_m2,issues))
        warnings.append("Linien-/Hornmodell: segmentierter Querschnitt, plane Wellen und angenäherte Faltungs-, Dämm- und Mündungsverluste. Prototyp mit Impedanz- und Nahfeldmessung abstimmen.")
        if cfg.enclosure_type in REAR_HORN_TYPES and folded_line.horn is not None:
            for code,message in rear_horn_notes(folded_line,cfg.tuning_hz,project.driver.vas_m3):
                if code:
                    issues.append(DesignWarning(code=code,severity="warning",message=message))
                else:
                    warnings.append(message)
    if cfg.enclosure_type == "horn_front":
        assert cfg.tuning_hz is not None
        front_horn=design_front_horn(cabinet,project.driver,cfg.tuning_hz)
        warnings.append(
            f"Front-Horn: {len(front_horn.section_lengths_m)} Pyramidenstumpf-Abschnitte mit Exponentialgesetz an den Grenzen "
            f"(fc {front_horn.cutoff_hz:.1f} Hz, S_M/S_T {front_horn.area_ratio:.2f}, Abweichung bis "
            f"{front_horn.max_area_deviation()*100:.1f} %); Richtwirkung, Halsübergang und Mundlast am Prototyp messen.")
        if front_horn.decompression > 1.2:
            warnings.append(
                f"Front-Horn: Hals {front_horn.throat_area_m2*1e4:.0f} cm² ist {front_horn.decompression:.1f}× die Membranfläche "
                "(Treiberrahmen bestimmt den Hals, keine Kompression); Wirkungsgradgewinn geringer als bei einem Hals ≈ Sd.")
        if front_horn.mouth_area_m2 < 0.5*front_horn.mouth_min_area_m2:
            warnings.append(
                f"Front-Horn: Mündung {front_horn.mouth_area_m2*1e4:.0f} cm² = "
                f"{front_horn.mouth_area_m2/front_horn.mouth_min_area_m2*100:.0f} % der freien Mindestfläche "
                f"{front_horn.mouth_min_area_m2*1e4:.0f} cm² für fc; Basserweiterung unterhalb der Mündungsgrenze begrenzt.")

    if cfg.enclosure_type not in FOLDED_TYPES and front_horn is None:
        issues.extend(_proportion_issues(cabinet, project.driver))
    if project.driver.cutout_diameter_m and project.driver.cutout_diameter_m > inner_w:
        warnings.append("Driver cutout is wider than the available internal cabinet width.")
    if project.driver.mounting_depth_m and project.driver.mounting_depth_m > cabinet.internal_depth_m:
        warnings.append("Driver mounting depth exceeds the available internal cabinet depth.")
    if coupler is not None and project.driver.mounting_depth_m is not None:
        tandem_depth = coupler.rear_extent_m
        if tandem_depth + 0.01 > cabinet.internal_depth_m:
            issues.append(DesignWarning(code="ISOBARIC_DEPTH", severity="error",
                message=(f"Isobarik-Paar benötigt {tandem_depth*1000:.1f} mm Einbautiefe plus 10 mm Rückwandabstand; "
                         f"verfügbar {cabinet.internal_depth_m*1000:.1f} mm. Die Tiefe ergibt sich aus Netto-Volumen "
                         "und Innenquerschnitt: Breite/Höhe verkleinern (Innenquerschnitt höchstens "
                         f"{cabinet.gross_internal_volume_m3/(tandem_depth+0.01)*10000:.0f} cm², heute "
                         f"{cabinet.internal_width_m*cabinet.internal_height_m*10000:.0f} cm²; die Koppelkammer braucht "
                         f"mindestens {(coupler.outer_diameter_m+0.01)*1000:.0f} mm), ein größeres Netto-Volumen "
                         "(höheres Qtc) wählen"
                         + ("." if coupler.w2_reversed else " oder den Push-Pull-Aufbau (Magnet an Magnet) nutzen."))))
    front_chamber_depth = None
    if front_volume is not None and rear_volume is not None:
        front_gross = front_volume + inside_displacement_m3(port, front_wall) + slot_wall_displacement
        front_chamber_depth = front_gross/(cabinet.internal_width_m*cabinet.internal_height_m)
        if front_chamber_depth + t >= cabinet.internal_depth_m:
            raise ValueError(
                f"Bandpass: kein Platz für die hintere Kammer (Frontkammer allein {front_chamber_depth*1000:.0f} mm "
                f"tief bei {cabinet.internal_depth_m*1000:.0f} mm Innentiefe). Frontkammer verkleinern oder "
                "Breite/Höhe des Gehäuses verringern.")
        if rear_port is not None:
            rear_gross = (rear_volume + inside_displacement_m3(rear_port, rear_port_wall) +
                          project.driver.displacement_m3 + cfg.additional_displacement_l/1000)
            if brace is not None:
                rear_gross += brace.total_displacement_m3
            available_rear = cabinet.internal_depth_m-front_chamber_depth-t
            if rear_gross/(cabinet.internal_width_m*cabinet.internal_height_m) > available_rear+0.0001:
                raise ValueError("Rückkammer mit Port und Verdrängung passt nicht in das Gehäuse")
    available_port_depth = front_chamber_depth or cabinet.internal_depth_m
    port_protrusion = port_protrusion_m(port.physical_length_m, front_wall) if port else 0.0
    if port and port_protrusion > available_port_depth:
        chamber = "Frontkammer" if front_chamber_depth is not None else "Gehäuse"
        warnings.append("Port ist länger als seine Kammer; Faltung oder anderes Gehäuse nötig.")
        issues.append(DesignWarning(code="PORT_BACK_WALL",severity="error",
            message=(f"BR1 passt nicht in die {chamber}: Rohrlänge {port.physical_length_m*1000:.0f} mm "
                     f"(davon {port_protrusion*1000:.0f} mm im Innenraum) bei nur "
                     f"{available_port_depth*1000:.0f} mm Tiefe, Überstand "
                     f"{(port_protrusion-available_port_depth)*1000:.1f} mm. "
                     + _port_fit_hint(port, front_volume if front_volume is not None else target_net_volume_m3,
                                      available_port_depth+front_wall))))
    if rear_port is not None and front_chamber_depth is not None:
        rear_depth = cabinet.internal_depth_m-front_chamber_depth-t
        rear_protrusion = port_protrusion_m(rear_port.physical_length_m, rear_port_wall)
        if rear_protrusion > rear_depth:
            issues.append(DesignWarning(code="REAR_PORT_BACK_WALL", severity="error",
                message=(f"BR2 passt nicht in die Rückkammer: Rohrlänge {rear_port.physical_length_m*1000:.0f} mm "
                         f"(davon {rear_protrusion*1000:.0f} mm im Innenraum) bei nur {rear_depth*1000:.0f} mm Tiefe, "
                         f"Überstand {(rear_protrusion-rear_depth)*1000:.1f} mm. "
                         + _port_fit_hint(rear_port, rear_volume if rear_volume is not None else 0.0,
                                          rear_depth+rear_port_wall))))
    source_layout = project.front_elements
    if folded_line is not None:
        top = cabinet.height_m-(cabinet.top_thickness_m or t)-folded_line.channel_heights_m[0]/2
        driver = project.driver
        woofer = FrontElement(id="W1",type=cast(Any, "woofer" if driver.driver_type == "midwoofer" else driver.driver_type),
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
        horn_driver = next((e for e in layout if e.id == "W1" and e.surface == "front"),None)
        if horn_driver is None:
            issues.append(DesignWarning(code="FRONT_HORN_DRIVER",severity="error",
                message="Front-Horn benötigt W1 mittig auf der Frontplatte."))
        elif abs(horn_driver.x_m-cabinet.width_m/2)>0.005 or abs(horn_driver.y_m-cabinet.height_m/2)>0.005:
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
        partition_bottom_m=cabinet.bottom_thickness_m or t,
        port_wall_m={"front": front_wall, "back": back_wall, "partition": t}))
    if coupler is not None:
        pair_woofer = next((e for e in layout if e.id == "W1" and e.surface == "front"), None)
        if pair_woofer is None:
            issues.append(DesignWarning(code="ISOBARIC_DRIVER", severity="error",
                message="Für Isobarik muss W1 auf der Front sitzen."))
        else:
            woofer = pair_woofer
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
            if e.type == "port":
                continue  # ports are reported as PORT_BACK_WALL / REAR_PORT_BACK_WALL with a fit hint
            if e.mounting_depth_m > available:
                issues.append(DesignWarning(code="CHAMBER_DEPTH",severity="error",
                    message=f"{e.id}: Einbautiefe {e.mounting_depth_m*1000:.1f} mm überschreitet die Kammer um {(e.mounting_depth_m-available)*1000:.1f} mm."))
    brace_start = ((front_chamber_depth+t) if front_chamber_depth is not None else
                   (coupler.rear_extent_m+0.01)
                   if coupler else (project.driver.mounting_depth_m or 0)+0.01
                   if front_horn else 0.0)
    if brace is not None and brace_start == 0.0:
        # Window braces must clear the chassis bodies; where a body cannot pass the window,
        # the braces move behind it instead of cutting through the magnet.
        blocking = [e.mounting_depth_m for e in layout if e.surface == "front"
                    and e.mounting_depth_m > 0 and _wall_gap(e, cabinet, t) < brace.border_m]
        if blocking:
            brace_start = max(blocking)+0.01
    try:
        brace_positions = brace_depths(cabinet.internal_depth_m, brace, start_m=brace_start,
                                       check_fit=cfg.enclosure_type in LINED_FAMILIES | {"cardioid"})
    except ValueError as exc:
        brace_positions = ()
        issues.append(DesignWarning(code="BRACE_SPACE", severity="error", message=str(exc)))
    if folded_line is None:
        issues.extend(check_interior(
            layout, InteriorGeometry(cabinet.internal_depth_m, front_wall, back_wall, t, front_chamber_depth),
            width_m=cabinet.width_m, height_m=cabinet.height_m, panel_thickness_m=t,
            bottom_thickness_m=cabinet.bottom_thickness_m or t, top_thickness_m=cabinet.top_thickness_m or t,
            brace=brace, brace_depths_m=brace_positions, coupler=coupler,
            ports={key: value for key, value in (("BR1", port), ("BR2", rear_port))
                   if value is not None and cfg.enclosure_type not in {"aperiodic", "cardioid"}}))

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
                                             port, power_w=cfg.input_power_w, rear_port=rear_port,
                                             rear_port_path_m=(cabinet.depth_m if rear_port is not None else 0.0))
        else:
            assert resonator is not None
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

    damping: WallLining | None = None
    if cfg.enclosure_type in LINED_FAMILIES and project.driver.mounting_depth_m:
        rear_obstruction = project.driver.mounting_depth_m
        if brace is not None and brace_positions:
            rear_obstruction = max(rear_obstruction, brace_positions[-1]+brace.thickness_m)
        damping = plan_wall_lining(cabinet, rear_obstruction, project.driver.cutout_diameter_m)
        if damping is None:
            issues.append(DesignWarning(code="DAMPING_NO_ROOM", severity="info",
                message=("Hinter dem Treiber ist zu wenig Tiefe für eine Wanddämmung (mindestens 10 mm Dämmung "
                         "plus 20 mm Abstand zum Magneten); Dämmung nur lose an die Seitenwände legen.")))
    vent_damper: VentDamper | None = None
    if port_resistance is not None and port is not None and cfg.enclosure_type in {"aperiodic", "cardioid"}:
        rs = specific_flow_resistance(port_resistance, port.area_m2)
        q = aperiodic_q(project.driver, target_net_volume_m3, port_resistance)
        vent_damper = VentDamper("back" if cfg.enclosure_type == "cardioid" else "front", port_resistance,
            port.area_m2, rs, q.qtc_closed, q.ql, q.qtc_effective, q.leak_corner_hz)
        if cfg.enclosure_type == "aperiodic":
            issues.append(DesignWarning(code="APERIODIC_QTC",
                severity="warning" if q.leak_corner_hz > 1.5*project.driver.fs_hz else "info",
                message=(f"Aperiodisch: Qtc geschlossen {q.qtc_closed:.2f}, Vent-Verlust QL {q.ql:.2f} "
                         f"→ Qtc gesamt ≈ {q.qtc_effective:.2f} (Ventmasse vernachlässigt). Unterhalb "
                         f"{q.leak_corner_hz:.0f} Hz fällt der Pegel zusätzlich mit 6 dB/Okt. "
                         f"Vent {port.area_m2*1e4:.0f} cm² braucht Dämpfungsmaterial mit ≈ {rs:.0f} Rayl "
                         f"(Rac {port_resistance:.0f} Pa·s/m³ = Rayl / Fläche)."),
                value=q.qtc_effective))
        elif response is not None and response.front_to_back_db is not None:
            band = (response.frequencies_hz >= 40) & (response.frequencies_hz <= 120)
            ratio = response.front_to_back_db[band]
            best = float(np.max(ratio))
            at = float(response.frequencies_hz[band][int(np.argmax(ratio))])
            ideal_ms = cardioid_ideal_delay_s(cabinet.depth_m)*1000
            issues.append(DesignWarning(code="CARDIOID_FRONT_BACK",
                severity="warning" if best < 10 else "info",
                message=(f"Kardioid: Rückdämpfung 40–120 Hz höchstens {best:.1f} dB (bei {at:.0f} Hz), "
                         f"Median {float(np.median(ratio)):.1f} dB"
                         + ("; ein Kardioid braucht ≥ 10 dB. " if best < 10 else ". ")
                         + f"Ideale Verzögerung Tiefe/c = {ideal_ms:.2f} ms (eingestellt "
                         f"{cfg.cardioid_delay_ms:.2f} ms); die Rückvent-Masse ρ·L/A muss klein gegen die "
                         "Boxnachgiebigkeit sein, sonst folgt der Volumenstrom des Vents dem Konus nicht."),
                value=best,limit=10.0))
    warnings.extend(issue.message for issue in issues)
    if coupler is not None:
        warnings.append("Isobarik: ideal gekoppeltes identisches Treiberpaar; endliches Koppelvolumen und Verluste sind nicht im Frequenzgang modelliert. Polung nach Verschaltung prüfen."
                        + (" Tandem: beide Membranen zeigen nach vorn, W2 sitzt hinter W1 und wird gleichsinnig gepolt." if cfg.enclosure_type != "compound_push_pull" else ""))
    if cfg.enclosure_type == "compound_push_pull":
        warnings.append("Push-Pull (Magnet an Magnet): W1 normal in der Front, W2 mechanisch umgedreht auf dem Montagering (Membran zeigt in die Hauptkammer, Magnete liegen in der Koppelkammer) und elektrisch gegensinnig gepolt, damit beide Membranen in dieselbe Richtung laufen. Verzerrungsreduktion wird nicht simuliert.")
    if port_resistance is not None:
        prefix = "Kardioid-Rückvent" if cfg.enclosure_type == "cardioid" else "Aperiodischer Vent"
        warnings.append(f"{prefix}widerstand Soll {port_resistance:.0f} Pa·s/m³; Dämpfungseinsatz durch Impedanzmessung am Prototyp abstimmen.")
    if cfg.enclosure_type == "cardioid":
        issues.append(DesignWarning(code="CARDIOID_MODEL_LIMIT",severity="info",
            message="Kardioid: polares Zweiquellenmodell mit festem Dämpfungsverzug; Richtwirkung und Verzögerung am Prototyp messen."))

    treatments = derived_treatments(damping, vent_damper) + project.treatments
    treatment_issues = check_treatments(cfg.enclosure_type, project.treatments)
    issues.extend(treatment_issues)
    warnings.extend(w.message for w in treatment_issues)
    return DesignBundle(
        project=project.model_copy(update={"front_elements":layout}),
        target_net_volume_m3=target_net_volume_m3,
        cabinet=cabinet,
        panels=cut_list(cabinet, cfg.joint_style) + slot_panels + (folded_line.baffle_panels if folded_line else ()) + (front_horn.panels if front_horn else ()) + ((CutPanel("Isobarik-Montagering", 1,
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
        sealed_response=(simulate_sealed(pair_driver, target_net_volume_m3, cfg.input_power_w,
                                         ql=cfg.ql) if sealed_result is not None and response is None else None),
        crossover_response=crossover_response,
        radiator=radiator,
        front_chamber_volume_m3=front_volume if rear_volume is not None else None,
        rear_chamber_volume_m3=rear_volume,
        partition_front_depth_m=front_chamber_depth,
        coupler=coupler,
        brace_depths_m=brace_positions,
        damping=damping,
        vent_damper=vent_damper,
        treatments=treatments,
        folded_line=folded_line,
        front_horn=front_horn,
    )
