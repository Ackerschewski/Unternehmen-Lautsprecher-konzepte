"""Reduced motion layer: short, non-blocking transitions that can be switched off.

State changes are authoritative; an animation only visualises them. With reduced motion every
transition completes immediately. Durations follow docs/DESIGN_SYSTEM.md (motion table of the
2026-10-06 UI review): hover 120-160 ms, tab/variant crossfade 120-220 ms, collapsible panels 180-220 ms,
splitter 220-280 ms, result reveal 180-240 ms.
"""
from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QEasingCurve, QObject, QVariantAnimation
from PySide6.QtWidgets import QGraphicsOpacityEffect, QWidget

DURATION_PANEL_MS = 240      # splitter / input panel
DURATION_FADE_MS = 160       # tab and variant crossfade (allowed 120-220)
DURATION_REVEAL_MS = 200     # collapsible sections (180-220)
DURATION_RESULT_MS = 220     # new result appears (180-240)
DURATION_ZOOM_MS = 170       # fit / zoom button (140-200)


def animate_value(owner: QObject, start: int, end: int, apply: Callable[[int], None], *,
                  reduced: bool, duration_ms: int = DURATION_PANEL_MS,
                  finished: Callable[[], None] | None = None) -> QVariantAnimation | None:
    """Run apply(value) from start to end; with reduced motion apply(end) at once."""
    previous = getattr(owner, "_motion", None)
    if isinstance(previous, QVariantAnimation):
        previous.stop()  # a newer request wins, no competing animations
    if reduced or start == end:
        apply(end)
        if finished:
            finished()
        return None
    animation = QVariantAnimation(owner)
    animation.setStartValue(start)
    animation.setEndValue(end)
    animation.setDuration(duration_ms)
    animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    animation.valueChanged.connect(lambda value: apply(int(value)))
    if finished:
        animation.finished.connect(finished)
    owner._motion = animation  # type: ignore[attr-defined]
    animation.start()
    return animation


def fade_in(widget: QWidget, *, reduced: bool, duration_ms: int = DURATION_FADE_MS) -> None:
    """Crossfade a freshly shown widget from transparent to opaque; never blocks, newest request wins.

    The opacity effect exists only during the transition (graphics effects slow down large drawings)."""
    previous = getattr(widget, "_fade", None)
    if isinstance(previous, QVariantAnimation):
        previous.stop()
    if reduced or not widget.isVisible():
        widget.setGraphicsEffect(None)
        return
    effect = QGraphicsOpacityEffect(widget)
    effect.setOpacity(0.0)
    widget.setGraphicsEffect(effect)
    animation = QVariantAnimation(widget)
    animation.setStartValue(0.0)
    animation.setEndValue(1.0)
    animation.setDuration(duration_ms)
    animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    animation.valueChanged.connect(lambda value: effect.setOpacity(float(value)))

    def done() -> None:
        try:
            if widget.graphicsEffect() is effect:
                widget.setGraphicsEffect(None)
        except RuntimeError:  # effect already replaced and deleted by a newer transition
            pass

    animation.finished.connect(done)
    widget._fade = animation  # type: ignore[attr-defined]
    animation.start()
