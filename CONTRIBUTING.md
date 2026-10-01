# Contributing

Alle Beiträge benötigen:

- eindeutige Task-ID
- eigenen Branch
- Einhaltung der Ownership-Regeln
- passende Tests
- aktualisierte Dokumentation
- Handoff
- Review vor Integration

Branch-Beispiele:

- `agent1/TASK-0001`
- `agent2/TASK-0002`
- `codex/TASK-0003`
- `manual/TASK-0004`


## CI-sparsamer Pull-Request-Ablauf

1. Task-Branch anlegen.
2. PR früh als **Draft** öffnen.
3. Während der Implementierung lokal testen und Änderungen sinnvoll bündeln.
4. Keine direkte Entwicklung auf `main`.
5. Erst nach lokal grünem, zusammenhängendem Stand den PR auf **Ready for review** setzen.
6. Die Cloud-CI validiert diesen Integrationsstand.
7. Muss danach wieder umfangreich gearbeitet werden, PR erneut auf Draft setzen; finale CI bei Bedarf manuell wiederholen.
