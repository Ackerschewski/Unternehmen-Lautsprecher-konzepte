"""Compact visual cabinet preview for the guided design result."""
from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from lautsprecher_konstruktion.services.design import DesignBundle
from lautsprecher_konstruktion.ui.tokens import DISPLAY_FONT, UI_FONT, theme


class CabinetPreview(QWidget):
    """Brand-consistent front/perspective preview; not a manufacturing drawing."""

    def __init__(self, mode: str = "light") -> None:
        super().__init__()
        self.mode = mode
        self.bundle: DesignBundle | None = None
        self.setMinimumHeight(250)

    def sizeHint(self) -> QSize:
        return QSize(460, 340)

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        self.update()

    def set_bundle(self, bundle: DesignBundle | None) -> None:
        self.bundle = bundle
        self.update()

    def paintEvent(self, _event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = theme(self.mode)
        painter.fillRect(self.rect(), QColor(t["surface"]))

        margin = 24.0
        area = QRectF(margin, margin, max(1.0, self.width()-2*margin), max(1.0, self.height()-2*margin))
        if self.bundle is None:
            painter.setPen(QColor(t["textSecondary"]))
            painter.setFont(QFont(UI_FONT, 11))
            painter.drawText(area, Qt.AlignmentFlag.AlignCenter, "Entwurfsvorschau\nNach der Berechnung erscheint hier das Gehäuse.")
            return

        cab = self.bundle.cabinet
        w_mm = cab.width_m*1000
        h_mm = cab.height_m*1000
        d_mm = cab.depth_m*1000

        title_font = QFont(DISPLAY_FONT, 20)
        painter.setFont(title_font)
        painter.setPen(QColor(t["textPrimary"]))
        painter.drawText(QRectF(area.left(), area.top(), area.width(), 34), Qt.AlignmentFlag.AlignLeft, "Entwurf")

        caption_font = QFont(UI_FONT, 9)
        painter.setFont(caption_font)
        painter.setPen(QColor(t["textSecondary"]))
        painter.drawText(
            QRectF(area.left(), area.top()+34, area.width(), 24),
            Qt.AlignmentFlag.AlignLeft,
            f"{w_mm:.0f} × {h_mm:.0f} × {d_mm:.0f} mm",
        )

        draw_top = area.top()+70
        draw_h = max(80.0, area.height()-105)
        perspective_x = min(60.0, draw_h*0.18)
        perspective_y = perspective_x*0.55
        usable_w = max(80.0, area.width()-perspective_x-20)
        scale = min(usable_w/max(w_mm, 1.0), draw_h/max(h_mm, 1.0))
        front_w = w_mm*scale
        front_h = h_mm*scale
        left = area.left() + (area.width()-front_w-perspective_x)/2
        top = draw_top + (draw_h-front_h)/2

        front = QRectF(left, top, front_w, front_h)
        line = QPen(QColor(t["accent"]), 2.0)
        painter.setPen(line)
        painter.setBrush(QColor(t["surfaceElevated"]))
        painter.drawRoundedRect(front, 7, 7)

        # Simple depth cue: enough to make the result tangible without pretending to be CAD.
        painter.setPen(QPen(QColor(t["borderStrong"]), 1.5))
        painter.drawLine(front.topRight(), front.topRight() + front.topRight().__class__(perspective_x, perspective_y))
        painter.drawLine(front.bottomRight(), front.bottomRight() + front.bottomRight().__class__(perspective_x, perspective_y))
        painter.drawLine(
            front.topRight() + front.topRight().__class__(perspective_x, perspective_y),
            front.bottomRight() + front.bottomRight().__class__(perspective_x, perspective_y),
        )

        for element in self.bundle.front_elements:
            if element.surface != "front":
                continue
            cx = front.left() + element.x_m*1000*scale
            cy = front.bottom() - element.y_m*1000*scale
            diameter = (element.outer_diameter_m or element.cutout_diameter_m or element.width)*1000*scale
            if element.outer_diameter_m or element.cutout_diameter_m:
                radius = max(3.0, diameter/2)
                painter.setPen(QPen(QColor(t["accent"]), 1.6))
                painter.setBrush(QColor(t["band"]))
                painter.drawEllipse(QRectF(cx-radius, cy-radius, 2*radius, 2*radius))
                inner = max(2.0, radius*0.62)
                painter.setBrush(QColor(t["surface"]))
                painter.drawEllipse(QRectF(cx-inner, cy-inner, 2*inner, 2*inner))
            else:
                ew = element.width*1000*scale
                eh = element.height*1000*scale
                painter.setPen(QPen(QColor(t["accent"]), 1.6))
                painter.setBrush(QColor(t["band"]))
                painter.drawRoundedRect(QRectF(cx-ew/2, cy-eh/2, ew, eh), 4, 4)

        painter.setFont(QFont(UI_FONT, 8))
        painter.setPen(QColor(t["textSecondary"]))
        painter.drawText(
            QRectF(area.left(), area.bottom()-24, area.width(), 20),
            Qt.AlignmentFlag.AlignCenter,
            "Visualisierung zur Orientierung · Fertigungsmaße stehen unter Zeichnungen",
        )
