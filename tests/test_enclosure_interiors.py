"""Interior geometry of port, bandpass, isobaric and passive-radiator families.

These tests check what is built where (chamber assignment, depth spans, port
protrusion, driver orientation), not just that a design calculates.
"""
from __future__ import annotations

import re
from math import pi

import numpy as np
import pytest

from lautsprecher_konstruktion.acoustics.bandpass import simulate_bandpass
from lautsprecher_konstruktion.drawings.assembly_svg import render_assembly_svg
from lautsprecher_konstruktion.drawings.internal_dimensions_svg import (
    render_internal_dimensions_svg,
)
from lautsprecher_konstruktion.enclosure.interior import (
    InteriorGeometry,
    element_span_m,
    port_protrusion_m,
)
from lautsprecher_konstruktion.enclosure.isobaric import make_coupler
from lautsprecher_konstruktion.enclosure.passive_radiator import design_passive_radiator
from lautsprecher_konstruktion.enclosure.ports import (
    round_port,
    round_port_diameter_for_length_m,
    slot_port,
)
from lautsprecher_konstruktion.project.demo import demo_driver, demo_project
from lautsprecher_konstruktion.project.models import CrossoverConfig, SpeakerProject
from lautsprecher_konstruktion.services.design import DesignBundle, calculate_project


def _project(kind: str, **updates: object) -> SpeakerProject:
    project = demo_project()
    return project.model_copy(update={
        "front_elements": (), "tweeter_name": "", "crossover": CrossoverConfig(enabled=False),
        "enclosure": project.enclosure.model_copy(update={"enclosure_type": kind, **updates})})


def _bundle(kind: str, **updates: object) -> DesignBundle:
    return calculate_project(_project(kind, **updates))


BP4 = {"target_volume_l": 40, "rear_volume_l": 40, "tuning_hz": 50, "port_diameter_mm": 60,
       "external_width_mm": 350, "external_height_mm": 600}
BP6_PARALLEL = {"target_volume_l": 40, "rear_volume_l": 40, "tuning_hz": 35, "rear_tuning_hz": 35,
                "port_diameter_mm": 50, "rear_port_diameter_mm": 50,
                "external_width_mm": 400, "external_height_mm": 1000}
BP6_SERIES = {"target_volume_l": 20, "rear_volume_l": 40, "tuning_hz": 50, "rear_tuning_hz": 40,
              "port_diameter_mm": 50, "rear_port_diameter_mm": 50,
              "external_width_mm": 350, "external_height_mm": 700}


def _errors(bundle: DesignBundle) -> list[str]:
    return [i.code for i in bundle.issues if i.severity == "error"]


def _geometry(bundle: DesignBundle) -> InteriorGeometry:
    cab = bundle.cabinet
    return InteriorGeometry(cab.internal_depth_m, cab.effective_front_thickness_m,
                            cab.effective_back_thickness_m, cab.panel_thickness_m,
                            bundle.partition_front_depth_m)


# --- port formulae and German errors -----------------------------------------------------

def test_port_length_matches_helmholtz_with_end_correction() -> None:
    port = round_port(box_volume_m3=0.045, tuning_hz=35, diameter_m=0.08)
    area = pi*0.04**2
    effective = 343.0**2*area/((2*pi*35)**2*0.045)
    assert port.effective_length_m == pytest.approx(effective)
    # one flanged (0.85 a) plus one free (0.61 a) end: 1.46 a = 0.73 D
    assert port.physical_length_m == pytest.approx(effective-0.73*0.08)


def test_diameter_for_length_inverts_round_port() -> None:
    for volume, fb, diameter in ((0.045, 35, 0.08), (0.12, 25, 0.1), (0.02, 60, 0.05)):
        length = round_port(box_volume_m3=volume, tuning_hz=fb, diameter_m=diameter).physical_length_m
        assert round_port_diameter_for_length_m(box_volume_m3=volume, tuning_hz=fb,
                                                length_m=length) == pytest.approx(diameter)


