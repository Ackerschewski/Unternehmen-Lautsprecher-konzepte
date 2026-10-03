"""Shared light and dark appearance for the assistant UI."""
from __future__ import annotations


def stylesheet(mode: str) -> str:
    dark = mode == "dark"
    bg, card, ink, muted, border, accent, selection = (
        ("#111827", "#1f2937", "#f9fafb", "#b6c2d1", "#374151", "#60a5fa", "#243b55")
        if dark else
        ("#f3f6fa", "#ffffff", "#17243a", "#52627a", "#d9e2ed", "#1769b3", "#eaf4ff")
    )
    return f"""
        QMainWindow, QDialog {{background:{bg}; color:{ink};}}
        QWidget {{color:{ink}; font-family:'Segoe UI'; font-size:13px;}}
        QLabel#title {{font-size:25px; font-weight:700;}}
        QLabel#subtitle {{color:{muted}; font-size:14px;}}
        QLabel#section {{font-size:17px; font-weight:650;}}
        QFrame#card, QGroupBox {{background:{card}; border:1px solid {border}; border-radius:10px;}}
        QGroupBox {{margin-top:12px; padding:14px; font-weight:600;}}
        QGroupBox::title {{subcontrol-origin:margin; left:14px; padding:0 4px;}}
        QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox, QTextEdit, QListWidget {{
            background:{card}; color:{ink}; border:1px solid {border}; border-radius:7px;
            padding:6px; selection-background-color:{selection}; selection-color:{ink};
        }}
        QComboBox::drop-down {{border:0; width:22px;}}
        QPushButton {{background:{card}; color:{ink}; border:1px solid {border};
            border-radius:7px; padding:8px 13px;}}
        QPushButton:hover {{border-color:{accent};}}
        QPushButton#primary {{background:{accent}; color:white; border:0; font-weight:700;
            padding:11px 16px;}}
        QPushButton#primary:disabled {{background:{border}; color:{muted};}}
        QTabWidget::pane {{border:1px solid {border}; border-radius:8px; background:{card};}}
        QTabBar::tab {{background:{bg}; padding:10px 14px; border:1px solid {border};}}
        QTabBar::tab:selected {{background:{card}; border-bottom:2px solid {accent};}}
        QProgressBar {{border:1px solid {border}; border-radius:5px; text-align:center; background:{card};}}
        QProgressBar::chunk {{background:{accent}; border-radius:4px;}}
    """
