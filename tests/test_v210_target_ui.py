import os

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from lautsprecher_konstruktion.targets.curve import PRESETS, TargetBand, TargetCurve
from lautsprecher_konstruktion.ui.assistant_window import AssistantWindow
from lautsprecher_konstruktion.ui.target_curve_panel import TargetCurvePanel

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])  # type: ignore[return-value]


def test_panel_starts_neutral_and_labels_the_curve_as_a_goal(app: QApplication) -> None:
    panel = TargetCurvePanel()
    assert panel.curve().is_neutral and not panel.table.isVisible()
    texts = " ".join(label.text() for label in panel.findChildren(type(panel.info)))
    assert "Sollwert" in texts and "kein gemessener Frequenzgang" in texts
    assert panel.info.text().startswith("Kein Entwurf")


def test_numeric_edit_undo_redo_reset_and_signal(app: QApplication) -> None:
    panel = TargetCurvePanel()
    seen: list[TargetCurve] = []
    panel.curveChanged.connect(seen.append)
    panel.add_button.click()
    assert len(panel.curve().bands) == 1 and len(seen) == 1
    gain = panel.table.cellWidget(0, 2)
    gain.setValue(6.0)  # type: ignore[attr-defined]
    assert panel.curve().bands[0].gain_db == 6.0
    panel.undo()
    assert panel.curve().bands[0].gain_db == 0.0
    panel.redo()
    assert panel.curve().bands[0].gain_db == 6.0
    panel.preset.setCurrentIndex(panel.preset.findText("Mehr Tiefbass"))
    panel._preset_chosen(panel.preset.currentIndex())
    assert panel.curve() == PRESETS["Mehr Tiefbass"]
    panel.reset()
    assert panel.curve().is_neutral and panel.undo_button.isEnabled()


class _Event:
    def __init__(self, x: float, y: float, xdata: float, ydata: float, button: int = 1, dbl: bool = False) -> None:
        self.x, self.y, self.xdata, self.ydata, self.button, self.dblclick = x, y, xdata, ydata, button, dbl
        self.inaxes = None


def test_mouse_drag_previews_fast_and_commits_once(app: QApplication) -> None:
    panel = TargetCurvePanel()
    panel.resize(900, 500)
    panel.show()
    panel.set_curve(TargetCurve(bands=(TargetBand(kind="peak", frequency_hz=1000.0, gain_db=0.0, q=1.0),)))
    seen: list[TargetCurve] = []
    panel.curveChanged.connect(seen.append)
    ax = panel.figure.axes[0]
    px, py = ax.transData.transform((1000.0, 0.0))
    ev = _Event(px, py, 1000.0, 0.0)
    ev.inaxes = ax
    panel._on_press(ev)
    assert panel._drag == 0
    for freq, gain in ((1200.0, 2.0), (1500.0, 4.0), (2000.0, 5.0)):
        panel._last_draw = 0.0
        panel._on_motion(_Event(px, py, freq, gain))
    assert seen == []  # no solver-relevant signal while dragging
    panel._on_release(_Event(px, py, 2000.0, 5.0))
    assert len(seen) == 1 and seen[0].bands[0].frequency_hz == 2000.0 and seen[0].bands[0].gain_db == 5.0
    panel.undo()
    assert panel.curve().bands[0].frequency_hz == 1000.0 and panel.curve().bands[0].gain_db == 0.0


def test_actual_curve_deviation_is_reported_only_for_model_range(app: QApplication) -> None:
    panel = TargetCurvePanel()
    f = np.geomspace(10, 500, 300)
    panel.set_actual(f, np.zeros_like(f))
    assert "Tiefton" in panel.deviation_text() and "keine Chassis-Messdaten" in panel.deviation_text()
    panel.set_actual(np.geomspace(1000, 20000, 50), np.zeros(50))
    assert "nicht ab" in panel.deviation_text()


def test_window_offers_both_ways_and_target_mode_drives_f3(app: QApplication) -> None:
    window = AssistantWindow()
    assert window.classic_mode.isChecked() and not window.target_mode.isChecked()
    assert window.tabs.tabText(window._sound_tab_index()) == "Klang && Simulation"
    assert window._request().target_f3_hz is None
    window.target_mode.setChecked(True)
    assert window.create_button.text() == "Entwurf aus Zielkurve erstellen"
    assert window._request().target_f3_hz is None  # neutral curve gives no constraint
    window.target_panel.set_curve(TargetCurve(bands=(
        TargetBand(kind="low_shelf", frequency_hz=60.0, gain_db=-12.0, q=0.7),)))
    f3 = window._request().target_f3_hz
    assert f3 is not None and 20 < f3 < 150
    window.options.setChecked(True)
    window.target_f3.setValue(45.0)
    assert window._request().target_f3_hz == 45.0  # explicit wish wins


def test_design_shows_deviation_and_curve_is_saved_in_the_project(app: QApplication, tmp_path) -> None:
    window = AssistantWindow()
    window.demo_choice.setCurrentIndex(1)
    window._demo()
    window.create_design()
    assert window.worker is not None
    window.worker.wait(180000)
    app.processEvents()
    assert window.designs
    assert window.comparison.item(0, 11).text().startswith("Ø")
    assert window.target_panel.deviation_text().startswith("Abweichung im Tiefton")
    window.target_panel.set_curve(PRESETS["Warm (Höhen leicht abfallend)"], emit=True)
    window.set_reduced_motion(True)
    text = window._project_json(window._current())
    assert '"target_curve"' in text and '"version": 1' in text
    window2 = AssistantWindow()
    path = tmp_path / "p.json"
    path.write_text(text, encoding="utf-8")
    window2._unsaved = False
    assert window2.open_project_file(path)
    assert window2.target_panel.curve() == PRESETS["Warm (Höhen leicht abfallend)"]
    assert window2.target_mode.isChecked()
