"""First-class "not feasible" state: main reason with numbers and one-click changes that were verified."""
from __future__ import annotations

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout, QWidget

from lautsprecher_konstruktion.library.store import ComponentLibrary
from lautsprecher_konstruktion.presentation import de
from lautsprecher_konstruktion.services.automatic import (
    AutomaticDesignRequest,
    AutomaticDesignResult,
    Diagnostic,
)
from lautsprecher_konstruktion.services.relaxation import Relaxation, find_relaxations

FIELD_UNITS = {"mm": 0, "l": 0, "Hz": 0, "dB": 0, "€": 0}


def _number(value: float, unit: str) -> str:
    return f"{de(value)} {unit}" if unit in FIELD_UNITS else f"{value:g} {unit}"


def describe(item: Diagnostic) -> tuple[str, str]:
    """(requested, reached) phrases with the right wording per constraint kind."""
    available, needed = _number(item.available, item.unit), _number(item.needed, item.unit)
    return {
        "depth": (f"verfügbar {available}", f"benötigt {needed}"),
        "outer_l": (f"verfügbar {available}", f"benötigt {needed}"),
        "budget": (f"Budget {available}", f"benötigt {needed}"),
        "f3": (f"gewünscht {available}", f"erreichbar {needed}"),
        "spl": (f"gewünscht {available}", f"erreichbar {needed}"),
    }.get(item.key, (f"verfügbar {available}", f"benötigt {needed}"))


class RelaxationWorker(QThread):
    """Runs the verified combined-change search off the UI thread (each proposal is a full design run)."""

    found = Signal(object)
    failed = Signal(str)

    def __init__(self, request: AutomaticDesignRequest, library: ComponentLibrary, result: AutomaticDesignResult) -> None:
        super().__init__()
        self.request, self.library, self.result = request, library, result

    def run(self) -> None:
        try:
            self.found.emit(find_relaxations(self.request, self.library, self.result))
        except Exception as exc:  # noqa: BLE001 - report worker failure through Qt signal
            self.failed.emit(str(exc))


class DiagnosticCard(QFrame):
    """Shows why no design exists and offers changes of the request inputs.

    ``apply`` is emitted with (field, suggested value); the window sets the input and recalculates.
    """

    apply = Signal(str, float)
    applyMany = Signal(object)  # list[(field, value)] of one verified combined proposal
    searchRequested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("diagnosticCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(10)
        self.title = QLabel("Dieser Entwurf ist mit den aktuellen Grenzen nicht möglich.")
        self.title.setObjectName("pageTitle")
        self.title.setWordWrap(True)
        layout.addWidget(self.title)
        self.main = QLabel()
        self.main.setObjectName("diagnosticMain")
        self.main.setWordWrap(True)
        layout.addWidget(self.main)
        self.change_heading = QLabel("Was du ändern kannst")
        self.change_heading.setObjectName("eyebrow")
        layout.addWidget(self.change_heading)
        self._buttons_box = QWidget()
        self._buttons = QVBoxLayout(self._buttons_box)
        self._buttons.setContentsMargins(0, 0, 0, 0)
        self._buttons.setSpacing(6)
        layout.addWidget(self._buttons_box)
        self.search_button = QPushButton("Kombinierte Änderungen prüfen")
        self.search_button.setObjectName("suggestion")
        self.search_button.setToolTip("Sucht kleine Änderungen mehrerer Vorgaben und prüft jede mit dem echten Entwurfsrechner.")
        self.search_button.clicked.connect(self.searchRequested.emit)
        layout.addWidget(self.search_button)
        self.search_note = QLabel()
        self.search_note.setObjectName("hint")
        self.search_note.setWordWrap(True)
        layout.addWidget(self.search_note)
        self.relax_buttons: list[QPushButton] = []
        self._relax_box = QWidget()
        self._relax_layout = QVBoxLayout(self._relax_box)
        self._relax_layout.setContentsMargins(0, 0, 0, 0)
        self._relax_layout.setSpacing(6)
        layout.addWidget(self._relax_box)
        self.more_heading = QLabel("Weitere Gründe")
        self.more_heading.setObjectName("eyebrow")
        layout.addWidget(self.more_heading)
        self.more = QLabel()
        self.more.setObjectName("hint")
        self.more.setWordWrap(True)
        layout.addWidget(self.more)
        layout.addStretch(1)
        self.action_buttons: list[QPushButton] = []
        self._plain: list[QLabel] = []

    def show_result(self, result: AutomaticDesignResult) -> None:
        for widget in (*self.action_buttons, *self._plain):
            widget.setParent(None)
            widget.deleteLater()
        self.action_buttons = []
        self._plain = []
        self._clear_relaxations()
        self.search_button.setVisible(bool(result.soft_misses))
        self.search_button.setEnabled(True)
        self.search_note.setText("")
        diagnostics = result.diagnostics
        if diagnostics:
            first = diagnostics[0]
            wanted, reached = describe(first)
            self.main.setText(f"Hauptgrund: {first.title}\n→ {wanted}\n→ {reached}")
            for item in diagnostics:
                if item.field is None or item.suggested is None:
                    continue
                button = QPushButton("+ " + item.action)
                button.setObjectName("suggestion")
                wanted, reached = describe(item)
                button.setToolTip(f"{item.title}: {wanted}, {reached}. Die Änderung wird eingetragen und neu berechnet.")
                button.clicked.connect(lambda _c=False, f=item.field, v=item.suggested: self.apply.emit(f, v))
                self._buttons.addWidget(button)
                self.action_buttons.append(button)
            self.change_heading.setVisible(bool(self.action_buttons))
        else:
            self.main.setText("Hauptgrund: Mehrere Vorgaben schließen sich gleichzeitig aus – keine einzelne "
                              "Änderung macht einen Entwurf möglich.")
            self.change_heading.setVisible(bool(result.suggested_constraint_changes))
        if not self.action_buttons:
            for text in result.suggested_constraint_changes:
                label = QLabel("• " + text)
                label.setWordWrap(True)
                self._buttons.addWidget(label)
                self._plain.append(label)
        reasons = [r for r in result.rejection_reasons if r]
        self.more.setText("\n".join("• " + reason for reason in reasons) or "–")
        self.more_heading.setVisible(bool(reasons))
        self.more.setVisible(bool(reasons))

    def _clear_relaxations(self) -> None:
        for button in self.relax_buttons:
            button.setParent(None)
            button.deleteLater()
        self.relax_buttons = []

    def searching(self) -> None:
        self.search_button.setEnabled(False)
        self.search_note.setText("Kombinierte Änderungen werden mit dem Entwurfsrechner geprüft …")

    def show_relaxations(self, items: tuple[Relaxation, ...]) -> None:
        self._clear_relaxations()
        self.search_button.setEnabled(True)
        if not items:
            self.search_note.setText("Auch kombinierte kleine Änderungen machen keinen Entwurf möglich. "
                                     "Bauraum, Klangprofil oder Komponenten müssten sich deutlich ändern.")
            return
        self.search_note.setText("Geprüfte Kombinationen (kleinste Änderung zuerst):")
        for item in items:
            button = QPushButton("+ " + item.text())
            button.setObjectName("suggestion")
            button.setToolTip("Alle genannten Änderungen werden eingetragen und neu berechnet.")
            pairs = [(c.field, c.new) for c in item.changes]
            button.clicked.connect(lambda _c=False, p=pairs: self.applyMany.emit(p))
            self._relax_layout.addWidget(button)
            self.relax_buttons.append(button)

    def buttons_text(self) -> list[str]:
        return [b.text() for b in self.action_buttons]
