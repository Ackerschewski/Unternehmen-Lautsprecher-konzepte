"""Resizable, zoomable SVG sheet with a real fit-to-window action."""
from __future__ import annotations

from PySide6.QtCore import QByteArray, QEvent, Qt, Signal
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class ZoomableSvgView(QWidget):
    fullscreenToggled = Signal(bool)

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
        self._reading = False
        bar = QHBoxLayout()
        # one clear set of controls: fit, 100 %, minus, plus, editable percentage, full screen
        fit_button = QPushButton("Einpassen")
        fit_button.clicked.connect(self.fit)
        bar.addWidget(fit_button)
        for label, callback in (("100 %", self.actual_size), ("−", lambda: self.zoom(1 / 1.25)),
                                ("+", lambda: self.zoom(1.25))):
            button = QPushButton(label)
            button.clicked.connect(callback)
            bar.addWidget(button)
        self.zoom_percent = QSpinBox()
        self.zoom_percent.setRange(10, 500)
        self.zoom_percent.setSuffix(" %")
        self.zoom_percent.setKeyboardTracking(False)
        self.zoom_percent.setToolTip("Zoom als Prozentwert eingeben")
        self.zoom_percent.valueChanged.connect(self._percent_entered)
        bar.addWidget(self.zoom_percent)
        self.zoom_label = QLabel("Einpassen")
        self.zoom_label.setObjectName("hint")
        bar.addWidget(self.zoom_label)
        bar.addStretch()
        self.fullscreen_button = QPushButton("Vollbild")
        self.fullscreen_button.setCheckable(True)
        self.fullscreen_button.setToolTip("Fenster im Vollbild anzeigen (Esc oder erneut klicken beendet es)")
        self.fullscreen_button.toggled.connect(self.fullscreenToggled)
        bar.addWidget(self.fullscreen_button)
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
        self.fit_width() if self._reading else self.fit()

    def set_reading(self, reading: bool) -> None:
        """Reading mode: sheets open at page width so labels have their natural on-screen size."""
        self._reading = reading
        self.fit_width() if reading else self.fit()

    def _percent_entered(self, value: int) -> None:
        self._fit = False
        self._reading = False
        self._scale = value / 100
        self._apply_scale()
        self.zoom_label.setText("Eigener Wert")

    def _show_percent(self) -> None:
        self.zoom_percent.blockSignals(True)
        self.zoom_percent.setValue(round(self._scale * 100))
        self.zoom_percent.blockSignals(False)

    def fit(self) -> None:
        self._fit = True
        width, height = self._native
        view = self.scroll.viewport().size()
        self._scale = max(0.05, min((view.width()-10)/width,
                                     (view.height()-10)/height))
        self._apply_scale()
        self.zoom_label.setText("Einpassen")
        self._show_percent()

    def fit_width(self) -> None:
        self._fit = False
        self._reading = True
        self._scale = max(0.05, (self.scroll.viewport().width() - 20) / self._native[0])
        self._apply_scale()
        self.zoom_label.setText("Seitenbreite")
        self._show_percent()

    def actual_size(self) -> None:
        self._fit = False
        self._reading = False
        self._scale = 1.0
        self._apply_scale()
        self.zoom_label.setText("Originalgröße")
        self._show_percent()

    def zoom(self, factor: float) -> None:
        self._fit = False
        self._reading = False
        self._scale = min(5.0, max(0.1, self._scale*factor))
        self._apply_scale()
        self.zoom_label.setText("Eigener Wert")
        self._show_percent()

    def _apply_scale(self) -> None:
        width, height = self._native
        self.sheet.setFixedSize(round(width*self._scale), round(height*self._scale))

    def eventFilter(self, watched: object, event: QEvent) -> bool:
        if watched is self.scroll.viewport() and event.type() == QEvent.Type.Resize:
            if self._reading:
                self.fit_width()
            elif self._fit:
                self.fit()
        if (watched is self.scroll.viewport() and event.type() == QEvent.Type.Wheel
                and event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self.zoom(1.15 if event.angleDelta().y() > 0 else 1 / 1.15)  # Ctrl + wheel zooms immediately
            return True
        return super().eventFilter(watched, event)
