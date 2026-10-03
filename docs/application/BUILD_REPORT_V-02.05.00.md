# Buildbericht V-02.05.00

## Umfang

29 gelistete Gehäusearten besitzen Berechnung, akustische Vorschau und Fertigungsgeometrie. Neu gegenüber V-02.04.00 sind Bandpass 6 seriell, Compound Push-Pull, Aperiodisch, passiver Kardioid, offene Schallwände, gefaltete Linien und segmentierte Hörner. Front-Horn und Tapped-Horn haben eigene Solver, Zeichnungen, PDF-Seiten und DXF-Profile. Der automatische Assistent kann beide Hornarten bei ausreichendem Bauraum auswählen.

## Prüfung

- Pytest: 93 Fälle, einschließlich parametrischer Bauformen, Front-/Tapped-Horn-Export und automatischer Horn-Auswahl.
- Ruff: Quellcode, Tests und Paketierung geprüft.
- Windows-Onedir-Build und Offscreen-Starttest: erfolgreich, PyInstaller 6.22.3 unter Windows 11 mit Python 3.14.7.
- Paketierung: Windows- und Quellcode-ZIP mit Beispielzeichnungen für Front-/Tapped-Horn.

## Modellgrenzen

Alle Akustikmodelle sind lineare Kleinsignal-Näherungen. Gefaltete Linien und Hörner verwenden ebene Wellen, segmentierte Querschnitte sowie angenäherte Faltungs- und Mündungsverluste. Kardioid und offene Schallwand verwenden vereinfachte räumliche Modelle. Fertigungszeichnungen sind dimensionierte Rohteilpläne, aber keine vollständige 3D-Kollisions-, Toleranz- oder Gehrungsprüfung. Vor einem realen Zuschnitt müssen Datenblatt, Chassis-Lochbild und Prototypmessungen geprüft werden. Details stehen in `docs/ENCLOSURE_MODELS_V205.md`.

## Installation

Windows-ZIP vollständig entpacken und die EXE im enthaltenen Ordner starten. Das `_internal`-Verzeichnis muss daneben bleiben. Für Entwicklung `pip install -e ".[dev]"` und `python -m lautsprecher_konstruktion.app` verwenden.
