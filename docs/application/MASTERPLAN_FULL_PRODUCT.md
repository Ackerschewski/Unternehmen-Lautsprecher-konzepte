# Masterplan – Lautsprecher Konstruktion als vollständige Design-Plattform

**Basis der Analyse:** V-02.07.00, Branch `claude/modest-bell-guqoxu`, Stand 05.10.2026.  
**Zweck:** Dieser Plan beschreibt den Ausbau vom bereits umfangreichen Konstruktionsassistenten zu einer belastbaren, alltagstauglichen und später kommerziell nutzbaren Lautsprecher-Design-Plattform.  
**Wichtig:** Bereits vorhandene Funktionen werden nicht neu erfunden. Neue Funktionen müssen dieselbe zentrale Projektgeometrie, dieselben Messdaten und dieselbe Komponentenbibliothek verwenden.

---

## 1. Aktueller Stand V-02.07.00

Der aktuelle Entwicklungsstand ist bereits deutlich mehr als ein einfacher Gehäuserechner.

### Vorhanden

- PySide6-Desktop-Anwendung für Windows.
- Einfacher Assistent plus Expertenmodus.
- 29 registrierte Gehäusetypen mit Berechnungspfad.
- Automatische Erzeugung von 1–3 Varianten nach Bauraum, Klangprofil, Budget und weiteren Anforderungen.
- Geschlossene Systeme, Bassreflex, Passivmembran, Bandpass, Isobarik, Transmission-Line-Familien, offene Schallwände, Cardioid-Varianten und Hornfamilien.
- Bassreflex-Kleinsignalmodell mit Frequenzgang, Auslenkung, Portgeschwindigkeit, Impedanz und Gruppenlaufzeit.
- Passive 2-Wege- und 3-Wege-Weichen, E12-Rundung, L-Pad, Zobel und Baffle-Step-Korrektur.
- FRD-/ZMA-Verarbeitung und Prototypvergleich.
- Interaktives Frontlayout mit Drag-and-drop, Raster, Mittellinie und Undo/Redo.
- Fertigungsausgabe als PDF, SVG, DXF, CSV und JSON.
- Zuschnittoptimierung mit Plattenformat, Sägeschnitt, Verschnitt und Plattenzahl.
- Einzelplatten-DXF sowie 45°-Gehrungsoption.
- Stückliste, Materialkosten, Budgetprüfung, Gewichtsschätzung und Bauanleitung.
- Autosave, Wiederherstellung, Zuletzt-geöffnet, Einstellungen, Log und Hilfe.
- 84 datierte Thomann-Katalogeinträge plus verifizierte Herstellerdaten für ausgewählte Chassis.
- 233 Pytest-Fälle.
- Ruff sauber.
- `mypy --strict` für alle Nicht-UI-Pakete.
- ca. 90 % Gesamtabdeckung; UI-Dateien laut Buildbericht 75–100 %.

### Derzeit wichtigste Grenzen

1. Die akustischen Modelle sind überwiegend lineare Kleinsignalmodelle und nicht ausreichend mit realen Prototypen validiert.
2. Alle 29 Gehäusetypen haben einen Berechnungspfad, aber die Genauigkeit der komplexen Horn-/Linienmodelle ist nicht auf demselben Vertrauensniveau wie Closed/Bassreflex.
3. Es fehlt eine vollständige 3D-Geometrie- und Kollisionsengine.
4. Die Komponentenbibliothek ist für automatische Entwürfe noch zu klein; viele Datensätze besitzen Preis, aber nicht alle nötigen T/S- und Montagedaten.
5. Der Assistent wählt automatisch noch keine vollständigen 3-Wege-Systeme.
6. Passive Weichen sind vorhanden, aber eine echte automatische akustische Weichenoptimierung auf gemessenen FRD/ZMA-Daten fehlt.
7. Aktive DSP-Systeme, Verstärkermodule, FIR/IIR-Export und Schutz-/Limiterkonzepte fehlen.
8. Richtwirkung, Off-Axis-Verhalten, Raum/Boundary-Gain, Bodenreflexion und Hörabstand sind noch keine vollständigen Entwurfsgrößen.
9. Windows-Build, interaktiver Sichttest und physische Messvalidierung sind weiterhin offene Release-Nachweise.
10. `main` enthält nicht den aktuellen Entwicklungsstand; Release- und Branch-Hygiene muss vor einem stabilen Produkt bereinigt werden.

---

# 2. Zielbild

Das Programm soll drei Bedienebenen besitzen, die auf **demselben Kernmodell** aufbauen.

## 2.1 Assistent

Für Nutzer ohne tiefes Lautsprecherwissen.

Eingaben:

- Lautsprechertyp
- maximale Breite / Höhe / Tiefe oder maximales Volumen
- Hörentfernung
- gewünschter Maximalpegel
- Klangprofil
- Budget
- passiv / aktiv
- optional bevorzugte Hersteller oder vorhandene Komponenten
- Raum-/Aufstellungsart optional

