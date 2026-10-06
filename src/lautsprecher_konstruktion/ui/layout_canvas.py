"""Interactive front layout: drag drivers and ports, nudge with the arrow keys, snap to a grid."""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QKeyEvent, QPainter, QPen, QWheelEvent
from PySide6.QtWidgets import QGraphicsItem, QGraphicsScene, QGraphicsView

from lautsprecher_konstruktion.enclosure.layout import FrontElement
from lautsprecher_konstruktion.ui.tokens import theme as theme_tokens

SNAP_GRID_MM = 5.0
CENTER_SNAP_MM = 4.0


def snap_position(x_mm: float, y_mm: float, plate_w_mm: float, plate_h_mm: float,
                  grid_mm: float = SNAP_GRID_MM, center_mm: float = CENTER_SNAP_MM) -> tuple[float, float]:
    """Snap to the vertical centre line first, otherwise to the grid; clamp to the plate."""
    if abs(x_mm - plate_w_mm / 2) <= center_mm:
        x_mm = plate_w_mm / 2
    elif grid_mm > 0:
        x_mm = round(x_mm / grid_mm) * grid_mm
    if grid_mm > 0:
        y_mm = round(y_mm / grid_mm) * grid_mm
    return min(max(x_mm, 0.0), plate_w_mm), min(max(y_mm, 0.0), plate_h_mm)


class _ElementItem(QGraphicsItem):
    """Circle (or rectangle) at the element centre; the scene uses millimetres, y pointing down."""

    def __init__(self, index: int, element: FrontElement, plate_h_mm: float, mode: str = "light") -> None:
        super().__init__()
        self.index = index
        self.element = element
        self._height = plate_h_mm
        outer = element.outer_diameter_m
        self._w = (outer if outer else element.width) * 1000
        self._h = (outer if outer else element.height) * 1000
        self._round = outer is not None
        cutout = element.cutout_diameter_m
        self._cut = (cutout * 1000) if (cutout and self._round) else None
        t = theme_tokens(mode)
        self._tokens = t
        # Type is shown by shape and label; colour only separates ports (dashed) from drivers.
        self._pen = QPen(QColor(t["textSecondary"]), 2)
        if element.type == "port":
            self._pen.setStyle(Qt.PenStyle.DashLine)
        self._brush = QBrush(QColor(t["surface"]))
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsMovable | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
                      | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setPos(element.x_m * 1000, plate_h_mm - element.y_m * 1000)
        self.setZValue(2)
        self.setToolTip(f"{element.id} · {element.type} · {element.x_m * 1000:.1f}/{element.y_m * 1000:.1f} mm")

    def boundingRect(self) -> QRectF:
        return QRectF(-self._w / 2 - 2, -self._h / 2 - 2, self._w + 4, self._h + 4)

    def paint(self, painter: QPainter, option: object, widget: object = None) -> None:
        painter.setPen(QPen(QColor(self._tokens["accent"]), 3) if self.isSelected() else self._pen)
        painter.setBrush(QBrush(QColor(self._tokens["accentSubtle"])) if self.isSelected() else self._brush)
        rect = QRectF(-self._w / 2, -self._h / 2, self._w, self._h)
        painter.drawEllipse(rect) if self._round else painter.drawRect(rect)
        if self._cut:
            painter.setPen(QPen(self._pen.color(), 1, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QRectF(-self._cut / 2, -self._cut / 2, self._cut, self._cut))
        painter.setPen(QPen(QColor(self._tokens["textPrimary"]), 1))
        painter.drawLine(QPointF(-4, 0), QPointF(4, 0))
        painter.drawLine(QPointF(0, -4), QPointF(0, 4))
        font = painter.font()
        font.setPixelSize(max(10, int(min(self._w, self._h) / 6)))
        painter.setFont(font)
        painter.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), self.element.id)


