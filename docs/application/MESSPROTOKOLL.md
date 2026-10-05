# Messprotokoll für die Modellvalidierung

Ziel: Messdaten eines gebauten Prototyps so aufnehmen, dass sie mit dem Prototypvergleich ausgewertet werden können
und zum Nachweis K3 (Messvalidierung) beitragen.

## Vorbereitung

- Prototyp so bauen, wie es die Zeichnung und die Stückliste angeben (Port-Länge, Dämmung, Volumina). Abweichungen notieren.
- Chassis einspielen: einige Stunden bei mäßigem Pegel betreiben, danach messen (T/S-Werte driften beim Einlaufen).
- Messsoftware, die **Impedanz mit Phase (ZMA)** und **Frequenzgang (FRD)** exportiert; Beispiele: REW, ARTA, VituixCAD.
  Dateiformat: Textspalten `Frequenz [Hz]  Pegel [dB]  Phase [°]` (FRD) bzw. `Frequenz [Hz]  Impedanz [Ω]  Phase [°]` (ZMA).
- Messpegel niedrig halten; kein Dauerton nahe der Resonanz bei hohem Pegel.

## Messungen je Prototyp

1. **Impedanz im Gehäuse** (10–1 000 Hz): Normalbetrieb, Dämmung wie gebaut. Bassreflex: Port offen.
2. **Impedanz mit verschlossenem Port** (nur Bassreflex): Es muss eine einzelne Spitze wie beim geschlossenen Gehäuse entstehen.
   Zeigt sie sich nicht, ist das Gehäuse undicht.
3. **Frequenzgang:** Nahfeld direkt vor Membran und Portmündung getrennt messen und nach Flächenverhältnis addieren (die
   Messsoftware kann das), oder gefenstertes Fernfeld im Freien. Nahfeld gilt nur unterhalb von etwa 300 Hz.
4. **Freiluft-Impedanz des Chassis** (Aufhängung frei) zur Kontrolle der T/S-Werte Fs, Qts.

## Auswertung

```
python -m lautsprecher_konstruktion.validation projekt.json --frd nahfeld.frd --zma impedanz.zma --out vergleich.md
```

oder in der Anwendung: **Werkzeuge → Prototyp vergleichen**.

## Dokumentation je Fall (Tabelle ausfüllen)

| Feld | Eintrag |
|---|---|
| Datum, Messperson | |
| Chassis (Hersteller, Modell, Charge) | |
| Gehäusetyp, Netto-Volumen, Port (Ø × Länge) | |
| Abweichung vom Plan | |
| Messmittel (Interface, Mikrofon, Software) | |
| Fb Simulation / Messung / Abweichung % | |
| F3 Simulation / Messung / Abweichung % | |
| RMS-Abweichung Frequenzgang [dB] | |
| Bewertung (gut / akzeptabel / abweichend) | |
| Auffälligkeiten (Leckage, Rattern, Portgeräusche) | |

## Nachweis K3

K3 ist erfüllt, wenn **mindestens drei Treiber in mindestens drei Bauformen** dokumentiert sind und die Abweichungen
eingeordnet wurden. Die Messdateien werden unter `coordination/runtime-tests/` als Nachweis abgelegt. Ohne diese
Nachweise bleibt der Status `NOT_RUN` – er wird nicht durch Simulation ersetzt.
