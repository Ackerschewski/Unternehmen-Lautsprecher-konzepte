"""Nearest E12 nominal values in SI units; availability is not implied."""
from __future__ import annotations

from dataclasses import replace
from math import floor, log10

from lautsprecher_konstruktion.crossover.passive import CrossoverDesign

E12 = (1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2)


def nearest_e12(value: float) -> float:
    if value <= 0:
        raise ValueError("Standardwert muss positiv sein")
    exponent = floor(log10(value))
    options = (base*10**power for power in (exponent-1, exponent, exponent+1)
               for base in E12)
    return min(options, key=lambda option: (abs(log10(option/value)), option))


def round_crossover_to_e12(design: CrossoverDesign) -> CrossoverDesign:
    components = tuple(replace(component, value_si=nearest_e12(component.value_si),
        target_value_si=component.value_si) if component.kind in
        {"inductor", "capacitor", "resistor"} else component
        for component in design.components)
    return replace(design, components=components,
        notes=design.notes+("E12-Nennwerte gewählt; reale Verfügbarkeit und Toleranzen prüfen.",))
