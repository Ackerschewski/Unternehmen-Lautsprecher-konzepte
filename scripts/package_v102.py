"""Create a local, GitHub-free Windows test delivery for V-01.02.00."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from lautsprecher_konstruktion.export.package import export_project_package
from lautsprecher_konstruktion.library.store import ComponentLibrary
from lautsprecher_konstruktion.services.automatic import AutomaticDesignRequest, automatic_design


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT.parents[1] / "outputs" / "V-01.02.00"
DIST = ROOT / "dist" / "Lautsprecher-Konstruktion_V-01.02.00"


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "BUILD_REPORT_V-01.02.00.md", OUTPUT)
    shutil.copy2(ROOT / "dimension_preview.png", OUTPUT / "Vorschau_Massblatt.png")
    (OUTPUT / "START_HIER.txt").write_text(
        "Lautsprecher Konstruktion V-01.02.00\n\n"
        "1. Windows-ZIP vollständig entpacken.\n"
        "2. Lautsprecher-Konstruktion_V-01.02.00.exe starten; _internal muss daneben bleiben.\n"
        "3. Entwurf erstellen. Zeichnung / Innenaufbau und Maßblatt prüfen.\n"
        "4. Fertigungsunterlagen exportieren: massblatt.svg, einbaukoordinaten.csv, PDF und DXF.\n\n"
        "Die Bibliothek enthält Dayton-Audio-Herstellerdaten und markierte TESTDATEN.\n"
        "Vier Gehäusefamilien sind berechenbar. Andere Typen sind noch in Entwicklung.\n"
        "Alle Maße und Herstellerangaben vor dem Bau am realen Chassis prüfen.\n",
        encoding="utf-8",
    )

    library = ComponentLibrary()
    result = automatic_design(AutomaticDesignRequest(
        project_name="Beispiel mit Herstellerdaten",
        preferred_manufacturer="Dayton Audio",
    ), library)
    if result.status != "ok" or not result.designs:
        raise RuntimeError(f"Kein Beispiel mit Herstellerdaten: {result.rejection_reasons}")
    design = result.designs[0]
    if design.woofer.manufacturer != "Dayton Audio":
        raise RuntimeError("Beispiel verwendet keine Herstellerdaten")
    demo_dir = OUTPUT / "Beispiel_Herstellerdaten"
    demo_dir.mkdir(exist_ok=True)
    export_project_package(design.bundle, demo_dir)
    (demo_dir / "Entwurf.json").write_text(
        json.dumps({"woofer": design.woofer.model, "tweeter": design.tweeter.model if design.tweeter else None,
                    "enclosure": design.project.enclosure.enclosure_type,
                    "source": str(design.woofer.source_url)}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    windows_zip = OUTPUT / "Lautsprecher-Konstruktion_V-01.02.00_Windows.zip"
    with ZipFile(windows_zip, "w", ZIP_DEFLATED, compresslevel=6) as archive:
        for file in DIST.rglob("*"):
            if file.is_file():
                archive.write(file, Path(DIST.name) / file.relative_to(DIST))

    source_zip = OUTPUT / "Lautsprecher-Konstruktion_V-01.02.00_Quellcode.zip"
    with ZipFile(source_zip, "w", ZIP_DEFLATED, compresslevel=6) as archive:
        for folder in ("src", "tests", "data", "docs", "scripts", "examples", "coordination"):
            for file in (ROOT / folder).rglob("*"):
                if file.is_file() and "__pycache__" not in file.parts and file.suffix != ".pyc":
                    archive.write(file, file.relative_to(ROOT))
        for name in ("README.md", "AGENTS.md", "PROJECT_STATUS.json", "pyproject.toml",
                     "BUILD_REPORT_V-01.02.00.md"):
            archive.write(ROOT / name, name)
    print(f"Windows ZIP: {windows_zip.stat().st_size:,} bytes")
    print(f"Source ZIP: {source_zip.stat().st_size:,} bytes")
    print(f"Output: {OUTPUT}")


if __name__ == "__main__":
    main()
