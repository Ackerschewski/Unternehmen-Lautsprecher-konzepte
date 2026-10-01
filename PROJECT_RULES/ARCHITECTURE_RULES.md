# Architecture Rules

## Standardmodule

- `src/domain/`: Fachlogik, Modelle, Regeln, Algorithmen
- `src/application/`: Use Cases und Orchestrierung
- `src/ui/`: UI und Präsentationslogik
- `src/integrations/`: Host-APIs und externe Systeme
- `src/infrastructure/`: Dateisystem, Persistenz, Konfiguration
- `src/diagnostics/`: Logging und Diagnose
- `src/common/`: kleine gemeinsame Hilfsbestandteile

## Harte Regeln

- Domain kennt keine UI.
- Domain importiert keine Host-API.
- UI implementiert keine Fachalgorithmen.
- Externe Systeme werden über Adapter gekapselt.
- Keine zyklischen Modulabhängigkeiten.
- Öffentliche Contracts werden dokumentiert und kontrolliert geändert.
