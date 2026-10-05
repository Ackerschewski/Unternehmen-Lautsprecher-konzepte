# Nutzerhandbuch — V-02.06.00

## Neu in V-02.06.00

### Zuschnitt, Gewicht und Bauanleitung

Der Reiter **Zuschnitt** zeigt, wie alle Teile auf Handelsplatten verteilt werden. Plattenmaß und Sägeschnitt sind einstellbar und werden gespeichert;
„Standardplatte des Materials“ nutzt 2 500 × 1 250 mm (Birke Multiplex) bzw. 2 440 × 1 220 mm (MDF, Spanplatte). Teile mit verschiedenen Plattendicken
werden getrennt geplant. Teile, die auf keine Platte passen, werden ausdrücklich gemeldet. Trapez- und Rundteile sind als umschreibendes Rechteck geplant.
Das Gewicht ist ein Bereich nur für das Plattenmaterial; Chassis, Weiche und Dämmung sind nicht enthalten.

Der Export enthält im Ordner `fertigung`: `zuschnittplan.pdf`, `zuschnittplan.csv`, `zuschnittplan/platte_*.svg`, `bauanleitung.pdf` und `bauanleitung.md`.
Die Bauanleitung folgt der berechneten Konstruktion (Trennwand, Isobarik-Kammer, Horn, Faltung, Port, Passivmembran) und nennt Kontrollschritte.

### Prototyp vergleichen

Nach dem Bau Impedanz (ZMA) und Frequenzgang (FRD) messen (siehe `MESSPROTOKOLL.md`), dann **Werkzeuge → Prototyp vergleichen** (Assistent) bzw.
**Prototyp vergleichen…** (Expertenmodus). Der Bericht zeigt RMS-/Maximalabweichung, F3, die Abstimmfrequenz aus dem Impedanzminimum und bei Bassreflex einen
Vorschlag zur Portlänge. Der Vorschlag setzt voraus, dass der Port wie geplant gebaut wurde; in kleinen Schritten korrigieren und neu messen.

### Schallwandkorrektur

Im Expertenmodus unter **Frequenzweiche → Schallwandkorrektur** (0 = aus, bis 6 dB). Es entstehen Spule `Lbs` und Widerstand `Rbs` im Tieftonzweig.
Der Übergang liegt bei etwa 115 Hz·m / Schallwandbreite. Die Näherung ist nicht an Messungen validiert; bei Subwoofern ist sie nicht sinnvoll.

### Komfort

- **Datei → Zuletzt geöffnet**, `Strg+O` laden, `Strg+S` speichern, `Strg+E` exportieren, `Strg+Q` beenden, `F1` Hilfe.
- Bei ungespeicherten Änderungen fragt das Programm vor dem Schließen und vor dem Laden eines anderen Projekts.
- Alle 60 Sekunden wird ein ungespeicherter Entwurf gesichert; nach einem Absturz bietet das Programm beim Start die Wiederherstellung an.
- Das Programmprotokoll liegt unter `%LOCALAPPDATA%\LautsprecherKonstruktion\logs`; **Hilfe → Protokollordner öffnen**. Bei Fehlermeldungen die Datei beilegen.

## Gehäusetypen in V-02.05.00

Im Expertenmodus sind alle 29 aufgeführten Gehäusetypen berechenbar. Bei Front-Horn braucht W1 eine mittige Frontposition ohne weitere Frontchassis. Das Horn sitzt vor einer geschlossenen Rückkammer. Der Zielwert „Abstimmung“ ist hier die Horn-Grenzfrequenz; Qtc bestimmt die Rückkammer. Bei Tapped-Horn wird W1 auf F1 im Innenraum montiert. Die Front zeigt nur die Mündung BR1. Zielvolumen, Breite und Höhe müssen genügend Tiefe für den Treiber auf F1 und Platz für beide Kanalwege ergeben. Der Grenzwert „Abstimmung“ dient als Ziel für die Viertelwellenlänge; die tatsächlich erreichte Frequenz steht im Ergebnis.

Beide Hornarten besitzen eine eigene Gesamtzeichnung und ein PDF-Fertigungsblatt. Das Front-Horn exportiert zwei Trapez-DXF-Profile; das Tapped-Horn exportiert `tapped_horn_f1.dxf` mit Treiberöffnung und nur dann Schraublöchern, wenn Lochkreis und Bohrdurchmesser bekannt sind. Der Assistent wählt Hornarten für einen einzelnen Tieftöner und nur bei ausreichenden Außenmaßen. Messung von Impedanz und Nahfeld am Prototyp bleibt erforderlich. Die Modellannahmen und geometrischen Grenzen stehen in `docs/ENCLOSURE_MODELS_V205.md`.

