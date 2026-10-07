"""UI-independent 3D scene of a rectangular enclosure, built from the same design bundle as the drawings.

Coordinates in metres: x = width (0 left … W), y = height (0 bottom … H), z = depth (0 front face … D).
Every solid carries an accuracy label. Panels use the nominal outer dimensions; chassis, ports and
braces are simplified envelopes (no manufacturer CAD), and the scene says so.
There is no second geometry: sizes come from the cabinet, front elements, brace and treatment objects.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from math import cos, pi, sin

import numpy as np
from numpy.typing import NDArray

from lautsprecher_konstruktion.services.design import DesignBundle

Vec = tuple[float, float, float]
SEGMENTS = 28
FLANGE_M = 0.0005  # chassis flange stands proud of the panel so faces are not coplanar
SIMPLIFIED = "vereinfachte Geometrie"
NOMINAL = "Nennmaß aus der Konstruktion"


class SolidKind(StrEnum):
    PANEL = "panel"
    DRIVER = "driver"
    PORT = "port"
    PASSIVE_RADIATOR = "passive_radiator"
    BRACE = "brace"
    DIVIDER = "divider"
    TREATMENT = "treatment"


@dataclass(frozen=True)
class Solid:
    id: str
    kind: SolidKind
    label: str
    shape: str  # "box" or "cylinder" (axis along z)
    lo: Vec  # box: minimum corner; cylinder: centre of the front base circle
    hi: Vec  # box: maximum corner; cylinder: centre of the back base circle
    radius_m: float = 0.0
    accuracy: str = SIMPLIFIED
    outer_wall: bool = False  # can be hidden to look inside

    @property
    def bounds(self) -> tuple[Vec, Vec]:
        if self.shape == "box":
            return self.lo, self.hi
        r = self.radius_m
        return ((self.lo[0] - r, self.lo[1] - r, min(self.lo[2], self.hi[2])),
                (self.hi[0] + r, self.hi[1] + r, max(self.lo[2], self.hi[2])))


@dataclass
class Scene:
    solids: list[Solid] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    unplaced: list[str] = field(default_factory=list)  # objects that exist in the project but have no defined 3D position

    def by_kind(self, kind: SolidKind) -> list[Solid]:
        return [s for s in self.solids if s.kind is kind]

    @property
    def extent(self) -> Vec:
        lo, hi = self.bounds()
        return hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]

    def bounds(self) -> tuple[Vec, Vec]:
        boxes = [s.bounds for s in self.solids]
        return ((min(b[0][0] for b in boxes), min(b[0][1] for b in boxes), min(b[0][2] for b in boxes)),
                (max(b[1][0] for b in boxes), max(b[1][1] for b in boxes), max(b[1][2] for b in boxes)))



def supports(bundle: DesignBundle) -> bool:
    """Rectangular boxes only; baffles, horns and folded lines stay in 2D until their geometry exists."""
    return (bundle.baffle_mode is None and bundle.front_horn is None and bundle.tapped_horn is None
            and bundle.folded_line is None)


def build_scene(bundle: DesignBundle) -> Scene | None:
    if not supports(bundle):
        return None
    cab = bundle.cabinet
    w, h, d = cab.width_m, cab.height_m, cab.depth_m
    tf, tb = cab.effective_front_thickness_m, cab.effective_back_thickness_m
    tt, tbo, ts = cab.top_thickness_m or cab.panel_thickness_m, cab.bottom_thickness_m or cab.panel_thickness_m, cab.panel_thickness_m
    scene = Scene(notes=["Chassis, Port und Verstärkungen sind vereinfachte Hüllen, kein Hersteller-CAD.",
                         "Plattenmaße sind die Nennmaße der Konstruktion; Verbindungsdetails (Gehrung, Nut) sind nicht modelliert."])
    add = scene.solids.append
    add(Solid("front", SolidKind.PANEL, "Frontplatte", "box", (0, 0, 0), (w, h, tf), accuracy=NOMINAL, outer_wall=True))
    add(Solid("back", SolidKind.PANEL, "Rückwand", "box", (0, 0, d - tb), (w, h, d), accuracy=NOMINAL, outer_wall=True))
    add(Solid("left", SolidKind.PANEL, "Seitenwand links", "box", (0, tbo, tf), (ts, h - tt, d - tb), accuracy=NOMINAL, outer_wall=True))
    add(Solid("right", SolidKind.PANEL, "Seitenwand rechts", "box", (w - ts, tbo, tf), (w, h - tt, d - tb), accuracy=NOMINAL, outer_wall=True))
    add(Solid("bottom", SolidKind.PANEL, "Boden", "box", (ts, 0, tf), (w - ts, tbo, d - tb), accuracy=NOMINAL, outer_wall=True))
    add(Solid("top", SolidKind.PANEL, "Deckel", "box", (ts, h - tt, tf), (w - ts, h, d - tb), accuracy=NOMINAL, outer_wall=True))

    for e in bundle.front_elements:
        if e.surface == "partition":
            continue
        radius = (e.outer_diameter_m or max(e.width, e.height)) / 2
        depth = e.mounting_depth_m or 0.0
        if e.type == "port":
            length = bundle.port.physical_length_m if bundle.port is not None else max(depth, tf)
            kind, label = SolidKind.PORT, f"Port {e.id}"
            radius = (bundle.port.diameter_m / 2) if bundle.port is not None and bundle.port.diameter_m else radius
            front_z = 0.0 if e.surface == "front" else d
            z0, z1 = (front_z, front_z + (length if e.surface == "front" else -length))
            add(Solid(e.id, kind, label, "cylinder", (e.x_m, e.y_m, z0), (e.x_m, e.y_m, z1), radius, SIMPLIFIED))
            continue
        if e.type == "brace":
            continue
        kind = SolidKind.PASSIVE_RADIATOR if e.type == "passive_radiator" else SolidKind.DRIVER
        z0 = -FLANGE_M if e.surface == "front" else d - tb + FLANGE_M
        z1 = tf + depth if e.surface == "front" else d - tb - depth
        add(Solid(e.id, kind, f"Chassis {e.id}" if kind is SolidKind.DRIVER else f"Passivmembran {e.id}", "cylinder",
                  (e.x_m, e.y_m, z0), (e.x_m, e.y_m, z1), radius, SIMPLIFIED))

    _add_braces(scene, bundle, tf, tbo, ts, w, h, tt)
    if bundle.rear_chamber_volume_m3 is not None and bundle.partition_front_depth_m is not None:
        z = tf + bundle.partition_front_depth_m
        add(Solid("partition", SolidKind.DIVIDER, "Trennwand", "box", (ts, tbo, z), (w - ts, h - tt, z + ts), accuracy=NOMINAL))
    _add_treatments(scene, bundle, tf, tb, tbo, tt, ts, w, h, d)
    return scene


def _add_braces(scene: Scene, bundle: DesignBundle, tf: float, bottom: float, side: float, w: float, h: float, top: float) -> None:
    brace = bundle.brace
    if brace is None:
        return
    iw, ih = w - 2 * side, h - top - bottom
    b = min(brace.border_m, iw / 2, ih / 2)
    for index, depth in enumerate(bundle.brace_depths_m, start=1):
        z0 = tf + depth
        z1 = z0 + brace.thickness_m
        frame = ((side, bottom, side + iw, bottom + b), (side, bottom + ih - b, side + iw, bottom + ih),
                 (side, bottom + b, side + b, bottom + ih - b), (side + iw - b, bottom + b, side + iw, bottom + ih - b))
        for part, (x0, y0, x1, y1) in enumerate(frame, start=1):
            scene.solids.append(Solid(f"brace{index}.{part}", SolidKind.BRACE, f"Verstärkungsrahmen {index}", "box",
                                      (x0, y0, z0), (x1, y1, z1), accuracy=SIMPLIFIED))


def _add_treatments(scene: Scene, bundle: DesignBundle, tf: float, tb: float, bottom: float, top: float, side: float,
                    w: float, h: float, d: float) -> None:
    iw, ih = w - 2 * side, h - top - bottom
    z_back = d - tb
    for t in bundle.treatments:
        slabs: list[tuple[Vec, Vec]] = []
        th = t.thickness_m
        if t.position == "rear":
            slabs.append(((side, bottom, z_back - th), (side + iw, bottom + ih, z_back)))
            behind = _side_depth(bundle, t.area_m2, ih, iw, th)
            if t.derived and behind > 0:
                for x0, x1 in ((side, side + th), (side + iw - th, side + iw)):
                    slabs.append(((x0, bottom, z_back - behind), (x1, bottom + ih, z_back)))
        elif t.position == "sides" and t.area_m2:
            depth = min(t.area_m2 / (2 * ih), z_back - tf)
            for x0, x1 in ((side, side + th), (side + iw - th, side + iw)):
                slabs.append(((x0, bottom, z_back - depth), (x1, bottom + ih, z_back)))
        elif t.position in {"top", "bottom"} and t.area_m2:
            depth = min(t.area_m2 / iw, z_back - tf)
            y0, y1 = (bottom + ih - th, bottom + ih) if t.position == "top" else (bottom, bottom + th)
            slabs.append(((side, y0, z_back - depth), (side + iw, y1, z_back)))
        if not slabs:
            scene.unplaced.append(f"{t.label_de()} ({t.id}): keine definierte 3D-Position")
            continue
        for index, (lo, hi) in enumerate(slabs, start=1):
            scene.solids.append(Solid(f"{t.id}.{index}", SolidKind.TREATMENT, t.label_de(), "box", lo, hi,
                                      accuracy=SIMPLIFIED if t.derived else NOMINAL))


def _side_depth(bundle: DesignBundle, rear_area: float | None, ih: float, iw: float, th: float) -> float:
    lining = bundle.damping
    if lining is None or lining.side_area_m2 <= 0:
        return 0.0
    return lining.side_area_m2 / (2 * ih)


def box_mesh(lo: Vec, hi: Vec, cell_m: float = 1e9) -> tuple[NDArray[np.float64], NDArray[np.int64]]:
    """Box as a triangle mesh; optionally subdivided (cell_m); the default is one cell per face."""
    verts: list[Vec] = []
    faces: list[tuple[int, int, int]] = []
    lo_a, hi_a = np.array(lo), np.array(hi)
    for axis in range(3):
        u, v = [a for a in range(3) if a != axis]
        nu = max(1, int(np.ceil((hi_a[u] - lo_a[u]) / cell_m)))
        nv = max(1, int(np.ceil((hi_a[v] - lo_a[v]) / cell_m)))
        for plane in (lo_a[axis], hi_a[axis]):
            base = len(verts)
            for i in range(nu + 1):
                for k in range(nv + 1):
                    point = [0.0, 0.0, 0.0]
                    point[axis] = float(plane)
                    point[u] = float(lo_a[u] + (hi_a[u] - lo_a[u]) * i / nu)
                    point[v] = float(lo_a[v] + (hi_a[v] - lo_a[v]) * k / nv)
                    verts.append((point[0], point[1], point[2]))
            for i in range(nu):
                for k in range(nv):
                    a = base + i * (nv + 1) + k
                    b, c, d = a + 1, a + nv + 1, a + nv + 2
                    faces += [(a, b, d), (a, d, c)]
    return np.array(verts, dtype=float), np.array(faces, dtype=np.int64)


def cylinder_mesh(front: Vec, back: Vec, radius: float, segments: int = SEGMENTS) -> tuple[NDArray[np.float64], NDArray[np.int64]]:
    ring = [(radius * cos(2 * pi * i / segments), radius * sin(2 * pi * i / segments)) for i in range(segments)]
    verts = [(front[0] + x, front[1] + y, front[2]) for x, y in ring] + [(back[0] + x, back[1] + y, back[2]) for x, y in ring]
    verts += [front, back]
    faces: list[tuple[int, int, int]] = []
    for i in range(segments):
        j = (i + 1) % segments
        faces += [(i, j, segments + j), (i, segments + j, segments + i), (2 * segments, j, i), (2 * segments + 1, segments + i, segments + j)]
    return np.array(verts, dtype=float), np.array(faces, dtype=np.int64)


def mesh(solid: Solid) -> tuple[NDArray[np.float64], NDArray[np.int64]]:
    return box_mesh(solid.lo, solid.hi) if solid.shape == "box" else cylinder_mesh(solid.lo, solid.hi, solid.radius_m)


VIEWS = ("iso", "front", "side", "top")


def camera_angles(view: str) -> tuple[float, float]:
    """(azimuth°, elevation°) for a named view; azimuth 0 looks at the front panel."""
    table = {"iso": (-35.0, 25.0), "front": (0.0, 0.0), "side": (90.0, 0.0), "top": (0.0, 89.0)}
    if view not in table:
        raise ValueError(f"unknown view: {view}")
    return table[view]