def test_non_positive_port_length_gives_german_error_with_minimum_diameter() -> None:
    with pytest.raises(ValueError, match=r"Der berechnete Port benötigt.*mindestens \d+ mm"):
        _bundle("bass_reflex", target_volume_l=120, tuning_hz=55, port_diameter_mm=75,
                external_width_mm=400, external_height_mm=1000)
    minimum = round_port_diameter_for_length_m(box_volume_m3=0.12, tuning_hz=55)
    # a larger port is a valid design, and the stated limit is the zero-length boundary
    assert round_port(box_volume_m3=0.12, tuning_hz=55, diameter_m=minimum*1.02).physical_length_m > 0
    with pytest.raises(ValueError, match="Der (berechnete Port|Rundport)"):
        round_port(box_volume_m3=0.12, tuning_hz=55, diameter_m=minimum*0.98)
    ok = _bundle("bass_reflex", target_volume_l=120, tuning_hz=55, port_diameter_mm=130,
                 external_width_mm=400, external_height_mm=1000)
    assert ok.port is not None and ok.port.physical_length_m > 0


def test_slot_port_non_positive_length_message_is_german() -> None:
    with pytest.raises(ValueError, match="Der (berechnete Port|Rundport)"):
        slot_port(box_volume_m3=0.2, tuning_hz=50, width_m=0.05, height_m=0.03)


def test_port_too_long_for_chamber_reports_numbers_and_remedy() -> None:
    bundle = _bundle("bandpass_4", target_volume_l=25, rear_volume_l=40, tuning_hz=50,
                     port_diameter_mm=80, external_width_mm=400, external_height_mm=700)
    issue = next(i for i in bundle.issues if i.code == "PORT_BACK_WALL")
    assert "Frontkammer" in issue.message and "mm" in issue.message
    assert "Rund-Ø höchstens" in issue.message
    # the suggested diameter really fits the front chamber
    assert bundle.port is not None and bundle.partition_front_depth_m is not None
    d_max = round_port_diameter_for_length_m(
        box_volume_m3=0.025, tuning_hz=50,
        length_m=bundle.partition_front_depth_m+bundle.cabinet.effective_front_thickness_m)
    assert d_max < 0.08


# --- bass reflex -----------------------------------------------------------------------

def test_bass_reflex_port_length_includes_front_panel_and_stays_clear_of_driver() -> None:
    bundle = _bundle("bass_reflex", target_volume_l=45, tuning_hz=35, port_diameter_mm=80,
                     external_width_mm=340, external_height_mm=560)
    assert not _errors(bundle) and bundle.port is not None
    geometry = _geometry(bundle)
    port = next(e for e in bundle.front_elements if e.id == "BR1")
    assert port.surface == "front" and port.mounting_depth_m == pytest.approx(bundle.port.physical_length_m)
    z0, z1 = element_span_m(port, geometry)
    assert z0 == 0.0
    assert z1 == pytest.approx(bundle.port.physical_length_m-geometry.front_wall_m)
    assert z1 < geometry.internal_depth_m
    driver = next(e for e in bundle.front_elements if e.id == "W1")
    assert (driver.y_m-driver.outer_diameter_m/2) > (port.y_m+port.outer_diameter_m/2)


def test_displacement_counts_only_the_port_part_inside_the_cabinet() -> None:
    bundle = _bundle("bass_reflex", target_volume_l=45, tuning_hz=35, port_diameter_mm=80,
                     external_width_mm=340, external_height_mm=560, brace_quantity=0)
    assert bundle.port is not None
    wall = bundle.cabinet.effective_front_thickness_m
    inside = bundle.port.area_m2*(bundle.port.physical_length_m-wall)
    expected = bundle.project.driver.displacement_m3+inside
    assert bundle.total_displacement_m3 == pytest.approx(expected)
    gross = bundle.cabinet.gross_internal_volume_m3
    assert gross == pytest.approx(bundle.target_net_volume_m3+bundle.total_displacement_m3)