## Neue Budget- und Bohrdatenprüfung

Bei Zweiwege-Entwürfen prüft die Automatik mehrere technisch passende Hochtöner. Der Variantenvergleich zeigt die gewählte Chassis-Kombination und bei gesetztem Gesamtbudget den verbleibenden Betrag nach allen kalkulierten Materialien und 15 % Reserve. Preise sind datierte Momentaufnahmen beziehungsweise gekennzeichnete Planwerte.

Ein Hersteller-Lochkreis allein genügt nicht für eine Bohrung: Fehlt der Bohrdurchmesser, enthalten SVG, PDF und DXF keine aus einem Standardwert abgeleiteten Schraublöcher. Das Gesamtblatt weist dann „Bohr-Ø fehlt“ aus. Im Expertenmodus kann ein gemessener Durchmesser eingetragen werden; 0 mm bedeutet unbekannt.

## Gesamtbudget und Fertigungszeichnung

Im ersten Schritt kann unter „Gesamtbudget bis“ ein Euro-Betrag für **einen Lautsprecher** eingegeben werden. 0 € bedeutet ohne Budgetgrenze. Der Assistent berücksichtigt alle kalkulierten Positionen der Stückliste und 15 % Materialreserve. Steht für ein ausgewähltes Chassis kein Euro-Preis zur Verfügung, wird es bei gesetztem Budget nicht als passend bestätigt. Händlerpreise sind datierte Momentaufnahmen; Holzpreise sind auf Zuschnittfläche hochgerechnete Materialreferenzen, Weichen- und Montageteile zum Teil Planpreise. Versand und Arbeitszeit sind nicht enthalten.

Die aktuelle Bibliothek umfasst 84 datierte Thomann-Einträge sowie weitere Chassis mit verifizierten Preisen, unter anderem zehn ergänzte Dayton-Audio-, Scan-Speak- und Visaton-Modelle. Über **Preisquelle öffnen** ist der Produktlink zugänglich. Ein Katalogeintrag ohne vollständige T/S- und Einbaudaten bleibt für die automatische Konstruktion gesperrt. Die Stückliste nennt Einzelpreis, Positionspreis und Preisart; der Budgetbedarf schließt die 15 % Reserve ein.

Die Registerkarte „Gesamtzeichnung“ enthält Vorderansicht, Rückansicht und Seitenschnitt sowie Tabellen mit Ausschnitten, Einbaukoordinaten, veröffentlichtem Lochkreis und allen daraus berechneten Bohrkoordinaten. Die Koordinaten beziehen sich je Außenfläche auf die linke untere Ecke. Für die innere Trennwand gilt das separate Einzelteilblatt als Bearbeitungsreferenz. Ohne veröffentlichten Lochkreis bleibt die Bohrung offen; am Originalteil messen. Die SVG ist frei skalierbar, Maßzahlen gelten vor grafischer Skalierung.

Berechenbar sind geschlossen, Bassreflex, Passivmembran, Bandpass 4. Ordnung, Bandpass 6. Ordnung parallel und zwei isobarische Bauarten. Die übrigen 22 Typen sind sichtbar, aber für eine Fertigungsfreigabe noch nicht ausreichend modelliert.

## Bibliothek und Preise in V-02.01.00

Der Assistent zeigt in Schritt 1 unter **Chassis / Preis** nur Lautsprecher mit T/S-Daten. Ein Modell kann festgelegt werden; sein Stückpreis erscheint direkt in der Auswahl. **Bibliothek** zeigt zusätzlich 73 Thomann-Katalogeinträge mit Preis und Quelllink. **Preisquelle öffnen** ruft die hinterlegte Thomann-Seite auf. Der Status **Katalog · T/S fehlen** bedeutet, dass das Produkt noch nicht automatisch berechnet werden kann. Für FaitalPRO 4FE35, 6FE200, 8FE200 und 15PR400 sind Herstellerdaten hinterlegt.

Die Preise sind offline gespeicherte Thomann-Momentaufnahmen vom 02.10.2026. Der Variantenvergleich zeigt nur den Preis der gewählten Chassis. Die Stückliste enthält Einzelpreis und Positionspreis, auch für die geschätzte Anzahl Dämmmaterialpackungen. **Bekannte Teilsumme** ist nur die Summe bepreister Positionen; unbepreiste Teile werden gezählt. PDF und CSV enthalten dieselbe Logik; im CSV steht zusätzlich die Preisquelle. Vor Kauf Preise und Verfügbarkeit beim Händler prüfen.

