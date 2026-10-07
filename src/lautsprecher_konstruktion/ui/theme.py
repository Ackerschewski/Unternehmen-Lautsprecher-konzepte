"""Stylesheet and chart style built from the ACK Studio tokens (light theme, area accent)."""
from __future__ import annotations

import tempfile
from pathlib import Path

from cycler import cycler

from lautsprecher_konstruktion.ui.tokens import (
    AREAS,
    DISPLAY_FALLBACK,
    DISPLAY_FONT,
    RADIUS_BADGE,
    RADIUS_CARD,
    RADIUS_CONTROL,
    TOUCH_TARGET,
    UI_FALLBACK,
    UI_FONT,
    theme,
)

_ASSETS = {
    "up": '<path d="M2 7 L5 3.5 L8 7" fill="none" stroke="{c}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>',
    "down": '<path d="M2 3.5 L5 7 L8 3.5" fill="none" stroke="{c}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>',
    "check": '<path d="M2 5.2 L4.2 7.4 L8 2.8" fill="none" stroke="{c}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',
    "right": '<path d="M3.5 2 L7 5 L3.5 8" fill="none" stroke="{c}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>',
}


def _asset(name: str, color: str) -> str:
    """Path of a small SVG control glyph in the given colour (Qt style sheets can only reference files)."""
    folder = Path(tempfile.gettempdir()) / "lautsprecher-konstruktion-ui"
    path = folder / f"{name}-{color.lstrip('#')}.svg"
    try:
        if not path.exists():
            folder.mkdir(parents=True, exist_ok=True)
            path.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 10 10">'
                            + _ASSETS[name].format(c=color) + "</svg>", encoding="utf-8")
    except OSError:
        return "none"
    return f"url({path.as_posix()})"


