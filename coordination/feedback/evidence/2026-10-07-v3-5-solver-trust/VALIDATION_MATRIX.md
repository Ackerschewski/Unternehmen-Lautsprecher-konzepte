# Validierungsmatrix

Erzeugt mit `python -m lautsprecher_konstruktion.validation.matrix`. Alle Angaben stammen aus den Solver-Deskriptoren, den Referenzfällen und einem Lauf; nichts ist von Hand eingetragen.

Stand der Fall-Definitionen: `5ee1a84ac62645f7` · alle Fälle bestanden: **ja**

## Übersicht

| Stufe | Anzahl Gehäusetypen |
|---|---|
| Experimentell | 18 |
| Formel geprüft | 9 |
| Referenz geprüft | 2 |
| Am Prototyp validiert | 0 |

„Vergeben“ ist die Stufe, die das Programm zeigt; „Belegt“ ist die höchste Stufe, die die bestandenen Fälle rechtfertigen. Vergeben wird nie mehr als belegt, kann aber weniger sein, wenn das Modell Näherungen enthält, die für Nutzer:innen zählen.

## Matrix

| Gehäusetyp | Solver | Vergeben | Belegt | Fälle (bestanden) | Art der bestandenen Fälle |
|---|---|---|---|---|---|
| Geschlossen | `sealed` | Referenz geprüft | Referenz geprüft | 3/3 | Formel, Konsistenz, Literatur |
| Bassreflex | `bass_reflex` | Referenz geprüft | Referenz geprüft | 5/5 | Formel, Konsistenz, Literatur |
| Aperiodisch | `aperiodic` | Formel geprüft | Formel geprüft | 4/4 | Formel, Grenzfall, Konsistenz |
| Passivmembran | `passive_radiator` | Formel geprüft | Formel geprüft | 3/3 | Formel, Konsistenz |
| Bandpass 4. Ordnung | `bandpass_4` | Formel geprüft | Formel geprüft | 2/2 | Formel, Konsistenz |
| Bandpass 6. Ordnung parallel | `bandpass_6_parallel` | Experimentell | Formel geprüft | 2/2 | Grenzfall, Konsistenz |
| Bandpass 6. Ordnung seriell | `bandpass_6_series` | Experimentell | Formel geprüft | 2/2 | Grenzfall, Konsistenz |
| Isobarisch geschlossen | `isobaric_sealed` | Formel geprüft | Formel geprüft | 2/2 | Formel, Konsistenz |
| Compound / Push-Pull | `compound_push_pull` | Formel geprüft | Formel geprüft | 2/2 | Formel, Konsistenz |
| Isobarisch Bassreflex | `isobaric_vented` | Formel geprüft | Formel geprüft | 2/2 | Formel, Konsistenz |
| Transmission Line geschlossen | `transmission_line_closed` | Experimentell | Formel geprüft | 3/3 | Formel, Konsistenz |
| Transmission Line offen | `transmission_line_open` | Experimentell | Formel geprüft | 3/3 | Formel, Konsistenz |
| Transmission Line verjüngt | `transmission_line_tapered` | Experimentell | Formel geprüft | 2/2 | Formel, Konsistenz |
| TQWT | `tqwt` | Experimentell | Formel geprüft | 2/2 | Formel, Konsistenz |
| Labyrinth | `labyrinth` | Experimentell | Formel geprüft | 2/2 | Formel, Konsistenz |
| Mass Loaded Transmission Line | `mltl` | Experimentell | Experimentell | 1/1 | Konsistenz |
| Rearloaded Horn | `horn_rear` | Experimentell | Formel geprüft | 2/2 | Formel, Konsistenz |
| Folded Horn | `horn_folded` | Experimentell | Formel geprüft | 2/2 | Formel, Konsistenz |
| Scoop | `horn_scoop` | Experimentell | Formel geprüft | 2/2 | Formel, Konsistenz |
| Exponentialhorn | `horn_exponential` | Experimentell | Formel geprüft | 3/3 | Formel, Konsistenz |
| Tractrixhorn | `horn_tractrix` | Experimentell | Formel geprüft | 2/2 | Formel, Konsistenz |
| Konisches Horn | `horn_conical` | Experimentell | Formel geprüft | 2/2 | Formel, Konsistenz |
| Hyperbolisches Horn | `horn_hyperbolic` | Experimentell | Formel geprüft | 2/2 | Formel, Konsistenz |
| Frontlasthorn | `horn_front` | Experimentell | Formel geprüft | 2/2 | Formel, Konsistenz |
| Tapped Horn | `horn_tapped` | Experimentell | Experimentell | 1/1 | Konsistenz |
| Infinite Baffle | `infinite_baffle` | Formel geprüft | Formel geprüft | 2/2 | Grenzfall, Konsistenz |
| Open Baffle | `open_baffle` | Formel geprüft | Formel geprüft | 2/2 | Formel, Konsistenz |
| Dipol / H-Frame | `dipole` | Formel geprüft | Formel geprüft | 2/2 | Formel, Konsistenz |
| Passiv-Kardioid | `cardioid` | Experimentell | Experimentell | 1/1 | Konsistenz |