class FrontLayoutCanvas(QGraphicsView):
    """Emits elementMoved(index, x_m, y_m) when a drag ends or an arrow key nudges, and elementSelected(index)."""

    elementMoved = Signal(int, float, float, bool)  # index, x_m, y_m, from_keyboard
    elementSelected = Signal(int)

    SURFACES = (("front", "Front"), ("back", "Rückwand"), ("partition", "Trennwand"))

    def __init__(self) -> None:
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumHeight(260)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self._elements: tuple[FrontElement, ...] = ()
        self._surface = "front"
        self._plate = (350.0, 600.0)
        self._items: dict[int, _ElementItem] = {}
        self._selected = -1
        self._dragging: _ElementItem | None = None
        self.snap_enabled = True
        self._mode = "light"
        self.scene().selectionChanged.connect(self._scene_selection_changed)
        self._updating = False

    # --- model -> view ---------------------------------------------------

    @property
    def surface(self) -> str:
        return self._surface

    @property
    def plate_mm(self) -> tuple[float, float]:
        return self._plate

    def set_plate(self, width_mm: float, height_mm: float) -> None:
        self._plate = (width_mm, height_mm)

    def set_mode(self, mode: str) -> None:
        self._mode = mode

    def set_surface(self, surface: str) -> None:
        self._surface = surface

    def set_layout(self, elements: tuple[FrontElement, ...], selected: int = -1) -> None:
        self._updating = True
        self._elements = elements
        self._selected = selected
        scene = self.scene()
        scene.clear()
        self._items.clear()
        width, height = self._plate
        t = theme_tokens(self._mode)
        self.setBackgroundBrush(QBrush(QColor(t["background"])))
        scene.addRect(QRectF(0, 0, width, height), QPen(QColor(t["textSecondary"]), 2),
                      QBrush(QColor(t["surfaceElevated"]))).setZValue(0)
        grid = QPen(QColor(t["border"]), 0.6)
        for gx in range(0, int(width) + 1, 50):
            scene.addLine(gx, 0, gx, height, grid).setZValue(1)
        for gy in range(0, int(height) + 1, 50):
            scene.addLine(0, gy, width, gy, grid).setZValue(1)
        scene.addLine(width / 2, 0, width / 2, height, QPen(QColor(t["accent"]), 1, Qt.PenStyle.DashLine)).setZValue(1)
        for index, element in enumerate(elements):
            if element.surface != self._surface:
                continue
            item = _ElementItem(index, element, height, self._mode)
            scene.addItem(item)
            self._items[index] = item
            if index == selected:
                item.setSelected(True)
        scene.setSceneRect(QRectF(-15, -15, width + 30, height + 30))
        self.fitInView(scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self._updating = False

    def select(self, index: int) -> None:
        self._selected = index
        self._updating = True
        for key, item in self._items.items():
            item.setSelected(key == index)
        self._updating = False
        self.viewport().update()

    # --- interaction ---------------------------------------------------------

    def _scene_selection_changed(self) -> None:
        if self._updating:
            return
        chosen = [key for key, item in self._items.items() if item.isSelected()]
        if chosen and chosen[0] != self._selected:
            self._selected = chosen[0]
            self.elementSelected.emit(chosen[0])

    def mousePressEvent(self, event: object) -> None:
        super().mousePressEvent(event)
        item = self.itemAt(event.position().toPoint())
        self._dragging = item if isinstance(item, _ElementItem) else None
        self.setFocus()

    def mouseMoveEvent(self, event: object) -> None:
        super().mouseMoveEvent(event)
        item = self._dragging
        if item is not None and event.buttons() & Qt.MouseButton.LeftButton:
            x, y = self._snapped(item)
            item.setPos(x, self._plate[1] - y)

    def _snapped(self, item: _ElementItem) -> tuple[float, float]:
        width, height = self._plate
        if not self.snap_enabled:
            return (min(max(item.pos().x(), 0.0), width), min(max(height - item.pos().y(), 0.0), height))
        return snap_position(item.pos().x(), height - item.pos().y(), width, height)

    def mouseReleaseEvent(self, event: object) -> None:
        super().mouseReleaseEvent(event)
        item, self._dragging = self._dragging, None
        if item is None:
            return
        x, y = self._snapped(item)
        item.setPos(x, self._plate[1] - y)
        old = self._elements[item.index]
        if abs(x - old.x_m * 1000) > 1e-6 or abs(y - old.y_m * 1000) > 1e-6:
            self.elementMoved.emit(item.index, x / 1000.0, y / 1000.0, False)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        steps = {Qt.Key.Key_Left: (-1, 0), Qt.Key.Key_Right: (1, 0), Qt.Key.Key_Up: (0, 1), Qt.Key.Key_Down: (0, -1)}
        if event.key() in steps and self._selected in self._items:
            step = 10.0 if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else 1.0
            old = self._elements[self._selected]
            width, height = self._plate
            dx, dy = steps[event.key()]
            x = min(max(old.x_m * 1000 + dx * step, 0.0), width)
            y = min(max(old.y_m * 1000 + dy * step, 0.0), height)
            self.elementMoved.emit(self._selected, x / 1000.0, y / 1000.0, True)
            event.accept()
            return
        super().keyPressEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)

    def resizeEvent(self, event: object) -> None:
        super().resizeEvent(event)
        if self.scene().items():
            self.fitInView(self.scene().sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def item_center_px(self, index: int) -> tuple[int, int]:
        """Viewport pixel of an element centre (used by tests and keyboard helpers)."""
        point = self.mapFromScene(self._items[index].pos())
        return point.x(), point.y()

