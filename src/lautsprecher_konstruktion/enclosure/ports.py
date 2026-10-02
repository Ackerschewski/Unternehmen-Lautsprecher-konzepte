from __future__ import annotations

from dataclasses import dataclass
from math import pi, sqrt

from lautsprecher_konstruktion.acoustics.bass_reflex import SPEED_OF_SOUND_M_S


@dataclass(frozen=True)
class PortDesign:
    shape: str
    area_m2: float
    physical_length_m: float
    effective_length_m: float
    tuning_hz: float
    width_m: float | None = None
    height_m: float | None = None
    diameter_m: float | None = None

    @property
    def displacement_m3(self) -> float:
        return self.area_m2 * self.physical_length_m


def _port_length_from_area(
    *,
    box_volume_m3: float,
    tuning_hz: float,
    area_m2: float,
    equivalent_radius_m: float,
    end_correction_factor_radius: float,
) -> tuple[float, float]:
    if min(box_volume_m3, tuning_hz, area_m2, equivalent_radius_m) <= 0:
        raise ValueError("port design inputs must be positive")
    omega = 2.0 * pi * tuning_hz
    effective = (SPEED_OF_SOUND_M_S**2 * area_m2) / (omega**2 * box_volume_m3)
    physical = effective - end_correction_factor_radius * equivalent_radius_m
    if physical <= 0:
        raise ValueError("selected port geometry produces a non-positive physical length")
    return physical, effective


def round_port(
    *,
    box_volume_m3: float,
    tuning_hz: float,
    diameter_m: float,
    end_correction_factor_radius: float = 1.46,
) -> PortDesign:
    radius = diameter_m / 2.0
    area = pi * radius**2
    physical, effective = _port_length_from_area(
        box_volume_m3=box_volume_m3,
        tuning_hz=tuning_hz,
        area_m2=area,
        equivalent_radius_m=radius,
        end_correction_factor_radius=end_correction_factor_radius,
    )
    return PortDesign(
        shape="round",
        area_m2=area,
        physical_length_m=physical,
        effective_length_m=effective,
        tuning_hz=tuning_hz,
        diameter_m=diameter_m,
    )


def slot_port(
    *,
    box_volume_m3: float,
    tuning_hz: float,
    width_m: float,
    height_m: float,
    end_correction_factor_radius: float = 1.46,
) -> PortDesign:
    if width_m <= 0 or height_m <= 0:
        raise ValueError("slot port dimensions must be positive")
    area = width_m * height_m
    equivalent_radius = sqrt(area / pi)
    physical, effective = _port_length_from_area(
        box_volume_m3=box_volume_m3,
        tuning_hz=tuning_hz,
        area_m2=area,
        equivalent_radius_m=equivalent_radius,
        end_correction_factor_radius=end_correction_factor_radius,
    )
    return PortDesign(
        shape="slot",
        area_m2=area,
        physical_length_m=physical,
        effective_length_m=effective,
        tuning_hz=tuning_hz,
        width_m=width_m,
        height_m=height_m,
    )
