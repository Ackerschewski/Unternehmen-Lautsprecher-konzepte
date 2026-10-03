# Bandpass 6. Ordnung parallel — Modell und Fertigung

## Topologie

Der Tieftöner sitzt in einer Trennwand zwischen zwei Kammern. BR1 verbindet die Frontkammer mit außen, BR2 die Rückkammer mit außen. Beide Ports sind außenliegende Auslässe; dies ist die parallele Variante. Die serielle Variante mit internem Verbindungskanal bleibt in Entwicklung.

## Kleinsignalmodell

Für die Kreisfrequenz ω und `s = jω` gelten die akustischen Nachgiebigkeiten `Cf = Vf/(ρc²)` und `Cr = Vr/(ρc²)`. Die Portimpedanzen sind `Zpf = sρLef/Sf` und `Zpr = sρLer/Sr`. Die Kammerimpedanzen sind `Zf = 1/(sCf + 1/Zpf)` und `Zr = 1/(sCr + 1/Zpr)`. Der Treiber wird über `Zm + Sd²(Zf + Zr)` belastet; bei vorhandenen Sd, Re und Qes wird die elektrische Ankopplung über Bl und Schwingspulenimpedanz berechnet. Die Volumenströme der beiden Portauslässe werden mit entgegengesetztem Vorzeichen kohärent summiert. Der Frequenzgang ist auf sein Maximum normiert. Für den Entwurf werden keine nicht vorhandenen Herstellerdaten ergänzt.

BR1 und BR2 haben eigene Abstimmfrequenz, Querschnitt und physische Länge. BR2 ist in dieser Version ein gerader Rundport an der Rückwand. Beide Portvolumina und die Trennwand gehen in die Gehäusetiefe ein. Front- und Rückkammer werden separat auf die Portlänge geprüft. Die Stückliste, Koordinaten, Rückwand-DXF und Fertigungsblätter übernehmen die berechneten Maße.

## Annahmen und Grenzen

- Punktförmig zusammengefasste Auslässe im Halbraum. Der tatsächliche Abstand zwischen Front- und Rückwandauslass und die richtungsabhängige Interferenz fehlen.
- Keine Leckage, Portreibung, Portkompression, Kanal-/Kammermoden, Temperaturdrift oder thermische Nichtlinearität.
- Die berechnete Portgeschwindigkeit ist eine Idealabschätzung. Ein Überschreiten der Grenze erscheint als Warnung.
- Geometrieprüfungen decken Wandtiefe, Flächenkollisionen und Kammerlänge ab; vollständige 3D-Kollisionen, Faltungen und Montagefreiräume sind nicht modelliert.
- Vor Fertigung den Port mit Originalkomponenten und Impedanzmessung abstimmen; danach Nahfeldmessung beider Auslässe und Gesamtfrequenzgang prüfen.

Die Topologie entspricht der von MathWorks beschriebenen „6th order parallel bandpass enclosure with two external ports“: https://www.mathworks.com/help/audio/ug/simulate-loudspeaker-types-in-simscape.html . Das vereinfachte Impedanznetz ist im Quellcode `acoustics/bandpass.py` implementiert; es ist kein Ersatz für eine gemessene Systemantwort.
