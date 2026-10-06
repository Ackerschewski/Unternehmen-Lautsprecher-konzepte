"""Ideal isobaric pair and its explicit sealed coupling chamber.

Two physical layouts share the same acoustic model (identical drivers, one
common moving mass, Vas/2):

* tandem / push-push ("isobaric_*"): both cones face the listener, W2 sits behind
  W1 on a mounting ring, both are driven with the same polarity;
* magnet-to-magnet / push-pull ("compound_push_pull", often called clamshell):
  W2 is mounted reversed on the ring (cone faces the main box, motor reaches into
  the coupler towards W1's motor) and must be wired with reversed polarity so that
  both cones still move in the same physical direction.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import pi

from lautsprecher_konstruktion.drivers.models import Driver


@dataclass(frozen=True)
class Coupler:
    inner_diameter_m: float
    outer_diameter_m: float
    length_m: float
    ring_thickness_m: float
    driver_cutout_m: float
    w2_depth_m: float = 0.0
    w2_reversed: bool = False

    @property
    def w2_extent_m(self) -> float:
        """Signed axial extent of W2 from the rear face of the ring (+ rearwards).

        Tandem: the motor points rearwards into the main box (+depth).
        Magnet-to-magnet: the motor points forwards into the coupler (-depth).
        """
        return -self.w2_depth_m if self.w2_reversed else self.w2_depth_m

    @property
    def rear_extent_m(self) -> float:
        """Distance from the inner face of the front panel to the rearmost point of the pair."""
        return self.length_m + self.ring_thickness_m + (0.0 if self.w2_reversed else self.w2_depth_m)

    @property
    def displaced_volume_m3(self) -> float:
        # The airtight chamber, including its wall and rear mounting ring,
        # occupies this full envelope inside the main cabinet.
        return pi * (self.outer_diameter_m / 2) ** 2 * (self.length_m + self.ring_thickness_m)


def make_coupler(driver: Driver, panel_thickness_m: float,
                 gap_m: float, *, reversed_w2: bool = False) -> Coupler:
    if not driver.cutout_diameter_m or not driver.outer_diameter_m or not driver.mounting_depth_m:
        raise ValueError("Isobarik benötigt Ausschnitt, Außendurchmesser und Einbautiefe beider identischer Chassis.")
    if driver.outer_diameter_m <= driver.cutout_diameter_m:
        raise ValueError("Außendurchmesser muss größer als der Ausschnitt sein.")
    if gap_m < 0.01:
        raise ValueError("Isobarik-Koppelkammer benötigt mindestens 10 mm Freiraum.")
    inner = driver.outer_diameter_m + 0.01
    # Tandem: W1's motor sits in the coupler, W2's cone looks into it from the
    # ring's rear face. Magnet-to-magnet: W2's motor reaches through the ring
    # (its flange is on the rear face), so the coupler also holds W2's motor.
    length = driver.mounting_depth_m + gap_m
    if reversed_w2:
        length += max(driver.mounting_depth_m - panel_thickness_m, 0.0)
    return Coupler(inner, inner + 2*panel_thickness_m, length, panel_thickness_m,
                   driver.cutout_diameter_m, driver.mounting_depth_m, reversed_w2)


def equivalent_driver(driver: Driver, wiring: str) -> Driver:
    """Ideal tandem: 2× moving mass, Vas/2, same Fs and Q factors.

    The electrical equivalent follows from two identical motors under
    series or parallel wiring. Finite chamber compliance is omitted.
    """
    if wiring not in {"series", "parallel"}:
        raise ValueError("Isobarik-Verschaltung muss series oder parallel sein.")
    if driver.vas_m3 is None:
        raise ValueError("Isobarik benötigt Vas.")
    factor = 2.0 if wiring == "series" else 0.5
    updates = {
        "vas_m3": driver.vas_m3 / 2,
        "re_ohm": driver.re_ohm * factor if driver.re_ohm else None,
        "le_h": driver.le_h * factor if driver.le_h is not None else None,
        "nominal_impedance_ohm": driver.nominal_impedance_ohm * factor if driver.nominal_impedance_ohm else None,
        "power_rms_w": driver.power_rms_w * 2 if driver.power_rms_w else None,
        "moving_mass_kg": driver.moving_mass_kg * 2 if driver.moving_mass_kg else None,
        "compliance_m_n": driver.compliance_m_n / 2 if driver.compliance_m_n else None,
        "force_factor_tm": driver.force_factor_tm * (2 if wiring == "series" else 1) if driver.force_factor_tm else None,
    }
    return driver.model_copy(update=updates)
