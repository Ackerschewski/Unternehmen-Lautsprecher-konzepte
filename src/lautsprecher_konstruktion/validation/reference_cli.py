"""Command line: run all solver reference cases, show the diff against the reviewed baseline.

    python -m lautsprecher_konstruktion.validation.reference_cli            # fast suite, exit code 1 on any failure
    python -m lautsprecher_konstruktion.validation.reference_cli --json out.json
    python -m lautsprecher_konstruktion.validation.reference_cli --accept-baseline --reason "..." --reviewer "Name"
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from lautsprecher_konstruktion.validation.cases import build_cases
from lautsprecher_konstruktion.validation.reference import (
    accept_baseline,
    load_baseline,
    render_diff,
    run_cases,
    run_to_json,
)

BASELINE_PATH = Path(__file__).resolve().parents[3] / "data" / "validation" / "reference_baseline.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lautsprecher_konstruktion.validation.reference_cli",
                                     description="Referenzfälle aller Solver prüfen und mit dem Referenzstand vergleichen.")
    parser.add_argument("--full", action="store_true", help="auch langsame Fälle ausführen")
    parser.add_argument("--json", type=Path, help="Ergebnis maschinenlesbar speichern")
    parser.add_argument("--baseline", type=Path, default=BASELINE_PATH, help="Referenzstand (JSON)")
    parser.add_argument("--accept-baseline", action="store_true", help="aktuelle Zahlen als neuen Referenzstand übernehmen")
    parser.add_argument("--reason", default="", help="technische Begründung für einen neuen Referenzstand")
    parser.add_argument("--reviewer", default="", help="Name der prüfenden Person")
    args = parser.parse_args(argv)

    baseline = load_baseline(args.baseline)
    run = run_cases(build_cases(), baseline, include_slow=args.full)
    if args.accept_baseline:
        try:
            accept_baseline(run, args.baseline, reason=args.reason, reviewer=args.reviewer)
        except ValueError as exc:
            print(f"Fehler: {exc}", file=sys.stderr)
            return 2
        print(f"Referenzstand geschrieben: {args.baseline}")
        return 0
    print(render_diff(run))
    if baseline is None:
        print("Hinweis: Es gibt noch keinen Referenzstand; --accept-baseline legt ihn mit Begründung an.", file=sys.stderr)
    elif baseline.get("definition_hash") != run.definition_hash:
        print("Die Definition der Referenzfälle weicht vom geprüften Referenzstand ab; ein Review ist nötig.", file=sys.stderr)
        return 2
    if args.json:
        args.json.write_text(json.dumps(run_to_json(run), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0 if run.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
