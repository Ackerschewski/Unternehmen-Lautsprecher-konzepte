"""'Modellvertrauen': every solver with its trust level, sources, limits and reference cases (expert view)."""
from __future__ import annotations

from html import escape

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from lautsprecher_konstruktion.enclosure.registry import registry
from lautsprecher_konstruktion.validation.cases import build_cases
from lautsprecher_konstruktion.validation.reference import (
    ReferenceCase,
    ValidationRun,
    render_diff,
    run_cases,
)
from lautsprecher_konstruktion.validation.solvers import SOLVER_DESCRIPTORS
from lautsprecher_konstruktion.validation.trust import SolverDescriptor, TrustLevel

KIND_LABELS = {"literature": "Literatur", "analytic": "geschlossene Formel", "limit": "Grenzfall",
               "consistency": "Konsistenz", "prototype": "Prototyp"}


def solver_detail_html(descriptor: SolverDescriptor, cases: tuple[ReferenceCase, ...], run: ValidationRun | None) -> str:
    """Detail text of one solver: what it computes, where it comes from, what it cannot do, and its reference cases."""
    mine = [c for c in cases if c.solver_id == descriptor.solver_id]
    rows = []
    for case in mine:
        state = "nicht geprüft" if run is None else ("bestanden" if run.case_passed(case.case_id) else "FEHLGESCHLAGEN")
        rows.append(f"<li><b>{escape(case.title)}</b> · {KIND_LABELS.get(case.kind.value, case.kind.value)} · {state}</li>")
    earned = None if run is None else run.earned_trust(descriptor.solver_id)
    earned_line = ("" if earned is None else
                   f"<p>Belegt durch bestandene Fälle: <b>{escape(earned.label_de)}</b>"
                   f"{' (vergeben wird weniger, weil die Näherungen unten gelten)' if earned > descriptor.trust else ''}.</p>")
    limits = "".join(f"<li><b>{escape(item.scope)}:</b> {escape(item.text)}</li>" for item in descriptor.limitations)
    sources = "".join(f"<li>{escape(item)}</li>" for item in descriptor.sources)
    return (f"<h2>{escape(descriptor.family)}</h2><p><b>{escape(descriptor.trust.label_de)}</b> · Modellversion {escape(descriptor.model_version)}<br>"
            f"{escape(descriptor.trust.meaning_de)}</p>{earned_line}<p>{escape(descriptor.equations)}</p>"
            f"<h3>Quellen</h3><ul>{sources}</ul><h3>Bekannte Grenzen</h3><ul>{limits}</ul>"
            f"<h3>Referenzfälle</h3><ul>{''.join(rows) or '<li>keine</li>'}</ul>"
            f"<h3>Festlegungen</h3><p>{escape(descriptor.conventions)}</p>")


class _Worker(QThread):
    done = Signal(object)

    def run(self) -> None:
        self.done.emit(run_cases(build_cases()))


class TrustDialog(QDialog):
    """Static information is shown at once; the reference cases run only on request (never on repaint)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Modellvertrauen")
        self.resize(1000, 640)
        self.cases = build_cases()
        self.run: ValidationRun | None = None
        self._worker: _Worker | None = None
        layout = QVBoxLayout(self)
        intro = QLabel("Wie weit darf man den Berechnungen jedes Gehäusetyps trauen? Die Stufe wird nie höher vergeben, "
                       "als die bestandenen Referenzfälle belegen. Ein Prototypvergleich ist eine eigene, höhere Stufe.")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        body = QHBoxLayout()
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Gehäusetyp", "Vertrauen", "Fälle", "Prüfstand"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in (1, 2, 3):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        body.addWidget(self.table, 3)
        self.detail = QTextBrowser()
        body.addWidget(self.detail, 2)
        layout.addLayout(body, 1)
        row = QHBoxLayout()
        self.run_button = QPushButton("Referenzfälle jetzt prüfen")
        self.run_button.clicked.connect(self.start_run)
        self.status = QLabel("")
        self.status.setWordWrap(True)
        row.addWidget(self.run_button)
        row.addWidget(self.status, 1)
        close = QPushButton("Schließen")
        close.clicked.connect(self.accept)
        row.addWidget(close)
        layout.addLayout(row)
        self.table.itemSelectionChanged.connect(self._show_detail)
        self._fill()
        self.table.selectRow(0)

    def _fill(self) -> None:
        self.table.setRowCount(0)
        for entry in registry.supported():
            descriptor = SOLVER_DESCRIPTORS[entry.id]
            mine = [c for c in self.cases if c.solver_id == entry.id]
            row = self.table.rowCount()
            self.table.insertRow(row)
            state = "nicht geprüft"
            if self.run is not None:
                passed = sum(1 for c in mine if self.run.case_passed(c.case_id))
                state = f"{passed}/{len(mine)} bestanden"
            for column, text in enumerate((entry.label, descriptor.trust.label_de, str(len(mine)), state)):
                item = QTableWidgetItem(text)
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, entry.id)
                if column == 1 and descriptor.trust is TrustLevel.EXPERIMENTAL:
                    item.setToolTip(descriptor.trust.meaning_de)
                    item.setText("⚠ " + text)
                self.table.setItem(row, column, item)

    def selected_solver(self) -> str | None:
        rows = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        return None if not rows else str(self.table.item(rows[0].row(), 0).data(Qt.ItemDataRole.UserRole))

    def _show_detail(self) -> None:
        key = self.selected_solver()
        if key:
            self.detail.setHtml(solver_detail_html(SOLVER_DESCRIPTORS[key], self.cases, self.run))

    def start_run(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            return
        self.run_button.setEnabled(False)
        self.status.setText("Referenzfälle werden gerechnet …")
        self._worker = _Worker()
        self._worker.done.connect(self._finished)
        self._worker.start()

    def _finished(self, run: ValidationRun) -> None:
        self.run = run
        keep = self.selected_solver()
        self._fill()
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).data(Qt.ItemDataRole.UserRole) == keep:
                self.table.selectRow(row)
        self.run_button.setEnabled(True)
        self.status.setText(render_diff(run) if not run.ok else "Alle Referenzfälle bestanden.")
        self._show_detail()
