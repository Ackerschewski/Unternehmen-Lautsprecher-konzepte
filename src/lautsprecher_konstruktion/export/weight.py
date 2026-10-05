"""Planning weight of the cabinet shell.

Only the plate material is estimated. Chassis, crossover, damping, terminals and
glue carry no mass data in the driver model and are deliberately excluded rather
than guessed. Densities come from typical trade ranges and are shown as a range.
"""
from __future__ import annotations

from dataclasses import dataclass

from lautsprecher_konstruktion.enclosure.materials import MATERIALS
from lautsprecher_konstruktion.services.design import DesignBundle


@dataclass(frozen=True)
class WeightEstimate:
    material: str
    volume_m3: float
    low_kg: float | None
    high_kg: float | None

    @property
    def mid_kg(self) -> float | None:
        if self.low_kg is None or self.high_kg is None:
            return None
        return (self.low_kg + self.high_kg) / 2

    def describe(self) -> str:
        if self.low_kg is None or self.high_kg is None:
            return f"Gehäusegewicht nicht berechenbar: keine Dichte für „{self.material}“ hinterlegt."
        return (f"Gehäuse ohne Chassis, Weiche und Dämmung ca. {self.low_kg:.1f}–{self.high_kg:.1f} kg "
                f"(Plattenvolumen {self.volume_m3 * 1000:.2f} l; Richtdichte, Datenblatt prüfen)")


def plate_volume_m3(bundle: DesignBundle) -> float:
    volume = sum(p.quantity * p.width_m * p.height_m * p.thickness_m for p in bundle.panels)
    if bundle.brace:
        volume += bundle.brace.material_volume_each_m3 * bundle.brace.quantity
    return volume


def estimate_weight(bundle: DesignBundle) -> WeightEstimate:
    material = bundle.project.material
    volume = plate_volume_m3(bundle)
    spec = next((m for m in MATERIALS if m.name == material), None)
    if spec is None or spec.density_range_kg_m3 is None:
        return WeightEstimate(material, volume, None, None)
    low, high = spec.density_range_kg_m3
    return WeightEstimate(material, volume, volume * low, volume * high)
