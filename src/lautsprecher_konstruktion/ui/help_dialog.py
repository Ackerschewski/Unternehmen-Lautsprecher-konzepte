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

1. **Start wählen:** Klassisch über Bauart/Bauraum/Klangprofil oder direkt **über Zielkurve**.
2. **Planen:** Maximalmaße festlegen; die proportionale Vorschau zeigt den verfügbaren Bauraum.
3. **Entwurf erstellen:** Das Programm prüft Chassis, Gehäuse, Geometrie und technische Grenzen.
4. **Varianten vergleichen:** Bis zu vier entscheidungsorientierte Kandidaten – Empfehlung, kompakter,
   mehr Tiefbass und, wenn sinnvoll bepreist, günstiger.
5. **Klang & Simulation:** Zielkurve bearbeiten, Presets oder parametrische Zielbänder verwenden und
   berechnete Varianten/Einflussgrenzen vergleichen.
6. **Zeichnungen:** Im **Lesemodus** Front, Seite und Schnitt groß prüfen; der **Druckblattmodus**
   zeigt das spätere Seitenlayout.
7. **Fertigung:** Stückliste, Zuschnitt und Export befinden sich gemeinsam im Bereich *Fertigung*.
8. **Bauen und messen:** Impedanz und Frequenzgang messen und unter
   *Werkzeuge → Prototyp vergleichen* gegen die Simulation legen.

## Zielkurve und Datenqualität

- Die Zielkurve ist ein **Sollwert**, kein gemessener Frequenzgang.
- Ohne FRD-/Messdaten werden Mittel- und Hochtonwerte nicht erfunden.
- Sind FRD/ZMA-Daten vorhanden, kann die vorhandene Weichensimulation den Summenfrequenzgang
  bis 20 kHz für den Vergleich verwenden.
- Die Variantenhülle und Einflusskarten basieren auf tatsächlich berechneten Kandidaten.
- DSP-Hubreserve wird nur dort angegeben, wo Hubdaten und Xmax vorliegen.

## Wichtige Hinweise

- Alle Gehäusemodelle sind **lineare Kleinsignal-Näherungen**. Sie ersetzen keine Messung am Prototyp.
- Herstellerdaten, Maße und Bohrbilder vor dem Zuschnitt am echten Chassis prüfen.
- Preise sind datierte Momentaufnahmen, kein Angebot. Versand und Arbeitszeit sind nicht enthalten.
- Daten ohne Quelle werden nie ergänzt; **TESTDATEN** sind nur zur Funktionsprüfung.
- Ein Export wird gesperrt, wenn die Geometrie nicht fertigungstauglich ist.

## Tastenkürzel

`Strg+O` Projekt laden · `Strg+S` speichern · `Strg+E` exportieren ·
`Strg+D` Zeichnung groß anzeigen · `Strg+Q` beenden
"""


def about_text() -> str:
    return f"""\
# Lautsprecher Konstruktion {REVISION}

Konstruktionsassistent für Lautsprecherentwürfe mit Berechnung, Zeichnungen, Zuschnitt und Stückliste.

| | |
|---|---|
| Python | {sys.version.split()[0]} ({platform.system()}) |
| PySide6 | {pyside_version} |
| Marke | ACK Studio |
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
