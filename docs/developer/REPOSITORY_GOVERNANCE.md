# Repository Governance

## Zweck

Repository-Zuordnung, Benennung und Metadaten müssen für Menschen, ChatGPT, Codex, Agents und Company OS eindeutig sein.

## Verbindliche Kategorien

Jedes Repository gehört genau einer Hauptkategorie an.

| Kategorie | Präfix | Bedeutung | GitHub-Owner |
|---|---|---|---|
| PRIVAT | `Privat-` | persönliche/private Projekte | `Ackerschewski` |
| WORK | `Work-` | Ausbildung, Arbeitgeberkontext und berufliche Hilfsprogramme | `Ackerschewski` |
| UNTERNEHMEN | `Unternehmen-` | eigene kommerzielle Produkte, Company OS, Website und Produktentwicklung | `Ackerschewski` |
| BASIS | `Basis-` | gemeinsame Standards, Infrastruktur, Templates und Design-Grundlagen | `Ackerschewski` |

Die früheren Klassen PRIVATE / WORK / SELF_EMPLOYED sowie die Präfixe `private-`, `work-` und `ac-` sind nicht mehr kanonisch.

## Source of Truth

Die maschinenlesbare Zuordnung liegt in `coordination/REPOSITORY_METADATA.yaml`.

Wenn tatsächlicher GitHub-Owner oder Repository-Name davon abweicht, muss die Metadatendatei oder die GitHub-Struktur bewusst korrigiert werden. GitHub-Redirects gelten nur als Übergangskompatibilität.

## Repository vs. Release

Repository:
`Unternehmen-jewelry-generator`

Versioniertes Artefakt:
`Unternehmen-jewelry-generator_V-01.04.03`

Versionen werden niemals in den dauerhaften Repository-Namen eingebaut.

## Topics und Views

Mindestens ein Klassifikations-Topic:
- `privat`
- `work`
- `unternehmen`
- `basis`

Saved Views sind nur Ansichten und keine Source of Truth.

## Migration bestehender Projekte

Nach einer Umbenennung müssen harte Repository-Referenzen in Metadaten, Agent-Profilen, Portfolio-Routing, Company OS, Linear, CI/Deployment, Dokumentation und Automationen aktualisiert werden.

Transfers oder Umbenennungen werden als Infrastructure-/Maintenance-Task dokumentiert, wenn CI, externe Integrationen, Clone-URLs oder Automationen betroffen sind.