## Quellen und Grenzen je Gehäusetyp

### Geschlossen (`sealed`)

Quellen:
- Small (1972), Closed-Box Loudspeaker Systems, J. AES 20

Bekannte Grenzen:
- Aussteuerung: Linearisiertes Kleinsignalmodell: Treibernichtlinearität, Erwärmung und Kompression sind nicht enthalten.
- Abstrahlung: Halbraum-Monopol ohne Kantenbeugung, Raum und Richtwirkung.
- Verluste: Gehäuse- und Portverluste sind Standardannahmen (Q-Werte), keine Messwerte.

### Bassreflex (`bass_reflex`)

Quellen:
- Small (1973), Vented-Box Loudspeaker Systems, J. AES 21
- Thiele (1971), Loudspeakers in Vented Boxes, J. AES 19

Bekannte Grenzen:
- Aussteuerung: Linearisiertes Kleinsignalmodell: Treibernichtlinearität, Erwärmung und Kompression sind nicht enthalten.
- Abstrahlung: Halbraum-Monopol ohne Kantenbeugung, Raum und Richtwirkung.
- Verluste: Gehäuse- und Portverluste sind Standardannahmen (Q-Werte), keine Messwerte.
- Port: Portmündungskorrektur 1,46·r (Standardannahme); Portströmungsverluste und Turbulenz sind nicht modelliert.

### Aperiodisch (`aperiodic`)

Quellen:
- Small (1973), Vented-Box Loudspeaker Systems, J. AES 21

Bekannte Grenzen:
- Aussteuerung: Linearisiertes Kleinsignalmodell: Treibernichtlinearität, Erwärmung und Kompression sind nicht enthalten.
- Abstrahlung: Halbraum-Monopol ohne Kantenbeugung, Raum und Richtwirkung.
- Vent: Ventmasse wird vernachlässigt; der Widerstand folgt aus einer Auslegungsregel, nicht aus gemessenem Material.

### Passivmembran (`passive_radiator`)

Quellen:
- Olson (1951), Elements of Acoustical Engineering
- Small (1974), Passive-Radiator Loudspeaker Systems, J. AES 22

Bekannte Grenzen:
- Aussteuerung: Linearisiertes Kleinsignalmodell: Treibernichtlinearität, Erwärmung und Kompression sind nicht enthalten.
- Abstrahlung: Halbraum-Monopol ohne Kantenbeugung, Raum und Richtwirkung.
- Verluste: Gehäuse- und Portverluste sind Standardannahmen (Q-Werte), keine Messwerte.
- Membran: Die Herstellerdaten der Passivmembran (Fs, Qms, Masse) werden als gegeben angenommen.

### Bandpass 4. Ordnung (`bandpass_4`)

Quellen:
- Geddes (1989), Loudspeaker bandpass enclosures
- Small (1973), Vented-Box Loudspeaker Systems, J. AES 21

Bekannte Grenzen:
- Aussteuerung: Linearisiertes Kleinsignalmodell: Treibernichtlinearität, Erwärmung und Kompression sind nicht enthalten.
- Abstrahlung: Halbraum-Monopol ohne Kantenbeugung, Raum und Richtwirkung.
- Verluste: Verlustfrei gerechnet; Kammer- und Portverluste fehlen.

