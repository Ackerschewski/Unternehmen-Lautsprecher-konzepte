# Validierung der Berechnungsmodelle (V-02.06.00)

Dieses Dokument beschreibt, **was geprüft ist** und **was noch nicht**. Es trennt automatische Prüfungen
(laufen bei jedem Testlauf) von Nachweisen, die nur mit gebauter Hardware möglich sind.

## 1. Automatisch geprüft (Referenztests)

`tests/test_v206_reference_models.py` vergleicht die Solver mit Textbuch-Beziehungen und Netzwerktheorie.
Die Tests nutzen die synthetische Demo-Chassis (`TESTDATEN`); sie belegen die **interne Konsistenz mit der Theorie**,
nicht die Übereinstimmung mit einem realen Lautsprecher.

| Prüfung | Referenz | Ergebnis |
|---|---|---|
| Geschlossen: Qtc = Qts·√(1+α), Fc = Fs·√(1+α) | Small 1972 | exakt (rel. 1e-9) |
| Geschlossen: F3/Fc für Qtc 0,5 / 0,707 / 1,0 | Hochpass 2. Ordnung: 1,554 / 1,000 / 0,786 | ±0,002 |
| Geschlossen: F3 als numerischer −3-dB-Punkt | unabhängige Nullstellensuche | ±0,2 % |
| Geschlossen: Flanke 12 dB/Oktave, flacher Hochtonbereich | Hochpass 2. Ordnung | ±0,05 dB |
| Bassreflex: Portlänge | Helmholtz: Leff = c²·A / ((2π·Fb)²·V) | ±1 % (c = 343 m/s) |
| Bassreflex QB3: Impedanzminimum bei Fb | Thiele 1971, Small 1973 | ±3 % |
| Bassreflex QB3: zwei gleich hohe Impedanzspitzen | QB3-Eigenschaft | ±5 % |
| Bassreflex: 24 dB/Oktave unter Fb | Hochpass 4. Ordnung | ±2 dB |
| Bassreflex QB3: F3 | Thiele-Näherung `0,26·Qts^−1,4·Fs` | ±10 % (Näherungsformel) |
| Bassreflex: Passivität (Re Z > 0) | Energieerhaltung | erfüllt |
| Bassreflex mit nahezu verschlossenem Port → geschlossenes Gehäuse | Grenzfall | Formabweichung < 1 dB |
| Weiche Butterworth 2: −3,01 dB bei fc, |HL|²+|HH|² = 1 | Netzwerktheorie | erfüllt |
| Weiche Linkwitz-Riley 2: −6,02 dB bei fc, |HL−HH| = 1 | Netzwerktheorie | erfüllt |
| Weiche 1./2. Ordnung: 6 bzw. 12 dB/Oktave | Netzwerktheorie | ±0,5 dB |
| E12-Rundung | Reihenabstand | ≤ 11 % |
| Schallwandstufe: 6,02 dB, halbe Stufe bei 115/B | Linkwitz, Näherung | exakt (Modelldefinition) |

Die Abweichung des F3 von der Thiele-Näherung (rund 7 %) liegt innerhalb der Genauigkeit dieser Näherungsformel;
der Solver bleibt bei Bedarf strenger zu prüfen (siehe Abschnitt 3).

## 2. Prototypvergleich (Werkzeug)

`Werkzeuge → Prototyp vergleichen` bzw. `python -m lautsprecher_konstruktion.validation` vergleicht Messungen mit der
berechneten Konstruktion:

- **Frequenzgang (FRD):** Pegelversatz wird angeglichen (Mittelwert über das Vergleichsband, abschaltbar), danach RMS-
  und Maximalabweichung sowie F3 nach der Konvention des Solvers (Referenz = Median 150–300 Hz).
- **Impedanz (ZMA):** Bei Bassreflex wird die Abstimmfrequenz als Impedanzminimum zwischen den zwei Spitzen bestimmt
  (parabolisch verfeinert), bei geschlossen die Resonanzspitze.
- **Portkorrektur:** Bei Bassreflex und isobarischem Bassreflex wird mit dem Modell die zusätzliche Portlänge gelöst, die das
  gemessene Impedanzminimum erklärt. Bei anderen ventilierten Typen gilt die Näherung Fb ∝ 1/√Leff und wird als „Näherung“
  gekennzeichnet. Annahme: Der Port wurde wie geplant gebaut und die Abweichung kommt allein vom Port.
- **Bewertung** (Richtwerte, kein Normwert): Frequenzgang RMS ≤ 1,5 dB gut, ≤ 3 dB akzeptabel; Abstimmung ≤ 5 % gut, ≤ 10 % akzeptabel.

Die Prüfung der Logik erfolgt mit synthetischen Kurven (`tests/test_v206_prototype_compare.py`): bekannte Portverlängerung →
Verfahren findet sie wieder; die vorgeschlagene Korrektur stellt die Abstimmung her (Rundlauf).

## 3. Offen: Messvalidierung

Folgendes ist **nicht** erfüllt und kann nur mit gebauten Prototypen nachgewiesen werden:

1. ≥ 3 reale Treiber in ≥ 3 Bauformen (z. B. geschlossen, Bassreflex, Passivmembran oder Bandpass) mit FRD/ZMA-Messung.
2. Dokumentierte Abweichung je Fall nach `MESSPROTOKOLL.md`; Auswertung mit dem Prototypvergleich.
3. Kalibrierung der Verlust-Parameter (Ql, Qa, Qp) aus diesen Messungen, falls die Abweichung systematisch ist.
4. Prüfung der Schallwandstufe-Näherung an einem Zweiwegelautsprecher.
5. Horn- und Linienmodelle (ebene Wellen) mit Impedanz- und Nahfeldmessung.

Bis dahin gilt: Simulationswerte sind Planungswerte. Es gibt keine Freigabe der Modelle für sicherheits- oder leistungskritische
Anwendungen.
