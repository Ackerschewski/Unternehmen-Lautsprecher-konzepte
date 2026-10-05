from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from pydantic import ValidationError
from PySide6.QtCore import QByteArray, Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from lautsprecher_konstruktion import REVISION
from lautsprecher_konstruktion.acoustics.alignment import suggest_alignments
from lautsprecher_konstruktion.acoustics.baffle_step import baffle_step_db, baffle_step_frequency_hz
from lautsprecher_konstruktion.acoustics.response import sealed_response_db
from lautsprecher_konstruktion.crossover.measurements import load_frd, load_zma
from lautsprecher_konstruktion.drawings.assembly_svg import render_assembly_svg
from lautsprecher_konstruktion.drivers.catalog import DriverCatalog
from lautsprecher_konstruktion.drivers.models import Driver
from lautsprecher_konstruktion.enclosure.layout import FrontElement
from lautsprecher_konstruktion.export.package import export_project_package
from lautsprecher_konstruktion.project.demo import demo_project
from lautsprecher_konstruktion.project.models import (
    CrossoverConfig,
    EnclosureConfig,
    ProjectAccessory,
    SpeakerProject,
)
from lautsprecher_konstruktion.services.design import DesignBundle, calculate_project
from lautsprecher_konstruktion.ui.cutting_panel import stored_cutting_settings
from lautsprecher_konstruktion.ui.history import History
from lautsprecher_konstruktion.ui.layout_canvas import FrontLayoutCanvas
from lautsprecher_konstruktion.ui.prototype_dialog import PrototypeDialog


