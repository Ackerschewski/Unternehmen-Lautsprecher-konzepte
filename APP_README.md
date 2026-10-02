# Lautsprecher Konstruktion V-02.02.00

Windows-Konstruktionsassistent f�r Lautsprecherentw�rfe. Der Startbildschirm fragt nach Typ, maximalen Au�enma�en und Klangprofil. Der Expertenmodus bietet T/S-Eingabe, Frontlayout, Messdatenimport und manuelle Geh�useparameter.

## Start

1. `Lautsprecher-Konstruktion_V-02.02.00_Windows.zip` vollst�ndig entpacken.
2. `Lautsprecher-Konstruktion_V-02.02.00.exe` starten; `_internal` muss daneben bleiben.
3. Entwurf erstellen und Variantenvergleich, Zeichnungen, Simulation und St�ckliste pr�fen.
4. Fertigungsunterlagen als PDF, SVG, DXF und CSV exportieren.

## V-02.02.00

Der Assistent fragt das Gesamtbudget direkt bei der Konfiguration ab. Die Budgetpr�fung rechnet f�r **ein Geh�use** Chassis, Holzplatten, Streben, Port beziehungsweise Passivmembran, Weichenbauteile, D�mpfung, Anschlussterminal, Kabel, Leim und Befestigung zusammen und addiert 15 % Materialreserve. Varianten mit fehlendem Chassispreis werden bei aktivem Budget verworfen. Die St�ckliste zeigt jeden kalkulierten Einzelpreis, dessen Art (H�ndlerpreis, Materialreferenz oder Planpreis), die Materialsumme und den Budgetbedarf mit Reserve. Planpreise sind ausdr�cklich Richtwerte, keine H�ndlerangebote; Versand, Werkzeuge, Arbeitszeit und Steuern �ber den ausgewiesenen Produktpreisen hinaus sind nicht modelliert.

Die Bibliothek enth�lt jetzt 84 datierte Thomann-Katalogeintr�ge. Acht FaitalPRO-Chassis haben zus�tzlich vollst�ndige, getrennt belegte Herstellerdaten f�r die Berechnung. Weitere Eintr�ge ohne T/S oder Montageangaben bleiben als Preis- und Recherchekatalog sichtbar; fehlende Daten werden nicht gesch�tzt. Die Gesamtzeichnung zeigt Vorder- und R�ckansicht, einen Seitenschnitt mit Innenteilen, Einbaukoordinaten, Ausschnitte, dokumentierte Lochkreise und jede daraus berechnete Bohrkoordinate, Zuschnitt und Hinweise. F�r unbekannte Lochbilder steht ausdr�cklich �nicht ver�ffentlicht� im Blatt. Einzelteilzeichnungen und DXF bleiben Bestandteil des Exports.

Zehn weitere Chassis von Dayton Audio, Scan-Speak und Visaton haben datierte Euro-Preise mit H�ndler- oder Herstellerlink erhalten. Damit k�nnen sie auch in einer Budgetberechnung ber�cksichtigt werden, sofern die erforderlichen Konstruktionsdaten vorliegen. Synthetische Testdatens�tze bleiben ausdr�cklich unbepreist.

Die sechs vollst�ndig integrierten Geh�usearten bleiben nutzbar. Die weiteren 23 vorgesehenen Arten sind in der Auswahl als Entwicklungsstand sichtbar. F�r Transmission Lines, H�rner und weitere Bandpassformen fehlen noch belastbare akustische Modelle und herstellbare Innengeometrien; sie werden nicht als fertig ausgegeben.

## V-02.01.00

Die Bibliothek wurde um 73 Thomann-Katalogeintr�ge aus den Bereichen Visaton, FaitalPRO, Eminence und weitere erg�nzt. Jeder Eintrag enth�lt einen gepr�ften Euro-Preisstand vom 02.10.2026 und eine Preisquelle. Diese Preise sind offline gespeicherte Momentaufnahmen, keine Live-Abfrage und kein Angebot. Produkte ohne vollst�ndige T/S- und Montagedaten sind in der Bibliothek sichtbar, aber f�r die automatische Berechnung gesperrt. Der FaitalPRO 6FE200 besitzt zus�tzlich Herstellerdaten aus dem Datenblatt; f�r bestehende Visaton B 200 und W 200 S sind Thomann-Preise hinterlegt.

