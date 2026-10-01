# Release Rules

## Versionsschema

`Repositoryname_V-01.00.02`

- erste Zahl = Hauptrelease
- zweite Zahl = Anzahl akzeptierter neuer Features seit dem letzten Hauptrelease
- dritte Zahl = Anzahl akzeptierter Fixes seit der aktuellen Feature-Version

## Zählregeln

### FEATURE
Ein fachlich zusammengehöriges, akzeptiertes Feature-Ticket erhöht den mittleren Zähler genau einmal.

Untertasks, Tests, Dokumentation und interne Refactorings erhöhen den Feature-Zähler nicht separat.

Beispiel:

`V-01.03.04 → FEATURE → V-01.04.00`

Der Fix-Zähler wird bei jedem Feature auf `00` zurückgesetzt.

### FIX
Ein akzeptierter Fehler-Fix erhöht den letzten Zähler genau einmal.

Beispiel:

`V-01.04.00 → FIX → V-01.04.01`

### MAJOR
Ein Hauptrelease ist eine bewusste Releaseentscheidung für eine größere Entwicklungsstufe mit mehreren wesentlichen Änderungen.

Beispiel:

`V-01.12.03 → MAJOR → V-02.00.00`

Feature- und Fix-Zähler werden auf `00` zurückgesetzt.

## Release Candidate

`Repositoryname_V-02.00.00-RC1`

RC-Nummern verändern die drei eigentlichen Versionszähler nicht.

## Verbindliche Dateien

- `VERSION`
- `coordination/VERSION_LEDGER.yaml`
- `CHANGELOG.md`
- `coordination/RELEASE_CHECKLIST.md`

`VERSION` und `VERSION_LEDGER.yaml` müssen übereinstimmen. Der Quality Gate prüft dies automatisch.

## Zuständigkeit

Versionsnummern werden zentral durch Agent 5 bzw. den definierten Integration-/Releaseprozess verwaltet. Andere Agents dürfen die Release-Version nicht eigenmächtig ändern.


## GitHub Release Boundary

A commit on `main` is not automatically a published release.

Before a release is considered published:
- the target version is accepted,
- required user tests are `USER_TEST_PASSED`,
- release-blocking validation is complete,
- CHANGELOG and known limitations are current,
- the tag matches the version,
- distributable artifacts are associated with that exact source revision.

When GitHub Actions budget is unavailable, build/test evidence may be local and explicitly labeled as such. Skipped cloud CI must never be represented as a passing cloud run.
