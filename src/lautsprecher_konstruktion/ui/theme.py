"""Stylesheet and chart style built from the ACK Studio tokens (light theme, area accent)."""
from __future__ import annotations

from cycler import cycler

from lautsprecher_konstruktion.ui.tokens import (
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


def stylesheet(mode: str = "light") -> str:
    t = theme(mode)
    ui = f"'{UI_FONT}', {UI_FALLBACK}"
    display = f"'{DISPLAY_FONT}', {DISPLAY_FALLBACK}"
    rc, rk = RADIUS_CONTROL, RADIUS_CARD
    return f"""
        QMainWindow, QDialog {{background:{t['background']}; color:{t['textPrimary']};}}
        QWidget {{color:{t['textPrimary']}; font-family:{ui}; font-size:14px;}}
        QToolTip {{background:{t['background']}; color:{t['textPrimary']}; border:1px solid {t['borderStrong']};
            padding:4px 8px;}}
        QMenuBar {{background:{t['background']}; color:{t['textPrimary']};}}
        QMenuBar::item:selected {{background:{t['band']};}}
        QMenu {{background:{t['background']}; border:1px solid {t['border']}; padding:4px;}}
        QMenu::item {{padding:8px 16px; border-radius:{RADIUS_BADGE}px;}}
        QMenu::item:selected {{background:{t['band']};}}
        QMenu::separator {{height:1px; background:{t['border']}; margin:4px 8px;}}
        QStatusBar {{background:{t['background']}; color:{t['textSecondary']}; font-size:12px;}}
        QLabel#title {{font-family:{display}; font-size:44px; font-weight:400; color:{t['textPrimary']};}}
        QLabel#subtitle {{color:{t['textSecondary']}; font-size:14px;}}
        QLabel#section {{font-family:{display}; font-size:26px; font-weight:400;}}
        QLabel#eyebrow {{color:{t['accent']}; font-size:12px; font-weight:600;}}
        QLabel#caption, QLabel#brand {{color:{t['textSecondary']}; font-size:12px;}}
        QLabel#statusLine {{padding:12px 16px; background:{t['panel']}; border:1px solid {t['border']};
            border-radius:{rc}px; font-weight:600;}}
        QLabel#statusLine[role="success"] {{border-left:4px solid {t['success']};}}
        QLabel#statusLine[role="warning"] {{border-left:4px solid {t['warning']};}}
        QLabel#statusLine[role="info"] {{border-left:4px solid {t['accent']};}}
        QLabel#statusLine[role="danger"] {{border:2px dashed {t['danger']}; border-left:4px solid {t['danger']};}}
        QLabel#kpi {{padding:12px 16px; background:{t['band']}; border:1px solid {t['border']};
            border-radius:{rc}px;}}
        QFrame#card {{background:{t['surface']}; border:none;}}
        QScrollArea {{border:none; background:transparent;}}
        QScrollArea > QWidget > QWidget {{background:transparent;}}
        QGroupBox {{border:none; border-top:1px solid {t['border']}; margin-top:14px; padding:10px 0 0 0;
            color:{t['accent']}; font-weight:600; font-size:12px;}}
        QGroupBox::title {{subcontrol-origin:margin; left:0; padding:0 8px 0 0; color:{t['accent']};}}
        QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox, QTextEdit, QPlainTextEdit, QListWidget, QTextBrowser {{
            background:{t['surfaceElevated']}; color:{t['textPrimary']}; border:1px solid {t['borderStrong']};
            border-radius:{rc}px; padding:6px 12px; selection-background-color:{t['band']};
            selection-color:{t['textPrimary']};
        }}
        QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox {{min-height:{TOUCH_TARGET - 16}px;}}
        QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus, QSpinBox:focus, QTextEdit:focus,
        QPlainTextEdit:focus, QListWidget:focus {{border:2px solid {t['accent']};}}
        QLineEdit:disabled, QComboBox:disabled, QDoubleSpinBox:disabled, QSpinBox:disabled {{
            background:{t['disabledSurface']}; color:{t['disabledText']}; border-color:{t['border']};}}
        QComboBox::drop-down {{border:0; width:24px;}}
        QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {{
            subcontrol-origin:border; width:20px; background:{t['band']};
            border:none; border-left:1px solid {t['border']};
        }}
        QAbstractSpinBox::up-button {{subcontrol-position:top right; border-top-right-radius:{rc}px;}}
        QAbstractSpinBox::down-button {{subcontrol-position:bottom right; border-bottom-right-radius:{rc}px;}}
        QComboBox QAbstractItemView {{background:{t['surfaceElevated']}; border:1px solid {t['borderStrong']};
            selection-background-color:{t['band']}; selection-color:{t['textPrimary']};}}
        QPushButton {{background:{t['surface']}; color:{t['accent']}; border:1px solid {t['accent']};
            border-radius:{rc}px; padding:8px 20px; min-height:{TOUCH_TARGET - 20}px; font-weight:600;}}
        QPushButton:hover {{background:{t['band']};}}
        QPushButton:pressed {{background:{t['panel']};}}
        QPushButton:focus {{border:3px solid {t['accent']}; padding:6px 18px;}}
        QPushButton:disabled {{background:{t['surface']}; color:{t['disabledText']};
            border-color:{t['border']};}}
        QPushButton#primary {{background:{t['accent']}; color:{t['onAccent']}; border:1px solid {t['accent']};
            padding:10px 20px;}}
        QPushButton#primary:hover {{background:{t['accentHover']}; border-color:{t['accentHover']};}}
        QPushButton#primary:pressed {{background:{t['accentPressed']}; border-color:{t['accentPressed']};}}
        QPushButton#primary:focus {{border:3px solid {t['textPrimary']}; padding:8px 18px;}}
        QPushButton#primary:disabled {{background:{t['disabledSurface']}; color:{t['disabledText']};
            border-color:{t['border']};}}
        QPushButton#choiceCard, QPushButton#variantCard {{
            text-align:left; padding:12px 14px; background:{t['surfaceElevated']};
            color:{t['textPrimary']}; border:1px solid {t['border']};
            border-radius:{rk}px; font-weight:600;
        }}
        QPushButton#choiceCard:hover, QPushButton#variantCard:hover {{
            background:{t['band']}; border-color:{t['borderStrong']};
        }}
        QPushButton#choiceCard:checked, QPushButton#variantCard:checked {{
            background:{t['accentSubtle']}; border:2px solid {t['accent']}; color:{t['textPrimary']};
        }}
        QFrame#variantCard {{background:{t['surfaceElevated']}; border:1px solid {t['border']}; border-radius:{rk}px;}}
        QFrame#variantCard:hover {{background:{t['band']}; border-color:{t['borderStrong']};}}
        QFrame#variantCard:focus {{border:2px solid {t['textPrimary']};}}
        QFrame#variantCard[selected="true"] {{background:{t['accentSubtle']}; border:2px solid {t['accent']};}}
        QLabel#variantTitle {{font-weight:700; font-size:15px; color:{t['textPrimary']};}}
        QLabel#variantTag {{font-weight:600; color:{t['textSecondary']};}}
        QLabel#metricChip {{background:{t['band']}; color:{t['textPrimary']}; border:1px solid {t['border']};
            border-radius:9px; padding:1px 6px; font-size:11px;}}
        QLabel#metricChip[tone="ok"] {{border-color:{t['success']};}}
        QLabel#metricChip[tone="warn"] {{border-color:{t['warning']};}}
        QLabel#metricChip[tone="bad"] {{border-color:{t['danger']}; font-weight:600;}}
        QFrame#resultSidebar {{
            background:{t['surfaceElevated']}; border:1px solid {t['border']};
            border-radius:{rk}px;
        }}
        QLabel#emptyState {{
            background:{t['surfaceElevated']}; color:{t['textPrimary']};
            border:1px solid {t['border']}; border-radius:{rk}px; padding:18px 22px;
        }}
        QLabel#recommendation {{
            background:{t['band']}; color:{t['textPrimary']};
            border-radius:{rc}px; padding:12px 14px;
        }}
        QPushButton#variantChip {{background:{t['surfaceElevated']}; color:{t['textPrimary']};
            border:1px solid {t['border']}; border-radius:{rc}px; padding:6px 12px; text-align:left;
            font-weight:500; font-size:12px; min-height:34px;}}
        QPushButton#variantChip:hover {{background:{t['band']}; border-color:{t['borderStrong']};}}
        QPushButton#variantChip:checked {{background:{t['accentSubtle']}; border:2px solid {t['accent']};
            padding:5px 11px;}}
        QFrame#kpiCard {{background:{t['surfaceElevated']}; border:1px solid {t['border']}; border-radius:{rc}px;}}
        QLabel#kpiLabel {{color:{t['textSecondary']}; font-size:11px; font-weight:600; background:transparent;}}
        QLabel#kpiValue {{color:{t['textPrimary']}; font-size:15px; font-weight:600; background:transparent;}}
        QFrame#diagnosticCard {{background:{t['surfaceElevated']}; border:1px solid {t['border']};
            border-left:4px solid {t['danger']}; border-radius:{rk}px;}}
        QLabel#diagnosticMain {{font-size:16px; font-weight:600; background:transparent;}}
        QPushButton#suggestion {{background:{t['accentSubtle']}; color:{t['textPrimary']};
            border:1px solid {t['accent']}; text-align:left; padding:10px 16px;}}
        QPushButton#suggestion:hover {{background:{t['band']};}}
        QMainWindow[compact="true"] QLabel#title {{font-size:28px;}}
        QMainWindow[compact="true"] QLineEdit, QMainWindow[compact="true"] QComboBox,
        QMainWindow[compact="true"] QDoubleSpinBox, QMainWindow[compact="true"] QSpinBox {{
            min-height:20px; padding:3px 10px;}}
        QMainWindow[compact="true"] QPushButton {{min-height:18px; padding:5px 14px;}}
        QMainWindow[compact="true"] QPushButton#primary {{padding:7px 14px;}}
        QMainWindow[compact="true"] QPushButton#variantChip {{min-height:30px; padding:3px 10px;}}
        QMainWindow[compact="true"] QLabel#statusLine {{padding:6px 14px;}}
        QLabel#pageTitle {{font-family:{display}; font-size:28px; font-weight:400; background:transparent;}}
        QTabBar::tab:disabled {{color:{t['disabledText']};}}
        QTabBar::tab:disabled:hover {{color:{t['disabledText']};}}
        QCheckBox {{spacing:8px; min-height:24px;}}
        QCheckBox::indicator {{width:18px; height:18px; border:1px solid {t['borderStrong']};
            border-radius:{RADIUS_BADGE}px; background:{t['surface']};}}
        QCheckBox::indicator:checked {{background:{t['accent']}; border-color:{t['accent']};}}
        QCheckBox::indicator:focus {{border:2px solid {t['accent']};}}
        QTabWidget::pane {{border:none; border-top:1px solid {t['border']}; background:{t['surface']};}}
        QTabBar::tab {{background:transparent; color:{t['textSecondary']}; padding:12px 16px; border:none;
            border-bottom:3px solid transparent; font-weight:600;}}
        QTabBar::tab:hover {{color:{t['accent']};}}
        QTabBar::tab:selected {{color:{t['accent']}; border-bottom:3px solid {t['accent']};}}
        QTabBar::tab:focus {{background:{t['band']};}}
        QHeaderView::section {{background:{t['band']}; color:{t['textPrimary']}; border:none;
            border-bottom:1px solid {t['border']}; padding:8px 12px; font-weight:600;}}
        QTableWidget {{background:{t['surface']}; alternate-background-color:{t['surfaceElevated']};
            gridline-color:{t['border']}; border:1px solid {t['border']}; border-radius:{rk}px;}}
        QTableWidget::item:selected, QListWidget::item:selected {{background:{t['band']};
            color:{t['textPrimary']};}}
        QProgressBar {{border:1px solid {t['borderStrong']}; border-radius:{rc}px; text-align:center;
            background:{t['surfaceElevated']}; color:{t['textPrimary']}; height:18px;}}
        QProgressBar::chunk {{background:{t['accent']}; border-radius:{rc - 1}px;}}
        QScrollBar:vertical {{background:transparent; width:10px;}}
        QScrollBar::handle:vertical {{background:{t['border']}; border-radius:5px; min-height:24px;}}
        QScrollBar:horizontal {{background:transparent; height:10px;}}
        QScrollBar::handle:horizontal {{background:{t['border']}; border-radius:5px; min-width:24px;}}
        QScrollBar::add-line, QScrollBar::sub-line {{width:0; height:0;}}
        QMenu {{
            background:{t['surfaceElevated']}; color:{t['textPrimary']};
            border:1px solid {t['border']}; padding:6px;
        }}
        QMenu::item {{padding:8px 26px 8px 12px; border-radius:{RADIUS_BADGE}px;}}
        QMenu::item:selected {{background:{t['band']}; color:{t['textPrimary']};}}
        QToolTip {{
            background:{t['surfaceElevated']}; color:{t['textPrimary']};
            border:1px solid {t['borderStrong']}; padding:6px 8px;
        }}
        QSplitter::handle {{background:{t['border']}; width:1px;}}
    """


def chart_rc(mode: str = "light") -> dict[str, object]:
    """Matplotlib rcParams using the current semantic software theme."""
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
