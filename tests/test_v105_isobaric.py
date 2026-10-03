from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree

import pytest

from lautsprecher_konstruktion.drawings.internal_dimensions_svg import (
    render_internal_dimensions_svg,
)
from lautsprecher_konstruktion.enclosure.isobaric import equivalent_driver
from lautsprecher_konstruktion.enclosure.registry import registry
from lautsprecher_konstruktion.export.bom import build_bom
from lautsprecher_konstruktion.export.package import export_project_package
from lautsprecher_konstruktion.library.store import ComponentLibrary
from lautsprecher_konstruktion.project.demo import demo_project
from lautsprecher_konstruktion.services.automatic import AutomaticDesignRequest, automatic_design
from lautsprecher_konstruktion.services.design import calculate_project


def _project(kind: str):
    p = demo_project().model_copy(update={"front_elements": (), "tweeter_name": ""})
    e = p.enclosure.model_copy(update={
        "enclosure_type": kind, "external_width_mm": 400,
        "external_height_mm": 450 if kind == "isobaric_sealed" else 600,
        "target_qtc": 0.5, "target_volume_l": 70,
    })
    return p.model_copy(update={"enclosure": e})


def test_isobaric_pair_equivalence_and_manufacturing(tmp_path: Path):
    driver = demo_project().driver
    series = equivalent_driver(driver, "series")
    parallel = equivalent_driver(driver, "parallel")
    assert series.vas_m3 == parallel.vas_m3 == driver.vas_m3/2
    assert series.re_ohm == driver.re_ohm*2
    assert parallel.re_ohm == driver.re_ohm/2
    assert {e.id for e in registry.supported()} >= {"isobaric_sealed", "isobaric_vented"}
    for kind in ("isobaric_sealed", "isobaric_vented"):
        bundle = calculate_project(_project(kind))
        assert bundle.coupler is not None
        assert not any(i.severity == "error" for i in bundle.issues)
        assert any(item.reference == "W1" and item.quantity == 2 for item in build_bom(bundle))
        package = export_project_package(bundle, tmp_path)
        assert (package / "zeichnungen" / "isobarik_montagering.dxf").is_file()
        assert "W2 · Isobarik" in (package / "zeichnungen" / "schnitt.svg").read_text(encoding="utf-8")
        sheet = render_internal_dimensions_svg(bundle)
        ElementTree.fromstring(sheet)
        assert "Koppelrohr" in sheet and "Fensterstrebe" in sheet
        assert (package / "zeichnungen" / "innenaufbau_massblatt.svg").is_file()


def test_isobaric_geometry_blocks_export(tmp_path: Path):
    project = _project("isobaric_sealed")
    enclosure = project.enclosure.model_copy(update={"external_height_mm": 650})
    bundle = calculate_project(project.model_copy(update={"enclosure": enclosure}))
    assert any(i.severity == "error" for i in bundle.issues)
    with pytest.raises(ValueError, match="Geometrie"):
        export_project_package(bundle, tmp_path)


def test_visaton_catalog_has_source_and_no_invented_xmax(tmp_path: Path):
    library = ComponentLibrary(user_root=tmp_path / "library")
    visaton = [e for e in library.entries("drivers")
               if e.manufacturer == "Visaton" and e.driver is not None]
    assert len(visaton) >= 2
    assert all(e.driver.source_url and e.driver.datasheet_url for e in visaton)
    assert all(e.driver.xmax_m is None for e in visaton)


@pytest.mark.parametrize("kind", ["isobaric_sealed", "isobaric_vented"])
def test_assistant_can_design_isobaric_variant(kind: str, tmp_path: Path):
    library = ComponentLibrary(user_root=tmp_path / "library")
    result = automatic_design(AutomaticDesignRequest(
        project_name="Isobarik-Test", speaker_type="Subwoofer",
        enclosure_preference=kind, max_width_m=.5, max_height_m=.7,
        max_depth_m=.8, amplifier_power_w=1), library)
    assert result.status == "ok"
    assert result.designs[0].project.enclosure.enclosure_type == kind
