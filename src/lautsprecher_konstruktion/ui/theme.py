"""Light and dark appearance built from the design tokens."""
from __future__ import annotations

from typing import Literal

from cycler import cycler
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication

from lautsprecher_konstruktion.ui.tokens import (
    ACCENT_FALLBACK,
    ACCENT_FONT,
    MONO_FALLBACK,
    MONO_FONT,
    RADIUS_PX,
    STATUS,
    UI_FALLBACK,
    UI_FONT,
    text_on,
    theme,
)

Preference = Literal["system", "light", "dark"]
PREFERENCES: tuple[Preference, ...] = ("system", "light", "dark")
LABELS = {"system": "System", "light": "Hell", "dark": "Dunkel"}


def resolve_mode(preference: str) -> str:
    """Concrete mode for a preference; "system" follows the operating system when it reports a scheme."""
    if preference in {"light", "dark"}:
        return preference
    app = QGuiApplication.instance()
    if app is not None:
        scheme = app.styleHints().colorScheme()
        if scheme == Qt.ColorScheme.Dark:
            return "dark"
    return "light"


def stylesheet(mode: str) -> str:
    t = theme(mode)
    on_accent = text_on(t["accent"])
    ui = f"'{UI_FONT}', {UI_FALLBACK}"
    serif = f"'{ACCENT_FONT}', {ACCENT_FALLBACK}"
    mono = f"'{MONO_FONT}', {MONO_FALLBACK}"
    r = RADIUS_PX
    return f"""
        QMainWindow, QDialog {{background:{t['background']}; color:{t['textPrimary']};}}
        QWidget {{color:{t['textPrimary']}; font-family:{ui}; font-size:14px;}}
        QToolTip {{background:{t['surfaceElevated']}; color:{t['textPrimary']}; border:1px solid {t['border']};
            padding:4px 8px;}}
        QMenuBar {{background:{t['background']}; color:{t['textPrimary']};}}
        QMenuBar::item:selected {{background:{t['accentSubtle']};}}
        QMenu {{background:{t['surface']}; border:1px solid {t['border']}; padding:4px;}}
        QMenu::item {{padding:6px 16px; border-radius:{r}px;}}
        QMenu::item:selected {{background:{t['accentSubtle']};}}
        QMenu::separator {{height:1px; background:{t['border']}; margin:4px 8px;}}
        QStatusBar {{background:{t['background']}; color:{t['textSecondary']}; font-size:12px;}}
        QLabel#title {{font-family:{serif}; font-size:32px; font-weight:700;}}
        QLabel#subtitle {{color:{t['textSecondary']}; font-size:14px;}}
        QLabel#section {{font-size:18px; font-weight:600;}}
        QLabel#caption {{color:{t['textSecondary']}; font-size:12px;}}
        QLabel#kpi {{font-family:{mono}; font-size:13px; padding:8px 12px; background:{t['surfaceElevated']};
            border:1px solid {t['border']}; border-radius:{r}px;}}
        QLabel#brand {{color:{t['textSecondary']}; font-size:12px;}}
        QLabel#statusLine {{padding:8px 12px; background:{t['surface']}; border:1px solid {t['border']};
            border-left:3px solid {t['border']}; border-radius:{r}px;}}
        QLabel#statusLine[role="success"] {{border-left-color:{STATUS['success']};}}
        QLabel#statusLine[role="warning"] {{border-left-color:{STATUS['warning']};}}
        QLabel#statusLine[role="danger"] {{border-left-color:{STATUS['danger']};}}
        QLabel#statusLine[role="info"] {{border-left-color:{STATUS['info']};}}
        QFrame#card {{background:{t['surface']}; border:none;}}
        QScrollArea {{border:none; background:transparent;}}
        QScrollArea > QWidget > QWidget {{background:transparent;}}
        QGroupBox {{border:none; border-top:1px solid {t['border']}; margin-top:16px; padding:12px 0 0 0;
            font-weight:600;}}
        QGroupBox::title {{subcontrol-origin:margin; left:0; padding:0 4px 0 0; color:{t['textPrimary']};}}
        QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox, QTextEdit, QPlainTextEdit, QListWidget, QTextBrowser {{
            background:{t['surface']}; color:{t['textPrimary']}; border:1px solid {t['border']};
            border-radius:{r}px; padding:4px 8px; selection-background-color:{t['accentSubtle']};
            selection-color:{t['textPrimary']};
        }}
        QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus, QSpinBox:focus, QTextEdit:focus,
        QPlainTextEdit:focus, QListWidget:focus {{border:1px solid {t['accent']};}}
        QLineEdit:disabled, QComboBox:disabled, QDoubleSpinBox:disabled, QSpinBox:disabled {{
            background:{t['disabledSurface']}; color:{t['disabledText']};}}
        QTextEdit#mono, QTextBrowser#mono {{font-family:{mono}; font-size:13px;}}
        QComboBox::drop-down {{border:0; width:22px;}}
        QComboBox QAbstractItemView {{background:{t['surface']}; border:1px solid {t['border']};
            selection-background-color:{t['accentSubtle']}; selection-color:{t['textPrimary']};}}
        QPushButton {{background:{t['surface']}; color:{t['textPrimary']}; border:1px solid {t['border']};
            border-radius:{r}px; padding:6px 12px; font-weight:500;}}
        QPushButton:hover {{border-color:{t['accent']};}}
        QPushButton:focus {{border:1px solid {t['accent']};}}
        QPushButton:disabled {{background:{t['disabledSurface']}; color:{t['disabledText']};
            border-color:{t['border']};}}
        QPushButton#primary {{background:{t['accent']}; color:{on_accent}; border:1px solid {t['accent']};
            font-weight:600; padding:8px 16px;}}
        QPushButton#primary:hover {{background:{t['accentHover']}; border-color:{t['accentHover']};}}
        QPushButton#primary:pressed {{background:{t['accentPressed']}; border-color:{t['accentPressed']};}}
        QPushButton#primary:focus {{border:2px solid {t['textPrimary']};}}
        QPushButton#primary:disabled {{background:{t['disabledSurface']}; color:{t['disabledText']};
            border-color:{t['border']};}}
        QPushButton#danger {{color:{STATUS['danger']}; border-color:{STATUS['danger']};}}
        QCheckBox {{spacing:8px;}}
        QCheckBox::indicator {{width:16px; height:16px; border:1px solid {t['border']}; border-radius:{r}px;
            background:{t['surface']};}}
        QCheckBox::indicator:checked {{background:{t['accent']}; border-color:{t['accent']};}}
        QCheckBox::indicator:focus {{border:1px solid {t['accent']};}}
        QTabWidget::pane {{border:none; border-top:1px solid {t['border']}; background:{t['surface']};}}
        QTabBar::tab {{background:transparent; color:{t['textSecondary']}; padding:8px 12px; border:none;
            border-bottom:2px solid transparent; font-weight:500;}}
        QTabBar::tab:hover {{color:{t['textPrimary']};}}
        QTabBar::tab:selected {{color:{t['textPrimary']}; border-bottom:2px solid {t['accent']};}}
        QTabBar::tab:focus {{background:{t['accentSubtle']};}}
        QHeaderView::section {{background:{t['surfaceElevated']}; color:{t['textSecondary']};
            border:none; border-bottom:1px solid {t['border']}; padding:6px 8px; font-weight:600;}}
        QTableWidget {{background:{t['surface']}; alternate-background-color:{t['surfaceElevated']};
            gridline-color:{t['border']}; border:1px solid {t['border']}; border-radius:{r}px;}}
        QTableWidget::item:selected, QListWidget::item:selected {{background:{t['accentSubtle']};
            color:{t['textPrimary']};}}
        QProgressBar {{border:1px solid {t['border']}; border-radius:{r}px; text-align:center;
            background:{t['surface']}; color:{t['textPrimary']}; height:16px;}}
        QProgressBar::chunk {{background:{t['accent']}; border-radius:{max(r - 1, 0)}px;}}
        QScrollBar:vertical {{background:transparent; width:10px;}}
        QScrollBar::handle:vertical {{background:{t['border']}; border-radius:5px; min-height:24px;}}
        QScrollBar:horizontal {{background:transparent; height:10px;}}
        QScrollBar::handle:horizontal {{background:{t['border']}; border-radius:5px; min-width:24px;}}
        QScrollBar::add-line, QScrollBar::sub-line {{width:0; height:0;}}
        QSplitter::handle {{background:{t['border']};}}
    """


def chart_rc(mode: str) -> dict[str, object]:
    """Matplotlib rcParams that follow the theme: thin neutral frame and grid, no decoration."""
    t = theme(mode)
    return {
        "figure.facecolor": t["surface"], "axes.facecolor": t["surface"], "savefig.facecolor": t["surface"],
        "axes.edgecolor": t["border"], "axes.labelcolor": t["textSecondary"], "axes.titlecolor": t["textPrimary"],
        "text.color": t["textPrimary"], "xtick.color": t["textSecondary"], "ytick.color": t["textSecondary"],
        "grid.color": t["border"], "grid.alpha": 0.6, "grid.linewidth": 0.6, "axes.grid": True,
        "axes.spines.top": False, "axes.spines.right": False, "axes.titlesize": 12, "axes.titleweight": "bold",
        "axes.labelsize": 11, "font.family": [UI_FONT, "DejaVu Sans"], "legend.frameon": False,
        "legend.fontsize": 10,
        "axes.prop_cycle": cycler(color=[t["accent"], t["textSecondary"], STATUS["info"], STATUS["success"]]),
    }
