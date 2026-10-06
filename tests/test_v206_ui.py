import json
import os
from pathlib import Path

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from lautsprecher_konstruktion import REVISION
from lautsprecher_konstruktion.appdata import Autosave, RecentProjects
from lautsprecher_konstruktion.project.demo import demo_project
from lautsprecher_konstruktion.ui.assistant_window import AssistantWindow
from lautsprecher_konstruktion.ui.cutting_panel import CuttingPanel, stored_cutting_settings
from lautsprecher_konstruktion.ui.help_dialog import HelpDialog, about_text
from lautsprecher_konstruktion.ui.main_window import MainWindow
from lautsprecher_konstruktion.ui.prototype_dialog import PrototypeDialog

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
YES, NO = QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.No


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture
def project_file(tmp_path: Path) -> Path:
    path = tmp_path / "demo.json"
    path.write_text(demo_project().model_dump_json(indent=2), encoding="utf-8")
    return path


def test_window_title_and_menu_structure(app: QApplication) -> None:
    window = AssistantWindow()
    assert REVISION in window.windowTitle()
    titles = [action.text().replace("&", "") for action in window.menuBar().actions()]
    assert titles == ["Datei", "Werkzeuge", "Ansicht", "Hilfe"]
    assert not window.recent_menu.isEnabled()


def test_open_project_updates_recent_list_cutting_tab_and_clears_unsaved(
        app: QApplication, project_file: Path) -> None:
    window = AssistantWindow()
    assert window.open_project_file(project_file)
    assert window.designs and not window._unsaved
    assert RecentProjects().items() == [project_file.resolve()]
    assert window.recent_menu.isEnabled()
    assert window.cutting_panel.plan is not None and window.cutting_panel.sheet_choice.count() >= 1
    assert "Gewicht" in window.cutting_panel.summary.toPlainText()


def test_unreadable_project_is_reported_not_raised(
        app: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    shown: list[str] = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: shown.append(args[2]))
    bad = tmp_path / "bad.json"
    bad.write_text("{kaputt", encoding="utf-8")
    window = AssistantWindow()
    assert window.open_project_file(bad) is False
    assert shown and RecentProjects().items() == []


def test_unsaved_changes_ask_before_discarding(
        app: QApplication, project_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    window = AssistantWindow()
    window.open_project_file(project_file)
    window._unsaved = True
    asked: list[str] = []
    answers = iter([NO, YES])
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: (asked.append(a[1]), next(answers))[1])
    assert window.open_project_file(project_file) is False  # declined
    assert window.open_project_file(project_file) is True   # accepted
    assert len(asked) == 2


def test_visible_window_close_can_be_cancelled(
        app: QApplication, project_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    window = AssistantWindow()
    window.open_project_file(project_file)
    window._unsaved = True
    window.show()
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: NO)
    assert window.close() is False and window.isVisible()
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: YES)
    assert window.close() is True


def test_save_writes_file_discards_autosave_and_remembers(
        app: QApplication, project_file: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    window = AssistantWindow()
    window.open_project_file(project_file)
    window._unsaved = True
    target = tmp_path / "saved.json"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(target), ""))
    window._autosave()
    assert Autosave().recoverable() is not None
    window._save()
    assert json.loads(target.read_text(encoding="utf-8"))["name"]
    assert not window._unsaved and Autosave().recoverable() is None
    assert RecentProjects().items()[0] == target.resolve()


def test_autosave_only_when_there_is_something_unsaved(app: QApplication, project_file: Path) -> None:
    window = AssistantWindow()
    window._autosave()
    assert Autosave().recoverable() is None
    window.open_project_file(project_file)
    window._autosave()
    assert Autosave().recoverable() is None  # clean state
    window._unsaved = True
    window._autosave()
    assert Autosave().recoverable() is not None


def test_recovery_offer_restore_and_decline(
        app: QApplication, monkeypatch: pytest.MonkeyPatch) -> None:
    Autosave().write(demo_project().model_dump_json())
    window = AssistantWindow()
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: NO)
    assert window.offer_recovery() is False and Autosave().recoverable() is None
    Autosave().write(demo_project().model_dump_json())
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: YES)
    assert window.offer_recovery() is True
    assert window.designs and window._unsaved
    assert RecentProjects().items() == []  # a restored session is not a saved file
    assert window.offer_recovery() is False  # nothing left to restore


