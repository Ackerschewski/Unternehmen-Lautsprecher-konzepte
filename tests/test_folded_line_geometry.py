"""Shape tests for the folded-line families (areas, taper, path, gaps, drawing)."""
import itertools
import os
import re

import numpy as np
import pytest

from lautsprecher_konstruktion.acoustics.folded_line import simulate_folded_line
from lautsprecher_konstruktion.drawings.internal_dimensions_svg import (
    render_internal_dimensions_svg,
)
from lautsprecher_konstruktion.enclosure.folded_line import (
    LINE_TYPES,
    mltl_loaded_path_m,
    mltl_loaded_resonance_hz,
)
from lautsprecher_konstruktion.project.demo import demo_project
from lautsprecher_konstruktion.project.models import CrossoverConfig
from lautsprecher_konstruktion.services.design import calculate_project

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _bundle(family: str, **extra):
    project = demo_project()
    cfg = project.enclosure.model_copy(update={
        "enclosure_type": family, "target_volume_l": 120.0, "tuning_hz": 50.0,
        "external_height_mm": 1200.0, "external_width_mm": 300.0, "brace_quantity": 0, **extra})
    return calculate_project(project.model_copy(update={
        "enclosure": cfg, "front_elements": (), "tweeter_name": "",
        "crossover": CrossoverConfig(enabled=False)}))


@pytest.mark.parametrize("family", sorted(LINE_TYPES))
def test_line_geometry_is_consistent(family: str) -> None:
    b = _bundle(family)
    line = b.folded_line
    assert line is not None
    count = len(line.channel_heights_m)
    assert count % 2 == 0, "mouth must end on the front baffle (even channel count)"
    d = b.cabinet.internal_depth_m
    w = b.cabinet.internal_width_m
    t = b.cabinet.panel_thickness_m
    # areas follow heights, heights + partitions fill the internal height
    for h, a in zip(line.channel_heights_m, line.channel_areas_m2, strict=True):
        assert a == pytest.approx(w*h)
    assert sum(line.channel_heights_m)+line.fold_count*t == pytest.approx(b.cabinet.internal_height_m)
    # partitions are shorter than the depth by exactly their gap; gaps alternate back/front
    assert len(line.baffle_panels) == line.fold_count == len(line.turn_gaps_m)
    for i, (panel, gap) in enumerate(zip(line.baffle_panels, line.turn_gaps_m, strict=True)):
        assert panel.height_m == pytest.approx(d-gap)
        assert ("hinten" if i % 2 == 0 else "vorn") in panel.name
        assert gap <= 0.5*d+1e-9
    # driver chamber holds the driver
    driver_d = b.project.driver.outer_diameter_m or b.project.driver.cutout_diameter_m
    assert line.channel_heights_m[0] >= driver_d+0.016
    # path = straight runs + turns, acoustic segments carry exactly that length
    assert sum(line.straight_lengths_m)+sum(line.turn_lengths_m) == pytest.approx(line.path_length_m)
    assert sum(length for _, length, _ in line.segments()) == pytest.approx(line.path_length_m)
    assert all(length < d for length in line.straight_lengths_m)
    assert len(line.stuffing) == count and line.stuffing[-1] != "heavy"


@pytest.mark.parametrize("family", ["transmission_line_closed", "transmission_line_open", "labyrinth"])
def test_plain_line_area_follows_driver_sd(family: str) -> None:
    b = _bundle(family)
    line = b.folded_line
    sd = b.project.driver.sd_m2
    assert line is not None and sd
    duct = line.channel_areas_m2[1:]
    assert all(1.0*sd-1e-9 <= a <= 1.5*sd+1e-9 for a in duct)
    assert max(duct) == pytest.approx(min(duct))          # constant cross-section
    assert 0.9 < line.path_length_m/(343/(4*50.0)) < 1.15  # c/(4 f)


def test_tapered_line_narrows_towards_mouth() -> None:
    line = _bundle("transmission_line_tapered").folded_line
    assert line is not None
    duct = line.channel_areas_m2[1:]
    assert all(a > b for a, b in itertools.pairwise(duct))


def test_tqwt_tapers_from_driver_end_to_mouth() -> None:
    b = _bundle("tqwt")
    line = b.folded_line
    assert line is not None
    areas = line.channel_areas_m2
    assert all(a > c for a, c in itertools.pairwise(areas))
    assert 1.5 <= areas[0]/areas[-1] <= 4.5
    assert areas[0] > b.project.driver.sd_m2
    assert any("TQWT" in text for text in b.warnings)


def test_labyrinth_is_stuffed_over_whole_length() -> None:
    lab = _bundle("labyrinth").folded_line
    tl = _bundle("transmission_line_open").folded_line
    assert lab is not None and tl is not None
    assert all(x in ("heavy", "medium") for x in lab.stuffing)
    assert tl.stuffing[-1] == "none"
    assert lab.stuffing.count("heavy") > tl.stuffing.count("heavy")


def test_mltl_loaded_line_is_shorter_than_quarter_wave() -> None:
    area, port, leff = 0.05, 0.012, 0.08
    path = mltl_loaded_path_m(50.0, area, port, leff)
    assert path < 343/(4*50.0)
    assert mltl_loaded_resonance_hz(path, area, port, leff) == pytest.approx(50.0, rel=1e-3)
    b = _bundle("mltl", port_diameter_mm=130.0)
    assert b.folded_line is not None and b.port is not None
    assert b.port.diameter_m == pytest.approx(0.13)
    assert b.folded_line.mltl_port_ratio == pytest.approx(
        b.port.area_m2/(b.folded_line.channel_areas_m2[-1]), rel=1e-6)
    assert b.folded_line.estimated_quarter_wave_hz < 343/(4*b.folded_line.path_length_m)


@pytest.mark.parametrize("family", sorted(LINE_TYPES))
def test_interior_drawing_shows_partitions_gaps_stuffing_and_mouth(family: str) -> None:
    b = _bundle(family)
    line = b.folded_line
    assert line is not None
    svg = render_internal_dimensions_svg(b)
    for i in range(line.fold_count):
        assert f"F{i+1} ·" in svg
        assert f"Spalt {line.turn_gaps_m[i]*1000:.0f} mm" in svg
    # one partition rect per fold with the gap-reduced length
    scale_free = re.findall(r'class="stuffing"', svg)
    assert len(scale_free) == sum(1 for x in line.stuffing if x != "none")
    assert "Mündung vorn" in svg and "Treiberkammer" in svg
    assert 'stroke-dasharray="7 5"' in svg
    assert svg.count("<polyline") == 1


def test_simulation_uses_drawn_geometry_and_stuffing() -> None:
    b = _bundle("transmission_line_open")
    line = b.folded_line
    assert line is not None
    first = simulate_folded_line(b.project.driver, line, 10.0)
    from dataclasses import replace
    unstuffed = replace(line, stuffing=("none",)*len(line.stuffing))
    second = simulate_folded_line(b.project.driver, unstuffed, 10.0)
    assert np.all(np.isfinite(first.response_db))
    assert not np.allclose(first.response_db, second.response_db)
