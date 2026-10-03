# Buildbericht V-02.04.00

## Änderungen

- Parallelbandpass 6. Ordnung mit getrennten Front-/Rückkammerabstimmungen und zwei geraden externen Ports.
- Gehäusegeometrie, Front-/Rückwandausschnitte, Innenaufbau, DXF, PDF, SVG, CSV und Stückliste enthalten BR1 und BR2.
- Beide Portgeschwindigkeiten werden separat ausgegeben; Kanalüberstände blockieren den Fertigungsexport.
- Modellgleichungen und Annahmen: `docs/BANDPASS6_MODEL.md`.

## Prüfung

- Pytest: 60 Fälle bestanden.
- Ruff: bestanden.
- Windows-PyInstaller-Build und Offscreen-Startprüfung: bestanden.
- Fertigungspaket, DXF/PDF-Ausgabe und lesbare SVG-Vorschau: bestanden.
- Windows-ZIP: rund 102,6 MB; Quellcode-ZIP: rund 259 kB.

## Grenzen

Der Zweiport-Frequenzgang ist eine ideale lineare Kleinsignalrechnung ohne Messabgleich. Besonders Portabstände, Verluste und Kanalmoden können die reale Antwort ändern. 22 weitere registrierte Typen bleiben in Entwicklung. Vor Zuschnitt und Produktfreigabe Testpaket am Windows-Rechner und an realen Komponenten prüfen.
