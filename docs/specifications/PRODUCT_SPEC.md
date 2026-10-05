# Product Specification

## Overview
Konstruktionsassistent für Lautsprecher: Wunschmaße → berechnete, geprüfte Entwürfe → Fertigungspaket. Detailbeschreibung: `docs/application/ARCHITECTURE.md`, `ENCLOSURE_MODELS_V205.md`, `VALIDATION.md`.

## Primary User Workflow
1. Typ, größtes Außenmaß, Klangprofil, optional Budget angeben (Assistent) oder T/S-Daten eingeben (Expertenmodus).
2. Varianten prüfen: Gesamtzeichnung, Maßblatt, Innenaufbau, Einzelteilpläne, Simulation, Stückliste, Zuschnitt.
3. Fertigungspaket exportieren, bauen, messen.
4. Messung gegen die Simulation vergleichen und Port/Dämmung anpassen.

## Inputs
Wunschmaße, Profil, Budget; Chassisdaten aus Bibliothek oder Datei (CSV/JSON); gemessene FRD/ZMA; Projektdateien (JSON, Schema 3).

## Outputs
SVG, DXF, PDF, CSV, Markdown, Projekt-JSON; Zuschnittplan; Bauanleitung; Prototypvergleichsbericht.

## Automation Level
Assistent: automatisch mit Nachvollziehbarkeit (Bewertungsaufschlüsselung). Export: nur nach bestandener Geometrieprüfung. Portkorrektur: Vorschlag, Entscheidung beim Nutzer.

## Error Behaviour
Unzulässige Eingaben werden mit Grund abgelehnt; fehlende Daten führen zu „nicht berechenbar“ statt Schätzung; Fehler werden protokolliert und angezeigt.

## UI / UX
Qt-Oberfläche mit Assistent und Expertenmodus, Hell/Dunkel, zoombare SVG-Blätter, Menü, Tastenkürzel, Hilfe (F1).

## Integrations
Keine externen Dienste im Betrieb; Messdaten als Textdateien (FRD/ZMA).

## Data Models
`SpeakerProject` (pydantic, Schema 3), `DesignBundle`, `CuttingPlan`, `PrototypeReport`.

## Logging / Diagnostics
Rotierendes Protokoll unter `%LOCALAPPDATA%\LautsprecherKonstruktion\logs`; unbehandelte Ausnahmen werden protokolliert und angezeigt.
