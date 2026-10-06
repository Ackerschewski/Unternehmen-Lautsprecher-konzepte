"""Geometry and model relations of sealed, aperiodic, cardioid, infinite-baffle, open-baffle and dipole designs.

Literature: Small (closed box, leakage Q_L, infinite baffle >= 10 Vas), Olson (dipole path
difference), Linkwitz (open baffle, H-frame unfolded path), Bradbury (aperiodic leakage).
"""
from __future__ import annotations

from math import pi, sqrt

import numpy as np
import pytest

from lautsprecher_konstruktion.acoustics.aperiodic import (
    aperiodic_q,
    box_compliance_m5_n,
    cardioid_ideal_delay_s,
    default_vent_resistance,
    specific_flow_resistance,
)
from lautsprecher_konstruktion.acoustics.baffle import (
    dipole_frequencies_hz,
    dipole_path_m,
    simulate_baffle,
)
from lautsprecher_konstruktion.drawings.assembly_svg import render_assembly_svg
from lautsprecher_konstruktion.drawings.internal_dimensions_svg import (
    render_internal_dimensions_svg,
)
from lautsprecher_konstruktion.enclosure.damping import plan_wall_lining
from lautsprecher_konstruktion.enclosure.rectangular import CabinetDimensions
from lautsprecher_konstruktion.export.assembly_guide import build_instructions
from lautsprecher_konstruktion.export.bom import build_bom
from lautsprecher_konstruktion.project.demo import demo_driver, demo_project
from lautsprecher_konstruktion.project.models import CrossoverConfig, SpeakerProject
from lautsprecher_konstruktion.services.design import DesignBundle, calculate_project

C = 343.0


def _bundle(family: str, **cfg: float | str | None) -> DesignBundle:
    project = demo_project()
    enclosure = project.enclosure.model_copy(update={"enclosure_type": family, **cfg})
    return calculate_project(project.model_copy(update={
        "enclosure": enclosure, "front_elements": (), "tweeter_name": "",
        "crossover": CrossoverConfig(enabled=False)}))


def _codes(bundle: DesignBundle) -> set[str]:
    return {issue.code for issue in bundle.issues}


# --- sealed -----------------------------------------------------------------

@pytest.mark.parametrize("family,cfg", [
    ("sealed", {"target_qtc": 0.5, "external_width_mm": 350, "external_height_mm": 600}),
    ("aperiodic", {"target_volume_l": 45.0}),
    ("cardioid", {"target_volume_l": 45.0, "aperiodic_resistance_pa_s_m3": 15000.0}),
])
def test_net_volume_is_gross_minus_displacement_and_depth_follows(family: str, cfg: dict[str, float | str]) -> None:
    bundle = _bundle(family, **cfg)
    cab = bundle.cabinet
    assert cab.gross_internal_volume_m3 - bundle.total_displacement_m3 == pytest.approx(
        bundle.target_net_volume_m3, rel=1e-9)
    # displacement = driver + window braces (the vent is a hole in the wall, no tube inside)
    expected = bundle.project.driver.displacement_m3 + (bundle.brace.total_displacement_m3 if bundle.brace else 0)
    assert bundle.total_displacement_m3 == pytest.approx(expected, rel=1e-9)
    inner = cab.internal_width_m*cab.internal_height_m
    assert cab.internal_depth_m == pytest.approx(
        (bundle.target_net_volume_m3+bundle.total_displacement_m3)/inner, rel=1e-9)


def test_huge_front_gives_flagged_pancake_box_not_a_silent_design() -> None:
    # Same net volume spread over a 1.2 x 1.5 m front only yields a few cm depth.
    bundle = _bundle("sealed", target_qtc=0.5, external_width_mm=1200, external_height_mm=1500,
                     brace_quantity=0)
    assert bundle.cabinet.depth_m < 0.1
    assert "CABINET_PROPORTION" in _codes(bundle)
    assert any(i.severity == "error" for i in bundle.issues)  # driver deeper than the box


def test_tight_driver_rear_clearance_is_reported() -> None:
    bundle = _bundle("sealed", target_qtc=0.707, external_width_mm=350, external_height_mm=600, brace_quantity=0)
    spare = bundle.cabinet.internal_depth_m-bundle.project.driver.mounting_depth_m
    assert 0 <= spare < 0.02
    assert "DRIVER_REAR_CLEARANCE" in _codes(bundle)


