# Build-Report TASK-0030 – Solver Validation & Reference Lab

Stand: 2026-10-07 · Branch `claude/modest-bell-guqoxu` · Linux, Qt offscreen. **Windows/DPI: NOT_RUN. Prototypmessung: NOT_RUN (nicht Teil des Tasks).**

## Ausgangsstand

29 Gehäusetypen waren als SUPPORTED registriert, aber ohne einheitliche Vertrauensangabe. Referenztests gab es nur verstreut (`test_v206_reference_models.py` für geschlossen/Bassreflex/Weiche). Die Automatik stufte alle Typen gleich ein.

## Ergebnis

- **Solver-Deskriptoren** für alle 29 Typen (`validation/solvers.py`): Gleichungen, Quellen, bekannte Grenzen, Modellversion, zentrale Konventionen (F3, Vb, Fb, SPL).
- **Vertrauensstufen** (`validation/trust.py`): Experimentell, Formel geprüft, Referenz geprüft, Am Prototyp validiert. Die vergebene Stufe darf nie über der liegen, die bestandene Fälle belegen (Test). Konsistenzfälle belegen nichts. Prototyp ist eine eigene Stufe; keine Datenbasis dafür vorhanden, also vergibt sie niemand.
- **Verteilung:** 2 × Referenz geprüft (geschlossen, Bassreflex), 9 × Formel geprüft (aperiodisch, Passivmembran, Bandpass 4., Isobarik ×3, Infinite/Open Baffle, Dipol), **18 × Experimentell** (alle TL- und Horn-Typen, Frontlasthorn, Tapped Horn, Kardioid, MLTL, Bandpass 6. Ordnung ×2). Bei 12 der 18 belegen die Fälle die Formeln, vergeben wird bewusst weniger, weil Faltungsverluste, Mundlast und Dämmwirkung Näherungen ohne Referenz sind (siehe `VALIDATION_MATRIX.md`, Spalten „Vergeben“ und „Belegt“).
- **Referenzfälle** (`validation/cases.py`): 65 Fälle mit 83 Erwartungen (Wert, Einheit, Toleranz abs/rel, Quelle, technische Begründung). Mindestens ein Fall je Solver; Arten: Literatur, Formel, Grenzfall, Konsistenz.
- **Unabhängige Referenzrechnung** (`validation/independent.py`): Erwartungswerte werden **ohne Aufruf des geprüften Solvers** berechnet (Small, Thiele, Olson, Beranek, Levine/Schwinger).
- **Harness** (`validation/reference.py`, CLI `python -m lautsprecher_konstruktion.validation.reference_cli`): ein Befehl, maschinenlesbare JSON-Datei, quantitativer Diff (FAIL/DRIFT/CRASH), versionierter Referenzstand `data/validation/reference_baseline.json`. Dauer der schnellen Suite ≈ 6 s.
- **Validierungsmatrix** `docs/application/VALIDATION_MATRIX.md/.json`, erzeugt aus Deskriptoren, Fällen und einem Lauf; ein Test prüft Aktualität. Beförderungsregeln stehen darin.
- **Gemeinsamer Kanalkern** `acoustics/waveguide.py`: Kettenmatrix und Mundlast aus Folded-Line-, Front-Horn- und Tapped-Horn-Solver herausgelöst. Rechenergebnisse **bit-identisch** (maximale Differenz 0 über alle 29 Familien, vorher/nachher verglichen).

## Was die Prüfung gefunden hat

- **Fehler in meiner eigenen Referenzformel**, nicht im Solver: Der s²-Term der Small-Gleichung war falsch (α gehört zu Tb², nicht zu Ts²). Bei Ts = Tb fällt das nicht auf. Aus der Schaltung neu hergeleitet; danach stimmt der Solver mit der Formel auf 1e-14 dB überein.
- **Falsche Literaturannahme meinerseits:** Die maximal flache B4-Ausrichtung hat Vas/Vb = √2 (nicht 1), Qts 0,3827, Fb = Fs. Aus dem Butterworth-Polynom hergeleitet; der Solver liefert F3/Fs = 1,0006 und 0 dB Überschwingen.
- Falscher Testaufbau beim Dipol (zwei verschiedene Rückvolumina) korrigiert.
- Die Strahlungsimpedanz im Kernmodul war als „flanschloser Kolben“ beschrieben, tatsächlich ist es die Levine-Schwinger-Näherung des freien Rohrendes (0,25 ka² + 0,61 j ka). Dokumentation berichtigt, Rechnung unverändert.
- **Zahlen unverändert, aber jetzt belegt:** keine Solverformel musste geändert werden.