### Bandpass 6. Ordnung parallel (`bandpass_6_parallel`)

Quellen:
- Geddes (1989), Loudspeaker bandpass enclosures

Bekannte Grenzen:
- Aussteuerung: Linearisiertes Kleinsignalmodell: Treibernichtlinearität, Erwärmung und Kompression sind nicht enthalten.
- Abstrahlung: Halbraum-Monopol ohne Kantenbeugung, Raum und Richtwirkung.
- Referenz: Nur der Grenzfall mit geschlossenem Rückvent ist gegen die 4. Ordnung geprüft, nicht die Kopplung beider Ports.
- Summierung: Beide Portausgänge werden als gleicher Ort mit fester Laufzeit angenommen.

### Bandpass 6. Ordnung seriell (`bandpass_6_series`)

Quellen:
- Geddes (1989), Loudspeaker bandpass enclosures

Bekannte Grenzen:
- Aussteuerung: Linearisiertes Kleinsignalmodell: Treibernichtlinearität, Erwärmung und Kompression sind nicht enthalten.
- Abstrahlung: Halbraum-Monopol ohne Kantenbeugung, Raum und Richtwirkung.
- Referenz: Nur der Grenzfall mit geschlossenem Innenkanal ist gegen die 4. Ordnung geprüft.
- Verluste: Portverluste mit pauschalem Q = 7.

### Isobarisch geschlossen (`isobaric_sealed`)

Quellen:
- Olson (1951), Elements of Acoustical Engineering
- Small (1972), Closed-Box Loudspeaker Systems, J. AES 20

Bekannte Grenzen:
- Aussteuerung: Linearisiertes Kleinsignalmodell: Treibernichtlinearität, Erwärmung und Kompression sind nicht enthalten.
- Abstrahlung: Halbraum-Monopol ohne Kantenbeugung, Raum und Richtwirkung.
- Verluste: Gehäuse- und Portverluste sind Standardannahmen (Q-Werte), keine Messwerte.
- Koppelkammer: Die Nachgiebigkeit der Koppelkammer zwischen den Chassis wird vernachlässigt (ideales Tandem).

### Compound / Push-Pull (`compound_push_pull`)

Quellen:
- Olson (1951), Elements of Acoustical Engineering
- Small (1972), Closed-Box Loudspeaker Systems, J. AES 20

Bekannte Grenzen:
- Aussteuerung: Linearisiertes Kleinsignalmodell: Treibernichtlinearität, Erwärmung und Kompression sind nicht enthalten.
- Abstrahlung: Halbraum-Monopol ohne Kantenbeugung, Raum und Richtwirkung.
- Verluste: Gehäuse- und Portverluste sind Standardannahmen (Q-Werte), keine Messwerte.
- Koppelkammer: Die Nachgiebigkeit der Koppelkammer zwischen den Chassis wird vernachlässigt (ideales Tandem).

### Isobarisch Bassreflex (`isobaric_vented`)

Quellen:
- Olson (1951), Elements of Acoustical Engineering
- Small (1973), Vented-Box Loudspeaker Systems, J. AES 21

Bekannte Grenzen:
- Aussteuerung: Linearisiertes Kleinsignalmodell: Treibernichtlinearität, Erwärmung und Kompression sind nicht enthalten.
- Abstrahlung: Halbraum-Monopol ohne Kantenbeugung, Raum und Richtwirkung.
- Verluste: Gehäuse- und Portverluste sind Standardannahmen (Q-Werte), keine Messwerte.
- Koppelkammer: Die Nachgiebigkeit der Koppelkammer zwischen den Chassis wird vernachlässigt (ideales Tandem).

### Transmission Line geschlossen (`transmission_line_closed`)

Quellen:
- Olson (1951), Elements of Acoustical Engineering
- Beranek (1954), Acoustics
- Levine und Schwinger (1948), On the radiation of sound from an unflanged circular pipe, Phys. Rev. 73

