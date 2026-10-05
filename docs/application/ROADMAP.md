# Roadmap

## V-00.01 und V-00.02 — vorhanden

Validierte Treiber, geschlossener Solver, Rund-/Slot-Port, einfache Gehäusegeometrie, passive 2-Wege-Startwerte, PySide6-GUI und grundlegende Fertigungsausgabe.

## V-00.03.00 — lokale Testversion

Umgesetzt: linearer Bassreflex-Solver mit Frequenzgang, Auslenkung, Portgeschwindigkeit, Gruppenlaufzeit und bedingter SPL/Impedanz; drei Abstimmungsvorschläge; FRD/ZMA-Import; elektrische Weichensimulation mit komplexer Last; akustische Summierung mit Phasenkennzeichnung; parametrisches Frontlayout mit numerischer Eingabe, Kollisions-/Bohrungsprüfung; getrennte Plattenstärken und doppelte Front; erweitertes Fertigungspaket, Demo-Projekt, Schema-2-Migration und Windows-Testbuild.

## V-01.00.00 — erweiterte lokale Testversion

Umgesetzt: sichtbarer Berechnungsstatus mit Änderungsanzeige und Schutz gegen Export veralteter Ergebnisse; kontraststarker, zoombarer Innenschnitt mit Bauteiltiefen, Port, Streben und Kammern; getrennte Montageflächen Front/Rückwand/Trennwand und passende DXF-Ausgaben; Passivmembran mit berechneter Zusatzmasse und linearem Resonatormodell; einfach abgestimmter Zweikammer-Bandpass mit unterem/oberem -3-dB-Punkt; Schema 3 und Regressionstests. Reale Messvalidierung steht weiterhin aus.

## V-01.01.00 — lokaler Konstruktionsassistent

Umgesetzt: neue einfache Startoberfläche mit geführten Vorgaben, optionalen Anforderungen und nachvollziehbaren Varianten; lokale JSON-/CSV-Komponentenbibliothek; Soundprofile, Vorfilter, Maßsuche, Machbarkeitsprüfung und Bewertungsaufschlüsselung; Hintergrundberechnung mit Abbruch; bisheriger Editor als Expertenmodus; E12-Weichenstartwerte; fünf reproduzierbare Szenarien. Die vier vorhandenen Gehäusefamilien haben getrennte Vorbereitungsstrategien; weitere Familien sind in einer Registry als `PLANNED` gekennzeichnet. Es werden ausschließlich synthetische TESTDATEN ausgeliefert.

## V-01.02.00 — Maßblatt und belegte Katalogdaten

Umgesetzt: separates Maßblatt mit Außen-/Innenmaßen, Einbaukoordinaten, Ausschnitten, Einbautiefen und schematischem Innenschnitt; CSV-Koordinaten und PDF-Maßseite im Fertigungspaket. Sieben Chassis und drei Passivmembranen wurden aus verlinkten Dayton-Audio-Produktdaten in SI-Einheiten erfasst. Die sechs synthetischen Demochassis bleiben gekennzeichnet. Der einfache Modus zeigt alle Gehäusetypen; geplante sind sichtbar, aber deaktiviert. Weitere Solver wurden in dieser Stufe nicht freigegeben, weil dafür noch validierte Akustik- und Fertigungsgeometrie fehlen.

## V-01.05.00 — Isobarik und Innenaufbau

Umgesetzt: zwei isobarische Tandemvarianten mit idealem akustischem Ersatzmodell, Koppelrohr und Montagering, Volumenverdrängung, Kollisionsprüfung, eigenem Ring-DXF, Stückliste und bemaßtem Innenschnitt. Ein zweites Maßblatt enthält die Positionen der Streben und Kammern sowie Platten- und Portmaße. Die gemeinsame Strebenposition beseitigt eine Abweichung zwischen Zeichnung und Prüfung. Herstellerbibliothek um belegte Datensätze von Visaton und Scan-Speak erweitert; fehlende Angaben bleiben leer. Der Assistent bietet nun sechs berechenbare Familien, alle weiteren bleiben als geplant sichtbar.

## V-02.06.00 — Zuschnitt, Bauanleitung, Prototypvergleich

Umgesetzt: Zuschnittplan mit Sägeschnitt (Guillotine-Verfahren, mehrere Heuristiken, deterministisch), Plattenzahl und Verschnitt je Dicke; Gewichtsbereich;
Bauanleitung je Bauform; Prototypvergleich mit Portkorrektur (UI und Kommandozeile); Schallwandkorrektur; Referenztests; Zuletzt geöffnet, Autosave, Protokoll,
Einstellungen, Hilfe; einheitliche Versionsquelle. Gesamtplan: `PLAN_V-03.00.00.md`.

## V-02.07.00 — Mehrwege und Bedienkomfort

Umgesetzt: passive 3-Wege-Weiche mit Kettenschaltungs-Simulation, interaktives Frontlayout mit Undo/Redo, `mypy --strict` für Nicht-UI-Pakete, UI-Tests.

## Nächste Ausbaustufe — priorisiert (Stand vor V-02.06.00, teilweise erledigt)

1. Modell gegen Messungen und etablierte Simulationsprogramme für mehrere reale Treiber abgleichen; Leckage-/Portverlustparameter kalibrieren.
2. Vollständige 3D-Kollisionsprüfung, Faltungen und Port-/Streben-Freiräume, präzise bemaßte Schnittzeichnungen und DXF/CNC-Profilvalidierung.
3. Wirklich frei veränderbare Mehrtreiber-Gehäuse mit Volumen pro Kammer, getrennten Chassis-Modellen und integrierter 3-Wege-Netlist.
4. Akustische Weichenoptimierung einschließlich Schallzentren, Baffle Step, Messfenster und Belastbarkeit der Bauteile.
5. Material-/Verbindungseditor, Dämmmaterial, Anschlussklemmen und vollständige Kosten-/Gewichtsliste.
6. Interaktives Frontlayout mit Drag-and-drop, Undo und Schnapp-/Ausrichtfunktionen.

Weitere Gehäusetypen wie Transmission Line, Horn und Doppelbandpass bleiben spätere Arbeit.
