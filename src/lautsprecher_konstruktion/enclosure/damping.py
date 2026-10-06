"""Wall lining (damping) and resistive vent elements of closed-type boxes.

The lining recommendation follows the common builder practice (Dickason, Small): a
25 to 50 mm layer of wool or foam on the rear wall and the walls behind the driver
(the planner uses the thin end, 25 mm), kept clear of the driver magnet and the cone. It is never counted as displacement:
fibre fill acts as extra apparent volume, not as lost volume.
"""
from __future__ import annotations

from dataclasses import dataclass

from lautsprecher_konstruktion.enclosure.rectangular import CabinetDimensions

LINING_MAX_M = 0.025   # 1 inch, lower end of the usual 25 to 50 mm
LINING_MIN_M = 0.01
LINING_STEP_M = 0.005
DRIVER_CLEARANCE_M = 0.02   # free air between lining and driver magnet / basket
SIDE_CLEARANCE_M = 0.01


@dataclass(frozen=True)
class WallLining:
    thickness_m: float
    rear_area_m2: float
    side_area_m2: float
    clearance_to_driver_m: float

    @property
    def area_m2(self) -> float:
        return self.rear_area_m2 + self.side_area_m2

    @property
    def volume_m3(self) -> float:
        return self.area_m2*self.thickness_m


@dataclass(frozen=True)
class VentDamper:
    """Resistive vent filling of an aperiodic box or a passive cardioid rear vent."""
    surface: str                 # "front" or "back"
    resistance_pa_s_m3: float    # R_ac required across the vent
    area_m2: float
    specific_resistance_rayl: float
    qtc_closed: float | None = None
    ql: float | None = None
    qtc_effective: float | None = None
    leak_corner_hz: float | None = None


def plan_wall_lining(cabinet: CabinetDimensions, driver_depth_m: float,
                     driver_cutout_m: float | None) -> WallLining | None:
    """Lining behind the driver plane; None when the box is too shallow to keep the magnet free."""
    free = cabinet.internal_depth_m-driver_depth_m
    thickness = min(LINING_MAX_M, free-DRIVER_CLEARANCE_M)
    thickness = int(max(0.0, thickness)/LINING_STEP_M+1e-9)*LINING_STEP_M
    if thickness < LINING_MIN_M:
        return None
    rear = cabinet.internal_width_m*cabinet.internal_height_m
    side = 0.0
    behind = cabinet.internal_depth_m-driver_depth_m
    cutout = driver_cutout_m or cabinet.internal_width_m
    if (cabinet.internal_width_m-cutout)/2-thickness >= SIDE_CLEARANCE_M and behind > 0:
        side = 2*cabinet.internal_height_m*behind
    return WallLining(thickness, rear, side, free-thickness)