def test_slot_port_walls_start_behind_the_front_panel_and_clear_the_brace() -> None:
    bundle = _bundle("bass_reflex", target_volume_l=45, tuning_hz=35, port_type="slot",
                     external_width_mm=340, external_height_mm=560)
    assert bundle.port is not None and bundle.port.shape == "slot"
    wall = bundle.cabinet.effective_front_thickness_m
    channel = [p for p in bundle.panels if p.name.startswith("Slotkanal")]
    assert channel and all(p.height_m == pytest.approx(bundle.port.physical_length_m-wall)
                           for p in channel if p.name.endswith("Deckel/Boden"))
    assert "BRACE_COLLISION" not in _errors(bundle)
    slot = next(e for e in bundle.front_elements if e.id == "BR1")
    t = bundle.cabinet.panel_thickness_m
    lowest_wall_edge = slot.y_m-slot.height_m/2-t
    assert lowest_wall_edge >= t+bundle.project.enclosure.brace_border_mm/1000


# --- bandpass --------------------------------------------------------------------------

def test_bandpass_4_driver_on_partition_sealed_rear_vented_front() -> None:
    bundle = _bundle("bandpass_4", **BP4)
    assert not _errors(bundle)
    driver = next(e for e in bundle.front_elements if e.id == "W1")
    port = next(e for e in bundle.front_elements if e.id == "BR1")
    assert driver.surface == "partition" and port.surface == "front"
    assert bundle.rear_port is None  # rear chamber sealed
    cab, t = bundle.cabinet, bundle.cabinet.panel_thickness_m
    front_depth = bundle.partition_front_depth_m
    assert front_depth is not None
    # chamber volumes follow from depth and inner cross-section (+ what sits inside)
    area = cab.internal_width_m*cab.internal_height_m
    assert front_depth*area == pytest.approx(0.040+bundle.port.area_m2*(
        bundle.port.physical_length_m-cab.effective_front_thickness_m))
    rear_depth = cab.internal_depth_m-front_depth-t
    brace_volume = bundle.brace.total_displacement_m3 if bundle.brace else 0.0
    assert rear_depth*area == pytest.approx(0.040+bundle.project.driver.displacement_m3+brace_volume)
    # the front port stays in the front chamber and does not reach the partition driver
    _, z1 = element_span_m(port, _geometry(bundle))
    assert z1 < front_depth
    # the motor points into the rear (sealed) chamber and fits there
    d0, d1 = element_span_m(driver, _geometry(bundle))
    assert d0 == pytest.approx(front_depth) and d1 <= cab.internal_depth_m


def test_bandpass_drawing_shows_driver_cone_in_front_chamber_and_motor_in_rear() -> None:
    bundle = _bundle("bandpass_4", **BP4)
    svg = render_internal_dimensions_svg(bundle)
    scale_x = _section_scale(svg, bundle)
    front_x = 90.0+bundle.cabinet.effective_front_thickness_m*1000*scale_x
    partition_x = front_x+bundle.partition_front_depth_m*1000*scale_x
    paths = _feature_paths(svg)
    driver = _path_with_label(svg, paths, "W1")
    # wide end (cone/flange) sits on the partition plane, narrow end (motor) lies behind it
    assert driver[0] == pytest.approx(partition_x, abs=1.0)
    assert driver[2] > driver[0]
    port_rect = _port_rect(svg, "BR1")
    assert port_rect[0] == pytest.approx(90.0, abs=1.0)  # starts at the outer face of the front
    assert port_rect[0]+port_rect[2] < partition_x  # ends inside the front chamber


