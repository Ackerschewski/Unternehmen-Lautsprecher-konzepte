# Roadmap TASK-0030 bis TASK-0050

## Zweck

Diese Roadmap verbindet die großen Folgepakete nach TASK-0029 zu einer konsistenten Entwicklungskette bis zum V4-Releasekandidaten.

Alle TASK-0030 bis TASK-0050 sind bewusst mindestens im Umfang von TASK-0028 ausgearbeitet. Sie dürfen nicht als kleine Einzeltickets behandelt werden.

Wichtig:

- TASK-0029 bleibt der **unmittelbar nächste** Produkt-Workstream.
- TASK-0030–0050 sind geplant, aber nicht automatisch gleichzeitig zu starten.
- Abhängigkeiten sind wichtiger als reine Nummernreihenfolge.
- Mehrere Pakete dürfen parallel vorbereitet werden, wenn sie keine gemeinsame Kernarchitektur gleichzeitig umbauen.
- TASK-0050 ist Integrations-/Releasearbeit und darf keine neue große Featurewelle starten.

---

# Phase A – Vertrauensbasis, Datenbasis, Geometriekern

## TASK-0030 – Solver Validation & Reference Lab

Ziel:
- Vertrauensstufen je Solver;
- Literatur-/Referenzfälle;
- Regression Harness;
- Cross-Solver-Konsistenz;
- Validation Matrix.

Warum zuerst:
Die Automatik darf komplexe Gehäusetypen nicht gleich behandeln, solange ihre Modelle unterschiedlich gut validiert sind.

Blockiert bzw. beeinflusst:
- TASK-0038 Advanced Enclosures
- TASK-0039 Automatic Synthesis
- TASK-0048 QA
- TASK-0050 Release Gate

---

## TASK-0031 – Component Library Expansion & Provenance 3.0

Ziel:
- feldweise Provenienz;
- deutlich größere reale Komponentenbibliothek;
- Readiness pro Use Case;
- Crossover-/DSP-/Hardware-/PR-Daten;
- skalierbarer Import und Audit.

Warum früh:
Fast jede spätere Automatik hängt von belastbaren Komponenten- und Quelldaten ab.

Blockiert bzw. beeinflusst:
- TASK-0033 Crossover Studio
- TASK-0034 Active DSP
- TASK-0039 Automatic Synthesis
- TASK-0041 Procurement
- TASK-0050 Release

---

## TASK-0032 – Parametric 3D Geometry & Collision Kernel

Ziel:
- kanonisches 3D-/2.5D-Geometriemodell;
- Collision Engine;
- Joinery;
- transparente/selektierbare 3D-Ansicht;
- Montagefreiraum.

Warum früh:
Fertigung, CAD, Bracing, Dämmung und STEP brauchen eine gemeinsame Geometriequelle.

Blockiert bzw. beeinflusst:
- TASK-0040 Manufacturing CAD
- TASK-0042 Materials/Bracing
- TASK-0043 V4 Workspace
- TASK-0050 Release

---

# Phase B – Elektroakustik, Weiche, DSP, Messung, Directivity

## TASK-0033 – Crossover Studio – N-Way Acoustic Optimization

Ziel:
- allgemeine N-Wege-Netlist;
- komplexe Lasten;
- akustische Summierung;
- automatische Weichenoptimierung;
- reale Standardbauteile;
- Belastungs-/Toleranzprüfung.

Abhängigkeiten:
TASK-0031 und bestehende FRD/ZMA-Infrastruktur.

---

## TASK-0034 – Active DSP & Amplifier System Designer

Ziel:
- aktive Weichen;
- DSP-Ketten;
- Verstärkerzuordnung;
- Headroom/Clipping;
- Limiter-/Subsonic-Startwerte;
- Biquad-/Filterexport.

Abhängigkeiten:
TASK-0031 + TASK-0033.

---

## TASK-0035 – Measurement Workspace & Prototype Correlation

Ziel:
- revisionssichere Messdatensätze;
- REW/ARTA/Vituix-kompatible Imports;
- Nah-/Fernfeld-Merge;
- Simulation-vs.-Messung;
- Parameter-Fitting;
- Measurement Studio.

Abhängigkeiten:
TASK-0030.

