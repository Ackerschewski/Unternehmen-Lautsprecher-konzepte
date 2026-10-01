# Repository Naming and Placement Rules

Diese Regeln gelten für neue Projekte.

## Kategorien

| Kategorie | Repository-Präfix | GitHub-Owner |
|---|---|---|
| PRIVAT | `Privat-` | `Ackerschewski` |
| WORK | `Work-` | `Ackerschewski` |
| UNTERNEHMEN | `Unternehmen-` | `Ackerschewski` |
| BASIS | `Basis-` | `Ackerschewski` |

Das Template selbst ist `Ackerschewski/Basis-Project-Template`.

## Bedeutung

- PRIVAT: persönliche/private Projekte.
- WORK: Ausbildung, Arbeitgeber und berufliche Hilfsprogramme.
- UNTERNEHMEN: eigene kommerzielle Produkte, Company OS, Website und Produktentwicklung.
- BASIS: gemeinsame Standards, Infrastruktur, Templates und Design-Grundlagen.

## Repository-Name

`<prefix><project-slug>`

Der neue Projekt-Slug soll bevorzugt lowercase kebab-case verwenden. Bereits migrierte Bestandsnamen dürfen ihre bisherige Schreibweise behalten, solange das Kategoriepräfix korrekt ist.

Beispiele:
- `Privat-bearing-visualizer`
- `Work-inventor-drawing-automation`
- `Unternehmen-jewelry-generator`
- `Basis-project-template`

Versionen gehören nicht in Repository-Namen.

## Release-/Programmname

Artefakte:

`<repository-name>_V-01.00.02`

## Topics

Mindestens der Klassifikations-Topic:
- `privat`
- `work`
- `unternehmen`
- `basis`

Zusätzliche technische Topics bleiben empfohlen.

## Migration

Nach einer GitHub-Umbenennung müssen kanonische Full-Names in Metadaten, Agent-Profilen, Portfolio-Routing, Company OS, CI/Deployment und Automationen aktualisiert werden. GitHub-Redirects gelten nur als Übergangskompatibilität.
