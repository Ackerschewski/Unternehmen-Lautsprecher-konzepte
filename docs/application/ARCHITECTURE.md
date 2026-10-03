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
