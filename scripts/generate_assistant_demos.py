"""Generate five reproducible assistant scenarios from bundled TESTDATEN."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from lautsprecher_konstruktion.export.package import export_project_package
from lautsprecher_konstruktion.library.store import ComponentLibrary
from lautsprecher_konstruktion.services.automatic import AutomaticDesignRequest, automatic_design


SCENARIOS = {
    "01_regallautsprecher": AutomaticDesignRequest(project_name="Kompakter 2-Wege-Regallautsprecher",
        speaker_type="Regallautsprecher", max_width_m=.23, max_height_m=.42, max_depth_m=.31),
    "02_bassreflex_subwoofer": AutomaticDesignRequest(project_name="Bassreflex-Subwoofer",
        speaker_type="Subwoofer", enclosure_preference="bass_reflex", sound_profile="deep_bass",
        max_width_m=.4, max_height_m=.6, max_depth_m=.6),
    "03_geschlossener_subwoofer": AutomaticDesignRequest(project_name="Geschlossener Subwoofer",
        speaker_type="Subwoofer", enclosure_preference="sealed",
        max_width_m=.4, max_height_m=.6, max_depth_m=.6),
    "04_standlautsprecher": AutomaticDesignRequest(project_name="Standlautsprecher",
        speaker_type="Standlautsprecher", max_width_m=.34, max_height_m=.95, max_depth_m=.45),
    "05_nicht_machbar": AutomaticDesignRequest(project_name="Unmögliche Anforderung",
        speaker_type="Subwoofer", sound_profile="deep_bass", max_width_m=.3,
        max_height_m=.3, max_depth_m=.2, target_f3_hz=20, target_spl_db=120),
}


def generate(output: Path, export: bool = False) -> None:
    library = ComponentLibrary()
    output.mkdir(parents=True, exist_ok=True)
    for name, request in SCENARIOS.items():
        folder = output / name
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "anfrage.json").write_text(request.model_dump_json(indent=2), encoding="utf-8")
        result = automatic_design(request, library)
        report = {"status": result.status, "candidates_tested": result.candidates_tested,
            "rejection_reasons": result.rejection_reasons,
            "suggested_constraint_changes": result.suggested_constraint_changes,
            "designs": [{"label": d.label, "score": d.score, "woofer": d.woofer.model,
                "tweeter": d.tweeter.model if d.tweeter else None,
                "enclosure": d.project.enclosure.enclosure_type,
                "dimensions_mm": [d.bundle.cabinet.width_m*1000,
                    d.bundle.cabinet.height_m*1000, d.bundle.cabinet.depth_m*1000],
                "score_breakdown": [metric.__dict__ for metric in d.breakdown]}
                for d in result.designs]}
        (folder / "ergebnis.json").write_text(json.dumps(report, indent=2,
            ensure_ascii=False), encoding="utf-8")
        if result.designs:
            (folder / "projekt.json").write_text(result.designs[0].project.model_dump_json(indent=2),
                encoding="utf-8")
            if export:
                export_project_package(result.designs[0].bundle, folder / "fertigungsbeispiel")
        print(name, result.status, len(result.designs))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "examples" / "assistant")
    parser.add_argument("--export", action="store_true")
    args = parser.parse_args()
    generate(args.output, args.export)
