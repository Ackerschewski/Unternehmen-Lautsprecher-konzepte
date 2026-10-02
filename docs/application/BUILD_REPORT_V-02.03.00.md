# Buildbericht V-02.03.00

## Änderungen

- Budgetsuche prüft kompatible Hochtöner als verschiedene Kandidaten. Bei Budgetvorgabe werden fehlende Chassispreise ausgeschlossen und die vollständige Materialsumme samt 15 % Reserve geprüft.
- Variantenvergleich zeigt gewählte Chassis und freien Budgetbetrag.
- Bohrkoordinaten werden nur bei dokumentiertem Lochkreis, Lochanzahl **und** Bohrdurchmesser exportiert. Unvollständige Lochbilder bleiben offen; bekannte Teilmaße werden benannt.
- Der priorisierte Umsetzungsplan steht in `docs/PLAN_V-02.03.00.md`.

## Prüfung

- Pytest: 58 Fälle bestanden.
- Ruff: bestanden.
- Windows-PyInstaller-Build und Offscreen-Startprüfung: bestanden.
- Paketexport und SVG-Vorschau: nach Durchführung ergänzen.

## Grenzen

Sechs Gehäusetypen sind berechenbar; die 23 weiteren registrierten Konzepte bleiben in Entwicklung. Holz-, Weichen- und Montagekosten enthalten Planwerte. Der Testbuild benötigt vor einer Produktfreigabe eine Prüfung durch den Nutzer am Windows-Rechner und am realen Chassis.
