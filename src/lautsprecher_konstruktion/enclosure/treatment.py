"""Acoustic treatment (damping material) as a project object with per-enclosure placement rules.

A treatment is data first: material, kind, position, area, thickness and a keep-out note. The model
never invents an acoustic effect. Where the solver has no reliable damping model (transmission
lines, horns) the treatment still appears in the bill of materials, build guide and drawings.
"""
from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from lautsprecher_konstruktion.enclosure.damping import VentDamper, WallLining
from lautsprecher_konstruktion.warnings import DesignWarning


class TreatmentKind(StrEnum):
    WALL_LINING = "wall_lining"
    FILL = "fill"
    LOCAL_ABSORBER = "local_absorber"
    VENT_FILL = "vent_fill"
    TL_SEGMENT = "tl_segment"


KIND_LABELS_DE = {
    TreatmentKind.WALL_LINING: "Wandbelag",
    TreatmentKind.FILL: "Füllung",
    TreatmentKind.LOCAL_ABSORBER: "Lokaler Absorber",
    TreatmentKind.VENT_FILL: "Resistive Vent-Füllung",
    TreatmentKind.TL_SEGMENT: "TL-Segment-Dämpfung",
}

POSITION_LABELS_DE = {
    "rear": "Rückwand", "sides": "Seitenwände", "top": "Decke", "bottom": "Boden",
    "volume": "gesamtes Volumen", "port": "Portbereich", "vent": "Vent", "front": "Front",
}

_VENTED = {"bass_reflex", "isobaric_vented", "passive_radiator"}
_CLOSED = {"sealed", "aperiodic", "isobaric_sealed", "compound_push_pull"}
_LINES = {"transmission_line_closed", "transmission_line_open", "transmission_line_tapered", "mltl", "tqwt", "labyrinth"}
_HORNS = {"horn_rear", "horn_folded", "horn_scoop", "horn_exponential", "horn_tractrix", "horn_conical",
          "horn_hyperbolic", "horn_front", "horn_tapped"}
_VENT_TYPES = {"aperiodic", "cardioid"}


class AcousticTreatment(BaseModel):
    id: str
    kind: TreatmentKind
    material: str = "Dämmwolle"
    position: str = "rear"  # rear|sides|top|bottom|volume|port|vent|front, "chamber:front|rear", "segment:<n>"
    area_m2: float | None = Field(default=None, gt=0)
    thickness_m: float = Field(default=0.025, gt=0)
    density_kg_m3: float | None = Field(default=None, gt=0)
    keepout_note: str = ""
    note: str = ""
    unit_price_eur_per_m2: float | None = Field(default=None, ge=0)  # never defaulted: unknown stays unknown
    derived: bool = False  # created by the planner (wall lining, vent insert), not typed in by the user

    @property
    def volume_m3(self) -> float | None:
        return None if self.area_m2 is None else self.area_m2 * self.thickness_m

    @property
    def mass_kg(self) -> float | None:
        volume = self.volume_m3
        return None if volume is None or self.density_kg_m3 is None else volume * self.density_kg_m3

    @property
    def cost_eur(self) -> float | None:
        if self.area_m2 is None or self.unit_price_eur_per_m2 is None:
            return None
        return self.area_m2 * self.unit_price_eur_per_m2

    def label_de(self) -> str:
        where = POSITION_LABELS_DE.get(self.position, self.position.replace("chamber:", "Kammer ").replace("segment:", "Segment "))
        return f"{KIND_LABELS_DE[self.kind]} · {self.material} · {where}"


def derived_treatments(damping: WallLining | None, vent_damper: VentDamper | None) -> tuple[AcousticTreatment, ...]:
    """The planner's own recommendation as treatment objects (so BOM, guide and drawings share one source)."""
    items: list[AcousticTreatment] = []
    if damping is not None:
        items.append(AcousticTreatment(
            id="DÄMM", kind=TreatmentKind.WALL_LINING, material="Dämmwolle oder Schaumstoff", position="rear",
            area_m2=damping.area_m2, thickness_m=damping.thickness_m, derived=True,
            keepout_note="Magnet, Port und Membranweg frei lassen",
            note="Rückwand und Seitenwände hinter dem Chassis"))
    if vent_damper is not None:
        items.append(AcousticTreatment(
            id="VENT-1", kind=TreatmentKind.VENT_FILL, material=f"Einsatz ≈ {vent_damper.specific_resistance_rayl:.0f} Rayl",
            position="vent", area_m2=vent_damper.area_m2, thickness_m=0.02, derived=True,
            note="Strömungswiderstand über der Ventfläche"))
    return tuple(items)


def check_treatments(enclosure_type: str, treatments: tuple[AcousticTreatment, ...]) -> list[DesignWarning]:
    """Placement rules per enclosure family. Errors block the export, info texts state what is not modelled."""
    out: list[DesignWarning] = []
    for t in treatments:
        if t.derived:
            continue
        name = f"{t.id} ({KIND_LABELS_DE[t.kind]})"
        if t.kind is TreatmentKind.VENT_FILL and enclosure_type not in _VENT_TYPES:
            out.append(DesignWarning(code="TREATMENT_VENT_FILL", severity="error",
                message=f"{name}: Eine resistive Vent-Füllung gibt es nur bei aperiodischen und Kardioid-Gehäusen."))
        if enclosure_type in _VENTED:
            if t.position == "port" and t.kind in {TreatmentKind.FILL, TreatmentKind.LOCAL_ABSORBER}:
                out.append(DesignWarning(code="TREATMENT_PORT_BLOCKED", severity="error",
                    message=f"{name}: Keine dichte Füllung vor oder im Port; sie verändert Abstimmung und Strömung. "
                            "Wandbelag stattdessen an Rück- oder Seitenwand legen."))
            elif t.kind is TreatmentKind.FILL:
                out.append(DesignWarning(code="TREATMENT_PORT_KEEPOUT", severity="warning",
                    message=f"{name}: Füllung im Bassreflexgehäuse lose halten und mindestens einen Portdurchmesser "
                            "Abstand zur Portmündung lassen."))
        if enclosure_type.startswith("bandpass") and not t.position.startswith("chamber:"):
            out.append(DesignWarning(code="TREATMENT_CHAMBER", severity="warning",
                message=f"{name}: Beim Bandpass gehört die Dämmung zu einer Kammer (Position „chamber:front“ oder „chamber:rear“)."))
        if enclosure_type in _LINES | _HORNS:
            out.append(DesignWarning(code="TREATMENT_NOT_MODELLED", severity="info",
                message=f"{name}: Für Transmission-Line und Horn berechnet das Programm keine Dämpfungswirkung. "
                        "Material und Position stehen in Stückliste, Anleitung und Zeichnung; Wirkung am Prototyp messen."))
        if enclosure_type in _CLOSED and t.kind is TreatmentKind.FILL:
            out.append(DesignWarning(code="TREATMENT_APPARENT_VOLUME", severity="info",
                message=f"{name}: Füllung wirkt wie zusätzliches scheinbares Volumen. Der Effekt ist nicht eingerechnet; "
                        "Abstimmung am Prototyp prüfen."))
    return out
