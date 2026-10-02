# Migration von V-01.00.00 zu V-01.01.00

## Ausgangslage

V-01.00.00 hatte ein validiertes `SpeakerProject` und `DesignBundle`, vier Gehäusefamilien, Messdatenimport, Fertigungsunterlagen und einen technischen PySide6-Editor. Der Editor verlangte schon beim Start T/S-Werte. Eine Komponentenbibliothek, Kandidatenauswahl und ein einfacher Projektablauf fehlten. Die Gehäusevorbereitung lag vollständig in `services/design.py`.

## Umsetzung

1. `Driver` nur um nullable, SI-basierte Hersteller-/Geometriefelder ergänzt; alte Projektdateien bleiben lesbar.
2. Lokale `ComponentLibrary` mit JSON/CSV, In-Memory-Index, deaktivierbaren Datensätzen und beschreibbaren Benutzerdaten eingeführt. Nur klar markierte synthetische Beispiele ausgeliefert.
3. `EnclosureTypeRegistry` und getrennte Strategien für die vier belegbaren Solver geschaffen. Weitere Familien sind ausdrücklich `PLANNED` und nicht berechenbar.
4. Soundprofile, Machbarkeitsfilter, Dimensionensuche, Simulationsbewertung, begründete Ergebnisse und Abbruchsignal in einem UI-unabhängigen Dienst eingeführt.
5. Neue `AssistantWindow` als Standardstart; der bisherige `MainWindow` bleibt Expertenmodus. Beide verwenden `SpeakerProject` und `DesignBundle`, weitere Treiber und Zubehör sind Bestandteil des Projekts.
6. Fünf reproduzierbare Demo-Szenarien, Integrationstests, Build und lokaler Smoke-Test ergänzt.

## Offene Arbeit

Sechster Bandpass, isobarische Systeme, Open Baffle, Transmission Line/MLTL und Hörner brauchen eigene belastbare Solver, Geometrie- und Messvalidierung. Auch echte Komponenten- und Preisdaten, 3D-CAD, aktives DSP und 2,5-/3-Wege-Weichen fehlen. Keine dieser Fähigkeiten wird als unterstützt ausgegeben.
