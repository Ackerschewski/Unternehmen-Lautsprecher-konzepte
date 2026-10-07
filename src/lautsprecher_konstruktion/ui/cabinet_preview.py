"""Proportional cabinet sketches drawn from real data: size limits at the start, the front of a calculated design."""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from lautsprecher_konstruktion.enclosure.layout import FrontElement
from lautsprecher_konstruktion.ui.tokens import theme as theme_tokens

DRIVER_TYPES = {"woofer", "midrange", "tweeter", "fullrange", "subwoofer", "passive_radiator"}


class CabinetPreview(QWidget):
    """Front view with dimension labels; elements are only drawn when a calculated design provides them."""

    def __init__(self) -> None:
        super().__init__()
        self.mode = "light"
        self._size_mm: tuple[float, float, float] | None = None
        self._elements: tuple[FrontElement, ...] = ()
        self._caption = ""
        self._depth_note = ""
        self.setMinimumSize(220, 220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        self.update()

    def set_limits(self, width_mm: float, height_mm: float, depth_mm: float) -> None:
        """Start page: the maximum space as a box (the real size is chosen inside these limits)."""
        self._size_mm = (width_mm, height_mm, depth_mm)
        self._elements = ()
        self._caption = "Maximaler Bauraum"
        self._depth_note = f"Tiefe bis {depth_mm:.0f} mm"
        self.update()

    def set_design(self, width_mm: float, height_mm: float, depth_mm: float,
                   elements: tuple[FrontElement, ...], caption: str) -> None:
        self._size_mm = (width_mm, height_mm, depth_mm)
        self._elements = elements
        self._caption = caption
        self._depth_note = f"Tiefe {depth_mm:.0f} mm"
        self.update()

    def clear(self) -> None:
        self._size_mm = None
        self._elements = ()
        self.update()

    def element_count(self) -> int:
        return len(self._elements)

    def paintEvent(self, _event: object) -> None:
        t = theme_tokens(self.mode)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        ink, muted = QColor(t["textPrimary"]), QColor(t["textSecondary"])
        if self._size_mm is None:
            painter.setPen(muted)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Noch kein Entwurf")
            return
        w_mm, h_mm, _depth = self._size_mm
        margin_l, margin_r, margin_t, margin_b = 56.0, 24.0, 34.0, 52.0
        avail_w = max(40.0, self.width() - margin_l - margin_r)
        avail_h = max(40.0, self.height() - margin_t - margin_b)
        scale = min(avail_w / w_mm, avail_h / h_mm)
        bw, bh = w_mm * scale, h_mm * scale
        x0 = margin_l + (avail_w - bw) / 2
        y0 = margin_t + (avail_h - bh) / 2
        box = QRectF(x0, y0, bw, bh)
        painter.setPen(QPen(ink, 2))
        painter.setBrush(QColor(t["panel"]))
        painter.drawRoundedRect(box, 4, 4)
        label_font = QFont(self.font())
        label_font.setPixelSize(13)
        painter.setFont(label_font)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for element in self._elements:
            if element.surface != "front":
                continue
            cx = x0 + element.x_m * 1000 * scale
            cy = y0 + bh - element.y_m * 1000 * scale
            self._draw_element(painter, element, cx, cy, scale, t)
        painter.setPen(QPen(muted, 1))
        # width dimension below, height dimension left
        yb = y0 + bh + 16
        painter.drawLine(QPointF(x0, yb), QPointF(x0 + bw, yb))
        painter.drawLine(QPointF(x0, yb - 4), QPointF(x0, yb + 4))
        painter.drawLine(QPointF(x0 + bw, yb - 4), QPointF(x0 + bw, yb + 4))
        painter.setPen(ink)
        painter.drawText(QRectF(x0 - 20, yb + 2, bw + 40, 20), Qt.AlignmentFlag.AlignCenter, f"{w_mm:.0f} mm")
        xl = x0 - 14
        painter.setPen(QPen(muted, 1))
        painter.drawLine(QPointF(xl, y0), QPointF(xl, y0 + bh))
        painter.drawLine(QPointF(xl - 4, y0), QPointF(xl + 4, y0))
        painter.drawLine(QPointF(xl - 4, y0 + bh), QPointF(xl + 4, y0 + bh))
        painter.save()
        painter.translate(xl - 6, y0 + bh / 2)
        painter.rotate(-90)
        painter.setPen(ink)
        painter.drawText(QRectF(-80, -16, 160, 16), Qt.AlignmentFlag.AlignCenter, f"{h_mm:.0f} mm")
        painter.restore()
        painter.setPen(muted)
        painter.drawText(QRectF(0, 4, self.width(), 22), Qt.AlignmentFlag.AlignCenter,
                         f"{self._caption} · {self._depth_note}")

    @staticmethod
    def _draw_element(painter: QPainter, element: FrontElement, cx: float, cy: float, scale: float,
                      t: dict[str, str]) -> None:
        ink = QColor(t["textPrimary"])
        flange = element.outer_diameter_m or max(element.width, element.height)
        cutout = element.cutout_diameter_m or flange * 0.85
        if element.type == "port":
            w = (element.width_m or element.outer_diameter_m or 0.05) * 1000 * scale
            h = (element.height_m or element.outer_diameter_m or 0.05) * 1000 * scale
            rect = QRectF(cx - w / 2, cy - h / 2, w, h)
            painter.setPen(QPen(ink, 1.6, Qt.PenStyle.DashLine))
            painter.drawRoundedRect(rect, min(w, h) / 2 if element.outer_diameter_m else 3, 3)
            painter.setPen(QColor(t["textSecondary"]))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "Port")
            return
        r_flange = flange * 1000 * scale / 2
        r_cut = cutout * 1000 * scale / 2
        painter.setPen(QPen(QColor(t["textSecondary"]), 1))
        painter.drawEllipse(QPointF(cx, cy), r_flange, r_flange)
        painter.setPen(QPen(QColor(t["accent"]), 2.2))
        painter.setBrush(QColor(t["band"]))
        painter.drawEllipse(QPointF(cx, cy), r_cut, r_cut)
        painter.setBrush(QColor(t["accent"]))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy), max(2.0, r_cut * 0.22), max(2.0, r_cut * 0.22))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(ink)
        painter.drawText(QRectF(cx - r_flange, cy + r_flange * 0.55, r_flange * 2, 18), Qt.AlignmentFlag.AlignCenter,
                         element.id)
