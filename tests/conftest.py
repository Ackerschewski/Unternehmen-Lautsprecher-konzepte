import os
import tempfile
from pathlib import Path

import pytest

# Keep tests away from the real user profile (settings, recent files, autosave, library overlay).
_TEST_USER_DIR = tempfile.mkdtemp(prefix="lk-test-user-")
os.environ["LK_USER_DIR"] = _TEST_USER_DIR
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(autouse=True)
def _isolated_user_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    folder = tmp_path / "userdata"
    monkeypatch.setenv("LK_USER_DIR", str(folder))
    return folder


@pytest.fixture(autouse=True)
def _fail_on_qt_slot_exceptions(monkeypatch: pytest.MonkeyPatch) -> object:
    """PySide6 prints exceptions raised inside slots and carries on; that hid real bugs, so fail the test instead."""
    import sys

    caught: list[BaseException] = []
    previous = sys.excepthook

    def hook(kind: type[BaseException], value: BaseException, trace: object) -> None:
        caught.append(value)
        previous(kind, value, trace)  # type: ignore[arg-type]

    monkeypatch.setattr(sys, "excepthook", hook)
    yield
    if caught:
        raise AssertionError(f"Exception inside a Qt slot: {caught[0]!r}")
