"""Validation matrix (Markdown and JSON) generated from descriptors, reference cases and a run: nothing typed in by hand."""
from __future__ import annotations

import json

from lautsprecher_konstruktion.validation.cases import build_cases
from lautsprecher_konstruktion.validation.reference import ReferenceCase, ValidationRun, run_cases
from lautsprecher_konstruktion.validation.solvers import SOLVER_DESCRIPTORS
from lautsprecher_konstruktion.validation.trust import CaseKind, TrustLevel

KIND_DE = {CaseKind.LITERATURE: "Literatur", CaseKind.ANALYTIC: "Formel", CaseKind.LIMIT: "Grenzfall",
           CaseKind.CONSISTENCY: "Konsistenz", CaseKind.PROTOTYPE: "Prototyp"}


def matrix_data(run: ValidationRun | None = None, cases: tuple[ReferenceCase, ...] | None = None) -> dict[str, object]:
    cases = cases if cases is not None else build_cases()
    run = run if run is not None else run_cases(cases)
    rows = []
    for solver_id, d in SOLVER_DESCRIPTORS.items():
        mine = [c for c in cases if c.solver_id == solver_id]
        passed = [c for c in mine if run.case_passed(c.case_id)]
        rows.append({
            "solver": solver_id, "family": d.family, "model_version": d.model_version, "granted": d.trust.name,
            "earned": run.earned_trust(solver_id).name, "cases": len(mine), "passed": len(passed),
            "kinds": sorted({KIND_DE[c.kind] for c in passed}), "case_ids": [c.case_id for c in mine],
            "sources": list(d.sources), "limitations": [f"{item.scope}: {item.text}" for item in d.limitations],
        })
    return {"definition_hash": run.definition_hash, "ok": run.ok, "solvers": rows}


def matrix_markdown(run: ValidationRun | None = None, cases: tuple[ReferenceCase, ...] | None = None) -> str:
    data = matrix_data(run, cases)
    rows = data["solvers"]
    assert isinstance(rows, list)
    counts = {level.name: sum(1 for r in rows if r["granted"] == level.name) for level in TrustLevel}
    lines = ["# Validierungsmatrix", "",
             ("Erzeugt mit `python -m lautsprecher_konstruktion.validation.matrix`. Alle Angaben stammen aus den Solver-Deskriptoren, "
              "den Referenzfällen und einem Lauf; nichts ist von Hand eingetragen."), "",
             f"Stand der Fall-Definitionen: `{data['definition_hash']}` · alle Fälle bestanden: **{'ja' if data['ok'] else 'NEIN'}**", "",
             "## Übersicht", "",
             "| Stufe | Anzahl Gehäusetypen |", "|---|---|"]
    lines += [f"| {level.label_de} | {counts[level.name]} |" for level in TrustLevel]
    lines += ["", ("„Vergeben“ ist die Stufe, die das Programm zeigt; „Belegt“ ist die höchste Stufe, die die bestandenen Fälle rechtfertigen. "
                   "Vergeben wird nie mehr als belegt, kann aber weniger sein, wenn das Modell Näherungen enthält, die für Nutzer:innen zählen."), "",
              "## Matrix", "", "| Gehäusetyp | Solver | Vergeben | Belegt | Fälle (bestanden) | Art der bestandenen Fälle |", "|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['family']} | `{r['solver']}` | {TrustLevel[str(r['granted'])].label_de} | {TrustLevel[str(r['earned'])].label_de} | "
                     f"{r['passed']}/{r['cases']} | {', '.join(r['kinds']) or '–'} |")
    lines += ["", "## Quellen und Grenzen je Gehäusetyp", ""]
    for r in rows:
        lines += [f"### {r['family']} (`{r['solver']}`)", "", "Quellen:", *[f"- {s}" for s in r["sources"]], "", "Bekannte Grenzen:",
                  *[f"- {item}" for item in r["limitations"]], ""]
    lines += ["## Beförderungsregeln", "",
              ("- **Experimentell → Formel geprüft:** Mindestens ein ANALYTIC- oder LIMIT-Fall besteht, dessen Erwartung in `independent.py` "
               "ohne Aufruf des geprüften Solvers berechnet wird; die Näherungen des Modells sind als Grenzen dokumentiert und für die "
               "Nutzer:innen unerheblich oder begrenzt."),
              ("- **Formel geprüft → Referenz geprüft:** Mindestens ein LITERATURE-Fall mit Quelle, Zahlenwert und begründeter Toleranz besteht."),
              ("- **Referenz geprüft → Am Prototyp validiert:** Ein gespeicherter Messdatensatz eines gebauten Prototyps (Fall der Art PROTOTYPE) "
               "stimmt innerhalb der dokumentierten Toleranz überein. Übereinstimmung mit Literatur genügt dafür nie."),
              ("- **Zurückstufung:** Besteht ein Fall nicht mehr, gilt sofort die belegte Stufe; ein Referenzstand wird nur mit Begründung und Namen "
               "erneuert (`--accept-baseline`)."), ""]
    return "\n".join(lines)


if __name__ == "__main__":  # pragma: no cover - documentation helper
    from pathlib import Path

    root = Path(__file__).resolve().parents[3] / "docs" / "application"
    run = run_cases(build_cases())
    (root / "VALIDATION_MATRIX.md").write_text(matrix_markdown(run), encoding="utf-8")
    (root / "VALIDATION_MATRIX.json").write_text(json.dumps(matrix_data(run), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(root / "VALIDATION_MATRIX.md")
