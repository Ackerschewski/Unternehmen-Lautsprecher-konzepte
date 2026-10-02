# Umsetzungsplan V-02.03.00

## Ziel

Ein Budgetentwurf soll verfügbare Chassis-Kombinationen tatsächlich vergleichen. Fertigungsunterlagen dürfen keine Schraublochdurchmesser aus einem stillen Standardwert ableiten.

## Arbeitsschritte und Abnahme

1. **Bohrdaten absichern:** Lochkreis, Anzahl und Bohrdurchmesser getrennt behandeln. Automatisch platzierte Chassis übernehmen veröffentlichte Maße aus der Bibliothek. Fehlt ein Maß, bleiben Bohrkoordinaten und DXF-Bohrungen offen und die Zeichnungen benennen das fehlende Maß. Manuell eingegebene Bohrungen bleiben möglich.
2. **Budgetsuche verbessern:** Für einen Tieftöner mehrere technisch kompatible Hochtöner prüfen. Bei gesetztem Budget zuerst Chassis mit Euro-Preis berücksichtigen und günstige passende Alternativen nicht durch die erste Überlappung ausschließen. Der vollständige Materialpreis inklusive Reserve entscheidet über die Zulässigkeit.
3. **Rückmeldung verbessern:** Im Variantenvergleich den Abstand zum Budget anzeigen; Preisarten und offene Fertigungsmaße erklären. Nicht fertig modellierte Gehäuse bleiben ausdrücklich in Entwicklung.
4. **Prüfen und liefern:** Gezielte Regressionstests, vollständiger Pytest-/Ruff-Lauf, Windows-Build mit Startprüfung, neues Testpaket und Upload in den bestehenden Entwurfs-PR.

## Weiterer Ausbau

Die 23 bisher geplanten Gehäuseformen werden nach physikalischer Familie umgesetzt: zuerst 6.-Ordnung-Bandpass mit zwei gekoppelten Kammern, dann Transmission-Line-Geometrien, danach Hornfamilien und Kardioid/Dipol. Jeder Typ benötigt ein passendes Simulationsmodell, herstellbare Innengeometrie, Volumenbilanz, Kollisionsprüfung und Fertigungszeichnung, bevor er als unterstützt erscheint.
