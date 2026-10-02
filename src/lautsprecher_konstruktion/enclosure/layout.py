"""Shared front-panel geometry for UI, collision checks and manufacturing output."""
from __future__ import annotations

from math import cos, hypot, pi, sin, sqrt
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from lautsprecher_konstruktion.warnings import DesignWarning


class FrontElement(BaseModel):
    id: str
    surface: Literal["front", "back", "partition"] = "front"
    type: Literal["woofer", "midrange", "tweeter", "fullrange", "subwoofer",
                  "passive_radiator", "port", "brace"]
    x_m: float = Field(ge=0)
    y_m: float = Field(ge=0)
    outer_diameter_m: float | None = Field(default=None, gt=0)
    cutout_diameter_m: float | None = Field(default=None, gt=0)
    mounting_depth_m: float = Field(default=0.0, ge=0)
    rotation_deg: float = 0.0
    bolt_circle_diameter_m: float | None = Field(default=None, gt=0)
    bolt_count: int = Field(default=0, ge=0)
    hole_diameter_m: float | None = Field(default=None, gt=0)
    angular_offset_deg: float = 0.0
    clearance_m: float = Field(default=0.005, ge=0)
    width_m: float | None = Field(default=None, gt=0)
    height_m: float | None = Field(default=None, gt=0)
    corner_radius_m: float = Field(default=0.0, ge=0)

    @model_validator(mode="after")
    def check_shape(self) -> FrontElement:
        if self.outer_diameter_m is None and (self.width_m is None or self.height_m is None):
            raise ValueError("front element requires a diameter or width and height")
        if self.bolt_count and self.bolt_circle_diameter_m is None:
            raise ValueError("bolt_count requires bolt_circle_diameter_m")
        return self

    @property
    def width(self) -> float:
        return self.width_m or self.outer_diameter_m or 0.0

    @property
    def height(self) -> float:
        return self.height_m or self.outer_diameter_m or 0.0


def bolt_holes(element: FrontElement) -> tuple[tuple[float, float, float], ...]:
    if (not element.bolt_count or element.bolt_circle_diameter_m is None
            or element.hole_diameter_m is None):
        return ()
    radius = element.bolt_circle_diameter_m / 2
    offset = (element.angular_offset_deg + element.rotation_deg) * pi / 180
    return tuple((element.x_m + radius * cos(offset + 2*pi*i/element.bolt_count),
                  element.y_m + radius * sin(offset + 2*pi*i/element.bolt_count),
                  element.hole_diameter_m / 2) for i in range(element.bolt_count))


def _overlap(a: FrontElement, b: FrontElement) -> float:
    # Exact for unrotated circles and rectangles, including circle/rectangle pairs.
    if a.outer_diameter_m is not None and b.outer_diameter_m is not None:
        return (a.outer_diameter_m + b.outer_diameter_m) / 2 + max(a.clearance_m, b.clearance_m) - hypot(a.x_m-b.x_m, a.y_m-b.y_m)
    if a.outer_diameter_m is None and b.outer_diameter_m is None:
        dx = (a.width+b.width)/2 + max(a.clearance_m,b.clearance_m) - abs(a.x_m-b.x_m)
        dy = (a.height+b.height)/2 + max(a.clearance_m,b.clearance_m) - abs(a.y_m-b.y_m)
        return min(dx,dy) if dx > 0 and dy > 0 else -1.0
    circle, rect = (a,b) if a.outer_diameter_m is not None else (b,a)
    dx = max(abs(circle.x_m-rect.x_m)-rect.width/2, 0.0)
    dy = max(abs(circle.y_m-rect.y_m)-rect.height/2, 0.0)
    return circle.outer_diameter_m/2 + max(a.clearance_m,b.clearance_m) - sqrt(dx*dx+dy*dy)


def check_layout(elements: tuple[FrontElement, ...], width_m: float, height_m: float,
                 depth_m: float, *, partition_inset_m: float = 0.0,
                 partition_top_m: float = 0.0,
                 partition_bottom_m: float = 0.0) -> tuple[DesignWarning, ...]:
    warnings: list[DesignWarning] = []
    if len({e.id for e in elements}) != len(elements):
        warnings.append(DesignWarning(code="DUPLICATE_ID", severity="error", message="Front-IDs sind nicht eindeutig."))
    for e in elements:
        left=partition_inset_m if e.surface == "partition" else 0.0
        right=width_m-partition_inset_m if e.surface == "partition" else width_m
        bottom=partition_bottom_m if e.surface == "partition" else 0.0
        top=height_m-partition_top_m if e.surface == "partition" else height_m
        margin = min(e.x_m-e.width/2-left, right-e.x_m-e.width/2,
                     e.y_m-e.height/2-bottom, top-e.y_m-e.height/2)
        if margin < e.clearance_m:
            warnings.append(DesignWarning(code="FRONT_EDGE", severity="error",
                message=f"{e.id} unterschreitet den Front-Randabstand um {(e.clearance_m-margin)*1000:.1f} mm.",
                value=margin*1000, limit=e.clearance_m*1000))
        if e.mounting_depth_m > depth_m:
            warnings.append(DesignWarning(code="BACK_WALL", severity="error",
                message=f"{e.id} kollidiert mit der Rückwand um {(e.mounting_depth_m-depth_m)*1000:.1f} mm."))
        for x,y,r in bolt_holes(e):
            if min(x-r-left,right-x-r,y-r-bottom,top-y-r) < e.clearance_m:
                warnings.append(DesignWarning(code="DRILL_EDGE", severity="warning",
                    message=f"Schraubbohrung von {e.id} liegt zu nah an der Frontkante."))
                break
            if e.cutout_diameter_m is not None and hypot(x-e.x_m,y-e.y_m)-r < e.cutout_diameter_m/2:
                warnings.append(DesignWarning(code="DRILL_CUTOUT",severity="error",
                    message=f"Schraubbohrung von {e.id} schneidet den Treiberausschnitt."))
                break
    for i,a in enumerate(elements):
        for b in elements[i+1:]:
            if a.surface != b.surface:
                continue
            overlap = _overlap(a,b)
            if overlap > 0:
                warnings.append(DesignWarning(code="FRONT_COLLISION", severity="error",
                    message=f"{a.id} kollidiert mit {b.id} um {overlap*1000:.1f} mm.", value=overlap*1000))
    return tuple(warnings)
