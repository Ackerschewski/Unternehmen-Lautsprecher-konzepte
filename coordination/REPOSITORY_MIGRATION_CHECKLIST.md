# Repository Migration Checklist

Für Umbenennung oder Neu-Klassifikation eines bestehenden Repositories.

## 1. Klassifikation
- [ ] Kategorie festgelegt: PRIVAT / WORK / UNTERNEHMEN / BASIS
- [ ] korrektes Präfix festgelegt: Privat- / Work- / Unternehmen- / Basis-
- [ ] Owner `Ackerschewski` bestätigt
- [ ] Projekt-Slug festgelegt
- [ ] erwarteter neuer Full Name dokumentiert

## 2. Vor der Umbenennung
- [ ] offene Pull Requests geprüft
- [ ] laufende GitHub Actions geprüft
- [ ] externe Webhooks / Integrationen erfasst
- [ ] lokale Clone-/Remote-Nutzer erfasst
- [ ] Dokumentation auf alte URLs durchsucht
- [ ] CI-/Deployment-Konfiguration auf harte Repo-URLs geprüft
- [ ] Secrets-Namen und Environment-Bezüge geprüft
- [ ] Abhängigkeiten anderer Repositories geprüft
- [ ] Linear-/Company-OS-Verweise erfasst

## 3. Umbenennung
- [ ] Repository umbenannt
- [ ] Kategoriepräfix stimmt
- [ ] Default Branch weiterhin korrekt
- [ ] Template-/Merge-Einstellungen geprüft
- [ ] Sichtbarkeit geprüft

## 4. Nach der Umbenennung
- [ ] `coordination/REPOSITORY_METADATA.yaml` aktualisiert
- [ ] `coordination/PROJECT_STATE.yaml` aktualisiert
- [ ] Agent-System-/Template-Referenzen aktualisiert
- [ ] Portfolio-Routing / Company OS aktualisiert
- [ ] Linear-Verweise aktualisiert
- [ ] GitHub Topics aktualisiert
- [ ] lokale Remotes aktualisiert
- [ ] Dokumentation aktualisiert
- [ ] Integrationen/Webhooks aktualisiert
- [ ] CI-Policy auf Low-Usage-Standard geprüft
- [ ] `python tools/validate_project.py` erfolgreich oder Abweichung dokumentiert
- [ ] alte Parallelkopien vermieden oder bewusst archiviert

## 5. Abschluss
- [ ] Migration als INFRA-/Maintenance-Task dokumentiert
- [ ] Handoff / Abschlussnotiz erstellt
- [ ] alte Namen werden nicht mehr als kanonische Source of Truth verwendet
