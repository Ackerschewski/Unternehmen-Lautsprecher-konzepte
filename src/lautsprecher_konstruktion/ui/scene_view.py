"""Interactive 3D view of the enclosure scene: orbit, zoom, named views, see-through walls.

Pure QPainter with a depth-sorted triangle fill: no OpenGL, so it works on every machine and in offscreen tests.
"""
from __future__ import annotations

from math import cos, radians, sin

import numpy as np
from PySide6.QtCore import QPointF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QImage, QMouseEvent, QPainter, QWheelEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from lautsprecher_konstruktion.enclosure.scene import (
    Scene,
    Solid,
    SolidKind,
    build_scene,
    camera_angles,
    mesh,
)
from lautsprecher_konstruktion.services.design import DesignBundle
from lautsprecher_konstruktion.ui.cabinet_preview import CabinetPreview
from lautsprecher_konstruktion.ui.raster import draw_triangle, new_buffers
from lautsprecher_konstruktion.ui.tokens import UI_FONT, theme

ZOOM_MIN, ZOOM_MAX = 0.4, 6.0
ELEVATION_LIMIT = 89.0


def _rotation(azimuth_deg: float, elevation_deg: float) -> np.ndarray:
    a, e = radians(azimuth_deg), radians(elevation_deg)
    about_y = np.array([[cos(a), 0, sin(a)], [0, 1, 0], [-sin(a), 0, cos(a)]])
    about_x = np.array([[1, 0, 0], [0, cos(e), -sin(e)], [0, sin(e), cos(e)]])
    return about_x @ about_y


class SceneCanvas(QWidget):
    viewChanged = Signal()

    def __init__(self, mode: str = "light") -> None:
        super().__init__()
        self.mode = mode
        self.scene: Scene | None = None
        self.azimuth, self.elevation = camera_angles("iso")
        self.zoom = 1.0
        self.pan = QPointF(0, 0)
        self.walls_transparent = False
        self._last: QPointF | None = None
        self.setMinimumSize(320, 240)
        self.setMouseTracking(False)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def sizeHint(self) -> QSize:
        return QSize(560, 380)

    def set_scene(self, scene: Scene | None) -> None:
        self.scene = scene
        self.reset()

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        self.update()

    def set_view(self, name: str) -> None:
        self.azimuth, self.elevation = camera_angles(name)
        self.viewChanged.emit()
        self.update()

    def reset(self) -> None:
        self.azimuth, self.elevation = camera_angles("iso")
        self.zoom, self.pan = 1.0, QPointF(0, 0)
        self.viewChanged.emit()
        self.update()

    def set_walls_transparent(self, on: bool) -> None:
        self.walls_transparent = on
        self.update()

    def orbit(self, d_azimuth: float, d_elevation: float) -> None:
        self.azimuth = (self.azimuth + d_azimuth) % 360.0
        self.elevation = max(-ELEVATION_LIMIT, min(ELEVATION_LIMIT, self.elevation + d_elevation))
        self.viewChanged.emit()
        self.update()

    def zoom_by(self, factor: float) -> None:
        self.zoom = max(ZOOM_MIN, min(ZOOM_MAX, self.zoom * factor))
        self.viewChanged.emit()
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._last = event.position()
        self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._last is None:
            return
        delta = event.position() - self._last
        self._last = event.position()
        if event.buttons() & Qt.MouseButton.RightButton:
            self.pan += delta
            self.update()
        else:
            self.orbit(-delta.x() * 0.5, delta.y() * 0.5)

    def mouseReleaseEvent(self, _event: QMouseEvent) -> None:
        self._last = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def wheelEvent(self, event: QWheelEvent) -> None:
        self.zoom_by(1.12 if event.angleDelta().y() > 0 else 1 / 1.12)

    def _project(self, points: np.ndarray, centre: np.ndarray, scale: float) -> tuple[np.ndarray, np.ndarray]:
        """Orthographic projection: screen x/y in pixels and view depth (larger = farther)."""
        # model: x right, y up, z into the cabinet; the viewer starts in front of the front panel
        local = (points - centre) * np.array([1.0, 1.0, -1.0])
        view = local @ _rotation(self.azimuth, self.elevation).T
        sx = self.width() / 2 + self.pan.x() + view[:, 0] * scale
        sy = self.height() / 2 + self.pan.y() - view[:, 1] * scale
        return np.column_stack((sx, sy)), -view[:, 2]

    def paintEvent(self, _event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = theme(self.mode)
        painter.fillRect(self.rect(), QColor(t["surface"]))
        if self.scene is None:
            painter.setPen(QColor(t["textSecondary"]))
            painter.setFont(QFont(UI_FONT, 11))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "3D-Ansicht für diese Bauart noch nicht verfügbar.")
            return
        lo, hi = self.scene.bounds()
        centre = (np.array(lo) + np.array(hi)) / 2
        diag = float(np.linalg.norm(np.array(hi) - np.array(lo)))
        scale = min(self.width(), self.height()) * 0.8 / max(diag, 1e-6) * self.zoom
        light = np.array([-0.4, 0.7, 0.6])
        light /= np.linalg.norm(light)
        rotation = _rotation(self.azimuth, self.elevation)
        ss = 1 if self._last is not None else 2  # coarser while dragging, supersampled when still
        width, height = max(1, self.width() * ss), max(1, self.height() * ss)
        bg = QColor(t["surface"])
        colour, depth = new_buffers(width, height, (bg.red(), bg.green(), bg.blue()))
        transparent: list[tuple[float, np.ndarray, np.ndarray, tuple[float, float, float], float]] = []
        for solid in self.scene.solids:
            vertices, faces = mesh(solid)
            xy, view_depth = self._project(vertices, centre, scale)
            xy = xy * ss
            base, alpha = self._colour(solid, t)
            middle = vertices.mean(axis=0)
            for face in faces:
                a, b, c = vertices[face[0]], vertices[face[1]], vertices[face[2]]
                normal = np.cross(b - a, c - a)
                norm = np.linalg.norm(normal)
                if norm == 0:
                    continue
                if float(np.dot(normal, (a + b + c) / 3 - middle)) < 0:  # solids are convex: point every normal outwards
                    normal = -normal
                view_normal = (normal / norm * np.array([1.0, 1.0, -1.0])) @ rotation.T
                if view_normal[2] <= 0:  # back faces are never drawn
                    continue
                shade = 0.58 + 0.42 * max(0.0, float(np.dot(view_normal, light)))
                rgb = (base.red() * shade, base.green() * shade, base.blue() * shade)
                if alpha == 255:
                    draw_triangle(colour, depth, xy[face], view_depth[face], rgb)
                else:
                    transparent.append((float(view_depth[face].mean()), xy[face], view_depth[face], rgb, alpha / 255))
        for _d, txy, tz, rgb, a in sorted(transparent, key=lambda item: -item[0]):  # far to near, tested but not written
            draw_triangle(colour, depth, txy, tz, rgb, a, write_depth=False)
        image = QImage(colour.clip(0, 255).astype(np.uint8).tobytes(), width, height, width * 3, QImage.Format.Format_RGB888)
        painter.drawImage(self.rect(), image.copy())
        painter.setPen(QColor(t["textSecondary"]))
        painter.setFont(QFont(UI_FONT, 9))
        ex, ey, ez = self.scene.extent
        painter.drawText(12, self.height() - 12,
                         f"{ex*1000:.0f} × {ey*1000:.0f} × {ez*1000:.0f} mm · vereinfachte Geometrie, kein Hersteller-CAD")

    def _colour(self, solid: Solid, t: dict[str, str]) -> tuple[QColor, int]:
        kind = solid.kind
        if kind is SolidKind.PANEL:
            return QColor(t["borderStrong"]).lighter(115), 40 if self.walls_transparent else 255
        if kind in {SolidKind.DRIVER, SolidKind.PASSIVE_RADIATOR}:
            return QColor(t["accent"]), 255
        if kind is SolidKind.PORT:
            return QColor(t["docAccent"]), 255
        if kind is SolidKind.TREATMENT:
            return QColor(t["constructionAccent"]), 210
        if kind is SolidKind.DIVIDER:
            return QColor(t["borderStrong"]), 255
        return QColor(t["textSecondary"]), 255


