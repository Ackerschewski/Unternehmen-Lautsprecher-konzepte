# Wartung / technische Annahmen V-01.01.00

## Automatischer Entwurf

`services/automatic.py` erzeugt Kandidaten aus validierten Bibliotheksdaten. Er prüft Treiberdurchmesser, Einbautiefe, Frequenzüberlappung, Impedanz, Nettovolumen, Außenmaße, Port-/Frontkollisionen, Xmax und Portgeschwindigkeit vor der Rangfolge. Explizites Budget erfordert Preisfelder; fehlende Preise führen zu keiner erfundenen Schätzung. Ein explizites SPL-Ziel wird nur gegen die grobe thermische Obergrenze `Empfindlichkeit + 10 log10(Pe/1 W)` vorgeprüft; diese Formel ist **kein** verlässlicher Max-SPL-Nachweis und die UI zeigt deshalb keinen gesicherten Max-SPL-Wert.

`optimization/profiles.py` enthält die Gewichte. Einzelwerte werden auf 0–100 begrenzt: Tiefbass `100 min(1, Ziel-F3/F3)`, Kompaktheit `100(1 - Außenvolumen/max. Bauraumvolumen)`, Auslenkungsreserve `100(1 - X/Xmax)`, Portreserve `100(1 - v/17 m/s)`, Gruppenlaufzeit `100(1 - GD/50 ms)` und Pegelspanne `100(1 - Spanne/12 dB)`. Kosten werden nur mit Preis und Budget gewertet. Die Gesamtzahl ist der gewichtete Mittelwert der **verfügbaren** Kriterien. Fehlende Werte bleiben unbekannt; Scores mit unterschiedlicher Datenlage sind nur eingeschränkt vergleichbar. Alle Einzelwerte und Grundlagen werden in der Oberfläche gezeigt.

Der passive automatische Weichenentwurf verwendet eine elektrische Butterworth-2-Grundschaltung, Nennimpedanzen, optional ein L-Pad aus vorhandenen Empfindlichkeitswerten und einen Zobel bei vorhandenen Re/Le. `crossover/standards.py` rundet auf E12; Soll- und gewählter Wert werden gespeichert. Das ersetzt keine Messung der akustischen Summenkurve.

## Einheiten und Datenfluss

Alle Kernmodelle verwenden SI. UI und CSV zeigen mm, Liter, cm², m/s, Hz. `SpeakerProject` ist die persistente Quelle für Treiber, Gehäuse, Weiche und Frontlayout. `calculate_project()` liefert aufgelöste Geometrie und `DesignWarning`-Objekte. Zeichnung, DXF, PDF und Stückliste verwenden dieselben `FrontElement`-Objekte. Der Portquerschnitt und die Länge kommen aus `PortDesign`; bei Berechnung wird das Port-Frontobjekt damit synchronisiert.

## Geschlossen

`alpha = (Qtc/Qts)^2 - 1`, `Vb = Vas/alpha`, `Fc = Fs Qtc/Qts`. Der normierte Hochpass wird aus der linearen Übertragungsfunktion zweiter Ordnung berechnet.

## Bassreflex Kleinsignalmodell

