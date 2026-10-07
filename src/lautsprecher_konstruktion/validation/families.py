"""Buildable parameter sets per enclosure family for reference and consistency cases (small demo woofer)."""
from __future__ import annotations

from functools import lru_cache

from lautsprecher_konstruktion.project.demo import demo_project
from lautsprecher_konstruktion.project.models import CrossoverConfig
from lautsprecher_konstruktion.services.design import DesignBundle, calculate_project

_PORT_BOX = {"target_volume_l": 45.0, "tuning_hz": 35.0, "external_width_mm": 340.0,
             "external_height_mm": 560.0, "port_diameter_mm": 80.0}
_GENERIC = {"target_volume_l": 200.0, "tuning_hz": 60.0, "external_height_mm": 1200.0,
            "external_width_mm": 450.0, "brace_quantity": 0}
FAMILY_PARAMETERS: dict[str, dict[str, float]] = {
    "sealed": {"external_width_mm": 340.0, "external_height_mm": 560.0},
    "bass_reflex": _PORT_BOX,
    "bandpass_4": {**_PORT_BOX, "rear_volume_l": 30.0},
    "bandpass_6_parallel": {**_PORT_BOX, "rear_volume_l": 30.0, "rear_tuning_hz": 50.0},
    "bandpass_6_series": {**_PORT_BOX, "rear_volume_l": 50.0, "rear_tuning_hz": 30.0, "rear_port_diameter_mm": 75.0},
    "passive_radiator": {"target_volume_l": 45.0, "tuning_hz": 35.0, "external_width_mm": 340.0,
                         "external_height_mm": 560.0, "radiator_mms_g": 60.0},
    "isobaric_sealed": {"external_width_mm": 400.0, "external_height_mm": 450.0, "target_qtc": 0.5, "target_volume_l": 70.0},
    "compound_push_pull": {"external_width_mm": 400.0, "external_height_mm": 450.0, "target_qtc": 0.5, "target_volume_l": 70.0},
    "isobaric_vented": {"external_width_mm": 400.0, "external_height_mm": 600.0, "target_qtc": 0.5,
                        "target_volume_l": 70.0, "tuning_hz": 35.0},
    "mltl": {"target_volume_l": 120.0, "tuning_hz": 25.0, "external_height_mm": 1200.0,
             "external_width_mm": 400.0, "port_diameter_mm": 40.0},
    "infinite_baffle": {"target_volume_l": 700.0},
    "horn_front": {"tuning_hz": 150.0, "external_width_mm": 450.0, "external_height_mm": 750.0, "target_qtc": 0.5},
}


def family_project(solver_id: str, **overrides: float) -> object:
    from lautsprecher_konstruktion.project.models import SpeakerProject
    project = demo_project()
    enclosure = project.enclosure.model_copy(update={
        "enclosure_type": solver_id, **_GENERIC, **FAMILY_PARAMETERS.get(solver_id, {}), **overrides})
    result: SpeakerProject = project.model_copy(update={
        "enclosure": enclosure, "front_elements": (), "tweeter_name": "", "crossover": CrossoverConfig(enabled=False)})
    return result


@lru_cache(maxsize=64)
def _solve_cached(solver_id: str, overrides: tuple[tuple[str, float], ...]) -> DesignBundle:
    from lautsprecher_konstruktion.project.models import SpeakerProject
    project = family_project(solver_id, **dict(overrides))
    assert isinstance(project, SpeakerProject)
    return calculate_project(project)


def solve_family(solver_id: str, **overrides: float) -> DesignBundle:
    """Solved design of a family with its buildable parameters; results are shared between cases (read-only)."""
    return _solve_cached(solver_id, tuple(sorted(overrides.items())))