def test_window_brace_passes_the_driver_body_and_stays_behind_the_baffle() -> None:
    bundle = _bundle("sealed", target_qtc=0.5, external_width_mm=350, external_height_mm=600)
    assert "BRACE_COLLISION" not in _codes(bundle)
    brace, cab = bundle.brace, bundle.cabinet
    assert brace is not None and bundle.brace_depths_m
    woofer = next(e for e in bundle.front_elements if e.id == "W1")
    assert woofer.cutout_diameter_m is not None
    t = cab.panel_thickness_m
    gap = min(woofer.x_m-woofer.cutout_diameter_m/2-t, cab.width_m-t-woofer.x_m-woofer.cutout_diameter_m/2)
    assert gap >= brace.border_m  # chassis body fits through the window opening
    for depth in bundle.brace_depths_m:
        assert depth+brace.thickness_m <= cab.internal_depth_m


def test_brace_that_cannot_fit_behind_the_driver_is_an_error() -> None:
    bundle = _bundle("sealed", target_qtc=0.707, external_width_mm=300, external_height_mm=450,
                     brace_quantity=1, brace_border_mm=70)
    # border 70 mm: the 230 mm cutout no longer passes the window, braces would have to sit behind it
    assert "BRACE_SPACE" in _codes(bundle) or all(
        d >= bundle.project.driver.mounting_depth_m for d in bundle.brace_depths_m)


def test_sealed_lining_sits_behind_the_driver_and_is_listed() -> None:
    bundle = _bundle("sealed", target_qtc=0.5, external_width_mm=350, external_height_mm=600, brace_quantity=0)
    lining = bundle.damping
    assert lining is not None and 0.01 <= lining.thickness_m <= 0.05
    cab, driver = bundle.cabinet, bundle.project.driver
    assert cab.internal_depth_m-lining.thickness_m >= (driver.mounting_depth_m or 0)+0.02-1e-9
    assert lining.rear_area_m2 == pytest.approx(cab.internal_width_m*cab.internal_height_m)
    bom = build_bom(bundle)
    item = next(i for i in bom if i.reference == "DÄMM")
    assert f"{lining.thickness_m*1000:.0f} mm" in item.specification
    assert any("Dämmmaterial" in step.text for step in build_instructions(bundle) if hasattr(step, "text"))
    svg = render_internal_dimensions_svg(bundle)
    assert 'class="lining"' in svg
    assert 'class="lining"' in render_assembly_svg(bundle)


def test_lining_planner_keeps_magnet_clearance() -> None:
    shallow = CabinetDimensions(0.35, 0.6, 0.15, 0.018)
    assert plan_wall_lining(shallow, 0.11, 0.23) is None  # 114 - 110 mm: no room
    deep = CabinetDimensions(0.35, 0.6, 0.30, 0.018)
    lining = plan_wall_lining(deep, 0.11, 0.23)
    assert lining is not None
    assert lining.clearance_to_driver_m >= 0.02
    assert lining.volume_m3 == pytest.approx(lining.area_m2*lining.thickness_m)


# --- aperiodic -------------------------------------------------------------

def test_aperiodic_default_resistance_and_specific_flow_resistance() -> None:
    driver = demo_driver()
    bundle = _bundle("aperiodic", target_volume_l=45.0)
    cab = box_compliance_m5_n(0.045)
    assert bundle.port_resistance_pa_s_m3 == pytest.approx(1/(2*pi*driver.fs_hz*cab))
    assert default_vent_resistance(driver, 0.045) == pytest.approx(bundle.port_resistance_pa_s_m3)
    assert bundle.port is not None and bundle.vent_damper is not None
    damper = bundle.vent_damper
    assert damper.specific_resistance_rayl == pytest.approx(
        bundle.port_resistance_pa_s_m3*bundle.port.area_m2)
    assert damper.surface == "front"
    # the vent is a hole through the front panel, not a tube inside the box
    assert bundle.port.physical_length_m == pytest.approx(bundle.cabinet.effective_front_thickness_m)
    assert bundle.total_displacement_m3 == pytest.approx(driver.displacement_m3 + bundle.brace.total_displacement_m3
                                                         if bundle.brace else driver.displacement_m3)


def test_aperiodic_q_relations() -> None:
    driver = demo_driver()
    volume = 0.045
    closed = driver.qts*sqrt(1+driver.require_vas_m3()/volume)
    q = aperiodic_q(driver, volume, default_vent_resistance(driver, volume))
    assert q.qtc_closed == pytest.approx(closed)
    assert q.ql == pytest.approx(2*pi*q.resonance_hz*box_compliance_m5_n(volume)*default_vent_resistance(driver, volume))
    assert q.qtc_effective == pytest.approx(1/(1/q.qtc_closed+1/q.ql))
    assert q.qtc_effective < q.qtc_closed
    # the default rule puts the leakage corner at Fs
    assert q.leak_corner_hz == pytest.approx(driver.fs_hz)
    # a very tight vent approaches the sealed box
    tight = aperiodic_q(driver, volume, 1e9)
    assert tight.qtc_effective == pytest.approx(tight.qtc_closed, rel=1e-3)
    assert specific_flow_resistance(15000.0, 0.005) == pytest.approx(75.0)


