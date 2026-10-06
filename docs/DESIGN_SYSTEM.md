# Design System – Projektprofil

Dieses Programm folgt dem **ACK Studio Designpaket** aus `Basis-Ackerschewski-Design-System`
(`packages/ack-studio`: Tokens, `docs/DESIGN_RULES.md`, `README`, Komponenten-CSS). Das Paket ist dort seit Commit `f7ec5ad`
die einzige Gestaltungsgrundlage; das frühere Orange-Profil (Ackerschewski_code) gilt nicht mehr und ist nicht umgesetzt.
Tokens: `src/lautsprecher_konstruktion/ui/tokens.py`; Abgleich per Test mit `docs/design/ack-studio-tokens.snapshot.json`.

## Umgesetzt
- **Produktwelt:** Software (`software`): Light-Akzent `#172d46`, helle Softwareflächen `#edf2f7`/`#e4edf5`. Das Programm erzwingt diese Produktwelt auch bei alten gespeicherten `area=construction`-Werten. Konstruktion-Ocker ist nur eine sekundäre technische Farbe, keine normale Interaktionsfarbe.
- **Farben:** warmes Papier `#fbfaf7`, Text `#282723`, Software-Navy `#172d46`, Software-Linie `#4c6a83`, heller Dark-Mode-Akzent `#adcadb`. Grün kennzeichnet valide Zustände, Burgunder kritische Zustände; Ocker bleibt sekundär für konstruktive Hinweise.
- **Typografie:** Inter für Text und Bedienung, Cormorant Garamond (Regular, aus der variablen Google-Fonts-Schrift auf Gewicht 400 instanziiert) für große Titel. Schriften in `data/fonts` mit Lizenzen (SIL OFL), im Windows-Build enthalten.
- **Form:** Steuerelemente 8 px, Karten/Tabellen 14 px Radius, Abzeichen 4 px; feine Trennlinien, Primäraktion gefüllt, Sekundäraktionen mit Akzentkontur; Auswahl mit Akzentlinie; Fokus mit 2–3 px Akzentrahmen.
- **Status:** Symbol + Text (✓ ⚠ ✕ ℹ), Fehler zusätzlich gestrichelter Rahmen und fett; keine Statusfarben (das Paket definiert keine, Farbe ist Bereichsidentität).
- **Diagramme:** Der Bereich „Klang & Simulation“ enthält eine editierbare Fullrange-Zielkurve von 20 Hz bis 20 kHz. Ist-Daten werden nur in belegten Frequenzbereichen gezeigt; fehlende Mittel-/Hochtondaten werden ausdrücklich als unbekannt markiert. Technische Tiefton-/Hubdiagramme bleiben separat verfügbar.
- **Progressive Offenlegung:** 6 statt 9 Reiter, Standard-Simulation mit 2 Diagrammen, 3-Wege-Felder nur bei 3-Wege.
- **Zugänglichkeit:** sichtbarer Fokus, Tastenkürzel, Tooltips, Fehlertexte mit nächstem Schritt.

## Begründete Abweichungen (Desktop)
- **Dunkelmodus (Projekterweiterung):** neutral-dunkler Grund `#11161d`, Arbeitsfläche `#151c25`, Panel `#1b2530`, Band `#223141`; primäre Interaktion `#adcadb`. Damit ist die App nicht mehr eine einzige blaue Vollfläche. Zeichnungsblätter bleiben warme Papierflächen.
- **Bewegung:** `ui/motion.py`, nur kurze, nicht blockierende Übergänge (Zeichnungsmodus 240 ms OutCubic); Einstellung „Animationen reduzieren“ (Ansicht-Menü) führt Änderungen sofort aus.
- **Rückmeldung 2026-10-06 umgesetzt:** Ergebnisse werden bei Start/Fehlschlag/Unmöglich vollständig invalidiert; Fortschrittstext außerhalb des Balkens (Balken nur während der Berechnung); Zeichnungsmodus (Strg+D), Zoom „Einpassen/Seitenbreite/100 %/Strg+Mausrad“; Kennwertkarten statt Textbalken; Vergleichstabelle mit Kernspalten; Footer „ACK Studio“. Offen: Outline-Icons, Expertenmodus-Umbau, Windows-DPI-Prüfung.
- **Zielgrößen:** Das Paket verlangt 44 px für Touch. Auf dem Desktop sind Buttons und Felder etwa 40–44 px hoch, dichte Tabellen und Listen kleiner.
- **Bewegung:** Es gibt keine animierten Themewechsel; Übergänge entfallen (Reduced-Motion-konform).
- **Fertigungszeichnungen und PDF:** gemeinsame Drawing-Tokens in `drawings/style.py`; warme Papierfläche, Software-Navy für Hauptlinien/Titel, Software-Blau für technische Highlights, Burgunder für bekannte Bohrungen/kritische Markierungen und Ocker nur für konstruktive Material-/Dämpfungsinformation. Farbe ist nie alleiniger Informationsträger.
- **Keine Produktbilder, Icons-Sprite und Autoplay:** Für ein Konstruktionswerkzeug nicht vorgesehen; Symbole nur als Textglyphen.
- **Navigation:** Reiterleiste statt Seitenleiste.
- Windows-DPI-Skalierung ist nicht auf Windows geprüft (siehe `docs/application/CODEX_TESTUEBERGABE.md`).
