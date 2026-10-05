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
