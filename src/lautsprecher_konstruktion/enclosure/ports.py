from __future__ import annotations

from dataclasses import dataclass
from math import pi, sqrt

from lautsprecher_konstruktion.acoustics.bass_reflex import SPEED_OF_SOUND_M_S
from lautsprecher_konstruktion.presentation import de


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


def round_port_diameter_for_length_m(
    *,
    box_volume_m3: float,
    tuning_hz: float,
    length_m: float = 0.0,
    end_correction_factor_radius: float = 1.46,
) -> float:
    """Round-port diameter whose physical length equals ``length_m``.

    L = k*D**2 - c*D with k = c0**2*pi/(4*w**2*V) and c = factor/2. A larger
    diameter gives a longer port, so ``length_m=0`` is the *smallest* buildable
    diameter and a chamber depth limit gives the *largest* diameter that fits.
    """
    if min(box_volume_m3, tuning_hz) <= 0:
        raise ValueError("Volumen und Abstimmfrequenz müssen positiv sein")
    omega = 2.0 * pi * tuning_hz
    k = SPEED_OF_SOUND_M_S**2 * pi / (4.0 * omega**2 * box_volume_m3)
    c = end_correction_factor_radius / 2.0
    return (c + sqrt(c * c + 4.0 * k * max(length_m, 0.0))) / (2.0 * k)


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
        limit = round_port_diameter_for_length_m(
            box_volume_m3=box_volume_m3, tuning_hz=tuning_hz,
            end_correction_factor_radius=end_correction_factor_radius)
        raise ValueError(
            f"Der berechnete Port benötigt bei Fb = {de(tuning_hz, 1)} Hz in {de(box_volume_m3*1000, 1)} l "
            f"Nettovolumen eine effektive Länge von {de(effective*1000)} mm; die Endkorrektur allein beträgt "
            f"aber schon {de(end_correction_factor_radius*equivalent_radius_m*1000)} mm "
            f"(Rohrlänge {de(physical*1000)} mm). Port-Querschnitt vergrößern (gleichwertiger Rund-Ø "
            f"mindestens {de(limit*1000)} mm), Fb senken oder das Volumen verkleinern.")
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