Im Assistenten kann ein berechenbares Chassis mit angezeigtem St�ckpreis fest gew�hlt werden. Der Variantenvergleich zeigt den Chassispreis, einschlie�lich zweitem Tieft�ner bei Isobarik. Die St�ckliste in der App sowie CSV und PDF enthalten Einzel- und Positionspreise. Die bekannte Teilsumme nennt ausdr�cklich die Anzahl unbepreister Positionen. Holz, Weichenbauteile, Port, Versand und Arbeitszeit werden ohne verifizierten Preis nicht hinzugerechnet. Visaton-D�mmmaterial ist als gesch�tzte Packungsmenge und mit Thomann-Preis enthalten; die tats�chliche Menge muss beim Bau angepasst werden.

## V-02.00.00

Die neue Ergebnisansicht enth�lt einen Variantenvergleich und vier Tieftonplots. Zeichnungen lassen sich an das Fenster anpassen und gezielt zoomen. Einzeln ausw�hlbare Fertigungspl�ne zeigen Front, R�ckwand und Trennwand samt Rohma�, Ausschnitt, Einbaukoordinaten und ver�ffentlichtem Bohrbild. F�r die Trennwand wird derselbe lokale Koordinatenursprung wie in der DXF-Datei verwendet. Ge�nderte Vorgaben sperren Speichern und Export, bis ein neuer Entwurf berechnet wurde.

Das Ma�blatt und das Innenaufbau-Blatt wachsen bei vielen Bauteilen mit, damit keine Tabellenzeilen abgeschnitten werden. Der Innenschnitt zeigt jetzt auch Treiber, Port und �ffnung in der Trennwand. Die PDF-Fertigungsunterlagen enthalten eigene Einzelteilseiten; Strebenpositionen und isobarische Koppelkammer folgen den berechneten Tiefenpositionen.

Sechs Geh�usearten sind berechenbar: geschlossen, Bassreflex, Passivmembran, Bandpass 4. Ordnung sowie isobarisch geschlossen und isobarisch Bassreflex. Weitere Typen bleiben sichtbar als �in Entwicklung� und sind nicht ausw�hlbar. F�r isobarische Entw�rfe werden zwei identische Chassis in gleicher Bewegungsrichtung, eine luftdichte Koppelkammer und Reihen- oder Parallelschaltung angenommen. Das ideale Kleinsignalmodell ber�cksichtigt die endliche Luftnachgiebigkeit und Verluste der Koppelkammer noch nicht; vor dem Bau Messung und Polung pr�fen.

Das neue Innenaufbau-Ma�blatt zeigt Tiefenpositionen von Streben, Kammern und Koppelring, Fenster�ffnungen, Portma�e und die Volumenbilanz. Ein Ringprofil-DXF und die Koppelrohr-Spezifikation werden mit exportiert. Geometriefehler wie zu geringe Tandemtiefe oder Kollisionen der Koppelkammer blockieren den Fertigungsexport.

Die Bibliothek enth�lt Herstellerdaten f�r Dayton Audio, Visaton und Scan-Speak sowie gekennzeichnete synthetische TESTDATEN. Jeder Herstellerdatensatz besitzt Quelle und Abrufdatum. Nicht ver�ffentlichte Ma�e und Werte bleiben leer; solche Treiber scheiden aus dem automatischen Entwurf aus, bis sie vervollst�ndigt werden. Frequenzgang- und Impedanzmessungen f�r die realen Treiber sind nicht eingebunden. Eigene JSON-/CSV-Daten k�nnen lokal importiert werden.

## Entwicklung

Aus dem Quellcode: `python -m venv .venv`, `.venv\Scripts\python -m pip install -e ".[dev]"`, `.venv\Scripts\python -m lautsprecher_konstruktion.app`.

Tests: `.venv\Scripts\python -m pytest --basetemp .test_run -p no:cacheprovider` und `.venv\Scripts\python -m ruff check src tests`. Der lokale Windows-Build l�uft �ber `powershell -ExecutionPolicy Bypass -File scripts/build_windows.ps1`.

## Grenzen

Die Geh�usemodelle sind lineare Kleinsignal-N�herungen ohne umfassenden Abgleich mit realen Messungen. Portkompression, thermische Effekte, Baffle Step, Raum, gefaltete Ports, vollst�ndige 3D-Kollisionen und Bauteiltoleranzen fehlen. Ein E12-Weichenvorschlag ist ein elektrischer Startwert. Alle Herstellerangaben, Ma�e und Bohrbilder vor dem Zuschnitt am echten Chassis pr�fen.

Weitere Details: `docs/USER_MANUAL.md`, `docs/ARCHITECTURE.md`, `docs/MAINTENANCE.md` und `BUILD_REPORT_V-02.02.00.md`.