class MainWindow(QMainWindow):
    projectCalculated = Signal(object)
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"Lautsprecher Konstruktion {REVISION} · Expertenmodus")
        self.resize(1450, 900)
        self._bundle: DesignBundle | None = None
        self._catalog = DriverCatalog()
        self._front_elements: list[FrontElement] = []
        self._history: History[tuple[FrontElement, ...]] = History((), merge_window_s=2.0)
        self._measurements: dict[str, object] = {}
        self._base_driver: Driver | None = None
        self._additional_drivers: tuple[Driver, ...] = ()
        self._accessories: tuple[ProjectAccessory, ...] = ()
        self._notes = ""
        self._round_to_standard = False
        self._dirty = False
        self._loading = False
        self._run_count = 0
        self._change_note = "Erste Berechnung"

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self._editor_widget = self._build_editor()
        splitter.addWidget(self._editor_widget)
        splitter.addWidget(self._build_output())
        splitter.setSizes([560, 890])
        self.setCentralWidget(splitter)

        self.statusBar().showMessage("Bereit")
        for sequence, slot in (("Ctrl+Z", self._undo), ("Ctrl+Y", self._redo), ("Ctrl+Shift+Z", self._redo)):
            QShortcut(QKeySequence(sequence), self, activated=slot)
        self._refresh_mode_controls()
        self._load_demo()
        self._connect_dirty_signals()

    def _build_editor(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)

        title = QLabel("Lautsprecher Konstruktion")
        title.setStyleSheet("font-size: 22px; font-weight: 650;")
        layout.addWidget(title)

        self.project_name = QLineEdit("Neues Lautsprecherprojekt")
        layout.addWidget(self.project_name)

        catalog_row = QHBoxLayout()
        self.catalog_combo = QComboBox()
        self.catalog_combo.addItem("Manuelle Eingabe", None)
        self.catalog_combo.currentIndexChanged.connect(self._catalog_selected)
        catalog_row.addWidget(self.catalog_combo, 1)

        load_catalog = QPushButton("Treiberdatei laden")
        load_catalog.clicked.connect(self._load_catalog)
        catalog_row.addWidget(load_catalog)

        load_project = QPushButton("Projekt laden")
        load_project.clicked.connect(self._load_project)
        catalog_row.addWidget(load_project)
        demo = QPushButton("Demo laden")
        demo.clicked.connect(self._load_demo)
        catalog_row.addWidget(demo)
        save_project = QPushButton("Projekt speichern")
        save_project.clicked.connect(self._save_project)
        catalog_row.addWidget(save_project)
        layout.addLayout(catalog_row)

        tabs = QTabWidget()
        tabs.addTab(self._scroll(self._build_driver_tab()), "Treiber")
        tabs.addTab(self._scroll(self._build_enclosure_tab()), "Gehäuse")
        tabs.addTab(self._scroll(self._build_layout_tab()), "Frontlayout")
        tabs.addTab(self._scroll(self._build_crossover_tab()), "Frequenzweiche")
        layout.addWidget(tabs, 1)

        action_row = QHBoxLayout()
        self.calculate_button = QPushButton("Projekt berechnen")
        self.calculate_button.setStyleSheet("font-weight: 600; padding: 8px;")
        self.calculate_button.clicked.connect(lambda: self.calculate(show_results=True))
        action_row.addWidget(self.calculate_button)

        self.export_button = QPushButton("Fertigungsunterlagen exportieren")
        self.export_button.setStyleSheet("font-weight: 600; padding: 8px;")
        self.export_button.clicked.connect(self.export)
        action_row.addWidget(self.export_button)
        self.prototype_button = QPushButton("Prototyp vergleichen…")
        self.prototype_button.setStyleSheet("padding: 8px;")
        self.prototype_button.clicked.connect(self._compare_prototype)
        action_row.addWidget(self.prototype_button)
        layout.addLayout(action_row)
        return container

    @staticmethod
    def _scroll(widget: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)
        return scroll

    def _build_driver_tab(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)

        self.manufacturer = QLineEdit("Example")
        self.driver_model = QLineEdit("Demo Woofer")
        self.fs = self._spin(1.0, 1000.0, 32.0, " Hz")
        self.qts = self._spin(0.05, 2.0, 0.36, "", 3)
        self.qes = self._spin(0.0, 20.0, 0.4, "", 3)
        self.qms = self._spin(0.0, 100.0, 3.6, "", 3)
        self.vas = self._spin(0.01, 5000.0, 58.0, " l")
        self.impedance = self._spin(1.0, 32.0, 8.0, " Ohm")
        self.re = self._spin(0.0, 50.0, 5.8, " Ohm", 3)
        self.le = self._spin(0.0, 50.0, 1.1, " mH", 3)
        self.sd = self._spin(0.0, 5000.0, 350.0, " cm²")
        self.xmax = self._spin(0.0, 100.0, 6.0, " mm")
        self.power_rating = self._spin(0.0, 5000.0, 100.0, " W")
        self.driver_displacement = self._spin(0.0, 50.0, 1.8, " l")
        self.cutout = self._spin(0.0, 1000.0, 230.0, " mm")
        self.outer_diameter = self._spin(0.0, 1000.0, 260.0, " mm")
        self.mounting_depth = self._spin(0.0, 1000.0, 115.0, " mm")
        self.source_name = QLineEdit("Manuell")

        for label, control in [
            ("Hersteller", self.manufacturer),
            ("Modell", self.driver_model),
            ("Fs", self.fs),
            ("Qts", self.qts),
            ("Qes", self.qes),
            ("Qms", self.qms),
            ("Vas", self.vas),
            ("Nennimpedanz", self.impedance),
            ("Re", self.re),
            ("Le", self.le),
            ("Sd", self.sd),
            ("Xmax", self.xmax),
            ("Nennbelastbarkeit Pe", self.power_rating),
            ("Treiberverdrängung", self.driver_displacement),
            ("Einbauausschnitt", self.cutout),
            ("Außendurchmesser", self.outer_diameter),
            ("Einbautiefe", self.mounting_depth),
            ("Datenquelle", self.source_name),
        ]:
            form.addRow(label, control)
        return widget

    def _build_enclosure_tab(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)

        self.enclosure_type = QComboBox()
        self.enclosure_type.addItem("Geschlossen", "sealed")
        self.enclosure_type.addItem("Bassreflex", "bass_reflex")
        self.enclosure_type.addItem("Aperiodisch", "aperiodic")
        self.enclosure_type.addItem("Passivmembran", "passive_radiator")
        self.enclosure_type.addItem("Bandpass 4. Ordnung", "bandpass_4")
        self.enclosure_type.addItem("Bandpass 6. Ordnung parallel", "bandpass_6_parallel")
        self.enclosure_type.addItem("Bandpass 6. Ordnung seriell", "bandpass_6_series")
        self.enclosure_type.addItem("Isobarisch geschlossen", "isobaric_sealed")
        self.enclosure_type.addItem("Compound / Push Pull", "compound_push_pull")
        self.enclosure_type.addItem("Isobarisch Bassreflex", "isobaric_vented")
        self.enclosure_type.addItem("Transmission Line geschlossen", "transmission_line_closed")
        self.enclosure_type.addItem("Transmission Line offen", "transmission_line_open")
        self.enclosure_type.addItem("Transmission Line verjüngt", "transmission_line_tapered")
        self.enclosure_type.addItem("Mass Loaded Transmission Line", "mltl")
        self.enclosure_type.addItem("TQWT", "tqwt")
        self.enclosure_type.addItem("Labyrinth", "labyrinth")
        self.enclosure_type.addItem("Rearloaded Horn · segmentiert", "horn_rear")
        self.enclosure_type.addItem("Folded Horn · segmentiert", "horn_folded")
        self.enclosure_type.addItem("Scoop · segmentiert", "horn_scoop")
        self.enclosure_type.addItem("Exponentialhorn · segmentiert", "horn_exponential")
        self.enclosure_type.addItem("Tractrixhorn · segmentiert", "horn_tractrix")
        self.enclosure_type.addItem("Konisches Horn · segmentiert", "horn_conical")
        self.enclosure_type.addItem("Hyperbolisches Horn · segmentiert", "horn_hyperbolic")
        self.enclosure_type.addItem("Infinite Baffle / Wandeinbau", "infinite_baffle")
        self.enclosure_type.addItem("Open Baffle / flache Schallwand", "open_baffle")
        self.enclosure_type.addItem("Dipol / U-Frame", "dipole")
        self.enclosure_type.addItem("Passiv-Kardioid", "cardioid")
        self.enclosure_type.addItem("Frontloaded Horn", "horn_front")
        self.enclosure_type.addItem("Tapped Horn · 2 Läufe", "horn_tapped")
        self.enclosure_type.currentIndexChanged.connect(self._refresh_mode_controls)

        self.target_qtc = self._spin(0.1, 2.0, 0.707, "", 3)
        self.target_volume = self._spin(0.1, 2000.0, 45.0, " l")
        self.rear_volume = self._spin(0.1, 2000.0, 50.0, " l")
        self.rear_tuning = self._spin(5.0, 300.0, 30.0, " Hz")
        self.rear_port_diameter = self._spin(10.0, 500.0, 75.0, " mm")
        self.aperiodic_resistance = self._spin(0.0, 1000000.0, 0.0, " Pa·s/m³", 0)
        self.baffle_wing_depth = self._spin(0.0, 1000.0, 150.0, " mm")
        self.cardioid_delay = self._spin(0.0, 10.0, 0.5, " ms", 2)
        self.isobaric_wiring = QComboBox()
        self.isobaric_wiring.addItem("Reihe", "series")
        self.isobaric_wiring.addItem("Parallel", "parallel")
        self.isobaric_gap = self._spin(10.0, 200.0, 20.0, " mm")
        self.tuning = self._spin(5.0, 300.0, 35.0, " Hz")
        self.radiator_sd = self._spin(1, 5000, 350, " cm²")
        self.radiator_mms = self._spin(1, 5000, 80, " g")
        self.radiator_fs = self._spin(1, 300, 20, " Hz")
        self.radiator_qms = self._spin(0.1, 100, 5, "", 2)
        self.radiator_xmax = self._spin(0.1, 100, 12, " mm")
        self.radiator_cutout = self._spin(10, 1000, 230, " mm")
        self.radiator_depth = self._spin(1, 500, 60, " mm")
        self.input_power = self._spin(0.1, 5000.0, 10.0, " W")
        self.power_preset=QComboBox()
        for label,value in (("1 W",1.0),("10 W",10.0),("50 W",50.0),("100 W",100.0),("Benutzerdefiniert",None)):
            self.power_preset.addItem(label,value)
        self.power_preset.setCurrentIndex(1)
        self.power_preset.currentIndexChanged.connect(lambda: self.input_power.setValue(self.power_preset.currentData()) if self.power_preset.currentData() is not None else None)
        self.alignment_button = QPushButton("Drei Abstimmungen vergleichen")
        self.alignment_button.clicked.connect(self._suggest_alignments)

        self.port_type = QComboBox()
        self.port_type.addItem("Rundport", "round")
        self.port_type.addItem("Slot-Port", "slot")
        self.port_type.currentIndexChanged.connect(self._refresh_mode_controls)
        self.port_diameter = self._spin(10.0, 500.0, 80.0, " mm")
        self.slot_width = self._spin(10.0, 1000.0, 200.0, " mm")
        self.slot_height = self._spin(5.0, 500.0, 30.0, " mm")

        self.cabinet_width = self._spin(100.0, 3000.0, 340.0, " mm")
        self.cabinet_height = self._spin(100.0, 3000.0, 560.0, " mm")
        self.panel_thickness = self._spin(3.0, 100.0, 18.0, " mm")
        self.front_thickness = self._spin(0.0,100.0,0.0," mm")
        self.back_thickness = self._spin(0.0,100.0,0.0," mm")
        self.top_thickness = self._spin(0.0,100.0,0.0," mm")
        self.bottom_thickness = self._spin(0.0,100.0,0.0," mm")
        self.front_layers=QSpinBox();self.front_layers.setRange(1,3);self.front_layers.setValue(1)
        self.additional_displacement = self._spin(0.0, 500.0, 0.0, " l")
        self.joint_style = QComboBox()
        self.joint_style.addItem("Stumpf verleimt", "butt")
        self.joint_style.addItem("Gehrung 45° (Seiten, Deckel, Boden)", "mitre")
        self.brace_count = QSpinBox()
        self.brace_count.setRange(0, 20)
        self.brace_count.setValue(1)
        self.brace_border = self._spin(5.0, 300.0, 35.0, " mm")
        self.material = QLineEdit("Birke Multiplex")

        for label, control in [
            ("Gehäusetyp", self.enclosure_type),
            ("Ziel-Qtc", self.target_qtc),
            ("Netto-Volumen / Frontkammer", self.target_volume),
            ("Bandpass Rückkammer netto", self.rear_volume),
            ("Rückkammer Abstimmung Fb2", self.rear_tuning),
            ("Rückkammer Port BR2 Ø", self.rear_port_diameter),
            ("Aperiodischer Widerstand (0 = Auto)", self.aperiodic_resistance),
            ("Dipol-Seitenflügel Tiefe", self.baffle_wing_depth),
            ("Kardioid-Ventverzug (Modell)", self.cardioid_delay),
            ("Isobarik Verschaltung", self.isobaric_wiring),
            ("Isobarik Freiraum", self.isobaric_gap),
            ("Abstimmziel Fb / Viertelwelle", self.tuning),
            ("PM wirksame Fläche Sd", self.radiator_sd),
            ("PM Grundmasse Mms", self.radiator_mms),
            ("PM Freiluft-Fs", self.radiator_fs),
            ("PM Qms", self.radiator_qms),
            ("PM Xmax", self.radiator_xmax),
            ("PM Ausschnitt", self.radiator_cutout),
            ("PM Einbautiefe", self.radiator_depth),
            ("Simulationsleistung", self.input_power),
            ("Leistungsvorgabe", self.power_preset),
            ("Automatische Vorschläge", self.alignment_button),
            ("Port-Typ", self.port_type),
            ("Port-Durchmesser", self.port_diameter),
            ("Slot-Breite", self.slot_width),
            ("Slot-Höhe", self.slot_height),
            ("Außenbreite", self.cabinet_width),
            ("Außenhöhe", self.cabinet_height),
            ("Materialstärke", self.panel_thickness),
            ("Front-Stärke (0 = Basis)",self.front_thickness),
            ("Front-Lagen",self.front_layers),
            ("Rückwand-Stärke (0 = Basis)",self.back_thickness),
            ("Deckel-Stärke (0 = Basis)",self.top_thickness),
            ("Boden-Stärke (0 = Basis)",self.bottom_thickness),
            ("Weitere Verdrängung", self.additional_displacement),
            ("Anzahl Fensterstreben", self.brace_count),
            ("Streben-Randbreite", self.brace_border),
            ("Verbindung", self.joint_style),
            ("Material", self.material),
        ]:
            form.addRow(label, control)
        guidance=QLabel("Passivmembran: die angezeigten Startwerte sind Platzhalter. Für reale Entwürfe gemessene Fs, Mms, Sd, Qms und Xmax der konkreten Membran verwenden. Bandpass: Frontkammer und Rückkammer getrennt prüfen.")
        guidance.setWordWrap(True)
        form.addRow(guidance)
        return widget

    def _build_crossover_tab(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)

        self.crossover_enabled = QCheckBox("Passive Frequenzweiche auslegen")
        self.crossover_enabled.setChecked(True)
        self.crossover_topology = QComboBox()
        self.crossover_topology.addItem("1. Ordnung / 6 dB", "first_order")
        self.crossover_topology.addItem("Butterworth 2. Ordnung / 12 dB", "butterworth_2")
        self.crossover_topology.addItem("Linkwitz-Riley 2. Ordnung / 12 dB", "linkwitz_riley_2")
        self.crossover_ways = QComboBox()
        self.crossover_ways.addItem("2-Wege", 2)
        self.crossover_ways.addItem("3-Wege", 3)
        self.upper_frequency = self._spin(40.0, 30000.0, 3500.0, " Hz")
        self.mid_impedance = self._spin(1.0, 32.0, 8.0, " Ohm")
        self.mid_attenuation = self._spin(0.0, 30.0, 0.0, " dB")
        self.crossover_frequency = self._spin(20.0, 30000.0, 2500.0, " Hz")
        self.woofer_impedance = self._spin(1.0, 32.0, 8.0, " Ohm")
        self.tweeter_impedance = self._spin(1.0, 32.0, 8.0, " Ohm")
        self.tweeter_name = QLineEdit("Tweeter")
        self.tweeter_attenuation = self._spin(0.0, 30.0, 0.0, " dB")
        self.woofer_zobel = QCheckBox("Zobel aus Re/Le ergänzen")
        self.baffle_step = self._spin(0.0, 6.0, 0.0, " dB", 1)
        self.baffle_step.setToolTip("0 = aus. Ergänzt eine Spule mit Parallelwiderstand im Tieftonzweig; "
                                    "Übergang bei ca. 115 Hz·m / Schallwandbreite (Näherung).")

        note = QLabel(
            "Die passive Weiche ist ein elektrischer Startentwurf auf Basis der Nennimpedanz. "
            "Für die Endabstimmung werden reale Impedanz- und Frequenzgangmessungen benötigt."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #a66; padding: 6px;")

        form.addRow(self.crossover_enabled)
        form.addRow("Wege", self.crossover_ways)
        form.addRow("Topologie", self.crossover_topology)
        form.addRow("Trennfrequenz (unten)", self.crossover_frequency)
        form.addRow("Obere Trennfrequenz (3-Wege)", self.upper_frequency)
        form.addRow("Mitteltöner-Impedanz (3-Wege)", self.mid_impedance)
        form.addRow("Mitteltöner-Absenkung (3-Wege)", self.mid_attenuation)
        form.addRow("Woofer-Impedanz", self.woofer_impedance)
        form.addRow("Tweeter", self.tweeter_name)
        form.addRow("Tweeter-Impedanz", self.tweeter_impedance)
        form.addRow("Tweeter-Absenkung", self.tweeter_attenuation)
        form.addRow(self.woofer_zobel)
        form.addRow("Schallwandkorrektur", self.baffle_step)
        for title, key in (("Woofer FRD laden", "woofer_frd"),
                           ("Mitteltöner FRD laden (3-Wege)", "mid_frd"),
                           ("Tweeter FRD laden", "tweeter_frd"),
                           ("Woofer ZMA laden", "woofer_zma"),
                           ("Mitteltöner ZMA laden (3-Wege)", "mid_zma"),
                           ("Tweeter ZMA laden", "tweeter_zma")):
            button = QPushButton(title)
            button.clicked.connect(lambda _=False, item=key: self._load_measurement(item))
            form.addRow(button)
        self.measurement_status = QLabel("Keine Messdaten geladen")
        self.measurement_status.setWordWrap(True)
        form.addRow(self.measurement_status)
        form.addRow(note)
        return widget

    def _build_layout_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        toolbar = QHBoxLayout()
        self.canvas_surface = QComboBox()
        for key, label in FrontLayoutCanvas.SURFACES:
            self.canvas_surface.addItem(label, key)
        self.canvas_surface.currentIndexChanged.connect(self._canvas_surface_changed)
        self.undo_button = QPushButton("↶ Rückgängig")
        self.redo_button = QPushButton("↷ Wiederholen")
        self.undo_button.clicked.connect(self._undo)
        self.redo_button.clicked.connect(self._redo)
        self.snap_check = QCheckBox("Einrasten (5 mm, Mitte)")
        self.snap_check.setChecked(True)
        for widget_ in (QLabel("Ansicht:"), self.canvas_surface, self.undo_button, self.redo_button, self.snap_check):
            toolbar.addWidget(widget_)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        self.layout_canvas = FrontLayoutCanvas()
        self.layout_canvas.elementSelected.connect(self._canvas_selected)
        self.layout_canvas.elementMoved.connect(self._canvas_moved)
        self.snap_check.toggled.connect(lambda on: setattr(self.layout_canvas, "snap_enabled", on))
        layout.addWidget(self.layout_canvas, 2)
        self.element_list = QListWidget()
        self.element_list.setMaximumHeight(110)
        self.element_list.currentRowChanged.connect(self._select_element)
        layout.addWidget(self.element_list)
        row = QHBoxLayout()
        for label, kind in (("Woofer +", "woofer"), ("Tweeter +", "tweeter"),
                            ("Port +", "port"), ("PM +", "passive_radiator")):
            button = QPushButton(label)
            button.clicked.connect(lambda _=False, element_type=kind: self._add_element(element_type))
            row.addWidget(button)
        remove = QPushButton("Auswahl löschen")
        remove.clicked.connect(self._remove_element)
        row.addWidget(remove)
        layout.addLayout(row)
        form = QFormLayout()
        self.layout_surface = QComboBox()
        self.layout_surface.addItem("Front", "front")
        self.layout_surface.addItem("Rückwand", "back")
        self.layout_surface.addItem("Trennwand", "partition")
        self.layout_surface.currentIndexChanged.connect(self._edit_selected_element)
        form.addRow("Montagefläche", self.layout_surface)
        self.layout_x = self._spin(0, 3000, 170, " mm")
        self.layout_y = self._spin(0, 3000, 340, " mm")
        self.layout_outer = self._spin(0, 1000, 260, " mm")
        self.layout_cutout = self._spin(0, 1000, 230, " mm")
        self.layout_width = self._spin(0, 1000, 0, " mm")
        self.layout_height = self._spin(0, 1000, 0, " mm")
        self.layout_depth = self._spin(0, 1000, 115, " mm")
        self.layout_bolt_circle = self._spin(0, 1000, 0, " mm")
        self.layout_bolt_count = QSpinBox(); self.layout_bolt_count.setRange(0, 32)
        self.layout_hole = self._spin(0, 50, 0, " mm")
        self.layout_clearance = self._spin(0, 100, 5, " mm")
        for label, control in (("X von links",self.layout_x),("Y von unten",self.layout_y),
            ("Außendurchmesser",self.layout_outer),("Ausschnitt",self.layout_cutout),
            ("Breite Rechteck",self.layout_width),("Höhe Rechteck",self.layout_height),
            ("Einbautiefe",self.layout_depth),("Lochkreis",self.layout_bolt_circle),
            ("Schrauben",self.layout_bolt_count),("Bohrung",self.layout_hole),
            ("Randabstand",self.layout_clearance)):
            form.addRow(label,control)
            control.valueChanged.connect(self._edit_selected_element)
        layout.addLayout(form)
        hint=QLabel("Elemente mit der Maus ziehen oder mit den Pfeiltasten verschieben (Umschalt = 10 mm); Strg+Z macht rückgängig, Strg+Y wiederholt. X/Y gelten auf der gewählten Platte von links/unten. Bei Bandpass sitzt der Tieftöner auf der Trennwand; die Passivmembran kann auf der Rückwand sitzen.")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        return widget

    def _refresh_element_list(self, selected: int | None = None) -> None:
        if selected is None and self._front_elements:
            selected=0
        self.element_list.blockSignals(True)
        self.element_list.clear()
        for e in self._front_elements:
            self.element_list.addItem(f"{e.id} · {e.type} · {e.surface} · {e.x_m*1000:.1f}/{e.y_m*1000:.1f} mm")
        self.element_list.blockSignals(False)
        if selected is not None and 0 <= selected < len(self._front_elements):
            self.element_list.setCurrentRow(selected)
        self._refresh_canvas()

    # --- interactive layout, undo/redo ------------------------------------------

    def _plate_size_mm(self, surface: str) -> tuple[float, float]:
        if self._bundle is not None:
            cabinet = self._bundle.cabinet
            if surface == "partition":
                return cabinet.internal_width_m * 1000, cabinet.internal_height_m * 1000
            return cabinet.width_m * 1000, cabinet.height_m * 1000
        return self.cabinet_width.value(), self.cabinet_height.value()

    def _refresh_canvas(self) -> None:
        if not hasattr(self, "layout_canvas"):
            return
        surface = self.canvas_surface.currentData()
        self.layout_canvas.set_surface(surface)
        self.layout_canvas.set_plate(*self._plate_size_mm(surface))
        self.layout_canvas.set_layout(tuple(self._front_elements), self.element_list.currentRow())
        self.undo_button.setEnabled(self._history.can_undo)
        self.redo_button.setEnabled(self._history.can_redo)

    def _canvas_surface_changed(self, _index: int = 0) -> None:
        self._refresh_canvas()

    def _canvas_selected(self, index: int) -> None:
        if index != self.element_list.currentRow():
            self.element_list.setCurrentRow(index)

    def _canvas_moved(self, index: int, x_m: float, y_m: float, from_keyboard: bool) -> None:
        if not 0 <= index < len(self._front_elements):
            return
        data = self._front_elements[index].model_dump()
        data.update(x_m=x_m, y_m=y_m)
        try:
            self._front_elements[index] = FrontElement.model_validate(data)
        except ValidationError as exc:
            self.statusBar().showMessage(str(exc))
            return
        self._record_history(("move", index) if from_keyboard else None)
        self._refresh_element_list(index)
        self._select_element(index)
        self.calculate()

    def _record_history(self, merge_key: object | None = None) -> None:
        self._history.push(tuple(self._front_elements), merge_key)
        if hasattr(self, "undo_button"):
            self.undo_button.setEnabled(self._history.can_undo)
            self.redo_button.setEnabled(self._history.can_redo)

    def _restore_history(self, state: tuple[FrontElement, ...] | None) -> None:
        if state is None:
            return
        selected = self.element_list.currentRow()
        self._front_elements = list(state)
        self._refresh_element_list(min(max(selected, 0), len(state) - 1) if state else None)
        self._select_element(self.element_list.currentRow())
        self.calculate()

    def _undo(self) -> None:
        self._restore_history(self._history.undo())

    def _redo(self) -> None:
        self._restore_history(self._history.redo())

    def _select_element(self, index: int) -> None:
        if not 0 <= index < len(self._front_elements):
            return
        e=self._front_elements[index]
        self.layout_surface.blockSignals(True)
        self.layout_surface.setCurrentIndex(max(0,self.layout_surface.findData(e.surface)))
        self.layout_surface.blockSignals(False)
        pairs=((self.layout_x,e.x_m*1000),(self.layout_y,e.y_m*1000),
            (self.layout_outer,(e.outer_diameter_m or 0)*1000),
            (self.layout_cutout,(e.cutout_diameter_m or 0)*1000),
            (self.layout_width,(e.width_m or 0)*1000),(self.layout_height,(e.height_m or 0)*1000),
            (self.layout_depth,e.mounting_depth_m*1000),
            (self.layout_bolt_circle,(e.bolt_circle_diameter_m or 0)*1000),
            (self.layout_bolt_count,e.bolt_count),(self.layout_hole,(e.hole_diameter_m or 0)*1000),
            (self.layout_clearance,e.clearance_m*1000))
        for control,value in pairs:
            control.blockSignals(True);control.setValue(value);control.blockSignals(False)

    def _edit_selected_element(self, _value: float = 0) -> None:
        index=self.element_list.currentRow()
        if not 0 <= index < len(self._front_elements):
            return
        old=self._front_elements[index]
        data=old.model_dump()
        data.update(surface=self.layout_surface.currentData(),
            x_m=self.layout_x.value()/1000,y_m=self.layout_y.value()/1000,
            outer_diameter_m=self.layout_outer.value()/1000 or None,
            cutout_diameter_m=self.layout_cutout.value()/1000 or None,
            width_m=self.layout_width.value()/1000 or None,
            height_m=self.layout_height.value()/1000 or None,
            mounting_depth_m=self.layout_depth.value()/1000,
            bolt_circle_diameter_m=self.layout_bolt_circle.value()/1000 or None,
            bolt_count=self.layout_bolt_count.value(),
            hole_diameter_m=self.layout_hole.value()/1000 or None,
            clearance_m=self.layout_clearance.value()/1000)
        try:
            self._front_elements[index]=FrontElement.model_validate(data)
        except ValidationError as exc:
            self.statusBar().showMessage(str(exc))
            return
        self._record_history(("edit", index))
        self._refresh_element_list(index)
        self.calculate()

    def _add_element(self, kind: str) -> None:
        number=1+sum(e.type==kind for e in self._front_elements)
        prefix={"woofer":"W","tweeter":"T","port":"BR","passive_radiator":"PM"}[kind]
        diameter={"woofer":0.26,"tweeter":0.105,"port":0.08,"passive_radiator":0.25}[kind]
        element=FrontElement(id=f"{prefix}{number}",type=kind,
            surface="back" if kind=="passive_radiator" else
                    "partition" if kind=="woofer" and str(self.enclosure_type.currentData()).startswith("bandpass_") else "front",
            x_m=self.cabinet_width.value()/2000,
            y_m=self.cabinet_height.value()/1000*(0.7 if kind=="tweeter" else 0.32 if kind=="woofer" else 0.12),
            outer_diameter_m=diameter,cutout_diameter_m=diameter*0.88,
            mounting_depth_m=0.1 if kind=="woofer" else 0.05)
        self._front_elements.append(element)
        self._record_history()
        self._refresh_element_list(len(self._front_elements)-1)
        self.calculate()

    def _remove_element(self) -> None:
        index=self.element_list.currentRow()
        if 0 <= index < len(self._front_elements):
            del self._front_elements[index]
            self._record_history()
            self._refresh_element_list(min(index,len(self._front_elements)-1))
            self.calculate()

    def _load_measurement(self, key: str) -> None:
        filename,_=QFileDialog.getOpenFileName(self,"Messdatei laden","",
            "Messdaten (*.frd *.zma *.txt);;Alle Dateien (*)")
        if not filename:
            return
        try:
            self._measurements[key]=(load_frd(filename) if key.endswith("frd") else load_zma(filename))
        except (OSError,ValueError,ValidationError) as exc:
            QMessageBox.critical(self,"Messdatenfehler",str(exc));return
        self.measurement_status.setText("Geladen: "+", ".join(sorted(self._measurements)))
        self.calculate()

    def _suggest_alignments(self) -> None:
        try:
            options=suggest_alignments(self._driver_from_form(),input_power_w=self.input_power.value(),
                external_width_m=self.cabinet_width.value()/1000,
                external_height_m=self.cabinet_height.value()/1000,
                panel_thickness_m=self.panel_thickness.value()/1000)
        except (ValueError,ValidationError) as exc:
            QMessageBox.warning(self,"Abstimmung",str(exc));return
        labels=[f"{o.name}: {o.volume_l:.1f} l / {o.tuning_hz:.1f} Hz · F3 {o.f3_hz:.1f} Hz · {o.port.diameter_m*1000:.0f} mm Port · {o.port.physical_length_m*1000:.0f} mm Länge" if o.f3_hz is not None else f"{o.name}: {o.volume_l:.1f} l / {o.tuning_hz:.1f} Hz · F3 –" for o in options]
        choice,ok=QInputDialog.getItem(self,"Abstimmung vergleichen",
            "Vorschlag wählen (Warnungen und Portlänge im Ergebnis prüfen):",labels,0,False)
        if ok:
            option=options[labels.index(choice)]
            self.enclosure_type.setCurrentIndex(self.enclosure_type.findData("bass_reflex"))
            self.target_volume.setValue(option.volume_l)
            self.tuning.setValue(option.tuning_hz)
            self.port_type.setCurrentIndex(self.port_type.findData("round"))
            self.port_diameter.setValue(option.port.diameter_m*1000)
            self.calculate()
            details=[option.name,f"Außenvolumen ca. {option.outer_volume_l:.1f} l",
                f"Max. Portgeschwindigkeit: {option.max_port_velocity_m_s:.1f} m/s" if option.max_port_velocity_m_s is not None else "Portgeschwindigkeit: Daten fehlen",
                f"Max. Auslenkung: {option.max_excursion_mm:.1f} mm" if option.max_excursion_mm is not None else "Auslenkung: Daten fehlen",
                f"Max. Gruppenlaufzeit: {option.max_group_delay_ms:.1f} ms",
                "Warnungen: "+"; ".join(option.warnings) if option.warnings else "Keine Vorschlagswarnung"]
            QMessageBox.information(self,"Abstimmung","\n".join(details))

    def _build_output(self) -> QWidget:
        container=QWidget()
        outer=QVBoxLayout(container)
        self.kpis=QLabel("Vb · Fb/Qtc · F3 · Außenmaße · Auslenkung · Port · Warnungen")
        self.kpis.setWordWrap(True)
        self.kpis.setStyleSheet("font-weight: 600; padding: 10px; background: #17394d; color: #ffffff;")
        outer.addWidget(self.kpis)
        self.revision_state=QLabel("Bereit")
        self.revision_state.setStyleSheet("padding: 7px; background: #e5f1e9; color: #173d2a; font-weight: 600;")
        outer.addWidget(self.revision_state)
        tabs = QTabWidget()
        self.output_tabs=tabs

        self.summary = QTextEdit()
        self.summary.setReadOnly(True)
        tabs.addTab(self.summary, "Ergebnis")

        drawing_page=QWidget()
        drawing_layout=QVBoxLayout(drawing_page)
        zoom_row=QHBoxLayout()
        zoom_row.addWidget(QLabel("Innenaufbau, Front und Rückwand · Zoom:"))
        self.drawing_zoom=QComboBox()
        for percent in (60,75,100,125):
            self.drawing_zoom.addItem(f"{percent} %",percent)
        self.drawing_zoom.setCurrentIndex(2)
        self.drawing_zoom.currentIndexChanged.connect(self._set_drawing_zoom)
        zoom_row.addWidget(self.drawing_zoom)
        zoom_row.addStretch()
        drawing_layout.addLayout(zoom_row)
        self.svg_preview = QSvgWidget()
        self._set_drawing_zoom()
        drawing_scroll=QScrollArea()
        drawing_scroll.setWidget(self.svg_preview)
        drawing_layout.addWidget(drawing_scroll,1)
        tabs.addTab(drawing_page, "Innenaufbau / Zeichnung")

        self.figure = Figure(figsize=(7, 5), tight_layout=True)
        self.canvas = FigureCanvasQTAgg(self.figure)
        tabs.addTab(self.canvas, "Frequenzgang")

        self.crossover_figure=Figure(figsize=(7,5),tight_layout=True)
        self.crossover_canvas=FigureCanvasQTAgg(self.crossover_figure)
        tabs.addTab(self.crossover_canvas,"Weichen-Simulation")

        outer.addWidget(tabs,1)
        return container

    def _set_drawing_zoom(self, _index: int = 0) -> None:
        factor=(self.drawing_zoom.currentData() or 100)/100
        self.svg_preview.setFixedSize(int(1200*factor),int(1020*factor))

    def _connect_dirty_signals(self) -> None:
        layout_controls={self.layout_surface,self.layout_x,self.layout_y,self.layout_outer,
            self.layout_cutout,self.layout_width,self.layout_height,self.layout_depth,
            self.layout_bolt_circle,self.layout_bolt_count,self.layout_hole,self.layout_clearance}
        for control in self._editor_widget.findChildren(QLineEdit):
            if isinstance(control.parent(), (QDoubleSpinBox,QSpinBox)):
                continue
            control.textChanged.connect(self._mark_dirty)
        for kind,signal in ((QDoubleSpinBox,"valueChanged"),(QSpinBox,"valueChanged"),
                            (QComboBox,"currentIndexChanged"),(QCheckBox,"toggled")):
            for control in self._editor_widget.findChildren(kind):
                if control in layout_controls:
                    continue
                getattr(control,signal).connect(self._mark_dirty)

    def _mark_dirty(self, *_: object) -> None:
        if self._loading:
            return
        self._dirty=True
        self.revision_state.setText("● Eingaben geändert – Projekt berechnen, um neue Ergebnisse zu sehen")
        self.revision_state.setStyleSheet("padding: 7px; background: #fff0d6; color: #603700; font-weight: 600;")
        self.calculate_button.setText("Änderungen berechnen ●")
        self.export_button.setEnabled(False)
        self.statusBar().showMessage("Eingaben geändert – Ergebnisse sind noch vom letzten Rechenlauf")

    @staticmethod
    def _spin(
        minimum: float,
        maximum: float,
        value: float,
        suffix: str,
        decimals: int = 2,
    ) -> QDoubleSpinBox:
        control = QDoubleSpinBox()
        control.setRange(minimum, maximum)
        control.setDecimals(decimals)
        control.setValue(value)
        control.setSuffix(suffix)
        control.setSingleStep(max((maximum - minimum) / 1000.0, 0.001))
        return control

    def _refresh_mode_controls(self) -> None:
        if not hasattr(self, "enclosure_type"):
            return
        enclosure = self.enclosure_type.currentData()
        single_horn=enclosure in {'horn_front','horn_tapped'}
        if single_horn and not self._loading:
            self._front_elements=[]
            self._refresh_element_list()
        self.tweeter_name.setEnabled(not single_horn)
        self.crossover_enabled.setEnabled(not single_horn)
        line = enclosure in {"transmission_line_closed","transmission_line_open",
                             "transmission_line_tapered","mltl","tqwt","labyrinth",
                             "horn_rear","horn_folded","horn_scoop","horn_exponential",
                             "horn_tractrix","horn_conical","horn_hyperbolic"}
        baffle = enclosure in {"infinite_baffle","open_baffle","dipole"}
        if enclosure == "infinite_baffle" and not self._loading and self.target_volume.value()<600:
            self.target_volume.setValue(1000.0)
        if enclosure == "horn_front" and not self._loading and self.tuning.value()<100:
            self.tuning.setValue(150.0)
        if enclosure == 'horn_front' and not self._loading and self.target_qtc.value()>0.55:
            self.target_qtc.setValue(0.5)
        if enclosure == 'horn_tapped' and not self._loading:
            if self.cabinet_height.value()<1000:
                self.cabinet_height.setValue(1200.0)
            if self.cabinet_width.value()<450:
                self.cabinet_width.setValue(450.0)
            if self.target_volume.value()<200:
                self.target_volume.setValue(200.0)
            self.brace_count.setValue(0)
            if self.tuning.value()<45 or self.tuning.value()>100:
                self.tuning.setValue(60.0)
        if (line and not self._loading and hasattr(self,"cabinet_height")
                and self.cabinet_height.value()<900):
            self.cabinet_height.setValue(1200.0)
            if self.cabinet_width.value()<400:
                self.cabinet_width.setValue(400.0)
            if self.target_volume.value()<100:
                self.target_volume.setValue(120.0)
            self.tuning.setValue(60.0)
            self.brace_count.setValue(0)
        tuned = enclosure not in {"sealed", "isobaric_sealed", "compound_push_pull", "horn_front"} and not baffle
        duct = enclosure in {"bass_reflex","bandpass_4","bandpass_6_parallel","bandpass_6_series","isobaric_vented"}
        radiator = enclosure == "passive_radiator"
        self.target_qtc.setEnabled(enclosure in {"sealed", "isobaric_sealed", "compound_push_pull", "horn_front"})
        self.isobaric_wiring.setEnabled(enclosure.startswith("isobaric_") or enclosure == "compound_push_pull")
        self.isobaric_gap.setEnabled(enclosure.startswith("isobaric_") or enclosure == "compound_push_pull")
        self.target_volume.setEnabled(tuned or enclosure == "infinite_baffle")
        self.rear_volume.setEnabled(enclosure.startswith("bandpass_"))
        self.rear_tuning.setEnabled(enclosure in {"bandpass_6_parallel", "bandpass_6_series"})
        self.rear_port_diameter.setEnabled(enclosure in {"bandpass_6_parallel", "bandpass_6_series"})
        self.aperiodic_resistance.setEnabled(enclosure in {"aperiodic","cardioid"})
        self.baffle_wing_depth.setEnabled(enclosure == "dipole")
        self.cardioid_delay.setEnabled(enclosure == "cardioid")
        self.tuning.setEnabled((tuned or enclosure == "horn_front") and enclosure not in {"aperiodic","cardioid"})
        self.alignment_button.setEnabled(enclosure == "bass_reflex")
        self.port_type.setEnabled(duct and enclosure != "aperiodic")
        for control in (self.radiator_sd,self.radiator_mms,self.radiator_fs,
                        self.radiator_qms,self.radiator_xmax,self.radiator_cutout,
                        self.radiator_depth):
            control.setEnabled(radiator)
        for control in (self.port_diameter,self.slot_width,self.slot_height):
            control.setEnabled(False)
        if duct or enclosure in {"aperiodic","mltl","cardioid"}:
            round_selected = self.port_type.currentData() == "round"
            self.port_diameter.setEnabled(round_selected or enclosure in {"aperiodic","mltl","cardioid"})
            self.slot_width.setEnabled(not round_selected and duct)
            self.slot_height.setEnabled(not round_selected and duct)

    def _driver_from_form(self) -> Driver:
        data = self._base_driver.model_dump(mode="python") if self._base_driver else {}
        data.update({
            "manufacturer": self.manufacturer.text().strip() or "Unknown",
            "model": self.driver_model.text().strip() or "Unnamed",
            "fs_hz": self.fs.value(),
            "qts": self.qts.value(),
            "qes": self.qes.value() or None,
            "qms": self.qms.value() or None,
            "vas_m3": self.vas.value() / 1000.0,
            "re_ohm": self.re.value() or None,
            "le_h": (self.le.value() / 1000.0) if self.le.value() else None,
            "sd_m2": (self.sd.value() / 10_000.0) if self.sd.value() else None,
            "xmax_m": (self.xmax.value() / 1000.0) if self.xmax.value() else None,
            "power_rms_w": self.power_rating.value() or None,
            "displacement_m3": self.driver_displacement.value() / 1000.0,
            "nominal_impedance_ohm": self.impedance.value(),
            "cutout_diameter_m": (self.cutout.value() / 1000.0) if self.cutout.value() else None,
            "outer_diameter_m": (self.outer_diameter.value() / 1000.0) if self.outer_diameter.value() else None,
            "mounting_depth_m": (
                self.mounting_depth.value() / 1000.0 if self.mounting_depth.value() else None
            ),
            "source_name": self.source_name.text().strip() or None,
        })
        return Driver.model_validate(data)

    def _project_from_form(self) -> SpeakerProject:
        return SpeakerProject(
            name=self.project_name.text().strip() or "Lautsprecherprojekt",
            revision=REVISION,
            material=self.material.text().strip() or "Plattenmaterial",
            driver=self._driver_from_form(),
            additional_drivers=() if self.enclosure_type.currentData() in {'horn_front','horn_tapped'} else self._additional_drivers,
            tweeter_name='' if self.enclosure_type.currentData() in {'horn_front','horn_tapped'} else self.tweeter_name.text().strip(),
            enclosure=EnclosureConfig(
                enclosure_type=self.enclosure_type.currentData(),
                target_qtc=self.target_qtc.value(),
                target_volume_l=self.target_volume.value(),
                rear_volume_l=self.rear_volume.value(),
                rear_tuning_hz=self.rear_tuning.value(),
                rear_port_diameter_mm=self.rear_port_diameter.value(),
                aperiodic_resistance_pa_s_m3=(self.aperiodic_resistance.value() or None),
                baffle_wing_depth_mm=self.baffle_wing_depth.value(),
                cardioid_delay_ms=self.cardioid_delay.value(),
                isobaric_wiring=self.isobaric_wiring.currentData(),
                isobaric_gap_mm=self.isobaric_gap.value(),
                tuning_hz=self.tuning.value(),
                radiator_sd_cm2=self.radiator_sd.value(),
                radiator_mms_g=self.radiator_mms.value(),
                radiator_fs_hz=self.radiator_fs.value(),
                radiator_qms=self.radiator_qms.value(),
                radiator_xmax_mm=self.radiator_xmax.value(),
                radiator_cutout_mm=self.radiator_cutout.value(),
                radiator_depth_mm=self.radiator_depth.value(),
                input_power_w=self.input_power.value(),
                port_type=self.port_type.currentData(),
                port_diameter_mm=self.port_diameter.value(),
                slot_width_mm=self.slot_width.value(),
                slot_height_mm=self.slot_height.value(),
                external_width_mm=self.cabinet_width.value(),
                external_height_mm=self.cabinet_height.value(),
                panel_thickness_mm=self.panel_thickness.value(),
                front_thickness_mm=self.front_thickness.value() or None,
                back_thickness_mm=self.back_thickness.value() or None,
                top_thickness_mm=self.top_thickness.value() or None,
                bottom_thickness_mm=self.bottom_thickness.value() or None,
                front_layers=self.front_layers.value(),
                additional_displacement_l=self.additional_displacement.value(),
                brace_quantity=self.brace_count.value(),
                brace_border_mm=self.brace_border.value(),
                joint_style=self.joint_style.currentData(),
            ),
            crossover=CrossoverConfig(
                enabled=self.crossover_enabled.isChecked() and self.enclosure_type.currentData() not in {'horn_front','horn_tapped'},
                ways=self.crossover_ways.currentData(),
                topology=self.crossover_topology.currentData(),
                crossover_hz=self.crossover_frequency.value(),
                upper_crossover_hz=(self.upper_frequency.value()
                                    if self.crossover_ways.currentData() == 3 else None),
                mid_impedance_ohm=self.mid_impedance.value(),
                mid_attenuation_db=self.mid_attenuation.value(),
                woofer_impedance_ohm=self.woofer_impedance.value(),
                tweeter_impedance_ohm=self.tweeter_impedance.value(),
                tweeter_attenuation_db=self.tweeter_attenuation.value(),
                add_woofer_zobel=self.woofer_zobel.isChecked(),
                baffle_step_compensation_db=self.baffle_step.value(),
                round_to_standard_values=self._round_to_standard,
                **self._measurements,
            ),
            front_elements=tuple(self._front_elements),
            accessories=self._accessories,
            notes=self._notes,
        )

    def calculate(self, show_results: bool = False) -> None:
        try:
            project = self._project_from_form()
            bundle = calculate_project(project)
        except (ValueError, ValidationError) as exc:
            QMessageBox.critical(self, "Berechnungsfehler", str(exc))
            self.statusBar().showMessage("Berechnung fehlgeschlagen")
            return

        previous=self._bundle
        self._bundle = bundle
        self._run_count += 1
        differences=[]
        if previous:
            old_driver,new_driver=previous.project.driver,bundle.project.driver
            if old_driver.fs_hz != new_driver.fs_hz:
                differences.append(f"Fs {old_driver.fs_hz:.1f} → {new_driver.fs_hz:.1f} Hz")
            old_f3=(previous.sealed.f3_hz if previous.sealed else
                    previous.vented_response.f3_hz if previous.vented_response else None)
            new_f3=(bundle.sealed.f3_hz if bundle.sealed else
                    bundle.vented_response.f3_hz if bundle.vented_response else None)
            if old_f3 is not None and new_f3 is not None and abs(new_f3-old_f3)>0.05:
                differences.append(f"F3 {old_f3:.1f} → {new_f3:.1f} Hz")
            old_depth,new_depth=previous.cabinet.depth_m*1000,bundle.cabinet.depth_m*1000
            if abs(new_depth-old_depth)>0.05:
                differences.append(f"Tiefe {old_depth:.1f} → {new_depth:.1f} mm")
            if previous.project.enclosure.enclosure_type != bundle.project.enclosure.enclosure_type:
                differences.insert(0,f"Gehäusetyp: {bundle.project.enclosure.enclosure_type}")
        self._change_note=" · ".join(differences) if differences else (
            "Erste Berechnung" if previous is None else "Eingaben unverändert oder Änderung in Detailwerten")
        if tuple(self._front_elements) != bundle.front_elements:
            self._front_elements=list(bundle.front_elements)
            self._refresh_element_list()
        self._render_summary(bundle)
        self._render_drawing(bundle)
        self._render_response(bundle)
        self._render_crossover(bundle)
        f3=(bundle.vented_response.f3_hz if bundle.front_horn and bundle.vented_response else
            bundle.sealed.f3_hz if bundle.sealed else
            bundle.vented_response.f3_hz if bundle.vented_response else None)
        x=(float(np.max(bundle.vented_response.excursion_mm)) if bundle.vented_response and bundle.vented_response.excursion_mm is not None else None)
        v=(float(np.max(bundle.vented_response.port_velocity_m_s)) if bundle.vented_response and bundle.vented_response.port_velocity_m_s is not None else None)
        tuning=(f"Horn fc {bundle.front_horn.target_cutoff_hz:.0f} Hz" if bundle.front_horn else
                f"Tapped ¼λ {bundle.tapped_horn.quarter_wave_hz:.1f} Hz" if bundle.tapped_horn else
                f"Schallweg {(bundle.baffle_path_m or 0)*1000:.0f} mm" if bundle.baffle_mode else
                f"¼λ {bundle.folded_line.estimated_quarter_wave_hz:.1f} Hz" if bundle.folded_line else
                f"Rv {bundle.port_resistance_pa_s_m3:.0f} Pa·s/m³" if bundle.port_resistance_pa_s_m3 else
                f"Fb {bundle.project.enclosure.tuning_hz:.1f} Hz" if bundle.port or bundle.radiator else
                f"Qtc {bundle.sealed.target_qtc:.3f}")
        self.kpis.setText("  |  ".join((
            (f"Rückraum ≥ {bundle.target_net_volume_m3*1000:.0f} l" if bundle.baffle_mode == "infinite_baffle" else
             "Offene Schallwand" if bundle.baffle_mode else
             f"Vb {bundle.target_net_volume_m3*1000:.1f} l"),tuning,
            f"F3 {f3:.1f} Hz" if f3 is not None else "F3 –",
            (f"Platte {bundle.cabinet.width_m*1000:.0f}×{bundle.cabinet.height_m*1000:.0f}×{bundle.cabinet.panel_thickness_m*1000:.0f} mm"
             if bundle.baffle_mode else
             f"Außen {bundle.cabinet.width_m*1000:.0f}×{bundle.cabinet.height_m*1000:.0f}×{bundle.cabinet.depth_m*1000:.0f} mm"),
            f"X {x:.1f} mm" if x is not None else "X –",
            (f"PM {v:.1f} m/s" if bundle.radiator else f"Port {v:.1f} m/s") if v is not None else "Resonator –",
            f"Warnungen {len(bundle.warnings)}")))
        self._dirty=False
        self.calculate_button.setText("Projekt berechnen")
        self.export_button.setEnabled(True)
        stamp=datetime.now(tz=UTC).astimezone().strftime("%H:%M:%S")
        self.revision_state.setText(f"✓ Berechnung #{self._run_count} um {stamp} · {self._change_note}")
        self.revision_state.setStyleSheet("padding: 7px; background: #e4f2e8; color: #17452a; font-weight: 600;")
        if show_results:
            self.output_tabs.setCurrentWidget(self.summary)
        self.statusBar().showMessage(f"Berechnung #{self._run_count} abgeschlossen: {self._change_note}")
        self.projectCalculated.emit(bundle)

    def _render_summary(self, bundle: DesignBundle) -> None:
        cabinet = bundle.cabinet
        lines = [
            f"BERECHNUNG #{self._run_count}: {self._change_note}",
            "",
            f"PROJEKT: {bundle.project.name}",
            "",
            "GEHÄUSE",
            f"Typ: {bundle.project.enclosure.enclosure_type}",
        ]
        if bundle.baffle_mode:
            lines.extend([
                f"Schallwand B × H × Stärke: {cabinet.width_m*1000:.1f} × {cabinet.height_m*1000:.1f} × {cabinet.panel_thickness_m*1000:.1f} mm",
                f"Wirksamer Schallweg: {(bundle.baffle_path_m or 0)*1000:.1f} mm",
                f"Seitenflügel: {bundle.baffle_wing_depth_m*1000:.1f} mm",
                (f"Rückraum mindestens: {bundle.target_net_volume_m3*1000:.1f} l"
                 if bundle.baffle_mode == "infinite_baffle" else "Vorder- und Rückseite offen"),
            ])
        else:
            lines.extend([f"Netto-Zielvolumen: {bundle.target_net_volume_m3 * 1000:.2f} l", (
                "Außenmaße B x H x T: "
                f"{cabinet.width_m*1000:.1f} x {cabinet.height_m*1000:.1f} x "
                f"{cabinet.depth_m*1000:.1f} mm"
            ),
            f"Gesamte Bauteilverdrängung: {bundle.total_displacement_m3*1000:.2f} l",
            ])

        if bundle.sealed:
            lines.extend(
                [
                    f"Fc: {bundle.sealed.resonance_hz:.2f} Hz",
                    f"F3: {bundle.sealed.f3_hz:.2f} Hz",
                    f"Qtc: {bundle.sealed.target_qtc:.3f}",
                ]
            )

        if bundle.port:
            lines.extend(
                [
                    "",
                    "LINIE / HORN-MÜNDUNG" if bundle.folded_line else
                    "KARDIOID / RÜCKVENT" if bundle.project.enclosure.enclosure_type == "cardioid" else
                    "APERIODISCH" if bundle.port_resistance_pa_s_m3 else
                    "BANDPASS / BASSREFLEX" if bundle.rear_chamber_volume_m3 else "BASSREFLEX",
                    f"BR1: {bundle.port.shape}",
                    (f"Viertelwelle: {bundle.folded_line.estimated_quarter_wave_hz:.2f} Hz"
                     if bundle.folded_line else
                     f"Tapped ¼λ: {bundle.tapped_horn.quarter_wave_hz:.2f} Hz"
                     if bundle.tapped_horn else f"Fb: {bundle.port.tuning_hz:.2f} Hz"),
                    f"Portfläche: {bundle.port.area_m2*1e4:.2f} cm²",
                    f"Portlänge: {bundle.port.physical_length_m*1000:.1f} mm",
                ]
            )
            if bundle.port_resistance_pa_s_m3:
                lines.append(f"Soll-Strömungswiderstand: {bundle.port_resistance_pa_s_m3:.0f} Pa·s/m³")
            if bundle.project.enclosure.enclosure_type == "cardioid" and bundle.vented_response:
                rejection=bundle.vented_response.front_to_back_db
                if rejection is not None:
                    index=int(np.argmin(abs(bundle.vented_response.frequencies_hz-80)))
                    lines.append(f"Front/Rück-Differenz bei 80 Hz: {rejection[index]:.1f} dB (Modell)")
        if bundle.folded_line:
            lines.extend(["", "INNERE KANALFALTUNG",
                          f"Linienweg: {bundle.folded_line.path_length_m*1000:.1f} mm",
                          f"Umlenkspalt: {bundle.folded_line.turn_gap_m*1000:.1f} mm",
                          *(f"Kanal {i+1}: {height*1000:.1f} mm hoch, {area*10000:.1f} cm²"
                            for i,(height,area) in enumerate(zip(bundle.folded_line.channel_heights_m,
                                                                     bundle.folded_line.channel_areas_m2,strict=True)))])
        if bundle.front_horn:
            horn=bundle.front_horn
            lines.extend(["", "FRONT-HORN",
                          f"Hals: {horn.throat_width_m*1000:.1f} × {horn.throat_height_m*1000:.1f} mm",
                          f"Mündung: {horn.mouth_width_m*1000:.1f} × {horn.mouth_height_m*1000:.1f} mm",
                          f"Axiale Länge: {horn.axial_length_m*1000:.1f} mm",
                          f"Ziel-Grenzfrequenz: {horn.target_cutoff_hz:.1f} Hz"])
        if bundle.tapped_horn:
            horn=bundle.tapped_horn
            lines.extend(["", "TAPPED-HORN / INNERER TREIBER",
                          f"F1: {horn.panel.width_m*1000:.1f} × {horn.baffle_length_m*1000:.1f} mm",
                          f"W1 ab F1-Vorderkante: {horn.driver_depth_from_front_m*1000:.1f} mm",
                          f"Oberer Kanal: {horn.upper_height_m*1000:.1f} mm",
                          f"Unterer Kanal: {horn.lower_height_m*1000:.1f} mm",
                          f"Umlenkspalt hinten: {horn.turn_gap_m*1000:.1f} mm",
                          f"Linienweg: {horn.path_length_m*1000:.1f} mm"])
        if bundle.rear_port:
            lines.extend([f"BR2 Rückkammer: Ø {(bundle.rear_port.diameter_m or 0)*1000:.1f} mm",
                          f"Fb2: {bundle.rear_port.tuning_hz:.2f} Hz",
                          f"BR2 Länge: {bundle.rear_port.physical_length_m*1000:.1f} mm"])
        if bundle.radiator:
            lines.extend(["", "PASSIVMEMBRAN",
                          f"Fb: {bundle.radiator.tuning_hz:.2f} Hz",
                          f"Grundmasse: {bundle.radiator.stock_mass_kg*1000:.1f} g",
                          f"Zusatzmasse: {bundle.radiator.added_mass_kg*1000:.1f} g",
                          f"Xmax: {bundle.radiator.xmax_m*1000:.1f} mm"])
        if bundle.front_chamber_volume_m3 is not None:
            lines.extend(["", "BANDPASS-KAMMERN",
                          f"Front ventiliert: {bundle.front_chamber_volume_m3*1000:.2f} l",
                          f"Rückkammer {'ventiliert' if bundle.rear_port else 'geschlossen'}: {bundle.rear_chamber_volume_m3*1000:.2f} l",
                          f"Trennwand ab Front innen: {bundle.partition_front_depth_m*1000:.1f} mm"])
            if bundle.vented_response and bundle.vented_response.upper_f3_hz:
                lines.append(f"Oberer -3-dB-Punkt: {bundle.vented_response.upper_f3_hz:.1f} Hz")

        lines.extend(["", "ZUSCHNITT"])
        for panel in bundle.panels:
            lines.append(
                f"{panel.quantity}x {panel.name}: "
                f"{panel.width_m*1000:.1f} x {panel.height_m*1000:.1f} x "
                f"{panel.thickness_m*1000:.1f} mm"
            )

        if bundle.crossover:
            lines.extend(
                [
                    "",
                    "FREQUENZWEICHE",
                    f"{bundle.crossover.name} @ {bundle.crossover.crossover_hz:.0f} Hz",
                ]
            )
            for component in bundle.crossover.components:
                lines.append(
                    f"{component.reference}: {component.display_value} "
                    f"({component.branch}, {component.connection})"
                )

        lines.extend(["", "WARNUNGEN / HINWEISE"])
        if bundle.warnings:
            lines.extend(f"• {warning}" for warning in bundle.warnings)
        else:
            lines.append("Keine automatischen Warnungen.")

        self.summary.setPlainText("\n".join(lines))

    def _render_drawing(self, bundle: DesignBundle) -> None:
        svg = render_assembly_svg(bundle)
        self.svg_preview.load(QByteArray(svg.encode("utf-8")))

    def _render_response(self, bundle: DesignBundle) -> None:
        self.figure.clear()
        axis = self.figure.add_subplot(111 if bundle.sealed is not None and bundle.front_horn is None else 221)
        if bundle.sealed is not None and bundle.front_horn is None:
            frequencies = np.geomspace(10.0, 500.0, 400)
            response = sealed_response_db(
                bundle.acoustic_driver,
                bundle.target_net_volume_m3,
                frequencies,
            )
            axis.semilogx(frequencies, response, label="Gehäuse")
            self._baffle_step_overlay(axis, bundle, frequencies, response)
            axis.axhline(-3.0, linewidth=0.8)
            axis.set_title("Normierter Kleinsignal-Frequenzgang – geschlossen")
            axis.set_xlabel("Frequenz [Hz]")
            axis.set_ylabel("Pegel [dB]")
            axis.set_ylim(-30, 5)
            axis.grid(True, which="both", alpha=0.25)
        else:
            response=bundle.vented_response
            if response is not None:
                axis.semilogx(response.frequencies_hz,response.response_db,
                             label="Vorderachse" if response.rear_response_db is not None else None)
                if response.rear_response_db is not None:
                    axis.semilogx(response.frequencies_hz,response.rear_response_db,
                                 label="Rückachse")
                    axis.legend()
                self._baffle_step_overlay(axis,bundle,response.frequencies_hz,response.response_db)
                axis.axhline(-3.0,linewidth=0.8)
                axis.set_title({"bass_reflex":"Bassreflex", "passive_radiator":"Passivmembran",
                                "bandpass_4":"Bandpass 4. Ordnung",
                                "bandpass_6_parallel":"Bandpass 6. Ordnung parallel",
                                "bandpass_6_series":"Bandpass 6. Ordnung seriell",
                                "compound_push_pull":"Compound / Push Pull",
                                "aperiodic":"Aperiodisch", "cardioid":"Passiv-Kardioid",
                                "horn_front":"Frontloaded Horn",
                                "horn_tapped":"Tapped Horn"}.get(bundle.project.enclosure.enclosure_type,
                                "Gehäuse")+" – Frequenzgang (relativ)")
                axis.set_xlabel("Hz");axis.set_ylabel("dB")
                axis.grid(True,which="both",alpha=0.25)
                for index,(values,title,unit) in enumerate((
                    (response.excursion_mm,"Membranauslenkung","mm"),
                    (response.port_velocity_m_s,
                     "Passivmembran-Geschwindigkeit" if bundle.radiator else "Portgeschwindigkeit","m/s"),
                    (response.group_delay_ms,"Gruppenlaufzeit","ms")),start=2):
                    ax=self.figure.add_subplot(2,2,index)
                    if values is None:
                        ax.text(.5,.5,"Treiberdaten fehlen",ha="center",va="center",transform=ax.transAxes)
                    else:
                        ax.semilogx(response.frequencies_hz,values)
                        if index==2 and bundle.project.driver.xmax_mm:
                            ax.axhline(bundle.project.driver.xmax_mm,color="red",linestyle="--",label="Xmax")
                        if index==3 and bundle.port is not None:
                            ax.axhline(17,color="orange",linestyle="--",label="Richtwert 17 m/s")
                    ax.set_title(title);ax.set_xlabel("Hz");ax.set_ylabel(unit)
                    ax.grid(True,which="both",alpha=.25)
        self.canvas.draw()

    @staticmethod
    def _baffle_step_overlay(axis: object, bundle: DesignBundle, frequencies: np.ndarray,
                             response_db: np.ndarray) -> None:
        """Dashed curve with the approximate baffle step for two-way speakers (not for subwoofers)."""
        if bundle.crossover is None or bundle.baffle_mode is not None:
            return
        width_m = bundle.cabinet.width_m
        axis.semilogx(frequencies, response_db + baffle_step_db(frequencies, width_m), linestyle="--",
                      label=f"mit Schallwandstufe ≈{baffle_step_frequency_hz(width_m):.0f} Hz (Näherung)")
        axis.legend(fontsize=8)

    def _render_crossover(self,bundle: DesignBundle) -> None:
        self.crossover_figure.clear()
        r=bundle.crossover_response
        if r is None:
            self.crossover_canvas.draw();return
        ax=self.crossover_figure.add_subplot(211)
        ax.semilogx(r.frequencies_hz,20*np.log10(np.maximum(abs(r.woofer_voltage),1e-12)),label="Woofer elektrisch")
        if r.midrange_voltage is not None:
            ax.semilogx(r.frequencies_hz,20*np.log10(np.maximum(abs(r.midrange_voltage),1e-12)),label="Mitteltöner elektrisch")
        ax.semilogx(r.frequencies_hz,20*np.log10(np.maximum(abs(r.tweeter_voltage),1e-12)),label="Tweeter elektrisch")
        if r.sum_acoustic_db is not None:
            ax.semilogx(r.frequencies_hz,r.woofer_acoustic_db,label="Woofer FRD")
            if r.midrange_acoustic_db is not None:
                ax.semilogx(r.frequencies_hz,r.midrange_acoustic_db,label="Mitteltöner FRD")
            ax.semilogx(r.frequencies_hz,r.tweeter_acoustic_db,label="Tweeter FRD")
            ax.semilogx(r.frequencies_hz,r.sum_acoustic_db,label="Summe"+("" if r.phase_complete else " (ohne Phase)"))
        ax.set_ylabel("Pegel [dB]");ax.set_xlabel("Frequenz [Hz]");ax.grid(True,which="both",alpha=.25);ax.legend()
        imp=self.crossover_figure.add_subplot(212)
        imp.semilogx(r.frequencies_hz,abs(r.total_impedance))
        imp.set_ylabel("Gesamtimpedanz [Ohm]");imp.set_xlabel("Frequenz [Hz]")
        imp.grid(True,which="both",alpha=.25)
        self.crossover_canvas.draw()

    def _compare_prototype(self) -> None:
        if self._bundle is None or self._dirty:
            QMessageBox.information(self, "Kein aktuelles Ergebnis",
                                    "Bitte zuerst das Projekt berechnen; der Vergleich nutzt die aktuelle Berechnung.")
            return
        PrototypeDialog(self._bundle, self).exec()

    def export(self) -> None:
        if self._bundle is None or self._dirty:
            self.calculate()
        if self._bundle is None:
            return

        directory = QFileDialog.getExistingDirectory(self, "Exportordner wählen")
        if not directory:
            return

        try:
            package = export_project_package(
                self._bundle, directory, stored_cutting_settings(self._bundle.project.material))
        except (OSError,ValueError) as exc:
            QMessageBox.critical(self, "Exportfehler", str(exc))
            return

        QMessageBox.information(
            self,
            "Export abgeschlossen",
            f"Fertigungsunterlagen wurden erstellt:\n{package}",
        )
        self.statusBar().showMessage(f"Exportiert: {package}")

    def _load_catalog(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Treiberdaten laden",
            "",
            "Treiberdaten (*.csv *.json);;CSV (*.csv);;JSON (*.json)",
        )
        if not filename:
            return
        try:
            if filename.lower().endswith(".json"):
                self._catalog = DriverCatalog.load_json(filename)
            else:
                self._catalog = DriverCatalog.load_csv(filename)
        except (OSError, ValueError, ValidationError, KeyError) as exc:
            QMessageBox.critical(self, "Importfehler", str(exc))
            return

        self.catalog_combo.blockSignals(True)
        self.catalog_combo.clear()
        self.catalog_combo.addItem("Manuelle Eingabe", None)
        for index, driver in enumerate(self._catalog.drivers):
            self.catalog_combo.addItem(f"{driver.manufacturer} — {driver.model}", index)
        self.catalog_combo.blockSignals(False)
        self.statusBar().showMessage(f"{len(self._catalog.drivers)} Treiber geladen")

    def _catalog_selected(self, _: int) -> None:
        index = self.catalog_combo.currentData()
        if index is None:
            return
        driver = self._catalog.drivers[int(index)]
        self._set_driver(driver)

    def _set_driver(self, driver: Driver) -> None:
        self._base_driver = driver
        self.manufacturer.setText(driver.manufacturer)
        self.driver_model.setText(driver.model)
        self.fs.setValue(driver.fs_hz)
        self.qts.setValue(driver.qts)
        self.qes.setValue(driver.qes or 0.0)
        self.qms.setValue(driver.qms or 0.0)
        self.vas.setValue(driver.vas_l)
        if driver.nominal_impedance_ohm:
            self.impedance.setValue(driver.nominal_impedance_ohm)
            self.woofer_impedance.setValue(driver.nominal_impedance_ohm)
        self.re.setValue(driver.re_ohm or 0.0)
        self.le.setValue((driver.le_h or 0.0) * 1000.0)
        self.sd.setValue((driver.sd_m2 or 0.0) * 10_000.0)
        self.xmax.setValue((driver.xmax_m or 0.0) * 1000.0)
        self.power_rating.setValue(driver.power_rms_w or 0.0)
        self.driver_displacement.setValue(driver.displacement_m3 * 1000.0)
        self.cutout.setValue((driver.cutout_diameter_m or 0.0) * 1000.0)
        self.outer_diameter.setValue((driver.outer_diameter_m or 0.0) * 1000.0)
        self.mounting_depth.setValue((driver.mounting_depth_m or 0.0) * 1000.0)
        self.source_name.setText(driver.source_name or "Import")

    def _load_project(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Projekt laden",
            "",
            "Lautsprecherprojekt (*.json);;JSON (*.json)",
        )
        if not filename:
            return
        try:
            project = SpeakerProject.model_validate_json(Path(filename).read_text(encoding="utf-8"))
        except (OSError, ValidationError) as exc:
            QMessageBox.critical(self, "Projektfehler", str(exc))
            return
        self._apply_project(project)
        self.calculate()

    def _apply_project(self, project: SpeakerProject) -> None:
        self._loading=True
        self._additional_drivers=project.additional_drivers
        self._accessories=project.accessories
        self._notes=project.notes
        self._round_to_standard=project.crossover.round_to_standard_values
        self.project_name.setText(project.name)
        self.material.setText(project.material)
        self._set_driver(project.driver)
        self._front_elements=list(project.front_elements)
        self._history.reset(tuple(self._front_elements))
        self._refresh_element_list()
        self._measurements={key:data for key,data in (
            ("woofer_frd",project.crossover.woofer_frd),("tweeter_frd",project.crossover.tweeter_frd),
            ("woofer_zma",project.crossover.woofer_zma),("tweeter_zma",project.crossover.tweeter_zma),
            ("mid_frd",project.crossover.mid_frd),("mid_zma",project.crossover.mid_zma)) if data is not None}
        self.measurement_status.setText("Geladen: "+", ".join(sorted(self._measurements)) if self._measurements else "Keine Messdaten geladen")
        enclosure_index = self.enclosure_type.findData(project.enclosure.enclosure_type)
        self.enclosure_type.setCurrentIndex(max(enclosure_index, 0))
        self.target_qtc.setValue(project.enclosure.target_qtc)
        if project.enclosure.target_volume_l:
            self.target_volume.setValue(project.enclosure.target_volume_l)
        self.rear_volume.setValue(project.enclosure.rear_volume_l)
        self.rear_tuning.setValue(project.enclosure.rear_tuning_hz or 30.0)
        self.rear_port_diameter.setValue(project.enclosure.rear_port_diameter_mm)
        self.aperiodic_resistance.setValue(project.enclosure.aperiodic_resistance_pa_s_m3 or 0.0)
        self.baffle_wing_depth.setValue(project.enclosure.baffle_wing_depth_mm)
        self.cardioid_delay.setValue(project.enclosure.cardioid_delay_ms)
        self.isobaric_wiring.setCurrentIndex(max(self.isobaric_wiring.findData(project.enclosure.isobaric_wiring), 0))
        self.isobaric_gap.setValue(project.enclosure.isobaric_gap_mm)
        if project.enclosure.tuning_hz:
            self.tuning.setValue(project.enclosure.tuning_hz)
        self.radiator_sd.setValue(project.enclosure.radiator_sd_cm2)
        self.radiator_mms.setValue(project.enclosure.radiator_mms_g)
        self.radiator_fs.setValue(project.enclosure.radiator_fs_hz)
        self.radiator_qms.setValue(project.enclosure.radiator_qms)
        self.radiator_xmax.setValue(project.enclosure.radiator_xmax_mm)
        self.radiator_cutout.setValue(project.enclosure.radiator_cutout_mm)
        self.radiator_depth.setValue(project.enclosure.radiator_depth_mm)
        self.input_power.setValue(project.enclosure.input_power_w)
        port_index = self.port_type.findData(project.enclosure.port_type)
        self.port_type.setCurrentIndex(max(port_index, 0))
        self.port_diameter.setValue(project.enclosure.port_diameter_mm)
        self.slot_width.setValue(project.enclosure.slot_width_mm)
        self.slot_height.setValue(project.enclosure.slot_height_mm)
        self.cabinet_width.setValue(project.enclosure.external_width_mm)
        self.cabinet_height.setValue(project.enclosure.external_height_mm)
        self.panel_thickness.setValue(project.enclosure.panel_thickness_mm)
        self.front_thickness.setValue(project.enclosure.front_thickness_mm or 0)
        self.back_thickness.setValue(project.enclosure.back_thickness_mm or 0)
        self.top_thickness.setValue(project.enclosure.top_thickness_mm or 0)
        self.bottom_thickness.setValue(project.enclosure.bottom_thickness_mm or 0)
        self.front_layers.setValue(project.enclosure.front_layers)
        self.additional_displacement.setValue(project.enclosure.additional_displacement_l)
        self.brace_count.setValue(project.enclosure.brace_quantity)
        self.brace_border.setValue(project.enclosure.brace_border_mm)
        self.joint_style.setCurrentIndex(max(self.joint_style.findData(project.enclosure.joint_style), 0))

        self.crossover_enabled.setChecked(project.crossover.enabled)
        topology_index = self.crossover_topology.findData(project.crossover.topology)
        self.crossover_topology.setCurrentIndex(max(topology_index, 0))
        self.crossover_ways.setCurrentIndex(max(self.crossover_ways.findData(project.crossover.ways), 0))
        self.crossover_frequency.setValue(project.crossover.crossover_hz)
        self.upper_frequency.setValue(project.crossover.upper_crossover_hz or 3500.0)
        self.mid_impedance.setValue(project.crossover.mid_impedance_ohm)
        self.mid_attenuation.setValue(project.crossover.mid_attenuation_db)
        self.woofer_impedance.setValue(project.crossover.woofer_impedance_ohm)
        self.tweeter_impedance.setValue(project.crossover.tweeter_impedance_ohm)
        self.tweeter_name.setText(project.tweeter_name)
        self.tweeter_attenuation.setValue(project.crossover.tweeter_attenuation_db)
        self.woofer_zobel.setChecked(project.crossover.add_woofer_zobel)
        self.baffle_step.setValue(project.crossover.baffle_step_compensation_db)
        self._refresh_mode_controls()
        self._loading=False

    def _save_project(self) -> None:
        try:
            project=self._project_from_form()
        except (ValueError,ValidationError) as exc:
            QMessageBox.critical(self,"Projektfehler",str(exc));return
        filename,_=QFileDialog.getSaveFileName(self,"Projekt speichern",
            f"{project.name}.json","Lautsprecherprojekt (*.json)")
        if filename:
            try:
                Path(filename).write_text(project.model_dump_json(indent=2),encoding="utf-8")
            except OSError as exc:
                QMessageBox.critical(self,"Speicherfehler",str(exc));return
            self.statusBar().showMessage(f"Gespeichert: {filename}")

    def _load_demo(self) -> None:
        self._apply_project(demo_project())
        self.calculate()