def test_help_and_about_dialogs(app: QApplication) -> None:
    dialog = HelpDialog()
    assert dialog.windowTitle() == "Hilfe"
    text = about_text()
    assert REVISION in text and "Datenordner" in text and "Protokolldatei" in text


def test_cutting_panel_settings_are_stored_and_used(app: QApplication) -> None:
    from lautsprecher_konstruktion.services.design import calculate_project
    panel = CuttingPanel()
    panel.use_defaults.setChecked(False)
    panel.sheet_width.setValue(2000)
    panel.sheet_height.setValue(1000)
    panel.kerf.setValue(4.0)
    bundle = calculate_project(demo_project())
    panel.set_bundle(bundle)
    assert panel.plan.groups[0].settings.sheet_width_mm == 2000
    stored = stored_cutting_settings("Birke Multiplex")
    assert (stored.sheet_width_mm, stored.sheet_height_mm, stored.kerf_mm) == (2000.0, 1000.0, 4.0)
    again = CuttingPanel()  # a new session restores the values
    assert again.sheet_width.value() == 2000 and not again.use_defaults.isChecked()
    panel.set_bundle(None)
    assert panel.plan is None


def test_expert_window_baffle_step_round_trip(app: QApplication) -> None:
    window = MainWindow()
    project = demo_project()
    project = project.model_copy(update={"crossover": project.crossover.model_copy(
        update={"baffle_step_compensation_db": 3.5})})
    window._apply_project(project)
    assert window.baffle_step.value() == pytest.approx(3.5)
    assert window._project_from_form().crossover.baffle_step_compensation_db == pytest.approx(3.5)
    window.calculate()
    assert window._bundle is not None
    assert {"Lbs", "Rbs"} <= {c.reference for c in window._bundle.crossover.components}
    assert window.figure.axes  # response plot including the baffle step overlay was drawn


def test_prototype_dialog_compares_files(app: QApplication, tmp_path: Path,
                                         monkeypatch: pytest.MonkeyPatch) -> None:
    from dataclasses import replace

    from lautsprecher_konstruktion.acoustics.vented import simulate_vented
    from lautsprecher_konstruktion.services.design import calculate_project

    bundle = calculate_project(demo_project())
    port = replace(bundle.port, physical_length_m=bundle.port.physical_length_m + 0.02,
                   effective_length_m=bundle.port.effective_length_m + 0.02)
    f = np.geomspace(10, 1000, 300)
    r = simulate_vented(bundle.project.driver, bundle.target_net_volume_m3, port, 10.0, f)
    z = r.impedance_ohm
    frd = tmp_path / "m.frd"
    zma = tmp_path / "m.zma"
    frd.write_text("\n".join(f"{a} {b}" for a, b in zip(f, r.response_db, strict=True)), encoding="utf-8")
    zma.write_text("\n".join(f"{a} {abs(c)} {np.degrees(np.angle(c))}" for a, c in zip(f, z, strict=True)),
                   encoding="utf-8")
    dialog = PrototypeDialog(bundle)
    shown: list[str] = []
    monkeypatch.setattr(QMessageBox, "information", lambda *a: shown.append(a[2]))
    assert dialog.compare() is None and shown  # nothing selected yet
    dialog.frd_path.setText(str(frd))
    dialog.zma_path.setText(str(zma))
    report = dialog.compare()
    assert report is not None and report.port_correction is not None
    assert len(dialog.figure.axes) == 2 and dialog.save_button.isEnabled()
    assert "Prototypvergleich" in dialog.text.toPlainText()
    target = tmp_path / "report.md"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(target), ""))
    dialog.save_report()
    assert target.read_text(encoding="utf-8").startswith("# Prototypvergleich")
    warned: list[str] = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a: warned.append(a[2]))
    dialog.frd_path.setText(str(tmp_path / "missing.frd"))
    assert dialog.compare() is None and warned
