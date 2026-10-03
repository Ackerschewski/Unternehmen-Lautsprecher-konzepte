from __future__ import annotations

from dataclasses import dataclass
from math import pi

SPEED_OF_SOUND_M_S = 343.0


@dataclass(frozen=True)
class RoundPortResult:
    tuning_hz: float
    box_volume_m3: float
    port_diameter_m: float
    port_area_m2: float
    physical_length_m: float
    effective_length_m: float

    @property
    def physical_length_cm(self) -> float:
        return self.physical_length_m * 100.0


def round_port_length(
    *,
    box_volume_m3: float,
    tuning_hz: float,
    port_diameter_m: float,
    end_correction_factor_radius: float = 1.46,
    speed_of_sound_m_s: float = SPEED_OF_SOUND_M_S,
) -> RoundPortResult:
    """Calculate the physical length of one circular Helmholtz port.

    The default end correction approximates a common one-flanged / one-free-end
    arrangement. Final construction must choose a geometry-specific correction.
    """
    if box_volume_m3 <= 0 or tuning_hz <= 0 or port_diameter_m <= 0:
        raise ValueError("box volume, tuning and port diameter must be positive")

    radius = port_diameter_m / 2.0
    area = pi * radius * radius
    omega = 2.0 * pi * tuning_hz
    effective_length = (speed_of_sound_m_s**2 * area) / (omega**2 * box_volume_m3)
    physical_length = effective_length - end_correction_factor_radius * radius

    if physical_length <= 0:
        raise ValueError(
            "Calculated physical port length is non-positive; choose a different "
            "diameter, tuning frequency or enclosure volume."
        )

    return RoundPortResult(
        tuning_hz=tuning_hz,
        box_volume_m3=box_volume_m3,
        port_diameter_m=port_diameter_m,
        port_area_m2=area,
        physical_length_m=physical_length,
        effective_length_m=effective_length,
    )
