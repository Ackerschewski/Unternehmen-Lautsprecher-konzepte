# Design System – Projektprofil

Dieses Programm folgt dem **ACK Studio Designpaket** aus `Basis-Ackerschewski-Design-System`
(`packages/ack-studio`: Tokens, `docs/DESIGN_RULES.md`, `README`, Komponenten-CSS). Das Paket ist dort seit Commit `f7ec5ad`
die einzige Gestaltungsgrundlage; das frühere Orange-Profil (Ackerschewski_code) gilt nicht mehr und ist nicht umgesetzt.
Tokens: `src/lautsprecher_konstruktion/ui/tokens.py`; Abgleich per Test mit `docs/design/ack-studio-tokens.snapshot.json`.

## Umgesetzt
- **Bereich:** Konstruktion (`construction`): Akzent `#735419`, Fläche `#f7f1e4`, Band `#f0e7d0`. Einstellbar über den Schlüssel `area` in den Benutzereinstellungen (`jewelry`, `apparel`, `construction`, `software`).
- **Farben:** warmes Papier `#fbfaf7`, Text `#282723`, Sekundärtext `#65615d`, Linie `#e2ddd5`, Text auf Akzent weiß. Kontrast aller Bereichsfarben per Test ≥ 4,5.
- **Typografie:** Inter für Text und Bedienung, Cormorant Garamond (Regular, aus der variablen Google-Fonts-Schrift auf Gewicht 400 instanziiert) für große Titel. Schriften in `data/fonts` mit Lizenzen (SIL OFL), im Windows-Build enthalten.
- **Form:** Steuerelemente 8 px, Karten/Tabellen 14 px Radius, Abzeichen 4 px; feine Trennlinien, Primäraktion gefüllt, Sekundäraktionen mit Akzentkontur; Auswahl mit Akzentlinie; Fokus mit 2–3 px Akzentrahmen.
- **Status:** Symbol + Text (✓ ⚠ ✕ ℹ), Fehler zusätzlich gestrichelter Rahmen und fett; keine Statusfarben (das Paket definiert keine, Farbe ist Bereichsidentität).
- **Diagramme:** Papierfläche, feine Linien, Akzent für die Hauptkurve, Grenzwerte gestrichelt und beschriftet.
- **Progressive Offenlegung:** 6 statt 9 Reiter, Standard-Simulation mit 2 Diagrammen, 3-Wege-Felder nur bei 3-Wege.
- **Zugänglichkeit:** sichtbarer Fokus, Tastenkürzel, Tooltips, Fehlertexte mit nächstem Schritt.

## Begründete Abweichungen (Desktop)
- **Dunkelmodus (Projekterweiterung):** Das Paket definiert nur ein helles Theme. Auf ausdrücklichen Wunsch gibt es ein dunkles Projekt-Theme (Ansicht → Erscheinungsbild: System/Hell/Dunkel), abgeleitet aus den Paket-Tokens: warmer Nachtgrund `#1c1b18`, Text `#f1eee8`/`#b4aea5`, Linie `#3b3832`; der Bereichsakzent wird bis mindestens 4,8:1 Kontrast aufgehellt, Flächen mischen den Akzent in den Grund. Zeichnungsblätter und Druckexporte bleiben Papier. Sobald das Paket ein Dark-Theme definiert, ersetzt es diese Ableitung.
- **Bewegung:** `ui/motion.py`, nur kurze, nicht blockierende Übergänge (Zeichnungsmodus 240 ms OutCubic); Einstellung „Animationen reduzieren“ (Ansicht-Menü) führt Änderungen sofort aus.
- **Rückmeldung 2026-10-06 umgesetzt:** Ergebnisse werden bei Start/Fehlschlag/Unmöglich vollständig invalidiert; Fortschrittstext außerhalb des Balkens (Balken nur während der Berechnung); Zeichnungsmodus (Strg+D), Zoom „Einpassen/Seitenbreite/100 %/Strg+Mausrad“; Kennwertkarten statt Textbalken; Vergleichstabelle mit Kernspalten; Footer „ACK Studio“. Offen: Outline-Icons, Expertenmodus-Umbau, Windows-DPI-Prüfung.
- **Zielgrößen:** Das Paket verlangt 44 px für Touch. Auf dem Desktop sind Buttons und Felder etwa 40–44 px hoch, dichte Tabellen und Listen kleiner.
- **Bewegung:** Es gibt keine animierten Themewechsel; Übergänge entfallen (Reduced-Motion-konform).
- **Fertigungszeichnungen und PDF** sind Druckdokumente mit technischen Linienfarben auf weißem Papier.
- **Keine Produktbilder, Icons-Sprite und Autoplay:** Für ein Konstruktionswerkzeug nicht vorgesehen; Symbole nur als Textglyphen.
- **Navigation:** Reiterleiste statt Seitenleiste.
- Windows-DPI-Skalierung ist nicht auf Windows geprüft (siehe `docs/application/CODEX_TESTUEBERGABE.md`).
