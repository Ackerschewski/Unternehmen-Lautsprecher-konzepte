# Nutzerhandbuch � V-02.02.00

## Gesamtbudget und Fertigungszeichnung

Im ersten Schritt kann unter �Gesamtbudget bis� ein Euro-Betrag f�r **einen Lautsprecher** eingegeben werden. 0 � bedeutet ohne Budgetgrenze. Der Assistent ber�cksichtigt alle kalkulierten Positionen der St�ckliste und 15 % Materialreserve. Steht f�r ein ausgew�hltes Chassis kein Euro-Preis zur Verf�gung, wird es bei gesetztem Budget nicht als passend best�tigt. H�ndlerpreise sind datierte Momentaufnahmen; Holzpreise sind auf Zuschnittfl�che hochgerechnete Materialreferenzen, Weichen- und Montageteile zum Teil Planpreise. Versand und Arbeitszeit sind nicht enthalten.

Die aktuelle Bibliothek umfasst 84 datierte Thomann-Eintr�ge sowie weitere Chassis mit verifizierten Preisen, unter anderem zehn erg�nzte Dayton-Audio-, Scan-Speak- und Visaton-Modelle. �ber **Preisquelle �ffnen** ist der Produktlink zug�nglich. Ein Katalogeintrag ohne vollst�ndige T/S- und Einbaudaten bleibt f�r die automatische Konstruktion gesperrt. Die St�ckliste nennt Einzelpreis, Positionspreis und Preisart; der Budgetbedarf schlie�t die 15 % Reserve ein.

Die Registerkarte �Gesamtzeichnung� enth�lt Vorderansicht, R�ckansicht und Seitenschnitt sowie Tabellen mit Ausschnitten, Einbaukoordinaten, ver�ffentlichtem Lochkreis und allen daraus berechneten Bohrkoordinaten. Die Koordinaten beziehen sich je Au�enfl�che auf die linke untere Ecke. F�r die innere Trennwand gilt das separate Einzelteilblatt als Bearbeitungsreferenz. Ohne ver�ffentlichten Lochkreis bleibt die Bohrung offen; am Originalteil messen. Die SVG ist frei skalierbar, Ma�zahlen gelten vor grafischer Skalierung.

Berechenbar sind geschlossen, Bassreflex, Passivmembran, Bandpass 4. Ordnung und zwei isobarische Bauarten. 23 weitere Typen sind sichtbar, aber f�r eine Fertigungsfreigabe noch nicht ausreichend modelliert.

## Bibliothek und Preise in V-02.01.00

Der Assistent zeigt in Schritt 1 unter **Chassis / Preis** nur Lautsprecher mit T/S-Daten. Ein Modell kann festgelegt werden; sein St�ckpreis erscheint direkt in der Auswahl. **Bibliothek** zeigt zus�tzlich 73 Thomann-Katalogeintr�ge mit Preis und Quelllink. **Preisquelle �ffnen** ruft die hinterlegte Thomann-Seite auf. Der Status **Katalog � T/S fehlen** bedeutet, dass das Produkt noch nicht automatisch berechnet werden kann. F�r FaitalPRO 4FE35, 6FE200, 8FE200 und 15PR400 sind Herstellerdaten hinterlegt.

Die Preise sind offline gespeicherte Thomann-Momentaufnahmen vom 02.10.2026. Der Variantenvergleich zeigt nur den Preis der gew�hlten Chassis. Die St�ckliste enth�lt Einzelpreis und Positionspreis, auch f�r die gesch�tzte Anzahl D�mmmaterialpackungen. **Bekannte Teilsumme** ist nur die Summe bepreister Positionen; unbepreiste Teile werden gez�hlt. PDF und CSV enthalten dieselbe Logik; im CSV steht zus�tzlich die Preisquelle. Vor Kauf Preise und Verf�gbarkeit beim H�ndler pr�fen.

## Neu in V-02