Ausgabe:

- 1–5 Pareto-optimierte Entwürfe
- verwendete Komponenten
- vollständige Gehäusekonstruktion
- Weiche/DSP
- Simulation
- Kosten
- Fertigungsunterlagen
- klare Erklärung, warum die Variante geeignet ist
- klare Ablehnung, wenn Anforderungen physikalisch nicht sinnvoll erreichbar sind

## 2.2 Expertenmodus

Vollständiger Zugriff auf:

- T/S-Parameter
- Gehäuseparameter
- Verlustgüten
- Port/PR
- Frontlayout
- Innengeometrie
- Bracing
- Messdaten
- Weiche
- DSP
- Simulation
- Fertigung
- Optimierungsgewichte

## 2.3 Mess- und Entwicklungsmodus

Für Prototypen und Feintuning:

- Messdaten importieren
- Simulation gegen Messung legen
- Abweichungen analysieren
- Parameter fitten
- Port/Weiche/DSP korrigieren
- Revision erzeugen
- A/B-Vergleich zwischen Simulation und Prototyp

---

# 3. Produktprinzipien

1. **Keine erfundenen Daten.** Fehlende Herstellerwerte bleiben unbekannt.
2. **Single Source of Truth.** Geometrie, Zeichnung, Kollision, BOM und Export verwenden dieselben Objekte.
3. **Messung vor Scheinpräzision.** Nicht validierte Modelle werden als Näherung gekennzeichnet.
4. **Automatik muss erklärbar sein.** Jede Auswahl enthält Score-Breakdown und Ausschlussgründe.
5. **Unmöglich bleibt unmöglich.** Das Programm darf keine physikalisch unsinnige Lösung erzwingen.
6. **Assistent und Expertenmodus teilen denselben Kern.**
7. **Fertigung ist Teil des Entwurfs**, nicht ein nachgelagerter Export.
8. **Datenprovenienz ist Pflicht.** Quelle, Abrufdatum und Mess-/Herstellerstatus bleiben erhalten.
9. **Release-Nachweise werden nicht simuliert.** NOT_RUN bleibt NOT_RUN.
10. **Neue Gehäusetypen nur als SUPPORTED markieren, wenn Solver, Geometrie und Tests vorhanden sind.**

---

# 4. Arbeitspaket A – Repository- und Release-Härtung

**Priorität: P0**

Der aktuelle produktive Entwicklungsstand liegt auf einem Arbeitsbranch, während `main` weit zurückliegt. Vor dem ersten stabilen Release:

- aktuellen V-02.07-Stand in einen sauberen Integrationsbranch überführen;
- alle abgeleiteten Template-Dateien von echten App-Dateien klar trennen;
- `main` wieder zum kanonischen stabilen Programmstand machen;
- Release-Branches nur für RC/Hotfix verwenden;
- Versionsschema automatisch aus genau einer Quelle ableiten;
- Changelog aus tatsächlich gemergten Änderungen pflegen;
- reproduzierbares Buildmanifest mit Hashes erzeugen;
- Windows-Onedir-Build reproduzierbar testen;
- optional später Installer mit Inno Setup oder MSIX;
- portable ZIP und Installer getrennt anbieten;
- Upgrade/Migration alter Projektdateien testen;
- automatische Sicherung vor Projektmigration;
- Crash-Report als lokale Datei, niemals ungefragt hochladen.

### Abnahme

- frischer Clone von `main` lässt sich installieren und testen;
- Version in UI, Paket, PDF, Projektdatei und Buildname identisch;
- V-00.xx/V-01.xx/V-02.xx-Projekte werden getestet migriert;
- Clean-Windows-Smoke dokumentiert.

---

# 5. Arbeitspaket B – Physikalische Validierung und Solver-Vertrauen

**Priorität: P0 – wichtiger als weitere exotische Features**

## 5.1 Validierungsmatrix

Für jede Gehäusefamilie festhalten:

- Gleichungen / Referenzquelle
- gültiger Parameterbereich
- bekannte Vereinfachungen
- numerische Referenzfälle
- Vergleich mit etablierten Tools
- reale Messungen
- zulässige Modellabweichung

Vertrauensstufe je Solver:

- `FORMULA_VERIFIED`
- `REFERENCE_VERIFIED`
- `PROTOTYPE_VALIDATED`
- `EXPERIMENTAL`

Diese Vertrauensstufe im Expertenmodus und in Exporten sichtbar machen.

## 5.2 Reale Prototypen

Mindestens:

- geschlossen
- Bassreflex
- Passivmembran
- Bandpass
- Transmission Line
- ein Hornsystem

Nicht nur Frequenzgang messen:

- Nahfeld Treiber
- Nahfeld Port
- Impedanz
- Abstimmfrequenz
- Pegelabhängigkeit
- Verzerrung
- Portgeräusch
- tatsächliches Nettovolumen
- Temperatur/Power Compression bei leistungsstärkeren Tests

