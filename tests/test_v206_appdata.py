import logging
import sys
import threading
from pathlib import Path

import pytest

from lautsprecher_konstruktion import appdata
from lautsprecher_konstruktion.appdata import Autosave, RecentProjects, Settings


def test_user_dir_can_be_relocated(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LK_USER_DIR", str(tmp_path / "x"))
    assert appdata.user_data_dir() == tmp_path / "x"
    monkeypatch.delenv("LK_USER_DIR")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    assert appdata.user_data_dir() == tmp_path / "local" / "LautsprecherKonstruktion"


def test_settings_round_trip_and_corrupt_file(tmp_path: Path) -> None:
    settings = Settings(tmp_path / "s.json")
    assert settings.get("kerf", 3.0) == 3.0
    settings.set("kerf", 4.5)
    settings.set("rotate", False)
    assert settings.get("kerf") == 4.5 and settings.get("rotate") is False
    (tmp_path / "s.json").write_text("{not json", encoding="utf-8")
    assert settings.get("kerf", 3.0) == 3.0
    settings.set("kerf", 2.0)  # a corrupt file is replaced, not fatal
    assert settings.get("kerf") == 2.0


def test_recent_projects_order_dedup_limit_and_missing_files(tmp_path: Path) -> None:
    recent = RecentProjects(tmp_path / "recent.json", limit=3)
    files = []
    for name in "abcd":
        path = tmp_path / f"{name}.json"
        path.write_text("{}", encoding="utf-8")
        files.append(path)
        recent.add(path)
    assert recent.items() == [files[3].resolve(), files[2].resolve(), files[1].resolve()]
    recent.add(files[1])
    assert recent.items()[0] == files[1].resolve()
    files[3].unlink()
    assert files[3].resolve() not in recent.items()
    recent.clear()
    assert recent.items() == []


def test_autosave_write_recover_discard(tmp_path: Path) -> None:
    autosave = Autosave(tmp_path / "auto")
    assert autosave.recoverable() is None
    autosave.write('{"a": 1}')
    assert autosave.recoverable() is not None and autosave.file.read_text(encoding="utf-8") == '{"a": 1}'
    autosave.write('{"a": 2}')
    assert autosave.file.read_text(encoding="utf-8") == '{"a": 2}'
    assert not list(autosave.folder.glob("*.tmp"))
    autosave.discard()
    assert autosave.recoverable() is None


def test_logging_writes_file_and_is_idempotent() -> None:
    path = appdata.configure_logging()
    assert appdata.configure_logging() == path
    appdata.get_logger("test").warning("Testeintrag äöü")
    for handler in logging.getLogger(appdata.LOG_NAME).handlers:
        handler.flush()
    assert "Testeintrag äöü" in path.read_text(encoding="utf-8")
    handlers = [h for h in logging.getLogger(appdata.LOG_NAME).handlers
                if getattr(h, "baseFilename", None) == str(path)]
    assert len(handlers) == 1


def test_excepthook_logs_and_reports(monkeypatch: pytest.MonkeyPatch) -> None:
    path = appdata.configure_logging()
    messages: list[str] = []
    old_hook, old_thread_hook = sys.excepthook, threading.excepthook
    try:
        appdata.install_excepthook(messages.append)
        try:
            raise RuntimeError("kaputt")
        except RuntimeError:
            sys.excepthook(*sys.exc_info())
        thread = threading.Thread(target=lambda: (_ for _ in ()).throw(ValueError("thread kaputt")))
        thread.start()
        thread.join()
    finally:
        sys.excepthook, threading.excepthook = old_hook, old_thread_hook
    for handler in logging.getLogger(appdata.LOG_NAME).handlers:
        handler.flush()
    text = path.read_text(encoding="utf-8")
    assert "RuntimeError: kaputt" in messages[0] and "kaputt" in text
    assert any("thread kaputt" in m for m in messages)
