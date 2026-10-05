# Project Brief

## Project Name
Lautsprecher Konstruktion (Repository `Unternehmen-Lautsprecher-konzepte`)

## Problem
Der Entwurf eines Lautsprechers verlangt gleichzeitig Akustikrechnung (Gehäusevolumen, Abstimmung, Weiche), Geometrie (Einbaupositionen, Ports, Streben)
und Fertigungsunterlagen (Zuschnitt, Zeichnungen, Stückliste, Kosten). Das geschieht heute in getrennten Werkzeugen und Tabellen; Fehler entstehen an den Übergängen.

## Goal
Ein Windows-Programm, das aus Wunschmaßen und Klangprofil nachvollziehbare Lautsprecherentwürfe berechnet, prüft und als vollständiges Fertigungspaket
(Zeichnungen SVG/DXF/PDF, Stückliste mit Preisen, Zuschnittplan, Bauanleitung) ausgibt – und die Simulation mit Messungen des gebauten Prototyps vergleicht.

## Target Users
Selbstbauer und kleine Werkstätten mit Grundkenntnissen in Lautsprecherbau. Messmittel (Impedanz, Frequenzgang) sind für die Validierung nötig, nicht für die Nutzung.

## Target Platform / Version
Windows 10/11 (PyInstaller-Onedir), Python 3.12+, PySide6 ≥ 6.8. Entwicklung und automatische Prüfung laufen zusätzlich unter Linux (Offscreen).

## Expected Result
`Unternehmen-Lautsprecher-konzepte_V-03.00.00`: fertiger Release-Kandidat nach Erfüllung aller Kriterien in `ACCEPTANCE_CRITERIA.md`. Veröffentlichung nur nach Owner-Freigabe.

## Success Criteria
Siehe `ACCEPTANCE_CRITERIA.md` und `docs/application/PLAN_V-03.00.00.md`, Abschnitt 3.

## Constraints
- Lineare Kleinsignalmodelle; Aussagen über reale Lautsprecher nur mit Messnachweis.
- Keine erfundenen Herstellerdaten, Preise oder Messwerte; Testdaten sind als `TESTDATEN` gekennzeichnet.
- Offline-fähig; Preise sind datierte Momentaufnahmen.
- Veröffentlichung und Release nie automatisch.
