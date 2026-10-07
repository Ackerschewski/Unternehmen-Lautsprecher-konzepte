# Build-Report TASK-0028 – V3.3 Visual Acceptance Sprint

Stand: 2026-10-07 · Branch `claude/modest-bell-guqoxu` · Prüfumgebung: Linux, Qt offscreen. **Windows/DPI: NOT_RUN.**

## Ausgangslage und Integration

- TASK-0028 lag auf `feature/LK-026-ui-v3-2-planner`. Dieser Branch enthielt seit dem Abzweig (`af83640`) eine eigene Umsetzung von TASK-0026 (Planner-UI, Zielkurve, Einflusskarten, Zeichnungs-Tokens). Der Branch `claude/modest-bell-guqoxu` enthielt parallel eine zweite UI-Umsetzung, die Geometrie-Prüfung aller Gehäuse und die Zeichnungsüberarbeitung.
- Entscheidung des Projektinhabers: **beide Stände zusammenführen**. Merge-Commit `3f3f11b`: 19 Konflikte. Auflösung:
  - Die **Planner-UI gewinnt** (assistant_window, tokens, theme, cabinet_preview, motion, Zielkurve). Meine parallele UI-Fassung (eigene Zielkurven-Komponente, Variantenkarten, Collapsible) und das doppelte Datenmodell `TargetCurve` wurden entfernt, damit keine konkurrierende UI entsteht.
  - **Geometrie, Innenzeichnungen, Titelblock** der Zeichnungen und alle Kernänderungen der Gehäuse-Prüfung blieben erhalten. Die Farben der Zeichnungen stammen jetzt aus der Planner-Palette (`drawings/style.py`: Rollen-Sentinels `%INK%` usw. auf die Planner-Konstanten abgebildet).
  - Der Test `test_bookshelf_design_fit_score_project_export` des Planner-Branches war dort rot (4 statt 3 Varianten) und wurde auf bis zu 4 Varianten angepasst.
- **TASK-0027 (Smooth EQ, Bibliothek, Dämmung, 3D) ist nicht umgesetzt.** Folge: kein Bereich „3D & Konstruktion", kein Smooth-EQ. Die Phasen unten sind unabhängig davon umgesetzt. Es wurden keine Fake-3D-Bilder eingebaut.

## Geänderte Informationsarchitektur

| Bereich | Vorher | Jetzt |
|---|---|---|
| Navigation | Planen · Varianten · Klang & Simulation · Zeichnungen · Fertigung, zusätzlich Header-Buttons | Planen · Varianten · Klang · Zeichnungen · Fertigung; Bibliothek/Expertenmodus nur im Menü „Werkzeuge"; nur noch **ein** Header-Button „Vorgaben ändern/einklappen" nach einem Ergebnis |
| Planungsspalte | immer ein Drittel der Breite | siehe responsive Regeln |
| Ergebnis | kleine Frontansicht, fünf überlappende Textlabels | Variantenleiste (A/B/C/D) über großer Visualisierung; sechs Kennwertkarten (Maße, F3, Max-SPL, Preis, Datenqualität, Warnungen); Details einklappbar |
| Varianten | Karten, darunter viel Leerraum | vier Karten oben ausgerichtet mit Max-SPL, Hub-/Port-Status, Bauaufwand, Deltas zu A; Abschnitt „Warum besser oder schlechter als A?" aus berechneten Werten; Tabelle nur unter „Alle technischen Daten" |
| Zeichnungen | Zoomleiste mit sieben Aktionen, Blatt bei ca. 19–45 % | eine Bildschirmansicht (Front, Seite, Schnitt, **Innenaufbau**, Einzelteile), automatisch eingepasst; Toolbar *Einpassen · 100 % · − · + · Prozentwert · Vollbild*; „Druckblatt anzeigen" als eigener Schalter; Statuszeile und Planungsspalte treten zurück |
| Klang | Zielkurve und vier Diagramme gleichzeitig, bei 1280 × 720 abgeschnitten | Hauptgraph (Zielkurve) dominant; darunter **ein** wählbares Sekundärdiagramm (Hub, Port, Impedanz, Gruppenlaufzeit, Weiche, DSP) – nur verfügbare Daten aktiv, ab 1700 px Breite zwei |
| Nicht machbar | Textliste, leere Fläche | Diagnosekarte: Hauptgrund mit verfügbar/benötigt, Änderungsbuttons mit geprüften Werten, weitere Gründe; irrelevante Reiter deaktiviert; Eingaben bleiben offen |

## Responsive Regeln (`ui/layout_rules.py`, pure Funktionen, getestet)

