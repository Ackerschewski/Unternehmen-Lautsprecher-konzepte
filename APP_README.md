# Lautsprecher Konstruktion V-02.07.00

Windows-Konstruktionsassistent für Lautsprecherentwürfe. Der Startbildschirm fragt nach Typ, maximalen Außenmaßen und Klangprofil. Der Expertenmodus bietet T/S-Eingabe, Frontlayout, Messdatenimport und manuelle Gehäuseparameter.

## Start

1. `Lautsprecher-Konstruktion_V-02.05.00_Windows.zip` vollständig entpacken.
2. `Lautsprecher-Konstruktion_V-02.05.00.exe` starten; `_internal` muss daneben bleiben.
3. Entwurf erstellen und Variantenvergleich, Zeichnungen, Simulation und Stückliste prüfen.
4. Fertigungsunterlagen als PDF, SVG, DXF und CSV exportieren.

## V-02.07.00

**Mehrwege und Bedienkomfort.** Der Expertenmodus berechnet jetzt eine **passive 3-Wege-Weiche** (1. Ordnung, Butterworth 2. Ordnung, Linkwitz-Riley 2. Ordnung) mit Tiefpass für den Woofer, Bandpass für den Mitteltöner und Hochpass für den Hochtöner. Optional kommen Zobel, Schallwandkorrektur und L-Pads für Mittel- und Hochtöner dazu. Die Simulation löst jeden Zweig als exakte Kettenschaltung gegen die komplexe Last (gemessene ZMA, falls geladen); die Wechselwirkung der beiden Mittelton-Abschnitte ist damit sichtbar. Schaltplan, Stückliste, Weichen-CSV und Export kennen die dritte Weg. Die Bauteilwerte sind elektrische Startwerte; Schallzentren, Laufzeit und Treiberpegel sind am Prototyp zu messen. Der Assistent wählt weiterhin keine 3-Wege-Lautsprecher automatisch.

Das **Frontlayout** hat eine interaktive Zeichenfläche: Treiber und Ports lassen sich mit der Maus ziehen (Einrasten auf 5 mm und Mittellinie, abschaltbar) oder mit den Pfeiltasten verschieben (Umschalt = 10 mm); die Ansicht wechselt zwischen Front, Rückwand und Trennwand. **Rückgängig/Wiederholen** (`Strg+Z`, `Strg+Y`) gilt für Hinzufügen, Löschen, Ziehen und Werteingaben; schnelle Folgeänderungen werden zu einem Schritt zusammengefasst.

**Fertigung:** Im Expertenmodus lässt sich die **Gehrungsverbindung** wählen (Seiten, Deckel und Boden mit 45°-Gehrung): die Zuschnittliste führt dann die volle Außenlänge und den Gehrungshinweis, die Bauanleitung enthält den Schritt „Gehrungen sägen und verkleben“. Das Innenvolumen ändert sich nicht; die Zeichnungen zeigen weiterhin die Plattenstärken, nicht die Gehrungsflächen. Zusätzlich liegt jede Zuschnitt-Platte als **DXF** (Ebenen SHEET, PARTS, TEXT) für CNC und Plattensägedienste im Ordner `zuschnittplan` vor.

Geschlossene Gehäuse haben jetzt dieselbe Simulation wie Bassreflex: Membranauslenkung, Impedanz, Gruppenlaufzeit und Pegel (auch im Export und im Prototypvergleich). Im Assistenten bleibt der Button „Entwurf erstellen“ unterhalb des scrollenden Formulars immer sichtbar. Eine Übergabe für externe Tests steht in `docs/application/CODEX_TESTUEBERGABE.md`.

Qualität: `mypy --strict` ist für alle Rechen-, Export- und Datenpakete grün (die Qt-Oberfläche ist ausdrücklich ausgenommen). Dabei wurden fehlende Vas-Werte als klare Fehlermeldung statt als Programmfehler behandelt und eine fehlerhafte Katalogdatei wird gemeldet statt abzustürzen. Alle Oberflächendateien sind zu mindestens 75 % getestet.

Nicht enthalten und weiter offen: 3D-Kollisions- und Gehrungsprüfung, Messvalidierung mit Prototypen, automatische Auswahl von 3-Wege-Lautsprechern, Windows-Build dieser Version.

## V-02.06.00

**Zuschnitt, Bauanleitung und Prototypvergleich.** Der Export enthält jetzt neben Zeichnungen und Stückliste einen **Zuschnittplan** (CSV, SVG je Platte, PDF): Alle Gehäuseteile einschließlich Streben werden mit Sägeschnitt auf Handelsplatten verteilt (Standard Birke Multiplex 2 500 × 1 250 mm, MDF/Spanplatte 2 440 × 1 220 mm, einstellbar), getrennt nach Plattendicke. Verschnitt, Plattenzahl und nicht passende Teile werden ausgewiesen; Trapez- und Rundteile werden als umschreibendes Rechteck geplant. Dazu kommen ein **Gehäusegewicht** als Bereich (nur Plattenmaterial; Chassis, Weiche und Dämmung sind nicht enthalten, die Dichten sind typische Handelswerte) und eine aus der berechneten Konstruktion abgeleitete **Bauanleitung** (Markdown und PDF) mit Kontrollschritten je Bauform.

