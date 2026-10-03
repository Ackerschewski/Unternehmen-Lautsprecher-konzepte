import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from lautsprecher_konstruktion.ui.main_window import MainWindow


def test_calculate_button_shows_changed_values_and_clears_dirty_state() -> None:
    app=QApplication.instance() or QApplication([])
    window=MainWindow()
    old_f3=window._bundle.vented_response.f3_hz
    window.fs.setValue(20)
    assert window._dirty
    assert not window.export_button.isEnabled()
    window.calculate_button.click()
    app.processEvents()
    assert not window._dirty
    assert window.export_button.isEnabled()
    assert window.output_tabs.currentWidget() is window.summary
    assert 'Fs 32.0 → 20.0 Hz' in window.revision_state.text()
    assert window._bundle.vented_response.f3_hz != old_f3
    window.close()
