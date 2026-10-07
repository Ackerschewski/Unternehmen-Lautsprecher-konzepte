# Build-Report TASK-0029 – Product Truth & Depth Sprint

Stand: 2026-10-07 · Branch `claude/modest-bell-guqoxu` · Prüfumgebung: Linux, Qt offscreen. **Windows/DPI 100/125/150 %: NOT_RUN.**

## Ergebnis in einem Satz

Die in TASK-0027 übersprungenen Kernfunktionen (glatte Zielkurve mit echten EQ-Bändern, Bibliotheks-Readiness, Dämmung als Projektobjekt, interaktive 3D-Vorschau) sind umgesetzt und getestet, dazu die Korrektheitsarbeit aus der V3.3-Review (Preiswahrheit, erklärbare Empfehlung, geprüfte Vorschläge), eine entschlackte Varianten- und Fertigungsansicht und eine neue Evidence-Serie. Einzelne Punkte sind bewusst nur teilweise erledigt; sie stehen unter „Weiterhin offen“.

## Reihenfolge und Umsetzung (bindende Reihenfolge des Tasks)

### A – Korrektheit

- **Preiswahrheit** (`services/price_status.py`): Status `COMPLETE`, `ESTIMATED`, `PARTIAL`, `UNKNOWN`; bekannte und geschätzte Kosten getrennt (Händlerpreis gegenüber Plan-/Materialreferenzpreis), fehlende Positionen namentlich, Abdeckung in Prozent. „Günstiger“ gibt es nur, wenn **beide** Varianten vollständig vergleichbar bepreist sind **und** der Unterschied mindestens 3 % beträgt. Preis ist bei unvollständiger Abdeckung kein Score-Anteil und im Vergleich nicht rankbar („Preisranking nicht möglich“). Der Preis erscheint als „18/20 Positionen bepreist“.
- **Erklärbare Empfehlung:** Anzeige „Zielerfüllung 66 %“ aus nur den belegten Kriterien, darunter Aufschlüsselung (Tiefbass, Kompaktheit, Auslenkungsreserve, Port, Gruppenlaufzeit, Linearität, Budget, Zielkurve), „Nicht bewertet: …“ und getrennt „Zusätzlich, nicht im Score“ (Datenabdeckung, Bauaufwand). Hat die Empfehlung mehr Hinweise als eine Alternative, steht ein Satz dazu, **warum** sie trotzdem vorn liegt (`recommendation_note`).
- **Statusbanner:** keine Null-Zähler (`ui/status_banner.py`).
- **Datenabdeckung und Modellstatus getrennt:** Karte zeigt „Eingeschränkt · 63 %“, der Hinweis nennt den Modellstatus („Weiche vorläufig · keine FRD · keine ZMA“).
- **Deutsch im Präsentationslayer** (`presentation.py`, nur ganze Wörter): Stückliste, Weichen-CSV und Portfehler. Interne IDs bleiben englisch.
- **Diagnosemeldungen:** Portlängen-Fehler als vollständige Sätze mit Einheit, aktuellem und benötigtem Wert; ein falscher Rat („kleineren Port-Durchmesser“) wurde korrigiert.
- Beim Test-Aufbau entdeckt und behoben: In der Stücklisten-Zusammenfassung fehlten Klammern am Aufruf; der Fehler wurde von PySide6 verschluckt. Seither **schlägt jeder Test fehl, in dem ein Qt-Slot eine Ausnahme wirft** (`tests/conftest.py`).

### B – EQ (aus TASK-0027)

- Glatte Zielkurve: 13 feste Kontrollpunkte, PCHIP in log f, 900 Renderpunkte, Kontrollpunkte exakt, Überschwinger begrenzt (`targets/smooth.py`).
- `EQBand` mit Typ (Glocke, Low-/High-Shelf, Low-/High-Pass, Notch), Frequenz 20 Hz–20 kHz, Gain ±18 dB, Q 0,2–10, Ordnung 2/4; Antwort aus echten RBJ-Biquads bei 48 kHz (`targets/eq.py`). Keine Gaußkurve.
- UI: Band-Inspector (Aktiv, Typ, Frequenz, Gain, Q, Entfernen), Ziehen in X/Y, Hinzufügen/Löschen, Undo/Redo, Persistenz im Projekt (`SpeakerProject.target_eq_bands`). Bei Gleichstand beim Anklicken hat das Band Vorrang vor dem Kontrollpunkt.
- Die Zielkurve fließt (mit EQ) in die Passung der Automatik ein.