Bekannte Grenzen:
- Aussteuerung: Linearisiertes Kleinsignalmodell: Treibernichtlinearität, Erwärmung und Kompression sind nicht enthalten.
- Abstrahlung: Halbraum-Monopol ohne Kantenbeugung, Raum und Richtwirkung.
- Wellenausbreitung: Nur ebene Wellen in segmentierten Kanälen; Querresonanzen und Biegungsverluste fehlen.
- Dämmung: Die Dämmwirkung ist ein pauschaler Dämpfungsfaktor je Zone, ohne Schallgeschwindigkeitsänderung.
- Mundlast: Strahlungsimpedanz des freien Rohrendes für kleine ka; Wandnähe und Faltung des Mundes sind nicht berücksichtigt.
- Geometrie: Der Berechnungskern ist gegen geschlossene Formeln geprüft; die Ableitung der Segmente aus dem Gehäuse (Faltung, Verjüngung) nur auf Konsistenz.

### Transmission Line offen (`transmission_line_open`)

Quellen:
- Olson (1951), Elements of Acoustical Engineering
- Beranek (1954), Acoustics
- Levine und Schwinger (1948), On the radiation of sound from an unflanged circular pipe, Phys. Rev. 73

Bekannte Grenzen:
- Aussteuerung: Linearisiertes Kleinsignalmodell: Treibernichtlinearität, Erwärmung und Kompression sind nicht enthalten.
- Abstrahlung: Halbraum-Monopol ohne Kantenbeugung, Raum und Richtwirkung.
- Wellenausbreitung: Nur ebene Wellen in segmentierten Kanälen; Querresonanzen und Biegungsverluste fehlen.
- Dämmung: Die Dämmwirkung ist ein pauschaler Dämpfungsfaktor je Zone, ohne Schallgeschwindigkeitsänderung.
- Mundlast: Strahlungsimpedanz des freien Rohrendes für kleine ka; Wandnähe und Faltung des Mundes sind nicht berücksichtigt.
- Geometrie: Der Berechnungskern ist gegen geschlossene Formeln geprüft; die Ableitung der Segmente aus dem Gehäuse (Faltung, Verjüngung) nur auf Konsistenz.

### Transmission Line verjüngt (`transmission_line_tapered`)

Quellen:
- Olson (1951), Elements of Acoustical Engineering
- Beranek (1954), Acoustics
- Levine und Schwinger (1948), On the radiation of sound from an unflanged circular pipe, Phys. Rev. 73

Bekannte Grenzen:
- Aussteuerung: Linearisiertes Kleinsignalmodell: Treibernichtlinearität, Erwärmung und Kompression sind nicht enthalten.
- Abstrahlung: Halbraum-Monopol ohne Kantenbeugung, Raum und Richtwirkung.
- Wellenausbreitung: Nur ebene Wellen in segmentierten Kanälen; Querresonanzen und Biegungsverluste fehlen.
- Dämmung: Die Dämmwirkung ist ein pauschaler Dämpfungsfaktor je Zone, ohne Schallgeschwindigkeitsänderung.
- Mundlast: Strahlungsimpedanz des freien Rohrendes für kleine ka; Wandnähe und Faltung des Mundes sind nicht berücksichtigt.
- Geometrie: Der Berechnungskern ist gegen geschlossene Formeln geprüft; die Ableitung der Segmente aus dem Gehäuse (Faltung, Verjüngung) nur auf Konsistenz.

### TQWT (`tqwt`)

Quellen:
- Olson (1951), Elements of Acoustical Engineering
- Beranek (1954), Acoustics
- Levine und Schwinger (1948), On the radiation of sound from an unflanged circular pipe, Phys. Rev. 73

Bekannte Grenzen:
- Aussteuerung: Linearisiertes Kleinsignalmodell: Treibernichtlinearität, Erwärmung und Kompression sind nicht enthalten.
- Abstrahlung: Halbraum-Monopol ohne Kantenbeugung, Raum und Richtwirkung.
- Wellenausbreitung: Nur ebene Wellen in segmentierten Kanälen; Querresonanzen und Biegungsverluste fehlen.
- Dämmung: Die Dämmwirkung ist ein pauschaler Dämpfungsfaktor je Zone, ohne Schallgeschwindigkeitsänderung.
- Mundlast: Strahlungsimpedanz des freien Rohrendes für kleine ka; Wandnähe und Faltung des Mundes sind nicht berücksichtigt.
- Geometrie: Der Berechnungskern ist gegen geschlossene Formeln geprüft; die Ableitung der Segmente aus dem Gehäuse (Faltung, Verjüngung) nur auf Konsistenz.