def test_bandpass_6_parallel_rear_port_exits_through_back_wall_into_rear_chamber() -> None:
    bundle = _bundle("bandpass_6_parallel", **BP6_PARALLEL)
    assert not _errors(bundle)
    rear = next(e for e in bundle.front_elements if e.id == "BR2")
    front = next(e for e in bundle.front_elements if e.id == "BR1")
    assert front.surface == "front" and rear.surface == "back"
    geometry = _geometry(bundle)
    z0, z1 = element_span_m(rear, geometry)
    assert z1 == pytest.approx(geometry.internal_depth_m)
    assert z0 > bundle.partition_front_depth_m+bundle.cabinet.panel_thickness_m
    assert bundle.rear_port is not None
    assert z1-z0 == pytest.approx(port_protrusion_m(bundle.rear_port.physical_length_m,
                                                    geometry.back_wall_m))
    # rear port clears the window brace border
    assert rear.y_m-rear.outer_diameter_m/2 >= (
        bundle.cabinet.panel_thickness_m+bundle.project.enclosure.brace_border_mm/1000)


def test_bandpass_6_series_internal_port_passes_through_partition_into_rear_chamber() -> None:
    bundle = _bundle("bandpass_6_series", **BP6_SERIES)
    assert not _errors(bundle)
    internal = next(e for e in bundle.front_elements if e.id == "BR2")
    external = next(e for e in bundle.front_elements if e.id == "BR1")
    assert internal.surface == "partition" and external.surface == "front"
    geometry = _geometry(bundle)
    z0, z1 = element_span_m(internal, geometry)
    assert z0 == pytest.approx(bundle.partition_front_depth_m)  # starts at the partition's front face
    assert z1 <= geometry.internal_depth_m
    # external port is in the front chamber, shorter than the chamber
    assert element_span_m(external, geometry)[1] < bundle.partition_front_depth_m
    driver = next(e for e in bundle.front_elements if e.id == "W1")
    assert abs(driver.y_m-internal.y_m) > (driver.outer_diameter_m+internal.outer_diameter_m)/2 - 1e-9


def test_bandpass_4_slopes_follow_second_order_high_and_low_pass() -> None:
    response = _bundle("bandpass_4", **BP4).vented_response
    assert response is not None
    f, db = response.frequencies_hz, response.response_db

    def slope(f1: float, f2: float) -> float:
        i, j = int(np.argmin(abs(f-f1))), int(np.argmin(abs(f-f2)))
        return float((db[j]-db[i])/np.log2(f[j]/f[i]))

    assert slope(10, 12) == pytest.approx(12, abs=2.5)  # +12 dB/oct below the passband
    assert slope(300, 500) == pytest.approx(-12, abs=3)  # -12 dB/oct above


def test_rear_port_path_delay_changes_only_the_summed_response() -> None:
    bundle = _bundle("bandpass_6_parallel", **BP6_PARALLEL)
    assert bundle.port is not None and bundle.rear_port is not None
    driver = bundle.project.driver
    base = simulate_bandpass(driver, 0.04, 0.04, bundle.port, rear_port=bundle.rear_port)
    delayed = simulate_bandpass(driver, 0.04, 0.04, bundle.port, rear_port=bundle.rear_port,
                                rear_port_path_m=bundle.cabinet.depth_m)
    assert not np.allclose(base.response_db, delayed.response_db)
    assert base.front_port_velocity_m_s is not None and delayed.front_port_velocity_m_s is not None
    assert np.allclose(base.front_port_velocity_m_s, delayed.front_port_velocity_m_s)
    assert np.allclose(base.rear_port_velocity_m_s, delayed.rear_port_velocity_m_s)


# --- isobaric ----------------------------------------------------------------------------

def _coupler_paths(svg: str) -> tuple[tuple[float, ...], tuple[float, ...]]:
    paths = _feature_paths(svg)
    assert len(paths) >= 2
    return paths[-2], paths[-1]  # W1 then W2


