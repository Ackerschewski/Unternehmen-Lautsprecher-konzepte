# Bibliotheks-Abdeckung

Erzeugt aus `data/library` mit `python -m lautsprecher_konstruktion.library.coverage`. Alle Werte sind aus den gespeicherten Datensätzen abgeleitet; fehlende Felder werden nie ergänzt.

## Reale Herstellerdaten

Chassis gesamt: **96**

| Kriterium | Anzahl |
|---|---|
| Gehäuseberechnung (`enclosure_ready`) | 19 (20 %) |
| Weichenentwurf (`crossover_ready`) | 0 (0 %) |
| Fertigungsmaße (`manufacturing_ready`) | 18 (19 %) |
| Breitbandaussage 20 Hz–20 kHz (`fullrange_ready`) | 0 (0 %) |
| Preis geprüft (`pricing_ready`) | 96 (100 %) |
| 3D-Hülle (`three_d_ready`) | 18 (19 %) |
| vollständige Herstellerdaten (alle Abdeckungsfelder) | 0 (0 %) |

Mit hinterlegten T/S-Daten: 20 (21 %). Reine Katalog-/Preiseinträge ohne Treiberdaten: 76 (79 %).

Häufigste Lücken:

- Frequenzgang (FRD): 96 (100 %) fehlen
- Impedanz (ZMA): 96 (100 %) fehlen
- Montagemaße: 78 (81 %) fehlen
- 3D-Hülle: 78 (81 %) fehlen
- T/S-Parameter: 77 (80 %) fehlen

## Demo-/Testdaten (getrennt, nicht Teil der realen Abdeckung)

Chassis gesamt: **6**

| Kriterium | Anzahl |
|---|---|
| Gehäuseberechnung (`enclosure_ready`) | 5 (83 %) |
| Weichenentwurf (`crossover_ready`) | 0 (0 %) |
| Fertigungsmaße (`manufacturing_ready`) | 6 (100 %) |
| Breitbandaussage 20 Hz–20 kHz (`fullrange_ready`) | 0 (0 %) |
| Preis geprüft (`pricing_ready`) | 0 (0 %) |
| 3D-Hülle (`three_d_ready`) | 6 (100 %) |
| vollständige Herstellerdaten (alle Abdeckungsfelder) | 0 (0 %) |

Mit hinterlegten T/S-Daten: 6 (100 %). Reine Katalog-/Preiseinträge ohne Treiberdaten: 0 (0 %).

Häufigste Lücken:

- Frequenzgang (FRD): 6 (100 %) fehlen
- Impedanz (ZMA): 6 (100 %) fehlen
- Preis mit Prüfdatum: 6 (100 %) fehlen
- T/S-Parameter: 1 (17 %) fehlen

## Lesehinweise

- `crossover_ready` und `fullrange_ready` erfordern eine FRD- und eine ZMA-Datei am Eintrag. Ohne diese Dateien gilt keine Aussage über 20 Hz–20 kHz.
- `three_d_ready` bedeutet nur: Außen-/Ausschnittsmaße und Einbautiefe reichen für eine vereinfachte Hüllgeometrie.
- Preise gelten als geprüft nur mit Preis und Prüfdatum; sie sind Momentaufnahmen.