- Vor einem Ergebnis: Planungsspalte offen, 320–440 px und höchstens 38 % der Fensterbreite.
- Mit Ergebnis: unter 1600 px eingeklappt, ab 1600 px kompakter Inspector (360 px); im Reiter Zeichnungen immer eingeklappt; „Vorgaben ändern" überschreibt bis zum nächsten Reiterwechsel.
- Arbeitsfläche nach einem Ergebnis ≥ 65 % der Breite (Test für 1280, 1366, 1600, 1920).
- Kompaktmodus unter 820 px Höhe: Untertitel und Empfehlungstext entfallen, Steuerelemente enger.
- Fenster-Resize ändert nur Layout; Diagramme zeichnen entprellt (120 ms) neu. Test: Resize startet **keine** Berechnung.

## Nicht machbar: geprüfte Vorschläge

`AutomaticDesignResult.diagnostics` (neu): Der Entwurfsrechner sammelt jetzt alle verletzten Grenzen je Kandidat. Ein Kandidat, der **genau eine** Grenze verfehlt, liefert den Messwert (Tiefe, Außenvolumen, F3, Budget, Max-SPL). Die Vorschläge wurden am Solver geprüft: Tiefe 100 → 145 mm macht den Bücherregal-Fall machbar (2 Entwürfe), Budget 50 → 357 € ebenfalls (4 Entwürfe). Gibt es keinen Ein-Grenzen-Fall (z. B. die Demo „Unmögliche Anforderung"), sagt die Karte das ausdrücklich und zeigt nur die allgemeinen Hinweise. Vorher wurden die Ablehnungsgründe teils am ersten verletzten Filter gezählt; die Zählreihenfolge der Gründe blieb erhalten.

## Zustände

- Leer/Start: Anleitung plus maßstäbliche Skizze des eingegebenen Bauraums statt eines leeren Ergebnisrahmens.
- Berechnung: Fortschritt, Kandidatenzahl und Abbrechen (unverändert aus der Planner-UI).
- Fehler: Fehlertext, „Erneut versuchen", „Diagnose kopieren"; keine alten Ergebnisse (Zeichnungen, Varianten, Kennwerte werden gelöscht).

## Tests und Qualität

- Neue Tests: `test_v212_diagnostics.py` (5), `test_v213_visual_acceptance.py` (22: responsive Regeln, Hero, Variantenwechsel, Karten, Zeichnungs-Workspace, Druckblatt-Schalter, Bildschirmviews, Sound Lab, Resize ohne Berechnung, Vorschläge, Nicht-machbar-Zustand, Fehlerzustand).
- Pytest, Ruff und mypy (Nicht-UI) laufen grün; Zahlen im Abschnitt „Abschluss" unten bzw. in `PROJECT_STATUS.json`.
- Geometrie-Tests ohne Pixel-Snapshots (Größen, Sichtbarkeit, Texte).

## Evidence

`coordination/feedback/evidence/2026-10-07-v3-3/` – Dark und Light, 1280 × 720 und 1920 × 1080: Start, Ergebnis, Varianten, Klang, Zeichnungen, Fertigung, Nicht machbar. Linux/offscreen, nicht Windows.

## Offene UX-Probleme (ehrlich)

- Bei 1280 × 720 scrollt der Reiter Klang vertikal: Hauptgraph samt Steuerung ist ohne Scrollen sichtbar, das Sekundärdiagramm liegt darunter. Beide gleichzeitig würden den Hauptgraph unter die geforderte Höhe drücken.
- Die Frontansicht im Hero ist eine schematische Vorschau (kein 3D, keine CAD-Geometrie). 3D bleibt TASK-0027.
- Einzelteil-Navigation und Innenaufbau-Ansicht sind auf Bildschirmlesbarkeit getrimmt, aber nicht für beliebig viele Teile getestet.
- Beschriftungen in den Bildschirmzeichnungen sind bei sehr schmalen Hochformat-Teilen weiter klein relativ zum Fenster (Fit ist durch die Fensterhöhe begrenzt).
- Der Smooth-EQ der Zielkurve (TASK-0027) fehlt; die Kurve besteht weiter aus Stützpunkten.
- **Windows 100/125/150 %: NOT_RUN.** Die Größenregeln sind in Pixeln der Offscreen-Umgebung geprüft.

## TASK-0027-Integration

Nicht ausgeführt. Voraussetzungen, die diese Runde dafür geschaffen hat: Vorgaben-Schublade und Reiterstruktur, `sound_plots.py` mit Verfügbarkeitslogik (DSP-Eintrag ist als „nicht Teil dieser Version" deaktiviert), `result_hero.py` mit Platz für eine 3D-Vorschau in der Hero-Fläche.

## Nächste Schritte

1. TASK-0027 (Smooth EQ, Bibliothek-Readiness, Dämmung als Projektobjekt, 3D-MVP) auf dieser Basis.
2. Nutzerprüfung der Evidence und Windows-Test mit 100/125/150 % Skalierung.
3. Expertenmodus im neuen Design (deutsche Begriffe, Kennwerte statt Text).