Hohe Priorität vor V4:
Messung ist die Grundlage für die reale Validierung des Gesamtprogramms.

---

## TASK-0036 – Directivity, Baffle Diffraction & Off-Axis Studio

Ziel:
- Mehrwinkel-FRD;
- positionsabhängige Baffle-Diffraction;
- Directivity-Metriken;
- gemessen vs. geschätzt;
- Directivity-aware Crossover.

Abhängigkeiten:
TASK-0033, Bibliothek und Frontlayout.

---

# Phase C – Hörkontext, Spezialgehäuse, automatische Systemsynthese

## TASK-0037 – Room, Placement & Subwoofer Integration

Ziel:
- Aufstellung;
- Boundary Gain;
- Floor Bounce;
- erste Raummoden;
- Hörplatz-SPL;
- Sub-/Satellitenintegration.

Abhängigkeiten:
TASK-0030, optional TASK-0036.

---

## TASK-0038 – Advanced Enclosure Fidelity

Ziel:
- TL/MLTL/TQWT härten;
- Hornprofile und Faltungen;
- Dipole/Cardioid;
- familienbezogene Parameter;
- Trust-aware Specialty Enclosures.

Abhängigkeiten:
TASK-0030 + TASK-0032.

---

## TASK-0039 – Automatic System Synthesis & Pareto Optimizer 2.0

Ziel:
- Hard/Soft Constraints;
- automatische 1-/2-/2.5-/3-Wege-Systeme;
- Early Pruning;
- Pareto-Front;
- transparente Auswahl;
- echte Trade-off-Varianten.

Abhängigkeiten:
TASK-0031 + TASK-0033 + TASK-0030.
TASK-0036 verbessert die Qualität zusätzlich.

Dieser Task ist der große Ausbau des einfachen Modus.

---

# Phase D – Fertigung, Beschaffung, Materialien

## TASK-0040 – Manufacturing CAD Pro

Ziel:
- Falz/Nut/Gehrung/Dado;
- Taschen/Bohrungen/Senkungen;
- CNC-Layer;
- STEP;
- fertigungstaugliche Zeichnung;
- geometrische Exportprüfung.

Abhängigkeiten:
TASK-0032.

---

## TASK-0041 – Procurement, Cost, Inventory & Sourcing

Ziel:
- Preis-Snapshots;
- Lagerbestand;
- Restplatten;
- Beschaffungsplan;
- Kostenabdeckung;
- budget-aware Automatik.

Abhängigkeiten:
TASK-0031 + TASK-0040.

---

## TASK-0042 – Materials, Panel Mechanics, Bracing & Damping 2.0

Ziel:
- Materialmechanik;
- Panelresonanz-Näherung;
- automatische Streben;
- Dämmungsmodell;
- Gewicht/Schwerpunkt;
- 3D-/BOM-Integration.

Abhängigkeiten:
TASK-0029 + TASK-0032.

---

# Phase E – V4 Produkt- und Plattformhärtung

## TASK-0043 – V4 Product Workspace & Interaction System

Ziel:
- Arbeitsbereiche statt wachsender Tabs;
- universeller Inspector;
- Command Palette;
- Cross-View Selection;
- responsive/DPI;
- Accessibility.

Abhängigkeiten:
V3.4 stabil; idealerweise TASK-0032/33/34-Schnittstellen bekannt.

Nicht zu früh starten:
Erst wenn klar ist, welche Hauptarbeitsbereiche V4 wirklich braucht.

---

## TASK-0044 – Project Lifecycle, Variants, Revisions & Reproducibility

Ziel:
- Projektpaket;
- Variantenbaum;
- Revisionen;
- Library-Snapshots;
- Historie;
- Recovery.

Abhängigkeiten:
Messung/Fertigungsschnittstellen sollten bekannt sein.

---

## TASK-0045 – Performance, Scalability & Background Execution

Ziel:
- Profiling;
- Worker;
- Cancel/Progress;
- Caching;
- inkrementelle Neuberechnung;
- große Library/Messdaten.

Kann teilweise parallel zu TASK-0043/44 vorbereitet werden.

---

## TASK-0046 – Plugin, Adapter & Extension Architecture

