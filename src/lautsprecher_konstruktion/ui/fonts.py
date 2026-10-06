"""Bundled fonts: Inter (text and controls) and Cormorant Garamond (large titles); SIL Open Font License."""
from __future__ import annotations

import sys
from pathlib import Path

from matplotlib import font_manager
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from lautsprecher_konstruktion.appdata import get_logger
from lautsprecher_konstruktion.ui.tokens import UI_FONT

LOG = get_logger("fonts")
_loaded: list[str] = []


def fonts_dir() -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[3]))
    return base / "data" / "fonts"


def load_fonts() -> list[str]:
    """Register the bundled fonts once; returns the available family names."""
    if _loaded:
        return list(_loaded)
    families: set[str] = set()
    for path in sorted(fonts_dir().glob("*.ttf")):
        font_id = QFontDatabase.addApplicationFont(str(path))
        if font_id < 0:
            LOG.warning("Schrift konnte nicht geladen werden: %s", path.name)
            continue
        families.update(QFontDatabase.applicationFontFamilies(font_id))
        font_manager.fontManager.addfont(str(path))  # charts use the same families
    _loaded.extend(sorted(families))
    return list(_loaded)


def apply_default_font(app: QApplication) -> None:
    """Inter as application font when available; otherwise the platform default stays."""
    if UI_FONT in load_fonts():
        font = QFont(UI_FONT)
        font.setPixelSize(14)
        app.setFont(font)
