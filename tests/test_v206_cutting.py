import os
from pathlib import Path

import pytest

from lautsprecher_konstruktion.enclosure.registry import registry
from lautsprecher_konstruktion.export.assembly_guide import build_instructions, render_markdown
from lautsprecher_konstruktion.export.cutting import (
    CuttingSettings,
    Part,
    _pack,
    collect_parts,
    plan_cutting,
    render_cutting_svg,
    write_cutting_csv,
)
from lautsprecher_konstruktion.export.package import export_project_package
from lautsprecher_konstruktion.export.weight import estimate_weight, plate_volume_m3
from lautsprecher_konstruktion.project.demo import demo_project
from lautsprecher_konstruktion.project.models import CrossoverConfig
from lautsprecher_konstruktion.services.design import calculate_project

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _bundle(**update: object):
    project = demo_project()
    return calculate_project(project.model_copy(update={"enclosure": project.enclosure.model_copy(update=update)}))


def _overlaps(a, b) -> bool:
    return (a.x_mm < b.x_mm + b.width_mm and b.x_mm < a.x_mm + a.width_mm
            and a.y_mm < b.y_mm + b.height_mm and b.y_mm < a.y_mm + a.height_mm)


def test_all_pieces_are_placed_without_overlap_and_inside_the_sheet() -> None:
    bundle = _bundle()
    settings = CuttingSettings.for_material(bundle.project.material, kerf_mm=3.0)
    plan = plan_cutting(bundle, settings)
    assert plan.feasible
    parts = collect_parts(bundle)
    placed = [item for group in plan.groups for sheet in group.sheets for item in sheet.placed]
    assert sorted(item.part.part_id for item in placed) == sorted(part.part_id for part in parts)
    for group in plan.groups:
        for sheet in group.sheets:
            for item in sheet.placed:
                assert item.x_mm >= -1e-9 and item.y_mm >= -1e-9
                assert item.x_mm + item.width_mm <= settings.sheet_width_mm + 1e-6
                assert item.y_mm + item.height_mm <= settings.sheet_height_mm + 1e-6
            for i, first in enumerate(sheet.placed):
                for second in sheet.placed[i + 1:]:
                    assert not _overlaps(first, second)


def test_kerf_is_kept_between_neighbouring_parts() -> None:
    bundle = _bundle()
    plan = plan_cutting(bundle, CuttingSettings.for_material(bundle.project.material, kerf_mm=5.0))
    for group in plan.groups:
        for sheet in group.sheets:
            for i, first in enumerate(sheet.placed):
                for second in sheet.placed[i + 1:]:
                    grown = type(first)(first.part, first.x_mm, first.y_mm,
                                        first.width_mm + 5.0 - 1e-6, first.height_mm + 5.0 - 1e-6, False)
                    assert not _overlaps(grown, second)


def test_area_conservation_and_waste() -> None:
    bundle = _bundle()
    plan = plan_cutting(bundle)
    part_area = sum(p.area_mm2 for p in collect_parts(bundle))
    group_area = sum(g.part_area_mm2 for g in plan.groups)
    assert group_area == pytest.approx(part_area)
    assert 0 <= plan.waste_percent < 100
    assert plan.sheet_count >= 1


def test_oversized_part_is_reported_not_silently_dropped() -> None:
    bundle = _bundle()
    tiny = CuttingSettings(300.0, 200.0, kerf_mm=3.0)
    plan = plan_cutting(bundle, tiny)
    assert not plan.feasible
    assert plan.unplaced
    assert any("passt auf keine Platte" in message for message in plan.warnings)


def test_rotation_can_be_disabled() -> None:
    part = Part("P01", "Lang", 1200.0, 400.0, 18.0)
    narrow = CuttingSettings(500.0, 1300.0, kerf_mm=0.0, allow_rotation=False)
    assert _pack((part,), narrow, "area", "short_side", "shorter_axis") == []
    rotating = CuttingSettings(500.0, 1300.0, kerf_mm=0.0, allow_rotation=True)
    sheets = _pack((part,), rotating, "area", "short_side", "shorter_axis")
    assert len(sheets) == 1 and sheets[0].placed[0].rotated


def test_packing_is_deterministic() -> None:
    first = plan_cutting(_bundle())
    second = plan_cutting(_bundle())
    assert [[(i.part.part_id, i.x_mm, i.y_mm) for i in s.placed] for g in first.groups for s in g.sheets] == \
           [[(i.part.part_id, i.x_mm, i.y_mm) for i in s.placed] for g in second.groups for s in g.sheets]


def test_settings_validation() -> None:
    with pytest.raises(ValueError):
        CuttingSettings(0, 100)
    with pytest.raises(ValueError):
        CuttingSettings(100, 100, kerf_mm=-1)
    with pytest.raises(ValueError):
        CuttingSettings(100, 100, trim_mm=60)


def test_svg_and_csv_output(tmp_path: Path) -> None:
    plan = plan_cutting(_bundle())
    svg = render_cutting_svg(plan, 0, 0)
    assert svg.startswith("<svg") and "Platte 1/" in svg and "P01" in svg
    csv_path = tmp_path / "plan.csv"
    write_cutting_csv(csv_path, plan)
    text = csv_path.read_text(encoding="utf-8-sig")
    assert text.splitlines()[0].startswith("Dicke_mm;Platte")
    assert len(text.splitlines()) == 1 + len(collect_parts(_bundle()))


