"""Compare the calculated design with FRD/ZMA measurements of a built prototype."""
from __future__ import annotations

from pathlib import Path

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from pydantic import ValidationError
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from lautsprecher_konstruktion.appdata import get_logger
from lautsprecher_konstruktion.crossover.measurements import load_frd, load_zma
from lautsprecher_konstruktion.services.design import DesignBundle
from lautsprecher_konstruktion.validation import (
    PrototypeReport,
    compare_prototype,
    render_report_markdown,
)

LOG = get_logger("prototype")


class PrototypeDialog(QDialog):
    def __init__(self, bundle: DesignBundle, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Prototypvergleich – Simulation und Messung")
        self.resize(1100, 820)
        self.bundle = bundle
        self.report: PrototypeReport | None = None

        form = QFormLayout()
        self.frd_path = QLineEdit()
        self.frd_path.setPlaceholderText("Frequenzgang (.frd) – Nahfeld oder gefenstert")
        self.zma_path = QLineEdit()
        self.zma_path.setPlaceholderText("Impedanz (.zma) – für Abstimmfrequenz und Portkorrektur")
        for label, field in (("FRD", self.frd_path), ("ZMA", self.zma_path)):
            row = QHBoxLayout()
            row.addWidget(field, 1)
            button = QPushButton("Wählen…")
            button.clicked.connect(lambda _=False, edit=field, kind=label: self._browse(edit, kind))
            row.addWidget(button)
            holder = QWidget()
            holder.setLayout(row)
            row.setContentsMargins(0, 0, 0, 0)
            form.addRow(label, holder)
        self.band_low = QDoubleSpinBox()
        self.band_low.setRange(5, 2000)
        self.band_low.setValue(20)
        self.band_low.setSuffix(" Hz")
        self.band_high = QDoubleSpinBox()
        self.band_high.setRange(10, 20000)
        self.band_high.setValue(300)
        self.band_high.setSuffix(" Hz")
        band = QHBoxLayout()
        band.addWidget(self.band_low)
        band.addWidget(self.band_high)
        holder = QWidget()
        holder.setLayout(band)
        band.setContentsMargins(0, 0, 0, 0)
        form.addRow("Vergleichsband", holder)
        self.align = QCheckBox("Pegelversatz angleichen (empfohlen für Nahfeld-Messungen)")
        self.align.setChecked(True)
        form.addRow(self.align)

        self.compare_button = QPushButton("Vergleichen")
        self.compare_button.clicked.connect(self.compare)
        self.save_button = QPushButton("Bericht speichern…")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_report)
        buttons = QHBoxLayout()
        buttons.addWidget(self.compare_button)
        buttons.addWidget(self.save_button)
        buttons.addStretch()

        self.figure = Figure(figsize=(8, 4.5), layout="constrained")
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.text = QTextBrowser()
        self.text.setMarkdown("Messdateien wählen und **Vergleichen** klicken. Die Messung bleibt unverändert; "
                              "das Projekt wird nicht geändert.")
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(buttons)
        layout.addWidget(self.canvas, 2)
        layout.addWidget(self.text, 1)

    def _browse(self, field: QLineEdit, kind: str) -> None:
        pattern = "Frequenzgang (*.frd *.txt *.csv)" if kind == "FRD" else "Impedanz (*.zma *.txt *.csv)"
        filename, _ = QFileDialog.getOpenFileName(self, f"{kind}-Messung wählen", "", pattern)
        if filename:
            field.setText(filename)

    def compare(self) -> PrototypeReport | None:
        frd_file, zma_file = self.frd_path.text().strip(), self.zma_path.text().strip()
        if not frd_file and not zma_file:
            QMessageBox.information(self, "Messung fehlt", "Bitte mindestens eine FRD- oder ZMA-Datei wählen.")
            return None
        try:
            self.report = compare_prototype(
                self.bundle, frd=load_frd(frd_file) if frd_file else None,
                zma=load_zma(zma_file) if zma_file else None,
                band_hz=(self.band_low.value(), self.band_high.value()), align_level=self.align.isChecked())
        except (OSError, ValidationError, ValueError) as exc:
            LOG.warning("Prototypvergleich fehlgeschlagen: %s", exc)
            QMessageBox.warning(self, "Vergleich nicht möglich", str(exc))
            return None
        self.text.setMarkdown(render_report_markdown(self.report))
        self._plot(self.report)
        self.save_button.setEnabled(True)
        return self.report

    def _plot(self, report: PrototypeReport) -> None:
        self.figure.clear()
        panels = [p for p in (report.frequency, report.impedance) if p is not None]
        for index, item in enumerate(panels, start=1):
            axis = self.figure.add_subplot(1, len(panels), index)
            if item is report.frequency:
                axis.semilogx(item.grid_hz, item.sim_db, label="Simulation", linewidth=2)
                axis.semilogx(item.grid_hz, item.meas_db, label="Messung (angeglichen)", linewidth=1.5)
                axis.set_title(f"Frequenzgang · RMS {item.rms_db:.2f} dB")
                axis.set_ylabel("Pegel [dB]")
            else:
                if item.sim_ohm is not None:
                    axis.semilogx(item.grid_hz, item.sim_ohm, label="Simulation", linewidth=2)
                if item.meas_ohm is not None:
                    axis.semilogx(item.grid_hz, item.meas_ohm, label="Messung", linewidth=1.5)
                axis.set_title(item.marker_name)
                axis.set_ylabel("|Z| [Ohm]")
            axis.set_xlabel("Frequenz [Hz]")
            axis.grid(True, which="both", alpha=0.25)
            axis.legend()
        self.canvas.draw_idle()

    def save_report(self) -> None:
        if self.report is None:
            return
        filename, _ = QFileDialog.getSaveFileName(self, "Bericht speichern", "prototypvergleich.md",
                                                  "Markdown (*.md)")
        if filename:
            try:
                Path(filename).write_text(render_report_markdown(self.report), encoding="utf-8")
            except OSError as exc:
                QMessageBox.warning(self, "Speichern fehlgeschlagen", str(exc))
