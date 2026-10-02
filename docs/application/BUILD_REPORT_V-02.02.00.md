# Buildbericht V-02.02.00

## Inhalt

- 84 datierte Thomann-Katalogpositionen; acht FaitalPRO-Chassis mit Herstellerdaten f�r die Konstruktion.
- Zehn weitere Dayton-Audio-, Scan-Speak- und Visaton-Chassis mit datierten Euro-Preisen und Produktlinks.
- Gesamtbudget im ersten Konfigurationsschritt f�r ein Geh�use. Die Materialst�ckliste enth�lt Chassis, Platten, Streben, Port/Passivmembran, Weiche, Terminal, D�mpfung, Kabel, Leim und Schrauben. Der Budgetbedarf enth�lt 15 % Reserve.
- Jeder St�cklistenposten hat einen Euro-Preis oder ist ausdr�cklich als fehlend markiert. H�ndlerpreise, Materialreferenzen und Planpreise sind getrennt. Ein Entwurf mit fehlendem Chassispreis besteht eine gesetzte Budgetgrenze nicht.
- Neues Gesamtblatt als SVG mit Vorder- und R�ckansicht, Seitenschnitt, Einbauma�en, dokumentierten Lochkreisen, einzelnen Bohrkoordinaten und Zuschnitt. Fehlende Hersteller-Lochbilder werden nicht erg�nzt.

## Pr�fung

- `pytest`: 56 F�lle bestanden.
- `ruff check src tests`: bestanden.
- PyInstaller Windows-Build mit Offscreen-Start: bestanden.
- Paketexport und SVG-Sichtpr�fung: bestanden; Gesamtzeichnung, Innenaufbau und Einzelteilblatt als PNG gerendert.
- Windows ZIP: etwa 102,6 MB; Quellcode ZIP: etwa 244 kB.

## Grenzen

Die sechs bisher unterst�tzten Geh�usearten sind weiterhin berechenbar. Die 23 weiteren registrierten Konzepte sind technisch nicht vollst�ndig; eine Fertigungsfreigabe erfordert eigene Akustikmodelle und herstellbare Geometrie. Materialkosten sind Planwerte und enthalten keinen Versand oder Arbeitslohn. Nicht ver�ffentlichte Bohrma�e m�ssen am realen Bauteil gemessen werden. Der Windows-Build ist ein lokaler Teststand, keine abschlie�end freigegebene Produktversion.
