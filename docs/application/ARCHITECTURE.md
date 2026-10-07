# Architektur V-01.01.00

```text
data/library/{drivers,passive_radiators,ports,crossover,hardware,materials}
        + %LOCALAPPDATA%/LautsprecherKonstruktion/library
        -> ComponentLibrary (JSON/CSV, Suche, Filter, Aktivstatus)
        -> AutomaticDesignRequest + SoundProfile
        -> automatische Filter / Gehäuse-Strategien / Dimensionssuche
        -> calculate_project(SpeakerProject) -> DesignBundle
        -> harte Machbarkeitsprüfung -> ScoreMetric[] -> 1–3 SpeakerDesign
        -> AssistantWindow (Standard) / MainWindow (Expertenmodus)
        -> SVG/DXF/PDF/CSV/JSON und gemeinsame Stückliste
```

Die Automatisierung liegt in `services/automatic.py` und importiert keine Qt-Klassen. `enclosure/registry.py` verwaltet Kennung, Status und Metadaten aller vorgesehenen Familien; `enclosure/strategies.py` enthält die sechs vorhandenen physikalischen Vorbereitungsstrategien. `enclosure/isobaric.py` definiert das ideale Ersatzchassis und die Koppelkammergeometrie. `calculate_project` behält gemeinsame Geometrie, Kollisionen und Simulation. Ein `PLANNED`-Typ darf im Projektmodell stehen, wird aber vor der Berechnung mit verständlicher Meldung abgewiesen. `SpeakerProject` speichert auch ausgewählte weitere Treiber und Zubehör. `ui/assistant_window.py` verwendet einen Worker-Thread mit Abbruchsignal. Beide Oberflächen arbeiten mit demselben Projektmodell.

```text
DriverCatalog/FRD/ZMA -> SpeakerProject (Schema 3)
                         -> calculate_project() -> DesignBundle
                             | acoustics: sealed, vented, passive radiator, bandpass, alignment
                             | enclosure: PortDesign, PassiveRadiatorDesign, CabinetDimensions, FrontElement
                             | crossover: RLC-Netzwerk, komplexe Last, FRD-Summe
                         -> UI-Diagramme
                         -> Zeichnungen/DXF/PDF/CSV/JSON
```

`src/lautsprecher_konstruktion/ui` enthält Eingabe, Diagramme und Live-Layoutsteuerung. Die Kernpakete `acoustics`, `crossover`, `drivers`, `enclosure` und `project` importieren keine PySide6-Klassen. `services/design.py` berechnet das Projekt und sammelt strukturierte Warnungen. `drawings` und `export` konsumieren den aufgelösten Bundle-Zustand; sie berechnen keine eigene Treiber-/Portposition.

`SpeakerProject` speichert Montageflächen, Positionen und Messdaten. V-00.02/V-00.03-Dateien werden beim Laden zu Schema 3 migriert. Der Portdurchmesser bzw. Slotquerschnitt kommt aus der Gehäusekonfiguration; das Layoutobjekt trägt Position, Montagefläche und Bohrungen. Der Resolver synchronisiert die Portgeometrie vor Zeichnung und Export. Die Passivmembran verwendet eigene gemessene Freiluftparameter. Der Bandpass ergänzt eine Trennwand und getrennte Front-/Rückkammern. Bei erkannten Geometriefehlern verweigert der Export Fertigungsunterlagen.

Erweiterungspunkte: weitere Treibertypen sind im Modell vorbereitet; zusätzliche Filterzweige sollten als echte Netlist statt weiterer fester 2-Wege-Topologien implementiert werden. Materialkatalog und Messdatenmodelle sind UI-unabhängig.

## Ergänzungen V3.4 (TASK-0029)

- `services/price_status.py` (Preiswahrheit), `services/variant_metrics.py` (Chips, Balken, Datenabdeckung, Empfehlungshinweis), `services/relaxation.py` (verifizierte Kombinationsvorschläge) sind UI-unabhängig und mypy-strikt.
- `targets/` (`smooth.py`, `eq.py`, `state.py`): PCHIP-Zielkurve und EQ-Bänder aus RBJ-Biquads; `SpeakerProject.target_eq_bands`.
- `library/readiness.py`, `library/coverage.py`: Readiness und Abdeckung werden aus dem Datensatz berechnet, nie gespeichert.
- `enclosure/treatment.py`: `AcousticTreatment` im Projekt (`treatments`); `DesignBundle.treatments` enthält abgeleitete und eigene Behandlungen. Stückliste, Anleitung, Zeichnungen (`drawings/treatment_svg.py`) und Szene lesen dieselbe Quelle.
- `enclosure/scene.py`: 3D-Szene aus Gehäuse, Frontelementen, Verstärkung und Behandlungen (keine eigene Geometrie). `ui/raster.py` (Z-Buffer) und `ui/scene_view.py` zeichnen sie; `HeroPreview` fällt auf 2D zurück, wo keine Szene existiert.
- `export/summary.py`: Gruppierung und Fertigungs-Zusammenfassung. `presentation.py`: deutsche Anzeigenamen (nur Präsentation).
- `ui/assistant_window.py` wurde in `sound_lab.py`, `result_text.py`, `assistant_files.py` aufgeteilt (Grenze 1500 Zeilen).

## Ergänzungen V-02.07.00

```text
crossover/three_way.py  three_way_network() + simulate_three_way()  (ladder per branch)  -> CrossoverDesign(ways=3)
services/design._crossover / _simulate_network  chooses 2- or 3-way
ui/layout_canvas.py + ui/history.py  interactive front layout, undo/redo over immutable snapshots
arrays.py  FloatArray / ComplexArray aliases;  drivers.Driver.require_vas_m3()
```

## Ergänzungen V-02.06.00

```text
DesignBundle ─┬─ export/cutting.py     guillotine nesting per plate thickness -> CuttingPlan -> CSV / SVG / PDF
              ├─ export/weight.py      plate volume x typical density range (no chassis mass is invented)
              ├─ export/assembly_guide.py  steps derived from bundle features (partition, coupler, horn, fold, port ...)
              └─ validation/prototype.py   FRD/ZMA vs. simulation -> PrototypeReport (+ port correction by solving the model)
acoustics/baffle_step.py + crossover/passive.baffle_step_compensation -> optional Lbs/Rbs in the woofer branch
appdata.py  user folder (LK_USER_DIR / LOCALAPPDATA): settings.json, recent.json, autosave/, logs/ (Qt-free)
ui/         cutting_panel, prototype_dialog, help_dialog; assistant_window: menu, recent, autosave, unsaved prompt
__init__.py single version source (__version__ -> REVISION), used by UI, project model and checked by tests
```

Kernpakete bleiben Qt-frei (`appdata`, `validation`, `export`). Das Programmprotokoll hängt an einem Logger `lautsprecher_konstruktion`;
unbehandelte Ausnahmen (auch aus Arbeitsthreads) werden protokolliert und im GUI-Thread angezeigt.
