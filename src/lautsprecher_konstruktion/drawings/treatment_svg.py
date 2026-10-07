"""Side-section rectangles of the project's own acoustic treatments, taken from the 3D scene (one geometry source)."""
from __future__ import annotations

from html import escape

from lautsprecher_konstruktion.enclosure.scene import SolidKind, build_scene
from lautsprecher_konstruktion.services.design import DesignBundle


def treatment_section_svg(bundle: DesignBundle, x_front: float, y_bottom: float, scale: float, label_class: str) -> list[str]:
    """Rectangles for user-defined treatments in the side section; planner-derived lining is drawn by the caller.

    ``x_front``/``y_bottom`` are the SVG coordinates of the outer front-bottom corner, ``scale`` is px per mm.
    """
    scene = build_scene(bundle)
    if scene is None:
        return []
    own = {t.id: t for t in bundle.treatments if not t.derived}
    parts: list[str] = []
    labelled: set[str] = set()
    for solid in scene.by_kind(SolidKind.TREATMENT):
        tid = solid.id.rsplit(".", 1)[0]
        if tid not in own:
            continue
        x0, x1 = x_front + solid.lo[2] * 1000 * scale, x_front + solid.hi[2] * 1000 * scale
        y1, y0 = y_bottom - solid.lo[1] * 1000 * scale, y_bottom - solid.hi[1] * 1000 * scale
        parts.append(f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{x1-x0:.1f}" height="{y1-y0:.1f}" class="lining"/>')
        if tid not in labelled:
            labelled.add(tid)
            parts.append(f'<text x="{x0+3:.1f}" y="{y0-4:.1f}" class="{label_class}">{escape(tid)}</text>')
    return parts


def treatment_notes(bundle: DesignBundle) -> list[str]:
    """One line per user-defined treatment for the drawing's information table (including unplaced ones)."""
    lines = []
    for t in bundle.treatments:
        if t.derived:
            continue
        size = f"{t.area_m2:.2f} m² × {t.thickness_m*1000:.0f} mm" if t.area_m2 else f"{t.thickness_m*1000:.0f} mm"
        lines.append(f"{t.id} {t.label_de()}: {size}")
    return lines