### Labyrinth (`labyrinth`)

Quellen:
- Olson (1951), Elements of Acoustical Engineering
- Beranek (1954), Acoustics
- Levine und Schwinger (1948), On the radiation of sound from an unflanged circular pipe, Phys. Rev. 73

Bekannte Grenzen:
- Aussteuerung: Linearisiertes Kleinsignalmodell: Treibernichtlinearität, Erwärmung und Kompression sind nicht enthalten.
- Abstrahlung: Halbraum-Monopol ohne Kantenbeugung, Raum und Richtwirkung.
- Wellenausbreitung: Nur ebene Wellen in segmentierten Kanälen; Querresonanzen und Biegungsverluste fehlen.
- Dämmung: Die Dämmwirkung ist ein pauschaler Dämpfungsfaktor je Zone, ohne Schallgeschwindigkeitsänderung.
- Mundlast: Strahlungsimpedanz des freien Rohrendes für kleine ka; Wandnähe und Faltung des Mundes sind nicht berücksichtigt.
- Geometrie: Der Berechnungskern ist gegen geschlossene Formeln geprüft; die Ableitung der Segmente aus dem Gehäuse (Faltung, Verjüngung) nur auf Konsistenz.

### Mass Loaded Transmission Line (`mltl`)

Quellen:
- Olson (1951), Elements of Acoustical Engineering
- Beranek (1954), Acoustics

Bekannte Grenzen:
- Aussteuerung: Linearisiertes Kleinsignalmodell: Treibernichtlinearität, Erwärmung und Kompression sind nicht enthalten.
- Abstrahlung: Halbraum-Monopol ohne Kantenbeugung, Raum und Richtwirkung.
- Wellenausbreitung: Nur ebene Wellen in segmentierten Kanälen; Querresonanzen und Biegungsverluste fehlen.
- Dämmung: Die Dämmwirkung ist ein pauschaler Dämpfungsfaktor je Zone, ohne Schallgeschwindigkeitsänderung.
- Mundlast: Strahlungsimpedanz des freien Rohrendes für kleine ka; Wandnähe und Faltung des Mundes sind nicht berücksichtigt.
- Geometrie: Der Berechnungskern ist gegen geschlossene Formeln geprüft; die Ableitung der Segmente aus dem Gehäuse (Faltung, Verjüngung) nur auf Konsistenz.
- Referenz: Die Portlast des Ausgangs ist nicht gegen eine geschlossene Formel geprüft.

### Rearloaded Horn (`horn_rear`)

Quellen:
- Olson (1951), Elements of Acoustical Engineering
- Beranek (1954), Acoustics
- Levine und Schwinger (1948), On the radiation of sound from an unflanged circular pipe, Phys. Rev. 73

Bekannte Grenzen:
- Aussteuerung: Linearisiertes Kleinsignalmodell: Treibernichtlinearität, Erwärmung und Kompression sind nicht enthalten.
- Abstrahlung: Halbraum-Monopol ohne Kantenbeugung, Raum und Richtwirkung.
- Wellenausbreitung: Nur ebene Wellen in segmentierten Kanälen; Querresonanzen und Biegungsverluste fehlen.
- Dämmung: Die Dämmwirkung ist ein pauschaler Dämpfungsfaktor je Zone, ohne Schallgeschwindigkeitsänderung.
- Mundlast: Strahlungsimpedanz des freien Rohrendes für kleine ka; Wandnähe und Faltung des Mundes sind nicht berücksichtigt.
- Geometrie: Der Berechnungskern ist gegen geschlossene Formeln geprüft; die Ableitung der Segmente aus dem Gehäuse (Faltung, Verjüngung) nur auf Konsistenz.
- Hornkontur: Die Kontur wird durch Abschnitte angenähert; der Kern ist gegen die Olson-Halsimpedanz geprüft.

### Folded Horn (`horn_folded`)

Quellen:
- Olson (1951), Elements of Acoustical Engineering
- Beranek (1954), Acoustics
- Levine und Schwinger (1948), On the radiation of sound from an unflanged circular pipe, Phys. Rev. 73

