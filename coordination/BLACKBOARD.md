# Blackboard — V-02.00.00

## TASK-0028 · V3.3 Visual Acceptance Sprint – umgesetzt

- Planner-UI und Geometrie-Branch zusammengeführt (Merge `3f3f11b`), Vorgaben-Schublade, Ergebnis-Hero, Variantenleiste, Zeichnungs-Workspace, Sound Lab mit einem Sekundärdiagramm, Diagnosekarte mit geprüften Vorschlägen.
- Wurzelursache der unlesbaren Zeichnungen gefunden und behoben: Qt-SVG ignoriert die CSS-Kurzschreibweise `font:`.
- Evidence: `coordination/feedback/evidence/2026-10-07-v3-3/`; Report: `docs/application/BUILD_REPORT_TASK_0028.md`. Windows/DPI: NOT_RUN.

## IN ARBEIT: TASK-0029 · Product Truth & Depth Sprint

- Verbindlich: `coordination/tasks/TASK-0029.md`; Reihenfolge Korrektheit → EQ → Library → Dämmung → 3D → Varianten/Diagnosen → Fertigung → Polish.

## NEXT: TASK-0029 · Product Truth & Depth Sprint

- **Priorität: CRITICAL · Owner: Claude Code · Status: READY.**
- Verbindliches Paket: `coordination/tasks/TASK-0029.md`.
- Review-Grundlage: `coordination/feedback/2026-10-07-V3-3-REVIEW.md`.
- Arbeitsbasis ist der aktuelle Stand auf `claude/modest-bell-guqoxu`, nicht `main`.
- TASK-0028/V3.3 ist umgesetzt und visuell geprüft; Buildreport: `docs/application/BUILD_REPORT_TASK_0028.md`.
- TASK-0027 wurde im TASK-0028-Buildreport ausdrücklich als **nicht umgesetzt** dokumentiert. Die offenen TASK-0027-Inhalte sind deshalb verbindlicher Bestandteil von TASK-0029; nicht separat überspringen.
- Reihenfolge: **Korrektheit → Smooth/parametrischer EQ → Library Readiness → Dämmung → 3D → Varianten/Diagnostik → Fertigung → UI-Polish → Evidence**.
- Kritischer Korrektheitsfehler: Varianten dürfen nicht als `Günstiger` bezeichnet werden, wenn Vergleichspreise unvollständig/nicht vergleichbar sind.
- Weitere Pflichtpunkte: Null-Zähler aus Status, saubere deutsche User-Texte, vollständige Diagnosemeldungen mit Einheiten, Multi-Constraint-Relaxation, gruppierte Fertigung.
- Neue Evidence-Serie: `coordination/feedback/evidence/2026-10-07-v3-4/`.
- Autonomous execution: nach Teilpaketen nicht auf ein neues "mach weiter" warten; funktionsfähigen grünen Stand hinterlassen.
- Windows/DPI bleibt `NOT_RUN`, solange kein echter Windows-Test ausgeführt wurde.

## LONG-RANGE ROADMAP: TASK-0030 → TASK-0050

- Vollständige Abhängigkeits-/Phasenübersicht: `coordination/tasks/ROADMAP_TASK_0030_0050.md`.
- TASK-0029 bleibt **unmittelbar NEXT**; TASK-0030–0050 sind große geplante Folge-Workstreams.
- Alle TASK-0030 bis TASK-0050 sind mindestens auf TASK-0028-Planungstiefe erweitert und enthalten Architektur, Core, UI, Migration, Tests, Evidence, Performance und Handoff.
- Reihenfolge grob:
  - 0030–0032: Solver-Vertrauen, Bibliothek, Geometriekern
  - 0033–0038: Weiche/DSP/Messung/Directivity/Raum/Spezialgehäuse
  - 0039: automatische Systemsynthese/Pareto
  - 0040–0042: CAD/Fertigung/Beschaffung/Materialmechanik
  - 0043–0049: V4 Workspace, Projektlebenszyklus, Performance, Plugins, Reliability, QA, Doku
  - 0050: V4 Integration und Release Gate
- Claude darf Tasks nicht blind numerisch starten, wenn deren Dependencies fehlen. In diesem Fall Dependency zuerst oder Task BLOCKED markieren und einen unabhängigen Workstream wählen.
- TASK-0050 darf keine neue große Featurewelle starten; Veröffentlichung bleibt Owner-gated.

