"""Family strategies prepare acoustic targets before shared cabinet construction.

Each strategy owns only its enclosure physics. Shared layout, geometry and
manufacturing checks stay in services.design. New families register here after
they have a defensible solver and drawing strategy.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import pi, sqrt
from typing import Protocol

from lautsprecher_konstruktion.acoustics.sealed import SealedResult, solve_sealed
from lautsprecher_konstruktion.drivers.models import Driver
from lautsprecher_konstruktion.enclosure.isobaric import equivalent_driver
from lautsprecher_konstruktion.enclosure.passive_radiator import (
    PassiveRadiatorDesign,
    design_passive_radiator,
)
from lautsprecher_konstruktion.enclosure.ports import PortDesign, round_port, slot_port
from lautsprecher_konstruktion.project.models import EnclosureConfig


@dataclass(frozen=True)
class EnclosurePreparation:
    target_net_volume_m3: float
    sealed: SealedResult | None = None
    port: PortDesign | None = None
    radiator: PassiveRadiatorDesign | None = None
    resonator: PortDesign | None = None
    front_volume_m3: float | None = None
    rear_volume_m3: float | None = None
    rear_port: PortDesign | None = None
    port_resistance_pa_s_m3: float | None = None


class EnclosureStrategy(Protocol):
    def prepare(self, cfg: EnclosureConfig, driver: Driver) -> EnclosurePreparation: ...


def _front_volume(cfg: EnclosureConfig) -> float:
    if cfg.target_volume_l is None or cfg.tuning_hz is None:
        raise ValueError("Volumen und Abstimmfrequenz fehlen")
    return cfg.target_volume_l/1000


def _port(cfg: EnclosureConfig, front_volume: float) -> PortDesign:
    assert cfg.tuning_hz is not None
    if cfg.port_type == "round":
        return round_port(box_volume_m3=front_volume, tuning_hz=cfg.tuning_hz,
                          diameter_m=cfg.port_diameter_mm/1000)
    return slot_port(box_volume_m3=front_volume, tuning_hz=cfg.tuning_hz,
                     width_m=cfg.slot_width_mm/1000, height_m=cfg.slot_height_mm/1000)


class SealedStrategy:
    def prepare(self, cfg: EnclosureConfig, driver: Driver) -> EnclosurePreparation:
        sealed = solve_sealed(driver, cfg.target_qtc)
        return EnclosurePreparation(sealed.box_volume_m3, sealed=sealed)


class BassReflexStrategy:
    def prepare(self, cfg: EnclosureConfig, driver: Driver) -> EnclosurePreparation:
        front = _front_volume(cfg)
        port = _port(cfg, front)
        return EnclosurePreparation(front, port=port, resonator=port,
                                    front_volume_m3=front)


class AperiodicStrategy:
    def prepare(self, cfg: EnclosureConfig, driver: Driver) -> EnclosurePreparation:
        if cfg.target_volume_l is None:
            raise ValueError("Aperiodisch benötigt ein Netto-Zielvolumen")
        volume = cfg.target_volume_l/1000
        diameter = cfg.port_diameter_mm/1000
        area = pi*(diameter/2)**2
        thickness = (cfg.front_thickness_mm or cfg.panel_thickness_mm)*cfg.front_layers/1000
        effective_length = thickness+1.46*diameter/2
        reference_hz = 343/(2*pi)*sqrt(area/(volume*effective_length))
        port = PortDesign("round",area,thickness,effective_length,
                          reference_hz,diameter_m=diameter)
        compliance = volume/(1.204*343**2)
        resistance = (cfg.aperiodic_resistance_pa_s_m3 or
                      1/(2*pi*driver.fs_hz*compliance))
        return EnclosurePreparation(volume, port=port, resonator=port,
                                    front_volume_m3=volume,
                                    port_resistance_pa_s_m3=resistance)


class CardioidStrategy(AperiodicStrategy):
    def prepare(self, cfg: EnclosureConfig, driver: Driver) -> EnclosurePreparation:
        # Same resistive rear cavity, but the vent exits the back and its
        # far-field phase is resolved separately in the radiation model.
        rear_cfg = cfg.model_copy(update={"front_thickness_mm": cfg.back_thickness_mm or
                                           cfg.panel_thickness_mm,"front_layers": 1})
        return super().prepare(rear_cfg,driver)


class FoldedLineStrategy:
    def prepare(self, cfg: EnclosureConfig, driver: Driver) -> EnclosurePreparation:
        if cfg.target_volume_l is None or cfg.tuning_hz is None:
            raise ValueError("Liniengehäuse benötigt Netto-Volumen und Ziel-Viertelwellenfrequenz")
        if driver.outer_diameter_m is None and driver.cutout_diameter_m is None:
            raise ValueError("Für die Linienfaltung fehlt der Treiber-Außendurchmesser")
        return EnclosurePreparation(cfg.target_volume_l/1000)


class PassiveRadiatorStrategy:
    def prepare(self, cfg: EnclosureConfig, driver: Driver) -> EnclosurePreparation:
        front = _front_volume(cfg)
        assert cfg.tuning_hz is not None
        radiator = design_passive_radiator(box_volume_m3=front, tuning_hz=cfg.tuning_hz,
            area_m2=cfg.radiator_sd_cm2/10000, stock_mass_kg=cfg.radiator_mms_g/1000,
            free_air_fs_hz=cfg.radiator_fs_hz, qms=cfg.radiator_qms,
            cutout_diameter_m=cfg.radiator_cutout_mm/1000,
            mounting_depth_m=cfg.radiator_depth_mm/1000,
            xmax_m=cfg.radiator_xmax_mm/1000)
        resonator = PortDesign(shape="passive_radiator", area_m2=radiator.area_m2,
            physical_length_m=radiator.mounting_depth_m,
            effective_length_m=radiator.acoustic_mass_kg_m4*radiator.area_m2/1.204,
            tuning_hz=cfg.tuning_hz, diameter_m=cfg.radiator_cutout_mm/1000)
        return EnclosurePreparation(front, radiator=radiator, resonator=resonator,
                                    front_volume_m3=front)


class Bandpass4Strategy:
    def prepare(self, cfg: EnclosureConfig, driver: Driver) -> EnclosurePreparation:
        front = _front_volume(cfg)
        rear = cfg.rear_volume_l/1000
        port = _port(cfg, front)
        return EnclosurePreparation(front+rear, port=port, resonator=port,
                                    front_volume_m3=front, rear_volume_m3=rear)


class Bandpass6ParallelStrategy:
    def prepare(self, cfg: EnclosureConfig, driver: Driver) -> EnclosurePreparation:
        front = _front_volume(cfg)
        rear = cfg.rear_volume_l/1000
        if cfg.rear_tuning_hz is None:
            raise ValueError("Bandpass 6 parallel benötigt eine zweite Abstimmfrequenz für die Rückkammer")
        front_port = _port(cfg, front)
        rear_port = round_port(box_volume_m3=rear, tuning_hz=cfg.rear_tuning_hz,
                               diameter_m=cfg.rear_port_diameter_mm/1000)
        return EnclosurePreparation(front+rear, port=front_port, rear_port=rear_port,
                                    resonator=front_port, front_volume_m3=front,
                                    rear_volume_m3=rear)


class Bandpass6SeriesStrategy:
    def prepare(self, cfg: EnclosureConfig, driver: Driver) -> EnclosurePreparation:
        front = _front_volume(cfg)
        rear = cfg.rear_volume_l/1000
        if cfg.rear_tuning_hz is None:
            raise ValueError("Bandpass 6 seriell benötigt die interne Kanalabstimmung")
        external_port = _port(cfg, front)
        internal_port = round_port(box_volume_m3=rear, tuning_hz=cfg.rear_tuning_hz,
                                   diameter_m=cfg.rear_port_diameter_mm/1000)
        return EnclosurePreparation(front+rear, port=external_port,
                                    rear_port=internal_port, resonator=external_port,
                                    front_volume_m3=front, rear_volume_m3=rear)


class IsobaricSealedStrategy:
    def prepare(self, cfg: EnclosureConfig, driver: Driver) -> EnclosurePreparation:
        pair = equivalent_driver(driver, cfg.isobaric_wiring)
        sealed = solve_sealed(pair, cfg.target_qtc)
        return EnclosurePreparation(sealed.box_volume_m3, sealed=sealed)


class CompoundPushPullStrategy(IsobaricSealedStrategy):
    """Ideal two-driver coupling; opposite mounting/polarity is a build detail."""


class FrontHornStrategy(SealedStrategy):
    def prepare(self, cfg: EnclosureConfig, driver: Driver) -> EnclosurePreparation:
        if cfg.tuning_hz is None:
            raise ValueError("Front-Horn benötigt eine Ziel-Grenzfrequenz")
        return super().prepare(cfg,driver)


class IsobaricVentedStrategy:
    def prepare(self, cfg: EnclosureConfig, driver: Driver) -> EnclosurePreparation:
        front = _front_volume(cfg)
        port = _port(cfg, front)
        return EnclosurePreparation(front, port=port, resonator=port,
                                    front_volume_m3=front)


STRATEGIES: dict[str, EnclosureStrategy] = {
    "sealed": SealedStrategy(),
    "bass_reflex": BassReflexStrategy(),
    "aperiodic": AperiodicStrategy(),
    "cardioid": CardioidStrategy(),
    "passive_radiator": PassiveRadiatorStrategy(),
    "bandpass_4": Bandpass4Strategy(),
    "bandpass_6_parallel": Bandpass6ParallelStrategy(),
    "bandpass_6_series": Bandpass6SeriesStrategy(),
    "isobaric_sealed": IsobaricSealedStrategy(),
    "compound_push_pull": CompoundPushPullStrategy(),
    "horn_front": FrontHornStrategy(),
    "isobaric_vented": IsobaricVentedStrategy(),
    **{key: FoldedLineStrategy() for key in (
        "transmission_line_closed", "transmission_line_open",
        "transmission_line_tapered", "mltl", "tqwt", "labyrinth",
        "horn_rear", "horn_folded", "horn_scoop", "horn_exponential",
        "horn_tractrix", "horn_conical", "horn_hyperbolic")},
}


def prepare_enclosure(cfg: EnclosureConfig, driver: Driver) -> EnclosurePreparation:
    try:
        strategy = STRATEGIES[cfg.enclosure_type]
    except KeyError as exc:
        raise ValueError(f"Kein Solver für {cfg.enclosure_type}") from exc
    return strategy.prepare(cfg, driver)