def test_weight_is_a_range_and_scales_with_volume() -> None:
    bundle = _bundle()
    weight = estimate_weight(bundle)
    assert weight.low_kg is not None and weight.high_kg is not None
    assert 0 < weight.low_kg < weight.high_kg
    assert weight.low_kg == pytest.approx(plate_volume_m3(bundle) * 640.0)
    assert "ohne Chassis" in weight.describe()
    bigger = estimate_weight(_bundle(external_height_mm=800.0, target_volume_l=60.0))
    assert bigger.high_kg > weight.high_kg


def test_unknown_material_has_no_invented_density() -> None:
    bundle = calculate_project(demo_project().model_copy(update={"material": "Eiche"}))
    weight = estimate_weight(bundle)
    assert weight.low_kg is None and "nicht berechenbar" in weight.describe()


def test_assembly_guide_follows_construction() -> None:
    plain = build_instructions(_bundle())
    titles = [step.title for step in plain]
    assert titles[0] == "Material und Werkzeug prüfen" and "Port einbauen" in titles
    assert "Frequenzweiche aufbauen" in titles
    bandpass = [s.title for s in build_instructions(_bundle(enclosure_type="bandpass_4", rear_volume_l=30.0))]
    assert "Kammertrennung dicht verleimen" in bandpass
    markdown = render_markdown(_bundle())
    assert markdown.startswith("# Bauanleitung") and "**Kontrolle:**" in markdown


_PORT_BOX = {"target_volume_l": 45.0, "tuning_hz": 35.0, "external_width_mm": 340.0,
             "external_height_mm": 560.0, "port_diameter_mm": 80.0}
_GENERIC = {"target_volume_l": 200.0, "tuning_hz": 60.0, "external_height_mm": 1200.0,
            "external_width_mm": 450.0, "brace_quantity": 0}
# Buildable parameter sets per enclosure family (small demo woofer); every type must be covered.
_OVERRIDES: dict[str, dict[str, float]] = {
    "sealed": {"external_width_mm": 340.0, "external_height_mm": 560.0},
    "bass_reflex": _PORT_BOX,
    "bandpass_4": {**_PORT_BOX, "rear_volume_l": 30.0},
    "bandpass_6_parallel": {**_PORT_BOX, "rear_volume_l": 30.0, "rear_tuning_hz": 50.0},
    "bandpass_6_series": {**_PORT_BOX, "rear_volume_l": 50.0, "rear_tuning_hz": 30.0,
                          "rear_port_diameter_mm": 75.0},
    "passive_radiator": {"target_volume_l": 45.0, "tuning_hz": 35.0, "external_width_mm": 340.0,
                         "external_height_mm": 560.0, "radiator_mms_g": 60.0},
    "isobaric_sealed": {"external_width_mm": 400.0, "external_height_mm": 450.0,
                        "target_qtc": 0.5, "target_volume_l": 70.0},
    "compound_push_pull": {"external_width_mm": 400.0, "external_height_mm": 450.0,
                           "target_qtc": 0.5, "target_volume_l": 70.0},
    "isobaric_vented": {"external_width_mm": 400.0, "external_height_mm": 600.0,
                        "target_qtc": 0.5, "target_volume_l": 70.0, "tuning_hz": 35.0},
    "mltl": {"target_volume_l": 120.0, "tuning_hz": 25.0, "external_height_mm": 1200.0,
             "external_width_mm": 400.0, "port_diameter_mm": 40.0},
    "infinite_baffle": {"target_volume_l": 700.0},
    "horn_front": {"tuning_hz": 150.0, "external_width_mm": 450.0, "external_height_mm": 750.0,
                   "target_qtc": 0.5},
}


@pytest.mark.parametrize("enclosure_id", [entry.id for entry in registry.supported()])
def test_every_enclosure_type_gets_cutting_plan_and_guide(enclosure_id: str, tmp_path: Path) -> None:
    project = demo_project()
    enclosure = project.enclosure.model_copy(update={
        "enclosure_type": enclosure_id, **_GENERIC, **_OVERRIDES.get(enclosure_id, {})})
    bundle = calculate_project(project.model_copy(update={
        "enclosure": enclosure, "front_elements": (), "tweeter_name": "",
        "crossover": CrossoverConfig(enabled=False)}))
    plan = plan_cutting(bundle)
    assert plan.sheet_count >= 1 and plan.feasible
    assert build_instructions(bundle, plan)
    package = export_project_package(bundle, tmp_path)
    for name in ("zuschnittplan.pdf", "zuschnittplan.csv", "bauanleitung.md", "bauanleitung.pdf"):
        assert (package / "fertigung" / name).is_file(), name
    assert any((package / "fertigung" / "zuschnittplan").glob("platte_*.svg"))
    assert "Zuschnitt:" in (package / "projektzusammenfassung.txt").read_text(encoding="utf-8")