Unter **Werkzeuge → Prototyp vergleichen** (und im Expertenmodus) werden gemessene FRD/ZMA-Kurven des gebauten Lautsprechers mit der Simulation verglichen: RMS- und Maximalabweichung, F3, Abstimmfrequenz aus dem Impedanzminimum und – bei Bassreflex – eine Portlängenkorrektur. Das Werkzeug ist auch per Kommandozeile nutzbar (`python -m lautsprecher_konstruktion.validation projekt.json --frd m.frd --zma m.zma`). Es **validiert das Modell nicht**; dafür sind Messungen mehrerer Treiber und Bauformen nötig (siehe `docs/application/MESSPROTOKOLL.md`).

Die **Schallwandkorrektur** (Baffle Step, Näherung 115 Hz·m / Schallwandbreite) ist im Expertenmodus als Weichenoption wählbar (0–6 dB, Spule mit Parallelwiderstand im Tieftonzweig) und erscheint als gestrichelte Kurve im Frequenzgang. Die Modellannahmen sind nicht an Messungen validiert.

Alltagstauglichkeit: Menü mit **Zuletzt geöffnet**, Tastenkürzeln, Ungespeichert-Warnung, **Autosave und Wiederherstellung** nach einem Absturz, gespeicherte Einstellungen (Theme, Plattenmaß, Sägeschnitt), rotierendes **Programmprotokoll** und Hilfe/Über (F1). Referenztests prüfen die Solver gegen Literaturwerte (Small/Thiele-Beziehungen, Butterworth-/Linkwitz-Riley-Eigenschaften). Die Versionsangabe stammt aus einer einzigen Quelle (`lautsprecher_konstruktion.__version__`).

Offen blieben in dieser Version: 3-Wege-Weiche, Undo/Redo und Drag-and-drop im Frontlayout (seit V-02.07.00 vorhanden), 3D-Kollisions- und Gehrungsprüfung, Messvalidierung mit realen Prototypen, Windows-Build.

## V-02.05.00

Alle 29 im Typenkatalog aufgeführten Gehäusearten haben jetzt einen Berechnungspfad. Ergänzt wurden Bandpass 6 seriell, Compound Push-Pull, Aperiodisch, passiver Kardioid, sechs gefaltete Linienformen, sieben segmentierte rückwärtige Hörner, Infinite/Open Baffle und U-Frame sowie Front-Horn und Tapped-Horn. Der Expertenmodus zeigt die passenden Eingaben, Ergebnisse und Fertigungsansichten. Der automatische Assistent kann Front-Horn und Tapped-Horn als Einzel-Tieftöner mit ausreichendem Bauraum auswählen. Bei unpassenden Maßen oder fehlenden Chassisdaten wird der Entwurf abgelehnt.

Front-Horn und Tapped-Horn besitzen eigene akustische Netzwerke. Für das Front-Horn werden Hals, Mund, axiale Länge und vier trapezförmige Platten berechnet und zwei Trapez-DXF-Dateien exportiert. Im Tapped-Horn sitzt W1 auf der innenliegenden Platte F1 zwischen zwei Kanalwegen. F1-Zuschnitt, Treiberausschnitt, dokumentierte Bohrungen, Umlenkspalt und Frontmündung erscheinen in Zeichnung, PDF, DXF und Stückliste. Beide Hörner haben eigene PDF-Fertigungsblätter. Die Innenformen und akustischen Näherungen sind in [Gehäusemodelle V-02.05.00](docs/ENCLOSURE_MODELS_V205.md) beschrieben. Vor dem Bau sind Prototypmessung, Montagefreiräume und Plattenstöße zu prüfen.

## V-02.04.00

Bandpass 6. Ordnung parallel ist als siebter berechenbarer Gehäusetyp ergänzt. Die Front- und Rückkammer besitzen getrennte Netto-Volumina, Abstimmfrequenzen und Ports BR1/BR2. Der Expertenmodus bietet die zweite Abstimmung und den Rückportdurchmesser; der Assistent kann diesen Typ für Subwoofer prüfen. Die zwei Portöffnungen erscheinen in Vorder-/Rückwand-DXF, Gesamtzeichnung, Innenschnitt, PDF, Zuschnitt und Stückliste. Die Simulation liefert beide Portgeschwindigkeiten getrennt und erkennt zu lange Ports in ihrer jeweiligen Kammer.

