"""Resizable, zoomable SVG sheet with a real fit-to-window action."""
from __future__ import annotations

from PySide6.QtCore import QByteArray, QEvent, Qt
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget


class ZoomableSvgView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.sheet = QSvgWidget()
        self.sheet.setMinimumSize(1, 1)
        self.scroll = QScrollArea()
        self.scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll.setWidget(self.sheet)
        self.scroll.viewport().installEventFilter(self)
        self._native = (1200, 1100)
        self._scale = 1.0
        self._fit = True
        bar = QHBoxLayout()
        for label, callback in (("−", lambda: self.zoom(1 / 1.25)),
                                ("+", lambda: self.zoom(1.25)),
                                ("Einpassen", self.fit)):
            button = QPushButton(label)
            button.clicked.connect(callback)
            bar.addWidget(button)
        self.zoom_label = QLabel("Einpassen")
        bar.addWidget(self.zoom_label)
        bar.addStretch()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(bar)
        layout.addWidget(self.scroll, 1)

    def renderer(self):
        return self.sheet.renderer()

    def load(self, data: QByteArray) -> None:
        self.sheet.load(data)
        size = self.sheet.renderer().defaultSize()
        if size.width() > 0 and size.height() > 0:
            self._native = (size.width(), size.height())
        self.fit()

    def fit(self) -> None:
        self._fit = True
        width, height = self._native
        view = self.scroll.viewport().size()
        self._scale = max(0.05, min((view.width()-10)/width,
                                     (view.height()-10)/height))
        self._apply_scale()
        self.zoom_label.setText(f"Einpassen · {self._scale*100:.0f} %")

    def zoom(self, factor: float) -> None:
        self._fit = False
        self._scale = min(5.0, max(0.1, self._scale*factor))
        self._apply_scale()
        self.zoom_label.setText(f"{self._scale*100:.0f} %")

    def _apply_scale(self) -> None:
        width, height = self._native
        self.sheet.setFixedSize(round(width*self._scale), round(height*self._scale))

    def eventFilter(self, watched: object, event: QEvent) -> bool:
        if watched is self.scroll.viewport() and event.type() == QEvent.Type.Resize and self._fit:
            self.fit()
        return super().eventFilter(watched, event)
