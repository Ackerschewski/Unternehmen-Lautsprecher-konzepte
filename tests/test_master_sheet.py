from __future__ import annotations

from PySide6.QtCore import QByteArray
from PySide6.QtSvg import QSvgRenderer

from lautsprecher_konstruktion.drawings.master_sheet_svg import render_master_sheet_svg
from lautsprecher_konstruktion.enclosure.layout import FrontElement
from lautsprecher_konstruktion.library.store import ComponentLibrary
from lautsprecher_konstruktion.project.models import (
    CrossoverConfig,
    EnclosureConfig,
    SpeakerProject,
)
from lautsprecher_konstruktion.services.design import calculate_project


def test_master_sheet_contains_all_mount_and_cut_dimensions(tmp_path):
    library = ComponentLibrary(user_root=tmp_path / "user")
    driver = library.entries("drivers", "18W/8531G00")[0].driver
    project = SpeakerProject(name="Fertigungszeichnung mit Bohrbild", driver=driver,
        crossover=CrossoverConfig(enabled=False), front_elements=(
            FrontElement(id="W1", type="woofer", x_m=.175, y_m=.36,
                outer_diameter_m=.1822, cutout_diameter_m=.156,
                mounting_depth_m=.0774, bolt_circle_diameter_m=.1698,
                bolt_count=5, hole_diameter_m=.0053),))
    bundle = calculate_project(project)
    svg = render_master_sheet_svg(bundle)
    assert QSvgRenderer(QByteArray(svg.encode())).isValid()
    assert "Vorderansicht" in svg and "Seitenschnitt" in svg and "Rückansicht" in svg
    assert "Zuschnittliste" in svg and "Einbauteile" in svg
    assert "LK Ø 169.8" in svg and "5 × Ø 5.3" in svg
    assert all(f"W1-{index}" in svg for index in range(1, 6))
    assert "156.0" in svg and "77.4" in svg


def test_master_sheet_marks_missing_hole_data(tmp_path):
    library = ComponentLibrary(user_root=tmp_path / "user")
    driver = library.entries("drivers", "B 200 - 6 Ohm")[0].driver
    bundle = calculate_project(SpeakerProject(driver=driver,
        enclosure=EnclosureConfig(target_qtc=1.0),
        crossover=CrossoverConfig(enabled=False)))
    svg = render_master_sheet_svg(bundle)
    assert "nicht veröffentlicht" in svg
    assert "Kein vollständiges Hersteller-Lochbild" in svg