Das Modell ist eine lineare Näherung mit konzentrierten akustischen Elementen und kohärent zusammengefassten Portauslässen. Tatsächlicher Abstand der beiden Auslässe, Leckagen, Strömungsverluste, Kanal- und Kammermoden bleiben offen. Frequenzgang und Abstimmungen am gebauten Gehäuse messen. Die Herleitung und Grenzen stehen in `docs/BANDPASS6_MODEL.md`.

## V-02.03.00

Die automatische Zweiwege-Suche prüft jetzt mehrere passende Hochtöner und wählt nicht mehr ausschließlich den mit der niedrigsten Übergangsfrequenz. Bei Budgetvorgabe werden nur bepreiste Chassis-Kombinationen geprüft; jede Variante muss mit ihrer gesamten Materialstückliste und 15 % Reserve unter dem Budget bleiben. Der Vergleich zeigt die konkrete Chassiswahl und den noch freien Budgetbetrag.

Automatisch erzeugte Fertigungspläne übernehmen den Bohrdurchmesser nur aus bekannten Herstellerdaten. Ist zwar der Lochkreis bekannt, aber der Bohrdurchmesser nicht, bleibt die Bohrung in SVG, PDF und DXF offen. Das Maßblatt benennt den fehlenden Wert. Im Expertenmodus kann der Nutzer einen gemessenen Bohrdurchmesser selbst eingeben. Der Umsetzungsplan mit Abnahmekriterien steht in `docs/PLAN_V-02.03.00.md`.

## V-02.02.00

Der Assistent fragt das Gesamtbudget direkt bei der Konfiguration ab. Die Budgetprüfung rechnet für **ein Gehäuse** Chassis, Holzplatten, Streben, Port beziehungsweise Passivmembran, Weichenbauteile, Dämpfung, Anschlussterminal, Kabel, Leim und Befestigung zusammen und addiert 15 % Materialreserve. Varianten mit fehlendem Chassispreis werden bei aktivem Budget verworfen. Die Stückliste zeigt jeden kalkulierten Einzelpreis, dessen Art (Händlerpreis, Materialreferenz oder Planpreis), die Materialsumme und den Budgetbedarf mit Reserve. Planpreise sind ausdrücklich Richtwerte, keine Händlerangebote; Versand, Werkzeuge, Arbeitszeit und Steuern über den ausgewiesenen Produktpreisen hinaus sind nicht modelliert.

Die Bibliothek enthält jetzt 84 datierte Thomann-Katalogeinträge. Acht FaitalPRO-Chassis haben zusätzlich vollständige, getrennt belegte Herstellerdaten für die Berechnung. Weitere Einträge ohne T/S oder Montageangaben bleiben als Preis- und Recherchekatalog sichtbar; fehlende Daten werden nicht geschätzt. Die Gesamtzeichnung zeigt Vorder- und Rückansicht, einen Seitenschnitt mit Innenteilen, Einbaukoordinaten, Ausschnitte, dokumentierte Lochkreise und jede daraus berechnete Bohrkoordinate, Zuschnitt und Hinweise. Für unbekannte Lochbilder steht ausdrücklich „nicht veröffentlicht“ im Blatt. Einzelteilzeichnungen und DXF bleiben Bestandteil des Exports.

Zehn weitere Chassis von Dayton Audio, Scan-Speak und Visaton haben datierte Euro-Preise mit Händler- oder Herstellerlink erhalten. Damit können sie auch in einer Budgetberechnung berücksichtigt werden, sofern die erforderlichen Konstruktionsdaten vorliegen. Synthetische Testdatensätze bleiben ausdrücklich unbepreist.

Die sechs vollständig integrierten Gehäusearten bleiben nutzbar. Die weiteren 23 vorgesehenen Arten sind in der Auswahl als Entwicklungsstand sichtbar. Für Transmission Lines, Hörner und weitere Bandpassformen fehlen noch belastbare akustische Modelle und herstellbare Innengeometrien; sie werden nicht als fertig ausgegeben.

## V-02.01.00

Die Bibliothek wurde um 73 Thomann-Katalogeinträge aus den Bereichen Visaton, FaitalPRO, Eminence und weitere ergänzt. Jeder Eintrag enthält einen geprüften Euro-Preisstand vom 02.10.2026 und eine Preisquelle. Diese Preise sind offline gespeicherte Momentaufnahmen, keine Live-Abfrage und kein Angebot. Produkte ohne vollständige T/S- und Montagedaten sind in der Bibliothek sichtbar, aber für die automatische Berechnung gesperrt. Der FaitalPRO 6FE200 besitzt zusätzlich Herstellerdaten aus dem Datenblatt; für bestehende Visaton B 200 und W 200 S sind Thomann-Preise hinterlegt.

