import os
from pathlib import Path

import numpy as np
import pytest

from lautsprecher_konstruktion.enclosure.folded_line import FOLDED_TYPES
from lautsprecher_konstruktion.enclosure.registry import registry
from lautsprecher_konstruktion.export.package import export_project_package
from lautsprecher_konstruktion.project.demo import demo_project
from lautsprecher_konstruktion.project.models import CrossoverConfig
from lautsprecher_konstruktion.services.design import calculate_project

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.mark.parametrize("family", sorted(FOLDED_TYPES))
def test_folded_line_has_solver_baffles_and_manufacturing_package(
    family: str, tmp_path: Path,
) -> None:
    assert registry.get(family).status == "SUPPORTED"
    project = demo_project()
    enclosure = project.enclosure.model_copy(update={
        "enclosure_type": family, "target_volume_l": 120.0,
        "tuning_hz": 60.0, "external_height_mm": 1200.0,
        "external_width_mm": 400.0, "brace_quantity": 0,
    })
    bundle = calculate_project(project.model_copy(update={
        "enclosure": enclosure, "front_elements": (), "tweeter_name": "",
        "crossover": CrossoverConfig(enabled=False),
    }))
    line = bundle.folded_line
    assert line is not None
    assert line.fold_count >= 1
    # horns may split an inclined septum into several straight boards
    assert len(line.baffle_panels) >= line.fold_count
    assert 0.8 < line.path_length_m < 4.0
    assert bundle.vented_response is not None
    assert np.all(np.isfinite(bundle.vented_response.response_db))
    assert not any(issue.severity == "error" for issue in bundle.issues)
    package = export_project_package(bundle, tmp_path)
    section = (package / "zeichnungen/schnitt.svg").read_text(encoding="utf-8")
    assert "F1" in section
    assert "Linienweg" in section
    assert "Linienfaltung F1" in (package / "fertigung/zuschnittliste.csv").read_text(
        encoding="utf-8-sig")


def test_folded_line_response_changes_with_length() -> None:
    project = demo_project()
    cfg = project.enclosure.model_copy(update={
        "enclosure_type": "transmission_line_open", "target_volume_l": 120.0,
        "tuning_hz": 60.0, "external_height_mm": 1200.0,
        "external_width_mm": 400.0, "brace_quantity": 0,
    })
    first = calculate_project(project.model_copy(update={"enclosure": cfg,
                                                   "front_elements": ()}))
    second_cfg = cfg.model_copy(update={"target_volume_l": 150.0})
    second = calculate_project(project.model_copy(update={"enclosure": second_cfg,
                                                    "front_elements": ()}))
    assert first.folded_line is not None and second.folded_line is not None
    assert first.folded_line.path_length_m != second.folded_line.path_length_m
    assert first.vented_response is not None and second.vented_response is not None
    assert not np.allclose(first.vented_response.response_db,
                           second.vented_response.response_db)


@pytest.mark.parametrize("family", ["transmission_line_closed", "horn_exponential"])
def test_folded_family_calculates_from_ui(family: str) -> None:
    from PySide6.QtWidgets import QApplication

    from lautsprecher_konstruktion.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    try:
        window.enclosure_type.setCurrentIndex(window.enclosure_type.findData(family))
        window.calculate_button.click()
        app.processEvents()
        assert window._bundle.folded_line is not None
        assert window._bundle.project.enclosure.enclosure_type == family
        assert "¼λ" in window.kpis.text()
        assert window.export_button.isEnabled()
    finally:
        window.close()
