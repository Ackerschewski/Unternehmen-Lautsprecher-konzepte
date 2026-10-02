"""Deterministic assistant pipeline sharing SpeakerProject and DesignBundle.

The engine rejects physical/available-data failures before scoring. Scores are
relative normalized engineering indicators, not listening-test ratings.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from math import ceil, log10
from typing import Literal

import numpy as np
from pydantic import BaseModel, Field

from lautsprecher_konstruktion.acoustics.sealed import solve_sealed
from lautsprecher_konstruktion.drivers.models import Driver
from lautsprecher_konstruktion.enclosure.isobaric import equivalent_driver
from lautsprecher_konstruktion.enclosure.layout import FrontElement
from lautsprecher_konstruktion.enclosure.registry import registry
from lautsprecher_konstruktion.export.bom import BomItem, build_bom
from lautsprecher_konstruktion.export.pricing import budget_cost
from lautsprecher_konstruktion.library.store import ComponentLibrary
from lautsprecher_konstruktion.optimization.profiles import PROFILES, SoundProfile
from lautsprecher_konstruktion.project.models import (
    CrossoverConfig,
    EnclosureConfig,
    ProjectAccessory,
    SpeakerProject,
)
from lautsprecher_konstruktion.services.design import DesignBundle, calculate_project

SPEAKER_TYPES = (
    "Subwoofer", "Regallautsprecher", "Kompaktlautsprecher", "Standlautsprecher",
    "Center", "Heimkino-Surround", "Studio-Monitor", "PA-Lautsprecher",
    "PA-Subwoofer", "Desktop-Lautsprecher", "Breitbandlautsprecher", "Custom",
)


class AutomaticDesignRequest(BaseModel):
    project_name: str = "Mein Lautsprecher"
    speaker_type: str = "Regallautsprecher"
    enclosure_preference: str = "auto"
    max_width_m: float = Field(default=0.3, gt=0)
    max_height_m: float = Field(default=0.5, gt=0)
    max_depth_m: float = Field(default=0.4, gt=0)
    max_outer_volume_l: float | None = Field(default=None, gt=0)
    sound_profile: str = "neutral"
    budget: float | None = Field(default=None, gt=0)
    target_spl_db: float | None = None
    target_f3_hz: float | None = Field(default=None, gt=0)
    way_count: int | None = Field(default=None, ge=1)
    active: bool = False
    preferred_size_m: float | None = Field(default=None, gt=0)
    amplifier_power_w: float = Field(default=5.0, gt=0)
    preferred_manufacturer: str | None = None
    preferred_driver: str | None = None
    panel_thickness_m: float = Field(default=0.018, gt=0)
    material: str = "Birke Multiplex"


@dataclass(frozen=True)
class ScoreMetric:
    name: str
    value: float
    weight: float
    evidence: str


@dataclass(frozen=True)
class SpeakerDesign:
    label: str
    project: SpeakerProject
    bundle: DesignBundle
    woofer: Driver
    tweeter: Driver | None
    score: float
    breakdown: tuple[ScoreMetric, ...]
    reasons: tuple[str, ...]
    bom: tuple[BomItem, ...]
    price: float | None
    spl_limit_db: float | None
    provisional_crossover: bool
    total_price_eur: float | None = None


@dataclass(frozen=True)
class AutomaticDesignResult:
    status: Literal["ok", "impossible", "cancelled"]
    designs: tuple[SpeakerDesign, ...]
    rejection_reasons: tuple[str, ...]
    suggested_constraint_changes: tuple[str, ...]
    candidates_tested: int


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


def _operating_band(request: AutomaticDesignRequest, frequencies: np.ndarray) -> np.ndarray:
    lower = 20 if "subwoofer" in request.speaker_type.casefold() else 30
    return (frequencies >= lower) & (frequencies <= 120)


def _allowed_types(request: AutomaticDesignRequest) -> tuple[str, ...]:
    name = request.speaker_type.casefold()
    if "subwoofer" in name:
        return ("subwoofer", "woofer")
    if "breitband" in name:
        return ("fullrange",)
    return ("midwoofer", "woofer", "fullrange")


def _enclosures(request: AutomaticDesignRequest) -> tuple[str, ...]:
    if request.enclosure_preference != "auto":
        entry = registry.get(request.enclosure_preference)
        return (entry.id,) if entry.status == "SUPPORTED" else ()
    if "subwoofer" in request.speaker_type.casefold():
        return ("sealed", "bass_reflex", "passive_radiator", "bandpass_4")
    return ("sealed", "bass_reflex", "passive_radiator")


def _reasonable_f3_limit(request: AutomaticDesignRequest) -> float:
    name = request.speaker_type.casefold()
    if "subwoofer" in name:
        base = 60.0
    elif "stand" in name:
        base = 55.0
    elif "desktop" in name or "breitband" in name:
        base = 100.0
    else:
        base = 75.0
    factor = {"deep_bass": .75, "compact": 1.35, "punch": 1.15,
              "max_spl": 1.2}.get(request.sound_profile, 1.0)
    return base * factor


def _compatible_tweeters(woofer: Driver, tweeters: tuple[Driver, ...],
                         budget: float | None) -> tuple[tuple[Driver, float], ...]:
    choices = []
    for tweeter in tweeters:
        if budget is not None and (tweeter.price is None or tweeter.currency != "EUR"):
            continue
        lower = max(tweeter.min_frequency_hz or tweeter.fs_hz * 2,
                    tweeter.fs_hz * 2, 1500)
        upper = min(woofer.max_frequency_hz or 0, tweeter.max_frequency_hz or 30_000)
        if lower > upper or (woofer.nominal_impedance_ohm and tweeter.nominal_impedance_ohm
                              and abs(woofer.nominal_impedance_ohm-tweeter.nominal_impedance_ohm)>4):
            continue
        choices.append((tweeter, lower))
    return tuple(sorted(choices, key=lambda value: (
        value[0].price if budget is not None else value[1],
        value[1], value[0].manufacturer, value[0].model)))


def _layout(woofer: Driver, tweeter: Driver | None, width: float, height: float,
            enclosure: str, port_diameter: float) -> tuple[FrontElement, ...]:
    diameter = woofer.outer_diameter_m or woofer.cutout_diameter_m or 0
    effective_diameter = diameter + (0.046 if enclosure.startswith("isobaric_") else 0)
    if enclosure == "bandpass_4":
        woofer_y = height * 0.55
    elif enclosure in {"bass_reflex", "isobaric_vented"}:
        port_y = max(port_diameter/2 + 0.018 + 0.035 + 0.005, height*0.12)
        woofer_y = port_y + port_diameter/2 + effective_diameter/2 + 0.012
    else:
        woofer_y = max(effective_diameter/2 + 0.02, height*0.42)
    result = [FrontElement(id="W1", type="subwoofer" if woofer.driver_type == "subwoofer" else
        "fullrange" if woofer.driver_type == "fullrange" else "woofer",
        surface="partition" if enclosure == "bandpass_4" else "front",
        x_m=width/2, y_m=woofer_y, outer_diameter_m=diameter,
        cutout_diameter_m=woofer.cutout_diameter_m,
        mounting_depth_m=woofer.mounting_depth_m or 0,
        bolt_circle_diameter_m=woofer.bolt_circle_diameter_m,
        bolt_count=woofer.bolt_count or 0 if woofer.bolt_circle_diameter_m else 0,
        hole_diameter_m=woofer.bolt_hole_diameter_m)]
    if tweeter is not None:
        td = tweeter.outer_diameter_m or tweeter.cutout_diameter_m or 0
        result.append(FrontElement(id="T1", type="tweeter", x_m=width/2,
            y_m=woofer_y+effective_diameter/2+td/2+0.012, outer_diameter_m=td,
            cutout_diameter_m=tweeter.cutout_diameter_m,
            mounting_depth_m=tweeter.mounting_depth_m or 0,
            bolt_circle_diameter_m=tweeter.bolt_circle_diameter_m,
            bolt_count=tweeter.bolt_count or 0 if tweeter.bolt_circle_diameter_m else 0,
            hole_diameter_m=tweeter.bolt_hole_diameter_m))
    return tuple(result)


def _dimensions(request: AutomaticDesignRequest, woofer: Driver, tweeter: Driver | None,
                enclosure: str, port_diameter: float) -> tuple[tuple[float, float], ...]:
    d = woofer.outer_diameter_m or woofer.cutout_diameter_m or 0
    if enclosure.startswith("isobaric_"):
        d += 0.046
    td = tweeter.outer_diameter_m if tweeter else 0
    min_width = max(d+(0.055 if enclosure.startswith("isobaric_") else 0.04), 0.16)
    min_height = d+(td or 0)+0.06
    if enclosure in {"bass_reflex", "bandpass_4", "isobaric_vented"}:
        min_height += port_diameter+0.05
    min_height = max(min_height, d+0.055)
    widths = sorted({round(min_width, 3), round(min(min_width+0.04, request.max_width_m), 3),
                     round(request.max_width_m, 3)})
    heights = sorted({round(min_height, 3), round(min(min_height+0.06, request.max_height_m), 3),
                      round(request.max_height_m, 3)})
    return tuple((w, h) for w in widths for h in heights
                 if w <= request.max_width_m+1e-6 and h <= request.max_height_m+1e-6)


def _score(bundle: DesignBundle, request: AutomaticDesignRequest,
           profile: SoundProfile, total_price: float | None) -> tuple[float, tuple[ScoreMetric, ...]]:
    response = bundle.vented_response
    f3 = bundle.sealed.f3_hz if bundle.sealed else (response.f3_hz if response else None)
    metrics: list[ScoreMetric] = []

    def add(key: str, value: float, evidence: str) -> None:
        metrics.append(ScoreMetric(key, _clamp(value), profile.weights[key], evidence))

    target = request.target_f3_hz or bundle.project.driver.fs_hz * profile.f3_to_fs_limit
    if f3 is not None:
        add("bass", 100*min(1, target/f3), f"F3 {f3:.1f} Hz; Ziel {target:.1f} Hz")
    used = bundle.cabinet.width_m*bundle.cabinet.height_m*bundle.cabinet.depth_m
    available = request.max_width_m*request.max_height_m*request.max_depth_m
    add("size", 100*(1-used/available), f"Außenvolumen {used*1000:.1f} von {available*1000:.1f} l")
    if response is not None:
        band = _operating_band(request, response.frequencies_hz)
        band_label = "20–120" if "subwoofer" in request.speaker_type.casefold() else "30–120"
        if response.excursion_mm is not None and bundle.project.driver.xmax_mm:
            x = float(np.max(response.excursion_mm[band]))
            add("headroom", 100*(1-x/bundle.project.driver.xmax_mm),
                f"Auslenkung {x:.1f}/{bundle.project.driver.xmax_mm:.1f} mm bei {request.amplifier_power_w:g} W")
        if response.port_velocity_m_s is not None and bundle.port is not None:
            v = float(np.max(response.port_velocity_m_s[band]))
            add("port", 100*(1-v/17), f"Portgeschwindigkeit {v:.1f}/17 m/s")
        delay = float(np.max(response.group_delay_ms[band]))
        add("delay", 100*(1-delay/50), f"Gruppenlaufzeit max. {delay:.1f} ms ({band_label} Hz)")
        level = response.response_db[band]
        ripple = float(np.percentile(level, 90)-np.percentile(level, 10))
        add("flatness", 100*(1-ripple/12), f"Pegelspanne {ripple:.1f} dB ({band_label} Hz)")
    if total_price is not None and request.budget:
        add("cost", 100*(1-total_price/request.budget),
            f"Gesamtkalkulation inkl. 15 % Reserve {total_price:.2f}/{request.budget:.2f} EUR")
    score = sum(item.value*item.weight for item in metrics)/sum(item.weight for item in metrics)
    return score, tuple(metrics)


def automatic_design(request: AutomaticDesignRequest, library: ComponentLibrary,
                     progress: Callable[[int], None] | None = None,
                     cancelled: Callable[[], bool] | None = None) -> AutomaticDesignResult:
    if request.sound_profile not in PROFILES:
        raise ValueError("Unbekanntes Klangprofil")
    if request.enclosure_preference != "auto":
        try:
            entry = registry.get(request.enclosure_preference)
        except KeyError as exc:
            raise ValueError("Unbekannter Gehäusetyp") from exc
        if entry.status != "SUPPORTED":
            return AutomaticDesignResult("impossible", (),
                (f"{entry.label} ist derzeit {entry.status}; es gibt keinen validierten Solver.",),
                ("Geschlossen, Bassreflex oder Passivmembran wählen.",), 0)
    if request.way_count is not None and request.way_count > 2:
        return AutomaticDesignResult("impossible", (),
            ("Automatischer 2,5-/3-Wege-Entwurf ist noch nicht berechenbar.",),
            ("1 oder 2 Wege wählen oder den Expertenmodus verwenden.",), 0)
    profile = PROFILES[request.sound_profile]
    allowed = _allowed_types(request)
    woofers = library.drivers(*allowed)
    tweeters = library.drivers("tweeter")
    if request.preferred_manufacturer:
        woofers = tuple(d for d in woofers if d.manufacturer.casefold() == request.preferred_manufacturer.casefold())
    if request.preferred_driver:
        woofers = tuple(d for d in woofers if
                        f"{d.manufacturer} {d.model}" == request.preferred_driver)
    if request.preferred_size_m:
        woofers = tuple(d for d in woofers if d.nominal_size_m is not None
                        and abs(d.nominal_size_m-request.preferred_size_m) <= 0.025)
    # Keep synthetic examples as a fallback for compact or unserved designs.
    # Every such result is visibly marked TESTDATEN in its project name.
    if not woofers:
        return AutomaticDesignResult("impossible", (), ("Kein passender Treiber in der Bibliothek.",),
            ("Weitere Treiber importieren oder die Größen-/Herstellervorgabe lockern.",), 0)
    t = request.panel_thickness_m
    max_internal_l = max(0.0, request.max_width_m-2*t)*max(0.0, request.max_height_m-2*t)*max(
        0.0, request.max_depth_m-2*t)*1000
    if request.target_spl_db is not None:
        ceilings = [driver.sensitivity_db_1w_1m+10*log10(driver.power_rms_w)
                    for driver in woofers if driver.sensitivity_db_1w_1m is not None
                    and driver.power_rms_w is not None]
        if not ceilings or request.target_spl_db > max(ceilings):
            reason = (f"Zielpegel {request.target_spl_db:.0f} dB über der vereinfachten "
                f"thermischen Obergrenze {max(ceilings):.1f} dB der Bibliothek."
                if ceilings else "Zielpegel mit vorhandenen Empfindlichkeitsdaten nicht belegbar.")
            return AutomaticDesignResult("impossible", (),
                (f"Maximales Brutto-Innenvolumen {max_internal_l:.1f} l.", reason),
                ("Zielpegel reduzieren oder einen belastbar dokumentierten Treiber importieren.",
                 "Für mehr Tiefbass Bauraum vergrößern oder das Ziel-F3 erhöhen."), 0)
    designs: list[SpeakerDesign] = []
    rejected: Counter[str] = Counter()
    tested = 0
    volumes_tested: list[float] = []
    two_way = request.way_count == 2 or (request.way_count is None and
        "subwoofer" not in request.speaker_type.casefold() and
        "breitband" not in request.speaker_type.casefold())
    driver_pairs: list[tuple[Driver, tuple[Driver, float] | None]] = []
    for woofer in woofers:
        if request.budget is not None and (woofer.price is None or woofer.currency != "EUR"):
            rejected["Chassispreis für Budgetentwurf fehlt"] += 1
            continue
        if two_way:
            matches = _compatible_tweeters(woofer, tweeters, request.budget)
            if not matches:
                rejected["Kein passender Hochtöner mit überlappendem Frequenzbereich und Preis"] += 1
            driver_pairs.extend((woofer, match) for match in matches)
        else:
            driver_pairs.append((woofer, None))
    for woofer, tweeter_choice in driver_pairs:
        if cancelled and cancelled():
            return AutomaticDesignResult("cancelled", (), (), (), tested)
        if woofer.nominal_impedance_ohm not in (4, 6, 8, 16):
            rejected["Nennimpedanz fehlt oder ist nicht unterstützt"] += 1
            continue
        if woofer.vas_m3 is None:
            rejected["Vas des Tieftöners fehlt"] += 1
            continue
        if two_way and woofer.driver_type == "fullrange":
            continue
        if not (woofer.outer_diameter_m and woofer.cutout_diameter_m and woofer.mounting_depth_m):
            rejected["Treiberabmessungen fehlen"] += 1
            continue
        tweeter, crossover_hz = tweeter_choice if tweeter_choice else (None, 2500.0)
        for enclosure in _enclosures(request):
            if enclosure == "bandpass_4" and two_way:
                continue
            radiators = tuple(item for item in library.entries("passive_radiators")
                if float(item.specs.get("sd_m2", 0)) >= (woofer.sd_m2 or 0))
            if any(not item.is_test_data for item in radiators):
                radiators = tuple(item for item in radiators if not item.is_test_data)
            if enclosure == "passive_radiator" and not radiators:
                rejected["Keine passende Passivmembran mit ausreichender Fläche"] += 1
                continue
            if enclosure in {"sealed", "isobaric_sealed"}:
                volumes = [(q, None, None) for q in profile.qtc_targets if q > woofer.qts]
            else:
                volumes = [(woofer.vas_m3*r*1000*(0.5 if enclosure.startswith("isobaric_") else 1), woofer.fs_hz*fb, None)
                           for r, fb in zip(profile.volume_ratios, (0.95, 0.85, 0.75), strict=True)]
            for volume, tuning, _ in volumes:
                volumes_tested.append(solve_sealed(
                    equivalent_driver(woofer,"series") if enclosure == "isobaric_sealed" else woofer,
                    volume).box_volume_l if enclosure in {"sealed", "isobaric_sealed"} else volume)
                port_diameters = (0.05, 0.06, 0.08) if enclosure in {"bass_reflex", "bandpass_4", "isobaric_vented"} else (0.0,)
                for port_diameter in port_diameters:
                    for width, height in _dimensions(request, woofer, tweeter, enclosure, port_diameter):
                        tested += 1
                        if progress and tested % 20 == 0:
                            progress(min(95, 5+tested//3))
                        if cancelled and cancelled():
                            return AutomaticDesignResult("cancelled", (), (), (), tested)
                        radiator = radiators[0] if enclosure == "passive_radiator" else None
                        pr = radiator.specs if radiator else {}
                        try:
                            estimated_volume_l = (solve_sealed(
                                equivalent_driver(woofer,"series") if enclosure == "isobaric_sealed" else woofer,
                                volume).box_volume_l if enclosure in {"sealed", "isobaric_sealed"} else volume)
                            cfg = EnclosureConfig(enclosure_type=enclosure,
                                target_qtc=volume if enclosure in {"sealed", "isobaric_sealed"} else 0.707,
                                target_volume_l=volume if enclosure not in {"sealed", "isobaric_sealed"} else None,
                                rear_volume_l=max(8.0, volume*0.5), tuning_hz=tuning,
                                port_diameter_mm=port_diameter*1000 if port_diameter else 60,
                                radiator_sd_cm2=float(pr.get("sd_m2", 0.035))*10000,
                                radiator_mms_g=float(pr.get("mms_kg", 0.08))*1000,
                                radiator_fs_hz=float(pr.get("fs_hz", 20)),
                                radiator_qms=float(pr.get("qms", 5)),
                                radiator_xmax_mm=float(pr.get("xmax_m", 0.012))*1000,
                                radiator_cutout_mm=float(pr.get("cutout_diameter_m", 0.23))*1000,
                                radiator_depth_mm=float(pr.get("mounting_depth_m", 0.06))*1000,
                                external_width_mm=width*1000, external_height_mm=height*1000,
                                panel_thickness_mm=request.panel_thickness_m*1000,
                                brace_quantity=1 if estimated_volume_l >= 25 or height >= .55 else 0,
                                input_power_w=request.amplifier_power_w)
                            crossover = CrossoverConfig(enabled=two_way and not request.active,
                                crossover_hz=crossover_hz,
                                woofer_impedance_ohm=(
                                    equivalent_driver(woofer,"series").nominal_impedance_ohm or 8
                                    if enclosure.startswith("isobaric_") else woofer.nominal_impedance_ohm or 8),
                                tweeter_impedance_ohm=tweeter.nominal_impedance_ohm if tweeter else 8,
                                tweeter_attenuation_db=max(0.0,
                                    tweeter.sensitivity_db_1w_1m-
                                    woofer.sensitivity_db_1w_1m) if tweeter and
                                    tweeter.sensitivity_db_1w_1m is not None and
                                    woofer.sensitivity_db_1w_1m is not None else 0,
                                add_woofer_zobel=bool(two_way and not request.active and
                                    woofer.re_ohm and woofer.le_h),
                                round_to_standard_values=two_way and not request.active)
                            test_data = woofer.manufacturer == "TESTDATEN" or (
                                tweeter is not None and tweeter.manufacturer == "TESTDATEN") or (
                                radiator is not None and radiator.is_test_data)
                            accessories = tuple(ProjectAccessory(category="Hardware",
                                reference="TERM1" if item.specs.get("kind") == "terminal" else "DÄMM1",
                                description=item.display(),
                                quantity=max(1, ceil((cfg.target_volume_l or 20)/20))
                                if item.specs.get("kind") == "damping" else 1,
                                specification="125 g / Packung, Richtwert für 20 l"
                                if item.specs.get("kind") == "damping" else
                                "Typ vor Fertigung festlegen",
                                notes="Richtmenge; Einbau und Dämpfung abstimmen"
                                if item.specs.get("kind") == "damping" else "TESTDATEN",
                                unit_price_eur=item.price_eur,
                                price_source_url=str(item.product_url or ""))
                                for item in library.entries("hardware")
                                if item.id in {"demo:terminal", "thomann:visaton-damping"})
                            project = SpeakerProject(name=request.project_name +
                                (" · TESTDATEN" if test_data and "TESTDATEN" not in request.project_name else ""),
                                revision="V-02.03.00", driver=woofer, material=request.material,
                                additional_drivers=(tweeter,) if tweeter else (),
                                tweeter_name=f"{tweeter.manufacturer} {tweeter.model}" if tweeter else "",
                                enclosure=cfg, crossover=crossover,
                                front_elements=_layout(woofer, tweeter, width, height, enclosure, port_diameter),
                                accessories=accessories,
                                notes="Automatisch berechnet. " +
                                ("Synthetische TESTDATEN. " if test_data else "") +
                                "Maße vor Fertigung prüfen.")
                            bundle = calculate_project(project)
                        except (ValueError, ZeroDivisionError, OverflowError) as exc:
                            rejected[f"Solver/Geometrie: {str(exc)[:70]}"] += 1
                            continue
                        if any(issue.severity == "error" for issue in bundle.issues):
                            rejected["Front, Port oder Kammer mechanisch nicht machbar"] += 1
                            continue
                        if any(issue.code in {"XMAX_EXCEEDED", "RADIATOR_XMAX"} for issue in bundle.issues):
                            rejected["Xmax von Treiber oder Passivmembran überschritten"] += 1
                            continue
                        if bundle.cabinet.depth_m > request.max_depth_m+1e-6:
                            rejected["Benötigtes Innenvolumen passt nicht in die maximale Tiefe"] += 1
                            continue
                        outer_l = (bundle.cabinet.width_m*bundle.cabinet.height_m*
                                   bundle.cabinet.depth_m*1000)
                        if request.max_outer_volume_l and outer_l > request.max_outer_volume_l:
                            rejected["Maximales Außenvolumen überschritten"] += 1
                            continue
                        f3 = bundle.sealed.f3_hz if bundle.sealed else (
                            bundle.vented_response.f3_hz if bundle.vented_response else None)
                        if request.target_f3_hz is not None and (f3 is None or f3 > request.target_f3_hz):
                            rejected["Gewünschter Tiefbass ist nicht erreichbar"] += 1
                            continue
                        if f3 is not None and f3 > _reasonable_f3_limit(request):
                            rejected["F3 für den gewählten Lautsprechertyp zu hoch"] += 1
                            continue
                        if f3 is None or (request.sound_profile == "deep_bass" and
                                          f3 > woofer.fs_hz*1.5):
                            rejected["Klangprofil: Tiefbassziel nicht erreicht oder F3 unbekannt"] += 1
                            continue
                        if bundle.vented_response is not None:
                            sim = bundle.vented_response
                            band = _operating_band(request, sim.frequencies_hz)
                            if sim.excursion_mm is not None and woofer.xmax_mm and float(np.max(sim.excursion_mm[band])) > woofer.xmax_mm:
                                rejected["Xmax bei der gewählten Verstärkerleistung überschritten"] += 1
                                continue
                            if sim.port_velocity_m_s is not None and bundle.port and float(np.max(sim.port_velocity_m_s[band])) > 17:
                                rejected["Portgeschwindigkeit über 17 m/s"] += 1
                                continue
                        selected_drivers = (woofer, tweeter) if tweeter else (woofer,)
                        price = (sum(driver.price * (2 if driver is woofer and bundle.coupler else 1)
                                     for driver in selected_drivers if driver.price is not None)
                            if all(driver.price is not None and driver.currency == "EUR"
                                   for driver in selected_drivers) else None)
                        bom = build_bom(bundle)
                        total_price = budget_cost(bom)
                        if request.budget is not None and (total_price is None or total_price > request.budget):
                            rejected["Budget für Material, Weiche, Zubehör und Reserve nicht belegbar oder überschritten"] += 1
                            continue
                        spl_limit = (woofer.sensitivity_db_1w_1m + 10*log10(woofer.power_rms_w)
                                     if woofer.sensitivity_db_1w_1m and woofer.power_rms_w else None)
                        if request.target_spl_db is not None and (spl_limit is None or
                                request.target_spl_db > spl_limit or bundle.sealed is not None):
                            rejected["Gewünschter SPL über thermischer Obergrenze oder Daten fehlen"] += 1
                            continue
                        score, breakdown = _score(bundle, request, profile, total_price)
                        why = [f"{woofer.model}: Geometrie passt und F3 {f3:.1f} Hz.",
                               f"Netto {bundle.target_net_volume_m3*1000:.1f} l; Außen {width*1000:.0f} × {height*1000:.0f} × {bundle.cabinet.depth_m*1000:.0f} mm."]
                        if tweeter:
                            why.append(f"{tweeter.model}: Überlappung bei {crossover_hz:.0f} Hz; "
                                + ("aktiver DSP-Filter extern einzustellen." if request.active else
                                   "passive Weiche vorläufig ohne FRD/ZMA."))
                        if bundle.port:
                            why.append(f"Port Ø {bundle.port.diameter_m*1000:.0f} mm, Länge {bundle.port.physical_length_m*1000:.0f} mm passt in die Kammer.")
                        designs.append(SpeakerDesign("", bundle.project, bundle, woofer, tweeter,
                            score, breakdown, tuple(why), bom, price, spl_limit,
                            two_way and not request.active, total_price))
    if progress:
        progress(100)
    if not designs:
        minimum_l = min(volumes_tested) if volumes_tested else None
        capacity = (f"Maximales Brutto-Innenvolumen {max_internal_l:.1f} l; "
            f"kleinste geprüfte Netto-Variante {minimum_l:.1f} l."
            if minimum_l is not None else f"Maximales Brutto-Innenvolumen {max_internal_l:.1f} l.")
        reasons = (capacity, *(reason for reason, _ in rejected.most_common(4)))
        needed_depth = (2*t+(minimum_l/1000)/(max(1e-9,
            (request.max_width_m-2*t)*(request.max_height_m-2*t)))
            if minimum_l is not None else None)
        suggestions = [f"Tiefe auf mindestens {needed_depth*1000:.0f} mm erhöhen (reiner Volumenunterwert)."
            if needed_depth and needed_depth > request.max_depth_m else
            "Maximale Breite, Höhe oder Tiefe erhöhen.",
                       "Klangprofil oder Ziel-F3 lockern.",
                       "Verstärkerleistung bzw. SPL-Ziel reduzieren oder weitere Komponenten importieren."]
        return AutomaticDesignResult("impossible", (), reasons, tuple(suggestions), tested)
    designs.sort(key=lambda item: (-item.score,
        item.bundle.cabinet.width_m*item.bundle.cabinet.height_m*item.bundle.cabinet.depth_m,
        item.woofer.model, item.project.enclosure.enclosure_type))
    unique: list[SpeakerDesign] = [designs[0]]
    for item in designs[1:]:
        if item.project.enclosure.enclosure_type != unique[0].project.enclosure.enclosure_type:
            unique.append(item)
            break
    for item in designs[1:]:
        signature = (item.woofer.model, item.project.enclosure.enclosure_type)
        if signature not in {(d.woofer.model, d.project.enclosure.enclosure_type) for d in unique}:
            unique.append(item)
        if len(unique) == 3:
            break
    labels = ("A · Favorit", "B · Alternative", "C · Alternative")
    return AutomaticDesignResult("ok", tuple(SpeakerDesign(labels[i], d.project, d.bundle,
        d.woofer, d.tweeter, d.score, d.breakdown, d.reasons, d.bom, d.price,
        d.spl_limit_db, d.provisional_crossover, d.total_price_eur)
        for i, d in enumerate(unique)), (), (), tested)