## 5.3 Modell-Fitting

Aus Messung ableitbar machen:

- reale Fb
- effektive Portlänge
- Ql/Qa/Qp
- tatsächliche Leckage
- effektives Volumen
- ggf. T/S-Abweichung zum Datenblatt

Der Nutzer muss Änderungen übernehmen können, ohne Rohmessungen zu überschreiben.

---

# 6. Arbeitspaket C – Akustik-Simulationskern 2.0

**Priorität: P0/P1**

## 6.1 Nichtlinearitäten

Späterer erweiterter Modus:

- Portkompression in Abhängigkeit von Geschwindigkeit;
- Strömungs-/Endverlust;
- thermische Schwingspulenerwärmung;
- Re-Anstieg;
- Power Compression;
- Pe/Xmax/Xmech getrennt;
- optional vereinfachtes Bl(x)/Cms(x)-Modell, wenn Daten vorhanden;
- Kompressionswarnungen nicht als Zertifizierung ausgeben.

## 6.2 Max-SPL

Maximalpegel nicht nur thermisch schätzen.

Frequenzabhängige Begrenzung aus:

- Xmax
- Xmech
- Pe
- thermischer Kompression
- Portgeschwindigkeit
- Passivmembran-Xmax
- Filter/DSP
- Hörentfernung

Ausgabe:

- Max-SPL-Kurve
- limitierender Mechanismus je Frequenz
- empfohlene Verstärkerleistung

## 6.3 Gehäuse- und Portresonanzen

Zusätzlich:

- erste Port-Längsresonanz;
- Slot-Port-Moden;
- Gehäuse-Stehwellen aus B/H/T;
- Warnung bei ungünstiger Nähe zu Trennfrequenzen;
- Vorschlag für Dämpfung / Strebenposition;
- optional Transmission-Line-Obermoden.

## 6.4 Baffle Diffraction

Baffle Step existiert bereits als Näherung. Ausbau zu:

- positionsabhängiger Schallwandbeugung;
- Treiberposition X/Y;
- Schallwandbreite/-höhe;
- Kantenradius/Fase;
- Off-Axis-Schätzung;
- Einfluss auf Weichenoptimierung.

## 6.5 Directivity

Bibliothek optional um Polardaten erweitern:

- horizontale/vertikale FRD-Winkel;
- Spinorama-kompatible Datensätze später;
- Directivity Index;
- geschätzte Übergangsfrequenz nach Abstrahlverhalten;
- Warnung bei starkem Directivity-Mismatch.

---

# 7. Arbeitspaket D – Raum, Aufstellung und Hörsituation

**Priorität: P2**

Nicht als vollständige Raumakustiksoftware, sondern als praxisrelevante Entwurfsebene.

Eingaben:

- freistehend / Wand / Ecke / Wandeinbau
- Abstand zu Front-/Seitenwand
- Hörabstand
- Raumgröße optional
- Bodenhöhe / Treiberhöhe

Simulation/Näherungen:

- Boundary Gain;
- 2π/4π-Übergang;
- Floor Bounce;
- erste axiale Raummoden;
- benötigter Pegel am Hörplatz;
- Subwoofer/Satelliten-Übergang;
- mehrere Subwoofer später.

Der Assistent darf daraufhin andere Entwürfe priorisieren.

---

# 8. Arbeitspaket E – Frequenzweichen-Studio

**Priorität: P0/P1**

## 8.1 N-Wege-Netlist

Das heutige 2-/3-Wege-Modell zu einer allgemeinen Netlist ausbauen:

- 1-Wege mit Korrekturgliedern
- 2-Wege
- 2.5-Wege
- 3-Wege
- 4-Wege
- beliebige parallele/serielle RLC-Netze

Bauteile:

- R
- L mit DCR
- C mit ESR optional
- Zobel
- Sperrkreis
- Saugkreis
- L-Pad
- Shelving/Baffle-Step
- Impedanzlinearisierung
- Notch

## 8.2 Akustische Optimierung

Mit gemessenen FRD/ZMA:

- komplexe akustische Summe;
- elektrische + akustische Phase;
- Treiberabstand und Schallzentren;
- Polaritätsumkehr;
- Delay;
- Zielkurven;
- automatische Bauteiloptimierung;
- Auswahl realer E-Reihen;
- Bauteiltoleranzen;
- Mindestimpedanz;
- Phasenwinkel;
- Widerstandsverlust;
- Spulen-DCR;
- Bauteilbelastung.

Optimierung nicht nur auf „flach“:

- Flat
- House Curve
- Studio
- Power Response
- Directivity Matching
- eigener Target-Import

## 8.3 Leistungsprüfung

- Widerstandsleistung;
- Spulenstrom;
- Kondensatorspannung;
- Gesamtimpedanz;
- Verstärkerverträglichkeit;
- Warnung bei kritischer Mindestimpedanz/Phase.