## COMPLETED: TASK-0028 · V3.3 Visual Acceptance Sprint

- Responsive Planner Drawer, Result Hero, Variantenkarten, Drawing Workspace, Sound-Lab-Struktur und Diagnostic Card umgesetzt.
- Evidence Dark/Light für 1280×720 und 1920×1080 vorhanden.
- Zeichnungen deutlich besser lesbar; Planungsleiste wird nach Ergebnis reduziert.
- Offene Punkte aus Review wurden in TASK-0029 übernommen.

## SUBSUMED: TASK-0027 · Product Depth Sprint

- Smooth EQ, Library Readiness, Dämmung und 3D wurden bisher **nicht umgesetzt**.
- Die technische Detail-Spezifikation in `TASK-0027.md` bleibt gültig.
- Umsetzung erfolgt jetzt innerhalb von TASK-0029, damit keine weitere UI-Runde diese Kernfunktionen erneut verdrängt.

## Task TASK-0025 · 3-Wege-Weiche, Frontlayout, Typprüfung / V-02.07.00

- Bearbeitet durch Claude Code auf `claude/modest-bell-guqoxu` · Status: technisch geprüft (Linux/Offscreen), Benutzerprüfung ausstehend.
- Passive 3-Wege-Weiche mit exakter Kettenschaltungs-Simulation; interaktives Frontlayout (Ziehen, Einrasten, Pfeiltasten) mit Rückgängig/Wiederholen; `mypy --strict` für alle Nicht-UI-Pakete.
- 228 Pytest-Fälle, Ruff, mypy, Smoke. NOT_RUN: Windows-Build, Sichttest, Messvalidierung.

## Task TASK-0024 · Zuschnitt, Bauanleitung, Prototypvergleich / V-02.06.00

- Bearbeitet durch Claude Code auf `claude/modest-bell-guqoxu` · Status: technisch geprüft (Linux/Offscreen), Benutzerprüfung ausstehend.
- Zuschnittplan mit Sägeschnitt, Gewichtsbereich, Bauanleitung, Prototypvergleich (UI und Kommandozeile), Schallwandkorrektur, Referenztests, Benutzerdaten (Zuletzt geöffnet, Autosave, Protokoll), Hilfe.
- Gesamtplan zur fertigen Version: `docs/application/PLAN_V-03.00.00.md`. Nicht ausgeführt: Windows-Build, Sichttest, Messvalidierung (NOT_RUN).
- Die Aufgaben LK-021..023 heißen jetzt TASK-0021..0023, weil das Template-Gate das Schema `TASK-NNNN` verlangt.

## Task LK-023 · Alle Gehäusetypen / V-02.05.00

- Owner/Arbeitsbereich: lokale Integration · Status: implementiert und technisch geprüft, Benutzerprüfung ausstehend.
- Alle 29 Katalogtypen haben berechenbare Geometrie und akustische Vorschau. Front-Horn und Tapped-Horn besitzen eigene Solver und Fertigungs-DXF/PDF/SVG.
- Der automatische Assistent kann beide Hornarten bei ausreichenden Baumaßen auswählen. Erkannte mechanische Fehler sperren den Export.
- 95 Pytest-Fälle, Ruff, Windows-Build und Offscreen-Starttest bestanden. Lineare Modelle, keine Messfreigabe oder vollständige 3D-Kollisionsprüfung.

## Task LK-022 · Bandpass 6 parallel

- Owner/Arbeitsbereich: lokale Integration · Status: Benutzerprüfung ausstehend.
- Siebter unterstützter Gehäusetyp mit zwei externen Ports, getrennten Kammern/Abstimmungen, Zweiport-Simulation und geometrischer Portlängenprüfung.
- Front-/Rückwand-DXF, Gesamtblatt, Schnitt, PDF, Stückliste und Simulations-CSV führen BR1 und BR2 getrennt.
- Das Modell nimmt kohärent zusammengefasste Auslässe, lineare Kleinsignale und verlustfreie Ports an; keine Messvalidierung. Die serielle Variante bleibt in Entwicklung.
- 60 Pytest-Fälle, Ruff, Windows-Build mit Offscreen-Smoke sowie Fertigungspaket und SVG-Vorschau bestanden. Code und Dokumentation liegen in Draft-PR #4, die ZIP-Dateien im unveröffentlichten Test-Release.

