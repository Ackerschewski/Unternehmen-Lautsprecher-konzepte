# Gehäusemodelle V-02.05.00

## Status

Der Typenkatalog umfasst 29 berechenbare Bauformen. „Berechenbar“ bedeutet, dass Entwurf, akustische Vorschau, Innengeometrie und Export denselben Parameterstand verwenden. Es bedeutet keine gemessene Übereinstimmung am fertigen Lautsprecher. Die folgenden Familien teilen sich jeweils ein physikalisches Grundmodell:

| Familie | Typen | Modell und Geometrie |
|---|---|---|
| Geschlossen, Bassreflex, Aperiodisch, Passivmembran | 4 | Lumped-Parameter-Treiber, Gehäusenachgiebigkeit und Resonator; Aperiodik mit endlichem Strömungswiderstand |
| Bandpass | 3 | Getrennte Kammern; vierter Ordnung, sechster Ordnung parallel und seriell mit externem und internem Port |
| Isobarik | 3 | Ideales Treiberpaar, Koppelring und geschlossenes oder ventiliertes Gehäuse; Push-Pull als mechanisch umgekehrtes Paar |
| Gefaltete Linien | 6 | Zwei bis zehn rechteckige Kanäle mit expliziten Faltplatten, Viertelwellenweg und Transfermatrix |
| Rückwärtige Hörner | 7 | Rechteckige Stufen mit verschiedenen Expansionsfunktionen; Transfermatrix wie gefaltete Linie |
| Offene Schallwand und Kardioid | 4 | Endliche Schallwand, U-Frame bzw. großer dichter Rückraum; passiver Kardioid als verzögertes Zweiquellenmodell |
| Front-Horn | 1 | Exponentieller Hals-Mund-Übergang mit 24 Segmenten und geschlossener Rückkammer |
| Tapped-Horn | 1 | Zwei gekoppelte Hornwege; Membranvorder- und Rückseite speisen an verschiedenen Kanalstellen ein |

## Front-Horn

Der Treiber sitzt mittig in der Frontwand eines geschlossenen Rückgehäuses. Der Hals ist quadratisch und größer als der Chassis-Außendurchmesser zuzüglich Platten und Montageabstand. Die Mündung entspricht den angegebenen Gehäuse-Außenmaßen. Aus der Ziel-Grenzfrequenz wird die axiale Länge mit `L = c ln(Sm/St)/(2π fc)` bestimmt. Vier Trapezplatten verbinden Hals und Mund; die DXF-Dateien enthalten die Zuschnittkontur. Die akustische Vorschau kaskadiert 24 ebene Wellensegmente mit frequenzabhängiger Mündungsimpedanz. Sie enthält keine vollständige Richtwirkung, Beugung, Kompression oder exakte Gehrungskonstruktion.

## Tapped-Horn

F1 ist eine horizontale Platte mit rundem Treiberausschnitt. Der Magnet sitzt im oberen Kanal, die Membran strahlt in den unteren. Ein Spalt am hinteren Ende verbindet beide Kanäle; die Mündung liegt vorn im unteren Kanal. F1 ist kürzer als die innere Gehäusetiefe um genau diesen Umlenkspalt. Die Geometrie prüft Treiber-Außendurchmesser, Einbautiefe, Randabstand und bekannten Lochkreis. Die Volumenbilanz zieht den F1-Ausschnitt von der Plattenverdrängung ab. Der akustische Solver bildet sechs Druckknoten mit Rohrsegment-Admittanzen, einer Mündungslast und zwei gegenläufigen Volumenstrom-Einspeisungen an den Membranseiten. Die Differenz der beiden Knotendrücke belastet den Treiber. Die elektrischen Größen folgen dem T/S-Kleinsignalmodell. Faltungsverluste werden angenähert; Strömungsablösung, höhere Moden, genaue Mundbeugung und Chassis-Asymmetrie fehlen.

## Fertigung und Grenzen

SVG und PDF benennen Außen- und Innenmaße, F1 bzw. Trapez-Zuschnitte, Hals/Mündung, Treiberkoordinaten und veröffentlichte Bohrbilder. DXF enthält nur Bohrungen mit bekanntem Durchmesser. Zuschnitte sind Rohplattenkonturen; Stöße, Gehrungswinkel, Fräserzugabe, Schraubenfreiheit und Dichtungen sind am Prototyp festzulegen. Schwerwiegende erkannte Geometriefehler sperren den Export. Eine vollständige 3D-Kollisionsprüfung ist nicht vorhanden.

Die Linien- und Hornmodelle nutzen ebene Wellen und lineare Kleinsignale. Bei realen Chassis können Gehäuseverluste, Dämmung, Leckage und Raumantwort die Simulation deutlich ändern. Vor Zuschnitt T/S- und Montageangaben am Datenblatt und am Original prüfen; nach Bau Impedanz, Nahfeld und Pegel messen.

## Referenzen

- MathWorks, [Loudspeaker enclosure examples](https://www.mathworks.com/help/audio/ug/simulate-loudspeaker-types-in-simscape.html): lumped enclosure equivalents.
- Martin J. King, [Transmission Line Anatomy](https://www.quarter-wave.com/TLs/TL_Anatomy.pdf): quarter-wave line behaviour and loss considerations.
- University of Illinois, [Webster horn equation study](https://www.ideals.illinois.edu/items/105435/bitstreams/333785/data.pdf): plane-wave horn modelling context.
