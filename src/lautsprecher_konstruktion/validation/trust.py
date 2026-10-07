"""Trust levels and solver descriptors: what a model is, where it comes from, what it may be used for.

The declared trust of a solver can never exceed what its reference cases earn (see ``earned_trust``);
prototype validation is a level of its own and cannot be inferred from literature agreement.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum


class TrustLevel(IntEnum):
    """Ordered: a higher number is more trust."""

    EXPERIMENTAL = 0
    FORMULA_VERIFIED = 1
    REFERENCE_VERIFIED = 2
    PROTOTYPE_VALIDATED = 3

    @property
    def label_de(self) -> str:
        return {0: "Experimentell", 1: "Formel geprüft", 2: "Referenz geprüft", 3: "Am Prototyp validiert"}[int(self)]

    @property
    def meaning_de(self) -> str:
        return {
            0: "Näherungsmodell ohne belastbaren Referenzfall. Ergebnisse als Richtwert behandeln und am Prototyp messen.",
            1: "Gleichungen sind gegen unabhängig berechnete Grenzfälle oder geschlossene Formeln geprüft.",
            2: "Zahlenwerte stimmen mit veröffentlichten Tabellen oder Literaturwerten innerhalb dokumentierter Toleranz überein.",
            3: "Das Modell wurde mit einer Messung an einem gebauten Prototyp verglichen und stimmt innerhalb der Toleranz.",
        }[int(self)]


class CaseKind(StrEnum):
    LITERATURE = "literature"      # published table or number
    ANALYTIC = "analytic"          # closed-form relation re-implemented independently of the solver
    LIMIT = "limit"                # physical limit case with a known answer
    CONSISTENCY = "consistency"    # internal sanity (units, finiteness, passivity); proves nothing about accuracy
    PROTOTYPE = "prototype"        # stored measurement of a built prototype


# What a passing case of each kind can earn.
KIND_TRUST = {
    CaseKind.LITERATURE: TrustLevel.REFERENCE_VERIFIED,
    CaseKind.ANALYTIC: TrustLevel.FORMULA_VERIFIED,
    CaseKind.LIMIT: TrustLevel.FORMULA_VERIFIED,
    CaseKind.CONSISTENCY: TrustLevel.EXPERIMENTAL,
    CaseKind.PROTOTYPE: TrustLevel.PROTOTYPE_VALIDATED,
}


GENERIC_SCOPES = frozenset({"Aussteuerung", "Abstrahlung", "Verluste"})


@dataclass(frozen=True)
class ModelLimitation:
    scope: str  # e.g. "Frequenzbereich", "Geometrie", "Verluste"
    text: str


@dataclass(frozen=True)
class SolverDescriptor:
    solver_id: str
    family: str
    model_version: str
    trust: TrustLevel
    equations: str                       # one honest sentence on what is computed
    sources: tuple[str, ...]             # where the equations come from
    limitations: tuple[ModelLimitation, ...]
    conventions: str = ""                # F3, volume, Fb definitions this solver uses

    @property
    def main_limitation(self) -> ModelLimitation | None:
        """The limit that matters most for this family: the first one that is not a generic small-signal/half-space note."""
        specific = [item for item in self.limitations if item.scope not in GENERIC_SCOPES]
        pool = specific or list(self.limitations)
        return pool[0] if pool else None

    @property
    def is_experimental(self) -> bool:
        return self.trust is TrustLevel.EXPERIMENTAL


def earned_trust(kinds_passed: list[CaseKind]) -> TrustLevel:
    """Highest trust the passing reference cases justify."""
    return max((KIND_TRUST[k] for k in kinds_passed), default=TrustLevel.EXPERIMENTAL)


def trust_record(descriptor: SolverDescriptor) -> dict[str, object]:
    """Machine-readable trust status written into exports; states what the model is and is not."""
    return {
        "solver_id": descriptor.solver_id, "family": descriptor.family, "model_version": descriptor.model_version,
        "trust": descriptor.trust.name, "trust_label": descriptor.trust.label_de, "meaning": descriptor.trust.meaning_de,
        "equations": descriptor.equations, "sources": list(descriptor.sources), "conventions": descriptor.conventions,
        "limitations": [{"scope": item.scope, "text": item.text} for item in descriptor.limitations],
        "note": "Modellstatus des Programms zum Zeitpunkt des Exports; ältere Projektdateien speichern ihn nicht.",
    }
