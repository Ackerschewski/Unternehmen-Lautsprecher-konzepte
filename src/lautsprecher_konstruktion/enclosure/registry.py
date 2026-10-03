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
    ("aperiodic", "Aperiodisch", "Standard", ("target_volume_l", "port_diameter_mm", "aperiodic_resistance_pa_s_m3")),
    ("passive_radiator", "Passivmembran", "Standard", ("target_volume_l", "tuning_hz", "radiator_sd_cm2", "radiator_mms_g")),
    ("bandpass_4", "Bandpass 4. Ordnung", "Bandpass", ("target_volume_l", "rear_volume_l", "tuning_hz")),
    ("bandpass_6_parallel", "Bandpass 6. Ordnung parallel", "Bandpass", ("target_volume_l", "rear_volume_l", "tuning_hz", "rear_tuning_hz", "rear_port_diameter_mm")),
    ("bandpass_6_series", "Bandpass 6. Ordnung seriell", "Bandpass", ("target_volume_l", "rear_volume_l", "tuning_hz", "rear_tuning_hz", "rear_port_diameter_mm")),
    ("isobaric_sealed", "Isobarisch geschlossen", "Isobarik", ("target_qtc", "isobaric_wiring", "isobaric_gap_mm")),
    ("compound_push_pull", "Compound / Push Pull", "Isobarik", ("target_qtc", "isobaric_wiring", "isobaric_gap_mm")),
    ("isobaric_vented", "Isobarisch Bassreflex", "Isobarik", ("target_volume_l", "tuning_hz", "isobaric_wiring", "isobaric_gap_mm")),
    ("transmission_line_closed", "Transmission Line geschlossen", "Transmission Line", ("target_volume_l", "tuning_hz", "external_height_mm")),
    ("transmission_line_open", "Transmission Line offen", "Transmission Line", ("target_volume_l", "tuning_hz", "external_height_mm")),
    ("transmission_line_tapered", "Transmission Line verjüngt", "Transmission Line", ("target_volume_l", "tuning_hz", "external_height_mm")),
    ("mltl", "Mass Loaded Transmission Line", "Transmission Line", ("target_volume_l", "tuning_hz", "port_diameter_mm")),
    ("tqwt", "TQWT", "Transmission Line", ("target_volume_l", "tuning_hz", "external_height_mm")),
    ("labyrinth", "Labyrinth", "Sonstige", ("target_volume_l", "tuning_hz", "external_height_mm")),
    ("infinite_baffle", "Infinite Baffle / Wandeinbau", "Standard", ("target_volume_l", "external_width_mm", "external_height_mm")),
    ("open_baffle", "Open Baffle", "Standard", ("external_width_mm", "external_height_mm")),
    ("dipole", "Dipol / H-Frame", "Sonstige", ("external_width_mm", "external_height_mm", "baffle_wing_depth_mm")),
    ("cardioid", "Passiv-Kardioid", "Sonstige", ("target_volume_l", "port_diameter_mm", "aperiodic_resistance_pa_s_m3", "cardioid_delay_ms")),
    ("horn_rear", "Rearloaded Horn (segmentiert)", "Horn", ("target_volume_l", "tuning_hz", "external_height_mm")),
    ("horn_folded", "Folded Horn (segmentiert)", "Horn", ("target_volume_l", "tuning_hz", "external_height_mm")),
    ("horn_scoop", "Scoop (segmentiert)", "Horn", ("target_volume_l", "tuning_hz", "external_height_mm")),
    ("horn_exponential", "Exponentialhorn (segmentiert)", "Horn", ("target_volume_l", "tuning_hz", "external_height_mm")),
    ("horn_tractrix", "Tractrixhorn (segmentiert)", "Horn", ("target_volume_l", "tuning_hz", "external_height_mm")),
    ("horn_conical", "Konisches Horn (segmentiert)", "Horn", ("target_volume_l", "tuning_hz", "external_height_mm")),
    ("horn_hyperbolic", "Hyperbolisches Horn (segmentiert)", "Horn", ("target_volume_l", "tuning_hz", "external_height_mm")),
    ("horn_front", "Frontloaded Horn", "Horn", ("target_qtc", "tuning_hz", "external_width_mm", "external_height_mm")),
    ("horn_tapped", "Tapped Horn (2 Läufe)", "Horn", ("target_volume_l", "tuning_hz", "external_width_mm", "external_height_mm")),
):
    registry.register(EnclosureType(key, label, category, "SUPPORTED", parameters, _low,
        ("response", "excursion", "group_delay", "impedance"),
        ("volume", "tuning", "dimensions"), key, "assembly_svg"))
