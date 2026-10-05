import os
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from lautsprecher_konstruktion.enclosure.rectangular import MITRE_NOTE, CabinetDimensions, cut_list
from lautsprecher_konstruktion.export.assembly_guide import build_instructions
from lautsprecher_konstruktion.export.bom import write_cutlist_csv
from lautsprecher_konstruktion.export.cutting import plan_cutting, render_cutting_dxf
from lautsprecher_konstruktion.export.package import export_project_package
from lautsprecher_konstruktion.project.demo import demo_project
from lautsprecher_konstruktion.services.design import calculate_project
from lautsprecher_konstruktion.ui.main_window import MainWindow

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _cabinet() -> CabinetDimensions:
    return CabinetDimensions(width_m=0.34, height_m=0.56, depth_m=0.30, panel_thickness_m=0.018)


def test_mitre_cut_list_spans_full_outer_length_and_notes_the_angle() -> None:
    butt = {p.name: p for p in cut_list(_cabinet())}
    mitre = {p.name: p for p in cut_list(_cabinet(), "mitre")}
    assert mitre["Top"].width_m == pytest.approx(0.34) and butt["Top"].width_m == pytest.approx(0.34 - 0.036)
    assert mitre["Bottom"].width_m == pytest.approx(0.34)
    assert mitre["Side"].height_m == pytest.approx(0.56) and mitre["Side"].quantity == 2
    assert mitre["Front"] == butt["Front"] and mitre["Back"] == butt["Back"]
    assert all(mitre[name].note == MITRE_NOTE for name in ("Side", "Top", "Bottom"))
    assert all(p.note == "" for p in butt.values())
    with pytest.raises(ValueError):
        cut_list(_cabinet(), "dovetail")


def test_total_plate_area_grows_only_for_top_and_bottom() -> None:
    def area(joint: str) -> float:
        return sum(p.quantity * p.width_m * p.height_m for p in cut_list(_cabinet(), joint))
    assert area("mitre") - area("butt") == pytest.approx(2 * 0.036 * _cabinet().internal_depth_m)


def _project(joint: str):
    project = demo_project()
    return project.model_copy(update={"enclosure": project.enclosure.model_copy(update={"joint_style": joint})})


def test_mitre_flows_into_bundle_csv_guide_and_cutting(tmp_path: Path) -> None:
    butt, mitre = calculate_project(_project("butt")), calculate_project(_project("mitre"))
    assert butt.target_net_volume_m3 == pytest.approx(mitre.target_net_volume_m3)  # volume is unaffected
    assert mitre.cabinet == butt.cabinet
    top_butt = next(p for p in butt.panels if p.name == "Top")
    top_mitre = next(p for p in mitre.panels if p.name == "Top")
    assert top_mitre.width_m > top_butt.width_m
    csv_path = tmp_path / "cut.csv"
    write_cutlist_csv(csv_path, mitre)
    assert "45° Gehrung" in csv_path.read_text(encoding="utf-8-sig")
    assert any(step.title.startswith("Gehrungen") for step in build_instructions(mitre))
    assert not any(step.title.startswith("Gehrungen") for step in build_instructions(butt))
    assert plan_cutting(mitre).feasible


def test_cutting_dxf_has_sheet_parts_and_text_inside_the_sheet(tmp_path: Path) -> None:
    bundle = calculate_project(_project("butt"))
    plan = plan_cutting(bundle)
    text = render_cutting_dxf(plan, 0, 0)
    assert text.startswith("0\nSECTION") and text.rstrip().endswith("EOF")
    sheet = plan.groups[0].sheets[0]
    assert text.count("0\nLINE\n") == 4 * (1 + len(sheet.placed))
    assert text.count("0\nTEXT\n") == len(sheet.placed)
    cfg = plan.groups[0].settings
    lines = text.split("\n")
    values = [float(lines[i + 1]) for i, code in enumerate(lines[:-1]) if code in {"10", "20", "11", "21"}
              and lines[i - 1] != "TEXT"]
    assert min(values) >= -1e-6
    assert max(values) <= max(cfg.sheet_width_mm, cfg.sheet_height_mm) + 1e-6
    package = export_project_package(bundle, tmp_path)
    assert list((package / "fertigung" / "zuschnittplan").glob("platte_*.dxf"))


def test_expert_window_joint_style_round_trip() -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    window = MainWindow()
    window._apply_project(_project("mitre"))
    assert window.joint_style.currentData() == "mitre"
    assert window._project_from_form().enclosure.joint_style == "mitre"
    window.calculate()
    assert next(p for p in window._bundle.panels if p.name == "Top").note == MITRE_NOTE