---

# 9. Arbeitspaket F – Aktive Systeme und DSP

**Priorität: P1**

Komponentenmodell erweitern um:

- DSP
- Plate Amp
- Mehrkanalverstärker
- Aktivmodul
- Netzteil optional

Filter:

- Butterworth / Bessel / Linkwitz-Riley
- Hoch-/Tiefpass
- PEQ
- High/Low Shelf
- Notch
- Gain
- Delay
- Polarity
- Allpass
- Limiter
- Subsonic

Exportadapter später:

- miniDSP-kompatible Parameterdatei, soweit Format sauber dokumentiert;
- Equalizer APO;
- generische Biquad-Koeffizienten;
- CSV/JSON;
- REW-Filterliste.

FIR:

- zunächst Import/Anzeige;
- später FIR-Zieloptimierung;
- Latenz und Tap-Anzahl explizit.

Assistent:

- „passiv“, „aktiv“, „egal“;
- aktive Variante darf ohne passive Weichenbauteile gerechnet werden;
- Verstärkerleistung und Kanalzahl in BOM/Kosten.

---

# 10. Arbeitspaket G – Automatischer Assistent 2.0

**Priorität: P0**

## 10.1 Automatische 3-Wege- und 2.5-Wege-Auswahl

Heute nur manuelle 3-Wege-Weiche.

Erweitern:

- Woofer/Mid/Tweeter-Kandidaten;
- sinnvolle Überlappung;
- Directivity Matching;
- Empfindlichkeitsreserve;
- Impedanz;
- Frontflächenbedarf;
- Kosten;
- erforderliche Kammern;
- Weichenkomplexität.

## 10.2 Pareto-Optimierung

Nicht nur einen gewichteten Gesamtscore.

Pareto-Front für:

- F3
- Max-SPL
- Größe
- Kosten
- Wirkungsgrad
- Gruppenlaufzeit
- Bauaufwand
- Gewicht
- Weichenkomplexität

Ausgabe z. B.:

- Favorit
- Kompakt
- Tiefbass
- Pegel
- Preis/Leistung

## 10.3 Constraint Solver

Harte und weiche Anforderungen unterscheiden.

Hart:

- max. B/H/T
- Budget
- gewünschte Impedanz
- Komponenten vorhanden
- Gehäuseart verboten
- Materialstärke

Weich:

- F3
- SPL
- Gewicht
- Kosten
- Klangprofil

Bei „nicht machbar“:

- kleinste nötige Abweichung ermitteln;
- konkrete Alternativen erzeugen;
- zeigen, welche Constraint den Entwurf verhindert.

## 10.4 Bestehende Komponenten

Nutzer kann „habe ich schon“ markieren:

- Treiber
- Verstärker
- DSP
- passive Weichenbauteile
- Plattenmaterial

Kostenoptimierung berücksichtigt Lagerbestand.

---

# 11. Arbeitspaket H – Komponentenbibliothek 2.0

**Priorität: P0/P1**

## 11.1 Zielumfang

Kurzfristiges Qualitätsziel statt bloßer Datensatzmenge:

- mindestens 100 vollständig berechenbare Chassis mit Herstellerquellen;
- mehrere Größen je Hersteller;
- Subwoofer, Woofer, Midwoofer, Midrange, Fullrange, Tweeter, Kompressionstreiber;
- mindestens 20 Passivmembranen;
- reale Port-/Aeroport-Daten;
- Standard-Weichenbauteile;
- Terminals/Speakon/Binding Posts;
- Aktivmodule/DSP/Plate Amps;
- Materialien und Handelsplatten.

Langfristig 250+ vollständig berechenbare Chassis.

## 11.2 Datenqualität

Pro Feld Provenienz ermöglichen:

- Herstellerdatenblatt
- Händler
- Messung
- Nutzerwert
- abgeleitet

Nicht nur eine Quelle pro Datensatz.

Felder zusätzlich:

- Datenblattversion
- Abrufdatum
- Messbedingungen
- Toleranz, falls veröffentlicht
- Bild/Thumbnail nur bei rechtlich sauberer Quelle
- Discontinued-Status
- Nachfolgemodell

## 11.3 Importadapter

- generisches CSV/JSON
- FRD/ZMA
- REW
- ARTA/LIMP
- VituixCAD-kompatible Messdateien, soweit Format eindeutig
- Hersteller-CSV/PDF nur mit nachvollziehbarer manueller/halbautomatischer Prüfung

Kein blindes Scraping ohne Lizenz-/Nutzungsprüfung.

## 11.4 Preis-/Beschaffungsebene

Preis immer als Snapshot:

- Händler
- Datum
- Währung
- Artikelnummer
- URL

Mehrere Angebote pro Komponente ermöglichen.