Im Assistenten kann ein berechenbares Chassis mit angezeigtem Stückpreis fest gewählt werden. Der Variantenvergleich zeigt den Chassispreis, einschließlich zweitem Tieftöner bei Isobarik. Die Stückliste in der App sowie CSV und PDF enthalten Einzel- und Positionspreise. Die bekannte Teilsumme nennt ausdrücklich die Anzahl unbepreister Positionen. Holz, Weichenbauteile, Port, Versand und Arbeitszeit werden ohne verifizierten Preis nicht hinzugerechnet. Visaton-Dämmmaterial ist als geschätzte Packungsmenge und mit Thomann-Preis enthalten; die tatsächliche Menge muss beim Bau angepasst werden.

## V-02.00.00

Die neue Ergebnisansicht enthält einen Variantenvergleich und vier Tieftonplots. Zeichnungen lassen sich an das Fenster anpassen und gezielt zoomen. Einzeln auswählbare Fertigungspläne zeigen Front, Rückwand und Trennwand samt Rohmaß, Ausschnitt, Einbaukoordinaten und veröffentlichtem Bohrbild. Für die Trennwand wird derselbe lokale Koordinatenursprung wie in der DXF-Datei verwendet. Geänderte Vorgaben sperren Speichern und Export, bis ein neuer Entwurf berechnet wurde.

Das Maßblatt und das Innenaufbau-Blatt wachsen bei vielen Bauteilen mit, damit keine Tabellenzeilen abgeschnitten werden. Der Innenschnitt zeigt jetzt auch Treiber, Port und Öffnung in der Trennwand. Die PDF-Fertigungsunterlagen enthalten eigene Einzelteilseiten; Strebenpositionen und isobarische Koppelkammer folgen den berechneten Tiefenpositionen.

Sechs Gehäusearten sind berechenbar: geschlossen, Bassreflex, Passivmembran, Bandpass 4. Ordnung sowie isobarisch geschlossen und isobarisch Bassreflex. Weitere Typen bleiben sichtbar als „in Entwicklung“ und sind nicht auswählbar. Für isobarische Entwürfe werden zwei identische Chassis in gleicher Bewegungsrichtung, eine luftdichte Koppelkammer und Reihen- oder Parallelschaltung angenommen. Das ideale Kleinsignalmodell berücksichtigt die endliche Luftnachgiebigkeit und Verluste der Koppelkammer noch nicht; vor dem Bau Messung und Polung prüfen.

Das neue Innenaufbau-Maßblatt zeigt Tiefenpositionen von Streben, Kammern und Koppelring, Fensteröffnungen, Portmaße und die Volumenbilanz. Ein Ringprofil-DXF und die Koppelrohr-Spezifikation werden mit exportiert. Geometriefehler wie zu geringe Tandemtiefe oder Kollisionen der Koppelkammer blockieren den Fertigungsexport.

Die Bibliothek enthält Herstellerdaten für Dayton Audio, Visaton und Scan-Speak sowie gekennzeichnete synthetische TESTDATEN. Jeder Herstellerdatensatz besitzt Quelle und Abrufdatum. Nicht veröffentlichte Maße und Werte bleiben leer; solche Treiber scheiden aus dem automatischen Entwurf aus, bis sie vervollständigt werden. Frequenzgang- und Impedanzmessungen für die realen Treiber sind nicht eingebunden. Eigene JSON-/CSV-Daten können lokal importiert werden.

## Entwicklung

Aus dem Quellcode: `python -m venv .venv`, `.venv\Scripts\python -m pip install -e ".[dev]"`, `.venv\Scripts\python -m lautsprecher_konstruktion.app`.

Tests: `.venv\Scripts\python -m pytest --basetemp .test_run -p no:cacheprovider` und `.venv\Scripts\python -m ruff check src tests`. Der lokale Windows-Build läuft über `powershell -ExecutionPolicy Bypass -File scripts/build_windows.ps1`.

## Grenzen

Die Gehäusemodelle sind lineare Kleinsignal-Näherungen ohne umfassenden Abgleich mit realen Messungen. Portkompression, thermische Effekte, Baffle Step, Raum, gefaltete Ports, vollständige 3D-Kollisionen und Bauteiltoleranzen fehlen. Ein E12-Weichenvorschlag ist ein elektrischer Startwert. Alle Herstellerangaben, Maße und Bohrbilder vor dem Zuschnitt am echten Chassis prüfen.

Weitere Details: `docs/application/USER_MANUAL.md`, `docs/application/ARCHITECTURE.md`, `docs/application/MAINTENANCE.md`, `docs/application/VALIDATION.md` und `docs/application/BUILD_REPORT_V-02.07.00.md`. Plan zur fertigen Version: `docs/application/PLAN_V-03.00.00.md`.
