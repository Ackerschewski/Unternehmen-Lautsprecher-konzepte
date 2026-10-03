import pytest

from lautsprecher_konstruktion.enclosure.rectangular import (
    calculate_net_volume,
    cut_list,
    solve_depth_for_net_volume,
)


def test_depth_solver_hits_requested_net_volume() -> None:
    cabinet = solve_depth_for_net_volume(
        external_width_m=0.35,
        external_height_m=0.60,
        panel_thickness_m=0.018,
        target_net_volume_m3=0.042,
        displacement_m3=0.003,
    )

    assert calculate_net_volume(cabinet, 0.003) == pytest.approx(0.042)
    assert cabinet.depth_m > 0.20


def test_cut_list_contains_six_panels() -> None:
    cabinet = solve_depth_for_net_volume(
        external_width_m=0.35,
        external_height_m=0.60,
        panel_thickness_m=0.018,
        target_net_volume_m3=0.042,
    )
    panels = cut_list(cabinet)
    assert sum(panel.quantity for panel in panels) == 6
