# Lautsprecher Konstruktion V-02.03.00

Windows-Konstruktionsassistent für Lautsprecherentwürfe. Der Startbildschirm fragt nach Typ, maximalen Außenmaßen und Klangprofil. Der Expertenmodus bietet T/S-Eingabe, Frontlayout, Messdatenimport und manuelle Gehäuseparameter.

## Start

1. `Lautsprecher-Konstruktion_V-02.03.00_Windows.zip` vollständig entpacken.
2. `Lautsprecher-Konstruktion_V-02.03.00.exe` starten; `_internal` muss daneben bleiben.
3. Entwurf erstellen und Variantenvergleich, Zeichnungen, Simulation und Stückliste prüfen.
4. Fertigungsunterlagen als PDF, SVG, DXF und CSV exportieren.

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

Weitere Details: `docs/USER_MANUAL.md`, `docs/ARCHITECTURE.md`, `docs/MAINTENANCE.md` und `BUILD_REPORT_V-02.03.00.md`.