### C – Bibliothek

- **Readiness abgeleitet, nicht gepflegt** (`library/readiness.py`): `enclosure_ready` (fs, Qts, Vas, Sd), `crossover_ready` (FRD **und** ZMA am Eintrag), `manufacturing_ready` (Außen-/Ausschnittsdurchmesser, Einbautiefe), `fullrange_ready` (FRD, ZMA und belegtes Band 50 Hz–15 kHz), `pricing_ready` (Preis **und** Prüfdatum), `three_d_ready` (Hülle aus Maßen).
- **Datenabdeckung in %** nur aus sieben definierten Feldern (T/S, FRD, ZMA, Montage, Preis, 3D-Hülle, Quelle). Bibliotheksdialog zeigt Abdeckung, Eignung und was fehlt; Testdaten sind gekennzeichnet.
- **Coverage-Report** `docs/application/LIBRARY_COVERAGE.md` (erzeugt, per Test auf Aktualität geprüft).

**Coverage vorher/nachher:** Vorher gab es keine abgeleitete Bewertung. Nachher: von 96 realen Chassis sind 19 gehäuserechenbereit (20 %), 18 fertigungs- und 3D-bereit (19 %), alle 96 preisgeprüft (100 %), **0 weichen- oder breitbandbereit** (keine FRD/ZMA im Bestand), 76 (79 %) reine Katalog-/Preiseinträge ohne T/S-Daten. Es wurden **keine Daten ergänzt**, um Prozentwerte zu verbessern; die Zahlen zeigen den tatsächlichen Datenstand.

Kopplung an den Assistenten: Die Datenqualitätskarte und die Variantenchips nennen fehlende FRD/ZMA; es wird keine Aussage über 20 Hz–20 kHz ohne Messdaten gemacht. **Nicht umgesetzt:** Bevorzugung FRD/ZMA-bereiter Komponenten im Auswahlalgorithmus (siehe offen).

### D – Dämmung als Projektobjekt (`enclosure/treatment.py`)

- `AcousticTreatment` (Typ, Material, Position, Fläche, Dicke, optional Dichte/Preis pro m², Freihalten-Notiz); Typen Wandbelag, Füllung, lokaler Absorber, resistive Vent-Füllung, TL-Segment. Die Planer-Empfehlung (Wandbelag, Vent-Einsatz) wird als abgeleitetes Treatment geführt.
- Regeln: geschlossen (Füllung wirkt wie scheinbares Volumen, Effekt nicht eingerechnet, Hinweis); Bassreflex (Füllung im Port ist Fehler, Füllung sonst Warnung mit Portabstand); Bandpass (Position muss eine Kammer sein); TL/Horn (**keine Wirkung erfunden**, nur Stückliste/Position/Hinweis); Vent-Füllung nur aperiodisch/Kardioid.
- Sichtbar in Projekt, Stückliste (eine Zeile je Treatment, Preis unbekannt bleibt „Preis fehlt“), Bauanleitung, Innen-/Schnittzeichnung (Rechtecke aus derselben Szene) und 3D.

### E – 3D-MVP