Keine automatische Aussage „günstigster Marktpreis“, solange Quellen nicht vollständig sind.

---

# 12. Arbeitspaket I – 3D-Geometrie- und CAD-Kern

**Priorität: P0 für echte Fertigungsreife**

Die größte technische Lücke der aktuellen Konstruktion.

## 12.1 Parametrischer Solid-/Panel-Kern

Jedes Bauteil benötigt:

- lokale Koordinaten
- Orientierung
- Dicke
- Kontur
- Ausschnitte
- Bohrungen
- Fasen/Radien
- Verbindungstyp
- Toleranz
- Material

## 12.2 Kollisionen

Prüfen:

- Treiberkorb vs. Seitenwand
- Magnet vs. Strebe
- Port vs. Treiber
- Port vs. Rückwand
- Port vs. Strebe
- Weiche vs. Magnet/Port
- Passivmembran vs. Innenbauteile
- Horn-/TL-Kanalquerschnitt
- Schrauben/Bohrungen vs. Kante
- Werkzeugzugänglichkeit
- Montageweg des Treibers

Nicht nur Endposition, sondern optional **Einbaupfad**.

## 12.3 Verbindungen

Unterstützen:

- stumpf
- Gehrung
- Falz
- Nut/Feder
- Dado/Nut
- Lamello/Dübel optional
- doppelte Front
- eingelassene Rückwand

Die Volumenrechnung muss durch Verbindungstypen unverändert korrekt bleiben.

## 12.4 3D-Vorschau

Interaktiv:

- drehen
- zoomen
- Explosionsansicht
- Schnitt
- transparente Wände
- Bauteile ein-/ausblenden
- Kollisionsmarkierungen

Technik evaluieren:

- Qt3D / OpenGL
- trimesh
- CadQuery/OpenCascade für STEP

Entscheidung erst nach Spike; CAD-Kern nicht an UI koppeln.

---

# 13. Arbeitspaket J – Fertigung/CNC 2.0

**Priorität: P1**

## 13.1 Fertigungszeichnungen

- echte Maßketten;
- Toleranzen;
- Bohrungsdurchmesser;
- Senkungen;
- Taschen/Einfräsungen;
- Falze/Nuten;
- Radius/Fase;
- Bauteilnummer;
- Material und Dicke;
- Revision.

## 13.2 DXF

Layerstandard:

- OUTER
- CUT_THROUGH
- POCKET
- DRILL
- COUNTERSINK
- ENGRAVE
- DIMENSION
- REFERENCE

Einheiten und Ursprung eindeutig.

DXF automatisch gegen interne Geometrie testen.

## 13.3 STEP/STL/3MF

Nach CAD-Kern:

- STEP Gesamtgehäuse;
- STEP je Platte;
- STL/3MF optional;
- Export nur, wenn 3D-Geometrie validiert.

## 13.4 CNC

Nicht vorschnell G-Code erzeugen.

Zunächst:

- neutrale Geometrie;
- Werkzeugdurchmesser/Innenradius beachten;
- Dogbones optional;
- CAM-freundliche Layer;
- Snapmaker-/Fusion-/FreeCAD-Workflow dokumentieren.

Später separate, ausdrücklich experimentelle CAM-Ausgabe.

---

# 14. Arbeitspaket K – Zuschnitt und Materialplanung 2.0

**Priorität: P1**

Aktuelle Guillotine-Nesting-Logik erweitern:

- Plattenrestlager;
- Maserungsrichtung;
- Bauteildrehung erlauben/verbieten;
- Sicherheitsrand;
- mehrere Plattenformate;
- mehrere Dicken;
- Reststücke speichern;
- echter Preis je Platte;
- Verschnittkosten;
- Optimierung nach Kosten statt nur Fläche;
- Export als Sägeplan.

Trapez-/Rundteile später polygonbasiert statt nur Bounding Box.

---

# 15. Arbeitspaket L – Innenakustik und Bracing

**Priorität: P1/P2**

## 15.1 Automatische Versteifung

Nicht nur Anzahl Fensterstreben.

Aus Geometrie vorschlagen:

- Strebenposition;
- Fenstergröße;
- Kreuzstreben;
- Ringstreben;
- Front-Rückwand-Verbindung;
- asymmetrische Positionen gegen Moden.

## 15.2 Panelresonanz-Näherung

Materialdaten erweitern:

- E-Modul
- Dichte
- Verlustfaktor optional

Daraus grobe Panelmoden und Bedarf für Bracing/Dämpfung ableiten.

Keine FEM vortäuschen.

## 15.3 Dämpfung

- Materialtyp
- Menge
- Position
- Wirkung als dokumentierte Näherung
- separate Behandlung Closed / TL / Horn

Bauanleitung übernimmt Positionen.

---

# 16. Arbeitspaket M – Messwerkstatt

**Priorität: P1**

Geführter Messworkflow:

