# Requirements

## MUST

- Alle Katalog-Gehäusetypen berechnen; erkannte Geometriefehler sperren den Fertigungsexport.
- Einheiten: SI im Kern, mm/Liter/Hz in Oberfläche und Dateien.
- Herstellerdaten mit Quelle und Abrufdatum; fehlende Werte bleiben leer und sperren die automatische Berechnung.
- Export: Zeichnungen (SVG, DXF), PDF, Stückliste (CSV, PDF) mit Preisart, Zuschnittliste.
- Zuschnittplan mit Sägeschnitt, Plattenzahl, Verschnitt; nicht passende Teile werden gemeldet.
- Prototypvergleich mit gemessenen FRD/ZMA und nachvollziehbarer Bewertung.
- Solver sind gegen Literaturbeziehungen abgesichert (Referenztests).
- Projekte speichern, laden, migrieren (Schema 3); ungespeicherte Änderungen werden nicht stillschweigend verworfen.
- Fehler und Absturzursachen werden protokolliert.

## SHOULD

- Autosave und Wiederherstellung; Einstellungen bleiben erhalten.
- Bauanleitung je Bauform.
- Gewichtsangabe als Bereich.
- Schallwandkorrektur als Option.
- `mypy --strict` für Nicht-UI-Pakete.

## COULD

- 3-Wege-Weiche, Undo/Redo, Drag-and-drop im Frontlayout.
- 3D-Kollisions- und Gehrungsprüfung.

## MUST NOT

- Messwerte, Herstellerdaten oder Preise erfinden.
- Release oder Veröffentlichung automatisch auslösen.
- Benutzerdaten in das Installationsverzeichnis schreiben.
- Simulation als Messung darstellen oder `NOT_RUN` als `PASS` ausweisen.

## Compatibility

Windows 10/11; Projektdateien Schema 3 bleiben lesbar (ältere Schemata werden migriert).

## Performance

Assistentenlauf mit Abbruchmöglichkeit im Hintergrundthread; Zuschnitt und Prototypvergleich in unter einer Sekunde für typische Projekte.

## Reliability

Atomare Schreibvorgänge für Einstellungen und Autosave; defekte Einstellungsdateien führen nicht zum Absturz.

## Security

Keine Netzwerkzugriffe im Betrieb; keine Geheimnisse im Repository; Messdateien werden nur gelesen.

## Open Questions

Siehe `coordination/OPEN_QUESTIONS.md`.
