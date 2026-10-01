# CI Workflows

Dieses Template verwendet standardmäßig eine **Low-Usage-CI** für Projekte mit Menschen, ChatGPT, Codex und mehreren Agents.

## Standard

1. Agent-Branches: lokal testen, keine Push-CI.
2. Aktive Pull Requests: als **Draft** führen; Runner-Jobs werden dort übersprungen.
3. Integrationsgrenze: PR erst nach lokalem Test auf **Ready for review** setzen; dann läuft die relevante schnelle CI.
4. Weitere Validierung: bewusst über `workflow_dispatch` starten.
5. Schwere Plattform-/Runtime-/Packaging-Jobs: ausschließlich bewusst manuell, sofern kein dokumentierter Projektgrund etwas anderes erfordert.
6. Wiederholbare Jobs: `concurrency` + `cancel-in-progress: true`.
7. Generierte Dateien und Koordinationsrauschen dürfen keine CI-Kaskaden erzeugen.
8. Windows/macOS nur verwenden, wenn eine plattformspezifische Prüfung nötig ist.
9. Kurze Artifact-Retention verwenden, standardmäßig 3 Tage für temporäre Testartefakte.
10. Dashboard primär lokal mit `python tools/generate_dashboard.py` erzeugen; der Actions-Workflow ist nur Fallback.

Der projektspezifische Stack wird erst nach dem Projekt-Intake ergänzt. Blender/Python, Inventor/.NET, Unreal und andere Projekte erhalten jeweils nur die tatsächlich benötigten Jobs.

Die vollständige Policy mit Beispielen liegt in `docs/developer/CI_EFFICIENCY.md`.