## Neu in V-02

Nach **Entwurf erstellen** zeigt **Variantenvergleich** Abmessungen, Nettovolumen, F3, technische Bewertung, Preis und Hinweiszahl nebeneinander. Die Tabs **Gesamtzeichnung**, **Maßblatt**, **Innenaufbau** und **Einzelteilplan** besitzen Zoom- und Einpassen-Schaltflächen. Im Einzelteilplan kann zwischen Front, Rückwand und Trennwand gewechselt werden, sofern die jeweilige Fläche Bauteile enthält. X und Y gelten jeweils ab der linken unteren Ecke des dargestellten Rohteils; Bohrbilder werden nur bei bekannten Herstellerangaben gezeichnet. Die Simulation zeigt neben dem relativen Pegel Auslenkung, Resonatorgeschwindigkeit und Gruppenlaufzeit, wenn die nötigen Daten vorhanden sind. Nach einer Änderung der Vorgaben ist erneut zu berechnen, bevor ein Projekt gespeichert oder exportiert werden kann.

## Einfacher Modus (Standardstart)

Beim Start erscheinen nur Projektname, Lautsprechertyp, Gehäuseprinzip, maximale Außenmaße und Klangprofil. Die tatsächlichen Maße dürfen kleiner sein. Optional lassen sich Außenvolumen, Budget, Ziel-F3, Zielpegel, Wegezahl, Aktiv/Passiv, Chassisgröße, Leistung, Material und Hersteller vorgeben. **Entwurf erstellen** läuft im Hintergrund; Fortschritt und **Abbrechen** bleiben verfügbar.

Die Ergebnisliste enthält bis zu drei Varianten. Jede Karte zeigt Komponenten, Gehäusemaße, F3, Bewertungsgrößen samt Mess-/Simulationsgrundlage, Warnungen und Begründung. Unter weiteren Tabs stehen Innenzeichnung, Tieftonsimulation und Stückliste. Speichern erzeugt `SpeakerProject`-JSON; Export nutzt dasselbe `DesignBundle` wie die Vorschau. Bei nicht erfüllbaren Vorgaben erscheinen Gründe und Änderungsvorschläge statt eines erzwungenen Designs.

**Bibliothek** öffnet sechs Kategorien mit Suche, JSON-Details, Import, Bearbeitung und Deaktivierung. Mitgeliefert sind markierte synthetische TESTDATEN und belegte Herstellerdaten von Dayton Audio, Visaton und Scan-Speak. Unvollständige Einbaumaße werden nicht ergänzt; die Automatik schließt solche Chassis aus. Ein vorläufiges passives 2-Wege-Netz enthält E12-Nennwerte; ohne passende FRD/ZMA ist seine akustische Summe unbekannt. Der bisherige technische Editor ist über **Expertenmodus** erreichbar. Seine Berechnung wird in die Startansicht übernommen.

Die nachfolgenden Abschnitte beschreiben die weiter vorhandene Expertenansicht.

## Teststart

Die Windows-EXE im entpackten Ordner starten oder die Python-App wie im README beschrieben ausführen. In der Startansicht stehen fünf Demo-Szenarien zur Auswahl. Im Expertenmodus lädt **Demo laden** den bisherigen synthetischen Beispielentwurf. Diese Werte dürfen nicht als reale Treiberdaten verwendet werden.

## Treiber

Fs, Qts und Vas sind für Gehäusewerte nötig. Für absolute Bassreflex-Auslenkung und Portgeschwindigkeit zusätzlich Qes, Re und Sd angeben; Qms kann aus Qts/Qes abgeleitet werden. Xmax und Pe dienen Warnungen. Qes/Qms/Qts werden auf Konsistenz geprüft. JSON/CSV-Kataloge lassen sich mit **Treiberdatei laden** öffnen. `data/test_driver_demo.json` ist ein gekennzeichneter Beispieldatensatz.

## Gehäuse und Simulation

