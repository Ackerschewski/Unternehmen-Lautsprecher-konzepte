from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MaterialSpec:
    name: str
    density_kg_m3: float | None
    standard_thicknesses_mm: tuple[float, ...]
    note: str = ""
    # Typical trade range for planning only; the supplied sheet's datasheet takes precedence.
    density_range_kg_m3: tuple[float, float] | None = None


MATERIALS = (
    MaterialSpec("MDF", None, (12, 16, 18, 19, 22, 25),
                 "Dichte ist hersteller- und chargenabhängig; Materialdatenblatt prüfen.",
                 (680.0, 800.0)),
    MaterialSpec("Birke Multiplex", None, (12, 15, 18, 21, 24),
                 "Tatsächliche Dicke am gelieferten Material messen.",
                 (640.0, 720.0)),
    MaterialSpec("Spanplatte", None, (16, 18, 19, 22),
                 "Kanten und Schraubhalt sind konstruktionstechnisch zu prüfen.",
                 (600.0, 750.0)),
)