class ScenePreview(QWidget):
    """Canvas plus view buttons, wall transparency and the accuracy note."""

    def __init__(self, mode: str = "light") -> None:
        super().__init__()
        self.canvas = SceneCanvas(mode)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        bar = QHBoxLayout()
        self.view_buttons: dict[str, QPushButton] = {}
        for key, text in (("iso", "ISO"), ("front", "Front"), ("side", "Seite"), ("top", "Oben")):
            button = QPushButton(text)
            button.setObjectName("sceneViewButton")
            button.clicked.connect(lambda _=False, k=key: self.canvas.set_view(k))
            bar.addWidget(button)
            self.view_buttons[key] = button
        self.reset_button = QPushButton("Zurücksetzen")
        self.reset_button.clicked.connect(self.canvas.reset)
        bar.addWidget(self.reset_button)
        self.walls = QCheckBox("Außenwände durchsichtig")
        self.walls.toggled.connect(self.canvas.set_walls_transparent)
        bar.addWidget(self.walls)
        bar.addStretch(1)
        layout.addLayout(bar)
        layout.addWidget(self.canvas, 1)
        self.note = QLabel("")
        self.note.setWordWrap(True)
        self.note.setObjectName("sceneNote")
        layout.addWidget(self.note)

    def set_mode(self, mode: str) -> None:
        self.canvas.set_mode(mode)

    def set_bundle(self, bundle: DesignBundle | None) -> bool:
        """True when a 3D scene exists for this design; False means the caller keeps showing the 2D preview."""
        scene = build_scene(bundle) if bundle is not None else None
        self.canvas.set_scene(scene)
        if scene is None:
            self.note.setText("Für diese Bauart gibt es noch keine 3D-Geometrie; die 2D-Vorschau bleibt.")
            return False
        text = " ".join(scene.notes)
        if scene.unplaced:
            text += " Ohne 3D-Position: " + "; ".join(scene.unplaced) + "."
        self.note.setText(text)
        return True


class HeroPreview(QStackedWidget):
    """Result hero: the 3D scene when the design has geometry for it, the 2D preview otherwise."""

    def __init__(self, mode: str = "light") -> None:
        super().__init__()
        self.flat = CabinetPreview(mode)
        self.solid = ScenePreview(mode)
        self.addWidget(self.flat)
        self.addWidget(self.solid)

    @property
    def showing_3d(self) -> bool:
        return self.currentWidget() is self.solid

    def set_mode(self, mode: str) -> None:
        self.flat.set_mode(mode)
        self.solid.set_mode(mode)

    def set_bundle(self, bundle: DesignBundle | None) -> None:
        self.flat.set_bundle(bundle)
        ok = self.solid.set_bundle(bundle) if bundle is not None else False
        self.setCurrentWidget(self.solid if ok else self.flat)
