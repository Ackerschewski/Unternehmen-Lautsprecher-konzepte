# Design System – Projektprofil

Dieses Programm folgt dem Profil **Ackerschewski_code (Desktop)** aus `Basis-Ackerschewski-Design-System`
(`docs/DESKTOP_APPS.md`, `COLORS.md`, `TYPOGRAPHY.md`, `COMPONENTS.md`, `CHARTS_AND_DATA.md`, `ACCESSIBILITY.md`).
Tokens: `src/lautsprecher_konstruktion/ui/tokens.py`; Abgleich per Test mit `docs/design/design-tokens.snapshot.json`
(Stand Design-System-Commit 1a74fc9).

## Umgesetzt
- **Farben:** Akzent `#F27216` für Primäraktion, Auswahl, Fokus, aktiven Reiter (dünne Linie); Light/Dark gemäß freigegebenen Werten; Statusfarben `#22C55E/#F59E0B/#EF4444/#3B82F6`.
  Status immer als Glyph + Text (✓ ⚠ ✕ ℹ), Farbe nur als Randmarkierung. Text auf Orange ist dunkel (Kontrast ≥ 4,5, per Test).
- **Typografie:** Inter (UI), Source Serif 4 (Seitentitel), JetBrains Mono (technische Werte, Kennzahlen, Ergebnisprotokoll). Schriften liegen in `data/fonts` (SIL OFL, Lizenzen dabei) und sind im Windows-Build enthalten.
- **Themes:** System / Hell / Dunkel (Menü Ansicht), Wechsel ohne Neustart, gilt für Assistent, Expertenmodus und Diagramme.
- **Komponenten:** 4 px Radius, flache Eingaben mit feiner Kontur, keine Pillen, eine Primäraktion je Kontext, Gruppen durch Trennlinien statt Karten in Karten, Tabellen für technische Daten.
- **Progressive Disclosure:** Reiter von 9 auf 6 gruppiert (Zeichnungen gebündelt), Standard-Simulation zeigt 2 Diagramme (weitere auf Wunsch), 3-Wege-Felder erscheinen nur bei 3-Wege, Expertenmodus bleibt vollständig.
- **Branding:** „Ackerschewski_code“ dezent in der Fußzeile und unter Hilfe → Über, kein Logo.
- **Bedienbarkeit:** sichtbarer Fokus (Akzentkontur), Tastenkürzel, Tooltips, Fehlermeldungen mit nächstem Schritt.

## Begründete Abweichungen
- **Fertigungszeichnungen und PDF** sind Druckdokumente: weißes Papier und technische Linienfarben bleiben in beiden Themes.
- **Gehäuse-Zeichnungsblätter** nutzen die Linienfarbe der Zeichnung, nicht den Akzent.
- Die Haupt-Navigation bleibt eine Reiterleiste (Navigationstiefe 2), keine Seitenleiste.
- Windows-DPI-Skalierung ist nicht auf Windows geprüft (siehe `docs/application/CODEX_TESTUEBERGABE.md`).
