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


def max_round_port_diameter_m(
    *,
    box_volume_m3: float,
    tuning_hz: float,
    max_length_m: float | None = None,
    end_correction_factor_radius: float = 1.46,
) -> float:
    """Largest round-port diameter for which the pipe stays buildable.

    Physical length L = k*D**2 - c*D with k = c0**2*pi/(4*w**2*V) and c = factor/2.
    Without ``max_length_m`` the limit is L -> 0; with it, L == max_length_m.
    """
    if min(box_volume_m3, tuning_hz) <= 0:
        raise ValueError("Volumen und Abstimmfrequenz müssen positiv sein")
    omega = 2.0 * pi * tuning_hz
    k = SPEED_OF_SOUND_M_S**2 * pi / (4.0 * omega**2 * box_volume_m3)
    c = end_correction_factor_radius / 2.0
    if max_length_m is None or max_length_m <= 0:
        return c / k
    return (c + sqrt(c * c + 4.0 * k * max_length_m)) / (2.0 * k)


def _port_length_from_area(
    *,
    box_volume_m3: float,
    tuning_hz: float,
    area_m2: float,
    equivalent_radius_m: float,
    end_correction_factor_radius: float,
) -> tuple[float, float]:
    if min(box_volume_m3, tuning_hz, area_m2, equivalent_radius_m) <= 0:
        raise ValueError("Volumen, Abstimmfrequenz und Portquerschnitt müssen positiv sein")
    omega = 2.0 * pi * tuning_hz
    effective = (SPEED_OF_SOUND_M_S**2 * area_m2) / (omega**2 * box_volume_m3)
    physical = effective - end_correction_factor_radius * equivalent_radius_m
    if physical <= 0:
        limit = max_round_port_diameter_m(
            box_volume_m3=box_volume_m3, tuning_hz=tuning_hz,
            end_correction_factor_radius=end_correction_factor_radius)
        raise ValueError(
            f"Port nicht berechenbar: bei {tuning_hz:g} Hz in {box_volume_m3*1000:.1f} l ist die "
            f"effektive Länge {effective*1000:.0f} mm kürzer als die Endkorrektur "
            f"({end_correction_factor_radius*equivalent_radius_m*1000:.0f} mm); die Rohrlänge wäre "
            f"{physical*1000:.0f} mm. Port-Querschnitt verkleinern (gleichwertiger Rund-Ø höchstens {limit*1000:.0f} mm), "
            "Abstimmfrequenz senken oder das Kammervolumen verkleinern.")
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
