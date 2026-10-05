"""Per-user application data: recent projects, settings, autosave and the program log.

Everything lives below one folder (LOCALAPPDATA on Windows) and never inside the program
installation. Set LK_USER_DIR to relocate it, which the tests do.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
import threading
from collections.abc import Callable
from logging.handlers import RotatingFileHandler
from pathlib import Path
from types import TracebackType
from typing import Any

APP_FOLDER = "LautsprecherKonstruktion"
MAX_RECENT = 10
LOG_NAME = "lautsprecher_konstruktion"


def user_data_dir() -> Path:
    override = os.environ.get("LK_USER_DIR")
    if override:
        return Path(override)
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    return base / APP_FOLDER


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.replace(temp_name, path)
    except BaseException:
        Path(temp_name).unlink(missing_ok=True)
        raise


class Settings:
    """Small JSON key/value store; unreadable files fall back to defaults."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or user_data_dir() / "settings.json"

    def _load(self) -> dict[str, Any]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def get(self, key: str, default: Any = None) -> Any:
        return self._load().get(key, default)

    def set(self, key: str, value: Any) -> None:
        data = self._load()
        data[key] = value
        _atomic_write(self.path, json.dumps(data, indent=2, ensure_ascii=False))


class RecentProjects:
    def __init__(self, path: Path | None = None, limit: int = MAX_RECENT) -> None:
        self.path = path or user_data_dir() / "recent.json"
        self.limit = limit

    def _stored(self) -> list[str]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        return [item for item in data if isinstance(item, str)] if isinstance(data, list) else []

    def items(self) -> list[Path]:
        """Most recent first; files that no longer exist are omitted."""
        return [Path(item) for item in self._stored() if Path(item).is_file()]

    def add(self, project_file: str | Path) -> None:
        resolved = str(Path(project_file).resolve())
        entries = [resolved] + [item for item in self._stored() if item != resolved]
        _atomic_write(self.path, json.dumps(entries[: self.limit], indent=2, ensure_ascii=False))

    def clear(self) -> None:
        self.path.unlink(missing_ok=True)


class Autosave:
    """Periodic copy of the open project; a clean exit or a save removes it."""

    def __init__(self, folder: Path | None = None) -> None:
        self.folder = folder or user_data_dir() / "autosave"
        self.file = self.folder / "session.json"

    def write(self, project_json: str) -> None:
        _atomic_write(self.file, project_json)

    def recoverable(self) -> Path | None:
        return self.file if self.file.is_file() and self.file.stat().st_size > 0 else None

    def discard(self) -> None:
        self.file.unlink(missing_ok=True)


def log_file() -> Path:
    return user_data_dir() / "logs" / "lautsprecher.log"


def configure_logging(level: int = logging.INFO) -> Path:
    """Attach one rotating file handler to the application logger; safe to call repeatedly."""
    path = log_file()
    logger = logging.getLogger(LOG_NAME)
    logger.setLevel(level)
    if any(isinstance(h, RotatingFileHandler) and Path(h.baseFilename) == path for h in logger.handlers):
        return path
    for handler in [h for h in logger.handlers if isinstance(h, RotatingFileHandler)]:
        logger.removeHandler(handler)
        handler.close()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(path, maxBytes=512_000, backupCount=3, encoding="utf-8")
    except OSError:
        return path  # logging must never stop the program
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(handler)
    return path


def get_logger(name: str = "") -> logging.Logger:
    return logging.getLogger(f"{LOG_NAME}.{name}" if name else LOG_NAME)


def install_excepthook(on_error: Callable[[str], None] | None = None) -> None:
    """Log uncaught exceptions (main and worker threads) and report a short text to the user."""
    logger = get_logger()

    def handle(kind: type[BaseException], value: BaseException, trace: TracebackType | None) -> None:
        if issubclass(kind, KeyboardInterrupt):
            sys.__excepthook__(kind, value, trace)
            return
        logger.critical("Unbehandelter Fehler", exc_info=(kind, value, trace))
        if on_error is not None:
            on_error(f"{kind.__name__}: {value}")

    sys.excepthook = handle

    def handle_thread(args: threading.ExceptHookArgs) -> None:
        if args.exc_type is not SystemExit and args.exc_value is not None:
            handle(args.exc_type, args.exc_value, args.exc_traceback)

    threading.excepthook = handle_thread
