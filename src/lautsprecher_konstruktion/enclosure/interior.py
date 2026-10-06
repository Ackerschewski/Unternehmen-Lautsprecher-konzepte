"""Depth-axis interior geometry of box families with ports, partitions and radiators.

All depths run from the inner face of the front panel towards the rear (z). A
port's physical length L includes the wall it passes through (the Helmholtz
column starts at the outer wall face), so only ``L - wall`` protrudes into the
cabinet. Driver and radiator depths are taken as given (conservatively from the
inner face of their wall).
"""
from __future__ import annotations

from dataclasses import dataclass
from math import pi, sqrt

from lautsprecher_konstruktion.enclosure.bracing import WindowBrace
from lautsprecher_konstruktion.enclosure.isobaric import Coupler
from lautsprecher_konstruktion.enclosure.layout import FrontElement, _overlap
from lautsprecher_konstruktion.enclosure.ports import PortDesign
from lautsprecher_konstruktion.warnings import DesignWarning

# A free port end acts like an unflanged opening only if it keeps roughly one
# port diameter to the nearest wall (Dickason; Small); below that the effective
# length shrinks and Fb rises.
PORT_END_CLEARANCE_FACTOR = 1.0
DEPTH_MARGIN_M = 0.005


@dataclass(frozen=True)
class InteriorGeometry:
    internal_depth_m: float
    front_wall_m: float
    back_wall_m: float
    partition_thickness_m: float
    partition_front_depth_m: float | None = None  # front chamber depth, None without partition

    def wall_m(self, surface: str) -> float:
        return {"front": self.front_wall_m, "back": self.back_wall_m,
                "partition": self.partition_thickness_m}[surface]

    @property
    def rear_chamber_depth_m(self) -> float | None:
        if self.partition_front_depth_m is None:
            return None
        return self.internal_depth_m - self.partition_front_depth_m - self.partition_thickness_m


def port_protrusion_m(physical_length_m: float, wall_m: float) -> float:
    """Part of a port tube that sticks into the cabinet (wall thickness is part of L)."""
    return max(0.0, physical_length_m - wall_m)


def inside_displacement_m3(port: PortDesign | None, wall_m: float) -> float:
    """Air volume of the port tube that is actually inside the cabinet."""
    return 0.0 if port is None else port.area_m2 * port_protrusion_m(port.physical_length_m, wall_m)


def equivalent_diameter_m(port: PortDesign) -> float:
    return port.diameter_m if port.diameter_m else sqrt(4.0 * port.area_m2 / pi)


def element_span_m(e: FrontElement, g: InteriorGeometry) -> tuple[float, float]:
    """Depth range [z0, z1] occupied by an element inside the cabinet."""
    depth = e.mounting_depth_m
    if e.surface == "partition":
        z0 = g.partition_front_depth_m or 0.0
        return z0, z0 + depth  # drivers and ducts are measured from the partition's front face
    if e.type == "port":
        depth = port_protrusion_m(depth, g.wall_m(e.surface))
    if e.surface == "back":
        return g.internal_depth_m - depth, g.internal_depth_m
    return 0.0, depth


def _coupler_element(woofer: FrontElement, coupler: Coupler) -> FrontElement:
    return FrontElement(id="Koppelkammer", surface="front", type="brace",
                        x_m=woofer.x_m, y_m=woofer.y_m,
                        outer_diameter_m=coupler.outer_diameter_m,
                        mounting_depth_m=coupler.rear_extent_m)