- **Szenenmodell UI-unabhängig** (`enclosure/scene.py`): Platten, Chassis, Port, Passivmembran, Verstärkungsrahmen, Trennwand, Dämmung, alle aus Gehäuse-, Frontelement-, Verstärkungs- und Treatment-Objekten; keine Parallelgeometrie.
- **Technik:** eigener numpy-Z-Buffer-Rasterizer (`ui/raster.py`), gezeichnet über QPainter. Kein OpenGL nötig, läuft auf jedem Rechner und offscreen. Orbit (Maus), Zoom (Rad), ISO/Front/Seite/Oben, Zurücksetzen, durchsichtige Außenwände; beim Ziehen gröber, im Stand 2× supersampled.
- **Genauigkeit gekennzeichnet:** Plattenmaße „Nennmaß aus der Konstruktion“; Chassis, Port, Verstärkungen „vereinfachte Geometrie“, kein Hersteller-CAD. Objekte ohne definierte Position werden aufgelistet statt geraten.
- Hero des Ergebnisses nutzt die 3D-Szene; für Schallwand, Horn, Tapped Horn und gefaltete Linien bleibt die 2D-Vorschau (Fallback).
- Neuer Bereich **„3D & Konstruktion“** (Szene plus Objektliste mit Genauigkeit), erst mit Entwurf aktiv.

### F – Varianten

Karten aus Metrik-Chips (Maße, F3, Max-SPL, Hub, Port, Preisstatus, Datenabdeckung, Plattenzahl, Warnungen) statt Textblock; Mini-Balkenvergleich (Tiefbass, Kompaktheit, Pegel, Preis, Datenabdeckung, Bauaufwand), Preiszeile deaktiviert bei unvollständigen Preisen. Tab ist scrollbar, kein horizontaler Überlauf bei 1280 px.

### G – Nicht machbar 2.0: Relaxation-Algorithmus (`services/relaxation.py`)

1. Der Entwurfsrechner merkt sich bis zu 4000 Kandidaten, die **nur einstellbare** Grenzen verfehlen (Tiefe, Außenvolumen, F3, Budget, SPL), mit den gemessenen Werten.
2. Aus jedem Kandidaten entsteht ein Änderungsvektor (sicher gerundet: Tiefe auf 5 mm auf, SPL ab). Vorschläge, die eine Grenze mehr als verdreifachen, entfallen.
3. Rang nach normierter Größe der Änderung; zuerst verschiedene Änderungsarten, dann deutlich verschiedene Werte.
4. **Jeder** der höchstens drei Vorschläge wird mit dem echten Entwurfsrechner erneut gerechnet; nur machbare werden gezeigt, mit Anzahl der gefundenen Entwürfe. Höchstens sechs Prüfläufe, im Hintergrund-Thread.
5. Beispiel (Test): Tiefe 100 → 145/185/220 mm mit Ziel-F3 35 → 72/71/62 Hz, jeweils 2 Entwürfe.

### H – Fertigung

Zusammenfassung oben (bekannte Kosten, geschätzte Kosten, fehlende Preise, Plattenzahl und Verschnitt, Gehäusegewicht, Bauteile), Stückliste nach Gruppen (Gehäuse, Chassis, Frequenzweiche, Anschlüsse, Dämmung, Hardware) mit Zwischensummen und Preis-Badges (Händlerpreis, Materialreferenz, Planpreis, Preis fehlt – immer mit Wort, nicht nur Farbe), Export-Liste mit Status je Format. STEP ist angekündigt und als „noch nicht verfügbar“ markiert, **nicht vorgetäuscht**.

### I – Polish

Startkarten brechen Text um statt ihn abzuschneiden; Untertitel entfällt nach einem Ergebnis; Kennzahlenkarten sind anklickbar (Preis → Fertigung, Warnungen/Datenqualität → Details); „18/20 Positionen bepreist“.

### Governance

`assistant_window.py` 1948 → 1470 Zeilen (Grenze 1500) durch Auslagerung in `sound_lab.py`, `result_text.py`, `assistant_files.py`. `tools/validate_project.py` meldet keine Code-Fehler mehr; die verbleibenden Fehler betreffen ausschließlich das Schema der Task-Dokumente TASK-0026 bis TASK-0050 (nicht von mir verändert).

## Tests und Qualität

