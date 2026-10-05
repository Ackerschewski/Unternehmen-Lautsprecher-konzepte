"""Undo/redo over immutable snapshots, without any Qt dependency.

Each entry is a complete state (here: the tuple of front elements). Edits that arrive
quickly after one another with the same merge key, for example typing digits into a
spin box, replace the newest entry instead of adding one.
"""
from __future__ import annotations

import time
from collections.abc import Callable


class History[T]:
    def __init__(self, initial: T, limit: int = 100, merge_window_s: float = 0.8,
                 clock: Callable[[], float] = time.monotonic) -> None:
        if limit < 2:
            raise ValueError("limit must be at least 2")
        self._states: list[T] = [initial]
        self._index = 0
        self._limit = limit
        self._window = merge_window_s
        self._clock = clock
        self._last_key: object | None = None
        self._last_time = 0.0

    @property
    def current(self) -> T:
        return self._states[self._index]

    @property
    def can_undo(self) -> bool:
        return self._index > 0

    @property
    def can_redo(self) -> bool:
        return self._index < len(self._states) - 1

    def reset(self, state: T) -> None:
        self._states = [state]
        self._index = 0
        self._last_key = None

    def push(self, state: T, merge_key: object | None = None) -> bool:
        """Record a new state; returns False if it equals the current one."""
        if state == self.current:
            return False
        now = self._clock()
        merge = (merge_key is not None and merge_key == self._last_key
                 and now - self._last_time <= self._window and self._index > 0)
        del self._states[self._index + 1:]
        if merge:
            self._states[self._index] = state
        else:
            self._states.append(state)
            self._index += 1
            if len(self._states) > self._limit:
                del self._states[0]
                self._index -= 1
        self._last_key, self._last_time = merge_key, now
        return True

    def undo(self) -> T | None:
        if not self.can_undo:
            return None
        self._index -= 1
        self._last_key = None
        return self.current

    def redo(self) -> T | None:
        if not self.can_redo:
            return None
        self._index += 1
        self._last_key = None
        return self.current
