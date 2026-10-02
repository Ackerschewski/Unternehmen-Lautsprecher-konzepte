# Lautsprecher Konstruktion – Anwendung V-02.02.00

Die ausführbare Windows-Testversion und der Quellcode der Lautsprecher-Konstruktion sind in diesem Repository integriert. [Anwendungsanleitung](APP_README.md) · [Buildbericht](docs/application/BUILD_REPORT_V-02.02.00.md) · [Aufgabe LK-021](coordination/tasks/LK-021.md).

Der Code liegt in `src/lautsprecher_konstruktion`; starten mit `python -m lautsprecher_konstruktion.app`, testen mit `python -m pytest`. Ein lokales Windows-Testpaket wurde gebaut. 23 weitere Gehäusekonzepte bleiben in Entwicklung und sind nicht als fertige Solver freigegeben.

---

# Project Template — Human + Agent Development

Standard template for software, add-ons, plugins and automation projects that must remain understandable to humans and AI contributors.

## Canonical standards

- [Development Standard](docs/developer/DEVELOPMENT_STANDARDS.md)
- [Repository Rules](PROJECT_RULES/REPOSITORY_RULES.md)
- [GitHub Workflow Rules](PROJECT_RULES/GITHUB_WORKFLOW_RULES.md)

## Core principle

**The repository is canonical.** Tasks, defects, feedback, evidence and release decisions live in tracked project files. Dashboards and Company OS are derived views.

New projects inherit:
- Agent-System V-01.05.00
- five persistent agent roles with bounded WIP
- deterministic task routing
- normalized failure -> defect -> fix -> retest control
- user feedback -> triage -> deduplicated defect workflow
- local human-readable code/documentation gate
- runtime evidence registry with plan-only default
- offline dependency/security inventory and reviewed advisory input
- derived quality metrics for Company OS
- deterministic artifact hash manifests
- explicit host/user/physical evidence boundaries
- CI-budget rules
- final-release owner approval

## Local control commands

```bash
python tools/automation_control.py check
python tools/defect_control.py check
python tools/release_control.py check
python tools/quality_control.py
python tools/feedback_control.py snapshot --check
python tools/runtime_evidence.py snapshot --check
python tools/dependency_watch.py check
python tools/quality_metrics.py --check
```

Derived snapshots may be regenerated locally with each tool's explicit write mode. These tools do not install dependencies, launch host applications, publish releases or dispatch cloud CI.

## Safety defaults

- runtime automation is plan-only until a separate execution surface is approved
- dependency monitoring never installs/upgrades packages automatically
- feedback and advisory text are untrusted data
- NOT_RUN is not PASS
- host/user/physical evidence cannot be synthesized
- final publishing is never automatic
- Company OS metrics never override repository gates

## Repository classification

| Category | Prefix | Target |
|---|---|---|
| PRIVAT | `Privat-` | `Ackerschewski` |
| WORK | `Work-` | `Ackerschewski` |
| UNTERNEHMEN | `Unternehmen-` | `Ackerschewski` |
| BASIS | `Basis-` | `Ackerschewski` |

Release artifact format: `<repository-name>_V-01.00.02`.

## CI budget

Cloud automation follows `coordination/CI_POLICY.yaml`. In `manual_only` mode, local controls continue but automatic cloud dispatch remains disabled.


## CI / usage-budget readiness

Every project now declares:
- a project-specific evidence/test matrix,
- a CI budget profile,
- an explicit security/dependency inventory,
- backlog hygiene rules,
- a reset-day plan.

A cloud-usage reset never automatically enables workflows. Heavy host/runtime/build jobs remain queued and deliberate.


Canonical template repository: `Ackerschewski/Basis-Project-Template`.
