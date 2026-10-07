"""Band inspector of the sound lab: band chips plus the parameters of the active band."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from lautsprecher_konstruktion.targets.eq import (
    FILTER_LABELS,
    FREQ_MAX_HZ,
    FREQ_MIN_HZ,
    GAIN_LIMIT_DB,
    EQBand,
    FilterType,
)


class BandInspector(QWidget):
    """Emits discrete user intentions; the editor owns the model and the history."""

    addRequested = Signal()
    removeRequested = Signal(str)
    selected = Signal(str)
    fieldEdited = Signal(str, str, object)  # band id, field name, new value

    def __init__(self) -> None:
        super().__init__()
        self._active: str | None = None
        self._building = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        chips = QHBoxLayout()
        chips.addWidget(QLabel("Filterbänder"))
        self._chip_box = QHBoxLayout()
        chips.addLayout(self._chip_box)
        self.add_button = QPushButton("+ Band")
        self.add_button.setObjectName("ghost")
        self.add_button.setToolTip("Neues Glockenfilter bei 1 kHz hinzufügen (oder Doppelklick im Graph)")
        self.add_button.clicked.connect(self.addRequested)
        chips.addWidget(self.add_button)
        chips.addStretch(1)
        layout.addLayout(chips)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._chips: dict[str, QPushButton] = {}

        self.hint = QLabel("Noch kein Filterband. Doppelklick im Graph oder „+ Band“ legt ein Band an; "
                           "Ziehen verschiebt Frequenz und Pegel.")
        self.hint.setObjectName("hint")
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)

        self.panel = QWidget()
        row = QHBoxLayout(self.panel)
        row.setContentsMargins(0, 0, 0, 0)
        self.enabled = QCheckBox("Aktiv")
        self.enabled.toggled.connect(lambda v: self._emit("enabled", bool(v)))
        row.addWidget(self.enabled)
        row.addWidget(QLabel("Typ"))
        self.kind = QComboBox()
        for key, label in FILTER_LABELS.items():
            self.kind.addItem(label, key)
        self.kind.currentIndexChanged.connect(lambda _i: self._emit("filter_type", self.kind.currentData()))
        row.addWidget(self.kind)
        row.addWidget(QLabel("Frequenz"))
        self.frequency = QDoubleSpinBox()
        self.frequency.setRange(FREQ_MIN_HZ, FREQ_MAX_HZ)
        self.frequency.setDecimals(0)
        self.frequency.setSuffix(" Hz")
        self.frequency.setKeyboardTracking(False)
        self.frequency.valueChanged.connect(lambda v: self._emit("frequency_hz", float(v)))
        row.addWidget(self.frequency)
        row.addWidget(QLabel("Gain"))
        self.gain = QDoubleSpinBox()
        self.gain.setRange(-GAIN_LIMIT_DB, GAIN_LIMIT_DB)
        self.gain.setDecimals(1)
        self.gain.setSingleStep(0.5)
        self.gain.setSuffix(" dB")
        self.gain.setKeyboardTracking(False)
        self.gain.valueChanged.connect(lambda v: self._emit("gain_db", float(v)))
        row.addWidget(self.gain)
        row.addWidget(QLabel("Q"))
        self.q = QDoubleSpinBox()
        self.q.setRange(0.2, 10.0)
        self.q.setDecimals(2)
        self.q.setSingleStep(0.1)
        self.q.setKeyboardTracking(False)
        self.q.valueChanged.connect(lambda v: self._emit("q", float(v)))
        row.addWidget(self.q)
        self.remove_button = QPushButton("Löschen")
        self.remove_button.clicked.connect(lambda: self._active and self.removeRequested.emit(self._active))
        row.addWidget(self.remove_button)
        row.addStretch(1)
        layout.addWidget(self.panel)
        self.panel.setVisible(False)

    @property
    def active_id(self) -> str | None:
        return self._active

    def summary(self, band: EQBand) -> str:
        kind = FILTER_LABELS[band.filter_type]
        if band.uses_gain:
            return f"{kind} | {band.frequency_hz:g} Hz | {band.gain_db:+.1f} dB | Q {band.q:g}"
        return f"{kind} | {band.frequency_hz:g} Hz | Q {band.q:g}"

    def set_bands(self, bands: tuple[EQBand, ...], active_id: str | None) -> None:
        self._building = True
        for chip in self._chips.values():
            self._group.removeButton(chip)
            chip.setParent(None)
            chip.deleteLater()
        self._chips = {}
        if active_id not in {b.id for b in bands}:
            active_id = bands[-1].id if bands else None
        self._active = active_id
        for number, band in enumerate(bands, start=1):
            chip = QPushButton(f"{number} · {FILTER_LABELS[band.filter_type]} {band.frequency_hz:g} Hz")
            chip.setObjectName("variantChip")
            chip.setCheckable(True)
            chip.setChecked(band.id == active_id)
            chip.setToolTip(self.summary(band))
            chip.clicked.connect(lambda _c=False, i=band.id: self.selected.emit(i))
            self._group.addButton(chip)
            self._chip_box.addWidget(chip)
            self._chips[band.id] = chip
        active = next((b for b in bands if b.id == active_id), None)
        self.hint.setVisible(not bands)
        self.panel.setVisible(active is not None)
        if active is not None:
            self.enabled.setChecked(active.enabled)
            self.kind.setCurrentIndex(self.kind.findData(active.filter_type))
            self.frequency.setValue(active.frequency_hz)
            self.gain.setValue(active.gain_db)
            self.q.setValue(active.q)
            self.gain.setEnabled(active.uses_gain)
            self.q.setToolTip("Güte: höher = schmaler" if active.filter_type is not FilterType.LOW_PASS else "")
        self._building = False

    def _emit(self, name: str, value: object) -> None:
        if self._building or self._active is None:
            return
        if name == "filter_type" and value is not None:
            value = FilterType(str(value))
        self.fieldEdited.emit(self._active, name, value)

    def keyPressEvent(self, event: object) -> None:
        if getattr(event, "key", lambda: None)() == Qt.Key.Key_Delete and self._active:
            self.removeRequested.emit(self._active)
            return
        super().keyPressEvent(event)  # type: ignore[arg-type]