## Integration

- **Assistent:** Ein Entwurf mit experimentellem Modell kann nie Favorit „A“ sein, solange ein geprüftes Modell existiert (Sortierschlüssel). Experimentelle Varianten tragen „· experimentell“ im Namen, den Chip „Experimentelles Modell“ und eine Warnung im Statusbanner. Wählt der Nutzer ausdrücklich einen experimentellen Typ, sind alle Varianten gleichrangig und gekennzeichnet.
- **Detailtext** nennt Vertrauensstufe, Modellversion und die wichtigste Grenze.
- **Expertenansicht „Modellvertrauen…“** (Menü Werkzeuge und Experten-Fenster): alle Solver mit Stufe, Fallzahl, Prüfstand; Detail mit Quellen, Grenzen, Fällen. Referenzfälle laufen nur auf Knopfdruck im Hintergrund-Thread, nie beim Zeichnen.
- **Export:** `modellvertrauen.json` und ein Abschnitt in `projektzusammenfassung.txt`.
- **Migration:** Projektdateien speichern keine Solverdaten; alte Projekte laden unverändert, der Export nennt den aktuellen Modellstatus und weist darauf hin, dass ältere Dateien ihn nicht speichern.

## Fehlerpolitik (getestet)

NaN/Inf, fehlende Ausgabe und Abstürze sind Fehlschläge, nie Auslassungen. Ein Referenzstand wird nur mit Begründung (mindestens 15 Zeichen) und Namen erneuert und nie mit fehlgeschlagenen Fällen. Der Hash der Fall-Definitionen im Referenzstand muss zu den Fällen passen. Ein Mutationstest (falsche Schallgeschwindigkeit im Kanalkern) beweist, dass die Fälle Fehler fangen.

## Tests

- Neue Testdatei `test_v221_validation.py` mit 21 Fällen (Deskriptoren, Abdeckung, Vertrauensobergrenze, Suite, Politik, Mutationstest, CLI, Matrix, Ranking, Export, Migration, Dialog, Chips/Banner).
- Gesamtlauf: **478 Pytest-Fälle grün** (457 vorher), Ruff und `mypy --strict` (Nicht-UI, 139 Dateien) grün.

## Evidence

`coordination/feedback/evidence/2026-10-07-v3-5-solver-trust/`: Vertrauensdialog vor/nach dem Lauf (Dark/Light, 1280×720 und breit), Ergebnisansicht und Varianten mit experimentellem Modell, Beispiel eines bestandenen Laufs, absichtlich fehlgeschlagener Diff, Matrix und Lauf als JSON. Die Bilder habe ich selbst gesichtet.

## Bekannte Grenzen

- **Keine Prototypvalidierung.** Alle Aussagen beruhen auf Literatur und Formeln; kein Typ ist am Prototyp validiert.
- Die Neuberechnungs-Fälle der Linien-/Horn-Familien verwenden dieselben Gleichungen wie der Solver (unabhängig kodiert, aber vom selben Autor); die echte Unabhängigkeit liefern die Kanalkern-Fälle (gleichförmiger Kanal, Olson-Horn).
- Tapped Horn, Kardioid, MLTL und Bandpass 6. Ordnung haben keine vollständige Referenz (nur Grenzfall oder Konsistenz); sie bleiben experimentell.
- Geometrieerzeugung (Falten, Segmentieren) ist nur auf Konsistenz geprüft.
- Windows/DPI: NOT_RUN.

## Nächste Schritte

1. Prototypmessung und PROTOTYPE-Fälle für Geschlossen und Bassreflex (TASK-0035).
2. TASK-0031 (Bibliothek und Provenienz), TASK-0032 (Geometriekern).