## Task LK-200 · Zeichnung, UI und Fertigungspläne

- Owner/Arbeitsbereich: lokale Integration · Status: abgeschlossen.
- Assistent zeigt zoombare SVG-Blätter, Einzelteilpläne, Variantenvergleich und vier Tieftonplots. Änderungen an Vorgaben markieren bestehende Ergebnisse als veraltet.
- Einzelteil-SVG und DXF teilen Maße und lokalen Koordinatenursprung; PDF zeigt die Einzelteile und die berechneten Strebenpositionen. Maßblatt-Tabellen wachsen nach Bedarf.
- Sechs zuvor unterstützte Gehäusetypen bleiben erhalten; weitere Typen ohne belastbares Modell bleiben sichtbar, aber deaktiviert.
- Kein GitHub-Einsatz. 49 Tests, Ruff, lokaler und gepackter UI-Smoke erfolgreich; PDF-Zeichnungen visuell geprüft.

## Task LK-105 · Isobarik, Innenaufbau und Bibliothek
- Owner/Arbeitsbereich: lokale Integration · Status: abgeschlossen.
- Zwei isobarische Typen teilen den geprüften Rechteck-/Port-Kern. Koppelrohr, Ring, Tandemtiefe und Kollisionsprüfung sind im `DesignBundle` verankert. Ideale Kopplung ist eine dokumentierte Modellannahme.
- Streben-Tiefenpositionen sind für Prüfung und Zeichnung identisch. Das neue Innenaufbau-Maßblatt wird exportiert und im Assistenten angezeigt.
- Bibliothek: Dayton Audio plus neue belegte Visaton- und Scan-Speak-Einträge. Unvollständige Herstellermessdaten und Maße wurden nicht ergänzt.
- Kein GitHub-Einsatz. 47 Tests, Ruff und Windows-Smoke erfolgreich; Innenaufbau-Vorschau sichtbar geprüft.

## Task LK-102 · Maßblatt und Herstellerbibliothek
- Owner/Arbeitsbereich: Integration, Zeichnung, Bibliothek · Status: abgeschlossen.
- Akzeptanz: berechnete Einbaukoordinaten und Innenmaße in UI, SVG, CSV und PDF; Herstellerdaten mit Quellen; geplante Gehäusearten nicht als berechenbar angeboten.
- Prüfung: 41 Tests, Ruff, lokaler und gepackter UI-Smoke; SVG visuell geprüft.
- Handoff: Nur vier Gehäusefamilien verfügen über eigene Solver. Nächster Typ erfordert Modell, Geometrie und Messvergleich. Keine Hersteller-Bohrkreise oder Gehäuseverdrängungen erfinden.

## Konstruktionsassistent V-01.01.00
- Lokaler Standardstart ist `AssistantWindow`; der bisherige `MainWindow` bleibt Expertenmodus und sendet berechnete `DesignBundle`-Ergebnisse zurück.
- Die Komponentenbibliothek verwaltet 6 synthetische Demo-Treiber sowie gekennzeichnete PR-, Port-, E12-, Hardware- und Materialeinträge. Benutzerimporte bleiben in LOCALAPPDATA.
- Vier Gehäusefamilien sind `SUPPORTED`; weitere Einträge sind `PLANNED` und werden vor einer Berechnung abgewiesen.
- Automatische Auswahl filtert Maße, Frequenzüberlappung, Volumen, Port, Xmax, Leistung und explizite Preis-/SPL-Grenzen. Fehlschläge erklären die Ursache.
- Fünf Szenarien sind reproduzierbar, inklusive einer bewusst unmöglichen Anforderung. Kein GitHub-Einsatz.

## Lokal abgeschlossene Integration
- ZIP V-00.02.00 als unveränderte Quelle entpackt und in einer lokalen Arbeitskopie erweitert.
- Kern, PySide6-Oberfläche und Fertigungsexport verwenden den aufgelösten `DesignBundle`.
- Vented-Solver, FRD/ZMA, komplexe Weiche, Frontlayout, Kollisionsprüfung und Schema 2 sind integriert.
- Synthetisches Demo-Projekt und numerische Regressionstests sind vorhanden.
- Windows-Onedir-Build startet im lokalen Offscreen-Smoke-Test erfolgreich; 21 Tests und Ruff sind grün.
- V-01 ergänzt Berechnungsstatus, Innenschnitt, Passivmembran, Zweikammer-Bandpass, Slot-Kanalwände und getrennte Platten-DXF; 26 Tests sind grün.

