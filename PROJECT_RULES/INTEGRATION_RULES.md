# External Integration and Plugin Rules

Externe Plugins, Connectoren und Dienste sind erlaubt, wenn sie den Projektablauf messbar vereinfachen.

## Grundregel

**GitHub bleibt die Source of Truth für Projektzustand und Entwicklung.**

Externe Systeme dürfen GitHub ergänzen, aber nicht ohne ausdrückliche Architekturentscheidung ersetzen.

## Sinnvolle Integrationen

Geeignet sind Dienste, die einen klaren zusätzlichen technischen Nutzen liefern, zum Beispiel:

- Deployment
- Fehler-/Crash-Monitoring
- Telemetrie und Observability
- Benachrichtigungen
- Artefaktspeicherung
- externe Testumgebungen
- dokumentierte Unternehmenssysteme
- automatisierte Browser-/Host-Workflows

## Nicht sinnvoll als Standard

Nicht standardmäßig integrieren, wenn ein Tool hauptsächlich dieselben Daten erneut verwaltet:

- zweite Task-Liste
- zweites Kanban-Board
- parallele Release-Liste
- paralleles Blackboard
- zweite technische Dokumentation

## Zulassung einer Integration

Vor Aufnahme prüfen:

1. Welchen konkreten manuellen Schritt ersetzt sie?
2. Welche Daten liest sie?
3. Welche Daten schreibt sie?
4. Entsteht doppelte Projektwahrheit?
5. Was passiert bei Ausfall des Dienstes?
6. Sind Secrets erforderlich?
7. Welche Lizenz-/Kostenfolgen entstehen?
8. Ist die Integration für alle Projekte oder nur projektspezifisch sinnvoll?

## Source-of-Truth-Regel

Wenn externe Daten GitHub beeinflussen, muss klar definiert sein:

- Richtung des Datenflusses
- Owner
- Konfliktregel
- Fehlerverhalten
- Logging
- Berechtigungen

## Projektmanagement-Dienste

Linear, monday.com, Coda oder ähnliche Systeme werden nicht pauschal eingebaut.

Sie dürfen projektspezifisch eingesetzt werden, wenn sie einen echten Zusatznutzen liefern. GitHub-Tasks, Specs, Architektur, Versionierung und Handoffs bleiben ansonsten kanonisch.

## Observability / Deployment

Dienste wie Datadog, PostHog oder Vercel sind sinnvolle optionale Integrationen für passende Web-/Server-/Produktprojekte, aber kein Bestandteil des allgemeinen Templates.

## Agenten

Agents dürfen keine neue externe Integration ohne dokumentierte Task und begründete Entscheidung hinzufügen.
