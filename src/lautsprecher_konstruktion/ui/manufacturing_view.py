"""Manufacturing workspace pieces: summary cards on top and the export format list with honest status."""
from __future__ import annotations

from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget

from lautsprecher_konstruktion.export.cutting import CuttingPlan
from lautsprecher_konstruktion.export.summary import summarize
from lautsprecher_konstruktion.services.automatic import SpeakerDesign
from lautsprecher_konstruktion.ui.result_hero import KpiGrid

SUMMARY_KEYS = ("Bekannte Kosten", "Geschätzte Kosten", "Fehlende Preise", "Materialplatten", "Gehäusegewicht", "Bauteile")

# (format, what it contains, status). STEP is announced, not offered.
EXPORT_FORMATS: tuple[tuple[str, str, str], ...] = (
    ("PDF", "Fertigungsunterlagen, Zuschnittplan und Bauanleitung zum Ausdrucken", "wird erzeugt"),
    ("DXF", "Frontplatte, Rück-/Trennwand und Platten-Schnittpläne für CNC oder Laser", "wird erzeugt"),
    ("SVG", "Alle Zeichnungen (Front, Seite, Schnitt, Innenaufbau, Einzelteile) als Vektorgrafik", "wird erzeugt"),
    ("CSV", "Stückliste, Zuschnittliste, Weichen-Stückliste und Simulationskurven", "wird erzeugt"),
    ("JSON", "Das vollständige Projekt zum erneuten Laden und Nachvollziehen", "wird erzeugt"),
    ("STEP", "3D-Austausch für CAD/CAM", "noch nicht verfügbar"),
)


class ManufacturingSummaryView(KpiGrid):
    def __init__(self) -> None:
        super().__init__(SUMMARY_KEYS, columns=3)

    def update_from(self, design: SpeakerDesign | None, plan: CuttingPlan | None) -> None:
        if design is None:
            self.clear()
            return
        for label, value, hint in summarize(design, plan).rows():
            self.set_value(label, value, hint)


class ExportFormatList(QWidget):
    """One row per output format with a short explanation and whether it is produced."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.rows: list[tuple[QLabel, QLabel, QLabel]] = []
        frame = QFrame()
        frame.setObjectName("kpiCard")
        grid = QGridLayout(frame)
        grid.setContentsMargins(12, 8, 12, 8)
        grid.setHorizontalSpacing(16)
        for row, (name, text, status) in enumerate(EXPORT_FORMATS):
            title, info, state = QLabel(name), QLabel(text), QLabel(("✓ " if status == "wird erzeugt" else "○ ") + status)
            title.setObjectName("kpiValue")
            info.setWordWrap(True)
            state.setProperty("role", "ok" if status == "wird erzeugt" else "muted")
            grid.addWidget(title, row, 0)
            grid.addWidget(info, row, 1)
            grid.addWidget(state, row, 2)
            grid.setColumnStretch(1, 1)
            self.rows.append((title, info, state))
        layout.addWidget(frame)
