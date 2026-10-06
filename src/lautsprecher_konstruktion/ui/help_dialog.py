"""Quick start and about dialog."""
from __future__ import annotations

import platform
import sys

from PySide6 import __version__ as pyside_version
from PySide6.QtWidgets import QDialog, QPushButton, QTabWidget, QTextBrowser, QVBoxLayout, QWidget

from lautsprecher_konstruktion import REVISION
from lautsprecher_konstruktion.appdata import log_file, user_data_dir

QUICK_START = """\
# Kurzanleitung

1. **Vorgaben eingeben:** Typ, größtes Außenmaß, Klangprofil und optional Budget.
2. **Entwurf erstellen:** Das Programm prüft Chassis und Gehäuse und zeigt bis zu drei Varianten.
3. **Variante prüfen:** Gesamtzeichnung, Maßblatt, Innenaufbau, Einzelteilplan, Simulation, Stückliste und *Zuschnitt*.
4. **Exportieren:** Zeichnungen (SVG/DXF), PDF, Stückliste, Zuschnittplan und Bauanleitung liegen im Paket.
5. **Bauen und messen:** Impedanz und Frequenzgang messen und unter *Werkzeuge → Prototyp vergleichen* gegen die Simulation legen.

## Wichtige Hinweise

- Alle Gehäusemodelle sind **lineare Kleinsignal-Näherungen**. Sie ersetzen keine Messung am Prototyp.
- Herstellerdaten, Maße und Bohrbilder vor dem Zuschnitt am echten Chassis prüfen.
- Preise sind datierte Momentaufnahmen, kein Angebot. Versand und Arbeitszeit sind nicht enthalten.
- Daten ohne Quelle werden nie ergänzt; **TESTDATEN** sind nur zur Funktionsprüfung.
- Ein Export wird gesperrt, wenn die Geometrie nicht fertigungstauglich ist.

## Tastenkürzel

`Strg+O` Projekt laden · `Strg+S` speichern · `Strg+E` exportieren · `Strg+Q` beenden
"""


def about_text() -> str:
    return f"""\
# Lautsprecher Konstruktion {REVISION}

Konstruktionsassistent für Lautsprecherentwürfe mit Berechnung, Zeichnungen, Zuschnitt und Stückliste.

| | |
|---|---|
| Python | {sys.version.split()[0]} ({platform.system()}) |
| PySide6 | {pyside_version} |
| Marke | Ackerschewski_code · Design: ACK Studio |
| Datenordner | `{user_data_dir()}` |
| Protokolldatei | `{log_file()}` |

Der Entwurf ist eine **Planungshilfe**. Für Bau und Betrieb trägt der Anwender die Verantwortung;
Messungen am Prototyp und die Datenblätter der Hersteller haben Vorrang vor allen berechneten Werten.
Verwendete Bibliotheken: PySide6, NumPy, SciPy, Matplotlib, Pydantic, ReportLab; deren Lizenzen gelten jeweils.
"""


class HelpDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Hilfe")
        self.resize(760, 640)
        tabs = QTabWidget()
        for title, text in (("Kurzanleitung", QUICK_START), ("Über", about_text())):
            browser = QTextBrowser()
            browser.setOpenExternalLinks(True)
            browser.setMarkdown(text)
            tabs.addTab(browser, title)
        close = QPushButton("Schließen")
        close.clicked.connect(self.accept)
        layout = QVBoxLayout(self)
        layout.addWidget(tabs, 1)
        layout.addWidget(close)
