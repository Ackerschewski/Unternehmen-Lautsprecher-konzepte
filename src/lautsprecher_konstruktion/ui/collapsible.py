"""Disclosure section whose content opens and closes smoothly (instantly with reduced motion)."""
from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QToolButton, QVBoxLayout, QWidget

from lautsprecher_konstruktion.ui.motion import animate_value


class Collapsible(QWidget):
    def __init__(self, title: str, content: QWidget, *, reduced_motion: Callable[[], bool] = lambda: False,
                 expanded: bool = False) -> None:
        super().__init__()
        self._title = title
        self._content = content
        self._reduced = reduced_motion
        self._full = 240
        self.button = QToolButton()
        self.button.setObjectName("disclosure")
        self.button.setCheckable(True)
        self.button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.button.toggled.connect(self._toggled)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.button)
        layout.addWidget(content)
        content.setMaximumHeight(0)
        content.setVisible(False)
        self.button.setChecked(expanded)
        if expanded:
            self._toggled(True)
        self._sync_title()

    def is_expanded(self) -> bool:
        return self.button.isChecked()

    def set_full_height(self, height: int) -> None:
        self._full = height

    def _sync_title(self) -> None:
        self.button.setText(("▾ " if self.button.isChecked() else "▸ ") + self._title)

    def _toggled(self, open_: bool) -> None:
        self._sync_title()
        content = self._content
        if open_:
            content.setVisible(True)
        end = self._full if open_ else 0
        start = content.maximumHeight() if content.maximumHeight() < 16_000_000 else self._full

        def apply(value: int) -> None:
            content.setMaximumHeight(value)

        def done() -> None:
            if not open_:
                content.setVisible(False)
            else:
                content.setMaximumHeight(16_777_215)

        animate_value(self, start, end, apply, reduced=self._reduced(), duration_ms=200, finished=done)
