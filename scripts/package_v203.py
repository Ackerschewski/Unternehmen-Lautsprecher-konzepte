"""Create a local, Windows test delivery for V-02.03.00."""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from PySide6.QtCore import QByteArray
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

from lautsprecher_konstruktion.export.package import export_project_package
from lautsprecher_konstruktion.library.store import ComponentLibrary
from lautsprecher_konstruktion.project.models import (
    CrossoverConfig,
    EnclosureConfig,
    SpeakerProject,
)
from lautsprecher_konstruktion.services.automatic import AutomaticDesignRequest, automatic_design
from lautsprecher_konstruktion.services.design import calculate_project

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = Path(os.environ.get("LK_OUTPUT_BASE", ROOT / "outputs")) / "V-02.03.00"
DIST = ROOT / "dist" / "Lautsprecher-Konstruktion_V-02.03.00"


def _preview(svg_path: Path, png_path: Path) -> None:
    app = QGuiApplication.instance() or QGuiApplication([])
    _ = app
    renderer = QSvgRenderer(QByteArray(svg_path.read_bytes()))
    if not renderer.isValid():
        raise RuntimeError(f"Ungültige SVG-Vorschau: {svg_path}")
    image = QImage(1200, 1100, QImage.Format.Format_ARGB32)
    image.fill(0xffffffff)
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()
    if not image.save(str(png_path)):
        raise RuntimeError(f"PNG-Vorschau konnte nicht gespeichert werden: {png_path}")


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "BUILD_REPORT_V-02.03.00.md", OUTPUT)
    (OUTPUT / "START_HIER.txt").write_text(
        "Lautsprecher Konstruktion V-02.03.00\n\n"
        "1. Windows-ZIP vollständig entpacken.\n"
        "2. Lautsprecher-Konstruktion_V-02.03.00.exe starten; _internal muss daneben bleiben.\n"
        "3. Entwurf erstellen. Variantenvergleich und Simulation prüfen.\n"
        "4. Gesamtzeichnung, Innenaufbau und Einzelteilpläne einpassen oder zoomen.\n"
        "5. Fertigungsunterlagen exportieren: SVG-Einzelteilpläne, Koordinaten, PDF und DXF.\n\n"
        "Die Bibliothek enthält Herstellerdaten von Dayton Audio, Visaton, Scan-Speak und FaitalPRO sowie 84 Thomann-Katalogeinträge und markierte TESTDATEN.\n"
        "Das Gesamtbudget berücksichtigt Chassis, Holz, Weiche und Zubehör sowie 15 % Reserve. Preisarten sind in der Stückliste markiert.\n"
        "Händlerpreise sind Momentaufnahmen vom 02.10.2026; Planpreise vor Einkauf prüfen.\n"
        "Die Budgetsuche prüft mehrere passende Hochtöner und zeigt den freien Betrag.\n"
        "Unbekannte Bohrdurchmesser werden nicht als DXF-Bohrungen exportiert.\n"
        "Sechs Gehäusefamilien sind berechenbar, darunter zwei isobarische Bauarten. Andere Typen sind in Entwicklung.\n"
        "Alle Maße und Herstellerangaben vor dem Bau am realen Chassis prüfen.\n",
        encoding="utf-8",
    )

    library = ComponentLibrary()
    priced = automatic_design(AutomaticDesignRequest(
        project_name="Preisbeispiel Visaton B 200", speaker_type="Breitbandlautsprecher",
        way_count=1, preferred_driver="Visaton B 200 - 6 Ohm",
        max_width_m=.45, max_height_m=.8, max_depth_m=.7), library)
    if priced.status != "ok":
        raise RuntimeError(f"Preisbeispiel fehlgeschlagen: {priced.rejection_reasons}")
    export_project_package(priced.designs[0].bundle, OUTPUT / "Beispiel_Stueckliste_mit_Preisen")
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
    scanspeak = library.entries("drivers", "18W/8531G00")[0].driver
    iso_project = SpeakerProject(name="Isobarik mit Herstellerdaten", revision="V-02.03.00",
        driver=scanspeak, tweeter_name="", crossover=CrossoverConfig(enabled=False),
        enclosure=EnclosureConfig(enclosure_type="isobaric_sealed", target_qtc=0.5,
                                  external_width_mm=350, external_height_mm=450))
    iso_bundle = calculate_project(iso_project)
    iso_folder = export_project_package(iso_bundle, OUTPUT / "Beispiel_Isobarik")
    _preview(iso_folder / "zeichnungen" / "innenaufbau_massblatt.svg",
             OUTPUT / "Vorschau_Innenaufbau.png")
    _preview(iso_folder / "zeichnungen" / "gesamtzeichnung.svg",
             OUTPUT / "Vorschau_Gesamtzeichnung.png")
    _preview(iso_folder / "zeichnungen" / "einzelteil_front.svg",
             OUTPUT / "Vorschau_Einzelteil_Front.png")

    windows_zip = OUTPUT / "Lautsprecher-Konstruktion_V-02.03.00_Windows.zip"
    with ZipFile(windows_zip, "w", ZIP_DEFLATED, compresslevel=6) as archive:
        for file in DIST.rglob("*"):
            if file.is_file():
                archive.write(file, Path(DIST.name) / file.relative_to(DIST))

    source_zip = OUTPUT / "Lautsprecher-Konstruktion_V-02.03.00_Quellcode.zip"
    with ZipFile(source_zip, "w", ZIP_DEFLATED, compresslevel=6) as archive:
        for folder in ("src", "tests", "data", "docs", "scripts", "examples", "coordination"):
            for file in (ROOT / folder).rglob("*"):
                if file.is_file() and "__pycache__" not in file.parts and file.suffix != ".pyc":
                    archive.write(file, file.relative_to(ROOT))
        for name in ("README.md", "AGENTS.md", "PROJECT_STATUS.json", "pyproject.toml",
                     "BUILD_REPORT_V-02.03.00.md"):
            archive.write(ROOT / name, name)
    print(f"Windows ZIP: {windows_zip.stat().st_size:,} bytes")
    print(f"Source ZIP: {source_zip.stat().st_size:,} bytes")
    print(f"Output: {OUTPUT}")


if __name__ == "__main__":
    main()



