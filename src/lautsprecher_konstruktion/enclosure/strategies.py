"""Family strategies prepare acoustic targets before shared cabinet construction.

Each strategy owns only its enclosure physics. Shared layout, geometry and
manufacturing checks stay in services.design. New families register here after
they have a defensible solver and drawing strategy.
"""
from __future__ import annotations

from dataclasses import dataclass
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


class IsobaricSealedStrategy:
    def prepare(self, cfg: EnclosureConfig, driver: Driver) -> EnclosurePreparation:
        pair = equivalent_driver(driver, cfg.isobaric_wiring)
        sealed = solve_sealed(pair, cfg.target_qtc)
        return EnclosurePreparation(sealed.box_volume_m3, sealed=sealed)


class IsobaricVentedStrategy:
    def prepare(self, cfg: EnclosureConfig, driver: Driver) -> EnclosurePreparation:
        front = _front_volume(cfg)
        port = _port(cfg, front)
        return EnclosurePreparation(front, port=port, resonator=port,
                                    front_volume_m3=front)


STRATEGIES: dict[str, EnclosureStrategy] = {
    "sealed": SealedStrategy(),
    "bass_reflex": BassReflexStrategy(),
    "passive_radiator": PassiveRadiatorStrategy(),
    "bandpass_4": Bandpass4Strategy(),
    "bandpass_6_parallel": Bandpass6ParallelStrategy(),
    "isobaric_sealed": IsobaricSealedStrategy(),
    "isobaric_vented": IsobaricVentedStrategy(),
}


def prepare_enclosure(cfg: EnclosureConfig, driver: Driver) -> EnclosurePreparation:
    try:
        strategy = STRATEGIES[cfg.enclosure_type]
    except KeyError as exc:
        raise ValueError(f"Kein Solver für {cfg.enclosure_type}") from exc
    return strategy.prepare(cfg, driver)
