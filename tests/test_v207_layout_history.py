import os

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from lautsprecher_konstruktion.enclosure.layout import FrontElement
from lautsprecher_konstruktion.project.demo import demo_project
from lautsprecher_konstruktion.ui.history import History
from lautsprecher_konstruktion.ui.layout_canvas import FrontLayoutCanvas, snap_position
from lautsprecher_konstruktion.ui.main_window import MainWindow

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_history_push_undo_redo_and_branching() -> None:
    history = History("a", clock=FakeClock())
    assert not history.can_undo and not history.can_redo and history.undo() is None
    assert history.push("b") and history.push("c")
    assert history.undo() == "b" and history.undo() == "a" and history.undo() is None
    assert history.redo() == "b"
    assert history.push("x")  # a new edit drops the redo branch
    assert not history.can_redo and history.current == "x"
    assert history.undo() == "b"


def test_history_ignores_unchanged_state_and_limits_size() -> None:
    history = History(0, limit=3, clock=FakeClock())
    assert history.push(0) is False
    for value in (1, 2, 3, 4):
        history.push(value)
    assert history.current == 4
    assert [history.undo(), history.undo(), history.undo()] == [3, 2, None]  # only 3 states are kept
    with pytest.raises(ValueError):
        History(0, limit=1)


def test_history_merges_rapid_edits_with_the_same_key() -> None:
    clock = FakeClock()
    history = History("a", merge_window_s=1.0, clock=clock)
    history.push("b", merge_key="edit")
    clock.now = 0.5
    history.push("c", merge_key="edit")  # merged into b's entry
    assert history.undo() == "a"
    history.redo()
    clock.now = 5.0
    history.push("d", merge_key="edit")  # too late: a new entry
    assert history.undo() == "c"
    clock.now = 5.1
    history.push("e", merge_key="other")
    history.push("f", merge_key="other")
    assert history.undo() == "c"


def test_snap_to_centre_grid_and_plate() -> None:
    assert snap_position(176.0, 301.0, 350.0, 600.0) == (175.0, 300.0)  # centre line of a 350 mm plate
    assert snap_position(60.2, 12.4, 350.0, 600.0) == (60.0, 10.0)
    assert snap_position(-20.0, 700.0, 350.0, 600.0) == (0.0, 600.0)
    assert snap_position(60.2, 12.4, 350.0, 600.0, grid_mm=0) == (60.2, 12.4)


def _elements() -> tuple[FrontElement, ...]:
    return (
        FrontElement(id="W1", type="woofer", x_m=0.10, y_m=0.30, outer_diameter_m=0.20, cutout_diameter_m=0.17),
        FrontElement(id="BR1", type="port", x_m=0.25, y_m=0.10, outer_diameter_m=0.06, cutout_diameter_m=0.06),
        FrontElement(id="R1", type="passive_radiator", surface="back", x_m=0.17, y_m=0.30, outer_diameter_m=0.2),
    )


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_canvas_shows_only_the_current_surface_and_selects(app: QApplication) -> None:
    canvas = FrontLayoutCanvas()
    canvas.resize(500, 700)
    canvas.set_plate(350.0, 600.0)
    canvas.set_layout(_elements(), 0)
    assert sorted(canvas._items) == [0, 1]
    canvas.set_surface("back")
    canvas.set_layout(_elements(), 2)
    assert sorted(canvas._items) == [2]
    selected: list[int] = []
    canvas.elementSelected.connect(selected.append)
    canvas.set_surface("front")
    canvas.set_layout(_elements(), -1)
    canvas.show()
    QTest.mouseClick(canvas.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(*canvas.item_center_px(1)))
    assert selected and selected[-1] == 1