Ziel:
- versionierte Extension API;
- Data/Measurement/Solver/Export/DSP Adapter;
- Plugin Manager;
- Compatibility/Security.

Erst sinnvoll, wenn Core-APIs ausreichend stabil sind.

---

## TASK-0047 – Reliability, Security, Privacy & Licensing Hardening

Ziel:
- Atomic Save;
- Import-Hardening;
- Logging/Privacy;
- SBOM;
- Lizenzprüfung;
- Plugin-Sicherheit.

Vor öffentlicher Distribution zwingend.

---

## TASK-0048 – QA Automation, Regression Lab & Visual Evidence

Ziel:
- Testtaxonomie;
- Golden Fixture Corpus;
- Migration Corpus;
- Exportvalidatoren;
- UI-E2E;
- reproduzierbare Screenshot-Evidence.

Abhängigkeiten:
TASK-0030 und V4-UI ausreichend stabil.

Dieser Task ist kein letzter Aufräumpunkt: Teile können schon während der vorherigen Phasen vorbereitet werden.

---

## TASK-0049 – Documentation, Learning Mode & Demo Project Suite

Ziel:
- vollständiges Nutzerhandbuch;
- Lernmodus;
- 7+ Demo-Projekte;
- Tutorials;
- Entwicklerdokumentation;
- In-App-Hilfe.

Erst finalisieren, wenn Workflows stabil sind; Demo-Fixtures dürfen früher wachsen.

---

# Phase F – Integration und Release Gate

## TASK-0050 – V4 Integration, Release Candidate & Product Acceptance

Dieser Task fügt **keine große neue Funktion** hinzu.

Er prüft:

- Architektur;
- End-to-End-Flows;
- Solver Trust;
- Windows Build;
- Migration;
- Visual Evidence;
- Performance;
- Security/Lizenzen;
- bekannte Grenzen;
- Owner-Freigabe.

V4 darf erst nach bewusster Owner-Entscheidung veröffentlicht werden.

---

# Empfohlene Reihenfolge

## Unmittelbar

1. TASK-0029
2. TASK-0030
3. TASK-0031
4. TASK-0032

## Danach parallelisierbar

Track Akustik:
- 0033
- 0034
- 0035
- 0036
- 0037
- 0038

Track Fertigung:
- 0040
- 0042
- 0041

Track Automatik:
- 0039 nach 0031/0033

## Produktintegration

- 0043
- 0044
- 0045
- 0046
- 0047
- 0048
- 0049

## Abschluss

- 0050

---

# Was nicht passieren darf

- Claude startet TASK-0043 und baut die UI erneut komplett um, bevor 3D/Weiche/Messung ihre Interfaces stabilisiert haben.
- TASK-0039 benutzt halbleere Library-Daten wie vollständige Messdaten.
- TASK-0040 baut eine zweite Geometriewelt neben TASK-0032.
- TASK-0041 bezeichnet Teilkosten als vollständigen Preis.
- TASK-0042 verkauft Panel-Näherungen als FEM.
- TASK-0046 stabilisiert Plugin-APIs zu früh und friert schlechte Core-Schnittstellen ein.
- TASK-0050 wird genutzt, um noch schnell große Features einzubauen.
- Physische Validierung wird durch synthetische Tests als erledigt markiert.

---

# Autonomous-Claude-Regel

Wenn Claude einen Task startet:

1. Task vollständig lesen.
2. Dependencies prüfen.
3. Wenn Dependency fehlt: nicht blind implementieren.
4. Entweder Dependency zuerst abschließen oder Task klar als BLOCKED markieren und den nächsten unabhängigen Workstream wählen.
5. Innerhalb eines Tasks selbstständig bis zu einem sauberen Handoff weiterarbeiten.
6. Nicht nach jeder Phase auf „mach weiter“ warten.

---

# Größenstandard

Referenz TASK-0028:
ca. 17.5 kB.

TASK-0030 bis TASK-0050:
alle wurden bewusst auf **mindestens denselben bzw. größeren Detailumfang** erweitert.

Der Umfang ist kein Qualitätsziel an sich; er soll sicherstellen, dass jeder Task genug Architektur-, QA-, UI-, Daten-, Migrations- und Evidence-Anweisungen enthält, um mehrere Stunden selbstständig daran arbeiten zu können.
