"""Interactive full-range target-curve editor and evidence-aware sound lab.

The target curve is a design objective, not a measured response. Actual curves and
feasibility envelopes are drawn only from data/calculations that exist in the current
project; unknown full-range regions remain explicitly unknown.
"""
from __future__ import annotations

from collections.abc import Iterable
from math import log2

import matplotlib
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
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

PRESETS: dict[str, tuple[str, tuple[float, ...]]] = {
    "neutral": ("Neutral", (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)),
    "warm": ("Warm", (3.5, 3.0, 2.4, 1.6, 0.8, 0.3, 0, 0, -0.2, -0.6, -1.0, -1.5, -1.7)),
    "house": ("House Curve", (5.0, 4.4, 3.5, 2.5, 1.7, 0.8, 0.2, 0, -0.4, -0.8, -1.3, -1.8, -2.0)),
    "nearfield": ("Nahfeld", (1.5, 1.2, 0.8, 0.4, 0.1, 0, 0, 0, 0, -0.3, -0.7, -1.0, -1.2)),
}

ANALYSIS_MODES = (
    ("overall", "Gesamt"),
    ("enclosure", "Gehäuse"),
    ("driver", "Chassis"),
    ("crossover", "Weiche"),
    ("dsp", "DSP"),
    ("influence", "Einfluss"),
)

MODE_TEXT = {
    "overall": "Gesamt: alle aktuell berechenbaren Varianten und Freiheitsgrade vergleichen.",
    "enclosure": "Gehäuse: Unterschiede zwischen berechneten Gehäusevarianten hervorheben.",
    "driver": "Chassis: Varianten mit anderen Treibern vergleichen, sofern berechnet.",
    "crossover": "Weiche: Fullrange-Aussagen nur mit vorhandenen FRD/ZMA-Daten.",
    "dsp": "DSP: Zielkurve formen; Headroom-/Hubgrenzen bleiben maßgeblich.",
    "influence": "Einfluss: zeigt, welche berechnete Alternative an kritischen Frequenzen näher am Ziel liegt.",
}


