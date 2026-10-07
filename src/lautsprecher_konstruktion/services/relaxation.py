"""Small, targeted relaxation search for requests without a feasible design.

The tested candidates that only miss adjustable limits (depth, outer volume, F3, budget, SPL) define the
needed values. The smallest normalised change vectors become proposals, and every proposal is re-run through
the real design service before it is shown: no proposal without a feasibility check.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from math import ceil, floor, sqrt

from lautsprecher_konstruktion.library.store import ComponentLibrary
from lautsprecher_konstruktion.services.automatic import (
    AutomaticDesignRequest,
    AutomaticDesignResult,
    automatic_design,
)

MAX_PROPOSALS = 3
MAX_VERIFICATIONS = 6

# key -> (request attribute, UI field name, unit, label, scale to request unit, direction)
_FIELDS: dict[str, tuple[str, str, str, str, float]] = {
    "depth": ("max_depth_m", "max_depth", "mm", "Tiefe", 1000.0),
    "outer_l": ("max_outer_volume_l", "max_volume", "l", "Außenvolumen", 1.0),
    "f3": ("target_f3_hz", "target_f3", "Hz", "Ziel-F3", 1.0),
    "budget": ("budget", "budget", "€", "Budget", 1.0),
    "spl": ("target_spl_db", "target_spl", "dB", "Max-SPL-Ziel", 1.0),
}


@dataclass(frozen=True)
class Change:
    field: str  # UI field name
    label: str
    old: float
    new: float
    unit: str


@dataclass(frozen=True)
class Relaxation:
    changes: tuple[Change, ...]
    cost: float  # normalised size of the change vector (0 = nothing changed)
    designs_found: int

    def text(self) -> str:
        parts = [f"{c.label} {c.old:.0f} → {c.new:.0f} {c.unit}" for c in self.changes]
        found = f"{self.designs_found} Entwurf" if self.designs_found == 1 else f"{self.designs_found} Entwürfe"
        return " · ".join(parts) + f"  ⇒ {found} geprüft"


def _current(request: AutomaticDesignRequest, key: str) -> float | None:
    attr, _field, _unit, _label, scale = _FIELDS[key]
    value = getattr(request, attr)
    return None if value is None else float(value) * scale


def _proposal(request: AutomaticDesignRequest, miss: dict[str, float]) -> tuple[tuple[Change, ...], float] | None:
    changes: list[Change] = []
    cost = 0.0
    for key, raw in miss.items():
        if key not in _FIELDS:
            return None
        current = _current(request, key)
        if current is None or current <= 0:
            return None
        _attr, field, unit, label, scale = _FIELDS[key]
        if key == "spl":
            new = float(floor(-raw))  # stored negated; round down so the limit still holds
            if new >= current:
                continue
        else:
            value = raw * scale
            new = float(ceil(value / 5) * 5) if key == "depth" else float(ceil(value))
            if new <= current:
                continue
        changes.append(Change(field, label, current, new, unit))
        cost += ((new - current) / current) ** 2
    if not changes:
        return None
    return tuple(changes), sqrt(cost)


def _applied(request: AutomaticDesignRequest, changes: tuple[Change, ...]) -> AutomaticDesignRequest:
    update: dict[str, float] = {}
    for change in changes:
        key = next(k for k, v in _FIELDS.items() if v[1] == change.field)
        attr, _f, _u, _l, scale = _FIELDS[key]
        update[attr] = change.new / scale
    return request.model_copy(update=update)


def find_relaxations(
    request: AutomaticDesignRequest,
    library: ComponentLibrary,
    result: AutomaticDesignResult,
    *,
    runner: Callable[[AutomaticDesignRequest, ComponentLibrary], AutomaticDesignResult] = automatic_design,
    max_results: int = MAX_PROPOSALS,
    max_verifications: int = MAX_VERIFICATIONS,
) -> tuple[Relaxation, ...]:
    """Up to ``max_results`` verified combined changes, smallest first. Empty when nothing feasible was found."""
    seen: dict[tuple[tuple[str, float], ...], tuple[tuple[Change, ...], float]] = {}
    for miss in result.soft_misses:
        proposal = _proposal(request, miss)
        if proposal is None:
            continue
        signature = tuple(sorted((c.field, c.new) for c in proposal[0]))
        if signature not in seen or proposal[1] < seen[signature][1]:
            seen[signature] = proposal
    ranked = sorted(seen.values(), key=lambda item: (item[1], len(item[0])))
    # offer different kinds of change first (distinct sets of limits), then fill up with clearly different values
    chosen: list[tuple[tuple[Change, ...], float]] = []
    used_sets: set[frozenset[str]] = set()
    for changes, cost in ranked:
        fields = frozenset(c.field for c in changes)
        if fields not in used_sets:
            used_sets.add(fields)
            chosen.append((changes, cost))
    for changes, cost in ranked:
        if len(chosen) >= max_verifications:
            break
        if all(changes is not other and (frozenset(c.field for c in changes) != frozenset(c.field for c in other)
                                         or any(abs(a.new - b.new) / a.new > 0.10 for a, b in zip(
                                             sorted(changes, key=lambda c: c.field), sorted(other, key=lambda c: c.field), strict=True)))
               for other, _ in chosen):
            chosen.append((changes, cost))
    verified: list[Relaxation] = []
    for changes, cost in chosen[:max_verifications]:
        outcome = runner(_applied(request, changes), library)
        if outcome.status != "impossible" and outcome.designs:
            verified.append(Relaxation(changes, cost, len(outcome.designs)))
        if len(verified) >= max_results:
            break
    return tuple(verified)
