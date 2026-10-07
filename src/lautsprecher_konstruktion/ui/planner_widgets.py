"""Reusable visual planner widgets for the guided loudspeaker workflow."""
from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QButtonGroup,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from lautsprecher_konstruktion.enclosure.registry import registry
from lautsprecher_konstruktion.services.automatic import SpeakerDesign
from lautsprecher_konstruktion.ui.tokens import DISPLAY_FONT, UI_FONT, theme


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
            button = QPushButton(f"{title}\n{subtitle}")
            button.setObjectName("choiceCard")
            button.setCheckable(True)
            button.setMinimumHeight(66)
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


class VariantCards(QWidget):
    """Decision-first comparison cards; the technical table remains secondary."""

    selected = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._buttons: list[QPushButton] = []
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(10)

    @staticmethod
    def _f3(design: SpeakerDesign) -> float | None:
        bundle = design.bundle
        return bundle.sealed.f3_hz if bundle.sealed else (
            bundle.vented_response.f3_hz if bundle.vented_response else None
        )

    @staticmethod
    def _tag(index: int, design: SpeakerDesign, baseline: SpeakerDesign) -> str:
        if index == 0:
            return "Empfehlung"
        f3 = VariantCards._f3(design)
        base_f3 = VariantCards._f3(baseline)
        cab = design.bundle.cabinet
        base = baseline.bundle.cabinet
        volume = cab.width_m*cab.height_m*cab.depth_m
        base_volume = base.width_m*base.height_m*base.depth_m
        if f3 is not None and base_f3 is not None and f3 < base_f3-3:
            return "Mehr Tiefbass"
        if volume < base_volume*0.92:
            return "Kompakter"
        if (
            design.total_price_eur is not None
            and baseline.total_price_eur is not None
            and design.total_price_eur < baseline.total_price_eur*0.92
        ):
            return "Günstiger"
        return "Alternative"

    def set_designs(self, designs: tuple[SpeakerDesign, ...]) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._buttons.clear()
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        if not designs:
            label = QLabel("Noch keine Varianten berechnet.")
            label.setObjectName("caption")
            self._layout.addWidget(label)
            return
        baseline = designs[0]
        for index, design in enumerate(designs):
            cab = design.bundle.cabinet
            f3 = self._f3(design)
            enclosure = registry.get(design.project.enclosure.enclosure_type).label
            price = (
                f"{design.total_price_eur:.0f} €"
                if design.total_price_eur is not None else "Preis unvollständig"
            )
            tag = self._tag(index, design, baseline)
            text = (
                f"{design.label}\n"
                f"{tag} · {enclosure}\n"
                f"{cab.width_m*1000:.0f} × {cab.height_m*1000:.0f} × {cab.depth_m*1000:.0f} mm"
                f" · F3 {f3:.0f} Hz\n" if f3 is not None else
                f"{design.label}\n{tag} · {enclosure}\n"
                f"{cab.width_m*1000:.0f} × {cab.height_m*1000:.0f} × {cab.depth_m*1000:.0f} mm"
                f" · F3 n/a\n"
            )
            text += f"{price} · Teilbewertung {design.score:.0f}/100"
            if index:
                base_cab = baseline.bundle.cabinet
                deltas: list[str] = []
                if f3 is not None:
                    base_f3 = self._f3(baseline)
                    if base_f3 is not None and abs(f3-base_f3) >= 0.5:
                        deltas.append(f"F3 {f3-base_f3:+.0f} Hz")
                volume = cab.width_m*cab.height_m*cab.depth_m
                base_volume = base_cab.width_m*base_cab.height_m*base_cab.depth_m
                if base_volume > 0 and abs(volume/base_volume-1) >= 0.03:
                    deltas.append(f"Volumen {(volume/base_volume-1)*100:+.0f} %")
                if (
                    design.total_price_eur is not None
                    and baseline.total_price_eur is not None
                    and abs(design.total_price_eur-baseline.total_price_eur) >= 1
                ):
                    deltas.append(
                        f"Kosten {design.total_price_eur-baseline.total_price_eur:+.0f} €"
                    )
                if deltas:
                    text += "\nvs. A · " + " · ".join(deltas)
            button = QPushButton(text)
            button.setObjectName("variantCard")
            button.setCheckable(True)
            button.setMinimumHeight(118)
            button.clicked.connect(lambda _checked=False, i=index: self.selected.emit(i))
            self._group.addButton(button)
            self._layout.addWidget(button, 1)
            self._buttons.append(button)
        self.select(0)

    def select(self, index: int) -> None:
        if 0 <= index < len(self._buttons):
            self._buttons[index].setChecked(True)
