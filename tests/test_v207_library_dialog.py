import json
import os
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from lautsprecher_konstruktion.library.store import ComponentLibrary
from lautsprecher_konstruktion.ui import library_dialog
from lautsprecher_konstruktion.ui.library_dialog import LibraryDialog

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture
def dialog(app: QApplication, tmp_path: Path) -> LibraryDialog:
    return LibraryDialog(ComponentLibrary(user_root=tmp_path / "lib"))


def _select_first(dialog: LibraryDialog) -> str:
    table = dialog.tables[dialog.tabs.currentIndex()]
    table.setCurrentCell(0, 0)
    key = dialog._selected_id()
    assert key
    return key


def test_tables_are_filled_and_filtered(dialog: LibraryDialog) -> None:
    assert dialog.tables[0].rowCount() > 20
    everything = dialog.tables[0].rowCount()
    dialog.search.setText("Visaton")
    assert 0 < dialog.tables[0].rowCount() < everything
    dialog.search.setText("gibt-es-nicht-xyz")
    assert dialog.tables[0].rowCount() == 0


def test_selection_shows_json_details(dialog: LibraryDialog) -> None:
    key = _select_first(dialog)
    assert json.loads(dialog.details.toPlainText())["id"] == key


def test_new_entry_template_save_and_category_check(dialog: LibraryDialog, monkeypatch: pytest.MonkeyPatch) -> None:
    warnings: list[str] = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a: warnings.append(a[2]))
    dialog.tabs.setCurrentIndex(2)  # ports
    dialog._new()
    data = json.loads(dialog.details.toPlainText())
    assert data["category"] == "ports"
    data.update(id="eigene:rohr1", manufacturer="Eigen", model="Rohr 80")
    dialog.details.setPlainText(json.dumps(data))
    dialog._save()
    assert not warnings
    assert any(e.id == "eigene:rohr1" for e in dialog.library.entries("ports"))
    data["category"] = "materials"  # wrong tab for this category
    dialog.details.setPlainText(json.dumps(data))
    dialog._save()
    assert warnings and "Kategorie" in warnings[-1]
    dialog.details.setPlainText("{kein json")
    dialog._save()
    assert len(warnings) == 2


def test_toggle_active_flips_state(dialog: LibraryDialog) -> None:
    key = _select_first(dialog)
    before = next(e for e in dialog.library.entries(include_inactive=True) if e.id == key).active
    dialog._toggle()
    after = next(e for e in dialog.library.entries(include_inactive=True) if e.id == key).active
    assert after is (not before)


def test_import_reports_count_and_errors(dialog: LibraryDialog, tmp_path: Path,
                                         monkeypatch: pytest.MonkeyPatch) -> None:
    info: list[str] = []
    warnings: list[str] = []
    monkeypatch.setattr(QMessageBox, "information", lambda *a: info.append(a[2]))
    monkeypatch.setattr(QMessageBox, "warning", lambda *a: warnings.append(a[2]))
    dialog.tabs.setCurrentIndex(2)
    good = tmp_path / "ports.json"
    good.write_text(json.dumps([{"id": "eigene:p", "category": "ports", "manufacturer": "E", "model": "P",
                                 "specs": {}, "source": "test"}]), encoding="utf-8")
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **k: (str(good), ""))
    dialog._import()
    assert info and "1" in info[0]
    bad = tmp_path / "bad.json"
    bad.write_text("{\"components\": 5}", encoding="utf-8")
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **k: (str(bad), ""))
    dialog._import()
    assert warnings


def test_price_source_without_url_informs_user(dialog: LibraryDialog, monkeypatch: pytest.MonkeyPatch) -> None:
    info: list[str] = []
    monkeypatch.setattr(QMessageBox, "information", lambda *a: info.append(a[2]))
    dialog.tabs.setCurrentIndex(5)  # materials: test data without price links
    _select_first(dialog)
    dialog._open_price_source()
    assert info


def test_price_source_opens_external_link(dialog: LibraryDialog, monkeypatch: pytest.MonkeyPatch) -> None:
    opened: list[str] = []
    monkeypatch.setattr(library_dialog.QDesktopServices, "openUrl", lambda url: opened.append(url.toString()) or True)
    dialog.search.setText("Thomann")
    table = dialog.tables[0]
    for row in range(table.rowCount()):
        table.setCurrentCell(row, 0)
        key = dialog._selected_id()
        entry = next(e for e in dialog.library.entries(include_inactive=True) if e.id == key)
        if entry.product_url is not None:
            dialog._open_price_source()
            assert opened and opened[-1].startswith("http")
            return
    pytest.skip("no entry with a price link in this filter")
