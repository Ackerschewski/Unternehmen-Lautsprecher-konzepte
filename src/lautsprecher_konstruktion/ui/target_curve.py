"""Interactive full-range target curve: smooth base curve plus real parametric EQ bands.

The target curve is a design objective, not a measured response. Actual curves and feasibility envelopes
are drawn only from data/calculations that exist in the current project; unknown full-range regions remain
explicitly unknown. Control points are connected by a shape-preserving PCHIP curve; filter bands use real
biquad responses (targets.eq).
"""
from __future__ import annotations

import time
from collections.abc import Iterable

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

from lautsprecher_konstruktion.targets.eq import EQBand, FilterType
from lautsprecher_konstruktion.targets.smooth import render_frequencies, smooth_curve_db
from lautsprecher_konstruktion.targets.state import (
    LEVEL_LIMIT_DB,
    NODE_FREQUENCIES,
    PRESET_LEVELS,
    TargetModel,
)
from lautsprecher_konstruktion.ui.eq_inspector import BandInspector
from lautsprecher_konstruktion.ui.theme import chart_rc
from lautsprecher_konstruktion.ui.tokens import theme

DEFAULT_FREQUENCIES = np.asarray(NODE_FREQUENCIES, dtype=float)
PRESETS = PRESET_LEVELS
PICK_RADIUS_PX = 14
DRAG_REDRAW_S = 0.025  # live preview while dragging; the solver is only told when the drag ends

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
        self.model = TargetModel()
        self._frequencies = DEFAULT_FREQUENCIES.copy()
        self._grid = render_frequencies()
        self._actual_frequencies: np.ndarray | None = None
        self._actual_levels: np.ndarray | None = None
        self._actual_label = "Ist · berechenbarer Bereich"
        self._envelope_frequencies: np.ndarray | None = None
        self._envelope_low: np.ndarray | None = None
        self._envelope_high: np.ndarray | None = None
        self._candidate_curves: list[tuple[np.ndarray, np.ndarray]] = []
        self._drag: tuple[str, int | str] | None = None
        self._drag_y = 0.0
        self._last_draw = 0.0
        self._syncing = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        heading = QHBoxLayout()
        title = QLabel("Zielkurve · Sollwert")
        title.setObjectName("section")
        title.setToolTip(
            "Sollwert für den Entwurf · 20 Hz–20 kHz. Stützpunkte ziehen, Filterbänder per Doppelklick "
            "anlegen und ziehen. Unbelegte Frequenzbereiche werden nicht erfunden."
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
        self.undo_button = QPushButton("Rückgängig")
        self.undo_button.clicked.connect(self.undo)
        heading.addWidget(self.undo_button)
        self.redo_button = QPushButton("Wiederholen")
        self.redo_button.clicked.connect(self.redo)
        heading.addWidget(self.redo_button)
        layout.addLayout(heading)

        self.figure = Figure(figsize=(10, 5), layout="constrained")
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setMinimumHeight(300)
        layout.addWidget(self.canvas, 1)

        base = QHBoxLayout()
        base.addWidget(QLabel("Basiskurve · Stützpunkt"))
        self.point = QComboBox()
        for value in self._frequencies:
            label = f"{value/1000:g} kHz" if value >= 1000 else f"{value:g} Hz"
            self.point.addItem(label)
        self.point.currentIndexChanged.connect(self._selected_point_changed)
        base.addWidget(self.point)
        base.addWidget(QLabel("Ziel"))
        self.level = QDoubleSpinBox()
        self.level.setRange(-LEVEL_LIMIT_DB, LEVEL_LIMIT_DB)
        self.level.setSingleStep(0.5)
        self.level.setDecimals(1)
        self.level.setSuffix(" dB")
        self.level.valueChanged.connect(self._numeric_level_changed)
        base.addWidget(self.level)
        self.readout = QLabel()
        self.readout.setObjectName("caption")
        base.addWidget(self.readout)
        base.addStretch(1)
        layout.addLayout(base)

        self.inspector = BandInspector()
        self.inspector.addRequested.connect(self.add_band)
        self.inspector.removeRequested.connect(self.remove_band)
        self.inspector.selected.connect(self._band_selected)
        self.inspector.fieldEdited.connect(self._band_field_edited)
        layout.addWidget(self.inspector)

        self.influence = QLabel(MODE_TEXT["overall"])
        self.influence.setObjectName("recommendation")
        self.influence.setWordWrap(True)
        layout.addWidget(self.influence)

        influence_grid = QGridLayout()
        influence_grid.setContentsMargins(0, 0, 0, 0)
        influence_grid.setHorizontalSpacing(8)
        self.influence_cards: dict[str, QLabel] = {}
        for column, (key, name) in enumerate((
            ("enclosure", "Gehäuse"), ("driver", "Chassis"), ("crossover", "Weiche"), ("dsp", "DSP"),
        )):
            card = QLabel(f"<b>{name}</b><br>noch keine Vergleichsdaten")
            card.setObjectName("kpi")
            card.setWordWrap(True)
            influence_grid.addWidget(card, 0, column)
            influence_grid.setColumnStretch(column, 1)
            self.influence_cards[key] = card
        layout.addLayout(influence_grid)

        self.canvas.mpl_connect("button_press_event", self._press)
        self.canvas.mpl_connect("motion_notify_event", self._motion)
        self.canvas.mpl_connect("button_release_event", self._release)
        self._active_band: str | None = None
        self._refresh()

    # --- data access (used by the assistant and the project file) ------------------------------------------
    @property
    def _levels(self) -> np.ndarray:
        return np.asarray(self.model.state.levels, dtype=float)

    def points(self) -> tuple[tuple[float, float], ...]:
        return self.model.points()

    def effective_points(self) -> tuple[tuple[float, float], ...]:
        """Target level at the control frequencies including EQ bands (what the design is compared with)."""
        return self.model.effective_points()

    def bands(self) -> tuple[EQBand, ...]:
        return self.model.bands

    def set_points(self, points: Iterable[tuple[float, float]]) -> None:
        self.model.set_from_points(points)
        self._set_preset_combo("custom")
        self._refresh()

    def set_bands(self, bands: Iterable[EQBand]) -> None:
        self.model.load(self.model.state.levels, tuple(bands))
        self._active_band = None
        self._refresh()

    def preset_id(self) -> str:
        return str(self.preset.currentData())

    def restore_state(
        self,
        points: Iterable[tuple[float, float]],
        *,
        preset: str = "custom",
        analysis_mode: str = "overall",
        bands: Iterable[EQBand] = (),
    ) -> None:
        data = tuple(points)
        self.model.load((0.0,) * len(NODE_FREQUENCIES), tuple(bands))
        if data:
            self.model.set_from_points(data)
        self._active_band = None
        if self.preset.findData(preset) >= 0:
            self._set_preset_combo(preset)
        self.set_analysis_mode(analysis_mode)
        self._refresh()

    def selected_frequency_hz(self) -> float:
        index = max(0, self.point.currentIndex())
        return float(self._frequencies[index])

    def set_component_influence(self, values: dict[str, str]) -> None:
        titles = {"enclosure": "Gehäuse", "driver": "Chassis", "crossover": "Weiche", "dsp": "DSP"}
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

    # --- overlays: actual curve and feasibility envelope ----------------------------------------------------
    @staticmethod
    def _normalise(frequencies: np.ndarray, values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        valid = np.isfinite(frequencies) & np.isfinite(values) & (frequencies > 0)
        f = frequencies[valid]
        v = values[valid].astype(float, copy=True)
        if f.size == 0:
            return f, v
        reference = (f >= 80.0) & (f <= 120.0)
        v -= float(np.median(v[reference])) if np.any(reference) else float(np.median(v))
        return f, v

    def set_actual_curve(self, frequencies_hz: Iterable[float], response_db: Iterable[float], *,
                         label: str = "Ist · berechenbarer Bereich") -> None:
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
        for target_f, target_db in self.effective_points():
            if target_f < f[0] or target_f > f[-1]:
                continue
            lo = float(np.interp(np.log10(target_f), np.log10(f), low))
            hi = float(np.interp(np.log10(target_f), np.log10(f), high))
            distance = lo-target_db if target_db < lo else target_db-hi if target_db > hi else 0.0
            if distance > 0 and (worst is None or distance > worst[1]):
                worst = (target_f, distance)
        return worst

    # --- editing --------------------------------------------------------------------------------------------
    def _refresh(self) -> None:
        self._sync_controls()
        self.inspector.set_bands(self.model.bands, self._active_band)
        self._active_band = self.inspector.active_id
        self.undo_button.setEnabled(self.model.can_undo)
        self.redo_button.setEnabled(self.model.can_redo)
        self._draw()

    def _changed(self) -> None:
        self._set_preset_combo("custom")
        self._refresh()
        self.curveChanged.emit()

    def reset(self) -> None:
        self.model.reset()
        self._active_band = None
        self._set_preset_combo("neutral")
        self._refresh()
        self.curveChanged.emit()

    def undo(self) -> None:
        if self.model.undo():
            self._set_preset_combo("custom")
            self._refresh()
            self.curveChanged.emit()

    def redo(self) -> None:
        if self.model.redo():
            self._set_preset_combo("custom")
            self._refresh()
            self.curveChanged.emit()

    def add_band(self, band: EQBand | None = None) -> None:
        new = self.model.add_band(band if isinstance(band, EQBand) else None)
        self._active_band = new.id
        self._changed()

    def remove_band(self, band_id: str) -> None:
        self.model.remove_band(band_id)
        self._active_band = None
        self._changed()

    def apply_parametric_band(self) -> None:
        """Compatibility: adds a bell band (a real filter, not a baked bump)."""
        self.add_band(EQBand(filter_type=FilterType.BELL, frequency_hz=1000.0, gain_db=2.0, q=1.0))

    def _band_selected(self, band_id: str) -> None:
        self._active_band = band_id
        self.inspector.set_bands(self.model.bands, band_id)
        self._draw()

    def _band_field_edited(self, band_id: str, name: str, value: object) -> None:
        self.model.checkpoint()
        self.model.update_band(band_id, **{name: value})
        self._changed()

    def _set_preset_combo(self, key: str) -> None:
        self._syncing = True
        index = self.preset.findData(key)
        if index >= 0:
            self.preset.setCurrentIndex(index)
        self._syncing = False

    def _preset_changed(self, _index: int) -> None:
        if self._syncing:
            return
        key = str(self.preset.currentData())
        if key == "custom":
            return
        self.model.apply_preset(key)
        self._active_band = None
        self._refresh()
        self.curveChanged.emit()

    def _analysis_changed(self, _index: int) -> None:
        if self._syncing:
            return
        self.set_influence_summary()
        self.analysisModeChanged.emit(self.analysis_mode())

    def _selected_point_changed(self, _index: int) -> None:
        self._sync_controls()
        self._draw()
        self.frequencySelected.emit(self.selected_frequency_hz())

    def _sync_controls(self) -> None:
        index = max(0, self.point.currentIndex())
        level = self.model.state.levels[index]
        self._syncing = True
        self.level.setValue(float(level))
        f = self._frequencies[index]
        self.readout.setText(f"{f/1000:g} kHz · {level:+.1f} dB" if f >= 1000 else f"{f:g} Hz · {level:+.1f} dB")
        self._syncing = False

    def _numeric_level_changed(self, value: float) -> None:
        if self._syncing:
            return
        index = max(0, self.point.currentIndex())
        if abs(self.model.state.levels[index] - value) < 1e-9:
            return
        self.model.checkpoint()
        self.model.set_level(index, value)
        self._changed()

    # --- mouse: drag base points and bands; double-click adds a band; right click removes -----------------
    def _marker_pixels(self) -> list[tuple[str, int | str, float, float]]:
        ax = self.figure.axes[0] if self.figure.axes else None
        if ax is None:
            return []
        markers: list[tuple[str, int | str, float, float]] = []
        base = smooth_curve_db(self.model.points(), self._frequencies)
        for index, (f, v) in enumerate(zip(self._frequencies, base, strict=True)):
            px, py = ax.transData.transform((f, v))
            markers.append(("node", index, float(px), float(py)))
        for band in self.model.bands:
            level = float(self.model.curve(np.asarray([band.frequency_hz]))[0])
            px, py = ax.transData.transform((band.frequency_hz, level))
            markers.append(("band", band.id, float(px), float(py)))
        return markers

    def _nearest(self, event: object) -> tuple[str, int | str] | None:
        ex, ey = getattr(event, "x", None), getattr(event, "y", None)
        if ex is None or ey is None:
            return None
        best: tuple[str, int | str] | None = None
        best_d = float(PICK_RADIUS_PX) + 1e-6
        for kind, ident, px, py in reversed(self._marker_pixels()):  # bands are drawn on top of nodes
            d = float(np.hypot(px - ex, py - ey))
            if d < best_d:  # strict: on equal distance the band (checked first) wins over a control point
                best, best_d = (kind, ident), d
        return best

    def _press(self, event: object) -> None:
        if getattr(event, "inaxes", None) is None:
            return
        x, y = getattr(event, "xdata", None), getattr(event, "ydata", None)
        if x is None or y is None or x <= 0:
            return
        hit = self._nearest(event)
        button = getattr(event, "button", None)
        if button == 3:
            if hit is not None and hit[0] == "band":
                self.remove_band(str(hit[1]))
            return
        if button != 1:
            return
        if getattr(event, "dblclick", False) and hit is None:
            base = float(self.model.curve(np.asarray([float(x)]))[0])
            self.add_band(EQBand(filter_type=FilterType.BELL, frequency_hz=float(np.clip(x, 20, 20000)),
                                 gain_db=float(np.clip(y - base, -12, 12)), q=1.0))
            return
        if hit is None:
            return
        self.model.checkpoint()  # one history entry per drag
        self._drag = hit
        self._drag_y = float(y)
        if hit[0] == "node":
            self.point.setCurrentIndex(int(hit[1]))
        else:
            self._active_band = str(hit[1])
            self.inspector.set_bands(self.model.bands, self._active_band)

    def _motion(self, event: object) -> None:
        if self._drag is None or getattr(event, "inaxes", None) is None:
            return
        x, y = getattr(event, "xdata", None), getattr(event, "ydata", None)
        if x is None or y is None:
            return
        self._apply_drag(float(x), float(y))
        now = time.monotonic()
        if now - self._last_draw >= DRAG_REDRAW_S:
            self._last_draw = now
            self._draw()

    def _apply_drag(self, x: float, y: float) -> None:
        assert self._drag is not None
        kind, ident = self._drag
        if kind == "node":
            self.model.set_level(int(ident), float(np.clip(y, -LEVEL_LIMIT_DB, LEVEL_LIMIT_DB)))  # markers sit on the base curve
        else:
            self.model.move_band(str(ident), x, gain_delta_db=y - self._drag_y)
            self._drag_y = y

    def _release(self, event: object) -> None:
        if self._drag is None:
            return
        x, y = getattr(event, "xdata", None), getattr(event, "ydata", None)
        if x is not None and y is not None and x > 0:
            self._apply_drag(float(x), float(y))  # the last pointer position wins over throttled previews
        self._drag = None
        self._changed()

    # --- drawing --------------------------------------------------------------------------------------------
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
                ax.semilogx(candidate_f, candidate_db, linewidth=1.0, alpha=0.38, color=t["borderStrong"],
                            label="berechnete Alternativen" if curve_index == 0 else None, zorder=-0.5)
            if (self._envelope_frequencies is not None and self._envelope_low is not None
                    and self._envelope_high is not None):
                ax.fill_between(self._envelope_frequencies, self._envelope_low, self._envelope_high,
                                color=t["band"], alpha=0.65, label="berechnete Variantenhülle", zorder=-1)

            target = self.model.curve(self._grid)
            base = smooth_curve_db(self.model.points(), self._grid)
            if self.model.bands:
                ax.semilogx(self._grid, base, linewidth=1.2, linestyle="--", color=t["accent"], alpha=0.55,
                            label="Basiskurve")
            ax.semilogx(self._grid, np.clip(target, -30, 30), linewidth=2.4, color=t["accent"], label="Zielkurve")
            ax.plot(self._frequencies, smooth_curve_db(self.model.points(), self._frequencies), "o",
                    markersize=4.5, color=t["accent"], zorder=4)
            selected = max(0, self.point.currentIndex())
            sel_f = self._frequencies[selected]
            ax.scatter([sel_f], smooth_curve_db(self.model.points(), np.asarray([sel_f])), s=60,
                       facecolors=t["surface"], edgecolors=t["accent"], linewidths=2.0, zorder=5)
            for band in self.model.bands:
                level = float(self.model.curve(np.asarray([band.frequency_hz]))[0])
                active = band.id == self._active_band
                ax.scatter([band.frequency_hz], [np.clip(level, -14.5, 14.5)], s=150 if active else 80, zorder=6,
                           facecolors=t["accent"] if band.enabled else t["surface"],
                           edgecolors=t["textPrimary"], linewidths=2.2 if active else 1.2)

            known_max = 0.0
            if self._actual_frequencies is not None and self._actual_frequencies.size:
                known_max = float(np.max(self._actual_frequencies))
                ax.semilogx(self._actual_frequencies, self._actual_levels, linewidth=1.8,
                            label=self._actual_label, color=t["textSecondary"])
            elif self._envelope_frequencies is not None and self._envelope_frequencies.size:
                known_max = float(np.max(self._envelope_frequencies))

            if known_max and known_max < 19900:
                ax.axvspan(max(known_max, 20), 20000, color=t["band"], alpha=0.34, zorder=-3)
                ax.text(min(max(known_max*1.25, 650), 15000), -13.2, "keine belastbaren Fullrange-Daten",
                        color=t["textSecondary"], fontsize=9, ha="left")
            elif not known_max:
                ax.text(.5, .08, "Noch kein Ist-Frequenzgang geladen/berechnet", transform=ax.transAxes,
                        color=t["textSecondary"], ha="center", fontsize=9)
            ax.legend(loc="upper right")
            ax.grid(True, which="both", alpha=.65)
        self.canvas.draw_idle()