def test_tandem_isobaric_w2_motor_points_rearwards() -> None:
    bundle = _bundle("isobaric_vented", target_volume_l=60, tuning_hz=30, port_diameter_mm=80,
                     external_width_mm=400, external_height_mm=600)
    assert not _errors(bundle) and bundle.coupler is not None
    coupler, driver = bundle.coupler, bundle.project.driver
    assert not coupler.w2_reversed and coupler.w2_extent_m == pytest.approx(driver.mounting_depth_m)
    assert coupler.length_m == pytest.approx(driver.mounting_depth_m+0.02)
    assert coupler.rear_extent_m == pytest.approx(
        coupler.length_m+coupler.ring_thickness_m+driver.mounting_depth_m)
    w1, w2 = _coupler_paths(render_internal_dimensions_svg(bundle))
    assert w1[2] > w1[0] and w2[2] > w2[0]  # both motors drawn towards the rear


def test_push_pull_pair_is_magnet_to_magnet_with_longer_coupler() -> None:
    kwargs = {"target_qtc": 0.707, "external_width_mm": 380, "external_height_mm": 380}
    push_pull = _bundle("compound_push_pull", **kwargs)
    tandem = _bundle("isobaric_sealed", **kwargs)
    assert push_pull.coupler is not None and tandem.coupler is not None
    k, d = push_pull.coupler, push_pull.project.driver
    assert k.w2_reversed and k.w2_extent_m == pytest.approx(-d.mounting_depth_m)
    # coupler holds both motors: W1 depth + W2 depth - ring + gap
    assert k.length_m == pytest.approx(d.mounting_depth_m*2-k.ring_thickness_m+0.02)
    assert k.rear_extent_m == pytest.approx(k.length_m+k.ring_thickness_m)
    assert k.rear_extent_m < tandem.coupler.rear_extent_m+0.05
    # both motors lie inside the coupler envelope: the driver volume is not counted twice
    assert push_pull.total_displacement_m3 == pytest.approx(
        k.displaced_volume_m3+push_pull.brace.total_displacement_m3
        + (push_pull.project.enclosure.additional_displacement_l/1000))
    w1, w2 = _coupler_paths(render_internal_dimensions_svg(push_pull))
    assert w1[2] > w1[0]  # W1 motor towards the rear
    assert w2[2] < w2[0]  # W2 reversed: its motor reaches forwards into the coupler
    assert 'W2 umgedreht' in render_assembly_svg(push_pull)
    # the drawn motors do not overlap each other (gap between the magnet ends)
    assert w1[2] < w2[2]


def test_coupler_helper_rejects_missing_driver_depth() -> None:
    driver = demo_driver().model_copy(update={"mounting_depth_m": None})
    with pytest.raises(ValueError, match="Einbautiefe"):
        make_coupler(driver, 0.018, 0.02)


def test_isobaric_depth_error_names_the_cross_section_limit() -> None:
    bundle = _bundle("isobaric_sealed", target_qtc=0.707, external_width_mm=400, external_height_mm=500)
    issue = next(i for i in bundle.issues if i.code == "ISOBARIC_DEPTH")
    assert "Innenquerschnitt höchstens" in issue.message


def test_isobaric_coupler_too_wide_error_has_numbers() -> None:
    with pytest.raises(ValueError, match=r"mindestens \d+ mm breit"):
        _bundle("isobaric_sealed", target_qtc=0.707, external_width_mm=300, external_height_mm=500)


# --- passive radiator --------------------------------------------------------------------