Nach **Entwurf erstellen** zeigt **Variantenvergleich** Abmessungen, Nettovolumen, F3, technische Bewertung, Preis und Hinweiszahl nebeneinander. Die Tabs **Gesamtzeichnung**, **Ma�blatt**, **Innenaufbau** und **Einzelteilplan** besitzen Zoom- und Einpassen-Schaltfl�chen. Im Einzelteilplan kann zwischen Front, R�ckwand und Trennwand gewechselt werden, sofern die jeweilige Fl�che Bauteile enth�lt. X und Y gelten jeweils ab der linken unteren Ecke des dargestellten Rohteils; Bohrbilder werden nur bei bekannten Herstellerangaben gezeichnet. Die Simulation zeigt neben dem relativen Pegel Auslenkung, Resonatorgeschwindigkeit und Gruppenlaufzeit, wenn die n�tigen Daten vorhanden sind. Nach einer �nderung der Vorgaben ist erneut zu berechnen, bevor ein Projekt gespeichert oder exportiert werden kann.

## Einfacher Modus (Standardstart)

Beim Start erscheinen nur Projektname, Lautsprechertyp, Geh�useprinzip, maximale Au�enma�e und Klangprofil. Die tats�chlichen Ma�e d�rfen kleiner sein. Optional lassen sich Au�envolumen, Budget, Ziel-F3, Zielpegel, Wegezahl, Aktiv/Passiv, Chassisgr��e, Leistung, Material und Hersteller vorgeben. **Entwurf erstellen** l�uft im Hintergrund; Fortschritt und **Abbrechen** bleiben verf�gbar.

Die Ergebnisliste enth�lt bis zu drei Varianten. Jede Karte zeigt Komponenten, Geh�usema�e, F3, Bewertungsgr��en samt Mess-/Simulationsgrundlage, Warnungen und Begr�ndung. Unter weiteren Tabs stehen Innenzeichnung, Tieftonsimulation und St�ckliste. Speichern erzeugt `SpeakerProject`-JSON; Export nutzt dasselbe `DesignBundle` wie die Vorschau. Bei nicht erf�llbaren Vorgaben erscheinen Gr�nde und �nderungsvorschl�ge statt eines erzwungenen Designs.

**Bibliothek** �ffnet sechs Kategorien mit Suche, JSON-Details, Import, Bearbeitung und Deaktivierung. Mitgeliefert sind markierte synthetische TESTDATEN und belegte Herstellerdaten von Dayton Audio, Visaton und Scan-Speak. Unvollst�ndige Einbauma�e werden nicht erg�nzt; die Automatik schlie�t solche Chassis aus. Ein vorl�ufiges passives 2-Wege-Netz enth�lt E12-Nennwerte; ohne passende FRD/ZMA ist seine akustische Summe unbekannt. Der bisherige technische Editor ist �ber **Expertenmodus** erreichbar. Seine Berechnung wird in die Startansicht �bernommen.

Die nachfolgenden Abschnitte beschreiben die weiter vorhandene Expertenansicht.

## Teststart

Die Windows-EXE im entpackten Ordner starten oder die Python-App wie im README beschrieben ausf�hren. In der Startansicht stehen f�nf Demo-Szenarien zur Auswahl. Im Expertenmodus l�dt **Demo laden** den bisherigen synthetischen Beispielentwurf. Diese Werte d�rfen nicht als reale Treiberdaten verwendet werden.

## Treiber

Fs, Qts und Vas sind f�r Geh�usewerte n�tig. F�r absolute Bassreflex-Auslenkung und Portgeschwindigkeit zus�tzlich Qes, Re und Sd angeben; Qms kann aus Qts/Qes abgeleitet werden. Xmax und Pe dienen Warnungen. Qes/Qms/Qts werden auf Konsistenz gepr�ft. JSON/CSV-Kataloge lassen sich mit **Treiberdatei laden** �ffnen. `data/test_driver_demo.json` ist ein gekennzeichneter Beispieldatensatz.

## Geh�use und Simulation