Siehe [Small, Vented-Box Loudspeaker Systems Part 1 (AES, 1973)](https://aes.org/publications/elibrary-page/?id=1967) und [Thiele, Loudspeakers in Vented Boxes Part 1 (AES, 1971)](https://aes.org/publications/elibrary-page/?id=2173) als Grundlage der linearen ventilierten Gehäuseanalyse. Die hier implementierte Darstellung ist ein direkter, konzentrierter Impedanzkreis:

- `Cms = Vas/(rho c² Sd²)`; `Mms = 1/((2πFs)² Cms)`; `Rms = 2πFs Mms/Qms`.
- `Bl²/Re = 2πFs Mms/Qes`; fehlendes Qms wird nur aus konsistentem Qts/Qes abgeleitet.
- `Cb = Vb/(rho c²)`; `Mp = rho Leff/Aport`; `Zport = Rp + jωMp` mit `Rp = 2πFb Mp/Qp`, falls Qp angegeben ist.
- `Zbox = 1/(jωCb + 1/Zport + 2πFb Cb/Ql + 2πFb Cb/Qa)`. Fehlende Verlust-Q bedeuten verlustfreies Ersatzglied.
- `Zmech = Rms + jωMms + 1/(jωCms) + Sd² Zbox`.
- `Zelec = Re + jωLe + Bl²/Zmech`; `I = sqrt(P Re)/Zelec`; `v = Bl I/Zmech`.
- `Ufront = Sd v`; `Uport = -Ufront Zbox/Zport`; `p(1 m) = jω rho (Ufront+Uport)/(2π)` als Halbraum-Monopol.
- `X = |v/(jω)|`; Portgeschwindigkeit `|Uport|/A`; Gruppenlaufzeit `-d phase(p)/dω`.

Die Leistung P ist eine **äquivalente RMS-Spannung `sqrt(P Re)`**, keine über Frequenz konstant gehaltene tatsächlich aufgenommene elektrische Leistung. Der Pegel ist auf den Median 150–300 Hz normiert; F3 ist der erste -3-dB-Durchgang dieser Referenz. SPL 1 m ist nur die ideale Halbraum-Monopolschätzung und setzt vollständige Re/Qes/Sd-Daten voraus. Ql/Qa/Qp sind optional. Luftwerte sind standardmäßig rho=1,204 kg/m³ und c=343 m/s. Das Modell umfasst keine Portkompression, Strömungsabrisse, thermische und mechanische Nichtlinearität, Baffle Step, Raum, Richtwirkung oder akustische Laufzeit zwischen Treibern. Die Testreferenz `test_vented_numerical_reference_and_power_scaling` verwendet die dokumentierten Demo-Eingaben; 10 W ergeben F3 ≈32,318 Hz, max. 7,848 m/s und 5,470 mm. Diese Zahlen sind Modellregressionen, keine Messvalidierung.

## Portlänge und Warnungen

`bass_reflex.py` und `enclosure/ports.py` nutzen die Helmholtzbeziehung `Leff = c² A/((2πFb)² Vb)`; der physikalische Rundport zieht 1,46 Radien als angenommene Endkorrektur ab. Einbau, Flansche und angrenzende Wände können diese Korrektur ändern. Slot-Port nutzt einen äquivalenten Radius. `acoustics/limits.py` enthält anpassbare Portgeschwindigkeits-Richtwerte 17 und 25 m/s. Xmax und Pe stammen ausschließlich aus den Treiberdaten. Eine Überschreitung ist ein Hinweis für Konstruktion und Test, kein Sicherheitszertifikat.

Ein Slot-Port wird als freistehender rechteckiger Kanal mit vier Wänden in Basisstärke modelliert. Die zwei Deckel/Boden- und zwei Seitenplatten stehen im Zuschnitt; ihre Verdrängung erhöht die benötigte Außentiefe. Der Seitenschnitt zeigt obere und untere Kanalwand. Gemeinsame Gehäusewände als Kanalwand werden noch nicht als Materialeinsparung berücksichtigt.

## Passivmembran und Bandpass

Die Passivmembran wird als akustisches Serienglied `Zpr = Rpr + jω Mpr + 1/(jω Cpr)` parallel zur Gehäuse-Luftfeder betrachtet. Aus den gemessenen Werten `Sdpr`, `Mms`, `Fs` und `Qms` folgen `Mpr,0=Mms/Sdpr²`, `Cpr=1/((2πFs)² Mpr,0)` und `Rpr=2πFs Mpr,0/Qms`. Für die gewünschte Fb wird `Mpr=(1/Cb+1/Cpr)/(2πFb)²` berechnet; die Zusatzmasse ist `(Mpr-Mpr,0)Sdpr²`. Negative Zusatzmasse wird abgelehnt. Das Gehäuse benutzt die gleiche gekoppelte Treiber-/Resonatorlösung wie Bassreflex, jedoch mit der Feder der Passivmembran im Resonator. Die errechnete Zusatzmasse muss anhand der tatsächlichen Impedanzkurve überprüft werden.

Der einfach abgestimmte Bandpass hat zwei Luftfedern `Cf=Vfront/(rho c²)` und `Cr=Vrear/(rho c²)`. Der Treiber sieht `Sd²(Zfront+Zrear)`, mit `Zfront=1/(jωCf+1/Zport)` und `Zrear=1/(jωCr)`; nach außen strahlt im Modell nur der Frontport. Die Kurve wird auf den höchsten Pegel normiert, beide -3-dB-Punkte werden interpoliert. Die Trennwandverdrängung geht in die Außentiefe ein, die Frontkammer erhält Portverdrängung, die Rückkammer Treiber-, Streben- und Zusatzverdrängung. Reale Kammerverluste, Port-/Hohlraumresonanzen, Undichtigkeiten und Trennwandflexibilität fehlen.

## Frequenzweiche und Messdaten

`crossover/simulation.py` löst Serien- und Parallelzweige als komplexe RLC-Impedanzen mit gemessenem ZMA oder Nennwiderstand. ZMA-Magnitude/Phase und FRD-Pegel/Phase werden logarithmisch in der Frequenz interpoliert; außerhalb der Messspanne wird kein Wert vorgetäuscht. Eine akustische Summe gibt es nur mit Woofer- und Tweeter-FRD. Fehlt Phase, wird die Summe von Beträgen statt kohärenter komplexer Addition gezeigt und markiert. Der Datensatz muss dieselbe Messreferenz besitzen. Schallwand, Schallzentren und Polarverhalten werden nicht optimiert. Die passive Weiche ist ein Startentwurf.

## Gehäuse und Fertigung

`rectangular.py` modelliert eine rechtwinklige stumpf gestoßene Konstruktion: Front/Rückwand decken die Außenfläche, Seiten stehen zwischen ihnen, Deckel/Boden zwischen Seiten. Seiten verwenden die Basisstärke; Frontlagen, Rückwand, Deckel und Boden können eigene Stärken haben. Bei Bandpass wird eine zusätzliche Trennwand zwischen den Kammern angesetzt. Die Fensterstreben sind vereinfachte Platten mit rechteckigem Fenster. SVG und PDF zeigen einen schematischen Seitenschnitt; Front-, Rück- und Trennwand-DXF trennen die Montageflächen. Kollisionen sind 2D-Kreis/Rechteck- und einfache Tiefenprüfungen, keine 3D-CAD-Analyse. PDF/DXF/SVG sind vor Fertigung gegen reale Bauteile zu prüfen.

## Prüfungen

`.venv\\Scripts\\python -m pytest` und `-m ruff check src tests`. Die EXE wird lokal mit PyInstaller gebaut. Der offscreen-QT-Test prüft Fensterausbau und den Demo-Workflow; ein interaktiver Sichttest auf dem Zielrechner bleibt sinnvoll.