def test_dragging_moves_with_snap_and_emits_once(app: QApplication) -> None:
    canvas = FrontLayoutCanvas()
    canvas.resize(500, 700)
    canvas.set_plate(350.0, 600.0)
    canvas.set_layout(_elements(), 1)
    canvas.show()
    moves: list[tuple[int, float, float, bool]] = []
    canvas.elementMoved.connect(lambda *args: moves.append(args))
    start = QPoint(*canvas.item_center_px(1))
    target = start + QPoint(-60, -80)
    QTest.mousePress(canvas.viewport(), Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseMove(canvas.viewport(), target + QPoint(-20, -20))
    QTest.mouseMove(canvas.viewport(), target)
    QTest.mouseRelease(canvas.viewport(), Qt.MouseButton.LeftButton, pos=target)
    assert len(moves) == 1
    index, x_m, y_m, keyboard = moves[0]
    assert index == 1 and not keyboard
    assert x_m < 0.25 and y_m > 0.10  # moved left and up
    assert (x_m * 1000) % 5 == pytest.approx(0, abs=1e-6) or x_m * 1000 == pytest.approx(175.0)
    assert (y_m * 1000) % 5 == pytest.approx(0, abs=1e-6)


def test_arrow_keys_nudge_the_selected_element(app: QApplication) -> None:
    canvas = FrontLayoutCanvas()
    canvas.resize(500, 700)
    canvas.set_plate(350.0, 600.0)
    canvas.set_layout(_elements(), 0)
    canvas.show()
    moves: list[tuple[int, float, float, bool]] = []
    canvas.elementMoved.connect(lambda *args: moves.append(args))
    QTest.keyClick(canvas, Qt.Key.Key_Right)
    QTest.keyClick(canvas, Qt.Key.Key_Up, Qt.KeyboardModifier.ShiftModifier)
    assert moves[0] == (0, pytest.approx(0.101), pytest.approx(0.30), True)
    assert moves[1][2] == pytest.approx(0.31) and moves[1][3] is True


def _window() -> MainWindow:
    window = MainWindow()
    window._apply_project(demo_project())
    window.calculate()
    return window


def test_expert_undo_redo_for_add_remove_and_edit(app: QApplication) -> None:
    window = _window()
    start = list(window._front_elements)
    assert not window.undo_button.isEnabled()
    window._add_element("tweeter")
    assert len(window._front_elements) == len(start) + 1 and window.undo_button.isEnabled()
    window._remove_element()
    assert len(window._front_elements) == len(start)
    window._undo()
    assert len(window._front_elements) == len(start) + 1
    window._undo()
    assert window._front_elements == start
    window._redo()
    assert len(window._front_elements) == len(start) + 1 and window.redo_button.isEnabled()


def test_expert_canvas_move_is_undoable_and_recalculates(app: QApplication) -> None:
    window = _window()
    window.element_list.setCurrentRow(0)
    before = window._front_elements[0].x_m
    window._canvas_moved(0, before + 0.02, window._front_elements[0].y_m, False)
    assert window._front_elements[0].x_m == pytest.approx(before + 0.02)
    assert window._bundle.front_elements[0].x_m == pytest.approx(before + 0.02)
    window._undo()
    assert window._front_elements[0].x_m == pytest.approx(before)


def test_loading_a_project_clears_the_history(app: QApplication) -> None:
    window = _window()
    window._add_element("woofer")
    assert window.undo_button.isEnabled()
    window._apply_project(demo_project())
    assert not window._history.can_undo and not window.undo_button.isEnabled()


def test_keyboard_nudges_merge_into_one_undo_step(app: QApplication) -> None:
    window = _window()
    window.element_list.setCurrentRow(0)
    window._history = History(tuple(window._front_elements), merge_window_s=1e6)  # recalculation time varies
    start = window._front_elements[0]
    for _ in range(3):
        element = window._front_elements[0]
        window._canvas_moved(0, element.x_m + 0.001, element.y_m, True)
    assert window._front_elements[0].x_m == pytest.approx(start.x_m + 0.003)
    window._undo()
    assert window._front_elements[0].x_m == pytest.approx(start.x_m)
