"""Editable target-curve state with undo/redo: smooth base curve (control points) plus parametric EQ bands.

UI independent. Control points sit at fixed frequencies (their levels are editable); EQ bands are free.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace

import numpy as np
from numpy.typing import NDArray

from lautsprecher_konstruktion.targets.eq import (
    FREQ_MAX_HZ,
    FREQ_MIN_HZ,
    GAIN_LIMIT_DB,
    EQBand,
    FilterType,
)
from lautsprecher_konstruktion.targets.smooth import target_level_db

Float = NDArray[np.float64]
LEVEL_LIMIT_DB = 12.0
HISTORY_LIMIT = 80
NODE_FREQUENCIES: tuple[float, ...] = (20.0, 31.5, 50.0, 80.0, 125.0, 250.0, 500.0, 1000.0, 2000.0,
                                       4000.0, 8000.0, 16000.0, 20000.0)
PRESET_LEVELS: dict[str, tuple[str, tuple[float, ...]]] = {
    "neutral": ("Neutral", (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)),
    "warm": ("Warm", (3.5, 3.0, 2.4, 1.6, 0.8, 0.3, 0, 0, -0.2, -0.6, -1.0, -1.5, -1.7)),
    "house": ("House Curve", (5.0, 4.4, 3.5, 2.5, 1.7, 0.8, 0.2, 0, -0.4, -0.8, -1.3, -1.8, -2.0)),
    "nearfield": ("Nahfeld", (1.5, 1.2, 0.8, 0.4, 0.1, 0, 0, 0, 0, -0.3, -0.7, -1.0, -1.2)),
}


@dataclass(frozen=True)
class TargetState:
    levels: tuple[float, ...]
    bands: tuple[EQBand, ...] = ()


class TargetModel:
    def __init__(self) -> None:
        self.state = TargetState((0.0,) * len(NODE_FREQUENCIES))
        self._undo: list[TargetState] = []
        self._redo: list[TargetState] = []
        self._counter = 0

    # --- read ----------------------------------------------------------------------------------------
    @property
    def frequencies(self) -> Float:
        return np.asarray(NODE_FREQUENCIES, dtype=float)

    def points(self) -> tuple[tuple[float, float], ...]:
        return tuple(zip(NODE_FREQUENCIES, self.state.levels, strict=True))

    @property
    def bands(self) -> tuple[EQBand, ...]:
        return self.state.bands

    def band(self, band_id: str) -> EQBand:
        return next(b for b in self.state.bands if b.id == band_id)

    def curve(self, frequencies_hz: Float) -> Float:
        return target_level_db(self.points(), self.state.bands, frequencies_hz)

    def effective_points(self) -> tuple[tuple[float, float], ...]:
        """Target level at the control-point frequencies including the EQ bands."""
        values = self.curve(self.frequencies)
        return tuple((float(f), float(v)) for f, v in zip(self.frequencies, values, strict=True))

    @property
    def is_neutral(self) -> bool:
        return not any(abs(v) > 1e-9 for v in self.state.levels) and not self.state.bands

    # --- history -------------------------------------------------------------------------------------
    def checkpoint(self) -> None:
        """Remember the current state before a change (drags call this once at the start)."""
        self._undo.append(self.state)
        del self._undo[:-HISTORY_LIMIT]
        self._redo.clear()

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    def undo(self) -> bool:
        if not self._undo:
            return False
        self._redo.append(self.state)
        self.state = self._undo.pop()
        return True

    def redo(self) -> bool:
        if not self._redo:
            return False
        self._undo.append(self.state)
        self.state = self._redo.pop()
        return True

    # --- edits (callers decide whether to checkpoint; the helpers below do it for discrete edits) -----
    def set_level(self, index: int, level_db: float) -> None:
        levels = list(self.state.levels)
        levels[index] = float(np.clip(level_db, -LEVEL_LIMIT_DB, LEVEL_LIMIT_DB))
        self.state = replace(self.state, levels=tuple(levels))

    def set_levels(self, levels: Iterable[float]) -> None:
        values = tuple(float(np.clip(v, -LEVEL_LIMIT_DB, LEVEL_LIMIT_DB)) for v in levels)
        if len(values) != len(NODE_FREQUENCIES):
            raise ValueError("one level per control point required")
        self.state = replace(self.state, levels=values)

    def set_from_points(self, points: Iterable[tuple[float, float]]) -> None:
        """Resample arbitrary stored points onto the fixed control frequencies."""
        data = np.asarray(sorted(points), dtype=float)
        if data.size == 0:
            self.set_levels((0.0,) * len(NODE_FREQUENCIES))
            return
        if data.ndim != 2 or data.shape[1] != 2 or np.any(data[:, 0] <= 0):
            raise ValueError("target curve points must be (frequency_hz, level_db)")
        self.set_levels(np.interp(np.log10(self.frequencies), np.log10(data[:, 0]), data[:, 1]))

    def new_band_id(self) -> str:
        used = {b.id for b in self.state.bands}
        while True:
            self._counter += 1
            if f"band-{self._counter}" not in used:
                return f"band-{self._counter}"

    def add_band(self, band: EQBand | None = None, *, record: bool = True) -> EQBand:
        if record:
            self.checkpoint()
        new = band or EQBand(filter_type=FilterType.BELL, frequency_hz=1000.0, gain_db=0.0, q=1.0)
        if not new.id or new.id == "band" or new.id in {b.id for b in self.state.bands}:
            new = new.model_copy(update={"id": self.new_band_id()})
        self.state = replace(self.state, bands=(*self.state.bands, new))
        return new

    def update_band(self, band_id: str, **fields: object) -> EQBand:
        bands = list(self.state.bands)
        for index, band in enumerate(bands):
            if band.id == band_id:
                bands[index] = EQBand.model_validate({**band.model_dump(), **fields})
                self.state = replace(self.state, bands=tuple(bands))
                return bands[index]
        raise KeyError(band_id)

    def remove_band(self, band_id: str, *, record: bool = True) -> None:
        if record:
            self.checkpoint()
        self.state = replace(self.state, bands=tuple(b for b in self.state.bands if b.id != band_id))

    def move_band(self, band_id: str, frequency_hz: float, gain_delta_db: float = 0.0) -> EQBand:
        band = self.band(band_id)
        fields: dict[str, object] = {"frequency_hz": float(np.clip(frequency_hz, FREQ_MIN_HZ, FREQ_MAX_HZ))}
        if band.uses_gain:
            fields["gain_db"] = float(np.clip(band.gain_db + gain_delta_db, -GAIN_LIMIT_DB, GAIN_LIMIT_DB))
        return self.update_band(band_id, **fields)

    def reset(self) -> None:
        self.checkpoint()
        self.state = TargetState((0.0,) * len(NODE_FREQUENCIES))

    def apply_preset(self, key: str) -> None:
        self.checkpoint()
        self.state = TargetState(tuple(float(v) for v in PRESET_LEVELS[key][1]), ())

    def load(self, levels: Iterable[float], bands: Iterable[EQBand]) -> None:
        """Replace the state without history (project load)."""
        self.state = TargetState(tuple(float(v) for v in levels), tuple(bands))
        self._undo.clear()
        self._redo.clear()
