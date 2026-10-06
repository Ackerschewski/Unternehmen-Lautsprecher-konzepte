"""Interactive full-range target-curve editor used by the guided assistant.

The target is a design objective, not a measured response. The widget deliberately
shows only frequency ranges for which the selected design has response evidence.
"""
from __future__ import annotations

from collections.abc import Iterable

import matplotlib
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from lautsprecher_konstruktion.ui.theme import chart_rc
from lautsprecher_konstruktion.ui.tokens import theme

DEFAULT_FREQUENCIES = np.array(
    [20.0, 31.5, 50.0, 80.0, 125.0, 250.0, 500.0, 1000.0, 2000.0,
     4000.0, 8000.0, 16000.0, 20000.0],
    dtype=float,
)


class TargetCurveEditor(QWidget):
    """Editable EQ-like target curve with an optional evidence-backed actual curve."""

    curveChanged = Signal()

    def __init__(self, mode: str = "light") -> None:
        super().__init__()
        self.mode = mode
        self._frequencies = DEFAULT_FREQUENCIES.copy()
        self._levels = np.zeros_like(self._frequencies)
        self._actual_frequencies: np.ndarray | None = None
        self._actual_levels: np.ndarray | None = None
        self._undo: list[np.ndarray] = []
        self._drag_index: int | None = None
        self._syncing = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        heading = QHBoxLayout()
        text = QVBoxLayout()
        title = QLabel("Zielkurve")
        title.setObjectName("section")
        text.addWidget(title)
        note = QLabel(
            "Sollwert für den Entwurf · 20 Hz–20 kHz. Bereiche ohne belastbare "
            "Treiber-/Messdaten werden nicht als Ist-Frequenzgang erfunden."
        )
        note.setObjectName("caption")
        note.setWordWrap(True)
        text.addWidget(note)
        heading.addLayout(text, 1)
        reset = QPushButton("Neutral zurücksetzen")
        reset.clicked.connect(self.reset)
        heading.addWidget(reset)
        undo = QPushButton("Rückgängig")
        undo.clicked.connect(self.undo)
        heading.addWidget(undo)
        layout.addLayout(heading)

        self.figure = Figure(figsize=(10, 5), layout="constrained")
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setMinimumHeight(310)
        layout.addWidget(self.canvas, 1)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Punkt"))
        self.point = QComboBox()
        for value in self._frequencies:
            label = f"{value/1000:g} kHz" if value >= 1000 else f"{value:g} Hz"
            self.point.addItem(label)
        self.point.currentIndexChanged.connect(self._selected_point_changed)
        controls.addWidget(self.point)
        controls.addWidget(QLabel("Zielpegel"))
        self.level = QDoubleSpinBox()
        self.level.setRange(-12.0, 12.0)
        self.level.setSingleStep(0.5)
        self.level.setDecimals(1)
        self.level.setSuffix(" dB")
        self.level.valueChanged.connect(self._numeric_level_changed)
        controls.addWidget(self.level)
        self.readout = QLabel("20 Hz · 0,0 dB")
        self.readout.setObjectName("caption")
        controls.addWidget(self.readout)
        controls.addStretch(1)
        layout.addLayout(controls)

        self.canvas.mpl_connect("button_press_event", self._press)
        self.canvas.mpl_connect("motion_notify_event", self._motion)
        self.canvas.mpl_connect("button_release_event", self._release)
        self._draw()

    def points(self) -> tuple[tuple[float, float], ...]:
        return tuple((float(f), float(v)) for f, v in zip(self._frequencies, self._levels, strict=True))

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        self._draw()

    def set_actual_curve(self, frequencies_hz: Iterable[float], response_db: Iterable[float]) -> None:
        freq = np.asarray(tuple(frequencies_hz), dtype=float)
        values = np.asarray(tuple(response_db), dtype=float)
        valid = np.isfinite(freq) & np.isfinite(values) & (freq >= 20) & (freq <= 20000)
        self._actual_frequencies = freq[valid]
        self._actual_levels = values[valid]
        self._draw()

    def clear_actual(self) -> None:
        self._actual_frequencies = None
        self._actual_levels = None
        self._draw()

    def reset(self) -> None:
        if np.allclose(self._levels, 0.0):
            return
        self._remember()
        self._levels[:] = 0.0
        self._sync_controls()
        self._draw()
        self.curveChanged.emit()

    def undo(self) -> None:
        if not self._undo:
            return
        self._levels = self._undo.pop()
        self._sync_controls()
        self._draw()
        self.curveChanged.emit()

    def _remember(self) -> None:
        self._undo.append(self._levels.copy())
        if len(self._undo) > 40:
            self._undo.pop(0)

    def _selected_point_changed(self, _index: int) -> None:
        self._sync_controls()
        self._draw()

    def _sync_controls(self) -> None:
        index = max(0, self.point.currentIndex())
        self._syncing = True
        self.level.setValue(float(self._levels[index]))
        f = self._frequencies[index]
        self.readout.setText(
            f"{f/1000:g} kHz · {self._levels[index]:+.1f} dB"
            if f >= 1000 else f"{f:g} Hz · {self._levels[index]:+.1f} dB"
        )
        self._syncing = False

    def _numeric_level_changed(self, value: float) -> None:
        if self._syncing:
            return
        index = max(0, self.point.currentIndex())
        if abs(self._levels[index] - value) < 1e-9:
            return
        self._remember()
        self._levels[index] = value
        self._sync_controls()
        self._draw()
        self.curveChanged.emit()

    def _press(self, event: object) -> None:
        if getattr(event, "inaxes", None) is None or getattr(event, "button", None) != 1:
            return
        x = getattr(event, "xdata", None)
        if x is None or x <= 0:
            return
        index = int(np.argmin(np.abs(np.log10(self._frequencies) - np.log10(float(x)))))
        self._remember()
        self._drag_index = index
        self.point.setCurrentIndex(index)
        self._set_drag_value(getattr(event, "ydata", None))

    def _motion(self, event: object) -> None:
        if self._drag_index is None or getattr(event, "inaxes", None) is None:
            return
        self._set_drag_value(getattr(event, "ydata", None))

    def _release(self, _event: object) -> None:
        if self._drag_index is None:
            return
        self._drag_index = None
        self.curveChanged.emit()

    def _set_drag_value(self, y: object) -> None:
        if y is None or self._drag_index is None:
            return
        self._levels[self._drag_index] = float(np.clip(float(y), -12.0, 12.0))
        self._sync_controls()
        self._draw()

    def _draw(self) -> None:
        t = theme(self.mode)
        with matplotlib.rc_context(chart_rc(self.mode)):
            self.figure.clear()
            ax = self.figure.add_subplot(1, 1, 1)
            ax.set_xscale("log")
            ax.set_xlim(20, 20000)
            ax.set_ylim(-15, 15)
            ax.set_xlabel("Frequenz [Hz]")
            ax.set_ylabel("relativer Zielpegel [dB]")
            ax.set_title("Fullrange-Zielkurve")
            ax.axhline(0.0, color=t["borderStrong"], linewidth=1.0, linestyle=":")
            ax.semilogx(
                self._frequencies, self._levels, linewidth=2.4, marker="o",
                markersize=5, label="Zielkurve", color=t["accent"],
            )
            selected = max(0, self.point.currentIndex())
            ax.scatter(
                [self._frequencies[selected]], [self._levels[selected]],
                s=70, facecolors=t["surface"], edgecolors=t["accent"], linewidths=2.0,
                zorder=5,
            )
            if self._actual_frequencies is not None and self._actual_frequencies.size:
                ax.semilogx(
                    self._actual_frequencies, self._actual_levels, linewidth=1.8,
                    label="Ist · berechenbarer Bereich", color=t["textSecondary"],
                )
                max_known = float(np.max(self._actual_frequencies))
                if max_known < 20000:
                    ax.axvspan(max(max_known, 20), 20000, color=t["band"], alpha=0.45, zorder=-2)
                    ax.text(
                        min(max_known * 1.35, 15000), -13.2,
                        "keine belastbaren Fullrange-Daten",
                        color=t["textSecondary"], fontsize=9, ha="left",
                    )
            else:
                ax.text(
                    .5, .08, "Noch kein Ist-Frequenzgang geladen/berechnet",
                    transform=ax.transAxes, color=t["textSecondary"], ha="center", fontsize=9,
                )
            ax.legend(loc="upper right")
            ax.grid(True, which="both", alpha=.65)
        self.canvas.draw_idle()
