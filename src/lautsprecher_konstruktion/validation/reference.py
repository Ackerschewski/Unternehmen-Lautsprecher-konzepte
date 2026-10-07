"""Reference cases, the harness that runs them, and the quantitative diff against the stored baseline.

A reference case computes metrics through the real solver and compares them with expectations that
carry value, unit, tolerance and source. The baseline stores the numbers the solvers produced at the last
reviewed state; it can only be rewritten with an explicit reason (``accept_baseline``).
"""
from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from lautsprecher_konstruktion.validation.trust import CaseKind, TrustLevel, earned_trust

HARNESS_VERSION = 1
REGRESSION_REL = 1e-6
REGRESSION_ABS = 1e-9


class Outcome(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"          # outside tolerance
    MISSING = "MISSING"    # the solver did not deliver the metric
    NOT_FINITE = "NOT_FINITE"  # NaN or Inf


@dataclass(frozen=True)
class ReferenceExpectation:
    metric: str
    value: float
    unit: str
    tolerance_kind: str          # "abs" or "rel"
    tolerance: float
    source: str                  # where the expected value comes from
    justification: str = ""      # why this tolerance is technically reasonable

    def limit(self) -> float:
        return self.tolerance if self.tolerance_kind == "abs" else abs(self.value) * self.tolerance


@dataclass(frozen=True)
class ReferenceCase:
    case_id: str
    solver_id: str
    title: str
    kind: CaseKind
    compute: Callable[[], dict[str, float]]
    expectations: tuple[ReferenceExpectation, ...]
    slow: bool = False

    def definition(self) -> dict[str, Any]:
        """Everything that defines the case except the code: used to detect silent changes of references."""
        return {"id": self.case_id, "solver": self.solver_id, "kind": self.kind.value,
                "expect": [[e.metric, e.value, e.unit, e.tolerance_kind, e.tolerance, e.source] for e in self.expectations]}


@dataclass(frozen=True)
class ValidationDifference:
    case_id: str
    solver_id: str
    metric: str
    unit: str
    expected: float
    actual: float | None
    tolerance: float
    error: float | None
    outcome: Outcome
    baseline: float | None = None
    baseline_delta: float | None = None
    regression: bool = False

    @property
    def relative_error(self) -> float | None:
        return None if self.error is None or self.expected == 0 else abs(self.error) / abs(self.expected)


@dataclass
class ValidationRun:
    harness_version: int
    differences: list[ValidationDifference] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)  # case id -> exception text (a crash is a failure)
    definition_hash: str = ""
    cases: tuple[ReferenceCase, ...] = ()

    @property
    def failed(self) -> list[ValidationDifference]:
        return [d for d in self.differences if d.outcome is not Outcome.PASS]

    @property
    def regressions(self) -> list[ValidationDifference]:
        return [d for d in self.differences if d.regression]

    @property
    def ok(self) -> bool:
        return not self.failed and not self.errors and not self.regressions

    def case_passed(self, case_id: str) -> bool:
        rows = [d for d in self.differences if d.case_id == case_id]
        return bool(rows) and case_id not in self.errors and all(d.outcome is Outcome.PASS for d in rows)

    def solver_passed_kinds(self, solver_id: str) -> list[CaseKind]:
        return [c.kind for c in self.cases if c.solver_id == solver_id and self.case_passed(c.case_id)]

    def earned_trust(self, solver_id: str) -> TrustLevel:
        return earned_trust(self.solver_passed_kinds(solver_id))