1. Mikrofon-/Soundkarteninformationen
2. Pegelkalibrierung
3. Impedanzmessung
4. Nahfeld Woofer
5. Nahfeld Port
6. Fernfeld/gated
7. Merge
8. Off-Axis
9. Verzerrung optional
10. Prototypvergleich

Das Programm muss nicht zwingend selbst Audio aufnehmen. Zunächst gute Import-/Workflow-Unterstützung für REW/ARTA/VituixCAD.

Später optional eigener Messclient.

Messdatensätze bekommen:

- Mikrofon
- Abstand
- Winkel
- Spannung
- Gate
- Glättung
- Datum
- Umgebung
- Projekt-/Treiberrevision

---

# 17. Arbeitspaket N – Vergleichs- und Variantenlabor

**Priorität: P1**

Beliebige Entwürfe nebeneinander:

- Frequenzgang
- Max-SPL
- Auslenkung
- Portgeschwindigkeit
- Impedanz
- Gruppenlaufzeit
- Preis
- Gewicht
- Außenmaße
- Materialbedarf
- Bauaufwand

A/B/C-Projektvarianten speichern.

„Was ändert sich wenn …“:

- 10 l kleiner
- 5 Hz tiefer
- anderer Treiber
- anderes Material
- aktiver statt passiver Filter
- Budget -20 %

---

# 18. Arbeitspaket O – UI/UX 3.0

**Priorität: P1**

Die Grundidee Assistent/Experte bleibt.

## Assistent

Wizard mit wenigen Entscheidungen:

1. Anwendung
2. Bauraum
3. Ziel
4. Budget/Verstärker
5. Komponentenpräferenzen
6. Ergebnis

Ergebnis nicht als Formular, sondern als Karten:

- Favorit
- Kompakt
- Tiefbass
- Pegel
- Preis/Leistung

Jede Karte zeigt:

- wichtigste Kennwerte
- Ampel/Warnungen
- Preis
- Bauaufwand
- „Warum?“
- „Was wäre besser mit mehr Platz/Budget?“

## Expertenmodus

- linke Navigation statt zu vieler Tabs;
- kontextabhängige Eigenschaften;
- Suchfunktion;
- Einheitenumschaltung;
- Favoriten/Presets;
- Reset je Gruppe;
- Feldhilfe mit Formel/Quelle;
- Ungültige Felder direkt erklären.

## Visualisierung

- 3D-Modell zentral;
- 2D-Zeichnung umschaltbar;
- Diagramme frei koppelbar;
- synchroner Cursor über Frequenzplots;
- Warnung anklicken → betroffenes Bauteil/Plot markieren.

## Barrierefreiheit

- skalierbare Schrift;
- Tastaturbedienung;
- nicht nur Farben für Warnungen;
- Light/Dark;
- High-Contrast später.

---

# 19. Arbeitspaket P – Projekt-, Varianten- und Revisionsmanagement

**Priorität: P1**

Projekt enthält:

- Varianten
- Revisionen
- Messungen
- Bibliotheks-Snapshots
- Exporthistorie
- Entscheidungen

Funktionen:

- Projekt duplizieren;
- Variante verzweigen;
- Revision vergleichen;
- „fertig für Zuschnitt“ sperren;
- nach Geometrieänderung Fertigungsstatus zurücksetzen;
- Messung einer konkreten Revision zuordnen.

Optional später:

- Projektpaket `.lkproj` als ZIP mit JSON + Messdaten + Referenzen.

---

# 20. Arbeitspaket Q – Qualität, Performance und Wartbarkeit

**Priorität: P0/P1**

Aktuelle große Dateien aufteilen:

- `main_window.py`
- `assistant_window.py`
- `services/design.py`
- `services/automatic.py`

Ziel:

- klar getrennte Use Cases;
- keine >1000-Zeilen-God-Objects;
- UI ViewModels/Controller;
- Solver unabhängig testbar;
- Optimierer unabhängig testbar.

Technisch:

- deterministische Optimierung;
- Cache für unveränderte Kandidaten;
- Cancellation;
- Worker-Pool;
- Profiling für große Bibliotheken;
- Test mit 1000+ Komponenten;
- Property-based Tests für Einheiten/Geometrie optional;
- Snapshot-Tests für Exportgeometrie;
- Fuzzing für Parser/Projektmigration.

---

# 21. Arbeitspaket R – Plugins und Erweiterbarkeit

**Priorität: P3**

Erst nach stabiler Kernarchitektur.

Plugin-Schnittstellen für:

- Treiberdatenquellen
- Solver
- Exporter
- DSP-Zielgeräte
- Preisquellen
- Materialbibliotheken

Plugins dürfen den Kern nicht ungeprüft überschreiben.

Manifest:

- Name
- Version
- API-Version
- benötigte Berechtigungen
- kompatible Programmversion

---

# 22. Arbeitspaket S – Dokumentation und Lernmodus

**Priorität: P1/P2**

