from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CabinetDimensions:
    width_m: float
    height_m: float
    depth_m: float
    panel_thickness_m: float
    front_thickness_m: float | None = None
    back_thickness_m: float | None = None
    top_thickness_m: float | None = None
    bottom_thickness_m: float | None = None
    front_layers: int = 1

    def __post_init__(self) -> None:
        values = (self.width_m, self.height_m, self.depth_m, self.panel_thickness_m)
        if any(v <= 0 for v in values):
            raise ValueError("All cabinet dimensions must be positive")
        if min(self.width_m, self.height_m, self.depth_m) <= 2 * self.panel_thickness_m:
            raise ValueError("Panel thickness leaves no positive internal dimension")
        if self.front_layers < 1 or any(v is not None and v <= 0 for v in
                                        (self.front_thickness_m,self.back_thickness_m,self.top_thickness_m,self.bottom_thickness_m)):
            raise ValueError("panel layer count and thickness must be positive")
        if self.internal_height_m <= 0 or self.internal_depth_m <= 0:
            raise ValueError("front/back or top/bottom thickness leaves no internal space")

    @property
    def effective_front_thickness_m(self) -> float:
        return (self.front_thickness_m or self.panel_thickness_m)*self.front_layers

    @property
    def effective_back_thickness_m(self) -> float:
        return self.back_thickness_m or self.panel_thickness_m

    @property
    def internal_width_m(self) -> float:
        return self.width_m - 2 * self.panel_thickness_m

    @property
    def internal_height_m(self) -> float:
        return self.height_m - (self.top_thickness_m or self.panel_thickness_m) - (self.bottom_thickness_m or self.panel_thickness_m)

    @property
    def internal_depth_m(self) -> float:
        return self.depth_m - self.effective_front_thickness_m - self.effective_back_thickness_m

    @property
    def gross_internal_volume_m3(self) -> float:
        return self.internal_width_m * self.internal_height_m * self.internal_depth_m


@dataclass(frozen=True)
class CutPanel:
    name: str
    quantity: int
    width_m: float
    height_m: float
    thickness_m: float


def calculate_net_volume(cabinet: CabinetDimensions, displacement_m3: float = 0.0) -> float:
    if displacement_m3 < 0:
        raise ValueError("displacement_m3 must not be negative")
    result = cabinet.gross_internal_volume_m3 - displacement_m3
    if result <= 0:
        raise ValueError("Displacements consume the complete internal volume")
    return result


def solve_depth_for_net_volume(
    *,
    external_width_m: float,
    external_height_m: float,
    panel_thickness_m: float,
    target_net_volume_m3: float,
    displacement_m3: float = 0.0,
    front_thickness_m: float | None = None,
    back_thickness_m: float | None = None,
    top_thickness_m: float | None = None,
    bottom_thickness_m: float | None = None,
    front_layers: int = 1,
) -> CabinetDimensions:
    if target_net_volume_m3 <= 0:
        raise ValueError("target_net_volume_m3 must be positive")
    if displacement_m3 < 0:
        raise ValueError("displacement_m3 must not be negative")

    inner_w = external_width_m - 2 * panel_thickness_m
    inner_h = external_height_m - (top_thickness_m or panel_thickness_m) - (bottom_thickness_m or panel_thickness_m)
    if inner_w <= 0 or inner_h <= 0:
        raise ValueError("Width/height are incompatible with panel thickness")

    required_gross = target_net_volume_m3 + displacement_m3
    inner_depth = required_gross / (inner_w * inner_h)
    external_depth = inner_depth + (front_thickness_m or panel_thickness_m)*front_layers + (back_thickness_m or panel_thickness_m)

    return CabinetDimensions(
        width_m=external_width_m,
        height_m=external_height_m,
        depth_m=external_depth,
        panel_thickness_m=panel_thickness_m,
        front_thickness_m=front_thickness_m,
        back_thickness_m=back_thickness_m,
        top_thickness_m=top_thickness_m,
        bottom_thickness_m=bottom_thickness_m,
        front_layers=front_layers,
    )


def cut_list(cabinet: CabinetDimensions) -> tuple[CutPanel, ...]:
    """Return a basic six-panel butt-joint cut list."""
    t = cabinet.panel_thickness_m
    between_front_back = cabinet.internal_depth_m
    between_sides = cabinet.width_m - 2 * t

    return (
        CutPanel("Front", cabinet.front_layers, cabinet.width_m, cabinet.height_m,
                 cabinet.front_thickness_m or t),
        CutPanel("Back", 1, cabinet.width_m, cabinet.height_m,
                 cabinet.back_thickness_m or t),
        CutPanel("Side", 2, between_front_back, cabinet.height_m, t),
        CutPanel("Top", 1, between_sides, between_front_back,
                 cabinet.top_thickness_m or t),
        CutPanel("Bottom", 1, between_sides, between_front_back,
                 cabinet.bottom_thickness_m or t),
    )
