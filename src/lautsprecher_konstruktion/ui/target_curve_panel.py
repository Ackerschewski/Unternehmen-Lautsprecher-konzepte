"""Editable full-range target curve (a goal, not a measurement) with numeric entry, undo/redo and actual curve."""
from __future__ import annotations

import time

import numpy as np
from matplotlib.backend_bases import MouseEvent
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from numpy.typing import NDArray
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from lautsprecher_konstruktion.targets.curve import (
    FREQ_MAX_HZ,
    FREQ_MIN_HZ,
    GAIN_LIMIT_DB,
    KIND_LABEL,
    MODEL_BAND_HZ,
    PRESETS,
    TargetBand,
    TargetCurve,
    deviation,
)
from lautsprecher_konstruktion.ui.history import History
from lautsprecher_konstruktion.ui.theme import chart_rc
from lautsprecher_konstruktion.ui.tokens import theme as theme_tokens

PICK_RADIUS_PX = 12
DRAG_REDRAW_S = 0.03  # fast preview while dragging; the exact calculation follows after release


class TargetCurvePanel(QWidget):
    """Graph (mouse) and table (numbers) edit the same curve; changes are signalled once per edit."""

    curveChanged = Signal(object)  # TargetCurve, emitted when an edit is finished

    def __init__(self) -> None:
        super().__init__()
        self.mode = "light"
        self._history: History[TargetCurve] = History(TargetCurve())
        self._frequencies: NDArray[np.float64] | None = None
        self._response: NDArray[np.float64] | None = None
        self._drag: int | None = None
        self._drag_start: TargetCurve | None = None
        self._last_draw = 0.0
        self._building = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel("Zielkurve · Sollwert, kein gemessener Frequenzgang")
        title.setObjectName("eyebrow")
        layout.addWidget(title)
        bar = QHBoxLayout()
        self.preset = QComboBox()
        self.preset.addItems(list(PRESETS))
        self.preset.setToolTip("Startkurven. Neutral ist eine gerade Linie.")
        self.preset.activated.connect(self._preset_chosen)
        bar.addWidget(QLabel("Startkurve"))
        bar.addWidget(self.preset)
        self.add_button = QPushButton("Punkt hinzufügen")
        self.add_button.clicked.connect(self._add_default_band)
        self.undo_button = QPushButton("Rückgängig")
        self.undo_button.clicked.connect(self.undo)
        self.redo_button = QPushButton("Wiederholen")
        self.redo_button.clicked.connect(self.redo)
        self.reset_button = QPushButton("Neutral")
        self.reset_button.setToolTip("Auf die gerade Referenzkurve zurücksetzen")
        self.reset_button.clicked.connect(self.reset)
        for widget in (self.add_button, self.undo_button, self.redo_button, self.reset_button):
            bar.addWidget(widget)
        bar.addStretch(1)
        layout.addLayout(bar)

        self.figure = Figure(figsize=(8, 3.4), layout="constrained")
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setMinimumHeight(280)
        self.canvas.mpl_connect("button_press_event", self._on_press)
        self.canvas.mpl_connect("motion_notify_event", self._on_motion)
        self.canvas.mpl_connect("button_release_event", self._on_release)
        layout.addWidget(self.canvas, 1)
        self.info = QLabel()
        self.info.setObjectName("hint")
        self.info.setWordWrap(True)
        layout.addWidget(self.info)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(("Art", "Frequenz [Hz]", "Pegel [dB]", "Güte Q", ""))
        self.table.verticalHeader().setVisible(False)
        self.table.setMaximumHeight(190)
        self.table.verticalHeader().setDefaultSectionSize(42)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setMinimumSectionSize(110)
        layout.addWidget(self.table)
        self.hint = QLabel("Punkte ziehen, Doppelklick fügt einen Punkt hinzu, Rechtsklick auf einen Punkt entfernt ihn. "
                           "Alternativ Werte in der Tabelle eingeben.")
        self.hint.setObjectName("hint")
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)
        self._refresh(all_widgets=True)

    # --- state ---------------------------------------------------------------------------------------------

    def curve(self) -> TargetCurve:
        return self._history.current

    def set_curve(self, curve: TargetCurve | None, *, emit: bool = False) -> None:
        self._history.reset(curve or TargetCurve())
        self._refresh(all_widgets=True)
        if emit:
            self.curveChanged.emit(self.curve())

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        self._draw()

    def set_actual(self, frequencies_hz: NDArray[np.float64] | None, response_db: NDArray[np.float64] | None) -> None:
        """Calculated (relative) response of the selected design, or None to show the target alone."""
        self._frequencies, self._response = frequencies_hz, response_db
        self._draw()

    def deviation_text(self) -> str:
        if self._frequencies is None or self._response is None:
            return "Kein Entwurf ausgewählt: es wird nur die Zielkurve angezeigt."
        dev = deviation(self.curve(), self._frequencies, self._response)
        if dev is None:
            return "Der berechnete Verlauf deckt den Vergleichsbereich nicht ab."
        return (f"Abweichung im Tiefton {dev.low_hz:.0f}–{dev.high_hz:.0f} Hz: Ø {dev.mean_abs_db:.1f} dB, "
                f"maximal {dev.max_abs_db:.1f} dB (beide Kurven bei 120–300 Hz angeglichen). "
                "Oberhalb von 500 Hz liegen keine Chassis-Messdaten vor: dort wird nichts berechnet.")

    def _push(self, curve: TargetCurve, key: object | None = None) -> None:
        if self._history.push(curve, key):
            self._refresh(all_widgets=True)
            self.curveChanged.emit(self.curve())

    def undo(self) -> None:
        if self._history.undo() is not None:
            self._refresh(all_widgets=True)
            self.curveChanged.emit(self.curve())

    def redo(self) -> None:
        if self._history.redo() is not None:
            self._refresh(all_widgets=True)
            self.curveChanged.emit(self.curve())

    def reset(self) -> None:
        self._push(TargetCurve())
        self.preset.setCurrentIndex(0)

    def _preset_chosen(self, index: int) -> None:
        self._push(PRESETS[self.preset.itemText(index)])

    def _add_default_band(self) -> None:
        self._push(self.curve().with_band(TargetBand(kind="peak", frequency_hz=1000.0, gain_db=0.0, q=1.0)))

    # --- table ---------------------------------------------------------------------------------------------

    def _fill_table(self) -> None:
        self._building = True
        bands = self.curve().bands
        self.table.setRowCount(len(bands))
        for row, band in enumerate(bands):
            kind = QComboBox()
            for key, label in KIND_LABEL.items():
                kind.addItem(label, key)
            kind.setCurrentIndex(kind.findData(band.kind))
            kind.currentIndexChanged.connect(lambda _i, r=row, w=kind: self._edit_row(r, kind=w.currentData()))
            self.table.setCellWidget(row, 0, kind)
            for column, value, low, high, decimals, step, name in (
                    (1, band.frequency_hz, FREQ_MIN_HZ, FREQ_MAX_HZ, 0, 10.0, "frequency_hz"),
                    (2, band.gain_db, -GAIN_LIMIT_DB, GAIN_LIMIT_DB, 1, 0.5, "gain_db"),
                    (3, band.q, 0.3, 8.0, 2, 0.1, "q")):
                spin = QDoubleSpinBox()
                spin.setRange(low, high)
                spin.setDecimals(decimals)
                spin.setSingleStep(step)
                spin.setValue(value)
                spin.setKeyboardTracking(False)
                spin.valueChanged.connect(lambda v, r=row, n=name: self._edit_row(r, **{n: v}))
                self.table.setCellWidget(row, column, spin)
            remove = QPushButton("Entfernen")
            remove.clicked.connect(lambda _c=False, r=row: self._push(self.curve().without_band(r)))
            self.table.setCellWidget(row, 4, remove)
        self.table.setVisible(bool(bands))
        self._building = False

    def _edit_row(self, row: int, **changes: object) -> None:
        if self._building or row >= len(self.curve().bands):
            return
        band = self.curve().bands[row].model_copy(update=changes)
        self._push(self.curve().with_replaced(row, band), key=("row", row, tuple(changes)))

    # --- graph ---------------------------------------------------------------------------------------------

    def _refresh(self, *, all_widgets: bool) -> None:
        if all_widgets:
            self._fill_table()
            self.undo_button.setEnabled(self._history.can_undo)
            self.redo_button.setEnabled(self._history.can_redo)
        self._draw()

    def _draw(self) -> None:
        t = theme_tokens(self.mode)
        import matplotlib
        with matplotlib.rc_context(chart_rc(self.mode)):
            self.figure.clear()
            self.figure.set_facecolor(t["surface"])
            ax = self.figure.add_subplot(1, 1, 1)
            f = np.geomspace(FREQ_MIN_HZ, FREQ_MAX_HZ, 600)
            ax.set_xscale("log")
            ax.set_xlim(FREQ_MIN_HZ, FREQ_MAX_HZ)
            ax.set_ylim(-GAIN_LIMIT_DB, GAIN_LIMIT_DB)
            ax.set_xlabel("Frequenz [Hz]")
            ax.set_ylabel("Pegel relativ [dB]")
            ax.axvspan(MODEL_BAND_HZ[1], FREQ_MAX_HZ, facecolor=t["panel"], alpha=0.9, zorder=0)
            ax.text(0.97, 0.06, "Mittel-/Hochton: keine Messdaten – nicht berechnet", transform=ax.transAxes,
                    ha="right", color=t["textSecondary"], fontsize=9)
            ax.axhline(0, color=t["borderStrong"], linewidth=0.8)
            curve = self.curve()
            ax.plot(f, curve.level_db(f), color=t["accent"], linewidth=2.2, label="Zielkurve (Sollwert)", zorder=3)
            if curve.bands:
                ax.plot([b.frequency_hz for b in curve.bands], [b.gain_db for b in curve.bands], "o",
                        color=t["accent"], markersize=9, markeredgecolor=t["textPrimary"], zorder=4)
            if self._frequencies is not None and self._response is not None:
                dev = deviation(curve, self._frequencies, self._response)
                if dev is not None:
                    fr = self._frequencies
                    sel = (fr >= MODEL_BAND_HZ[0]) & (fr <= MODEL_BAND_HZ[1])
                    ax.plot(fr[sel], (self._response - dev.reference_offset_db)[sel], color=t["textPrimary"],
                            linewidth=1.6, linestyle="--", label="Berechneter Tiefton (relativ)", zorder=3)
            ax.legend(loc="upper right", fontsize=9)
        self.info.setText(self.deviation_text())
        self.canvas.draw_idle()

    def _nearest(self, event: MouseEvent) -> int | None:
        ax = self.figure.axes[0] if self.figure.axes else None
        if ax is None or event.x is None or event.y is None:
            return None
        best, best_d = None, float(PICK_RADIUS_PX)
        for index, band in enumerate(self.curve().bands):
            px, py = ax.transData.transform((band.frequency_hz, band.gain_db))
            d = float(np.hypot(px - event.x, py - event.y))
            if d <= best_d:
                best, best_d = index, d
        return best

    def _on_press(self, event: MouseEvent) -> None:
        if not self.figure.axes or event.inaxes is not self.figure.axes[0] or event.xdata is None:
            return
        index = self._nearest(event)
        if event.button == 3 and index is not None:  # right click removes
            self._push(self.curve().without_band(index))
        elif event.dblclick and index is None and event.ydata is not None:
            self._push(self.curve().with_band(TargetBand(kind="peak", frequency_hz=float(event.xdata),
                                                         gain_db=float(np.clip(event.ydata, -GAIN_LIMIT_DB, GAIN_LIMIT_DB)),
                                                         q=1.0)))
        elif event.button == 1 and index is not None:
            self._drag, self._drag_start = index, self.curve()

    def _on_motion(self, event: MouseEvent) -> None:
        if self._drag is None or event.xdata is None or event.ydata is None:
            return
        now = time.monotonic()
        if now - self._last_draw < DRAG_REDRAW_S:
            return
        self._last_draw = now
        # fast preview only: replace the newest state without notifying the solver
        self._history.replace_current(self.curve().with_moved(self._drag, float(event.xdata), float(event.ydata)))
        self._draw()

    def _on_release(self, event: MouseEvent) -> None:
        if self._drag is None:
            return
        index, start, self._drag = self._drag, self._drag_start, None
        if event.xdata is not None and event.ydata is not None:  # last pointer position wins over throttled previews
            self._history.replace_current(self.curve().with_moved(index, float(event.xdata), float(event.ydata)))
        final = self.curve()
        if start is not None:
            self._history.replace_current(start)
            self._push(final)
        self._refresh(all_widgets=True)