Neben Nutzer- und Entwicklerhandbuch:

- „Warum diese Box?“
- Glossar T/S
- Gehäusetypen mit Einsatzbereich
- Weichen-Grundlagen
- Messworkflow
- Fertigungsworkflow
- typische Fehler
- Tutorials anhand Demo-Projekten

Optional Lernmodus:

- Formeln anzeigen
- Parameter live erklären
- Veränderung eines Parameters visualisieren

---

# 23. Gehäuseportfolio – Ziel

Die vorhandenen 29 Typen bleiben erhalten, aber „SUPPORTED“ muss künftig zusätzlich eine Vertrauensstufe besitzen.

### Familien

- Closed / Acoustic Suspension
- Bass Reflex: Rund, Multi-Port, Slot, flared
- Passive Radiator
- Aperiodic
- Bandpass 4
- Bandpass 6 parallel
- Bandpass 6 seriell
- Isobaric closed/vented
- Compound/Push-Pull
- Infinite Baffle
- Open Baffle
- U-/H-Frame / Dipole
- Passive Cardioid
- TL closed/open/tapered
- MLTL
- TQWT
- Labyrinth
- Front Horn
- Rear Horn
- Folded Horn
- Tapped Horn
- Scoop
- Exponential/Tractrix/Conical/Hyperbolic families

### Spätere Spezialvarianten

Nur ergänzen, wenn ein belastbarer Bedarf und ein nachvollziehbares Modell existieren:

- Ripole
- PPSL / slot-loaded push-pull
- Onken/large-slot alignments
- dual-opposed arrangements
- distributed sub / multi-sub system design
- active cardioid arrays

Nicht jede exotische Bezeichnung braucht einen eigenen Solver, wenn sie nur eine Parametervariante eines vorhandenen Modells ist.

---

# 24. Sicherheits- und Plausibilitätsprüfungen

Zusätzlich zu bestehenden Warnungen:

- elektrische Mindestimpedanz;
- Weichenbauteil-Leistung;
- Verstärkerkanal-Leistung;
- Portresonanz;
- Gehäusemodus;
- Panelresonanz;
- Treiber-Ausbauweg;
- Schraubenabstand;
- verbleibende Wandstärke bei Taschen;
- Materialbruchrisiko bei zu kleinem Rand;
- Schwerpunkt/Kippstabilität grob;
- Wandhalterungsgewicht;
- Temperatur/Power Compression;
- DSP-Clipping/Headroom;
- PR-Xmax;
- Hornhals-Kompression als Hinweis.

Warnungen bleiben Engineering-Hinweise, keine Sicherheitszertifizierung.

---

# 25. Daten- und Lizenzstrategie

Vor öffentlicher/kommerzieller Verteilung klären:

- Darf Hersteller-/Händlerdatenbank mit ausgeliefert werden?
- Welche Produktbilder dürfen gespeichert werden?
- Welche Preisquellen dürfen automatisiert aktualisiert werden?
- Welche Lizenzen gelten für Referenzdaten?
- Welche Third-Party-Python-Pakete werden verteilt?

Bibliothek so bauen, dass rechtlich problematische Daten separat aktualisierbar sind.

---

# 26. Release-Plan

## V-02.08.00 – Geometrie-Härtung

Pflicht:

- 3D-/2.5D-Kollisionskernel;
- Gehrung/Falz/Nut korrekt in Geometrie;
- echte Plattenstöße;
- Montagefreiräume;
- Horn-/TL-Innenprofile härten;
- DXF-Validierung;
- große UI-/Service-Dateien zerlegen.

Abnahme:

- keine bekannte Kollision in Demo-/Regressionprojekten;
- Export verweigert bei geometrisch unmöglichem Aufbau.

## V-02.09.00 – Bibliothek und automatische Mehrwege

- deutlich mehr vollständig verifizierte Chassis;
- automatische 3-Wege- und 2.5-Wege-Auswahl;
- allgemeine Weichen-Netlist;
- reale Standardbauteilbibliothek;
- Component Compatibility Matrix;
- Pareto-Varianten.

## V-03.00.00 – Validierter Produktions-Beta-Stand

Release erst nach:

- reale Messvalidierung mehrerer Bauformen;
- Windows-Build;
- Sichttest;
- Projektmigration;
- Installer/portable Paket;
- Owner-Freigabe;
- bekannte Modellgrenzen vollständig dokumentiert.

V-03.00 ist **nicht** „fertig für immer“, sondern die erste Version, der man für reale Projekte mit dokumentierten Grenzen vertrauen kann.

## V-03.01.00 – Measurement & Crossover Studio

- Messworkflow;
- automatische akustische Weichenoptimierung;
- N-Wege-Netlist;
- Directivity-/Off-Axis-Grundlage;
- Leistungsprüfung.

## V-03.02.00 – Active / DSP

