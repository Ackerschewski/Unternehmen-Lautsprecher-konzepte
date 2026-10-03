from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from xml.etree import ElementTree

from lautsprecher_konstruktion.drawings.dimension_svg import render_dimension_svg
from lautsprecher_konstruktion.drawings.internal_dimensions_svg import (
    render_internal_dimensions_svg,
)
from lautsprecher_konstruktion.drawings.panel_sheet_svg import (
    panel_sheet_surfaces,
    render_panel_sheet_svg,
)
from lautsprecher_konstruktion.export.package import export_project_package
from lautsprecher_konstruktion.project.demo import demo_project
from lautsprecher_konstruktion.services.design import calculate_project


def test_v200_panel_sheets_export_with_same_coordinates_as_dxf(tmp_path: Path):
    bundle = calculate_project(demo_project())
    assert panel_sheet_surfaces(bundle) == ("front",)
    svg = render_panel_sheet_svg(bundle, "front")
    ElementTree.fromstring(svg)
    element = bundle.front_elements[0]
    assert f"Mitte X {element.x_m*1000:.1f} / Y {element.y_m*1000:.1f}" in svg
    package = export_project_package(bundle, tmp_path)
    assert (package / "zeichnungen" / "einzelteil_front.svg").is_file()
    dxf = (package / "zeichnungen" / "frontplatte.dxf").read_text(encoding="ascii")
    assert f"10\n{element.x_m*1000}" in dxf
    assert (package / "fertigung" / "fertigungsunterlagen.pdf").stat().st_size > 10000


def test_v200_dimension_sheets_keep_all_rows():
    bundle = calculate_project(demo_project())
    extra = bundle.front_elements * 20
    expanded = replace(bundle, front_elements=extra)
    dimension = render_dimension_svg(expanded)
    internal = render_internal_dimensions_svg(expanded)
    assert dimension.count(" · X ") >= len(extra)
    assert 'height="1100"' not in dimension
    ElementTree.fromstring(dimension)
    ElementTree.fromstring(internal)
