"""TASK-0029 workstream D: acoustic treatment as a project object with placement rules."""
from __future__ import annotations

import pytest

from lautsprecher_konstruktion.enclosure.treatment import (
    AcousticTreatment,
    TreatmentKind,
    check_treatments,
)
from lautsprecher_konstruktion.export.assembly_guide import build_instructions
from lautsprecher_konstruktion.export.bom import build_bom
from lautsprecher_konstruktion.project.demo import demo_project
from lautsprecher_konstruktion.project.models import CrossoverConfig, SpeakerProject
from lautsprecher_konstruktion.services.design import calculate_project


def _t(**kw: object) -> AcousticTreatment:
    base: dict[str, object] = {"id": "T1", "kind": TreatmentKind.WALL_LINING, "area_m2": 0.2, "thickness_m": 0.03}
    base.update(kw)
    return AcousticTreatment.model_validate(base)


def _project(enclosure: str, treatments: tuple[AcousticTreatment, ...]) -> SpeakerProject:
    base = demo_project()
    config = base.enclosure.model_copy(update={"enclosure_type": enclosure, "target_qtc": 0.5, "external_width_mm": 350,
                                               "external_height_mm": 600, "brace_quantity": 0})
    return base.model_copy(update={"treatments": treatments, "enclosure": config, "front_elements": (),
                                   "tweeter_name": "", "crossover": CrossoverConfig(enabled=False)})


def test_derived_values_and_unknown_price_stays_unknown() -> None:
    t = _t(density_kg_m3=30.0)
    assert t.volume_m3 == pytest.approx(0.006) and t.mass_kg == pytest.approx(0.18)
    assert t.cost_eur is None
    assert _t(unit_price_eur_per_m2=10.0).cost_eur == pytest.approx(2.0)


def test_port_blocking_fill_is_an_error_in_vented_box() -> None:
    issues = check_treatments("bass_reflex", (_t(kind=TreatmentKind.FILL, position="port"),))
    assert [i.severity for i in issues] == ["error"] and "Port" in issues[0].message
    ok = check_treatments("bass_reflex", (_t(position="rear"),))
    assert ok == []


def test_vent_fill_only_for_aperiodic_or_cardioid() -> None:
    assert check_treatments("sealed", (_t(kind=TreatmentKind.VENT_FILL, position="vent"),))[0].severity == "error"
    assert check_treatments("aperiodic", (_t(kind=TreatmentKind.VENT_FILL, position="vent"),)) == []


def test_bandpass_requires_chamber_position() -> None:
    assert check_treatments("bandpass_4", (_t(position="rear"),))[0].code == "TREATMENT_CHAMBER"
    assert check_treatments("bandpass_4", (_t(position="chamber:rear"),)) == []


def test_transmission_line_claims_no_modelled_effect() -> None:
    (issue,) = check_treatments("transmission_line_closed", (_t(kind=TreatmentKind.TL_SEGMENT, position="segment:2"),))
    assert issue.severity == "info" and "keine Dämpfungswirkung" in issue.message


def test_planner_lining_is_a_treatment_and_user_treatment_reaches_bom_guide_and_warnings() -> None:
    bundle = calculate_project(_project("sealed", (_t(id="T9", kind=TreatmentKind.LOCAL_ABSORBER, position="top"),)))
    ids = [t.id for t in bundle.treatments]
    assert "T9" in ids and any(t.derived for t in bundle.treatments)
    bom = build_bom(bundle)
    assert any(item.reference == "T9" for item in bom)
    (own,) = [item for item in bom if item.reference == "T9"]
    assert own.unit_price_eur is None  # the user gave no price: it stays unknown
    assert all(item.price_kind == "Planpreis" for item in bom
               if item.category == "Dämmung" and item.unit_price_eur is not None)  # catalogue prices are labelled
    guide = " ".join(str(step) for step in build_instructions(bundle))
    assert "Lokaler Absorber" in guide


def test_blocking_treatment_surfaces_in_bundle_warnings() -> None:
    bundle = calculate_project(_project("bass_reflex", (_t(kind=TreatmentKind.FILL, position="port"),)))
    assert any(i.code == "TREATMENT_PORT_BLOCKED" for i in bundle.issues)
    assert any("Port" in w for w in bundle.warnings)


def test_treatments_round_trip_in_project_file() -> None:
    project = _project("sealed", (_t(density_kg_m3=25.0, note="Rückwand"),))
    restored = SpeakerProject.model_validate_json(project.model_dump_json())
    assert restored.treatments == project.treatments


def test_user_treatment_is_drawn_in_both_section_drawings_and_listed() -> None:
    from lautsprecher_konstruktion.drawings.assembly_svg import render_assembly_svg
    from lautsprecher_konstruktion.drawings.internal_dimensions_svg import (
        render_internal_dimensions_svg,
    )
    bundle = calculate_project(_project("sealed", (_t(id="T9", kind=TreatmentKind.LOCAL_ABSORBER, position="top", area_m2=0.05),)))
    plain = calculate_project(_project("sealed", ()))
    for render in (render_internal_dimensions_svg, render_assembly_svg):
        with_t, without = render(bundle), render(plain)
        assert with_t.count('class="lining"') == without.count('class="lining"') + 1
        assert ">T9<" in with_t
    assert "T9 Lokaler Absorber" in render_internal_dimensions_svg(bundle)