Bekannte Grenzen:
- Aussteuerung: Linearisiertes Kleinsignalmodell: Treibernichtlinearität, Erwärmung und Kompression sind nicht enthalten.
- Abstrahlung: Halbraum-Monopol ohne Kantenbeugung, Raum und Richtwirkung.
- Wellenausbreitung: Nur ebene Wellen in segmentierten Kanälen; Querresonanzen und Biegungsverluste fehlen.
- Dämmung: Die Dämmwirkung ist ein pauschaler Dämpfungsfaktor je Zone, ohne Schallgeschwindigkeitsänderung.
- Mundlast: Strahlungsimpedanz des freien Rohrendes für kleine ka; Wandnähe und Faltung des Mundes sind nicht berücksichtigt.
- Geometrie: Der Berechnungskern ist gegen geschlossene Formeln geprüft; die Ableitung der Segmente aus dem Gehäuse (Faltung, Verjüngung) nur auf Konsistenz.
- Hornkontur: Die Kontur wird durch Abschnitte angenähert; der Kern ist gegen die Olson-Halsimpedanz geprüft.

### Scoop (`horn_scoop`)

Quellen:
- Olson (1951), Elements of Acoustical Engineering
- Beranek (1954), Acoustics
- Levine und Schwinger (1948), On the radiation of sound from an unflanged circular pipe, Phys. Rev. 73

Bekannte Grenzen:
- Aussteuerung: Linearisiertes Kleinsignalmodell: Treibernichtlinearität, Erwärmung und Kompression sind nicht enthalten.
- Abstrahlung: Halbraum-Monopol ohne Kantenbeugung, Raum und Richtwirkung.
- Wellenausbreitung: Nur ebene Wellen in segmentierten Kanälen; Querresonanzen und Biegungsverluste fehlen.
- Dämmung: Die Dämmwirkung ist ein pauschaler Dämpfungsfaktor je Zone, ohne Schallgeschwindigkeitsänderung.
- Mundlast: Strahlungsimpedanz des freien Rohrendes für kleine ka; Wandnähe und Faltung des Mundes sind nicht berücksichtigt.
- Geometrie: Der Berechnungskern ist gegen geschlossene Formeln geprüft; die Ableitung der Segmente aus dem Gehäuse (Faltung, Verjüngung) nur auf Konsistenz.
- Hornkontur: Die Kontur wird durch Abschnitte angenähert; der Kern ist gegen die Olson-Halsimpedanz geprüft.

### Exponentialhorn (`horn_exponential`)

Quellen:
- Olson (1951), Elements of Acoustical Engineering
- Beranek (1954), Acoustics
- Levine und Schwinger (1948), On the radiation of sound from an unflanged circular pipe, Phys. Rev. 73

Bekannte Grenzen:
- Aussteuerung: Linearisiertes Kleinsignalmodell: Treibernichtlinearität, Erwärmung und Kompression sind nicht enthalten.
- Abstrahlung: Halbraum-Monopol ohne Kantenbeugung, Raum und Richtwirkung.
- Wellenausbreitung: Nur ebene Wellen in segmentierten Kanälen; Querresonanzen und Biegungsverluste fehlen.
- Dämmung: Die Dämmwirkung ist ein pauschaler Dämpfungsfaktor je Zone, ohne Schallgeschwindigkeitsänderung.
- Mundlast: Strahlungsimpedanz des freien Rohrendes für kleine ka; Wandnähe und Faltung des Mundes sind nicht berücksichtigt.
- Geometrie: Der Berechnungskern ist gegen geschlossene Formeln geprüft; die Ableitung der Segmente aus dem Gehäuse (Faltung, Verjüngung) nur auf Konsistenz.
- Hornkontur: Die Kontur wird durch Abschnitte angenähert; der Kern ist gegen die Olson-Halsimpedanz geprüft.

### Tractrixhorn (`horn_tractrix`)

Quellen:
- Olson (1951), Elements of Acoustical Engineering
- Beranek (1954), Acoustics
- Levine und Schwinger (1948), On the radiation of sound from an unflanged circular pipe, Phys. Rev. 73