Geschlossen: Ziel-Qtc bestimmt Vb, Fc und F3. Bassreflex: Netto-Vb, Fb und Rund-/Slot-Port festlegen; die Software berechnet Portl�nge und eine relative �bertragungsfunktion. Passivmembran: Netto-Vb und Fb sowie gemessene Membranfl�che, Grundmasse, Freiluft-Fs, Qms, Xmax und Einbauma�e eintragen. Aus der Zielabstimmung wird die Zusatzmasse berechnet; ist die Grundmasse bereits zu hoch, erscheint ein Fehler. Die Passivmembran sitzt in der Demo-Konstruktion auf der R�ckwand. Bandpass 4. Ordnung: Front- und R�ckkammervolumen w�hlen, die Frontkammer �ber einen Port abstimmen; der Tieft�ner sitzt in der Trennwand. Isobarisch geschlossen/Bassreflex: zwei identische Chassis und Reihen- oder Parallelschaltung w�hlen; die Koppelkammer wird mit ihrer tats�chlichen H�llgeometrie in der Volumenbilanz ber�cksichtigt. Das akustische Modell setzt ideale Kopplung voraus. Die Leistungswahl bietet 1, 10, 50, 100 W und freie Eingabe. Angezeigt werden Frequenzgang, Membranauslenkung, Resonatorgeschwindigkeit und Gruppenlaufzeit. F�r Bandpass erscheinen unterer und oberer -3-dB-Punkt. 17/25 m/s sind Port-Richtwerte im Code, keine Naturgrenzen. **Drei Abstimmungen vergleichen** bietet Vorschl�ge f�r Bassreflex.

Plattenst�rken: Basisst�rke gilt f�r Seiten und optional alle anderen Platten. Eine Eingabe von 0 bei Front/R�ckwand/Deckel/Boden bedeutet Basisst�rke. Front-Lagen 2 erzeugt eine doppelte Front. Die Tiefe und Zuschnittliste folgen den effektiven St�rken. Verdr�ngungen von Treiber, Port, Fensterstreben und Zusatzvolumen gehen in die Nettovolumenrechnung ein.

## Frontlayout

Positionen sind in mm, Ursprung links unten auf der gew�hlten Front-, R�ck- oder Trennwand. Element ausw�hlen und numerische Werte �ndern; Vorschau und Kollisionspr�fung laufen neu. Das Portprofil kommt aus der Portkonfiguration, die Position aus dem Layout. Lochkreis, Schraubenzahl und Bohrdurchmesser erzeugen DXF/SVG-Bohrungen. Die Innenaufbau-Zeichnung zeigt Seitenschnitt, Materialst�rken, Bauteiltiefen, Port, Fensterstreben und gegebenenfalls Kammertrennwand, isobarische Koppelkammer und r�ckw�rtige Passivmembran. Das zus�tzliche Innenaufbau-Ma�blatt nennt Strebenpositionen, Fenster�ffnungen, Kammer- und Portma�e sowie die Volumenbilanz. Die Ansicht l�sst sich zoomen. Kanten, Element�berschneidungen auf derselben Platte, Tiefen und einige Strebenkonflikte werden gepr�ft. Bei erkannten Geometriefehlern wird der Fertigungsexport abgebrochen. Eine manuelle Werkstattpr�fung bleibt erforderlich.

## Frequenzweiche

1. Ordnung, Butterworth 2 und LR2, optional L-Pad und Zobel. Ohne ZMA nutzt die Simulation Nennwiderst�nde; mit ZMA die frequenzabh�ngige komplexe Impedanz. FRD-Dateien brauchen Frequenz/Pegel, Phase ist optional. ZMA ben�tigt Frequenz/Ohm/Phase. Kommentare und Textkopfzeilen werden toleriert. Messdaten gelten nur in ihrem Frequenzbereich; au�erhalb zeigt die Simulation keine extrapolierten Werte. Ohne beide FRD gibt es keine akustische Summe. Ohne Phase ist die Summe nur eine Pegel-N�herung.

## Speichern und Export

Nach einer Eingabe zeigt die App �Eingaben ge�ndert� und deaktiviert den Export bis zur erneuten Berechnung. **Projekt berechnen** �ffnet die Ergebnisse und zeigt Rechenzeit sowie ge�nderte Kennwerte. **Projekt speichern** schreibt ein JSON mit Schema 3. **Projekt laden** akzeptiert alte JSONs ohne Schema-Feld sowie Schema 2. **Fertigungsunterlagen exportieren** schreibt das vollst�ndige Paket wie im README. Das Projekt im Paket kann wieder geladen werden. Vor einem realen Zuschnitt Treiber-Ma�bl�tter, Portfreiraum, Schrauben, Geh�useverbindungen und die Weiche am aufgebauten Lautsprecher pr�fen.
