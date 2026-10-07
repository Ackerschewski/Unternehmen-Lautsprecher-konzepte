"""Reusable visual planner widgets for the guided loudspeaker workflow."""
from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QButtonGroup,
    QGridLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from lautsprecher_konstruktion.ui.tokens import UI_FONT, theme


class ChoiceCard(QPushButton):
    """Checkable card whose description wraps instead of being cut off."""

    def __init__(self, title: str, subtitle: str) -> None:
        super().__init__()
        self._title, self._subtitle = title, subtitle
        self.setObjectName("choiceCard")
        self.setCheckable(True)
        self.setAccessibleName(f"{title}. {subtitle}")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(1)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("choiceTitle")
        self.sub_label = QLabel(subtitle)
        self.sub_label.setObjectName("choiceSub")
        self.sub_label.setWordWrap(True)
        for label in (self.title_label, self.sub_label):
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            layout.addWidget(label)
        line = self.sub_label.fontMetrics().lineSpacing()
        self.sub_label.setMinimumHeight(2 * line + 2)  # room for two lines; longer text wraps within them
        self.setMinimumHeight(self.title_label.sizeHint().height() + 2 * line + 24)

    def text(self) -> str:
        return f"{self._title}\n{self._subtitle}"


class ChoiceGrid(QWidget):
    """Large card choices that remain keyboard accessible."""

    valueChanged = Signal(str)

    def __init__(
        self,
        items: Iterable[tuple[str, str, str]],
        *,
        columns: int = 2,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._buttons: dict[str, QPushButton] = {}
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(8)
        for index, (value, title, subtitle) in enumerate(items):
            button = ChoiceCard(title, subtitle)
            button.setProperty("choiceValue", value)
            button.clicked.connect(lambda _checked=False, v=value: self.valueChanged.emit(v))
            self._group.addButton(button)
            self._buttons[value] = button
            layout.addWidget(button, index // columns, index % columns)
        layout.setColumnStretch(0, 1)
        if columns > 1:
            layout.setColumnStretch(1, 1)

    def set_value(self, value: str) -> None:
        button = self._buttons.get(value)
        if button is not None:
            button.setChecked(True)

    def value(self) -> str | None:
        button = self._group.checkedButton()
        return None if button is None else str(button.property("choiceValue"))


class DimensionPreview(QWidget):
    """Small proportional preview while the user edits maximum dimensions."""

    def __init__(self, mode: str = "light", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.mode = mode
        self.width_mm = 300.0
        self.height_mm = 500.0
        self.depth_mm = 400.0
        self.setMinimumHeight(150)

    def sizeHint(self) -> QSize:
        return QSize(300, 170)

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        self.update()

    def set_dimensions(self, width_mm: float, height_mm: float, depth_mm: float) -> None:
        self.width_mm = max(1.0, width_mm)
        self.height_mm = max(1.0, height_mm)
        self.depth_mm = max(1.0, depth_mm)
        self.update()

    def paintEvent(self, _event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = theme(self.mode)
        painter.fillRect(self.rect(), QColor(t["surface"]))
        area = QRectF(16, 14, max(1, self.width()-32), max(1, self.height()-28))
        max_h = max(50.0, area.height()-28)
        max_w = max(50.0, area.width()-70)
        scale = min(max_w/self.width_mm, max_h/self.height_mm)
        fw = self.width_mm*scale
        fh = self.height_mm*scale
        depth = min(46.0, self.depth_mm/max(self.width_mm, 1.0)*fw*0.22)
        dy = depth*0.52
        left = area.left()+(area.width()-fw-depth)/2
        top = area.top()+(max_h-fh)/2
        front = QRectF(left, top, fw, fh)

        painter.setPen(QPen(QColor(t["accent"]), 1.8))
        painter.setBrush(QColor(t["surfaceElevated"]))
        painter.drawRoundedRect(front, 5, 5)
        painter.setPen(QPen(QColor(t["borderStrong"]), 1.2))
        painter.drawLine(front.topRight(), front.topRight() + _point(depth, dy))
        painter.drawLine(front.bottomRight(), front.bottomRight() + _point(depth, dy))
        painter.drawLine(front.topRight() + _point(depth, dy), front.bottomRight() + _point(depth, dy))

        painter.setFont(QFont(UI_FONT, 8))
        painter.setPen(QColor(t["textSecondary"]))
        painter.drawText(
            QRectF(area.left(), area.bottom()-22, area.width(), 20),
            Qt.AlignmentFlag.AlignCenter,
            f"max. {self.width_mm:.0f} × {self.height_mm:.0f} × {self.depth_mm:.0f} mm",
        )


def _point(x: float, y: float):
    from PySide6.QtCore import QPointF
    return QPointF(x, y)
