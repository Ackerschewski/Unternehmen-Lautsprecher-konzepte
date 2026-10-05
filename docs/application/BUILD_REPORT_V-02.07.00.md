# Buildbericht V-02.07.00

## Umfang

3-Wege-Weiche mit exakter Kettenschaltungs-Simulation, Gehrungsoption, DXF je Zuschnitt-Platte, interaktives Frontlayout mit Ziehen, Einrasten, Pfeiltasten und Rückgängig/Wiederholen,
`mypy --strict` für alle Nicht-UI-Pakete, UI-Tests für Bibliotheksdialog und Frontlayout, Aufnahme der Prüfkommandos in die Qualitätsmatrix.
Basis ist V-02.06.00 (Zuschnitt, Bauanleitung, Prototypvergleich, Benutzerdaten).

## Prüfung (lokal, Linux, ohne Anzeige)

| Prüfung | Ergebnis |
|---|---|
| Pytest | 233 Fälle bestanden |
| Ruff | bestanden |
| `mypy --strict` | 87 Quelldateien ohne Befund (Qt-Oberfläche und `app` sind in `pyproject.toml` ausdrücklich ausgenommen) |
| Offscreen-Smoke `--smoke` und `--smoke-assistant` | bestanden |
| Abdeckung gesamt | 90 %; Oberfläche je Datei 75–100 % |
| Repository-Gates (`validate_project`, `automation_control`, `defect_control`, `release_control`, `ci_budget_check`, Schnappschüsse) | bestanden, 6 Größenwarnungen (>800 Zeilen: `main_window.py`, `assistant_window.py`) |

## Nicht ausgeführt (NOT_RUN)

| Nachweis | Grund |
|---|---|
| Windows-PyInstaller-Build und Smoke der EXE | nur unter Windows möglich (`scripts/build_windows.ps1`; Skript unverändert bis auf den Versionsnamen) |
| Interaktiver Sichttest, Mausbedienung des Frontlayouts auf dem Zielrechner | USER_TEST; getestet wurde mit simulierten Maus- und Tastenereignissen |
| Messvalidierung mit Prototypen | PHYSICAL; siehe `VALIDATION.md` und `MESSPROTOKOLL.md` |

## Modellgrenzen

Die 3-Wege-Weiche rechnet mit linearen Elementen und nominalen bzw. gemessenen Treiberimpedanzen. Schallzentren, Laufzeitunterschiede, Treiberpegel und die akustische
Phase ohne FRD sind nicht modelliert; die akustische Summe erscheint nur mit FRD aller drei Treiber. Alle Kleinsignalmodelle der Gehäuse bleiben Näherungen.

## Hinweise für Entwickler

`py.typed` ist gesetzt. Neue Dateien außerhalb von `ui/` müssen `mypy --strict` bestehen (`tests/test_v207_typing.py` führt das aus).
Gemeinsame NumPy-Typen stehen in `lautsprecher_konstruktion/arrays.py`. `Driver.require_vas_m3()` ersetzt direkte Zugriffe auf ein optionales Vas.
