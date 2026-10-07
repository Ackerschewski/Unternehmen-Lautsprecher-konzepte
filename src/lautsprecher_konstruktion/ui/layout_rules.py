"""Responsive workspace rules as pure functions (no Qt), so they can be tested without a window.

The planning column is only large while the user still enters data. Once a result exists the workspace
gets the room: collapsed below 1600 px, a slim inspector above, closed for the drawing workspace.
"""
from __future__ import annotations

from dataclasses import dataclass

START_SHARE = 0.38  # share of the window width for the planner before a result exists
START_MAX_PX = 440
START_MIN_PX = 320
INSPECTOR_PX = 360
WIDE_WINDOW_PX = 1600


@dataclass(frozen=True)
class PlannerLayout:
    open: bool
    width: int


def planner_layout(window_width: int, *, has_result: bool, view: str,
                   user_open: bool | None = None) -> PlannerLayout:
    """Width of the planning column. ``user_open`` is an explicit choice made with the "Vorgaben" button."""
    if not has_result:
        return PlannerLayout(True, max(START_MIN_PX, min(START_MAX_PX, round(window_width * START_SHARE))))
    if user_open is not None:
        return PlannerLayout(user_open, INSPECTOR_PX if user_open else 0)
    if view == "drawings":
        return PlannerLayout(False, 0)
    if window_width >= WIDE_WINDOW_PX:
        return PlannerLayout(True, INSPECTOR_PX)
    return PlannerLayout(False, 0)


def secondary_plot_count(window_width: int) -> int:
    """Sound lab: one secondary plot on laptops, two on wide screens."""
    return 2 if window_width >= 1700 else 1


def workspace_share(window_width: int, layout: PlannerLayout) -> float:
    """Share of the window width left for the workspace."""
    return 1.0 - (layout.width / window_width if layout.open and window_width else 0.0)