Bekannte Grenzen:
- Aussteuerung: Linearisiertes Kleinsignalmodell: Treibernichtlinearität, Erwärmung und Kompression sind nicht enthalten.
- Abstrahlung: Halbraum-Monopol ohne Kantenbeugung, Raum und Richtwirkung.
- Wellenausbreitung: Nur ebene Wellen in segmentierten Kanälen; Querresonanzen und Biegungsverluste fehlen.
- Dämmung: Die Dämmwirkung ist ein pauschaler Dämpfungsfaktor je Zone, ohne Schallgeschwindigkeitsänderung.
- Mundlast: Strahlungsimpedanz des freien Rohrendes für kleine ka; Wandnähe und Faltung des Mundes sind nicht berücksichtigt.
- Geometrie: Der Berechnungskern ist gegen geschlossene Formeln geprüft; die Ableitung der Segmente aus dem Gehäuse (Faltung, Verjüngung) nur auf Konsistenz.
- Hornkontur: Die Kontur wird durch Abschnitte angenähert; der Kern ist gegen die Olson-Halsimpedanz geprüft.

### Konisches Horn (`horn_conical`)

Quellen:
- Olson (1951), Elements of Acoustical Engineering
- Beranek (1954), Acoustics
- Levine und Schwinger (1948), On the radiation of sound from an unflanged circular pipe, Phys. Rev. 73

Bekannte Grenzen:
- Aussteuerung: Linearisiertes Kleinsignalmodell: Treibernichtlinearität, Erwärmung und Kompression sind nicht enthalten.
- Abstrahlung: Halbraum-Monopol ohne Kantenbeugung, Raum und Richtwirkung.
- Wellenausbreitung: Nur ebene Wellen in segmentierten Kanälen; Querresonanzen und Biegungsverluste fehlen.
- Dämmung: Die Dämmwirkung ist ein pauschaler Dämpfungsfaktor je Zone, ohne Schallgeschwindigkeitsänderung.
- Mundlast: Strahlungsimpedanz des freien Rohrendes für kleine ka; Wandnähe und Faltung des Mundes sind nicht berücksichtigt.
- Geometrie: Der Berechnungskern ist gegen geschlossene Formeln geprüft; die Ableitung der Segmente aus dem Gehäuse (Faltung, Verjüngung) nur auf Konsistenz.
- Hornkontur: Die Kontur wird durch Abschnitte angenähert; der Kern ist gegen die Olson-Halsimpedanz geprüft.

### Hyperbolisches Horn (`horn_hyperbolic`)

Quellen:
- Olson (1951), Elements of Acoustical Engineering
- Beranek (1954), Acoustics
- Levine und Schwinger (1948), On the radiation of sound from an unflanged circular pipe, Phys. Rev. 73

Bekannte Grenzen:
- Aussteuerung: Linearisiertes Kleinsignalmodell: Treibernichtlinearität, Erwärmung und Kompression sind nicht enthalten.
- Abstrahlung: Halbraum-Monopol ohne Kantenbeugung, Raum und Richtwirkung.
- Wellenausbreitung: Nur ebene Wellen in segmentierten Kanälen; Querresonanzen und Biegungsverluste fehlen.
- Dämmung: Die Dämmwirkung ist ein pauschaler Dämpfungsfaktor je Zone, ohne Schallgeschwindigkeitsänderung.
- Mundlast: Strahlungsimpedanz des freien Rohrendes für kleine ka; Wandnähe und Faltung des Mundes sind nicht berücksichtigt.
- Geometrie: Der Berechnungskern ist gegen geschlossene Formeln geprüft; die Ableitung der Segmente aus dem Gehäuse (Faltung, Verjüngung) nur auf Konsistenz.
- Hornkontur: Die Kontur wird durch Abschnitte angenähert; der Kern ist gegen die Olson-Halsimpedanz geprüft.

### Frontlasthorn (`horn_front`)

Quellen:
- Olson (1951), Elements of Acoustical Engineering
- Levine und Schwinger (1948), On the radiation of sound from an unflanged circular pipe, Phys. Rev. 73

