# Testübergabe (z. B. für ChatGPT Codex)

Stand: V-02.07.00, Branch `claude/modest-bell-guqoxu`. Ziel: unabhängig prüfen, ob Programm, Berechnung und Export korrekt arbeiten, und Fehler reproduzierbar melden.
**Nichts veröffentlichen, keine Releases, keine Änderungen an `coordination/` außer Testnachweisen.**

## Einrichtung

```bash
python3.12 -m venv .venv && .venv/bin/pip install -e ".[dev]"
# Linux: apt-get install libegl1 libgl1 libxkbcommon0 libfontconfig1
export QT_QPA_PLATFORM=offscreen LK_USER_DIR=/tmp/lk-test
```

## Automatische Prüfungen (müssen grün sein)

```bash
.venv/bin/ruff check src tests
.venv/bin/mypy
.venv/bin/python -m pytest -p no:cacheprovider        #  Fälle
.venv/bin/python -m lautsprecher_konstruktion.app --smoke
.venv/bin/python -m lautsprecher_konstruktion.app --smoke-assistant
python tools/validate_project.py && python tools/automation_control.py check
```

## Manuelle Prüfungen (Bildschirm nötig; auf Windows 10/11 ausführen, wenn möglich)

1. **Start:** `python -m lautsprecher_konstruktion.app`. Fenster, Menü (Datei/Werkzeuge/Hilfe), F1-Hilfe. Design nach ACK Studio (Papierweiß, Senfgelb, Serifentitel), siehe `docs/DESIGN_SYSTEM.md`.
2. **Assistent:** Demo „Kompakter 2-Wege-Regallautsprecher“ einsetzen → „Entwurf erstellen“ (Button muss ohne Scrollen sichtbar sein). Alle Reiter durchgehen: Entwürfe, Variantenvergleich, Gesamtzeichnung, Maßblatt, Innenaufbau, Einzelteilplan, Simulation, Stückliste, Zuschnitt. Zoom/Einpassen testen.
3. **Geschlossenes Gehäuse:** Demo „Geschlossener Subwoofer“ → Simulation zeigt Pegel, Auslenkung, Gruppenlaufzeit (Port-Diagramm: „Kein Port“).
4. **Export:** „Fertigungsunterlagen exportieren“. Prüfen: `fertigung/` (PDF, CSV, `zuschnittplan.*`, `bauanleitung.*`), `zeichnungen/` (SVG/DXF öffnen), `zuschnittplan/platte_*.svg|dxf`, `simulation/*.csv`.
5. **Speichern/Laden:** Projekt speichern, Programm neu starten, über „Zuletzt geöffnet“ laden. Ungespeichert schließen → Rückfrage. Autosave: Entwurf erzeugen, Prozess beenden (kill), neu starten → Wiederherstellungsfrage.
6. **Expertenmodus – Frontlayout:** Element mit Maus ziehen (Einrasten), Pfeiltasten (Umschalt = 10 mm), Strg+Z / Strg+Y, Ansicht Front/Rückwand/Trennwand.
7. **Expertenmodus – Weiche:** 2-Wege und 3-Wege (untere/obere Trennfrequenz), Schallwandkorrektur, Zobel; Weichen-Simulation und Schaltplan prüfen.
8. **Gehrung:** Gehäuse → Verbindung „Gehrung 45°“ → Zuschnittliste und Bauanleitung ändern sich, Volumen nicht.
9. **Prototypvergleich:** Werkzeuge → Prototyp vergleichen mit Beispiel-FRD/ZMA (`data/demo_*.frd|zma` sind synthetisch). Bericht speichern.
10. **Fehlerfälle:** unmögliche Vorgaben („Unmögliche Anforderung“ in den Demos), kaputte Projektdatei laden, Messdatei mit falschem Format → verständliche Meldung, kein Absturz. Protokoll: Hilfe → Protokollordner.

## Plausibilität (Stichproben, mit Taschenrechner)

- Geschlossen: Fc = Fs·√(1+Vas/Vb), Qtc = Qts·√(1+Vas/Vb).
- Bassreflex: Portlänge aus Leff = c²·A/((2π·Fb)²·V) minus 1,46·r; Impedanzminimum nahe Fb.
- Zuschnitt: Summe der Teilflächen ≤ Plattenfläche, kein Teil überlappt, Sägeschnitt eingehalten.
- Maße in Zeichnung, Stückliste und Zuschnittliste stimmen überein.

## Bekannte Grenzen (kein Fehler)

Lineare Kleinsignalmodelle ohne Messvalidierung; Zuschnitt plant umschreibende Rechtecke; keine 3D-Kollisionsprüfung; Assistent wählt keine 3-Wege-Lautsprecher; Chassisdaten sind nur teilweise vollständig; Windows-Build dieser Version wurde nicht ausgeführt.

## Fehlerbericht (je Befund)

| Feld | Inhalt |
|---|---|
| Titel | kurz, ein Satz |
| Schritte | nummeriert, mit Eingabewerten/Projektdatei |
| Erwartet / Beobachtet | |
| Umgebung | Betriebssystem, Python, `pip list`-Auszug |
| Anhang | Screenshot, Protokolldatei, exportiertes Paket |
| Schwere | blockierend / hoch / mittel / niedrig |

Befunde als Datei `coordination/feedback/<datum>_<kurztitel>.md` ablegen (siehe `coordination/feedback/README.md`), nicht im Code beheben, außer es wird ausdrücklich verlangt.
