from __future__ import annotations

import os
import xml.etree.ElementTree as ET

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from lautsprecher_konstruktion.drawings.dimension_svg import dimension_rows, render_dimension_svg
from lautsprecher_konstruktion.enclosure.registry import registry
from lautsprecher_konstruktion.library.store import ComponentLibrary
from lautsprecher_konstruktion.project.demo import demo_project
from lautsprecher_konstruktion.services.design import calculate_project
from lautsprecher_konstruktion.ui.assistant_window import AssistantWindow


def test_verified_catalog_retains_missing_manufacturer_data(tmp_path):
    library = ComponentLibrary(user_root=tmp_path / "library")
    real = [entry for entry in library.entries("drivers")
            if not entry.is_test_data and entry.driver is not None]
    assert len(real) >= 7
    assert all(entry.driver.source_url is not None for entry in real)
    tweeter = library.entries("drivers", "DC28F-8")[0].driver
    assert tweeter.vas_m3 is None
    assert len([entry for entry in library.entries("passive_radiators")
                if not entry.is_test_data]) >= 3


def test_dimension_sheet_uses_resolved_geometry():
    bundle = calculate_project(demo_project())
    rows = dimension_rows(bundle)
    assert rows and rows[0][2] == bundle.front_elements[0].x_m * 1000
    svg = render_dimension_svg(bundle)
    ET.fromstring(svg)
    assert "Außenbreite" in svg and "Innentiefe" in svg
    assert "Ausschnitte und Einbauorte" in svg
    assert rows[0][4] in svg


def test_all_enclosure_families_remain_visible_in_selector():
    app = QApplication.instance() or QApplication([])
    window = AssistantWindow()
    try:
        assert window.enclosure.count() == len(registry.all()) + 1
        for index, entry in enumerate(registry.all(), start=1):
            assert window.enclosure.itemData(index) == entry.id
            assert window.enclosure.model().item(index).isEnabled() == (entry.status == "SUPPORTED")
    finally:
        window.close()
        app.processEvents()
