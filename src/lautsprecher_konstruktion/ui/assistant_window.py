"""Default guided workflow; the existing editor remains the expert view."""
from __future__ import annotations

from html import escape
from pathlib import Path
from threading import Event

import matplotlib
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from pydantic import ValidationError
from PySide6.QtCore import QByteArray, Qt, QThread, QTimer, QUrl, Signal
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QDesktopServices,
    QFont,
    QGuiApplication,
    QKeySequence,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from lautsprecher_konstruktion import REVISION
from lautsprecher_konstruktion.acoustics.response import sealed_response_db
from lautsprecher_konstruktion.appdata import (
    Autosave,
    RecentProjects,
    Settings,
    configure_logging,
    get_logger,
    log_file,
)
from lautsprecher_konstruktion.drawings.dimension_svg import render_dimension_svg
from lautsprecher_konstruktion.drawings.internal_dimensions_svg import (
    render_internal_dimensions_svg,
)
from lautsprecher_konstruktion.drawings.master_sheet_svg import render_master_sheet_svg
from lautsprecher_konstruktion.drawings.panel_sheet_svg import (
    panel_sheet_surfaces,
    render_panel_sheet_svg,
)
from lautsprecher_konstruktion.enclosure.registry import registry
from lautsprecher_konstruktion.export.bom import build_bom, priced_subtotal
from lautsprecher_konstruktion.export.package import export_project_package
from lautsprecher_konstruktion.export.pricing import budget_cost
from lautsprecher_konstruktion.library.store import ComponentLibrary
from lautsprecher_konstruktion.optimization.profiles import PROFILES
from lautsprecher_konstruktion.project.models import SpeakerProject
from lautsprecher_konstruktion.services.automatic import (
    SPEAKER_TYPES,
    AutomaticDesignRequest,
    AutomaticDesignResult,
    SpeakerDesign,
    automatic_design,
)
from lautsprecher_konstruktion.services.design import DesignBundle, calculate_project
from lautsprecher_konstruktion.targets.curve import (
    derive_f3_target_hz,
    deviation,
)
from lautsprecher_konstruktion.ui.cabinet_preview import CabinetPreview
from lautsprecher_konstruktion.ui.collapsible import Collapsible
from lautsprecher_konstruktion.ui.cutting_panel import CuttingPanel
from lautsprecher_konstruktion.ui.help_dialog import HelpDialog
from lautsprecher_konstruktion.ui.library_dialog import LibraryDialog
from lautsprecher_konstruktion.ui.main_window import MainWindow
from lautsprecher_konstruktion.ui.motion import animate_value
from lautsprecher_konstruktion.ui.prototype_dialog import PrototypeDialog
from lautsprecher_konstruktion.ui.target_curve_panel import TargetCurvePanel
from lautsprecher_konstruktion.ui.theme import chart_rc, stylesheet
from lautsprecher_konstruktion.ui.tokens import DEFAULT_AREA, set_area, status_line
from lautsprecher_konstruktion.ui.tokens import theme as theme_tokens
from lautsprecher_konstruktion.ui.variant_cards import CardData, VariantCards
from lautsprecher_konstruktion.ui.zoom_svg import ZoomableSvgView

LOG = get_logger("ui")
AUTOSAVE_INTERVAL_MS = 60_000


class DesignWorker(QThread):
    progress = Signal(int)
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, request: AutomaticDesignRequest, library: ComponentLibrary) -> None:
        super().__init__()
        self.request = request
        self.library = library
        self.cancel_event = Event()

    def run(self) -> None:
        try:
            result = automatic_design(self.request, self.library,
                self.progress.emit, self.cancel_event.is_set)
            self.completed.emit(result)
        except Exception as exc:  # noqa: BLE001 - report worker failure through Qt signal
            self.failed.emit(str(exc))


def _spin(default: float, minimum: float, maximum: float, suffix: str,
          decimals: int = 0) -> QDoubleSpinBox:
    control = QDoubleSpinBox()
    control.setRange(minimum, maximum)
    control.setDecimals(decimals)
    control.setValue(default)
    control.setSuffix(suffix)
    control.setSingleStep(10 if decimals == 0 else 0.5)
    return control


class AssistantWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"Lautsprecher Konstruktion {REVISION}")
        screen = QGuiApplication.primaryScreen()
        available = screen.availableGeometry() if screen is not None else None
        self.setMinimumSize(980, 620)
        self.resize(min(1500, available.width() - 40) if available else 1500,
                    min(920, available.height() - 60) if available else 920)
        self.library = ComponentLibrary()
        self.designs: tuple[SpeakerDesign, ...] = ()
        self.worker: DesignWorker | None = None
        self.expert_window: MainWindow | None = None
        self._stale = False
        self._unsaved = False
        self.settings = Settings()
        self.recent = RecentProjects()
        self.autosave = Autosave()
        configure_logging()
        try:
            set_area(str(self.settings.get("area_v2", DEFAULT_AREA)))  # area accent of the design package
        except ValueError:
            set_area(DEFAULT_AREA)
        self.theme_choice = str(self.settings.get("theme", "system"))
        if self.theme_choice not in ("system", "light", "dark"):
            self.theme_choice = "system"
        self.reduced_motion = bool(self.settings.get("reduced_motion", False))
        self.mode = self._resolve_mode()
        self.setStyleSheet(stylesheet(self.mode))

        root = QWidget()
        outer = QVBoxLayout(root)
        outer.setContentsMargins(22, 17, 22, 17)
        outer.setSpacing(15)
        head = QHBoxLayout()
        headings = QVBoxLayout()
        title = QLabel("Lautsprecher Konstruktion")
        title.setObjectName("title")
        title_font = title.font()
        title_font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 97)  # tight display tracking
        title.setFont(title_font)
        headings.addWidget(title)
        subtitle = QLabel("Aus Wunschmaßen wird ein nachvollziehbarer Lautsprecherentwurf.")
        subtitle.setObjectName("subtitle")
        headings.addWidget(subtitle)
        head.addLayout(headings, 1)
        self.focus_button = QPushButton("Zeichnungsmodus")
        self.focus_button.setObjectName("ghost")
        self.focus_button.setCheckable(True)
        self.focus_button.setToolTip("Eingabespalte einklappen und die Ergebnisfläche vergrößern (Strg+D)")
        self.focus_button.toggled.connect(self.set_focus_mode)
        head.addWidget(self.focus_button)
        for label, method in (("Bibliothek", self._library), ("Expertenmodus", self._expert)):
            button = QPushButton(label)
            button.setObjectName("ghost")
            button.clicked.connect(method)
            head.addWidget(button)
        outer.addLayout(head)

        self.split = split = QSplitter(Qt.Orientation.Horizontal)
        split.setChildrenCollapsible(False)
        self.wizard_panel = self._build_wizard()
        split.addWidget(self.wizard_panel)
        split.addWidget(self._build_results())
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setSizes([470, 950])
        self._connect_inputs()
        for spin_box in (self.max_width, self.max_height, self.max_depth):
            spin_box.valueChanged.connect(self._update_start_preview)
        self._update_start_preview()
        outer.addWidget(split, 1)
        self.setCentralWidget(root)
        self._build_menu()
        self.autosave_timer = QTimer(self)
        self.autosave_timer.setInterval(AUTOSAVE_INTERVAL_MS)
        self.autosave_timer.timeout.connect(self._autosave)
        self.autosave_timer.start()
        self.statusBar().showMessage("Bereit · Bibliothek: Herstellerdaten und gekennzeichnete Testdaten")
        brand = QLabel("ACK Studio")  # subtle branding in the footer, no logo
        brand.setObjectName("brand")
        self.statusBar().addPermanentWidget(brand)

    def _resolve_mode(self) -> str:
        """light/dark from the setting; "system" follows the operating-system colour scheme."""
        if self.theme_choice in ("light", "dark"):
            return self.theme_choice
        hints = QGuiApplication.styleHints()
        return "dark" if hints is not None and hints.colorScheme() == Qt.ColorScheme.Dark else "light"

    def set_theme_choice(self, choice: str, *, remember: bool = True) -> None:
        if choice not in ("system", "light", "dark"):
            raise ValueError(f"unknown appearance: {choice}")
        self.theme_choice = choice
        if remember:
            self.settings.set("theme", choice)
        self.apply_mode(self._resolve_mode())

    def apply_mode(self, mode: str) -> None:
        self.mode = mode
        self.setStyleSheet(stylesheet(mode))
        if self.expert_window is not None:
            self.expert_window.set_mode(mode)
        if hasattr(self, "target_panel"):
            self.target_panel.set_mode(mode)
            self.preview.set_mode(mode)
            self.start_preview.set_mode(mode)
        self._redraw_simulation()

    def set_reduced_motion(self, reduced: bool) -> None:
        self.reduced_motion = reduced
        self.settings.set("reduced_motion", reduced)

    def _connect_inputs(self) -> None:
        for control in (self.project_name, self.manufacturer):
            control.textChanged.connect(self._mark_stale)
        for control in (self.speaker_type, self.enclosure, self.profile, self.ways,
                        self.active_mode, self.material, self.driver_choice):
            control.currentIndexChanged.connect(self._mark_stale)
        for control in (self.max_width, self.max_height, self.max_depth, self.max_volume,
                        self.budget, self.target_spl, self.target_f3, self.power,
                        self.preferred_size, self.thickness):
            control.valueChanged.connect(self._mark_stale)
        self.options.toggled.connect(self._mark_stale)

    def _set_state(self, role: str, text: str) -> None:
        """Status line with glyph and text (colour is never the only signal) and a role-coloured edge."""
        self.state.setProperty("role", role)
        self.state.setText(status_line(role, text))
        self.state.style().unpolish(self.state)
        self.state.style().polish(self.state)

    def _clear_results(self) -> None:
        """Invalidate every result view so no drawing, chart or list of an older run stays unmarked."""
        self.designs = ()
        self._stale = False
        self._unsaved = False
        self.variant_list.clear()
        self.variant_cards.clear()
        self.preview.clear()
        self.comparison.setRowCount(0)
        self.details.clear()
        self.why.clear()
        self.kpi_row.setVisible(False)
        self._show_results(False)
        empty = QByteArray(b"<svg xmlns='http://www.w3.org/2000/svg' width='10' height='10'/>")
        for view in (self.svg, self.dimension_svg, self.internal_svg, self.panel_svg):
            view.load(empty)
        self.panel_choice.clear()
        self.bom_view.clear()
        self.cutting_panel.set_bundle(None)
        self.figure.clear()
        self.canvas.draw_idle()
        self.target_panel.set_actual(None, None)
        self.save_button.setEnabled(False)
        self.export_button.setEnabled(False)

    def _mark_stale(self, *_args: object) -> None:
        if self.designs:
            self._stale = True
            self.save_button.setEnabled(False)
            self.export_button.setEnabled(False)
            self._set_state("warning", "Eingaben geändert · Entwurf erneut erstellen, um aktuelle Ergebnisse zu erhalten.")

    @staticmethod
    def _form(parent: QWidget) -> QFormLayout:
        """Form that wraps labels above fields when narrow and never forces a wide minimum."""
        form = QFormLayout(parent)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setVerticalSpacing(6)
        return form

    def _build_wizard(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        card = QFrame()
        card.setObjectName("card")
        card.setMinimumWidth(360)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 12, 20, 16)
        layout.setSpacing(8)

        section = QLabel("Dein Projekt")
        section.setObjectName("section")
        layout.addWidget(section)
        way = QHBoxLayout()
        self.classic_mode = QPushButton("Klassisch")
        self.target_mode = QPushButton("Über Zielkurve")
        for button in (self.classic_mode, self.target_mode):
            button.setObjectName("choiceCard")
            button.setCheckable(True)
            button.setAutoExclusive(True)
            way.addWidget(button)
        self.classic_mode.setChecked(True)
        self.classic_mode.setToolTip("Typ, Bauraum, Klangprofil und Budget vorgeben; die Zielkurve dient danach zur Analyse.")
        self.target_mode.setToolTip("Zuerst die gewünschte Klangkurve formen; der Entwurf richtet sich nach ihr.")
        self.target_mode.toggled.connect(self._design_way_changed)
        layout.addLayout(way)
        self.target_hint = QLabel("Zielkurvenmodus: Forme zuerst die Kurve im Reiter „Klang & Simulation“. "
                                  "Der Tiefton (Gehäuse und Chassis) wird danach daran ausgerichtet; für Mittel- und "
                                  "Hochton liegen ohne Chassis-Messdaten keine Berechnungen vor.")
        self.target_hint.setObjectName("hint")
        self.target_hint.setWordWrap(True)
        self.target_hint.setVisible(False)
        layout.addWidget(self.target_hint)
        self.project_name = QLineEdit("Mein Lautsprecher")
        self.project_name.setPlaceholderText("Projektname")
        layout.addWidget(self.project_name)

        step1 = QGroupBox("1 · Was möchtest du bauen?")
        form1 = self._form(step1)
        self.speaker_type = QComboBox()
        for name in SPEAKER_TYPES:
            self.speaker_type.addItem(name)
        self.speaker_type.setCurrentText("Regallautsprecher")
        form1.addRow("Typ", self.speaker_type)
        self.enclosure = QComboBox()
        self.enclosure.addItem("Automatisch wählen", "auto")
        for entry in registry.all():
            available = entry.status == "SUPPORTED"
            self.enclosure.addItem(entry.label if available else
                                   f"{entry.label} · in Entwicklung", entry.id)
            if not available:
                item = self.enclosure.model().item(self.enclosure.count()-1)
                item.setEnabled(False)
                item.setToolTip("Für diesen Gehäusetyp fehlen noch geprüfter Solver und Fertigungsgeometrie.")
        self.driver_choice = QComboBox()
        self.driver_choice.addItem("Automatisch aus berechenbaren Chassis", None)
        for entry in self.library.entries("drivers"):
            if entry.driver is None:
                continue
            price = entry.price_eur if entry.price_eur is not None else entry.driver.price
            label = entry.display() + (f" · {price:.2f} €/Stück" if price is not None else
                                       " · Preis unbekannt")
            self.driver_choice.addItem(label, entry.display())
        self.driver_choice.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.driver_choice.setMinimumContentsLength(16)
        self.driver_choice.setToolTip("Nur Chassis mit T/S-Daten. Thomann-Preise sind Momentaufnahmen vom 02.10.2026.")
        self.budget = _spin(0, 0, 100000, " €")
        self.budget.setToolTip("Gesamtbudget für ein Gehäuse inkl. Chassis, Holz, Weiche, Zubehör und 15 % Kostenreserve. 0 = offen.")
        layout.addWidget(step1)

        step2 = QGroupBox("2 · Maximaler Bauraum")
        form2 = self._form(step2)
        self.max_width = _spin(300, 120, 2000, " mm")
        self.max_height = _spin(500, 120, 2500, " mm")
        self.max_depth = _spin(400, 120, 2000, " mm")
        self.max_volume = _spin(0, 0, 2000, " l", 1)
        for label, widget in (("Breite bis", self.max_width), ("Höhe bis", self.max_height),
                              ("Tiefe bis", self.max_depth),
                              ("Außenvolumen (optional)", self.max_volume)):
            form2.addRow(label, widget)
        hint = QLabel("Die tatsächlichen Maße werden innerhalb dieser Grenzen gewählt. 0 l = ohne Volumengrenze.")
        hint.setWordWrap(True)
        form2.addRow(hint)
        layout.addWidget(step2)

        step3 = QGroupBox("3 · Gewünschter Klang")
        form3 = self._form(step3)
        self.profile = QComboBox()
        for item in PROFILES.values():
            self.profile.addItem(item.label, item.id)
        form3.addRow("Klangprofil", self.profile)
        layout.addWidget(step3)

        step3b = QGroupBox("Gehäuse, Chassis und Kosten")
        form3b = self._form(step3b)
        form3b.addRow("Gehäuseprinzip", self.enclosure)
        form3b.addRow("Chassis / Preis", self.driver_choice)
        form3b.addRow("Gesamtbudget bis", self.budget)
        layout.addWidget(step3b)

        step4 = QGroupBox("4 · Weitere Anforderungen (optional)")
        step4.setCheckable(True)
        step4.setChecked(False)
        options_body = QWidget()
        form4 = self._form(options_body)
        QVBoxLayout(step4).addWidget(options_body)
        step4.toggled.connect(options_body.setVisible)
        options_body.setVisible(False)
        self.target_spl = _spin(0, 0, 160, " dB")
        self.target_f3 = _spin(0, 0, 300, " Hz")
        self.ways = QComboBox()
        for label, count in (("Automatisch", None), ("1 Weg", 1), ("2 Wege", 2),
                             ("3 Wege · derzeit nicht automatisch", 3)):
            self.ways.addItem(label, count)
        self.power = _spin(5, 0.1, 5000, " W", 1)
        self.active_mode = QComboBox()
        self.active_mode.addItem("Passiv", False)
        self.active_mode.addItem("Aktiv", True)
        self.preferred_size = _spin(0, 0, 1000, " mm")
        self.thickness = _spin(18, 5, 50, " mm")
        self.manufacturer = QLineEdit()
        self.manufacturer.setPlaceholderText("beliebig")
        self.material = QComboBox()
        self.material.addItems(["Birke Multiplex", "MDF", "Spanplatte"])
        for label, widget in (("Zielpegel ab", self.target_spl),
                              ("Ziel-F3 bis", self.target_f3), ("Anzahl Wege", self.ways),
                              ("Aktiv / Passiv", self.active_mode),
                              ("Chassisgröße", self.preferred_size),
                              ("Verstärkerleistung", self.power), ("Materialstärke", self.thickness),
                              ("Hersteller", self.manufacturer), ("Material", self.material)):
            form4.addRow(label, widget)
        layout.addWidget(step4)
        self.options = step4

        footer = QVBoxLayout()  # stays visible below the scrolling form
        row = QHBoxLayout()
        self.create_button = QPushButton("Entwurf erstellen")
        self.create_button.setObjectName("primary")
        self.create_button.clicked.connect(self.create_design)
        row.addWidget(self.create_button, 1)
        self.cancel_button = QPushButton("Abbrechen")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self._cancel)
        row.addWidget(self.cancel_button)
        footer.addLayout(row)
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setTextVisible(False)  # text on the filled accent bar has too little contrast
        footer.addWidget(self.progress)
        self.progress.setVisible(False)  # shown only while a calculation runs
        self.progress_label = QLabel("Noch kein Entwurf berechnet")
        self.progress_label.setObjectName("caption")
        footer.addWidget(self.progress_label)
        demos = QHBoxLayout()
        self.demo_choice = QComboBox()
        self.demo_choice.setMinimumContentsLength(14)
        self.demo_choice.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.demo_choice.addItems(["Demo wählen", "Kompakter 2-Wege-Regallautsprecher",
            "Bassreflex-Subwoofer", "Geschlossener Subwoofer", "Standlautsprecher",
            "Unmögliche Anforderung"])
        demos.addWidget(self.demo_choice, 1)
        load = QPushButton("Demo einsetzen")
        load.clicked.connect(self._demo)
        demos.addWidget(load)
        footer.addLayout(demos)
        layout.addStretch(1)
        scroll.setWidget(card)
        panel = QWidget()
        outer = QVBoxLayout(panel)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll, 1)
        outer.addLayout(footer)
        return panel

    def _build_start_page(self) -> QWidget:
        """Guided start instead of an empty result frame: three steps and a live sketch of the space."""
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(24)
        guide = QVBoxLayout()
        guide.setSpacing(14)
        title = QLabel("In drei Schritten zum ersten Entwurf")
        title.setObjectName("pageTitle")
        guide.addWidget(title)
        for number, head, text in (
                ("1", "Was möchtest du bauen?", "Wähle den Lautsprechertyp. Das Programm sucht dazu passende Gehäuse und Chassis."),
                ("2", "Wie viel Platz hast du?", "Gib Breite, Höhe und Tiefe an. Die Skizze rechts zeigt den Bauraum."),
                ("3", "Wie soll er klingen?", "Wähle ein Klangprofil – oder forme die Zielkurve selbst.")):
            row = QHBoxLayout()
            badge = QLabel(number)
            badge.setObjectName("stepNumber")
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            row.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)
            column = QVBoxLayout()
            column.setSpacing(2)
            heading = QLabel(f"<b>{head}</b>")
            body = QLabel(text)
            body.setObjectName("hint")
            body.setWordWrap(True)
            column.addWidget(heading)
            column.addWidget(body)
            row.addLayout(column, 1)
            guide.addLayout(row)
        example = QPushButton("Beispiel einsetzen: kompakter Regallautsprecher")
        example.clicked.connect(self._load_example)
        guide.addWidget(example, 0, Qt.AlignmentFlag.AlignLeft)
        note = QLabel("Alle Beispiele sind als TESTDATEN gekennzeichnet. Preise und Herstellerdaten werden nie geschätzt.")
        note.setObjectName("hint")
        note.setWordWrap(True)
        guide.addWidget(note)
        guide.addStretch(1)
        layout.addLayout(guide, 3)
        self.start_preview = CabinetPreview()
        self.start_preview.set_mode(self.mode)
        layout.addWidget(self.start_preview, 2)
        return page

    def _load_example(self) -> None:
        self.demo_choice.setCurrentIndex(1)
        self._demo()

    def _update_start_preview(self, *_args: object) -> None:
        if hasattr(self, "start_preview"):
            self.start_preview.set_limits(self.max_width.value(), self.max_height.value(), self.max_depth.value())

    def _show_results(self, show: bool) -> None:
        self.result_stack.setCurrentIndex(1 if show else 0)
        self.actions_bar.setVisible(show)

    def _refresh_cards(self) -> None:
        cards = []
        for row, design in enumerate(self.designs):
            c = design.bundle.cabinet
            f3 = design.bundle.sealed.f3_hz if design.bundle.sealed else (
                design.bundle.vented_response.f3_hz if design.bundle.vented_response else None)
            errors = sum(1 for issue in design.bundle.issues if issue.severity == "error")
            check = (f"✕ {errors} Geometriefehler" if errors else
                     f"⚠ {len(design.bundle.warnings)} Hinweise" if design.bundle.warnings else "✓ keine Hinweise")
            item = self.comparison.item(row, 11)
            cards.append(CardData(
                design.label, registry.get(design.project.enclosure.enclosure_type).label,
                f"{c.width_m*1000:.0f} × {c.height_m*1000:.0f} × {c.depth_m*1000:.0f}", f3,
                design.total_price_eur, check, item.text() if item else "–",
                design.woofer.model + (f" + {design.tweeter.model}" if design.tweeter else "")))
        self.variant_cards.set_cards(cards)

    def _build_results(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        self.state = QLabel()
        self.state.setObjectName("statusLine")
        self.state.setWordWrap(True)
        layout.addWidget(self.state)
        self._set_state("info", "Wähle Typ, Bauraum und Klangprofil. Dann klicke auf „Entwurf erstellen“.")
        self.result_stack = QStackedWidget()
        layout.addWidget(self.result_stack, 1)
        self.result_stack.addWidget(self._build_start_page())
        self.tabs = QTabWidget()

        overview = QWidget()
        ov = QVBoxLayout(overview)
        self.variant_cards = VariantCards()
        self.variant_cards.selected.connect(lambda i: self.variant_list.setCurrentRow(i))
        ov.addWidget(self.variant_cards)
        hero = QHBoxLayout()
        self.preview = CabinetPreview()
        self.preview.set_mode(self.mode)
        hero.addWidget(self.preview, 3)
        self.kpi_row = QWidget()  # right column: at most five key figures
        kpi_layout = QVBoxLayout(self.kpi_row)
        kpi_layout.setContentsMargins(0, 0, 0, 0)
        kpi_layout.setSpacing(8)
        self.kpis: dict[str, tuple[QLabel, QLabel]] = {}
        for key in ("Maße", "Tiefbass F3", "Preisstatus", "Datenqualität", "Prüfstatus"):
            card = QFrame()
            card.setObjectName("surfaceCard")
            inner = QVBoxLayout(card)
            inner.setContentsMargins(12, 6, 12, 6)
            inner.setSpacing(0)
            card.setMinimumHeight(54)
            name = QLabel(key)
            name.setObjectName("kpiLabel")
            value = QLabel()
            value.setObjectName("kpiValue")
            value.setWordWrap(True)
            note = QLabel()  # explanation lives in the tooltip to keep the cards compact
            note.setVisible(False)
            for widget in (name, value):
                inner.addWidget(widget)
            kpi_layout.addWidget(card)
            self.kpis[key] = (value, note)
        kpi_layout.addStretch(1)
        self.kpi_row.setMaximumWidth(340)
        self.kpi_row.setVisible(False)
        hero.addWidget(self.kpi_row, 2)
        ov.addLayout(hero, 1)
        self.variant_list = QListWidget()  # model of the selection; the cards are its view
        self.variant_list.setVisible(False)
        self.variant_list.currentRowChanged.connect(self._select_variant)
        ov.addWidget(self.variant_list)
        self.why = QTextBrowser()
        self.why.setMinimumHeight(140)
        self.why_section = Collapsible("Warum empfohlen?", self.why, reduced_motion=lambda: self.reduced_motion)
        self.why_section.set_full_height(190)
        ov.addWidget(self.why_section)
        self.details = QTextBrowser()
        self.details.setMinimumHeight(200)
        self.details_section = Collapsible("Technische Details", self.details,
                                           reduced_motion=lambda: self.reduced_motion)
        self.details_section.set_full_height(260)
        ov.addWidget(self.details_section)
        self.tabs.addTab(overview, "Entwürfe")

        self.comparison = QTableWidget()
        self.comparison.setColumnCount(12)
        self.comparison.setHorizontalHeaderLabels(("Variante", "Gehäuse", "B × H × T [mm]",
            "Netto [l]", "F3 [Hz]", "Bewertung", "Chassiswahl", "Chassis [€]",
            "Gesamt inkl. Reserve [€]", "Budget frei [€]", "Hinweise", "Abweichung Zielkurve [dB]"))
        self.comparison.setAlternatingRowColors(True)
        self.comparison.setWordWrap(True)
        self.comparison.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.comparison.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.comparison.cellClicked.connect(lambda row, _column: self.variant_list.setCurrentRow(row))
        compare = QWidget()
        compare_layout = QVBoxLayout(compare)
        self.all_columns = QCheckBox("Alle Spalten anzeigen")
        self.all_columns.toggled.connect(self._apply_column_choice)
        compare_layout.addWidget(self.all_columns)
        compare_layout.addWidget(self.comparison, 1)
        self.tabs.addTab(compare, "Variantenvergleich")

        self.drawing_tabs = QTabWidget()
        self.drawing_tabs.setDocumentMode(True)
        self.svg = ZoomableSvgView()
        self.drawing_tabs.addTab(self.svg, "Gesamtzeichnung")
        self.dimension_svg = ZoomableSvgView()
        self.drawing_tabs.addTab(self.dimension_svg, "Maßblatt")
        self.internal_svg = ZoomableSvgView()
        self.drawing_tabs.addTab(self.internal_svg, "Innenaufbau")
        panel = QWidget()
        panel_layout = QVBoxLayout(panel)
        self.panel_choice = QComboBox()
        self.panel_choice.currentIndexChanged.connect(self._show_panel_sheet)
        panel_layout.addWidget(self.panel_choice)
        self.panel_svg = ZoomableSvgView()
        panel_layout.addWidget(self.panel_svg, 1)
        self.drawing_tabs.addTab(panel, "Einzelteilplan")
        self.tabs.addTab(self.drawing_tabs, "Zeichnungen")

        sound = QSplitter(Qt.Orientation.Vertical)
        sound.setChildrenCollapsible(False)
        self.target_panel = TargetCurvePanel()
        self.target_panel.set_mode(self.mode)
        self.target_panel.curveChanged.connect(self._target_changed)
        sound.addWidget(self.target_panel)
        simulation = QWidget()
        sim_layout = QVBoxLayout(simulation)
        sim_layout.setContentsMargins(0, 0, 0, 0)
        self.more_charts = QCheckBox("Weitere Diagramme (Port, Gruppenlaufzeit)")
        self.more_charts.toggled.connect(self._redraw_simulation)
        sim_layout.addWidget(self.more_charts)
        self.figure = Figure(figsize=(9, 6), layout="constrained")
        self.canvas = FigureCanvasQTAgg(self.figure)
        sim_layout.addWidget(self.canvas, 1)
        sound.addWidget(simulation)
        sound.setStretchFactor(0, 3)
        sound.setStretchFactor(1, 2)
        sound.setSizes([560, 280])
        self.tabs.addTab(sound, "Klang && Simulation")  # && shows a literal ampersand

        self.bom_view = QTextBrowser()
        self.tabs.addTab(self.bom_view, "Stückliste")
        self.cutting_panel = CuttingPanel(self.settings)
        self.tabs.addTab(self.cutting_panel, "Zuschnitt")
        results_page = QWidget()
        results_layout = QVBoxLayout(results_page)
        results_layout.setContentsMargins(0, 0, 0, 0)
        results_layout.addWidget(self.tabs, 1)
        self.result_stack.addWidget(results_page)
        actions = QHBoxLayout()
        self.save_button = QPushButton("Projekt speichern")
        self.save_button.clicked.connect(self._save)
        self.load_button = QPushButton("Projekt laden")
        self.load_button.clicked.connect(self._load)
        self.export_button = QPushButton("Fertigungsunterlagen exportieren")
        self.export_button.setObjectName("primary")
        self.export_button.clicked.connect(self._export)
        self.save_button.setObjectName("ghost")
        self.load_button.setVisible(False)  # loading lives in the File menu and the recent list
        actions.addStretch(1)
        for button in (self.save_button, self.load_button, self.export_button):
            actions.addWidget(button)
        self.actions_bar = QWidget()
        self.actions_bar.setLayout(actions)
        actions.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.actions_bar)
        self.actions_bar.setVisible(False)
        self.save_button.setEnabled(False)
        self.export_button.setEnabled(False)
        return container

    def _target_f3(self) -> float | None:
        """Explicit F3 wish, else the -3 dB point of the shaped target curve in target mode."""
        if self.options.isChecked() and self.target_f3.value():
            return self.target_f3.value()
        if self.target_mode.isChecked():
            return derive_f3_target_hz(self.target_panel.curve())
        return None

    def _design_way_changed(self, target: bool) -> None:
        self.target_hint.setVisible(target)
        self.create_button.setText("Entwurf aus Zielkurve erstellen" if target else "Entwurf erstellen")
        if target:
            self.tabs.setCurrentIndex(self._sound_tab_index())
        self._mark_stale()

    def _sound_tab_index(self) -> int:
        return next(i for i in range(self.tabs.count()) if self.tabs.tabText(i).startswith("Klang"))

    def _target_changed(self, _curve: object) -> None:
        self._unsaved = self._unsaved or bool(self.designs)
        self._update_deviation_column()
        if self.target_mode.isChecked():
            self._mark_stale()  # the variants were not derived from this curve

    def _update_deviation_column(self) -> None:
        curve = self.target_panel.curve()
        for row, design in enumerate(self.designs[: self.comparison.rowCount()]):
            frequencies, response = self._response_of(design)
            dev = deviation(curve, frequencies, response)
            text = "–" if dev is None else f"Ø {dev.mean_abs_db:.1f} / max {dev.max_abs_db:.1f}"
            self.comparison.setItem(row, 11, QTableWidgetItem(text))
        self.target_panel.set_actual(*(self._response_of(self._current()) if self._current() else (None, None)))

    @staticmethod
    def _response_of(design: SpeakerDesign) -> tuple[np.ndarray, np.ndarray]:
        bundle = design.bundle
        r = bundle.vented_response or bundle.sealed_response
        if r is not None:
            return np.asarray(r.frequencies_hz), np.asarray(r.response_db)
        frequencies = np.geomspace(10, 500, 400)
        return frequencies, np.asarray(sealed_response_db(bundle.acoustic_driver, bundle.target_net_volume_m3,
                                                          frequencies))

    def _request(self) -> AutomaticDesignRequest:
        optional = self.options.isChecked()
        return AutomaticDesignRequest(project_name=self.project_name.text().strip() or "Mein Lautsprecher",
            speaker_type=self.speaker_type.currentText(),
            enclosure_preference=self.enclosure.currentData(),
            max_width_m=self.max_width.value()/1000, max_height_m=self.max_height.value()/1000,
            max_depth_m=self.max_depth.value()/1000,
            max_outer_volume_l=self.max_volume.value() or None,
            sound_profile=self.profile.currentData(),
            budget=self.budget.value() or None,
            target_spl_db=self.target_spl.value() or None if optional else None,
            target_f3_hz=self._target_f3(),
            way_count=self.ways.currentData() if optional else None,
            active=self.active_mode.currentData() if optional else False,
            preferred_size_m=self.preferred_size.value()/1000 if optional and self.preferred_size.value() else None,
            amplifier_power_w=self.power.value() if optional else 5,
            panel_thickness_m=self.thickness.value()/1000 if optional else .018,
            preferred_manufacturer=self.manufacturer.text().strip() or None if optional else None,
            preferred_driver=self.driver_choice.currentData(),
            material=self.material.currentText() if optional else "Birke Multiplex")

    def create_design(self) -> None:
        if self.worker and self.worker.isRunning():
            return
        try:
            request = self._request()
        except ValidationError as exc:
            QMessageBox.warning(self, "Vorgaben ungültig", str(exc))
            return
        self.worker = DesignWorker(request, self.library)
        self.worker.progress.connect(self._progress)
        self.worker.completed.connect(self._completed)
        self.worker.failed.connect(self._failed)
        self._clear_results()  # no unmarked results of an earlier run while a new one is calculated
        self.create_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress.setValue(0)
        self.progress.setVisible(True)
        self.progress_label.setText("Varianten werden berechnet… 0 %")
        self._set_state("info", "Komponenten werden geprüft und Gehäusevarianten simuliert…")
        self.worker.start()

    # decision-relevant columns first: variant, enclosure, size, F3, total cost, notes
    _CORE_COLUMNS = (0, 1, 2, 4, 8, 10, 11)

    def _apply_column_choice(self, *_args: object) -> None:
        show_all = self.all_columns.isChecked()
        for column in range(self.comparison.columnCount()):
            self.comparison.setColumnHidden(column, not (show_all or column in self._CORE_COLUMNS))

    def _progress(self, value: int) -> None:
        self.progress.setValue(value)
        self.progress_label.setText(f"Varianten werden berechnet… {value} %")

    def _cancel(self) -> None:
        if self.worker:
            self.worker.cancel_event.set()
            self.progress_label.setText("Berechnung wird abgebrochen…")

    def _completed(self, result: AutomaticDesignResult) -> None:
        self.create_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress.setValue(100 if result.status != "cancelled" else 0)
        self.progress.setVisible(False)
        self.designs = result.designs
        self._stale = result.status != "ok"
        self._unsaved = result.status == "ok" and bool(result.designs)
        self.variant_list.clear()
        self.comparison.setRowCount(0)
        if result.status == "ok":
            self.progress_label.setText(f"{result.candidates_tested} Kandidaten geprüft")
            self._set_state("success", f"{len(result.designs)} nachvollziehbare Entwürfe · Datenquelle je Chassis prüfen")
            self.comparison.setRowCount(len(result.designs))
            for row, design in enumerate(result.designs):
                c = design.bundle.cabinet
                self.variant_list.addItem(f"{design.label}  ·  {registry.get(design.project.enclosure.enclosure_type).label}  ·  "
                    f"{design.woofer.model}" + (f" + {design.tweeter.model}" if design.tweeter else ""))
                f3 = design.bundle.sealed.f3_hz if design.bundle.sealed else (
                    design.bundle.vented_response.f3_hz if design.bundle.vented_response else None)
                values = (design.label,
                    registry.get(design.project.enclosure.enclosure_type).label,
                    f"{c.width_m*1000:.0f} × {c.height_m*1000:.0f} × {c.depth_m*1000:.0f}",
                    f"{design.bundle.target_net_volume_m3*1000:.1f}",
                    f"{f3:.1f}" if f3 else "–", f"{design.score:.0f}/100",
                    design.woofer.model + (f" + {design.tweeter.model}" if design.tweeter else ""),
                    f"{design.price:.2f}" if design.price is not None else "–",
                    f"{design.total_price_eur:.2f}" if design.total_price_eur is not None else "–",
                    f"{self.budget.value()-design.total_price_eur:.2f}"
                    if self.budget.value() and design.total_price_eur is not None else "–",
                    str(len(design.bundle.warnings)))
                for column, value in enumerate(values):
                    self.comparison.setItem(row, column, QTableWidgetItem(value))
            self._update_deviation_column()
            self._refresh_cards()
            self._show_results(True)
            self.comparison.resizeColumnsToContents()
            self._apply_column_choice()
            self.save_button.setEnabled(True)
            self.variant_list.setCurrentRow(0)
        elif result.status == "impossible":
            self.progress_label.setText(f"{result.candidates_tested} Kandidaten geprüft")
            self._set_state("danger", "Mit diesen Vorgaben ist kein sinnvoller Entwurf möglich. Änderungsvorschläge stehen unter „Entwürfe“.")
            reasons = "".join(f"<li>{escape(item)}</li>" for item in result.rejection_reasons)
            changes = "".join(f"<li>{escape(item)}</li>" for item in result.suggested_constraint_changes)
            self._clear_results()
            self._stale = True
            self.details.setHtml(f"<h2>Nicht machbar</h2><p>Technische Meldungen des Berechnungskerns "
                f"(Originaltext, daher teils englisch):</p><b>Gründe</b><ul>{reasons}</ul>"
                f"<b>Mögliche Änderungen</b><ul>{changes}</ul>")
            self._show_results(True)
            self.tabs.setCurrentIndex(0)
            self.details_section.button.setChecked(True)  # the reasons are the content here
            self.save_button.setEnabled(False)
            self.export_button.setEnabled(False)
        else:
            self.progress_label.setText("Berechnung abgebrochen")
            self._set_state("warning", "Berechnung abgebrochen")
        self.statusBar().showMessage(self.state.text())

    def _failed(self, message: str) -> None:
        self.create_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress.setVisible(False)
        self._clear_results()
        self.progress_label.setText("Berechnung fehlgeschlagen")
        self._set_state("danger", f"{message} Nächster Schritt: Vorgaben prüfen oder die Protokolldatei (Hilfe) ansehen.")

    def _current(self) -> SpeakerDesign | None:
        index = self.variant_list.currentRow()
        return self.designs[index] if 0 <= index < len(self.designs) else None

    def _select_variant(self, index: int) -> None:
        if not (0 <= index < len(self.designs)):
            return
        design = self.designs[index]
        bundle = design.bundle
        self.cutting_panel.set_bundle(bundle)
        c = bundle.cabinet
        f3 = bundle.sealed.f3_hz if bundle.sealed else (
            bundle.vented_response.f3_hz if bundle.vented_response else None)
        why_lines = [f"<h2>{escape(design.label)} · Warum empfohlen?</h2>"]
        lines = [
            f"<p><b>Gehäuse:</b> {escape(registry.get(design.project.enclosure.enclosure_type).label)} · "
            f"{c.width_m*1000:.0f} × {c.height_m*1000:.0f} × {c.depth_m*1000:.0f} mm<br>"
            f"<b>Netto:</b> {bundle.target_net_volume_m3*1000:.1f} l · "
            f"<b>F3:</b> {f3:.1f} Hz</p>" if f3 else "<p>F3 nicht berechenbar</p>",
            f"<p><b>Tieftöner:</b> {escape(design.woofer.manufacturer)} {escape(design.woofer.model)}<br>"
            f"<b>Hochtöner:</b> {escape(design.tweeter.model) if design.tweeter else '–'}<br>"
            f"<b>Chassispreis:</b> {design.price:.2f} €</p>" if design.price is not None else
            f"<p><b>Tieftöner:</b> {escape(design.woofer.manufacturer)} {escape(design.woofer.model)}<br>"
            f"<b>Hochtöner:</b> {escape(design.tweeter.model) if design.tweeter else '–'}<br>"
            "<b>Chassispreis:</b> nicht verfügbar</p>"]
        lines.append("<p><b>Gesamtkalkulation inkl. 15 % Reserve:</b> "+
            (f"{design.total_price_eur:.2f} €" if design.total_price_eur is not None else
             "nicht vollständig bepreist")+"</p>")
        if self.budget.value() and design.total_price_eur is not None:
            lines.append(f"<p><b>Budget noch frei:</b> "
                         f"{self.budget.value()-design.total_price_eur:.2f} €</p>")
        if design.breakdown:
            why_lines.append(f"<h3>Teilbewertung · {design.score:.0f}/100 aus {len(design.breakdown)} "
                         "bewerteten Kriterien</h3><p>Keine Qualitätsfreigabe: nicht belegbare Kriterien "
                         "fließen nicht ein.</p>")
            names = {"bass": "Tiefbass", "size": "Kompaktheit", "headroom": "Auslenkungsreserve",
                "port": "Portreserve", "delay": "Gruppenlaufzeit", "flatness": "Linearität",
                "cost": "Budgetreserve"}
            for metric in design.breakdown:
                why_lines.append(f"<p><b>{names.get(metric.name, metric.name)}</b> "
                    f"{metric.value:.0f}/100 "
                    f"(Gewicht {metric.weight:g})<br>{escape(metric.evidence)}</p>")
            missing = {"headroom", "port", "delay", "flatness"}-{
                metric.name for metric in design.breakdown}
            if bundle.port is None:
                missing.discard("port")
            if missing:
                why_lines.append("<p><i>Nicht bewertet: "+", ".join(names[key] for key in sorted(missing))+
                    ". Nicht verfügbare Werte werden nicht ergänzt.</i></p>")
        why_lines.append("<h3>Gründe</h3><ul>"+
            "".join(f"<li>{escape(reason)}</li>" for reason in design.reasons)+"</ul>")
        if design.provisional_crossover:
            lines.append("<p><b>Vorläufiger Frequenzweichenentwurf:</b> Für eine Endabstimmung "
                "sind FRD/ZMA-Messungen am aufgebauten Lautsprecher nötig.</p>")
        if bundle.warnings:
            lines.append("<h3>Hinweise</h3><ul>"+
                "".join(f"<li>{escape(message)}</li>" for message in bundle.warnings)+"</ul>")
        if design.total_price_eur is None:
            why_lines.append("<p><i>Preis unvollständig: Dieser Entwurf wird nicht als günstiger bewertet.</i></p>")
        self.why.setHtml("".join(why_lines))
        self.details.setHtml("".join(lines))
        geometry_issue_count = sum(1 for issue in bundle.issues if issue.severity == "error")
        values = {
            "Maße": (f"{c.width_m*1000:.0f} × {c.height_m*1000:.0f} × {c.depth_m*1000:.0f} mm",
                     f"Netto {bundle.target_net_volume_m3*1000:.1f} l"),
            "Tiefbass F3": (f"{f3:.0f} Hz" if f3 else "nicht berechenbar", "−3 dB, relativ, Kleinsignalmodell"),
            "Preisstatus": (f"{design.total_price_eur:.0f} € inkl. Reserve" if design.total_price_eur is not None
                            else "unvollständig bepreist", "Händlerpreise sind Momentaufnahmen"),
            "Datenqualität": ("vorläufige Weiche" if design.provisional_crossover else "Herstellerdaten",
                              "Quelle je Chassis prüfen"),
            "Prüfstatus": (f"✕ {geometry_issue_count} Geometriefehler" if geometry_issue_count else
                           f"⚠ {len(bundle.warnings)} Hinweise" if bundle.warnings else "✓ keine Hinweise",
                           "Export nur ohne Geometriefehler")}
        for key, (value, note) in values.items():
            self.kpis[key][0].setText(value)
            self.kpis[key][0].setToolTip(note)
            self.kpis[key][1].setText(note)
        self.kpi_row.setVisible(True)
        self.preview.set_design(c.width_m * 1000, c.height_m * 1000, c.depth_m * 1000, bundle.front_elements,
                                f"{design.label} · {registry.get(design.project.enclosure.enclosure_type).label}")
        self.variant_cards.select(index)
        self.comparison.selectRow(index)
        self.svg.load(QByteArray(render_master_sheet_svg(bundle).encode("utf-8")))
        self.dimension_svg.load(QByteArray(render_dimension_svg(bundle).encode("utf-8")))
        self.internal_svg.load(QByteArray(render_internal_dimensions_svg(bundle).encode("utf-8")))
        self.panel_choice.blockSignals(True)
        self.panel_choice.clear()
        for surface in panel_sheet_surfaces(bundle):
            self.panel_choice.addItem({"front": "Frontplatte", "back": "Rückwand",
                                       "partition": "Trennwand"}[surface], surface)
        self.panel_choice.blockSignals(False)
        self._show_panel_sheet(0)
        subtotal, missing = priced_subtotal(design.bom)
        planned_total = budget_cost(design.bom)
        rows = "".join("<tr><td>"+escape(item.reference)+"</td><td>"+
            escape(item.description)+"</td><td>"+str(item.quantity)+"</td><td>"+
            (f"{item.unit_price_eur:.2f} €" if item.unit_price_eur is not None else "–")+
            "</td><td>"+
            (f"{item.line_total_eur:.2f} €" if item.line_total_eur is not None else "–")+
            "</td><td>"+escape(item.price_kind)+"</td></tr>" for item in design.bom)
        self.bom_view.setHtml("<h2>Stückliste</h2><table border='1' cellpadding='5'>"
            "<tr><th>Ref.</th><th>Bauteil</th><th>Anzahl</th><th>Einzelpreis</th><th>Position</th><th>Art</th></tr>"+
            rows+"</table><p><b>Bekannte Teilsumme: "+f"{subtotal:.2f} €"+
            f"</b> · {missing} Positionen ohne Preis.</p>"+
            (f"<p><b>Budgetansatz inkl. 15 % Reserve: {planned_total:.2f} €</b></p>"
             if planned_total is not None else "<p>Budgetansatz nicht vollständig belegbar.</p>")+
            "<p>Händlerpreise und Planpreise sind getrennt gekennzeichnet. Versand und Arbeitszeit "
            "sind nicht kalkuliert. Preisquellen stehen im CSV-Export.</p>")
        self._redraw_simulation()
        self.target_panel.set_actual(*self._response_of(design))
        status = (f"{registry.get(design.project.enclosure.enclosure_type).label} · "
            f"{c.width_m*1000:.0f}×{c.height_m*1000:.0f}×{c.depth_m*1000:.0f} mm · "
            f"F3 {f3:.1f} Hz · " if f3 else "F3 nicht berechenbar · ")
        geometry_errors = [issue.message for issue in bundle.issues if issue.severity == "error"]
        self.export_button.setEnabled(not geometry_errors and not self._stale)
        self.export_button.setToolTip("; ".join(geometry_errors) if geometry_errors else
                                      "Geprüfte Zeichnungen, DXF, PDF und Stücklisten exportieren")
        status += f"Hinweise {len(bundle.warnings)} · Geometriefehler {len(geometry_errors)}"
        if geometry_errors:
            status += " · Export gesperrt: " + geometry_errors[0]
        if self._stale:
            self._set_state("warning", "Eingaben geändert · Entwurf erneut erstellen.")
        else:
            self._set_state("danger" if geometry_errors else "warning" if bundle.warnings else "success", status)

    def _redraw_simulation(self, *_args: object) -> None:
        """Default: frequency response and excursion (two charts); the others on request."""
        design = self._current()
        if design is None:
            return
        bundle = design.bundle
        r = bundle.vented_response or bundle.sealed_response
        tokens = theme_tokens(self.mode)
        with matplotlib.rc_context(chart_rc(self.mode)):
            self.figure.clear()
            self.figure.set_facecolor(tokens["surface"])
            wide = self.more_charts.isChecked()
            panels = [("Tiefton · relativ", "Pegel [dB]", None, None),
                      ("Membranauslenkung", "mm", r.excursion_mm if r is not None else None,
                       (bundle.project.driver.xmax_mm, "Xmax"))]
            if wide:
                panels += [("Port / Passivmembran", "m/s", r.port_velocity_m_s if r is not None else None,
                            (17.0, "Richtwert 17 m/s") if bundle.port else None),
                           ("Gruppenlaufzeit", "ms", r.group_delay_ms if r is not None else None, None)]
            for index, (title, ylabel, values, limit) in enumerate(panels, start=1):
                ax = self.figure.add_subplot(2, 2, index) if wide else self.figure.add_subplot(1, 2, index)
                ax.set_title(title)
                ax.set_xlabel("Frequenz [Hz]")
                ax.set_ylabel(ylabel)
                ax.set_xlim(10, 500)
                if index == 1:
                    if r is not None:
                        ax.semilogx(r.frequencies_hz, r.response_db, linewidth=2)
                    else:
                        frequencies = np.geomspace(10, 500, 400)
                        ax.semilogx(frequencies, sealed_response_db(bundle.acoustic_driver,
                            bundle.target_net_volume_m3, frequencies), linewidth=2)
                    ax.axhline(-3.0, color=tokens["textSecondary"], linestyle=":", linewidth=1)
                    ax.text(0.99, 0.04, "−3 dB", transform=ax.transAxes, ha="right", fontsize=9,
                            color=tokens["textSecondary"])
                elif values is None:
                    note = ("Kein Port in diesem Gehäuse" if (bundle.sealed is not None and title.startswith("Port"))
                            else "Mess-/Treiberwerte fehlen")
                    ax.text(.5, .5, note, ha="center", va="center", transform=ax.transAxes,
                            color=tokens["textSecondary"])
                elif r is not None:
                    ax.semilogx(r.frequencies_hz, values, linewidth=1.8)
                    if limit is not None and limit[0] is not None:
                        ax.axhline(limit[0], color=tokens["textPrimary"], linestyle="--", linewidth=1.2, label=limit[1])
                        ax.legend(loc="upper right")
        self.canvas.draw_idle()

    def _show_panel_sheet(self, index: int) -> None:
        current = self._current()
        if current is None or index < 0:
            return
        surface = self.panel_choice.itemData(index)
        if surface:
            self.panel_svg.load(QByteArray(render_panel_sheet_svg(
                current.bundle, surface).encode("utf-8")))

    def set_focus_mode(self, on: bool) -> None:
        """Collapse the input column so drawings and results get the full width."""
        sizes = self.split.sizes()
        total = sum(sizes) or 1
        target = 0 if on else max(420, round(total * 0.33))
        self.wizard_panel.setMinimumWidth(0 if on else 360)

        def apply(width: int) -> None:
            self.split.setSizes([width, total - width])

        def done() -> None:
            self.wizard_panel.setVisible(not on)
            for view in (self.svg, self.dimension_svg, self.internal_svg, self.panel_svg):
                view.fit()  # fit exactly once after the transition

        if not on:
            self.wizard_panel.setVisible(True)
        animate_value(self.split, sizes[0], target, apply, reduced=self.reduced_motion, finished=done)
        self.focus_button.setText("Eingaben zeigen" if on else "Zeichnungsmodus")
        if on:
            self.tabs.setCurrentIndex(2)

    def _expert(self) -> None:
        if self.expert_window is None:
            self.expert_window = MainWindow()
            self.expert_window.set_mode(self.mode)
            self.expert_window.projectCalculated.connect(self._expert_updated)
        current = self._current()
        if current:
            self.expert_window._apply_project(current.project)
            self.expert_window.calculate()
        self.expert_window.show()
        self.expert_window.raise_()

    def _expert_updated(self, bundle: DesignBundle) -> None:
        bom = build_bom(bundle)
        design = SpeakerDesign("Expertenentwurf", bundle.project, bundle,
            bundle.project.driver, None, 0, (), ("Im Expertenmodus bearbeitet.",),
            bom, None, None, False, budget_cost(bom))
        self.designs = (design,)
        self._stale = False
        self._unsaved = True
        self.variant_list.clear()
        self.comparison.setRowCount(0)
        self.variant_list.addItem("Expertenentwurf · aktuelle Berechnung")
        self.comparison.setRowCount(1)
        self._refresh_cards()
        self._show_results(True)
        self.save_button.setEnabled(True)
        self.variant_list.setCurrentRow(0)
        self._set_state("info", "Expertenentwurf übernommen")

    def _library(self) -> None:
        dialog = LibraryDialog(self.library, self)
        dialog.exec()

    def _demo(self) -> None:
        choice = self.demo_choice.currentIndex()
        if choice == 0:
            return
        presets = {
            1: ("Regallautsprecher", "auto", 230, 420, 310, "neutral", None, None),
            2: ("Subwoofer", "bass_reflex", 400, 600, 600, "deep_bass", None, None),
            3: ("Subwoofer", "sealed", 400, 600, 600, "neutral", None, None),
            4: ("Standlautsprecher", "auto", 340, 950, 450, "neutral", None, None),
            5: ("Subwoofer", "auto", 300, 300, 200, "deep_bass", 20, 120),
        }
        speaker, enclosure, w, h, d, profile, f3, spl = presets[choice]
        self.speaker_type.setCurrentText(speaker)
        self.enclosure.setCurrentIndex(self.enclosure.findData(enclosure))
        self.max_width.setValue(w)
        self.max_height.setValue(h)
        self.max_depth.setValue(d)
        self.max_volume.setValue(0)
        self.profile.setCurrentIndex(self.profile.findData(profile))
        self.options.setChecked(f3 is not None or spl is not None)
        self.target_f3.setValue(f3 or 0)
        self.target_spl.setValue(spl or 0)
        self.project_name.setText(self.demo_choice.currentText()+" · TESTDATEN")

    def _save(self) -> None:
        design = self._current()
        if not design:
            return
        filename, _ = QFileDialog.getSaveFileName(self, "Projekt speichern",
            design.project.name+".json", "Lautsprecherprojekt (*.json)")
        if filename:
            try:
                Path(filename).write_text(self._project_json(design), encoding="utf-8")
            except OSError as exc:
                LOG.warning("Speichern fehlgeschlagen: %s", exc)
                QMessageBox.warning(self, "Speichern fehlgeschlagen", str(exc))
                return
            self._unsaved = False
            self.autosave.discard()
            self.recent.add(filename)
            self._refresh_recent_menu()
            self.statusBar().showMessage(f"Projekt gespeichert: {filename}")

    def _project_json(self, design: SpeakerDesign) -> str:
        """Project file; the target curve is stored only when it was actually shaped (optional, versioned)."""
        curve = self.target_panel.curve()
        project = design.project
        if not curve.is_neutral or self.target_mode.isChecked():
            project = project.model_copy(update={"target_curve": curve})
        return project.model_dump_json(indent=2)

    def _load(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "Projekt laden", "", "Lautsprecherprojekt (*.json)")
        if filename:
            self.open_project_file(filename)

    def open_project_file(self, filename: str | Path, *, remember: bool = True) -> bool:
        """Load and calculate a saved project; returns False and informs the user on failure."""
        if not self._confirm_discard():
            return False
        try:
            project = SpeakerProject.model_validate_json(Path(filename).read_text(encoding="utf-8"))
            bundle = calculate_project(project)
        except (OSError, ValidationError, ValueError) as exc:
            LOG.warning("Projekt laden fehlgeschlagen (%s): %s", filename, exc)
            QMessageBox.warning(self, "Projekt laden fehlgeschlagen", str(exc))
            return False
        self._expert_updated(bundle)
        self.target_panel.set_curve(project.target_curve)
        if project.target_curve is not None:
            self.target_mode.setChecked(True)
        if remember:
            self._unsaved = False
            self.recent.add(filename)
            self._refresh_recent_menu()
        self.statusBar().showMessage(f"Projekt geladen: {filename}")
        return True

    def _export(self) -> None:
        design = self._current()
        if not design:
            return
        folder = QFileDialog.getExistingDirectory(self, "Exportordner wählen")
        if folder:
            try:
                package = export_project_package(design.bundle, folder,
                    self.cutting_panel.settings(design.project.material))
                self.statusBar().showMessage(f"Fertigungsunterlagen: {package}")
            except (OSError, ValueError) as exc:
                LOG.warning("Export fehlgeschlagen: %s", exc)
                QMessageBox.warning(self, "Export fehlgeschlagen", str(exc))

    # --- menu, help, recovery -------------------------------------------------

    def _action(self, text: str, slot: object, shortcut: str | None = None) -> QAction:
        action = QAction(text, self)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        action.triggered.connect(slot)
        return action

    def _build_menu(self) -> None:
        bar = self.menuBar()
        file_menu = bar.addMenu("&Datei")
        file_menu.addAction(self._action("Projekt &laden…", self._load, "Ctrl+O"))
        self.recent_menu = file_menu.addMenu("&Zuletzt geöffnet")
        file_menu.addAction(self._action("Projekt &speichern…", self._save, "Ctrl+S"))
        file_menu.addAction(self._action("Fertigungsunterlagen &exportieren…", self._export, "Ctrl+E"))
        file_menu.addSeparator()
        file_menu.addAction(self._action("&Beenden", self.close, "Ctrl+Q"))
        tools = bar.addMenu("&Werkzeuge")
        tools.addAction(self._action("&Bibliothek", self._library))
        tools.addAction(self._action("&Expertenmodus", self._expert))
        tools.addAction(self._action("&Prototyp vergleichen…", self._prototype))
        view = bar.addMenu("&Ansicht")
        view.addAction(self._action("&Zeichnungsmodus", lambda: self.focus_button.toggle(), "Ctrl+D"))
        look = view.addMenu("&Erscheinungsbild")
        self.theme_group = QActionGroup(self)
        self.theme_actions: dict[str, QAction] = {}
        for key, label in (("system", "&System"), ("light", "&Hell"), ("dark", "&Dunkel")):
            action = QAction(label, self, checkable=True)
            action.setChecked(self.theme_choice == key)
            action.triggered.connect(lambda _checked=False, k=key: self.set_theme_choice(k))
            self.theme_group.addAction(action)
            look.addAction(action)
            self.theme_actions[key] = action
        self.motion_action = QAction("&Animationen reduzieren", self, checkable=True)
        self.motion_action.setChecked(self.reduced_motion)
        self.motion_action.toggled.connect(self.set_reduced_motion)
        view.addAction(self.motion_action)
        help_menu = bar.addMenu("&Hilfe")
        help_menu.addAction(self._action("&Kurzanleitung und Über…", self._help, "F1"))
        help_menu.addAction(self._action("&Protokollordner öffnen", self._open_log_folder))
        self._refresh_recent_menu()

    def _refresh_recent_menu(self) -> None:
        self.recent_menu.clear()
        items = self.recent.items()
        for path in items:
            self.recent_menu.addAction(self._action(
                path.name, lambda _=False, target=path: self.open_project_file(target)))
        if items:
            self.recent_menu.addSeparator()
            self.recent_menu.addAction(self._action("Liste leeren", self._clear_recent))
        self.recent_menu.setEnabled(bool(items))

    def _clear_recent(self) -> None:
        self.recent.clear()
        self._refresh_recent_menu()

    def _help(self) -> None:
        HelpDialog(self).exec()

    def _open_log_folder(self) -> None:
        folder = log_file().parent
        folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def _prototype(self) -> None:
        current = self._current()
        if current is None:
            QMessageBox.information(self, "Kein Entwurf", "Bitte zuerst einen Entwurf erstellen oder ein Projekt laden.")
            return
        PrototypeDialog(current.bundle, self).exec()

    def _autosave(self) -> None:
        design = self._current()
        if design is None or not self._unsaved:
            return
        try:
            self.autosave.write(self._project_json(design))
        except OSError as exc:
            LOG.warning("Autosave fehlgeschlagen: %s", exc)

    def offer_recovery(self) -> bool:
        """After a crash the newest autosave can be restored; returns True if it was restored."""
        saved = self.autosave.recoverable()
        if saved is None:
            return False
        answer = QMessageBox.question(self, "Projekt wiederherstellen",
            "Beim letzten Beenden wurde ein ungespeicherter Entwurf gefunden. Wiederherstellen?")
        if answer != QMessageBox.StandardButton.Yes:
            self.autosave.discard()
            return False
        if not self.open_project_file(saved, remember=False):
            return False
        self._unsaved = True  # restored data is not yet saved to a project file
        self.autosave.discard()
        return True

    def _confirm_discard(self) -> bool:
        if not self._unsaved or self._current() is None:
            return True
        answer = QMessageBox.question(self, "Ungespeicherte Änderungen",
            "Der aktuelle Entwurf ist nicht gespeichert. Trotzdem fortfahren?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        return answer == QMessageBox.StandardButton.Yes

    def closeEvent(self, event: object) -> None:
        # Only a user-initiated close of a visible window asks for confirmation.
        if self.isVisible() and not self._confirm_discard():
            event.ignore()
            return
        self.autosave_timer.stop()
        self.autosave.discard()
        if self.worker and self.worker.isRunning():
            self.worker.cancel_event.set()
            self.worker.wait(5000)
        if self.expert_window:
            self.expert_window.close()
        super().closeEvent(event)