## Entscheidungen
- Kein GitHub, kein Push, kein PR, keine Actions oder Tags für diese Version.
- Alle internen Einheiten bleiben SI; UI/CSV formatieren benutzerfreundlich.
- Bei unvollständigen Treiberdaten keine absolute Bewegung, Geschwindigkeit, SPL oder Impedanz.
- Fertigungsexport blockiert erkannte Geometriefehler.
- Portgröße und Länge stammen aus dem gelösten Port, Frontlayout liefert die Position.
- Der Build entfernt die von PyInstaller falsch eingesammelte `icuuc.dll`, damit Qt die Windows-ICU mit passenden Exporten lädt.

## Offene Risiken
- Kleinsignalmodell und akustische Weichensumme sind noch nicht mit echten Messungen abgeglichen.
- 3D-Portfaltung, Schraubenfreiraum, Gehrungen und exakte Strebenöffnungen fehlen.
- Komponententoleranzen und Verlustwiderstände der passiven Weiche werden nicht modelliert.

## Nächster Meilenstein
Messvalidierung und vollständige 3D-Fertigungskontrolle, danach frei konfigurierbare Mehrwege-Netzwerke.

## V-02.01.00 · LK-020 abgeschlossen
- 73 Thomann-Produkte mit Preisquelle und Preisstand 02.10.2026 aufgenommen. Katalogeinträge ohne T/S bleiben sichtbar, werden aber nicht automatisch konstruiert.
- Vier FaitalPRO-Chassis besitzen zusätzlich Herstellerdatenblätter. Visaton B 200 und W 200 S haben verifizierte Preisstände.
- Chassiswahl und Variantenvergleich zeigen Chassispreise; BOM in UI/CSV/PDF zeigt Einzelpreis, Position und bekannte Teilsumme samt Anzahl fehlender Preise.
- 52 Tests, Ruff und Windows-Offscreen-Smoke bestanden. Lokales ZIP unter `outputs/V-02.01.00`.
## V-02.02.00 · LK-021 Umsetzung und Prüfung
- Gesamtbudget ab Konfiguration: alle kalkulierten Stücklistenpositionen zuzüglich 15 % Materialreserve; unbepreiste Chassis bestehen die Budgetprüfung nicht.
- Holz nach dokumentierten Flächenreferenzen, nicht spezifizierte Weichen-, Port- und Montageteile als klar markierte Planpreise.
- 84 Thomann-Katalogeinträge, davon acht FaitalPRO-Chassis mit separat belegten T/S- und Montagedaten.
- Gesamt-Fertigungsblatt als SVG: Vorderansicht, Rückansicht, Seitenschnitt, Einbau-/Bohrkoordinaten und Zuschnitt; fehlende Lochbilder werden ausgewiesen.
- Sechs Gehäusearten berechenbar; 23 weitere bleiben wegen fehlender Solver und Fertigungsgeometrie in Entwicklung.
- 55 lokale Pytest-Fälle bestanden; Windows-Build und GitHub-Integration stehen noch aus.


## Nutzerfeedback 2026-10-06 · ACK Studio UI und Zeichnungslesbarkeit

- Vollständige Review, direkte Nutzerkritik, neun Screenshots und konkreter Bewegungsplan: [Feedback und Abnahmekriterien](feedback/2026-10-06-ACK-STUDIO-UI-REVIEW-AND-MOTION.md).
- Nutzer empfindet die UI als zu technisch und wenig angenehm; Zeichnungen sind zu klein und schlecht lesbar.
- Priorität: veraltete Ergebnisansichten/Clipping korrigieren, danach Zeichnungs-Fokusmodus und visuelle Ergebnisübersicht, anschließend kurze funktionale Animationen mit Reduktionsoption.
- Feedback-Events `FB-2BDA3F31C2` und `FB-E8A6C330E8` aufgenommen; Status `NEEDS_TRIAGE`. Keine Umsetzung oder Nutzerabnahme als erledigt gemeldet.
- Bildnachweise beziehen sich auf Review-Commit `b2e03d89b4829466dc3838764edd6e30d81e9fa2`; spätere Änderungen vor Nacharbeit gegenprüfen.