Geschlossen: Ziel-Qtc bestimmt Vb, Fc und F3. Bassreflex: Netto-Vb, Fb und Rund-/Slot-Port festlegen; die Software berechnet Portlänge und eine relative Übertragungsfunktion. Passivmembran: Netto-Vb und Fb sowie gemessene Membranfläche, Grundmasse, Freiluft-Fs, Qms, Xmax und Einbaumaße eintragen. Aus der Zielabstimmung wird die Zusatzmasse berechnet; ist die Grundmasse bereits zu hoch, erscheint ein Fehler. Die Passivmembran sitzt in der Demo-Konstruktion auf der Rückwand. Bandpass 4. Ordnung: Front- und Rückkammervolumen wählen, die Frontkammer über einen Port abstimmen; der Tieftöner sitzt in der Trennwand. Bandpass 6. Ordnung parallel: zusätzlich Fb2 und BR2-Ø der Rückkammer angeben. BR2 ist ein gerader Rundport an der Rückwand. Aus beiden Portströmen entsteht der modellierte Gesamtfrequenzgang; die CSV nennt die Geschwindigkeiten einzeln. Zu lange Kanäle blockieren den Fertigungsexport. Isobarisch geschlossen/Bassreflex: zwei identische Chassis und Reihen- oder Parallelschaltung wählen; die Koppelkammer wird mit ihrer tatsächlichen Hüllgeometrie in der Volumenbilanz berücksichtigt. Das akustische Modell setzt ideale Kopplung voraus. Die Leistungswahl bietet 1, 10, 50, 100 W und freie Eingabe. Angezeigt werden Frequenzgang, Membranauslenkung, Resonatorgeschwindigkeit und Gruppenlaufzeit. Für Bandpass erscheinen unterer und oberer -3-dB-Punkt. 17/25 m/s sind Port-Richtwerte im Code, keine Naturgrenzen. **Drei Abstimmungen vergleichen** bietet Vorschläge für Bassreflex.

Plattenstärken: Basisstärke gilt für Seiten und optional alle anderen Platten. Eine Eingabe von 0 bei Front/Rückwand/Deckel/Boden bedeutet Basisstärke. Front-Lagen 2 erzeugt eine doppelte Front. Die Tiefe und Zuschnittliste folgen den effektiven Stärken. Verdrängungen von Treiber, Port, Fensterstreben und Zusatzvolumen gehen in die Nettovolumenrechnung ein.

## Frontlayout

Positionen sind in mm, Ursprung links unten auf der gewählten Front-, Rück- oder Trennwand. Element auswählen und numerische Werte ändern; Vorschau und Kollisionsprüfung laufen neu. Das Portprofil kommt aus der Portkonfiguration, die Position aus dem Layout. Lochkreis, Schraubenzahl und Bohrdurchmesser erzeugen DXF/SVG-Bohrungen. Die Innenaufbau-Zeichnung zeigt Seitenschnitt, Materialstärken, Bauteiltiefen, Port, Fensterstreben und gegebenenfalls Kammertrennwand, isobarische Koppelkammer und rückwärtige Passivmembran. Das zusätzliche Innenaufbau-Maßblatt nennt Strebenpositionen, Fensteröffnungen, Kammer- und Portmaße sowie die Volumenbilanz. Die Ansicht lässt sich zoomen. Kanten, Elementüberschneidungen auf derselben Platte, Tiefen und einige Strebenkonflikte werden geprüft. Bei erkannten Geometriefehlern wird der Fertigungsexport abgebrochen. Eine manuelle Werkstattprüfung bleibt erforderlich.

## Frequenzweiche

1. Ordnung, Butterworth 2 und LR2, optional L-Pad und Zobel. Ohne ZMA nutzt die Simulation Nennwiderstände; mit ZMA die frequenzabhängige komplexe Impedanz. FRD-Dateien brauchen Frequenz/Pegel, Phase ist optional. ZMA benötigt Frequenz/Ohm/Phase. Kommentare und Textkopfzeilen werden toleriert. Messdaten gelten nur in ihrem Frequenzbereich; außerhalb zeigt die Simulation keine extrapolierten Werte. Ohne beide FRD gibt es keine akustische Summe. Ohne Phase ist die Summe nur eine Pegel-Näherung.

## Speichern und Export

Nach einer Eingabe zeigt die App „Eingaben geändert“ und deaktiviert den Export bis zur erneuten Berechnung. **Projekt berechnen** öffnet die Ergebnisse und zeigt Rechenzeit sowie geänderte Kennwerte. **Projekt speichern** schreibt ein JSON mit Schema 3. **Projekt laden** akzeptiert alte JSONs ohne Schema-Feld sowie Schema 2. **Fertigungsunterlagen exportieren** schreibt das vollständige Paket wie im README. Das Projekt im Paket kann wieder geladen werden. Vor einem realen Zuschnitt Treiber-Maßblätter, Portfreiraum, Schrauben, Gehäuseverbindungen und die Weiche am aufgebauten Lautsprecher prüfen.
