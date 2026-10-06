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
from lautsprecher_konstruktion.ui.cabinet_preview import CabinetPreview
from lautsprecher_konstruktion.ui.cutting_panel import CuttingPanel
from lautsprecher_konstruktion.ui.help_dialog import HelpDialog
from lautsprecher_konstruktion.ui.library_dialog import LibraryDialog
from lautsprecher_konstruktion.ui.main_window import MainWindow
from lautsprecher_konstruktion.ui.motion import animate_value
from lautsprecher_konstruktion.ui.planner_widgets import ChoiceGrid, DimensionPreview, VariantCards
from lautsprecher_konstruktion.ui.prototype_dialog import PrototypeDialog
from lautsprecher_konstruktion.ui.theme import chart_rc, stylesheet
from lautsprecher_konstruktion.ui.target_curve import TargetCurveEditor
from lautsprecher_konstruktion.ui.tokens import set_area, status_line
from lautsprecher_konstruktion.ui.tokens import theme as theme_tokens
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
        # Loudspeaker Konstruktion is an ACK Studio software product.
        # Ignore legacy area=construction settings from older builds.
        set_area("software")
        self.settings.set("area", "software")
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
        self.focus_button = QPushButton("Zeichnung groß anzeigen")
        self.focus_button.setCheckable(True)
        self.focus_button.setVisible(False)
        self.focus_button.setToolTip("Eingabespalte einklappen und die Ergebnisfläche vergrößern (Strg+D)")
        self.focus_button.toggled.connect(self.set_focus_mode)
        head.addWidget(self.focus_button)
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
        if hasattr(self, "target_curve"):
            self.target_curve.set_mode(mode)
        if hasattr(self, "preview"):
            self.preview.set_mode(mode)
        if hasattr(self, "dimension_preview"):
            self.dimension_preview.set_mode(mode)
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
        self.design_method.currentIndexChanged.connect(self._design_method_changed)
        self.design_method.currentIndexChanged.connect(self._sync_method_cards)
        self.speaker_type.currentTextChanged.connect(self._sync_speaker_cards)
        self.profile.currentIndexChanged.connect(self._sync_profile_cards)
        self.target_curve.curveChanged.connect(self._target_curve_changed)
        self.target_curve.analysisModeChanged.connect(self._update_sound_lab)
        for control in (self.max_width, self.max_height, self.max_depth, self.max_volume,
                        self.budget, self.target_spl, self.target_f3, self.power,
                        self.preferred_size, self.thickness):
            control.valueChanged.connect(self._mark_stale)
        self.options.toggled.connect(self._mark_stale)
        for control in (self.max_width, self.max_height, self.max_depth):
            control.valueChanged.connect(self._update_dimension_preview)
        self._update_dimension_preview()

    def _set_design_method_value(self, value: str) -> None:
        index = self.design_method.findData(value)
        if index >= 0:
            self.design_method.setCurrentIndex(index)

    def _set_speaker_type_value(self, value: str) -> None:
        self.speaker_type.setCurrentText(value)

    def _set_profile_value(self, value: str) -> None:
        index = self.profile.findData(value)
        if index >= 0:
            self.profile.setCurrentIndex(index)

    def _sync_method_cards(self, _index: int = 0) -> None:
        if hasattr(self, "method_cards"):
            self.method_cards.set_value(str(self.design_method.currentData()))

    def _sync_speaker_cards(self, value: str) -> None:
        if hasattr(self, "speaker_cards"):
            self.speaker_cards.set_value(value)

    def _sync_profile_cards(self, _index: int = 0) -> None:
        if hasattr(self, "profile_cards"):
            self.profile_cards.set_value(str(self.profile.currentData()))

    def _update_dimension_preview(self, *_args: object) -> None:
        if hasattr(self, "dimension_preview"):
            self.dimension_preview.set_dimensions(
                self.max_width.value(), self.max_height.value(), self.max_depth.value()
            )

    def _result_tab_changed(self, index: int) -> None:
        on_drawings = self.tabs.tabText(index) == "Zeichnungen"
        self.focus_button.setVisible(on_drawings)
        if on_drawings and self.drawing_mode.currentData() == "read":
            if not self.focus_button.isChecked():
                self.focus_button.setChecked(True)
            self._drawing_view_changed(self.drawing_tabs.currentIndex())
        elif not on_drawings and self.focus_button.isChecked():
            self.focus_button.setChecked(False)

    def _toggle_details(self, on: bool) -> None:
        self.details.setVisible(on)
        self.details_toggle.setText(
            "Technische Details schließen" if on else "Warum empfohlen? · Technische Details"
        )

    def _select_variant_from_card(self, index: int) -> None:
        self.variant_list.setCurrentRow(index)
        self.variant_cards.select(index)

    def _toggle_technical_table(self, on: bool) -> None:
        self.comparison.setVisible(on)
        if on:
            self._apply_column_choice()

    def _drawing_mode_changed(self, _index: int = 0) -> None:
        read_mode = self.drawing_mode.currentData() == "read"
        self.drawing_hint.setText(
            "Lesemodus: Ansicht füllt die Breite; ideal zum Prüfen und Lesen."
            if read_mode else
            "Druckblatt: vollständiges Seitenlayout für PDF-/Exportkontrolle."
        )
        if read_mode and self.tabs.tabText(self.tabs.currentIndex()) == "Zeichnungen":
            if not self.focus_button.isChecked():
                self.focus_button.setChecked(True)
        self._drawing_view_changed(self.drawing_tabs.currentIndex())

    def _drawing_view_changed(self, _index: int = 0) -> None:
        view = self.drawing_tabs.currentWidget()
        if isinstance(view, ZoomableSvgView):
            if self.drawing_mode.currentData() == "read":
                view.fit_width()
            else:
                view.fit()
        elif view is not None and hasattr(self, "panel_svg"):
            if self.drawing_mode.currentData() == "read":
                self.panel_svg.fit_width()
            else:
                self.panel_svg.fit()

    def _design_method_changed(self, _index: int = 0) -> None:
        target_mode = self.design_method.currentData() == "target_curve"
        self.create_button.setText(
            "Passenden Entwurf zur Zielkurve berechnen" if target_mode else "Entwurf erstellen"
        )
        if target_mode:
            self.tabs.setCurrentWidget(self.sound_tab)
            self._set_state(
                "info",
                "Zielkurvenmodus aktiv · Forme den gewünschten Verlauf. "
                "Bewertet wird nur, was vorhandene Treiber-/Simulationsdaten belegen.",
            )
        else:
            self._set_state(
                "info",
                "Klassischer Entwurf · Typ, Bauraum und Klangprofil wählen.",
            )
        self._mark_stale()

    def _target_curve_changed(self) -> None:
        self._update_sound_lab()
        if self.design_method.currentData() != "target_curve":
            return
        self._mark_stale()
        if not self.designs:
            self._set_state(
                "info",
                "Zielkurve geändert · Randbedingungen prüfen und passenden Entwurf berechnen.",
            )

    @staticmethod
    def _sound_curve(
        design: SpeakerDesign,
    ) -> tuple[np.ndarray, np.ndarray, str] | None:
        crossover = design.bundle.crossover_response
        if crossover is not None and crossover.sum_acoustic_db is not None:
            return (
                np.asarray(crossover.frequencies_hz, dtype=float),
                np.asarray(crossover.sum_acoustic_db, dtype=float),
                "Ist · FRD/Weichensumme",
            )
        response = design.bundle.vented_response or design.bundle.sealed_response
        if response is None:
            return None
        return (
            np.asarray(response.frequencies_hz, dtype=float),
            np.asarray(response.response_db, dtype=float),
            "Ist · Gehäuse-/Tieftonsimulation",
        )

    @staticmethod
    def _relative_curve(
        frequencies: np.ndarray, levels: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        valid = np.isfinite(frequencies) & np.isfinite(levels) & (frequencies > 0)
        f = frequencies[valid]
        v = levels[valid].astype(float, copy=True)
        if not f.size:
            return f, v
        reference = (f >= 80.0) & (f <= 120.0)
        v -= float(np.median(v[reference])) if np.any(reference) else float(np.median(v))
        return f, v

    def _update_sound_lab(self, *_args: object) -> None:
        if not hasattr(self, "target_curve"):
            return
        current = self._current()
        if current is None:
            self.target_curve.set_candidate_curves(())
            self.target_curve.clear_actual()
            self.target_curve.set_influence_summary(
                "Berechne zuerst Varianten; danach zeigt die Hülle nur tatsächlich gefundene Lösungen."
            )
            return

        mode = self.target_curve.analysis_mode()
        current_enclosure = current.project.enclosure.enclosure_type
        current_driver = current.woofer.model

        candidates = list(self.designs)
        if mode == "enclosure":
            candidates = [d for d in candidates if d.woofer.model == current_driver]
        elif mode == "driver":
            candidates = [
                d for d in candidates
                if d.project.enclosure.enclosure_type == current_enclosure
            ]
        elif mode == "crossover":
            candidates = [
                d for d in candidates
                if d.bundle.crossover_response is not None
                and d.bundle.crossover_response.sum_acoustic_db is not None
            ]

        curves: list[tuple[np.ndarray, np.ndarray]] = []
        for design in candidates:
            data = self._sound_curve(design)
            if data is not None:
                curves.append((data[0], data[1]))
        self.target_curve.set_candidate_curves(curves)

        current_curve = self._sound_curve(current)
        if current_curve is not None:
            self.target_curve.set_actual_curve(
                current_curve[0], current_curve[1], label=current_curve[2]
            )
        else:
            self.target_curve.clear_actual()

        notes: list[str] = []
        outside = self.target_curve.outside_envelope()
        if outside is not None:
            notes.append(
                f"Ziel bei {outside[0]:.0f} Hz liegt etwa {outside[1]:.1f} dB außerhalb "
                "der aktuell berechneten Variantenhülle."
            )

        if mode == "crossover" and not candidates:
            notes.append(
                "Für eine belastbare Weichen-/Fullrange-Aussage fehlen FRD-Daten. "
                "Vorhandene T/S-Daten reichen dafür absichtlich nicht."
            )
        elif mode == "dsp":
            response = current.bundle.vented_response or current.bundle.sealed_response
            xmax = current.bundle.project.driver.xmax_mm
            if response is not None and response.excursion_mm is not None and xmax:
                margins: list[tuple[float, float]] = []
                rf = np.asarray(response.frequencies_hz, dtype=float)
                ex = np.asarray(response.excursion_mm, dtype=float)
                for frequency, target_db in self.target_curve.points():
                    if frequency < rf[0] or frequency > rf[-1] or target_db <= 0:
                        continue
                    excursion = float(np.interp(np.log10(frequency), np.log10(rf), ex))
                    if excursion > 0:
                        headroom_db = 20*np.log10(xmax/excursion)
                        margins.append((frequency, headroom_db-target_db))
                if margins:
                    frequency, margin = min(margins, key=lambda item: item[1])
                    if margin < 0:
                        notes.append(
                            f"DSP-Anhebung bei {frequency:.0f} Hz überschreitet die berechnete "
                            f"Hubreserve um etwa {-margin:.1f} dB. Gehäuse/Chassis ändern statt nur boosten."
                        )
                    else:
                        notes.append(
                            f"Tiefton-DSP bleibt in den geprüften Punkten mindestens {margin:.1f} dB "
                            "unter der berechneten Xmax-Grenze."
                        )
            else:
                notes.append("DSP-Headroom ist ohne belastbare Hubdaten nicht quantifizierbar.")

        if mode in {"overall", "enclosure", "driver", "influence"} and current_curve is not None:
            cf, cv = self._relative_curve(current_curve[0], current_curve[1])
            best: tuple[float, int, float, float] | None = None
            targets = self.target_curve.points()
            for alt_index, alternative in enumerate(self.designs):
                if alternative is current:
                    continue
                if mode == "enclosure" and alternative.woofer.model != current_driver:
                    continue
                if mode == "driver" and (
                    alternative.project.enclosure.enclosure_type != current_enclosure
                ):
                    continue
                alt_curve = self._sound_curve(alternative)
                if alt_curve is None:
                    continue
                af, av = self._relative_curve(alt_curve[0], alt_curve[1])
                for frequency, target_db in targets:
                    if (
                        not cf.size or not af.size
                        or frequency < cf[0] or frequency > cf[-1]
                        or frequency < af[0] or frequency > af[-1]
                    ):
                        continue
                    current_db = float(np.interp(np.log10(frequency), np.log10(cf), cv))
                    alternative_db = float(np.interp(np.log10(frequency), np.log10(af), av))
                    improvement = abs(current_db-target_db)-abs(alternative_db-target_db)
                    if improvement > 1.0 and (best is None or improvement > best[0]):
                        best = (improvement, alt_index, frequency, alternative_db)
            if best is not None:
                improvement, alt_index, frequency, _alternative_db = best
                alternative = self.designs[alt_index]
                enclosure = registry.get(
                    alternative.project.enclosure.enclosure_type
                ).label
                change = (
                    f"anderes Gehäuse ({enclosure})"
                    if alternative.woofer.model == current_driver
                    else f"anderes Chassis ({alternative.woofer.model})"
                )
                notes.append(
                    f"Bei {frequency:.0f} Hz liegt {alternative.label} rund {improvement:.1f} dB "
                    f"näher am Ziel – hier wäre {change} die bessere Richtung."
                )

        if not notes:
            notes.append(
                f"{len(curves)} berechnete Kurve(n) bilden die aktuell belegbare Vergleichsbasis."
            )
        self.target_curve.set_influence_summary(" ".join(notes))

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
        self.variant_list.setVisible(False)
        self.comparison.setRowCount(0)
        self.comparison.setVisible(False)
        self.all_columns.blockSignals(True)
        self.all_columns.setChecked(False)
        self.all_columns.blockSignals(False)
        self.variant_cards.set_designs(())
        self.details.clear()
        self.details_toggle.blockSignals(True)
        self.details_toggle.setChecked(False)
        self.details_toggle.blockSignals(False)
        self.details.setVisible(False)
        self.details_toggle.setText("Warum empfohlen? · Technische Details")
        self.selected_title.setText("Noch kein Entwurf")
        self.recommendation_summary.setText(
            "Nach der Berechnung stehen hier die wichtigsten Gründe für die Empfehlung."
        )
        self.empty_guide.setVisible(True)
        if hasattr(self, "preview"):
            self.preview.set_bundle(None)
        self.kpi_row.setVisible(False)
        empty = QByteArray(b"<svg xmlns='http://www.w3.org/2000/svg' width='10' height='10'/>")
        for view in (self.svg, self.dimension_svg, self.internal_svg, self.panel_svg):
            view.load(empty)
        self.panel_choice.clear()
        self.bom_view.clear()
        self.cutting_panel.set_bundle(None)
        self.figure.clear()
        self.canvas.draw_idle()
        if hasattr(self, "target_curve"):
            self.target_curve.clear_actual()
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
        self.project_name = QLineEdit("Mein Lautsprecher")
        self.project_name.setPlaceholderText("Projektname")
        layout.addWidget(self.project_name)

        method_box = QGroupBox("Wie möchtest du starten?")
        method_layout = QVBoxLayout(method_box)
        method_layout.setContentsMargins(0, 12, 0, 0)
        self.design_method = QComboBox()
        self.design_method.addItem("Klassisch konfigurieren", "classic")
        self.design_method.addItem("Über Zielkurve konfigurieren", "target_curve")
        self.design_method.setVisible(False)
        self.method_cards = ChoiceGrid((
            ("classic", "Klassisch", "Typ · Bauraum · Klangprofil"),
            ("target_curve", "Zielkurve", "Klang formen · passenden Entwurf suchen"),
        ), columns=1)
        self.method_cards.set_value("classic")
        self.method_cards.valueChanged.connect(self._set_design_method_value)
        method_layout.addWidget(self.method_cards)
        layout.addWidget(method_box)

        step1 = QGroupBox("1 · Was möchtest du bauen?")
        step1_layout = QVBoxLayout(step1)
        step1_layout.setContentsMargins(0, 12, 0, 0)
        self.speaker_type = QComboBox()
        for name in SPEAKER_TYPES:
            self.speaker_type.addItem(name)
        self.speaker_type.setCurrentText("Regallautsprecher")
        self.speaker_cards = ChoiceGrid((
            ("Regallautsprecher", "Regal", "kompakt · wohnraumtauglich"),
            ("Standlautsprecher", "Stand", "mehr Volumen · mehr Tiefgang"),
            ("Subwoofer", "Subwoofer", "Tiefton und Pegel"),
            ("Desktop-Lautsprecher", "Desktop", "Nahfeld · kompakt"),
            ("Studio-Monitor", "Monitor", "präzise · kontrolliert"),
            ("Custom", "Custom", "freie Vorgaben"),
        ))
        self.speaker_cards.set_value("Regallautsprecher")
        self.speaker_cards.valueChanged.connect(self._set_speaker_type_value)
        step1_layout.addWidget(self.speaker_cards)
        exact_type = QWidget()
        exact_form = self._form(exact_type)
        exact_form.addRow("Weitere / genaue Bauart", self.speaker_type)
        step1_layout.addWidget(exact_type)
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
        self.dimension_preview = DimensionPreview(self.mode)
        form2.addRow(self.dimension_preview)
        layout.addWidget(step2)

        step3 = QGroupBox("3 · Gewünschter Klang")
        step3_layout = QVBoxLayout(step3)
        step3_layout.setContentsMargins(0, 12, 0, 0)
        self.profile = QComboBox()
        for item in PROFILES.values():
            self.profile.addItem(item.label, item.id)
        self.profile.setVisible(False)
        self.profile_cards = ChoiceGrid((
            ("neutral", "Neutral", "ausgewogen · universell"),
            ("deep_bass", "Tiefbass", "tiefer · voller"),
            ("punch", "Punch", "Kickbass · Dynamik"),
            ("compact", "Kompakt", "kleiner vor maximalem Tiefgang"),
            ("precise", "Studio", "präzise · geringe Verzögerung"),
            ("max_spl", "Max SPL", "Pegel · Reserve"),
        ))
        self.profile_cards.set_value("neutral")
        self.profile_cards.valueChanged.connect(self._set_profile_value)
        step3_layout.addWidget(self.profile_cards)
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

    def _build_results(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.state = QLabel()
        self.state.setObjectName("statusLine")
        self.state.setWordWrap(True)
        layout.addWidget(self.state)
        self._set_state(
            "info",
            "Starte links mit Bauart, Bauraum und Klang – oder forme direkt eine Zielkurve.",
        )

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        # PLANEN – visualization first, technical detail on demand.
        overview = QWidget()
        ov = QVBoxLayout(overview)
        ov.setContentsMargins(0, 8, 0, 0)
        self.empty_guide = QLabel(
            "<h2>Dein Lautsprecher entsteht in drei Schritten</h2>"
            "<p><b>1.</b> Bauart wählen &nbsp; <b>2.</b> Bauraum festlegen &nbsp; "
            "<b>3.</b> Klangziel wählen oder Zielkurve formen.</p>"
            "<p>Nach der Berechnung erscheint hier der empfohlene Entwurf mit "
            "Visualisierung, Kennwerten und nachvollziehbarer Begründung.</p>"
        )
        self.empty_guide.setWordWrap(True)
        self.empty_guide.setObjectName("emptyState")
        ov.addWidget(self.empty_guide)

        # Hidden selector keeps the established selection API and project logic.
        self.variant_list = QListWidget()
        self.variant_list.setVisible(False)
        self.variant_list.currentRowChanged.connect(self._select_variant)

        result_body = QWidget()
        result_layout = QHBoxLayout(result_body)
        result_layout.setContentsMargins(0, 0, 0, 0)
        result_layout.setSpacing(16)

        self.preview = CabinetPreview(self.mode)
        result_layout.addWidget(self.preview, 7)

        side = QFrame()
        side.setObjectName("resultSidebar")
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(14, 14, 14, 14)
        side_layout.setSpacing(8)
        self.selected_title = QLabel("Noch kein Entwurf")
        self.selected_title.setObjectName("section")
        self.selected_title.setWordWrap(True)
        side_layout.addWidget(self.selected_title)

        self.kpi_row = QWidget()
        kpi_layout = QVBoxLayout(self.kpi_row)
        kpi_layout.setContentsMargins(0, 0, 0, 0)
        kpi_layout.setSpacing(6)
        self.kpis: dict[str, QLabel] = {}
        for key in ("Maße", "Tiefbass F3", "Preisstatus", "Datenqualität", "Prüfstatus"):
            label = QLabel()
            label.setObjectName("kpi")
            label.setWordWrap(True)
            kpi_layout.addWidget(label)
            self.kpis[key] = label
        self.kpi_row.setVisible(False)
        side_layout.addWidget(self.kpi_row)

        self.recommendation_summary = QLabel(
            "Nach der Berechnung stehen hier die wichtigsten Gründe für die Empfehlung."
        )
        self.recommendation_summary.setObjectName("recommendation")
        self.recommendation_summary.setWordWrap(True)
        side_layout.addWidget(self.recommendation_summary)

        self.details_toggle = QPushButton("Warum empfohlen? · Technische Details")
        self.details_toggle.setCheckable(True)
        self.details_toggle.toggled.connect(self._toggle_details)
        side_layout.addWidget(self.details_toggle)
        self.details = QTextBrowser()
        self.details.setVisible(False)
        self.details.setMinimumHeight(150)
        side_layout.addWidget(self.details, 1)
        result_layout.addWidget(side, 4)

        ov.addWidget(result_body, 1)
        self.tabs.addTab(overview, "Planen")

        # VARIANTEN – cards first, full engineering table only on request.
        compare = QWidget()
        compare_layout = QVBoxLayout(compare)
        compare_layout.setContentsMargins(0, 8, 0, 0)
        compare_intro = QLabel(
            "Vergleiche die wichtigsten Trade-offs zuerst. Die vollständige technische "
            "Tabelle ist optional."
        )
        compare_intro.setObjectName("caption")
        compare_intro.setWordWrap(True)
        compare_layout.addWidget(compare_intro)
        self.variant_cards = VariantCards()
        self.variant_cards.selected.connect(self._select_variant_from_card)
        compare_layout.addWidget(self.variant_cards)

        self.all_columns = QCheckBox("Alle technischen Daten anzeigen")
        self.all_columns.toggled.connect(self._toggle_technical_table)
        compare_layout.addWidget(self.all_columns)
        self.comparison = QTableWidget()
        self.comparison.setColumnCount(11)
        self.comparison.setHorizontalHeaderLabels((
            "Variante", "Gehäuse", "B × H × T [mm]", "Netto [l]", "F3 [Hz]",
            "Bewertung", "Chassiswahl", "Chassis [€]", "Gesamt inkl. Reserve [€]",
            "Budget frei [€]", "Hinweise",
        ))
        self.comparison.setAlternatingRowColors(True)
        self.comparison.setWordWrap(True)
        self.comparison.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.comparison.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.comparison.cellClicked.connect(
            lambda row, _column: self.variant_list.setCurrentRow(row)
        )
        self.comparison.setVisible(False)
        compare_layout.addWidget(self.comparison, 1)
        self.tabs.addTab(compare, "Varianten")

        # KLANG – target-first workflow plus detailed technical charts.
        simulation = QWidget()
        self.sound_tab = simulation
        sim_layout = QVBoxLayout(simulation)
        sim_layout.setContentsMargins(0, 8, 0, 0)
        sound_views = QTabWidget()
        sound_views.setDocumentMode(True)
        self.target_curve = TargetCurveEditor(self.mode)
        sound_views.addTab(self.target_curve, "Zielkurve")
        technical = QWidget()
        technical_layout = QVBoxLayout(technical)
        self.more_charts = QCheckBox("Weitere Diagramme (Port, Gruppenlaufzeit)")
        self.more_charts.toggled.connect(self._redraw_simulation)
        technical_layout.addWidget(self.more_charts)
        self.figure = Figure(figsize=(9, 6), layout="constrained")
        self.canvas = FigureCanvasQTAgg(self.figure)
        technical_layout.addWidget(self.canvas, 1)
        sound_views.addTab(technical, "Technische Simulation")
        sim_layout.addWidget(sound_views, 1)
        self.tabs.addTab(simulation, "Klang & Simulation")

        # ZEICHNUNGEN – explicit screen reading vs. print-sheet mode.
        drawing_root = QWidget()
        drawing_layout = QVBoxLayout(drawing_root)
        drawing_layout.setContentsMargins(0, 8, 0, 0)
        drawing_bar = QHBoxLayout()
        drawing_bar.addWidget(QLabel("Darstellung"))
        self.drawing_mode = QComboBox()
        self.drawing_mode.addItem("Lesemodus · groß und direkt lesbar", "read")
        self.drawing_mode.addItem("Druckblatt · Seitenlayout prüfen", "print")
        self.drawing_mode.currentIndexChanged.connect(self._drawing_mode_changed)
        drawing_bar.addWidget(self.drawing_mode)
        self.drawing_hint = QLabel("Lesemodus nutzt automatisch die verfügbare Breite.")
        self.drawing_hint.setObjectName("caption")
        drawing_bar.addWidget(self.drawing_hint, 1)
        drawing_layout.addLayout(drawing_bar)

        self.drawing_tabs = QTabWidget()
        self.drawing_tabs.setDocumentMode(True)
        self.drawing_tabs.currentChanged.connect(self._drawing_view_changed)
        self.svg = ZoomableSvgView()
        self.drawing_tabs.addTab(self.svg, "Übersicht")
        self.dimension_svg = ZoomableSvgView()
        self.drawing_tabs.addTab(self.dimension_svg, "Maße")
        self.internal_svg = ZoomableSvgView()
        self.drawing_tabs.addTab(self.internal_svg, "Innenaufbau")
        panel = QWidget()
        panel_layout = QVBoxLayout(panel)
        self.panel_choice = QComboBox()
        self.panel_choice.currentIndexChanged.connect(self._show_panel_sheet)
        panel_layout.addWidget(self.panel_choice)
        self.panel_svg = ZoomableSvgView()
        panel_layout.addWidget(self.panel_svg, 1)
        self.drawing_tabs.addTab(panel, "Einzelteile")
        drawing_layout.addWidget(self.drawing_tabs, 1)
        self.tabs.addTab(drawing_root, "Zeichnungen")

        # FERTIGUNG – BOM, cutting and export live in one contextual workspace.
        manufacturing = QWidget()
        manufacturing_layout = QVBoxLayout(manufacturing)
        manufacturing_layout.setContentsMargins(0, 8, 0, 0)
        self.manufacturing_tabs = QTabWidget()
        self.manufacturing_tabs.setDocumentMode(True)
        self.bom_view = QTextBrowser()
        self.manufacturing_tabs.addTab(self.bom_view, "Stückliste")
        self.cutting_panel = CuttingPanel(self.settings)
        self.manufacturing_tabs.addTab(self.cutting_panel, "Zuschnitt")
        export_page = QWidget()
        export_layout = QVBoxLayout(export_page)
        export_title = QLabel("Fertigungsunterlagen")
        export_title.setObjectName("section")
        export_layout.addWidget(export_title)
        export_info = QLabel(
            "Exportiert die geprüften Zeichnungen, DXF/PDF, Stückliste und weitere "
            "Fertigungsdaten des aktuell ausgewählten Entwurfs."
        )
        export_info.setWordWrap(True)
        export_info.setObjectName("caption")
        export_layout.addWidget(export_info)
        export_layout.addStretch(1)
        self.export_button = QPushButton("Fertigungsunterlagen exportieren")
        self.export_button.setObjectName("primary")
        self.export_button.clicked.connect(self._export)
        export_layout.addWidget(self.export_button)
        self.manufacturing_tabs.addTab(export_page, "Export")
        manufacturing_layout.addWidget(self.manufacturing_tabs, 1)
        self.tabs.addTab(manufacturing, "Fertigung")

        self.tabs.currentChanged.connect(self._result_tab_changed)
        layout.addWidget(self.tabs, 1)

        # File operations remain available through menu/shortcuts and autosave.
        self.save_button = QPushButton("Projekt speichern")
        self.save_button.clicked.connect(self._save)
        self.save_button.setVisible(False)
        self.load_button = QPushButton("Projekt laden")
        self.load_button.clicked.connect(self._load)
        self.load_button.setVisible(False)
        self.save_button.setEnabled(False)
        self.export_button.setEnabled(False)
        return container

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
            target_f3_hz=self.target_f3.value() or None if optional else None,
            way_count=self.ways.currentData() if optional else None,
            active=self.active_mode.currentData() if optional else False,
            preferred_size_m=self.preferred_size.value()/1000 if optional and self.preferred_size.value() else None,
            amplifier_power_w=self.power.value() if optional else 5,
            panel_thickness_m=self.thickness.value()/1000 if optional else .018,
            preferred_manufacturer=self.manufacturer.text().strip() or None if optional else None,
            preferred_driver=self.driver_choice.currentData(),
            material=self.material.currentText() if optional else "Birke Multiplex",
            target_curve_points=(self.target_curve.points()
                if self.design_method.currentData() == "target_curve" else None),
            target_curve_preset=self.target_curve.preset_id(),
            target_curve_mode=self.target_curve.analysis_mode())

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
    _CORE_COLUMNS = (0, 1, 2, 4, 8, 10)

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
            self.variant_list.setVisible(False)
            self.empty_guide.setVisible(False)
            self.variant_cards.set_designs(result.designs)
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
            self.comparison.resizeColumnsToContents()
            self._apply_column_choice()
            self.save_button.setEnabled(True)
            self.variant_list.setCurrentRow(0)
        elif result.status == "impossible":
            self.progress_label.setText(f"{result.candidates_tested} Kandidaten geprüft")
            self._set_state(
                "danger",
                "Mit diesen Vorgaben ist kein sinnvoller Entwurf möglich. "
                "Die wirksamsten Änderungen stehen unter „Planen“.",
            )
            reasons = "".join(f"<li>{escape(item)}</li>" for item in result.rejection_reasons)
            changes = "".join(f"<li>{escape(item)}</li>" for item in result.suggested_constraint_changes)
            self._clear_results()
            self._stale = True
            self.empty_guide.setVisible(False)
            self.selected_title.setText("Nicht machbar")
            self.recommendation_summary.setText(
                "Die aktuellen Randbedingungen schließen alle geprüften Varianten aus. "
                "Öffne die technischen Details für Ursachen und konkrete Änderungsvorschläge."
            )
            self.details.setHtml(
                f"<h2>Nicht machbar</h2><b>Gründe</b><ul>{reasons}</ul>"
                f"<b>Mögliche Änderungen</b><ul>{changes}</ul>"
            )
            self.details_toggle.setChecked(True)
            self.tabs.setCurrentIndex(0)
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
        self.variant_cards.select(index)
        self.empty_guide.setVisible(False)
        self.selected_title.setText(design.label)
        reasons = tuple(design.reasons[:3])
        self.recommendation_summary.setText(
            "Warum passend:\n" + "\n".join(f"• {reason}" for reason in reasons)
            if reasons else "Die Variante erfüllt die aktuell bewertbaren Randbedingungen."
        )
        self.details_toggle.setChecked(False)
        self.preview.set_bundle(bundle)
        self.cutting_panel.set_bundle(bundle)
        c = bundle.cabinet
        f3 = bundle.sealed.f3_hz if bundle.sealed else (
            bundle.vented_response.f3_hz if bundle.vented_response else None)
        lines = [f"<h2>{escape(design.label)}</h2>",
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
            lines.append(f"<h3>Teilbewertung · {design.score:.0f}/100 aus {len(design.breakdown)} "
                         "bewerteten Kriterien</h3><p>Keine Qualitätsfreigabe: nicht belegbare Kriterien "
                         "fließen nicht ein.</p>")
            names = {"bass": "Tiefbass", "size": "Kompaktheit", "headroom": "Auslenkungsreserve",
                "port": "Portreserve", "delay": "Gruppenlaufzeit", "flatness": "Linearität",
                "cost": "Budgetreserve", "target_curve": "Nähe zur Zielkurve"}
            for metric in design.breakdown:
                lines.append(f"<p><b>{names.get(metric.name, metric.name)}</b> "
                    f"{metric.value:.0f}/100 "
                    f"(Gewicht {metric.weight:g})<br>{escape(metric.evidence)}</p>")
            missing = {"headroom", "port", "delay", "flatness"}-{
                metric.name for metric in design.breakdown}
            if bundle.port is None:
                missing.discard("port")
            if missing:
                lines.append("<p><i>Nicht bewertet: "+", ".join(names[key] for key in sorted(missing))+
                    ". Nicht verfügbare Werte werden nicht ergänzt.</i></p>")
        lines.append("<h3>Warum dieser Entwurf?</h3><ul>"+
            "".join(f"<li>{escape(reason)}</li>" for reason in design.reasons)+"</ul>")
        if design.provisional_crossover:
            lines.append("<p><b>Vorläufiger Frequenzweichenentwurf:</b> Für eine Endabstimmung "
                "sind FRD/ZMA-Messungen am aufgebauten Lautsprecher nötig.</p>")
        if bundle.warnings:
            lines.append("<h3>Hinweise</h3><ul>"+
                "".join(f"<li>{escape(message)}</li>" for message in bundle.warnings)+"</ul>")
        self.details.setHtml("".join(lines))
        geometry_issue_count = sum(1 for issue in bundle.issues if issue.severity == "error")
        self.kpis["Maße"].setText(f"<b>Maße</b><br>{c.width_m*1000:.0f} × {c.height_m*1000:.0f} × "
                                  f"{c.depth_m*1000:.0f} mm")
        self.kpis["Tiefbass F3"].setText(f"<b>Tiefbass F3</b><br>{f'{f3:.0f} Hz' if f3 else 'nicht berechenbar'}")
        self.kpis["Preisstatus"].setText("<b>Preisstatus</b><br>" + (
            f"{design.total_price_eur:.0f} € inkl. Reserve" if design.total_price_eur is not None
            else "unvollständig bepreist"))
        self.kpis["Datenqualität"].setText("<b>Datenqualität</b><br>" + (
            "vorläufige Weiche" if design.provisional_crossover else "Herstellerdaten, Quelle je Chassis prüfen"))
        self.kpis["Prüfstatus"].setText("<b>Prüfstatus</b><br>" + (
            f"✕ {geometry_issue_count} Geometriefehler" if geometry_issue_count else
            f"⚠ {len(bundle.warnings)} Hinweise" if bundle.warnings else "✓ keine Hinweise"))
        self.kpi_row.setVisible(True)
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
            if hasattr(self, "target_curve"):
                self.target_curve.clear_actual()
            return
        bundle = design.bundle
        r = bundle.vented_response or bundle.sealed_response
        if r is not None:
            self.target_curve.set_actual_curve(r.frequencies_hz, r.response_db)
        else:
            self.target_curve.clear_actual()
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
            self._drawing_view_changed(self.drawing_tabs.currentIndex())

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
            self._drawing_view_changed(self.drawing_tabs.currentIndex())

        if not on:
            self.wizard_panel.setVisible(True)
        animate_value(self.split, sizes[0], target, apply, reduced=self.reduced_motion, finished=done)
        self.focus_button.setText("Eingaben zeigen" if on else "Zeichnung groß anzeigen")
        if on:
            for index in range(self.tabs.count()):
                if self.tabs.tabText(index) == "Zeichnungen":
                    self.tabs.setCurrentIndex(index)
                    break

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
        self.variant_cards.set_designs(self.designs)
        self.empty_guide.setVisible(False)
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
                Path(filename).write_text(design.project.model_dump_json(indent=2), encoding="utf-8")
            except OSError as exc:
                LOG.warning("Speichern fehlgeschlagen: %s", exc)
                QMessageBox.warning(self, "Speichern fehlgeschlagen", str(exc))
                return
            self._unsaved = False
            self.autosave.discard()
            self.recent.add(filename)
            self._refresh_recent_menu()
            self.statusBar().showMessage(f"Projekt gespeichert: {filename}")

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
            self.autosave.write(design.project.model_dump_json(indent=2))
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