Bekannte Grenzen:
- Aussteuerung: Linearisiertes Kleinsignalmodell: Treibernichtlinearität, Erwärmung und Kompression sind nicht enthalten.
- Abstrahlung: Halbraum-Monopol ohne Kantenbeugung, Raum und Richtwirkung.
- Wellenausbreitung: Ebene Wellen; Halsübergang und Richtwirkung des Horns fehlen.
- Mundlast: Freies Rohrende; ein Horn vor einer Wand oder in einer Ecke hat eine andere Mundlast.

### Tapped Horn (`horn_tapped`)

Quellen:
- Olson (1951), Elements of Acoustical Engineering

Bekannte Grenzen:
- Aussteuerung: Linearisiertes Kleinsignalmodell: Treibernichtlinearität, Erwärmung und Kompression sind nicht enthalten.
- Abstrahlung: Halbraum-Monopol ohne Kantenbeugung, Raum und Richtwirkung.
- Referenz: Es gibt keinen unabhängigen Referenzfall; das Netzmodell ist nur auf Konsistenz geprüft.
- Verluste: Pauschaler Dämpfungsfaktor 0,025 im Kanal.

### Infinite Baffle (`infinite_baffle`)

Quellen:
- Small (1972), Closed-Box Loudspeaker Systems, J. AES 20

Bekannte Grenzen:
- Aussteuerung: Linearisiertes Kleinsignalmodell: Treibernichtlinearität, Erwärmung und Kompression sind nicht enthalten.
- Abstrahlung: Halbraum-Monopol ohne Kantenbeugung, Raum und Richtwirkung.
- Rückraum: Der Rückraum wird als dichte, reine Nachgiebigkeit angenommen (mindestens 10·Vas).

### Open Baffle (`open_baffle`)

Quellen:
- Olson (1951), Elements of Acoustical Engineering

Bekannte Grenzen:
- Aussteuerung: Linearisiertes Kleinsignalmodell: Treibernichtlinearität, Erwärmung und Kompression sind nicht enthalten.
- Beugung: Weg um die Kante als einzelner Weglängenunterschied; Kantenbeugung, Richtwirkung und Raum fehlen.

### Dipol / H-Frame (`dipole`)

Quellen:
- Olson (1951), Elements of Acoustical Engineering
- Linkwitz, Dipole Loudspeakers

Bekannte Grenzen:
- Aussteuerung: Linearisiertes Kleinsignalmodell: Treibernichtlinearität, Erwärmung und Kompression sind nicht enthalten.
- Beugung: Nur der kürzeste Weg um die Kanten; Flügelresonanzen fehlen.

### Passiv-Kardioid (`cardioid`)

Quellen:
- Olson (1951), Elements of Acoustical Engineering

Bekannte Grenzen:
- Aussteuerung: Linearisiertes Kleinsignalmodell: Treibernichtlinearität, Erwärmung und Kompression sind nicht enthalten.
- Abstrahlung: Halbraum-Monopol ohne Kantenbeugung, Raum und Richtwirkung.
- Referenz: Kein unabhängiger Referenzfall; das Zweiquellenmodell ist nur auf Konsistenz geprüft.
- Richtwirkung: Nur Vorne/Hinten, nicht das volle Polardiagramm.

## Beförderungsregeln

- **Experimentell → Formel geprüft:** Mindestens ein ANALYTIC- oder LIMIT-Fall besteht, dessen Erwartung in `independent.py` ohne Aufruf des geprüften Solvers berechnet wird; die Näherungen des Modells sind als Grenzen dokumentiert und für die Nutzer:innen unerheblich oder begrenzt.
- **Formel geprüft → Referenz geprüft:** Mindestens ein LITERATURE-Fall mit Quelle, Zahlenwert und begründeter Toleranz besteht.
- **Referenz geprüft → Am Prototyp validiert:** Ein gespeicherter Messdatensatz eines gebauten Prototyps (Fall der Art PROTOTYPE) stimmt innerhalb der dokumentierten Toleranz überein. Übereinstimmung mit Literatur genügt dafür nie.
- **Zurückstufung:** Besteht ein Fall nicht mehr, gilt sofort die belegte Stufe; ein Referenzstand wird nur mit Begründung und Namen erneuert (`--accept-baseline`).