- **457 Pytest-Fälle grün** (352 im V-02.07.00-Bericht), Ruff grün, `mypy --strict` für alle Nicht-UI-Pakete grün (129 Dateien).
- Neue Testdateien: `test_v212_diagnostics`, `test_v212_price_truth`, `test_v214_eq`, `test_v214_target_state`, `test_v214_eq_ui`, `test_v215_library_readiness`, `test_v216_treatment`, `test_v217_scene`, `test_v218_variants`, `test_v219_relaxation`, `test_v220_manufacturing_view`; Pflichttests zur Preisregel: `test_v212_price_truth` (Status, Vergleichbarkeit, 3-%-Regel, falsches „Günstiger“), dazu `test_v218_variants` (Chips, Balken, Tag).

## Evidence

`coordination/feedback/evidence/2026-10-07-v3-4/`: Dark und Light, 1280 × 720 und 1920 × 1080 (Start, Ergebnis mit 3D, durchsichtige Wände, Variante C, Varianten, Klang, Zeichnungen, Fertigung, 3D & Konstruktion, Nicht machbar vor und nach der Kombinationssuche) sowie die Bibliotheks-Readiness. Echte Renderings der Anwendung (Linux, offscreen), **keine Windows-Aufnahmen**.

## Weiterhin offen (ehrlich)

- **Windows/DPI 100/125/150 %: NOT_RUN.** Kein Windows-Build und kein Sichttest auf echter Hardware.
- **B4 nur teilweise:** Zielkurve (Basis und mit EQ) und Ist-Kurve (FRD/Weichensumme oder Gehäusemodell) werden getrennt dargestellt, nur wenn Daten da sind. Eine eigene **DSP-Antwort** und die Summe aus Ziel, Weiche und DSP fehlen; die EQ-Bänder formen die Ziel- statt einer simulierten DSP-Kette. Gehört zu TASK-0034.
- **Bibliothek:** Es gibt weiterhin keine FRD/ZMA-Dateien im Bestand; `crossover_ready` und `fullrange_ready` sind für alle Einträge falsch, bis echte Messdaten importiert werden. Die Bevorzugung FRD/ZMA-bereiter Chassis im Auswahlalgorithmus fehlt noch (TASK-0031/0039).
- **Deutsch (A5) teilweise:** Stückliste, Weichen-CSV, Preisarten, Bibliotheks- und Diagnosetexte sind deutsch. Teilebezeichnungen im Zuschnittplan und in einzelnen Zeichnungstabellen sowie ältere Solver-Hinweise im Expertenfenster können noch englische Fragmente enthalten.
- **Diagnosen (A6) teilweise:** Port- und Volumenmeldungen sind vollständige Sätze mit Einheit; nicht jeder ältere Solver-Hinweis wurde angefasst.
- **3D:** nur rechteckige Gehäuse (geschlossen, Bassreflex, Passivmembran, Bandpass, isobarisch, Aperiodisch u. a.). Keine Kollisionsprüfung, keine Verbindungsdetails, keine Treiber-CAD, kein STEP; Dämmung auf Seiten, Kammern, Port und Segmenten ohne 3D-Position wird nur aufgelistet.
- **Dämmung:** Für TL und Horn wird bewusst keine Wirkung berechnet; Füllung im geschlossenen Gehäuse ist als scheinbares Volumen nicht eingerechnet. Preis je m² nur, wenn Nutzer:in ihn angibt. Die Zeichnung zeigt Rückwand, Decke und Boden, Seitenwände nur in der Liste.
- **Relaxation:** Suche läuft bis zu ~10 s (sechs volle Prüfläufe); Randfälle ohne Ein-Grenzen-Kandidaten liefern keine Vorschläge und sagen das.
- **Governance-Gate:** Die Task-Dokumente TASK-0026 bis TASK-0050 erfüllen das Template-Schema nicht (fehlende Überschriften, Typ-Feld); das ist Aufgabe der Planung.

## Nächste Schritte

1. Nutzerprüfung der Evidence; Windows-Test mit 100/125/150 % Skalierung.
2. TASK-0030 (Solver-Validierung), 0031 (Bibliothek und Provenienz), 0032 (3D-Geometriekern) laut Roadmap, danach 0033/0034.