def test_passive_radiator_sits_on_back_wall_above_brace_border_and_clear_of_driver() -> None:
    bundle = _bundle("passive_radiator", target_volume_l=45, tuning_hz=30,
                     external_width_mm=340, external_height_mm=600)
    assert not _errors(bundle) and bundle.radiator is not None
    pm = next(e for e in bundle.front_elements if e.type == "passive_radiator")
    assert pm.surface == "back"
    assert pm.y_m-pm.cutout_diameter_m/2 >= (
        bundle.cabinet.panel_thickness_m+bundle.project.enclosure.brace_border_mm/1000)
    z0, z1 = element_span_m(pm, _geometry(bundle))
    assert z1 == pytest.approx(bundle.cabinet.internal_depth_m)
    assert z1-z0 == pytest.approx(bundle.radiator.mounting_depth_m)
    # tuning: Fb = 1/(2 pi sqrt(Map * Ctotal)) reproduces the target
    r, rho, c = bundle.radiator, 1.204, 343.0
    cb = bundle.target_net_volume_m3/(rho*c**2)
    series = 1/(1/cb+1/r.acoustic_compliance_m5_n)
    fb = 1/(2*pi*np.sqrt(r.acoustic_mass_kg_m4*series))
    assert fb == pytest.approx(30.0, rel=1e-6)
    assert r.total_mass_kg == pytest.approx(
        r.acoustic_mass_kg_m4*r.area_m2**2)


def test_passive_radiator_front_and_back_depth_collision_is_reported() -> None:
    bundle = _bundle("passive_radiator", target_volume_l=20, tuning_hz=25,
                     external_width_mm=350, external_height_mm=700)
    assert any(i.code == "DEPTH_COLLISION" for i in bundle.issues)


def test_passive_radiator_sd_larger_than_cutout_is_rejected_in_german() -> None:
    with pytest.raises(ValueError, match="größer als der Ausschnitt"):
        design_passive_radiator(box_volume_m3=0.045, tuning_hz=30, area_m2=0.035, stock_mass_kg=0.06,
                                free_air_fs_hz=20, qms=5, cutout_diameter_m=0.15,
                                mounting_depth_m=0.06, xmax_m=0.012)


def test_passive_radiator_unreachable_tuning_names_the_ceiling() -> None:
    with pytest.raises(ValueError, match=r"Grundmasse.*höchstens \d+\.\d Hz"):
        design_passive_radiator(box_volume_m3=0.045, tuning_hz=35, area_m2=0.035, stock_mass_kg=2,
                                free_air_fs_hz=20, qms=5, cutout_diameter_m=0.23,
                                mounting_depth_m=0.06, xmax_m=0.012)


def test_passive_radiator_displacement_rule_of_thumb() -> None:
    project = _project("passive_radiator", target_volume_l=45, tuning_hz=30,
                       external_width_mm=340, external_height_mm=600, radiator_xmax_mm=2.0)
    bundle = calculate_project(project)
    assert any(i.code == "RADIATOR_DISPLACEMENT" for i in bundle.issues)


# --- helpers for SVG assertions ------------------------------------------------------------

def _section_scale(svg: str, bundle: DesignBundle) -> float:
    d, h = bundle.cabinet.depth_m*1000, bundle.cabinet.height_m*1000
    return min(550/max(d, 1), 360/max(h, 1))


def _feature_paths(svg: str) -> list[tuple[float, ...]]:
    """(x_start, y_start, x_end, ...) of trapezoid feature paths in drawing order."""
    result = []
    for match in re.finditer(r'<path d="M([\d.]+) ([\d.]+)L([\d.]+) ([\d.]+)L([\d.]+) ([\d.]+)L([\d.]+) '
                             r'([\d.]+)Z" class="feature"/>', svg):
        result.append(tuple(float(g) for g in match.groups()))
    return result


def _path_with_label(svg: str, paths: list[tuple[float, ...]], label: str) -> tuple[float, ...]:
    for path in paths:
        if re.search(rf'<text x="{path[0]+6:.1f}" y="[\d.]+" class="dimtext">{label}</text>', svg):
            return path
    raise AssertionError(f"no drawn element {label}")


def _port_rect(svg: str, label: str) -> tuple[float, float, float, float]:
    """x, y, width, height of the feature rectangle that carries the given port label."""
    for match in re.finditer(r'<rect x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)" '
                             r'class="feature"/><text x="([\d.]+)" y="[\d.]+" class="dimtext">'
                             rf'{label}', svg):
        return tuple(float(match.group(i)) for i in range(1, 5))  # type: ignore[return-value]
    raise AssertionError(f"no drawn port {label}")
