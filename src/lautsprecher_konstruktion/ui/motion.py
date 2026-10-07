"""Reduced motion layer: short, non-blocking transitions that can be switched off.

State changes are authoritative; an animation only visualises them. With reduced motion every
transition completes immediately.
"""
from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QEasingCurve, QObject, QVariantAnimation
from PySide6.QtWidgets import QGraphicsOpacityEffect, QWidget

DURATION_PANEL_MS = 240
DURATION_FADE_MS = 160


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


def fade_in(widget: QWidget, *, reduced: bool, duration_ms: int = DURATION_FADE_MS) -> QVariantAnimation | None:
    """Subtle content-arrival transition; disabled completely for reduced motion."""
    previous = getattr(widget, "_fade_motion", None)
    if isinstance(previous, QVariantAnimation):
        previous.stop()
    if reduced or not widget.isVisible():
        widget.setGraphicsEffect(None)
        return None
    effect = QGraphicsOpacityEffect(widget)
    effect.setOpacity(0.35)
    widget.setGraphicsEffect(effect)
    animation = QVariantAnimation(widget)
    animation.setStartValue(0.35)
    animation.setEndValue(1.0)
    animation.setDuration(duration_ms)
    animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    animation.valueChanged.connect(lambda value: effect.setOpacity(float(value)))
    animation.finished.connect(lambda: widget.setGraphicsEffect(None))
    widget._fade_motion = animation  # type: ignore[attr-defined]
    animation.start()
    return animation
