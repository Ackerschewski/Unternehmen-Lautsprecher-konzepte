# Buildbericht V-02.06.00

## Umfang

Zuschnittoptimierung mit Sägeschnitt, Gewichtsbereich, Bauanleitung, Prototypvergleich (Oberfläche und Kommandozeile),
Schallwandkorrektur, Referenztests der Solver, Benutzerdaten (Zuletzt geöffnet, Einstellungen, Autosave, Protokoll),
Hilfe/Über, einheitliche Versionsquelle. Details: `APP_README.md`, Plan: `PLAN_V-03.00.00.md`.

## Prüfung (lokal, Linux, ohne Anzeige)

| Prüfung | Ergebnis |
|---|---|
| Pytest | alle Fälle bestanden (Stand siehe `PROJECT_STATUS.json`) |
| Ruff | bestanden |
| Offscreen-Smoke `--smoke` und `--smoke-assistant` | bestanden (Exit 0) |
| Kernabdeckung | Berechnung/Export 94–100 %; neue Module 91–100 % |
| Zuschnitt, Bauanleitung und Export für alle 29 Gehäusetypen | geprüft (Parametertabelle im Test, kein Überspringen) |

## Nicht ausgeführt (NOT_RUN)

| Nachweis | Grund |
|---|---|
| Windows-PyInstaller-Build und Smoke der EXE | nur unter Windows möglich (`scripts/build_windows.ps1`, unverändert bis auf den Versionsnamen) |
| Interaktiver Sichttest auf dem Zielrechner | USER_TEST |
| Messvalidierung mit Prototypen | PHYSICAL; siehe `VALIDATION.md` und `MESSPROTOKOLL.md` |
| `mypy --strict` | nicht erfüllt: 164 Fehler in 27 Dateien (`py.typed` fehlt bewusst, damit das Ziel nicht still gilt) |

## Modellgrenzen

Alle Akustikmodelle bleiben lineare Kleinsignal-Näherungen. Der Zuschnitt plant umschreibende Rechtecke; das Gewicht umfasst
nur Plattenmaterial mit typischen Richtdichten (MDF 680–800, Birke-Multiplex 640–720, Spanplatte 600–750 kg/m³). Die Schallwandstufe
folgt der Regel 115 Hz·m/B und ist nicht an Messungen validiert.

## Installation

Windows-ZIP vollständig entpacken und die EXE im Ordner starten; `_internal` muss daneben bleiben. Für die Entwicklung
`pip install -e ".[dev]"` und `python -m lautsprecher_konstruktion.app`. Auf Linux wird für die Oberflächentests
`QT_QPA_PLATFORM=offscreen` sowie `libegl1` und `libgl1` benötigt.
