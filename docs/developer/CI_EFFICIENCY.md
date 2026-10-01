# CI Efficiency Policy

## Ziel

GitHub Actions soll Integrationsfehler zuverlässig erkennen, ohne jeden Agent-Mikro-Commit als kostenpflichtigen Build zu behandeln. Der normale schnelle Feedback-Loop läuft lokal; GitHub Actions prüft Integrationspunkte.

## Trigger-Modell

### Agent- und Feature-Branches

Kein globales `push:`. Ein Agent darf viele lokale Änderungen und Commits erzeugen, ohne pro Commit einen Cloud-Runner zu starten.

### Pull Requests

Schnelle Tests dürfen bei `pull_request` laufen, aber nur für relevante Pfade. Verwende beispielsweise:

```yaml
on:
  pull_request:
    paths:
      - "src/**"
      - "tests/**"
      - ".github/workflows/ci.yml"
```

Dokumentation, Blackboard, Handoffs und andere reine Koordinationsdateien sollen keine Produkt-Builds starten.

### Pull-Request-Lebenszyklus

Für agentenintensive Projekte ist das Standardmodell:

1. PR früh als **Draft** öffnen.
2. Während der Implementierung lokal testen; Draft-PR-Jobs werden übersprungen.
3. Erst nach lokal grünem, kohärentem Slice auf **Ready for review** setzen.
4. Die Cloud-CI validiert diesen Integrationsstand.
5. Bei neuer größerer Arbeit den PR wieder auf Draft setzen oder die finale Prüfung bewusst manuell erneut starten.

Workflow-Muster:

```yaml
on:
  pull_request:
    types: [opened, synchronize, reopened, ready_for_review]
    paths:
      - "src/**"
      - "tests/**"
  workflow_dispatch:

jobs:
  test:
    if: github.event_name != 'pull_request' || github.event.pull_request.draft == false
```

Direkte Entwicklung auf `main` ist im Standard-Agentenprozess nicht vorgesehen. Dadurch entfällt der doppelte Cloud-Build nach einem bereits geprüften PR.

### Schwere Jobs

Blender-Runtime-Downloads, Windows-Runner, Inventor-nahe Builds, Packaging, große Matrix-Tests, Evidence-Erzeugung und Projektmetriken werden bevorzugt manuell ausgeführt:

```yaml
on:
  workflow_dispatch:
```

Wenn ein schwerer Job automatisch notwendig ist, soll er auf `main` statt auf jedem Agent-Branch laufen.

## Concurrency

Jeder Workflow, bei dem nur der neueste Stand relevant ist, verwendet:

```yaml
concurrency:
  group: ci-${{ github.event.pull_request.number || github.ref }}
  cancel-in-progress: true
```

Damit werden veraltete lange Läufe abgebrochen.

## Runner-Wahl

- Linux zuerst, wenn keine Plattformbindung besteht.
- Windows nur für echte Windows-/PowerShell-/.NET-Plattformvalidierung.
- macOS nur für echte macOS-Anforderungen.
- Keine Runner-Matrix aus Vorsicht; jede zusätzliche Plattform braucht einen konkreten Testgrund.

## Jobs sinnvoll zusammenfassen

GitHub rechnet Runner-Zeit jobweise. Viele Sekunden-Jobs können dadurch teurer sein als ein zusammengefasster kurzer Job. Zusammengehörige schnelle Prüfungen deshalb in einem Job bündeln, solange Isolation keinen klaren Qualitätsvorteil bringt.

## Artifacts

- Temporäre Test-/Evidence-Artefakte: standardmäßig 3 Tage.
- Release-Artefakte: projektspezifisch länger.
- Keine Artefakte hochladen, die im Repository bereits deterministisch reproduzierbar sind, außer sie werden für Review oder Runtime-Nachweise benötigt.

## Bot-Commits

Ein Workflow, der selbst Dateien committen kann, muss Folgeläufe verhindern. Dafür Path-Filter, Actor-Filter oder klar getrennte generierte Pfade verwenden. Ein Dashboard-Refresh darf beispielsweise keinen neuen vollständigen Quality-Build starten.

## Agent-Verhalten

Agents sollen:
- vor Push lokale Tests ausführen,
- Mikro-Änderungen zu kohärenten Arbeitsblöcken bündeln,
- bestehende CI nicht durch neue globale Trigger erweitern,
- bei neuen Workflows immer Path-Filter, Runner-Kosten und Concurrency prüfen,
- keine Cron-/Schedule-Automation ohne dokumentierten Bedarf ergänzen.

## Empfohlenes Standardprofil

Für die meisten neuen Projekte:

- schneller Linux-Test: finaler, nicht-draft PR + manuelle Wiederholung bei Bedarf
- plattformspezifischer Test: manuell
- Runtime-/End-to-End-Test: manuell
- Packaging/Release: Tag, Release oder manuell
- Dashboard/Metadaten: nur relevante Pfade
- Dokumentation-only: kein Produkt-Build

## Review-Checkliste für neue Workflows

Vor Merge eines neuen oder geänderten Workflows:

- Ist `push:` auf Branches/Pfade begrenzt?
- Läuft derselbe Test unnötig gleichzeitig für Push und PR?
- Gibt es `concurrency`?
- Kann ein Bot-Commit einen zweiten Lauf auslösen?
- Muss dieser Job wirklich Windows/macOS verwenden?
- Kann ein schwerer Job manuell laufen?
- Sind mehrere Minijobs sinnvoll zusammenfassbar?
- Ist Artifact-Retention kurz genug?
- Werden reine Docs-/Coordination-Änderungen ausgeschlossen?
- Gibt es einen lokalen Testbefehl als primären Agent-Feedback-Loop?


## Dashboard

`python tools/generate_dashboard.py` ist der Standardweg und wird lokal vor Review ausgeführt. Der GitHub-Workflow `Update Project Dashboard` bleibt als manueller Fallback verfügbar, startet aber nicht automatisch bei jedem Status-/Main-Commit.
