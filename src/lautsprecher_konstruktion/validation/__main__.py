"""Command line: python -m lautsprecher_konstruktion.validation project.json --frd m.frd --zma m.zma"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pydantic import ValidationError

from lautsprecher_konstruktion.crossover.measurements import load_frd, load_zma
from lautsprecher_konstruktion.project.models import SpeakerProject
from lautsprecher_konstruktion.services.design import calculate_project
from lautsprecher_konstruktion.validation.prototype import compare_prototype, render_report_markdown


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lautsprecher_konstruktion.validation",
                                     description="Simulation mit Prototypmessung vergleichen.")
    parser.add_argument("project", type=Path, help="Projektdatei (.json)")
    parser.add_argument("--frd", type=Path, help="gemessener Frequenzgang (FRD)")
    parser.add_argument("--zma", type=Path, help="gemessene Impedanz (ZMA)")
    parser.add_argument("--band", nargs=2, type=float, metavar=("VON_HZ", "BIS_HZ"), default=(20.0, 300.0),
                        help="Vergleichsband für den Frequenzgang")
    parser.add_argument("--no-align", action="store_true", help="Pegelversatz nicht angleichen")
    parser.add_argument("--out", type=Path, help="Bericht als Markdown speichern")
    args = parser.parse_args(argv)
    if args.frd is None and args.zma is None:
        print("Fehler: mindestens --frd oder --zma angeben.", file=sys.stderr)
        return 2
    try:
        project = SpeakerProject.model_validate_json(args.project.read_text(encoding="utf-8"))
        bundle = calculate_project(project)
        report = compare_prototype(
            bundle, frd=load_frd(args.frd) if args.frd else None,
            zma=load_zma(args.zma) if args.zma else None,
            band_hz=(args.band[0], args.band[1]), align_level=not args.no_align)
    except (OSError, ValidationError, ValueError) as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 2
    text = render_report_markdown(report)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
