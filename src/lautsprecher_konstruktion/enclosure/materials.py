from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MaterialSpec:
    name: str
    density_kg_m3: float | None
    standard_thicknesses_mm: tuple[float, ...]
    note: str = ""


MATERIALS = (
    MaterialSpec("MDF", None, (12, 16, 18, 19, 22, 25),
                 "Dichte ist hersteller- und chargenabhängig; Materialdatenblatt prüfen."),
    MaterialSpec("Birke Multiplex", None, (12, 15, 18, 21, 24),
                 "Tatsächliche Dicke am gelieferten Material messen."),
    MaterialSpec("Spanplatte", None, (16, 18, 19, 22),
                 "Kanten und Schraubhalt sind konstruktionstechnisch zu prüfen."),
)