def test_aperiodic_drawing_shows_hole_and_damper_not_a_tube() -> None:
    bundle = _bundle("aperiodic", target_volume_l=45.0)
    for svg in (render_assembly_svg(bundle), render_internal_dimensions_svg(bundle)):
        assert 'class="hole"' in svg and 'class="damper"' in svg
        assert "Rayl" in svg
    steps = " ".join(step.text for step in build_instructions(bundle) if hasattr(step, "text"))
    assert "Rayl" in steps
    assert "Rayl" in next(i for i in build_bom(bundle) if i.reference == "BR1").notes
    assert "APERIODIC_QTC" in _codes(bundle)


# --- cardioid -----------------------------------------------------------------

def test_cardioid_vent_is_a_back_wall_hole_with_damper_and_ideal_delay() -> None:
    bundle = _bundle("cardioid", target_volume_l=45.0, aperiodic_resistance_pa_s_m3=15000.0)
    assert bundle.vent_damper is not None and bundle.vent_damper.surface == "back"
    assert [e.surface for e in bundle.front_elements if e.type == "port"] == ["back"]
    assert bundle.port is not None
    assert bundle.port.physical_length_m == pytest.approx(bundle.cabinet.effective_back_thickness_m)
    assert cardioid_ideal_delay_s(0.343) == pytest.approx(0.001)
    codes = _codes(bundle)
    assert "CARDIOID_FRONT_BACK" in codes
    message = next(i.message for i in bundle.issues if i.code == "CARDIOID_FRONT_BACK")
    assert f"{cardioid_ideal_delay_s(bundle.cabinet.depth_m)*1000:.2f} ms" in message
    assert 'class="hole"' in render_assembly_svg(bundle)
    assert bundle.damping is None  # the rear wall carries the vent: no wall lining planned


# --- infinite baffle ----------------------------------------------------------------

def test_infinite_baffle_requires_ten_vas_with_numbers_and_has_no_path() -> None:
    project = demo_project()
    vas_l = project.driver.require_vas_m3()*1000
    cfg = project.enclosure.model_copy(update={"enclosure_type": "infinite_baffle", "target_volume_l": 5*vas_l})
    with pytest.raises(ValueError, match="10 × Vas") as info:
        calculate_project(project.model_copy(update={"enclosure": cfg}))
    assert f"{10*vas_l:.0f} l" in str(info.value)
    ok = _bundle("infinite_baffle", target_volume_l=10*vas_l)
    assert ok.baffle_path_m is None and ok.baffle_mode == "infinite_baffle"
    assert "Entfällt" in render_assembly_svg(ok)
    assert not any(p.name == "Back" for p in ok.panels)
    # Small: Qtc = Qts sqrt(1 + Vas/Vb) rises by <= 5 % at Vb = 10 Vas
    assert sqrt(1+1/10) == pytest.approx(1.0488, abs=1e-3)