- DSP-Kette;
- aktive Varianten;
- Verstärkermodule;
- Biquad-Export;
- Limitierung/Headroom;
- MiniDSP/Equalizer-APO-Adapter soweit technisch/rechtlich sauber.

## V-03.03.00 – CAD & Manufacturing Pro

- 3D-Vorschau;
- STEP;
- Taschen/Nuten/Falze;
- CNC-Layer;
- Explosionsansicht;
- Restplattenlager;
- detaillierte Montageunterlagen.

## V-03.04.00 – Room & Placement

- Boundary Gain;
- Floor Bounce;
- Hörabstand;
- erste Raummoden;
- Multi-Sub-Grundlage.

## V-04.00.00 – Vollständige Design-Plattform

Zielkriterien:

- Assistent, Experte, Messmodus;
- große verifizierte Komponentenbibliothek;
- passive + aktive Systeme;
- validierte Kernsolver;
- CAD/Fertigung;
- Varianten-/Pareto-Optimierung;
- Raum-/Aufstellungskontext;
- reproduzierbare Builds;
- Pluginfähige Architektur.

---

# 27. Priorisierte nächste 20 Aufgaben

1. Aktuellen V-02.07-Branch als kanonischen Integrationsstand sichern.
2. 3D-/2.5D-Geometrie-Datenmodell definieren.
3. Kollisionsengine für Treiber/Port/Strebe/Wand implementieren.
4. Verbindungstypen stumpf/Gehrung/Falz/Nut modellieren.
5. `main_window.py`, `assistant_window.py`, `design.py`, `automatic.py` zerlegen.
6. Solver-Vertrauensstufen einführen.
7. Validierungsmatrix je Gehäusefamilie anlegen.
8. Drei reale Prototyp-Projekte für Closed/Bassreflex/PR festlegen.
9. Messprotokoll praktisch durchführen.
10. Bibliothek auf mindestens 100 vollständig berechenbare Chassis ausbauen.
11. Feldweise Provenienz im Bibliotheksmodell ergänzen.
12. allgemeine N-Wege-Weichen-Netlist einführen.
13. automatische 3-Wege-Auswahl implementieren.
14. akustische Weichenoptimierung auf FRD/ZMA implementieren.
15. Mindestimpedanz/Phase und Bauteilleistung prüfen.
16. Pareto-Optimierung im Assistenten ergänzen.
17. echte 3D-Vorschau als isolierten Technik-Spike bauen.
18. Windows-Onedir-Build und Clean-Machine-Smoke durchführen.
19. Installerstrategie festlegen.
20. V-03.00-Release-Checkliste mit Owner-Abnahme durchführen.

---

# 28. Definition „umfangreiches Programm“

Das Programm gilt nicht deshalb als umfangreich, weil viele Menüpunkte existieren. Es gilt als umfangreich, wenn ein realer Arbeitsablauf vollständig abgedeckt ist:

**Anforderung → Komponentenwahl → akustische Auslegung → Geometrie → Weiche/DSP → Simulation → Validierung → Fertigung → Prototypmessung → Revision.**

Für jeden Schritt muss es:

- nachvollziehbare Eingaben,
- reproduzierbare Berechnung,
- Plausibilitätsprüfung,
- dokumentierte Grenzen,
- speicherbaren Zustand,
- und verwertbare Ausgabe geben.

Das ist das eigentliche Zielbild für V-04.00.00.

---

# 29. Nicht vorziehen

Solange Solververtrauen, Bibliotheksqualität und 3D-Geometrie nicht ausreichend sind, nicht priorisieren:

- Cloud-Accountsystem;
- Online-Marktplatz;
- automatische Veröffentlichung;
- generatives „KI erfindet Lautsprecher“-Feature ohne physikalische Prüfung;
- FEM/BEM als Eigenentwicklung;
- ungeprüfte G-Code-Ausgabe;
- Live-Webscraping großer Händlerkataloge;
- kosmetische Animationen ohne UX-Nutzen.

---

# 30. Entscheidungsbedarf des Owners

Zusätzlich zu `coordination/OPEN_QUESTIONS.md`:

1. Wird das Programm privat, intern oder kommerziell verteilt?
2. Soll V-03.00 primär **Heim-Hifi**, **PA**, **Studio** oder alle drei gleichwertig optimieren?
3. Soll automatische 3-Wege-Auslegung Pflicht für V-03 sein?
4. Aktive/DSP-Systeme vor oder nach V-03?
5. Bevorzugtes CAD-Ziel: STEP/CadQuery, FreeCAD-Workflow oder primär DXF?
6. Welche realen Prototypen werden für Messvalidierung gebaut?
7. Welche Händler-/Herstellerbibliotheken dürfen dauerhaft ausgeliefert werden?
8. Welche Windows-Auslieferung wird bevorzugt: portable ZIP, Installer oder beides?

Bis diese Fragen entschieden sind, soll die Architektur Optionen offenhalten und keine stillen Annahmen festschreiben.
