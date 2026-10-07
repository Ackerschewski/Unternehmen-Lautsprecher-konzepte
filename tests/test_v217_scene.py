"""TASK-0029 workstream E: UI-independent 3D scene and interactive preview."""
from __future__ import annotations

import os

import numpy as np
import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from lautsprecher_konstruktion.enclosure.scene import (
    SolidKind,
    build_scene,
    camera_angles,
    mesh,
    supports,
)
from lautsprecher_konstruktion.enclosure.treatment import AcousticTreatment, TreatmentKind
from lautsprecher_konstruktion.project.demo import demo_project
from lautsprecher_konstruktion.project.models import CrossoverConfig
from lautsprecher_konstruktion.services.design import DesignBundle, calculate_project
from lautsprecher_konstruktion.ui.scene_view import HeroPreview, SceneCanvas

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])  # type: ignore[return-value]


def _bundle(family: str = "sealed", **extra: object) -> DesignBundle:
    project = demo_project()
    config = project.enclosure.model_copy(update={"enclosure_type": family, "target_qtc": 0.5, "external_width_mm": 350,
                                                  "external_height_mm": 600, "brace_quantity": 1, **extra})
    return calculate_project(project.model_copy(update={
        "enclosure": config, "treatments": (AcousticTreatment(id="T1", kind=TreatmentKind.LOCAL_ABSORBER, position="top",
                                                              area_m2=0.05, thickness_m=0.03),),
        "crossover": CrossoverConfig(enabled=False), "tweeter_name": ""}))


def test_scene_uses_the_cabinet_dimensions_and_has_all_object_classes() -> None:
    bundle = _bundle()
    scene = build_scene(bundle)
    assert scene is not None
    cab = bundle.cabinet
    ex, ey, ez = scene.extent
    assert (ex, ey, ez) == pytest.approx((cab.width_m, cab.height_m, cab.depth_m), abs=1e-3)  # the chassis flanges stand 0.5 mm proud of the panels
    kinds = {s.kind for s in scene.solids}
    assert {SolidKind.PANEL, SolidKind.DRIVER, SolidKind.BRACE, SolidKind.TREATMENT} <= kinds
    assert len(scene.by_kind(SolidKind.PANEL)) == 6
    assert any("vereinfachte" in s.accuracy for s in scene.by_kind(SolidKind.DRIVER))
    assert any("Hersteller-CAD" in n for n in scene.notes)


def test_driver_sits_on_the_front_and_inside_the_cabinet() -> None:
    bundle = _bundle()
    scene = build_scene(bundle)
    assert scene is not None
    (driver, *_) = scene.by_kind(SolidKind.DRIVER)
    assert driver.lo[2] <= 0.0 and driver.hi[2] > 0.0
    lo, hi = driver.bounds
    assert -1e-6 <= lo[0] and hi[0] <= bundle.cabinet.width_m and -1e-6 <= lo[1] and hi[1] <= bundle.cabinet.height_m


def test_treatments_stay_inside_the_internal_volume_and_unplaced_ones_are_reported() -> None:
    bundle = _bundle()
    scene = build_scene(bundle)
    assert scene is not None
    cab = bundle.cabinet
    for solid in scene.by_kind(SolidKind.TREATMENT):
        assert solid.lo[0] >= cab.panel_thickness_m - 1e-9 and solid.hi[0] <= cab.width_m - cab.panel_thickness_m + 1e-9
        assert solid.lo[2] >= 0 and solid.hi[2] <= cab.depth_m
    placed = build_scene(bundle.__class__(**{**bundle.__dict__, "treatments": (
        AcousticTreatment(id="X", kind=TreatmentKind.TL_SEGMENT, position="segment:2"),)}))
    assert placed is not None and placed.unplaced and "keine definierte 3D-Position" in placed.unplaced[0]


def test_unsupported_families_have_no_scene() -> None:
    bundle = _bundle("open_baffle", brace_quantity=0)
    assert not supports(bundle) and build_scene(bundle) is None


def test_meshes_are_closed_triangle_sets() -> None:
    scene = build_scene(_bundle())
    assert scene is not None
    for solid in scene.solids:
        vertices, faces = mesh(solid)
        assert vertices.shape[1] == 3 and faces.max() < len(vertices) and np.isfinite(vertices).all()


def test_camera_presets() -> None:
    assert camera_angles("front") == (0.0, 0.0) and camera_angles("top")[1] > 80
    with pytest.raises(ValueError):
        camera_angles("diagonal")


def test_canvas_orbit_zoom_views_and_reset(app: QApplication) -> None:
    canvas = SceneCanvas()
    canvas.resize(500, 400)
    canvas.set_scene(build_scene(_bundle()))
    start = (canvas.azimuth, canvas.elevation)
    canvas.orbit(30, 10)
    assert canvas.azimuth != start[0] and canvas.elevation > start[1]
    canvas.orbit(0, 500)
    assert canvas.elevation <= 89.0  # never flips over the pole
    zoom = canvas.zoom
    canvas.zoom_by(1.5)
    assert canvas.zoom > zoom
    canvas.zoom_by(1000)
    assert canvas.zoom <= 6.0
    canvas.set_view("side")
    assert (canvas.azimuth, canvas.elevation) == (90.0, 0.0)
    canvas.reset()
    assert (canvas.azimuth, canvas.elevation) == start and canvas.zoom == 1.0


def _render(canvas: SceneCanvas) -> QImage:
    return canvas.grab().toImage()


def test_canvas_renders_something_and_transparency_changes_the_picture(app: QApplication) -> None:
    canvas = SceneCanvas()
    canvas.resize(500, 400)
    canvas.set_scene(build_scene(_bundle()))
    opaque = _render(canvas)
    canvas.set_walls_transparent(True)
    see_through = _render(canvas)
    assert opaque != see_through
    background = opaque.pixel(2, 2)
    assert any(opaque.pixel(x, y) != background for x in range(150, 350, 10) for y in range(100, 300, 10))


def test_mouse_drag_orbits(app: QApplication) -> None:
    from PySide6.QtGui import QMouseEvent
    canvas = SceneCanvas()
    canvas.resize(400, 300)
    canvas.set_scene(build_scene(_bundle()))
    before = canvas.azimuth
    press = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPointF(100, 100), Qt.MouseButton.LeftButton,
                        Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    move = QMouseEvent(QMouseEvent.Type.MouseMove, QPointF(160, 100), Qt.MouseButton.NoButton,
                       Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    canvas.mousePressEvent(press)
    canvas.mouseMoveEvent(move)
    assert canvas.azimuth != before


def test_hero_falls_back_to_2d_when_no_geometry(app: QApplication) -> None:
    hero = HeroPreview()
    hero.set_bundle(_bundle())
    assert hero.showing_3d
    hero.set_bundle(_bundle("open_baffle", brace_quantity=0))
    assert not hero.showing_3d
    hero.set_bundle(None)
    assert not hero.showing_3d
