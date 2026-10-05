# Plan zur fertigen Version V-03.00.00

Stand der Analyse: V-02.05.00, Branch `feature/LK-021-budget-fertigungsblatt` (Draft-PR #4).
Dieser Plan beantwortet zwei Fragen: **Was fehlt noch?** und **Was muss in einer fertigen Version enthalten sein?**
Er trennt strikt zwischen Arbeit, die im Repository erledigt und automatisch geprüft werden kann, und Nachweisen,
die nur am Windows-Rechner oder am gebauten Lautsprecher entstehen (`NOT_RUN` ist kein `PASS`).

## 1. Ist-Stand (gemessen, nicht geschätzt)

| Bereich | Stand V-02.05.00 |
|---|---|
| Umfang | Python 3.12 / PySide6, rund 9 600 Zeilen Quellcode, 95 Pytest-Fälle (alle grün), Ruff sauber |
| Gehäuse | alle 29 Katalogtypen mit Solver, Zeichnung, DXF, PDF, Stückliste |
| Assistent | Wunschmaße → 1–3 Varianten, Budget, Sound-Profile, Zweiwege-Auswahl |
| Bibliothek | 84 Thomann-Preiseinträge, aber nur ~25 Chassis mit vollständigen T/S- und Montagedaten |
| Weiche | nur 2-Wege, passiv, Startwerte (E12) |
| Testabdeckung | Kern 93–99 %; `assistant_window` 55 %, `library_dialog` 18 %, `zoom_svg` 65 % |
| Typprüfung | `mypy --strict` ist konfiguriert, läuft aber nie: es fehlt `py.typed`; mit Marker 164 Fehler in 27 Dateien |
| Governance | Spezifikationsdokumente (`docs/specifications/*`) sind noch leeres Template |

## 2. Lücken zwischen V-02.05.00 und „fertig“

### A. Vertrauen in die Ergebnisse (größtes Risiko)
1. Kein Abgleich der Solver mit Literaturwerten (Small/Thiele-Alignments, geschlossene Formeln) als dauerhafte Regressionstests.
2. Kein Werkzeug, um **gemessene** Prototyp-Kurven (FRD/ZMA) gegen die Simulation zu legen und daraus eine Korrektur abzuleiten (Abstimmfrequenz, Portlänge).
3. Reale Messvalidierung für mehrere Treiber und Bauformen fehlt (nur mit gebauter Hardware möglich).
4. Keine Schallwand-Korrektur (Baffle Step): Weichen-Startwerte und Systemfrequenzgang ignorieren sie.

### B. Fertigung
5. Kein Zuschnittplan: Plattenteile werden nur gelistet, nicht auf Handelsplatten (z. B. 2 500 × 1 250 mm) mit Sägeschnitt verteilt; Verschnitt und Plattenzahl (= echte Materialkosten) fehlen.
6. Kein Gewicht (Transport, Wandmontage, Standfestigkeit).
7. Keine Bauanleitung / Montagereihenfolge; das Paket enthält Zeichnungen, aber keinen Ablauf.
8. Keine vollständige 3D-Kollisions- und Gehrungsprüfung; gefaltete Horn-/Linienprofile sind Stufenprofile.

### C. Bedienung im Alltag
9. Kein „Zuletzt geöffnet“, keine Einstellungen (Fenstergröße, Theme, Plattenformat), kein Wiederherstellen nach Absturz.
10. Keine Warnung bei ungespeicherten Änderungen; kein Programmlog für Fehlersuche beim Nutzer.
11. Kein Undo/Redo und keine Drag-and-drop-Bearbeitung im Frontlayout.
12. Keine Hilfe/Über-Seite im Programm; Handbuch-Kopfzeilen sind teils veraltet (V-01.01.00).

### D. Funktionsumfang
13. 3-Wege-Weiche / Netlist, aktive Weiche, Kosten für Mehrwege fehlen.
14. Datenbasis: Chassis ohne T/S bleiben gesperrt; die Bibliothek muss durch belegte Herstellerdaten wachsen (nie geschätzt).

### E. Qualität und Release
15. `mypy --strict` nicht erfüllt; UI-Tests dünn.
16. Versionsangaben an acht Stellen manuell gepflegt (Paket, App-Titel, Projektmodell, Doku).
17. Windows-Build, interaktiver Sichttest und Owner-Freigabe stehen aus.

## 3. Definition „fertige Version“ V-03.00.00

Ein Punkt gilt erst als erfüllt, wenn der genannte Nachweis existiert.

| ID | Kriterium | Nachweis | Heute |
|---|---|---|---|
| F1 | Alle 29 Gehäusetypen berechenbar mit Fertigungsgeometrie | Pytest | erfüllt |
| F2 | Baffle-Step-Korrektur im Systemfrequenzgang, abschaltbar, dokumentiert | Pytest | V-02.06 |
| F3 | 3-Wege-Weiche | Pytest + Doku | **erfüllt (V-02.07)** |
| K1 | Solver gegen Literaturreferenzen abgesichert | Pytest (`test_reference_*`) | V-02.06 |
| K2 | Prototyp-Messvergleich mit Abweichungskennzahlen und Korrekturvorschlag | Pytest + Beispielmessung | V-02.06 |
| K3 | Messvalidierung: ≥ 3 reale Treiber in ≥ 3 Bauformen, Abweichung dokumentiert | Messprotokoll (PHYSICAL) | **nur Nutzer** |
| M1 | Zuschnittoptimierung mit Sägeschnitt, Verschnitt, Plattenzahl, SVG/CSV/PDF | Pytest | V-02.06 |
| M2 | Gewicht (Gehäuse, Chassis, gesamt) in Stückliste und PDF | Pytest | V-02.06 |
| M3 | Bauanleitung mit Montagereihenfolge je Bauform | Pytest + Sichtprüfung | V-02.06 |
| M4 | 3D-Kollisions-/Gehrungsprüfung | Pytest | teilweise: Gehrungsoption und Zuschnitt seit V-02.07; 3D-Kollisionsprüfung offen (V-02.08) |
| U1 | Zuletzt geöffnet, Einstellungen, Autosave/Wiederherstellung, Ungespeichert-Warnung | Offscreen-UI-Test | V-02.06 |
| U2 | Programmlog (rotierend), Hilfe/Über, Handbuch aktuell | Pytest + Review | V-02.06 |
| U3 | Undo/Redo + Drag-and-drop im Frontlayout | Offscreen-UI-Test | **erfüllt (V-02.07)** |
| Q1 | Ruff sauber, Pytest grün, Kernabdeckung ≥ 90 %, UI ≥ 70 % | lokaler Lauf | **erfüllt (V-02.07)**: gesamt 90 %, UI-Dateien 75–100 % |
| Q2 | `mypy --strict` für Nicht-UI-Pakete grün | mypy | **erfüllt (V-02.07)** |
| Q3 | Eine einzige Versionsquelle | Pytest | V-02.06 |
| Q4 | Spezifikation, Anforderungen, Abnahmekriterien ausgefüllt | Review | V-02.06 |
| R1 | Windows-Onedir-Build + Smoke-Test grün | HOST_RUNTIME (Windows) | **nur Nutzer/CI** |
| R2 | Interaktiver Sichttest auf Zielrechner | USER_TEST | **nur Nutzer** |
| R3 | Owner-Freigabe; Veröffentlichung nie automatisch | Owner | **nur Owner** |

## 4. Stufenplan

### V-02.06.00 — „Fertigung und Vertrauen“ (umgesetzt)
1. WP-A Zuschnittoptimierung, Gewicht, Bauanleitung (M1–M3).
2. WP-B Referenztests und Prototyp-Messvergleich (K1, K2).
3. WP-C Baffle Step (F2).
4. WP-D Alltagstauglichkeit: Einstellungen, Zuletzt geöffnet, Autosave, Log, Hilfe (U1, U2).
5. WP-E Governance: einheitliche Version, Spezifikation, Task, Changelog (Q3, Q4).

### V-02.07.00 — „Mehrwege und Bedienkomfort“ (umgesetzt)
3-Wege-Weiche, Undo/Redo und Drag-and-drop im Frontlayout, `mypy --strict` für alle Nicht-UI-Pakete, UI-Tests. Nicht umgesetzt: Erweiterung der Chassis-Datenbank (braucht belegte Herstellerdaten, die nicht erfunden werden dürfen) und automatische 3-Wege-Auswahl im Assistenten.

### V-02.08.00 — „Geometrie-Härtung“
3D-Kollisionsprüfung, Gehrungen, Plattenstöße, Horn-Faltungen mit echten Profilen, DXF-Validierung gegen CNC-Software.

### V-03.00.00 — Release-Kandidat
Erst nach K3 (Prototypmessungen), R1 (Windows-Build), R2 (Sichttest) und R3 (Owner-Freigabe). Der Release-Kandidat wird vorbereitet, **nicht automatisch veröffentlicht**.

## 5. Was nur der Nutzer liefern kann

- Bau und Messung von Prototypen (Impedanz, Nahfeld/Frequenzgang) mit Import in das neue Vergleichswerkzeug.
- Windows-Build und interaktiver Test auf dem Zielrechner.
- Entscheidungen zu den offenen Fragen in `coordination/OPEN_QUESTIONS.md`.
- Freigabe der Veröffentlichung.

Es werden keine Messdaten, Herstellerwerte oder Preise erfunden. Synthetische Daten bleiben als `TESTDATEN` gekennzeichnet.

## 6. Risiken

| Risiko | Gegenmaßnahme |
|---|---|
| Lineare Kleinsignalmodelle weichen von Realität ab | K1/K2/K3; Warnhinweise bleiben in Export und Oberfläche |
| Zuschnitt auf Bounding-Box bei Trapez-/Rundteilen verschenkt Material | bewusst konservativ, im Plan ausgewiesen |
| Plattenpreise veraltet | Preisart bleibt „Materialreferenz“, nie als Angebot |
| Große UI-Dateien (`main_window.py` > 1 200 Zeilen) erschweren Wartung | Aufteilen in V-02.07 |