class TargetCurveEditor(QWidget):
    """Editable EQ-like target curve with evidence-backed overlays."""

    curveChanged = Signal()
    analysisModeChanged = Signal(str)
    frequencySelected = Signal(float)

    def __init__(self, mode: str = "light") -> None:
        super().__init__()
        self.mode = mode
        self._frequencies = DEFAULT_FREQUENCIES.copy()
        self._levels = np.zeros_like(self._frequencies)
        self._actual_frequencies: np.ndarray | None = None
        self._actual_levels: np.ndarray | None = None
        self._actual_label = "Ist · berechenbarer Bereich"
        self._envelope_frequencies: np.ndarray | None = None
        self._envelope_low: np.ndarray | None = None
        self._envelope_high: np.ndarray | None = None
        self._candidate_curves: list[tuple[np.ndarray, np.ndarray]] = []
        self._undo: list[np.ndarray] = []
        self._drag_index: int | None = None
        self._syncing = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        heading = QHBoxLayout()
        title = QLabel("Zielkurve · Sollwert")
        title.setObjectName("section")
        title.setToolTip(
            "Sollwert für den Entwurf · 20 Hz–20 kHz. Ziehen, numerisch ändern oder "
            "parametrisches Zielband anwenden. Unbelegte Frequenzbereiche werden nicht erfunden."
        )
        heading.addWidget(title, 1)

        heading.addWidget(QLabel("Preset"))
        self.preset = QComboBox()
        for key, (label, _values) in PRESETS.items():
            self.preset.addItem(label, key)
        self.preset.addItem("Benutzerdefiniert", "custom")
        self.preset.currentIndexChanged.connect(self._preset_changed)
        heading.addWidget(self.preset)

        heading.addWidget(QLabel("Analyse"))
        self.analysis = QComboBox()
        for key, label in ANALYSIS_MODES:
            self.analysis.addItem(label, key)
        self.analysis.currentIndexChanged.connect(self._analysis_changed)
        heading.addWidget(self.analysis)

        reset = QPushButton("Neutral")
        reset.clicked.connect(self.reset)
        heading.addWidget(reset)
        undo = QPushButton("Rückgängig")
        undo.clicked.connect(self.undo)
        heading.addWidget(undo)
        layout.addLayout(heading)

        self.figure = Figure(figsize=(10, 5), layout="constrained")
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setMinimumHeight(300)
        layout.addWidget(self.canvas, 1)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Punkt"))
        self.point = QComboBox()
        for value in self._frequencies:
            label = f"{value/1000:g} kHz" if value >= 1000 else f"{value:g} Hz"
            self.point.addItem(label)
        self.point.currentIndexChanged.connect(self._selected_point_changed)
        controls.addWidget(self.point)
        controls.addWidget(QLabel("Ziel"))
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
        controls.addSpacing(16)
        controls.addWidget(QLabel("Zielband"))
        band = controls
        self.band_frequency = QDoubleSpinBox()
        self.band_frequency.setRange(20, 20000)
        self.band_frequency.setValue(100)
        self.band_frequency.setDecimals(0)
        self.band_frequency.setSuffix(" Hz")
        band.addWidget(self.band_frequency)
        self.band_gain = QDoubleSpinBox()
        self.band_gain.setRange(-12, 12)
        self.band_gain.setValue(2)
        self.band_gain.setSingleStep(0.5)
        self.band_gain.setSuffix(" dB")
        band.addWidget(self.band_gain)
        self.band_q = QDoubleSpinBox()
        self.band_q.setRange(0.2, 10.0)
        self.band_q.setValue(1.0)
        self.band_q.setSingleStep(0.1)
        self.band_q.setPrefix("Q ")
        band.addWidget(self.band_q)
        apply_band = QPushButton("Band anwenden")
        apply_band.clicked.connect(self.apply_parametric_band)
        band.addWidget(apply_band)
        band.addStretch(1)
        layout.addLayout(controls)

        self.influence = QLabel(MODE_TEXT["overall"])
        self.influence.setObjectName("recommendation")
        self.influence.setWordWrap(True)
        layout.addWidget(self.influence)

        influence_grid = QGridLayout()
        influence_grid.setContentsMargins(0, 0, 0, 0)
        influence_grid.setHorizontalSpacing(8)
        self.influence_cards: dict[str, QLabel] = {}
        for column, (key, title) in enumerate((
            ("enclosure", "Gehäuse"),
            ("driver", "Chassis"),
            ("crossover", "Weiche"),
            ("dsp", "DSP"),
        )):
            card = QLabel(f"<b>{title}</b><br>noch keine Vergleichsdaten")
            card.setObjectName("kpi")
            card.setWordWrap(True)
            influence_grid.addWidget(card, 0, column)
            influence_grid.setColumnStretch(column, 1)
            self.influence_cards[key] = card
        layout.addLayout(influence_grid)

        self.canvas.mpl_connect("button_press_event", self._press)
        self.canvas.mpl_connect("motion_notify_event", self._motion)
        self.canvas.mpl_connect("button_release_event", self._release)
        self._draw()

    def points(self) -> tuple[tuple[float, float], ...]:
        return tuple(
            (float(f), float(v))
            for f, v in zip(self._frequencies, self._levels, strict=True)
        )

    def set_points(self, points: Iterable[tuple[float, float]]) -> None:
        data = np.asarray(tuple(points), dtype=float)
        if data.size == 0:
            self.reset()
            return
        if data.ndim != 2 or data.shape[1] != 2 or np.any(data[:, 0] <= 0):
            raise ValueError("target curve points must be (frequency_hz, level_db)")
        self._levels = np.interp(
            np.log10(self._frequencies), np.log10(data[:, 0]), data[:, 1]
        )
        self._levels = np.clip(self._levels, -12.0, 12.0)
        self._set_preset_combo("custom")
        self._sync_controls()
        self._draw()

    def preset_id(self) -> str:
        return str(self.preset.currentData())

    def restore_state(
        self,
        points: Iterable[tuple[float, float]],
        *,
        preset: str = "custom",
        analysis_mode: str = "overall",
    ) -> None:
        data = tuple(points)
        if data:
            self.set_points(data)
        else:
            self._levels[:] = 0.0
            self._sync_controls()
            self._draw()
        if self.preset.findData(preset) >= 0:
            self._set_preset_combo(preset)
        self.set_analysis_mode(analysis_mode)

    def selected_frequency_hz(self) -> float:
        index = max(0, self.point.currentIndex())
        return float(self._frequencies[index])

    def set_component_influence(self, values: dict[str, str]) -> None:
        titles = {
            "enclosure": "Gehäuse",
            "driver": "Chassis",
            "crossover": "Weiche",
            "dsp": "DSP",
        }
        for key, card in self.influence_cards.items():
            card.setText(f"<b>{titles[key]}</b><br>{values.get(key, 'keine belastbaren Vergleichsdaten')}")

    def analysis_mode(self) -> str:
        return str(self.analysis.currentData())

    def set_analysis_mode(self, value: str) -> None:
        index = self.analysis.findData(value)
        if index >= 0:
            self.analysis.setCurrentIndex(index)

    def set_influence_summary(self, text: str | None = None) -> None:
        base = MODE_TEXT.get(self.analysis_mode(), "")
        self.influence.setText(base if not text else f"{base}\n{text}")

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        self._draw()

    @staticmethod
    def _normalise(
        frequencies: np.ndarray, values: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        valid = np.isfinite(frequencies) & np.isfinite(values) & (frequencies > 0)
        f = frequencies[valid]
        v = values[valid].astype(float, copy=True)
        if f.size == 0:
            return f, v
        reference = (f >= 80.0) & (f <= 120.0)
        if np.any(reference):
            v -= float(np.median(v[reference]))
        else:
            v -= float(np.median(v))
        return f, v

    def set_actual_curve(
        self,
        frequencies_hz: Iterable[float],
        response_db: Iterable[float],
        *,
        label: str = "Ist · berechenbarer Bereich",
    ) -> None:
        freq = np.asarray(tuple(frequencies_hz), dtype=float)
        values = np.asarray(tuple(response_db), dtype=float)
        valid = np.isfinite(freq) & np.isfinite(values) & (freq >= 20) & (freq <= 20000)
        freq, values = self._normalise(freq[valid], values[valid])
        self._actual_frequencies = freq
        self._actual_levels = values
        self._actual_label = label
        self._draw()

    def clear_actual(self) -> None:
        self._actual_frequencies = None
        self._actual_levels = None
        self._draw()

    def set_candidate_curves(
        self,
        curves: Iterable[tuple[Iterable[float], Iterable[float]]],
    ) -> None:
        prepared: list[tuple[np.ndarray, np.ndarray]] = []
        for frequencies, levels in curves:
            f = np.asarray(tuple(frequencies), dtype=float)
            v = np.asarray(tuple(levels), dtype=float)
            if f.size != v.size:
                continue
            f, v = self._normalise(f, v)
            if f.size >= 8:
                prepared.append((f, v))
        self._candidate_curves = prepared[:4]
        if not prepared:
            self._envelope_frequencies = self._envelope_low = self._envelope_high = None
            self._draw()
            return
        low_bound = max(20.0, min(float(f[0]) for f, _ in prepared))
        high_bound = min(20000.0, max(float(f[-1]) for f, _ in prepared))
        if high_bound <= low_bound:
            self._candidate_curves = []
            self._envelope_frequencies = self._envelope_low = self._envelope_high = None
            self._draw()
            return
        grid = np.geomspace(low_bound, high_bound, 360)
        rows: list[np.ndarray] = []
        for f, v in prepared:
            row = np.full(grid.shape, np.nan)
            inside = (grid >= f[0]) & (grid <= f[-1])
            row[inside] = np.interp(np.log10(grid[inside]), np.log10(f), v)
            rows.append(row)
        matrix = np.vstack(rows)
        count = np.sum(np.isfinite(matrix), axis=0)
        valid = count >= 1
        self._envelope_frequencies = grid[valid]
        self._envelope_low = np.nanmin(matrix[:, valid], axis=0)
        self._envelope_high = np.nanmax(matrix[:, valid], axis=0)
        self._draw()

    def outside_envelope(self) -> tuple[float, float] | None:
        if (
            self._envelope_frequencies is None
            or self._envelope_low is None
            or self._envelope_high is None
        ):
            return None
        f = self._envelope_frequencies
        low = self._envelope_low
        high = self._envelope_high
        worst: tuple[float, float] | None = None
        for target_f, target_db in self.points():
            if target_f < f[0] or target_f > f[-1]:
                continue
            lo = float(np.interp(np.log10(target_f), np.log10(f), low))
            hi = float(np.interp(np.log10(target_f), np.log10(f), high))
            distance = lo-target_db if target_db < lo else target_db-hi if target_db > hi else 0.0
            if distance > 0 and (worst is None or distance > worst[1]):
                worst = (target_f, distance)
        return worst

    def reset(self) -> None:
        if np.allclose(self._levels, 0.0):
            self._set_preset_combo("neutral")
            return
        self._remember()
        self._levels[:] = 0.0
        self._set_preset_combo("neutral")
        self._sync_controls()
        self._draw()
        self.curveChanged.emit()

    def undo(self) -> None:
        if not self._undo:
            return
        self._levels = self._undo.pop()
        self._set_preset_combo("custom")
        self._sync_controls()
        self._draw()
        self.curveChanged.emit()

    def apply_parametric_band(self) -> None:
        self._remember()
        f0 = self.band_frequency.value()
        gain = self.band_gain.value()
        q = max(0.2, self.band_q.value())
        sigma_oct = max(0.06, 0.72/q)
        offsets = np.array([log2(f/f0) for f in self._frequencies], dtype=float)
        delta = gain*np.exp(-0.5*np.square(offsets/sigma_oct))
        self._levels = np.clip(self._levels+delta, -12.0, 12.0)
        self._set_preset_combo("custom")
        self._sync_controls()
        self._draw()
        self.curveChanged.emit()

    def _set_preset_combo(self, key: str) -> None:
        index = self.preset.findData(key)
        if index < 0:
            return
        self._syncing = True
        self.preset.setCurrentIndex(index)
        self._syncing = False

    def _preset_changed(self, _index: int) -> None:
        if self._syncing:
            return
        key = str(self.preset.currentData())
        if key == "custom":
            return
        preset = PRESETS[key][1]
        self._remember()
        self._levels = np.asarray(preset, dtype=float)
        self._sync_controls()
        self._draw()
        self.curveChanged.emit()

    def _analysis_changed(self, _index: int) -> None:
        if self._syncing:
            return
        mode = self.analysis_mode()
        self.set_influence_summary()
        self.analysisModeChanged.emit(mode)

    def _remember(self) -> None:
        self._undo.append(self._levels.copy())
        if len(self._undo) > 40:
            self._undo.pop(0)

    def _mark_custom(self) -> None:
        self._set_preset_combo("custom")

    def _selected_point_changed(self, _index: int) -> None:
        self._sync_controls()
        self._draw()
        self.frequencySelected.emit(self.selected_frequency_hz())

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
        self._mark_custom()
        self._sync_controls()
        self._draw()
        self.curveChanged.emit()

    def _press(self, event: object) -> None:
        if getattr(event, "inaxes", None) is None or getattr(event, "button", None) != 1:
            return
        x = getattr(event, "xdata", None)
        if x is None or x <= 0:
            return
        index = int(
            np.argmin(np.abs(np.log10(self._frequencies)-np.log10(float(x))))
        )
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
        self._mark_custom()
        self.curveChanged.emit()

    def _set_drag_value(self, y: object) -> None:
        if y is None or self._drag_index is None:
            return
        self._levels[self._drag_index] = float(np.clip(float(y), -12.0, 12.0))
        self._mark_custom()
        self._sync_controls()
        self._draw()

    def _draw(self) -> None:
        t = theme(self.mode)
        with matplotlib.rc_context(chart_rc(self.mode)):
            self.figure.clear()
            self.figure.set_facecolor(t["surface"])
            ax = self.figure.add_subplot(1, 1, 1)
            ax.set_xscale("log")
            ax.set_xlim(20, 20000)
            ax.set_ylim(-15, 15)
            ax.set_xlabel("Frequenz [Hz]")
            ax.set_ylabel("relativer Zielpegel [dB]")
            ax.set_title("Fullrange-Zielkurve")
            ax.axhline(0.0, color=t["borderStrong"], linewidth=1.0, linestyle=":")

            for curve_index, (candidate_f, candidate_db) in enumerate(self._candidate_curves):
                ax.semilogx(
                    candidate_f,
                    candidate_db,
                    linewidth=1.0,
                    alpha=0.38,
                    color=t["borderStrong"],
                    label="berechnete Alternativen" if curve_index == 0 else None,
                    zorder=-0.5,
                )

            if (
                self._envelope_frequencies is not None
                and self._envelope_low is not None
                and self._envelope_high is not None
            ):
                ax.fill_between(
                    self._envelope_frequencies,
                    self._envelope_low,
                    self._envelope_high,
                    color=t["band"],
                    alpha=0.65,
                    label="berechnete Variantenhülle",
                    zorder=-1,
                )

            ax.semilogx(
                self._frequencies, self._levels, linewidth=2.4, marker="o",
                markersize=5, label="Zielkurve", color=t["accent"],
            )
            selected = max(0, self.point.currentIndex())
            ax.scatter(
                [self._frequencies[selected]], [self._levels[selected]],
                s=70, facecolors=t["surface"], edgecolors=t["accent"],
                linewidths=2.0, zorder=5,
            )

            known_max = 0.0
            if self._actual_frequencies is not None and self._actual_frequencies.size:
                known_max = float(np.max(self._actual_frequencies))
                ax.semilogx(
                    self._actual_frequencies, self._actual_levels, linewidth=1.8,
                    label=self._actual_label, color=t["textSecondary"],
                )
            elif self._envelope_frequencies is not None and self._envelope_frequencies.size:
                known_max = float(np.max(self._envelope_frequencies))

            if known_max and known_max < 19900:
                ax.axvspan(
                    max(known_max, 20), 20000, color=t["band"], alpha=0.34, zorder=-3
                )
                ax.text(
                    min(max(known_max*1.25, 650), 15000), -13.2,
                    "keine belastbaren Fullrange-Daten",
                    color=t["textSecondary"], fontsize=9, ha="left",
                )
            elif not known_max:
                ax.text(
                    .5, .08, "Noch kein Ist-Frequenzgang geladen/berechnet",
                    transform=ax.transAxes, color=t["textSecondary"],
                    ha="center", fontsize=9,
                )
            ax.legend(loc="upper right")
            ax.grid(True, which="both", alpha=.65)
        self.canvas.draw_idle()
