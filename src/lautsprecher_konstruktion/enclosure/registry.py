"""One registry for supported enclosure solvers and explicitly planned families."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Status = Literal["SUPPORTED", "EXPERIMENTAL", "PLANNED"]


@dataclass(frozen=True)
class EnclosureType:
    id: str
    label: str
    category: str
    status: Status
    required_parameters: tuple[str, ...]
    supported_driver_types: tuple[str, ...]
    simulations: tuple[str, ...]
    optimization_parameters: tuple[str, ...]
    solver_id: str | None = None
    geometry_id: str | None = None


class EnclosureTypeRegistry:
    def __init__(self) -> None:
        self._types: dict[str, EnclosureType] = {}

    def register(self, entry: EnclosureType) -> None:
        if entry.id in self._types:
            raise ValueError(f"Doppelter Gehäusetyp: {entry.id}")
        if entry.status == "SUPPORTED" and (entry.solver_id is None or entry.geometry_id is None):
            raise ValueError("Unterstützte Typen benötigen Solver und Geometrie.")
        self._types[entry.id] = entry

    def get(self, key: str) -> EnclosureType:
        return self._types[key]

    def all(self) -> tuple[EnclosureType, ...]:
        return tuple(self._types.values())

    def supported(self) -> tuple[EnclosureType, ...]:
        return tuple(item for item in self.all() if item.status == "SUPPORTED")

    def solve(self, key: str, project: object) -> object:
        entry = self.get(key)
        if entry.status != "SUPPORTED":
            raise ValueError(f"{entry.label}: derzeit kein belastbarer Solver ({entry.status}).")
        from lautsprecher_konstruktion.services.design import calculate_project
        return calculate_project(project)


registry = EnclosureTypeRegistry()
_low = ("woofer", "midwoofer", "subwoofer", "fullrange")
for key, label, category, parameters in (
    ("sealed", "Geschlossen", "Standard", ("target_qtc",)),
    ("bass_reflex", "Bassreflex", "Standard", ("target_volume_l", "tuning_hz", "port_type")),
    ("passive_radiator", "Passivmembran", "Standard", ("target_volume_l", "tuning_hz", "radiator_sd_cm2", "radiator_mms_g")),
    ("bandpass_4", "Bandpass 4. Ordnung", "Bandpass", ("target_volume_l", "rear_volume_l", "tuning_hz")),
    ("bandpass_6_parallel", "Bandpass 6. Ordnung parallel", "Bandpass", ("target_volume_l", "rear_volume_l", "tuning_hz", "rear_tuning_hz", "rear_port_diameter_mm")),
    ("isobaric_sealed", "Isobarisch geschlossen", "Isobarik", ("target_qtc", "isobaric_wiring", "isobaric_gap_mm")),
    ("isobaric_vented", "Isobarisch Bassreflex", "Isobarik", ("target_volume_l", "tuning_hz", "isobaric_wiring", "isobaric_gap_mm")),
):
    registry.register(EnclosureType(key, label, category, "SUPPORTED", parameters, _low,
        ("response", "excursion", "group_delay", "impedance"),
        ("volume", "tuning", "dimensions"), key, "assembly_svg"))

for key, label, category in (
    ("infinite_baffle", "Infinite Baffle", "Standard"),
    ("open_baffle", "Open Baffle", "Standard"),
    ("bandpass_6_series", "Bandpass 6. Ordnung seriell", "Bandpass"),
    ("transmission_line_closed", "Transmission Line geschlossen", "Transmission Line"),
    ("transmission_line_open", "Transmission Line offen", "Transmission Line"),
    ("transmission_line_tapered", "Transmission Line verjüngt", "Transmission Line"),
    ("mltl", "Mass Loaded Transmission Line", "Transmission Line"),
    ("tqwt", "TQWT", "Transmission Line"),
    ("horn_front", "Frontloaded Horn", "Horn"),
    ("horn_rear", "Rearloaded Horn", "Horn"),
    ("horn_folded", "Folded Horn", "Horn"),
    ("horn_tapped", "Tapped Horn", "Horn"),
    ("horn_scoop", "Scoop", "Horn"),
    ("horn_exponential", "Exponentialhorn", "Horn"),
    ("horn_tractrix", "Tractrixhorn", "Horn"),
    ("horn_conical", "Konisches Horn", "Horn"),
    ("horn_hyperbolic", "Hyperbolisches Horn", "Horn"),
    ("compound_push_pull", "Compound / Push Pull", "Sonstige"),
    ("dipole", "Dipol", "Sonstige"),
    ("cardioid", "Kardioid", "Sonstige"),
    ("aperiodic", "Aperiodisch", "Sonstige"),
    ("labyrinth", "Labyrinth", "Sonstige"),
):
    registry.register(EnclosureType(key, label, category, "PLANNED", (), _low, (), ()))
