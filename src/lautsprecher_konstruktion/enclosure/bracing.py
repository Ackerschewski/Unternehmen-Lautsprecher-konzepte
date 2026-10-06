from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WindowBrace:
    outer_width_m: float
    outer_height_m: float
    thickness_m: float
    border_m: float
    quantity: int = 1

    def __post_init__(self) -> None:
        if min(self.outer_width_m, self.outer_height_m, self.thickness_m, self.border_m) <= 0:
            raise ValueError("brace dimensions must be positive")
        if self.quantity < 1:
            raise ValueError("brace quantity must be at least 1")
        if 2 * self.border_m >= min(self.outer_width_m, self.outer_height_m):
            raise ValueError("brace border leaves no window opening")

    @property
    def material_volume_each_m3(self) -> float:
        outer = self.outer_width_m * self.outer_height_m
        inner = (
            (self.outer_width_m - 2 * self.border_m)
            * (self.outer_height_m - 2 * self.border_m)
        )
        return (outer - inner) * self.thickness_m

    @property
    def total_displacement_m3(self) -> float:
        return self.material_volume_each_m3 * self.quantity


def brace_depths(inner_depth_m: float, brace: WindowBrace | None,
                 *, start_m: float = 0.0, check_fit: bool = False) -> tuple[float, ...]:
    """Brace planes measured from the inner face of the front panel.

    With check_fit the free depth must hold every brace including its thickness
    (planes may neither overlap each other nor the back wall).
    """
    if brace is None:
        return ()
    if start_m >= inner_depth_m:
        raise ValueError("Für Fensterstreben bleibt hinter den Einbauteilen kein Platz.")
    available = inner_depth_m - start_m
    if check_fit and available/(brace.quantity+1) < brace.thickness_m:
        raise ValueError(
            f"Für {brace.quantity} Fensterstrebe(n) à {brace.thickness_m*1000:.0f} mm bleiben hinter den "
            f"Einbauteilen nur {available*1000:.0f} mm; Strebenzahl verringern oder Tiefe vergrößern.")
    return tuple(start_m + available*i/(brace.quantity+1)
                 for i in range(1, brace.quantity+1))
