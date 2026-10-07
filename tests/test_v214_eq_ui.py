import os

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from lautsprecher_konstruktion.targets.eq import EQBand, FilterType
from lautsprecher_konstruktion.ui.assistant_window import AssistantWindow
from lautsprecher_konstruktion.ui.target_curve import TargetCurveEditor

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])  # type: ignore[return-value]


class Ev:
    def __init__(self, ax, f: float, y: float, *, button: int = 1, dbl: bool = False, level=None) -> None:
        px, py = ax.transData.transform((f, y if level is None else level))
        self.x, self.y, self.xdata, self.ydata = px, py, f, y
        self.button, self.dblclick, self.inaxes = button, dbl, ax


def editor_with_axes(app: QApplication) -> TargetCurveEditor:
    editor = TargetCurveEditor("dark")
    editor.resize(900, 600)
    editor.show()
    app.processEvents()
    return editor


def test_editor_starts_with_a_smooth_neutral_curve_and_no_bands(app: QApplication) -> None:
    editor = editor_with_axes(app)
    assert editor.bands() == () and editor.model.is_neutral
    assert "Noch kein Filterband" in editor.inspector.hint.text() and editor.inspector.hint.isVisible()
    assert not editor.undo_button.isEnabled() and not editor.redo_button.isEnabled()


def test_inspector_edits_the_active_band_with_undo_redo(app: QApplication) -> None:
    editor = editor_with_axes(app)
    seen: list[int] = []
    editor.curveChanged.connect(lambda: seen.append(1))
    editor.inspector.add_button.click()
    band = editor.bands()[0]
    assert editor.inspector.active_id == band.id and editor.inspector.panel.isVisible()
    editor.inspector.frequency.setValue(82)
    editor.inspector.gain.setValue(3.5)
    editor.inspector.q.setValue(0.85)
    band = editor.bands()[0]
    assert (band.frequency_hz, band.gain_db, band.q) == (82.0, 3.5, 0.85)
    assert editor.inspector.summary(band) == "Glocke | 82 Hz | +3.5 dB | Q 0,85".replace(",", ".")
    editor.inspector.kind.setCurrentIndex(editor.inspector.kind.findData("high_pass"))
    assert editor.bands()[0].filter_type is FilterType.HIGH_PASS and not editor.inspector.gain.isEnabled()
    editor.inspector.enabled.setChecked(False)
    assert editor.bands()[0].enabled is False
    n = len(seen)
    editor.undo()
    assert editor.bands()[0].enabled is True and len(seen) == n + 1
    editor.undo()
    editor.undo()
    assert editor.bands()[0].gain_db == 3.5 and editor.bands()[0].filter_type is FilterType.BELL
    editor.redo()
    assert editor.bands()[0].q == 0.85 and editor.bands()[0].filter_type is FilterType.BELL
    editor.redo()
    assert editor.bands()[0].filter_type is FilterType.HIGH_PASS
    assert editor.preset_id() == "custom"
    editor.reset()
    assert editor.bands() == () and editor.preset_id() == "neutral"


def test_double_click_adds_a_band_through_the_clicked_point_and_right_click_removes_it(app: QApplication) -> None:
    editor = editor_with_axes(app)
    ax = editor.figure.axes[0]
    editor._press(Ev(ax, 200.0, 4.0, dbl=True))
    assert len(editor.bands()) == 1
    band = editor.bands()[0]
    assert band.frequency_hz == pytest.approx(200.0) and band.gain_db == pytest.approx(4.0, abs=0.01)
    level = float(editor.model.curve(np.asarray([200.0]))[0])
    assert level == pytest.approx(4.0, abs=0.1)  # the curve passes through the clicked point
    ax = editor.figure.axes[0]
    editor._press(Ev(ax, 200.0, 4.0, button=3, level=level))
    assert editor.bands() == ()


def test_dragging_a_band_moves_frequency_and_gain_and_signals_once(app: QApplication) -> None:
    editor = editor_with_axes(app)
    editor.add_band(EQBand(filter_type=FilterType.BELL, frequency_hz=1000, gain_db=0.0, q=1.0))
    ax = editor.figure.axes[0]
    seen: list[int] = []
    editor.curveChanged.connect(lambda: seen.append(1))
    editor._press(Ev(ax, 1000.0, 0.0))
    assert editor._drag is not None and editor._drag[0] == "band"
    editor._last_draw = 0.0
    editor._motion(Ev(ax, 1500.0, 2.0))
    editor._motion(Ev(ax, 2000.0, 5.0))
    assert seen == []  # no solver-relevant signal while dragging
    editor._release(Ev(ax, 2000.0, 5.0))
    band = editor.bands()[0]
    assert band.frequency_hz == pytest.approx(2000.0) and band.gain_db == pytest.approx(5.0)
    assert len(seen) == 1
    editor.undo()
    assert editor.bands()[0].frequency_hz == 1000.0 and editor.bands()[0].gain_db == 0.0


def test_dragging_a_control_point_changes_only_the_base_curve(app: QApplication) -> None:
    editor = editor_with_axes(app)
    ax = editor.figure.axes[0]
    editor._press(Ev(ax, 1000.0, 0.0))
    assert editor._drag is not None and editor._drag[0] == "node"
    editor._motion(Ev(ax, 1000.0, 3.0))
    editor._release(Ev(ax, 1000.0, 3.0))
    assert dict(editor.points())[1000.0] == pytest.approx(3.0) and editor.bands() == ()
    assert dict(editor.effective_points())[1000.0] == pytest.approx(3.0, abs=0.01)


def test_assistant_passes_bands_to_the_request_only_in_target_mode_and_restores_them(app: QApplication) -> None:
    window = AssistantWindow()
    window.target_curve.add_band(EQBand(filter_type=FilterType.LOW_SHELF, frequency_hz=80, gain_db=4, q=0.7))
    assert window._request().target_eq_bands == ()
    window.design_method.setCurrentIndex(window.design_method.findData("target_curve"))
    request = window._request()
    assert request.target_eq_bands[0].filter_type is FilterType.LOW_SHELF
    assert request.target_curve_points is not None
    window.target_curve.restore_state((), bands=())
    assert window.target_curve.bands() == ()
    window.target_curve.restore_state(((20.0, 1.0), (20000.0, 0.0)), bands=request.target_eq_bands)
    assert window.target_curve.bands() == request.target_eq_bands


def test_band_changes_the_candidate_fit_score() -> None:
    from lautsprecher_konstruktion.services.automatic import _target_curve_fit

    f = np.geomspace(20, 500, 200)
    response = np.zeros_like(f)
    flat = _target_curve_fit(f, response, ((20.0, 0.0), (500.0, 0.0)))
    bumped = _target_curve_fit(f, response, ((20.0, 0.0), (500.0, 0.0)),
                               (EQBand(filter_type=FilterType.BELL, frequency_hz=60, gain_db=8, q=1),))
    assert flat is not None and bumped is not None
    assert bumped[1] > flat[1]  # RMS deviation grows when the target asks for a bump the response does not have