def check_interior(
    layout: tuple[FrontElement, ...],
    g: InteriorGeometry,
    *,
    width_m: float,
    height_m: float,
    panel_thickness_m: float,
    bottom_thickness_m: float,
    top_thickness_m: float,
    brace: WindowBrace | None,
    brace_depths_m: tuple[float, ...],
    coupler: Coupler | None = None,
    ports: dict[str, PortDesign] | None = None,
) -> tuple[DesignWarning, ...]:
    """Cross-surface collisions, brace passage and port end clearance."""
    issues: list[DesignWarning] = []
    spans = {e.id: element_span_m(e, g) for e in layout}
    bodies = list(layout)
    woofer = next((e for e in layout if e.id == "W1" and e.surface == "front"), None)
    if coupler is not None and woofer is not None:
        pseudo = _coupler_element(woofer, coupler)
        bodies.append(pseudo)
        spans[pseudo.id] = (0.0, coupler.rear_extent_m)

    for i, a in enumerate(bodies):
        for b in bodies[i + 1:]:
            if a.surface == b.surface:
                continue  # same-surface pairs are handled by check_layout / the coupler checks
            a0, a1 = spans[a.id]
            b0, b1 = spans[b.id]
            if a0 >= b1 + DEPTH_MARGIN_M or b0 >= a1 + DEPTH_MARGIN_M:
                continue
            if a1 <= a0 or b1 <= b0:
                continue
            overlap = _overlap(a, b)
            if overlap > 0:
                depth_overlap = min(a1, b1) - max(a0, b0)
                issues.append(DesignWarning(
                    code="DEPTH_COLLISION", severity="error",
                    message=(f"{a.id} und {b.id} kollidieren im Innenraum: Grundflächen überlappen um "
                             f"{overlap*1000:.0f} mm und die Einbautiefen überschneiden sich um "
                             f"{max(depth_overlap, 0.0)*1000:.0f} mm (Abstand mindestens "
                             f"{DEPTH_MARGIN_M*1000:.0f} mm). Position oder Fläche ändern."),
                    value=overlap * 1000))

    if brace is not None:
        for index, zb in enumerate(brace_depths_m, start=1):
            for e in layout:
                z0, z1 = spans[e.id]
                if z1 <= z0 or z1 <= zb or z0 >= zb + brace.thickness_m:
                    continue
                edge_gap = min(e.x_m - e.width / 2 - panel_thickness_m,
                               width_m - panel_thickness_m - e.x_m - e.width / 2,
                               e.y_m - e.height / 2 - bottom_thickness_m,
                               height_m - top_thickness_m - e.y_m - e.height / 2)
                if edge_gap < brace.border_m:
                    over = (brace.border_m - edge_gap) * 1000
                    issues.append(DesignWarning(
                        code="BRACE_COLLISION", severity="error",
                        message=f"{e.id} kollidiert mit Strebe B{index} um {over:.1f} mm.", value=over))

    for key, port in (ports or {}).items():
        element = next((e for e in layout if e.id == key), None)
        if element is None:
            continue
        wall = g.wall_m(element.surface)
        if port.physical_length_m < wall - 1e-9:
            issues.append(DesignWarning(
                code="PORT_TOO_SHORT", severity="warning",
                message=(f"{key}: berechnete Rohrlänge {port.physical_length_m*1000:.0f} mm ist kürzer als die "
                         f"durchstoßene Wand ({wall*1000:.0f} mm); der Port wäre mindestens so lang wie die Wand, "
                         "Fb läge tiefer als berechnet. Kleineren Portquerschnitt wählen."),
                value=port.physical_length_m * 1000, limit=wall * 1000))
            continue
        protrusion = port_protrusion_m(port.physical_length_m, wall)
        if element.surface == "front":
            room = g.partition_front_depth_m if g.partition_front_depth_m is not None else g.internal_depth_m
            wall_name = "Trennwand" if g.partition_front_depth_m is not None else "Rückwand"
        elif element.surface == "back":
            room = g.rear_chamber_depth_m if g.rear_chamber_depth_m is not None else g.internal_depth_m
            wall_name = "Trennwand" if g.rear_chamber_depth_m is not None else "Frontplatte"
        else:
            room = g.rear_chamber_depth_m or 0.0
            wall_name = "Rückwand"
        clearance = room - protrusion
        needed = PORT_END_CLEARANCE_FACTOR * equivalent_diameter_m(port)
        if 0 <= clearance < needed - 1e-9:
            issues.append(DesignWarning(
                code="PORT_END_CLEARANCE", severity="warning",
                message=(f"{key}: Portende nur {clearance*1000:.0f} mm von der {wall_name}; mindestens ein "
                         f"Portdurchmesser ({needed*1000:.0f} mm) Abstand halten, sonst verkürzt sich die "
                         "wirksame Länge und Fb steigt."),
                value=clearance * 1000, limit=needed * 1000))
    return tuple(issues)