def stylesheet(mode: str = "light") -> str:
    t = theme(mode)
    ui = f"'{UI_FONT}', {UI_FALLBACK}"
    display = f"'{DISPLAY_FONT}', {DISPLAY_FALLBACK}"
    rc, rk = RADIUS_CONTROL, RADIUS_CARD
    up, down = _asset("up", t["textPrimary"]), _asset("down", t["textPrimary"])
    check = _asset("check", t["onAccent"])
    doc_ok, doc_critical = AREAS["apparel"]["accent"], AREAS["jewelry"]["accent"]  # on paper cards in both modes
    return f"""
        QMainWindow, QDialog {{background:{t['background']}; color:{t['textPrimary']};}}
        QWidget {{color:{t['textPrimary']}; font-family:{ui}; font-size:14px;}}
        QToolTip {{background:{t['panel']}; color:{t['textPrimary']}; border:1px solid {t['borderStrong']};
            padding:4px 8px;}}
        QMenuBar {{background:{t['background']}; color:{t['textPrimary']}; padding:2px 8px;}}
        QMenuBar::item {{padding:6px 10px; border-radius:{RADIUS_BADGE}px; background:transparent;}}
        QMenuBar::item:selected {{background:{t['band']};}}
        QMenu {{background:{t['panel']}; border:1px solid {t['border']}; border-radius:{rc}px; padding:6px;}}
        QMenu::item {{padding:8px 24px 8px 16px; border-radius:{RADIUS_BADGE}px;}}
        QMenu::item:selected {{background:{t['band']};}}
        QMenu::item:disabled {{color:{t['disabledText']};}}
        QMenu::separator {{height:1px; background:{t['border']}; margin:4px 8px;}}
        QStatusBar {{background:{t['background']}; color:{t['textSecondary']}; font-size:12px;}}
        QStatusBar::item {{border:none;}}
        QLabel {{background:transparent;}}
        QLabel#title {{font-family:{display}; font-size:34px; font-weight:400; color:{t['textPrimary']};}}
        QLabel#pageTitle {{font-family:{display}; font-size:30px; font-weight:400; color:{t['textPrimary']};}}
        QLabel#subtitle {{color:{t['textSecondary']}; font-size:14px;}}
        QLabel#section {{font-family:{display}; font-size:24px; font-weight:400;}}
        QLabel#eyebrow {{color:{t['accent']}; font-size:12px; font-weight:600; letter-spacing:1px;}}
        QLabel#caption, QLabel#brand {{color:{t['textSecondary']}; font-size:12px;}}
        QLabel#hint {{color:{t['textSecondary']}; font-size:13px;}}
        QLabel#stepNumber {{background:{t['accent']}; color:{t['onAccent']}; border-radius:12px; font-weight:700;
            font-size:13px; min-width:24px; max-width:24px; min-height:24px; max-height:24px;}}
        QLabel#statusLine {{padding:10px 16px; background:{t['panel']}; border:none; border-left:4px solid {t['accent']};
            border-radius:{rc}px; font-weight:600;}}
        QLabel#statusLine[role="success"] {{border-left:4px solid {t['success']};}}
        QLabel#statusLine[role="warning"] {{border-left:4px solid {t['ochre']};}}
        QLabel#statusLine[role="danger"] {{border:2px dashed {t['danger']};}}
        QLabel#staleChip {{padding:4px 10px; background:{t['band']}; color:{t['textPrimary']};
            border:1px dashed {t['ochre']}; border-radius:{RADIUS_BADGE + 4}px; font-weight:600; font-size:12px;}}
        QLabel#fieldError {{color:{t['danger']}; font-size:12px; font-weight:600;}}
        QLabel#kpiLabel {{color:{t['textSecondary']}; font-size:12px; font-weight:600;}}
        QLabel#kpiValue {{font-size:18px; font-weight:600;}}
        QLabel#kpiNote {{color:{t['textSecondary']}; font-size:12px;}}
        QLabel#badge {{background:{t['band']}; color:{t['textPrimary']}; border-radius:{RADIUS_BADGE + 2}px;
            padding:2px 8px; font-size:12px; font-weight:600;}}
        QLabel#valid {{color:{t['success']}; font-weight:600;}}
        QLabel#critical {{color:{t['danger']}; font-weight:600;}}
        QFrame#card {{background:{t['background']}; border:none;}}
        QFrame#sidePanel {{background:{t['panel']}; border:none; border-radius:{rk}px;}}
        QFrame#surfaceCard {{background:{t['panel']}; border:none; border-radius:{rk}px;}}
        QFrame#navbar {{background:transparent; border:none; border-bottom:1px solid {t['border']};}}
        QPushButton#navButton {{background:transparent; color:{t['textSecondary']}; border:none;
            border-bottom:3px solid transparent; border-radius:0; padding:10px 16px; font-weight:600; min-height:20px;}}
        QPushButton#navButton:hover {{color:{t['textPrimary']}; background:transparent;}}
        QPushButton#navButton:checked {{color:{t['accent']}; border-bottom:3px solid {t['accent']};}}
        QPushButton#navButton:focus {{background:{t['band']}; padding:10px 16px;}}
        QPushButton#navButton:disabled {{color:{t['disabledText']}; background:transparent; border-color:transparent;}}
        QFrame#paperCard, QFrame#variantCard {{background:{t['docSurface']}; border:1px solid {t['docLine']};
            border-radius:{rk}px;}}
        QFrame#variantCard[selected="true"] {{border:2px solid {t['docAccent']};}}
        QFrame#paperCard QLabel, QFrame#variantCard QLabel {{color:{t['docInk']};}}
        QFrame#paperCard QLabel#caption, QFrame#variantCard QLabel#caption,
        QFrame#variantCard QLabel#kpiLabel, QFrame#variantCard QLabel#kpiNote {{color:{t['docMuted']};}}
        QFrame#variantCard QLabel#eyebrow {{color:{t['docAccent']};}}
        QFrame#variantCard QLabel#badge {{background:{t['docBand']}; color:{t['docInk']};}}
        QFrame#variantCard QLabel#valid {{color:{doc_ok};}}
        QFrame#variantCard QLabel#critical {{color:{doc_critical};}}
        QFrame#variantCard QPushButton {{background:{t['docSurface']}; color:{t['docAccent']};
            border:1px solid {t['docAccent']};}}
        QFrame#variantCard QPushButton:hover {{background:{t['docBand']};}}
        QPushButton#choiceCard {{background:{t['panel']}; color:{t['textPrimary']}; border:1px solid {t['border']};
            border-radius:{rk}px; padding:12px 14px; text-align:left; font-weight:600; min-height:44px;}}
        QPushButton#choiceCard:hover {{background:{t['band']}; border-color:{t['borderStrong']};}}
        QPushButton#choiceCard:checked {{background:{t['band']}; border:2px solid {t['accent']}; padding:11px 13px;
            color:{t['textPrimary']};}}
        QPushButton#choiceCard:focus {{border:2px solid {t['accent']}; padding:11px 13px;}}
        QToolButton#disclosure {{background:transparent; border:none; color:{t['textPrimary']}; font-weight:600;
            padding:6px 4px; text-align:left;}}
        QToolButton#disclosure:hover {{color:{t['accent']};}}
        QToolButton#disclosure:focus {{background:{t['band']}; border-radius:{RADIUS_BADGE}px;}}
        QPushButton#ghost {{background:transparent; border:1px solid transparent; color:{t['accent']};
            padding:6px 10px;}}
        QPushButton#ghost:hover {{background:{t['band']};}}
        QPushButton#chip {{background:{t['panel']}; color:{t['textPrimary']}; border:1px solid {t['border']};
            border-radius:{rc + 4}px; padding:4px 12px; font-size:15px; font-weight:500; min-height:24px;}}
        QPushButton#chip:hover {{background:{t['band']};}}
        QPushButton#chip:checked {{background:{t['band']}; border:1px solid {t['accent']}; color:{t['textPrimary']};}}
        QPushButton#variantChip {{background:{t['panel']}; color:{t['textPrimary']}; border:1px solid {t['border']};
            border-radius:{rc + 4}px; padding:4px 14px; font-weight:600; min-height:24px;}}
        QPushButton#variantChip:hover {{background:{t['band']};}}
        QPushButton#variantChip:checked {{background:{t['accent']}; color:{t['onAccent']}; border-color:{t['accent']};}}
        QFrame#marker {{border:2px solid {t['accent']}; border-radius:4px; background:transparent;}}
        QScrollArea {{border:none; background:transparent;}}
        QScrollArea > QWidget > QWidget {{background:transparent;}}
        QGroupBox {{border:none; border-top:1px solid {t['border']}; margin-top:14px; padding:10px 0 0 0;
            color:{t['accent']}; font-weight:600; font-size:12px;}}
        QGroupBox::title {{subcontrol-origin:margin; left:0; padding:0 8px 0 0; color:{t['accent']};}}
        QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox, QTextEdit, QPlainTextEdit, QListWidget, QTextBrowser {{
            background:{t['background']}; color:{t['textPrimary']}; border:1px solid {t['borderStrong']};
            border-radius:{rc}px; padding:5px 10px; selection-background-color:{t['accent']};
            selection-color:{t['onAccent']};
        }}
        QTextBrowser {{border:none; background:transparent; padding:0;}}
        QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox {{min-height:{TOUCH_TARGET - 16}px;}}
        QLineEdit:hover, QComboBox:hover, QDoubleSpinBox:hover, QSpinBox:hover {{border-color:{t['accent']};}}
        QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus, QSpinBox:focus, QTextEdit:focus,
        QPlainTextEdit:focus, QListWidget:focus {{border:2px solid {t['accent']}; padding:4px 9px;}}
        QLineEdit[error="true"], QComboBox[error="true"], QDoubleSpinBox[error="true"], QSpinBox[error="true"] {{
            border:2px solid {t['danger']}; padding:4px 9px;}}
        QLineEdit:disabled, QComboBox:disabled, QDoubleSpinBox:disabled, QSpinBox:disabled {{
            background:{t['disabledSurface']}; color:{t['disabledText']}; border-color:{t['border']};}}
        QDoubleSpinBox, QSpinBox {{padding-right:26px;}}
        QDoubleSpinBox::up-button, QSpinBox::up-button {{subcontrol-origin:border; subcontrol-position:top right;
            width:22px; border:none; border-left:1px solid {t['border']}; border-top-right-radius:{rc}px;
            background:transparent; margin:1px 1px 0 0;}}
        QDoubleSpinBox::down-button, QSpinBox::down-button {{subcontrol-origin:border; subcontrol-position:bottom right;
            width:22px; border:none; border-left:1px solid {t['border']}; border-bottom-right-radius:{rc}px;
            background:transparent; margin:0 1px 1px 0;}}
        QDoubleSpinBox::up-button:hover, QSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover,
        QSpinBox::down-button:hover {{background:{t['band']};}}
        QDoubleSpinBox::up-button:pressed, QSpinBox::up-button:pressed, QDoubleSpinBox::down-button:pressed,
        QSpinBox::down-button:pressed {{background:{t['accent']};}}
        QDoubleSpinBox::up-arrow, QSpinBox::up-arrow {{image:{up}; width:10px; height:10px;}}
        QDoubleSpinBox::down-arrow, QSpinBox::down-arrow {{image:{down}; width:10px; height:10px;}}
        QComboBox {{padding-right:30px;}}
        QComboBox::drop-down {{subcontrol-origin:border; subcontrol-position:center right; width:26px; border:none;
            border-left:1px solid {t['border']}; border-top-right-radius:{rc}px; border-bottom-right-radius:{rc}px;}}
        QComboBox::down-arrow {{image:{down}; width:10px; height:10px;}}
        QComboBox QAbstractItemView {{background:{t['panel']}; color:{t['textPrimary']}; border:1px solid {t['borderStrong']};
            border-radius:{RADIUS_BADGE}px; padding:4px; outline:0; selection-background-color:{t['band']};
            selection-color:{t['textPrimary']};}}
        QComboBox QAbstractItemView::item {{min-height:28px; padding:2px 8px; border-radius:{RADIUS_BADGE}px;}}
        QComboBox QAbstractItemView::item:disabled {{color:{t['disabledText']};}}
        QPushButton {{background:{t['background']}; color:{t['accent']}; border:1px solid {t['accent']};
            border-radius:{rc}px; padding:8px 20px; min-height:{TOUCH_TARGET - 20}px; font-weight:600;}}
        QPushButton:hover {{background:{t['band']};}}
        QPushButton:pressed {{background:{t['panel']};}}
        QPushButton:focus {{border:3px solid {t['accent']}; padding:6px 18px;}}
        QPushButton:disabled {{background:{t['background']}; color:{t['disabledText']};
            border-color:{t['border']};}}
        QPushButton#primary {{background:{t['accent']}; color:{t['onAccent']}; border:1px solid {t['accent']};
            padding:10px 24px; font-size:15px;}}
        QPushButton#primary:hover {{background:{t['accentHover']}; border-color:{t['accentHover']};}}
        QPushButton#primary:pressed {{background:{t['accentPressed']}; border-color:{t['accentPressed']};}}
        QPushButton#primary:focus {{border:3px solid {t['textPrimary']}; padding:8px 22px;}}
        QPushButton#primary:disabled {{background:{t['disabledSurface']}; color:{t['disabledText']};
            border-color:{t['border']};}}
        QCheckBox {{spacing:8px; min-height:24px;}}
        QCheckBox::indicator {{width:18px; height:18px; border:1px solid {t['borderStrong']};
            border-radius:{RADIUS_BADGE}px; background:{t['background']};}}
        QCheckBox::indicator:hover {{border-color:{t['accent']};}}
        QCheckBox::indicator:checked {{background:{t['accent']}; border-color:{t['accent']}; image:{check};}}
        QCheckBox::indicator:focus {{border:2px solid {t['accent']};}}
        QGroupBox::indicator {{width:16px; height:16px; border:1px solid {t['borderStrong']};
            border-radius:{RADIUS_BADGE}px; background:{t['background']};}}
        QGroupBox::indicator:checked {{background:{t['accent']}; border-color:{t['accent']}; image:{check};}}
        QTabWidget::pane {{border:none; border-top:1px solid {t['border']}; background:{t['background']};}}
        QTabBar::tab {{background:transparent; color:{t['textSecondary']}; padding:12px 16px; border:none;
            border-bottom:3px solid transparent; font-weight:600;}}
        QTabBar::tab:hover {{color:{t['accent']};}}
        QTabBar::tab:selected {{color:{t['accent']}; border-bottom:3px solid {t['accent']};}}
        QTabBar::tab:focus {{background:{t['band']};}}
        QHeaderView {{background:{t['band']}; border:none;}}
        QHeaderView::section {{background:{t['band']}; color:{t['textPrimary']}; border:none;
            border-bottom:1px solid {t['border']}; padding:8px 12px; font-weight:600;}}
        QTableWidget, QTableView {{background:{t['background']}; alternate-background-color:{t['panel']};
            gridline-color:{t['border']}; border:1px solid {t['border']}; border-radius:{rk}px;
            selection-background-color:{t['band']}; selection-color:{t['textPrimary']}; outline:0;}}
        QTableCornerButton::section {{background:{t['band']}; border:none;}}
        QTableWidget::item, QTableView::item {{padding:4px 8px;}}
        QTableWidget::item:selected, QListWidget::item:selected {{background:{t['band']};
            color:{t['textPrimary']};}}
        QTableWidget::item:focus {{outline:0; border:none;}}
        QListWidget {{outline:0; padding:4px;}}
        QListWidget::item {{padding:6px 8px; border-radius:{RADIUS_BADGE}px;}}
        QListWidget::item:hover {{background:{t['panel']};}}
        QListWidget::item:selected {{background:{t['band']}; color:{t['textPrimary']};}}
        QListWidget#viewNav {{background:transparent; border:none; padding:0;}}
        QListWidget#viewNav::item {{padding:8px 10px; margin:1px 0;}}
        QListWidget#viewNav::item:selected {{background:{t['band']}; color:{t['textPrimary']};
            border-left:3px solid {t['accent']};}}
        QProgressBar {{border:none; border-radius:4px; text-align:center;
            background:{t['band']}; color:{t['textPrimary']}; height:8px; max-height:8px;}}
        QProgressBar::chunk {{background:{t['accent']}; border-radius:4px;}}
        QProgressBar#metric {{height:6px; max-height:6px;}}
        QScrollBar:vertical {{background:transparent; width:12px; margin:0;}}
        QScrollBar::handle:vertical {{background:{t['borderStrong']}; border-radius:4px; min-height:32px; margin:2px 3px;}}
        QScrollBar::handle:vertical:hover {{background:{t['accent']};}}
        QScrollBar:horizontal {{background:transparent; height:12px; margin:0;}}
        QScrollBar::handle:horizontal {{background:{t['borderStrong']}; border-radius:4px; min-width:32px; margin:3px 2px;}}
        QScrollBar::handle:horizontal:hover {{background:{t['accent']};}}
        QScrollBar::add-line, QScrollBar::sub-line {{width:0; height:0; background:none; border:none;}}
        QScrollBar::add-page, QScrollBar::sub-page {{background:transparent;}}
        QSplitter::handle {{background:transparent;}}
        QSplitter::handle:hover {{background:{t['border']};}}
        QMessageBox, QDialog {{background:{t['background']};}}
    """.replace("{doc_ok}", t["success"] if mode == "light" else AREAS["apparel"]["accent"]).replace(
        "{doc_critical}", t["danger"] if mode == "light" else AREAS["jewelry"]["accent"])


def chart_rc(mode: str = "light") -> dict[str, object]:
    """Matplotlib rcParams: warm paper, fine rules, the area accent for the primary curve."""
    t = theme(mode)
    return {
        "figure.facecolor": t["surface"], "axes.facecolor": t["surface"], "savefig.facecolor": t["surface"],
        "axes.edgecolor": t["border"], "axes.labelcolor": t["textSecondary"], "axes.titlecolor": t["textPrimary"],
        "text.color": t["textPrimary"], "xtick.color": t["textSecondary"], "ytick.color": t["textSecondary"],
        "grid.color": t["border"], "grid.alpha": 1.0, "grid.linewidth": 0.7, "axes.grid": True,
        "axes.spines.top": False, "axes.spines.right": False, "axes.titlesize": 12, "axes.titleweight": "bold",
        "axes.labelsize": 11, "font.family": [UI_FONT, "DejaVu Sans"], "legend.frameon": False,
        "legend.fontsize": 10,
        "axes.prop_cycle": cycler(color=[t["accent"], t["textSecondary"], t["textPrimary"]]),
    }