def definition_hash(cases: tuple[ReferenceCase, ...]) -> str:
    payload = json.dumps(sorted((c.definition() for c in cases), key=lambda d: str(d["id"])), sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _compare(case: ReferenceCase, exp: ReferenceExpectation, actual: float | None) -> ValidationDifference:
    limit = exp.limit()
    if actual is None:
        return ValidationDifference(case.case_id, case.solver_id, exp.metric, exp.unit, exp.value, None, limit, None, Outcome.MISSING)
    if not math.isfinite(actual):
        return ValidationDifference(case.case_id, case.solver_id, exp.metric, exp.unit, exp.value, actual, limit, None, Outcome.NOT_FINITE)
    error = actual - exp.value
    outcome = Outcome.PASS if abs(error) <= limit else Outcome.FAIL
    return ValidationDifference(case.case_id, case.solver_id, exp.metric, exp.unit, exp.value, actual, limit, error, outcome)


def run_cases(cases: tuple[ReferenceCase, ...], baseline: dict[str, Any] | None = None, *, include_slow: bool = False) -> ValidationRun:
    """Run the reference cases; compare with the baseline numbers when given."""
    selected = tuple(c for c in cases if include_slow or not c.slow)
    run = ValidationRun(HARNESS_VERSION, definition_hash=definition_hash(selected), cases=selected)
    stored: dict[str, dict[str, float]] = (baseline or {}).get("values", {})
    for case in selected:
        try:
            produced = case.compute()
        except Exception as exc:  # noqa: BLE001 - a crashing solver is a failed case, never a skipped one
            run.errors[case.case_id] = f"{type(exc).__name__}: {exc}"
            for exp in case.expectations:
                run.differences.append(_compare(case, exp, None))
            continue
        for exp in case.expectations:
            diff = _compare(case, exp, produced.get(exp.metric))
            old = stored.get(case.case_id, {}).get(exp.metric)
            if old is not None and diff.actual is not None and math.isfinite(diff.actual):
                delta = diff.actual - old
                moved = abs(delta) > max(REGRESSION_ABS, REGRESSION_REL * abs(old))
                diff = ValidationDifference(**{**diff.__dict__, "baseline": old, "baseline_delta": delta, "regression": moved})
            run.differences.append(diff)
    return run


def baseline_from(run: ValidationRun) -> dict[str, float | str | int | dict[str, dict[str, float]]]:
    values: dict[str, dict[str, float]] = {}
    for d in run.differences:
        if d.actual is not None and math.isfinite(d.actual):
            values.setdefault(d.case_id, {})[d.metric] = d.actual
    return {"harness_version": run.harness_version, "definition_hash": run.definition_hash, "values": values}


def load_baseline(path: Path) -> dict[str, Any] | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def accept_baseline(run: ValidationRun, path: Path, *, reason: str, reviewer: str) -> None:
    """Rewrite the baseline. Needs a reason and a name: golden values are never regenerated just to turn tests green."""
    if len(reason.strip()) < 15 or not reviewer.strip():
        raise ValueError("Ein neuer Referenzstand braucht eine technische Begründung (mindestens 15 Zeichen) und einen Namen.")
    if run.errors or any(d.outcome is not Outcome.PASS for d in run.differences):
        raise ValueError("Ein Referenzstand mit fehlgeschlagenen Fällen kann nicht übernommen werden.")
    old = load_baseline(path) or {}
    history = list(old.get("history", []))
    history.append({"definition_hash": run.definition_hash, "reason": reason.strip(), "reviewer": reviewer.strip()})
    data = baseline_from(run)
    data["history"] = history  # type: ignore[assignment]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def run_to_json(run: ValidationRun) -> dict[str, Any]:
    """Machine-readable result for CI and the QA infrastructure."""
    return {
        "harness_version": run.harness_version, "definition_hash": run.definition_hash, "ok": run.ok,
        "errors": run.errors,
        "results": [{"case": d.case_id, "solver": d.solver_id, "metric": d.metric, "unit": d.unit, "expected": d.expected,
                     "actual": d.actual, "tolerance": d.tolerance, "error": d.error, "outcome": d.outcome.value,
                     "baseline": d.baseline, "baseline_delta": d.baseline_delta, "regression": d.regression}
                    for d in run.differences],
    }


def render_diff(run: ValidationRun) -> str:
    """Plain-text diff: failed expectations and regressions against the baseline, with numbers."""
    lines: list[str] = []
    for d in run.differences:
        if d.outcome is not Outcome.PASS:
            lines.append(f"FAIL  {d.case_id} · {d.metric}: erwartet {d.expected:g} {d.unit}, erhalten "
                         f"{'—' if d.actual is None else format(d.actual, 'g')} (Toleranz ±{d.tolerance:g}) [{d.outcome.value}]")
        elif d.regression and d.baseline is not None and d.baseline_delta is not None:
            lines.append(f"DRIFT {d.case_id} · {d.metric}: Referenzstand {d.baseline:g} → {d.actual:g} (Δ {d.baseline_delta:+g} {d.unit})")
    for case_id, text in run.errors.items():
        lines.append(f"CRASH {case_id}: {text}")
    return "\n".join(lines) if lines else "Alle Referenzfälle bestanden, keine Abweichung vom Referenzstand."
