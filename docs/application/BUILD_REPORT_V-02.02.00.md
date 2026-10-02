# Buildbericht V-02.02.00

## Inhalt

- 84 datierte Thomann-Katalogpositionen; acht FaitalPRO-Chassis mit Herstellerdaten für die Konstruktion.
- Gesamtbudget im ersten Konfigurationsschritt für ein Gehäuse. Die Materialstückliste enthält Chassis, Platten, Streben, Port/Passivmembran, Weiche, Terminal, Dämpfung, Kabel, Leim und Schrauben. Der Budgetbedarf enthält 15 % Reserve.
- Jeder Stücklistenposten hat einen Euro-Preis oder ist ausdrücklich als fehlend markiert. Händlerpreise, Materialreferenzen und Planpreise sind getrennt. Ein Entwurf mit fehlendem Chassispreis besteht eine gesetzte Budgetgrenze nicht.
- Neues Gesamtblatt als SVG mit Vorder- und Rückansicht, Seitenschnitt, Einbaumaßen, dokumentierten Lochkreisen, einzelnen Bohrkoordinaten und Zuschnitt. Fehlende Hersteller-Lochbilder werden nicht ergänzt.

## Prüfung

- `pytest`: 55 Fälle bestanden.
- `ruff check src tests`: bestanden.
- PyInstaller Windows-Build mit Offscreen-Start: bestanden.
- Paketexport und SVG-Sichtprüfung: bestanden; Gesamtzeichnung, Innenaufbau und Einzelteilblatt als PNG gerendert.
- Windows ZIP: 102.599.959 Byte; Quellcode ZIP: 244.109 Byte.

## Grenzen

Die sechs bisher unterstützten Gehäusearten sind weiterhin berechenbar. Die 23 weiteren registrierten Konzepte sind technisch nicht vollständig; eine Fertigungsfreigabe erfordert eigene Akustikmodelle und herstellbare Geometrie. Materialkosten sind Planwerte und enthalten keinen Versand oder Arbeitslohn. Nicht veröffentlichte Bohrmaße müssen am realen Bauteil gemessen werden. Der Windows-Build ist ein lokaler Teststand, keine abschließend freigegebene Produktversion.
