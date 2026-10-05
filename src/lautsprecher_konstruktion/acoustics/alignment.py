"""Compare candidate vented alignments; these are suggestions, not final designs."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from lautsprecher_konstruktion.acoustics.vented import simulate_vented
from lautsprecher_konstruktion.drivers.models import Driver
from lautsprecher_konstruktion.enclosure.ports import PortDesign, round_port


@dataclass(frozen=True)
class AlignmentOption:
    name: str
    volume_l: float
    tuning_hz: float
    f3_hz: float | None
    outer_volume_l: float
    port: PortDesign
    max_port_velocity_m_s: float | None
    max_excursion_mm: float | None
    max_group_delay_ms: float
    warnings: tuple[str, ...]


def suggest_alignments(driver: Driver, *, input_power_w: float = 1.0,
                       external_width_m: float = 0.34, external_height_m: float = 0.56,
                       panel_thickness_m: float = 0.018) -> tuple[AlignmentOption, ...]:
    """Grid-search three distinct size/depth preferences with physical port checks."""
    if input_power_w <= 0:
        raise ValueError("input_power_w must be positive")
    inner_area = (external_width_m-2*panel_thickness_m)*(external_height_m-2*panel_thickness_m)
    if inner_area <= 0:
        raise ValueError("cabinet width/height are too small")
    profiles = (("Kompakt", 0.55, 1.00), ("Ausgewogen", 0.85, 0.88),
                ("Tiefbass", 1.25, 0.75))
    vas = driver.require_vas_m3()
    candidates: list[AlignmentOption] = []
    for name, volume_ratio, tuning_ratio in profiles:
        ranked: list[tuple[float, AlignmentOption]] = []
        for vm in (0.85, 1.0, 1.15):
            volume = vas * volume_ratio * vm
            for fm in (0.92, 1.0, 1.08):
                fb = driver.fs_hz * tuning_ratio * fm
                for diameter in (0.06, 0.08, 0.10):
                    try:
                        port = round_port(box_volume_m3=volume, tuning_hz=fb, diameter_m=diameter)
                        sim = simulate_vented(driver, volume, port, input_power_w)
                    except ValueError:
                        continue
                    gross = volume + driver.displacement_m3 + port.displacement_m3
                    depth = gross / inner_area + 2*panel_thickness_m
                    outside_l = external_width_m*external_height_m*depth*1000
                    speed = (float(np.max(sim.port_velocity_m_s)) if sim.port_velocity_m_s is not None else None)
                    excursion = (float(np.max(sim.excursion_mm)) if sim.excursion_mm is not None else None)
                    gd = float(np.max(sim.group_delay_ms[(sim.frequencies_hz >= 20) & (sim.frequencies_hz <= 150)]))
                    warnings = []
                    if speed is not None and speed >= 17:
                        warnings.append("Portgeschwindigkeit über 17 m/s beim gewählten Leistungspegel")
                    if excursion is not None and driver.xmax_mm is not None and excursion > driver.xmax_mm:
                        warnings.append("Xmax überschritten")
                    if port.physical_length_m > depth-2*panel_thickness_m:
                        warnings.append("Port muss gefaltet oder anders platziert werden")
                    score = (abs(volume/vas-volume_ratio)*3
                             + abs(fb/driver.fs_hz-tuning_ratio)*3
                             + (speed or 0)/35 + len(warnings)*0.5
                             + (sim.f3_hz or 200)/200)
                    ranked.append((score, AlignmentOption(name, volume*1000, fb, sim.f3_hz,
                        outside_l, port, speed, excursion, gd, tuple(warnings))))
        if not ranked:
            raise ValueError(f"no valid {name} alignment found")
        candidates.append(min(ranked, key=lambda item: item[0])[1])
    return tuple(candidates)