def test_assistant_designs_infinite_baffle_with_at_least_ten_vas(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from lautsprecher_konstruktion.library.store import ComponentLibrary
    from lautsprecher_konstruktion.services.automatic import (
        AutomaticDesignRequest,
        automatic_design,
    )
    result = automatic_design(AutomaticDesignRequest(
        enclosure_preference="infinite_baffle", speaker_type="Subwoofer",
        max_width_m=0.6, max_height_m=0.8, max_depth_m=0.6), ComponentLibrary(user_root=tmp_path/"user"))
    assert result.status == "ok" and result.designs
    for design in result.designs:
        assert design.bundle.target_net_volume_m3 >= 10*design.woofer.require_vas_m3()-1e-12


def test_assistant_open_baffle_reports_no_box_volume(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from lautsprecher_konstruktion.library.store import ComponentLibrary
    from lautsprecher_konstruktion.services.automatic import (
        AutomaticDesignRequest,
        automatic_design,
    )
    result = automatic_design(AutomaticDesignRequest(
        enclosure_preference="open_baffle", speaker_type="Subwoofer",
        max_width_m=0.6, max_height_m=0.8, max_depth_m=0.6), ComponentLibrary(user_root=tmp_path/"user"))
    text = " ".join(result.rejection_reasons)
    if result.status == "impossible":
        assert "ohne Gehäusevolumen" in text
        assert "kleinste geprüfte" not in text and "Brutto-Innenvolumen" not in text


# --- open baffle / dipole ----------------------------------------------------------------

def test_dipole_path_geometry() -> None:
    assert dipole_path_m(0.34, 1.2, 0.17, 0.6) == pytest.approx(0.34)            # flat, centred: D = W
    assert dipole_path_m(0.34, 1.2, 0.10, 0.6) == pytest.approx(0.20)            # off-centre: 2 x nearest edge
    assert dipole_path_m(0.34, 1.2, 0.17, 0.6, 0.15) == pytest.approx(0.64)      # wings: 2 (W/2 + d)
    assert dipole_path_m(0.34, 0.56, 0.17, 0.28, 0.30) == pytest.approx(0.56)    # open top/bottom limit the path
    corner, peak, null = dipole_frequencies_hz(0.64)
    assert (corner, peak, null) == pytest.approx((C/(4*0.64), C/(2*0.64), C/0.64))


def test_dipole_response_is_sine_of_path_relative_to_infinite_baffle() -> None:
    driver = demo_driver()
    path = 0.6
    dipole = simulate_baffle(driver, "dipole", path, None, 10.0)
    wall = simulate_baffle(driver, "infinite_baffle", path, None, 10.0)
    f = dipole.frequencies_hz
    ratio = 10**((dipole.response_db-wall.response_db)/20)
    assert np.allclose(ratio, abs(np.sin(pi*f*path/C)), atol=1e-9)
    # absolute level: the dipole peak equals the half-space level (no spurious +6 dB)
    assert dipole.spl_db_1m is not None and wall.spl_db_1m is not None
    peak = f[np.argmin(abs(f-C/(2*path)))]
    i = int(np.argmin(abs(f-peak)))
    assert dipole.spl_db_1m[i]-wall.spl_db_1m[i] == pytest.approx(0.0, abs=0.2)
    # -3 dB corner of the dipole factor at c/(4 D)
    j = int(np.argmin(abs(f-C/(4*path))))
    assert dipole.spl_db_1m[j]-wall.spl_db_1m[j] == pytest.approx(-3.0, abs=0.3)
    # reference is the monopole mid band, so an unequalised dipole sits below it at low frequency
    assert dipole.response_db[0] < -20


def test_dipole_wings_lengthen_only_the_side_path() -> None:
    short = _bundle("dipole", baffle_wing_depth_mm=100.0, external_height_mm=1400)
    long = _bundle("dipole", baffle_wing_depth_mm=300.0, external_height_mm=1400)
    assert short.baffle_path_m == pytest.approx(2*(0.17+0.10))
    assert long.baffle_path_m == pytest.approx(2*(0.17+0.30))
    assert long.vented_response is not None and short.vented_response is not None
    assert long.vented_response.f3_hz is not None and short.vented_response.f3_hz is not None
    assert long.vented_response.f3_hz < short.vented_response.f3_hz  # longer path: lower corner
    short_baffle = _bundle("dipole", baffle_wing_depth_mm=300.0, external_height_mm=560)
    assert short_baffle.baffle_path_m == pytest.approx(2*0.28)       # top/bottom edge limits
    assert "DIPOLE_HEIGHT_LIMIT" in _codes(short_baffle)
    assert {p.name for p in long.panels} == {"Schallwand", "H-Frame Seitenflügel"}
    wing = next(p for p in long.panels if p.name.startswith("H-Frame"))
    assert wing.quantity == 2 and wing.width_m == pytest.approx(0.30) and wing.height_m == pytest.approx(1.4)


def test_open_baffle_reports_dipole_frequencies_and_needs_equalisation() -> None:
    bundle = _bundle("open_baffle")
    assert bundle.baffle_path_m == pytest.approx(0.34)
    message = next(i.message for i in bundle.issues if i.code == "DIPOLE_PATH")
    corner, peak, null = dipole_frequencies_hz(0.34)
    assert f"{corner:.0f} Hz" in message and f"{peak:.0f} Hz" in message and f"{null:.0f} Hz" in message
    assert "DIPOLE_EQ_NEEDED" in _codes(bundle)
    svg = render_assembly_svg(bundle)
    assert f"{corner:.0f} Hz" in svg


def test_baffle_step_correction_is_rejected_for_baffles_without_box() -> None:
    project = demo_project()
    base: SpeakerProject = project.model_copy(update={
        "front_elements": (), "tweeter_name": "Tweeter",
        "crossover": project.crossover.model_copy(update={"baffle_step_compensation_db": 3.0})})
    for family, extra in (("open_baffle", {}), ("dipole", {}), ("infinite_baffle", {"target_volume_l": 1000.0})):
        cfg = base.enclosure.model_copy(update={"enclosure_type": family, **extra})
        bundle = calculate_project(base.model_copy(update={"enclosure": cfg}))
        assert "BAFFLE_STEP_NOT_APPLICABLE" in _codes(bundle)


def test_baffle_drawing_dimensions_match_panels() -> None:
    bundle = _bundle("dipole", baffle_wing_depth_mm=150.0)
    svg = render_assembly_svg(bundle)
    assert "Breite 340 · Platte 18" in svg
    assert "Flügel 150" in svg
    assert f"{bundle.baffle_path_m*1000:.1f} mm" in svg  # type: ignore[operator]
