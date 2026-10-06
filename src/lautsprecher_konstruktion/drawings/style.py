"""Shared ACK Studio drawing palette and SVG CSS.

Manufacturing geometry must remain readable without colour. Colour only reinforces
semantic roles; it never carries the sole fabrication meaning.
"""
from __future__ import annotations

PAPER = "#fbfaf7"
WHITE = "#ffffff"
INK = "#172d46"
TEXT = "#30465c"
MUTED = "#657789"
LINE = "#cbd5de"
LINE_STRONG = "#4c6a83"
ACCENT = "#4c6a83"
ACCENT_DARK = "#294b67"
ACCENT_FILL = "#e4edf5"
PANEL_FILL = "#edf2f7"
SUCCESS = "#293b30"
SUCCESS_FILL = "#e7ede4"
CRITICAL = "#471b28"
CONSTRUCTION = "#735419"
CONSTRUCTION_FILL = "#f0e7d0"

FONT_UI = "'Inter',Arial,sans-serif"
FONT_DISPLAY = "'Cormorant Garamond',Georgia,serif"


def master_css() -> str:
    return (
        f"<style>.brand{{font:700 12px {FONT_UI};letter-spacing:1.5px;fill:{MUTED}}}"
        f".title{{font:600 35px {FONT_DISPLAY};fill:{INK}}}.head{{font:700 22px {FONT_UI};fill:{INK}}}"
        f".text{{font:17px {FONT_UI};fill:{TEXT}}}.small{{font:15px {FONT_UI};fill:{MUTED}}}"
        f".callout{{font:700 16px {FONT_UI};fill:{ACCENT_DARK}}}.dimlabel{{font:16px {FONT_UI};fill:{TEXT}}}"
        f".outline{{fill:{WHITE};stroke:{INK};stroke-width:2.4}}"
        f".material{{fill:{PANEL_FILL};stroke:{LINE_STRONG};stroke-width:1.4}}"
        f".brace{{fill:{SUCCESS_FILL};stroke:{SUCCESS};stroke-width:1.4;fill-opacity:.75}}"
        f".component{{fill:{ACCENT_FILL};stroke:{ACCENT_DARK};stroke-width:1.6}}"
        f".flange{{fill:none;stroke:{LINE_STRONG};stroke-width:1.5;stroke-dasharray:6 4}}"
        f".cut{{fill:none;stroke:{ACCENT_DARK};stroke-width:2}}"
        f".hole{{fill:{WHITE};stroke:{CRITICAL};stroke-width:2}}"
        f".axis{{stroke:{LINE};stroke-width:1;stroke-dasharray:5 5}}"
        f".dim{{stroke:{LINE_STRONG};stroke-width:1.3}}.rule{{stroke:{LINE};stroke-width:1}}"
        f".box{{fill:{PANEL_FILL};stroke:{LINE_STRONG};stroke-width:1.5}}</style>"
    )


def dimension_css() -> str:
    return (
        f"<style>.brand{{font:700 11px {FONT_UI};letter-spacing:1.4px;fill:{MUTED}}}"
        f".title{{font:600 28px {FONT_DISPLAY};fill:{INK}}}.label{{font:700 18px {FONT_UI};fill:{INK}}}"
        f".text{{font:15px {FONT_UI};fill:{TEXT}}}.small{{font:13px {FONT_UI};fill:{MUTED}}}"
        f".dimtext{{font:13px {FONT_UI};fill:{TEXT}}}.id{{font:700 14px {FONT_UI};fill:{ACCENT_DARK}}}"
        f".outline{{fill:{WHITE};stroke:{INK};stroke-width:2}}"
        f".dim{{fill:none;stroke:{LINE_STRONG};stroke-width:1}}"
        f".flange{{fill:{ACCENT_FILL};stroke:{LINE_STRONG};stroke-width:1.5}}"
        f".cut{{fill:none;stroke:{ACCENT_DARK};stroke-width:2}}"
        f".hole{{fill:{WHITE};stroke:{CRITICAL};stroke-width:1.4}}"
        f".panel{{fill:{PANEL_FILL};stroke:{LINE_STRONG};stroke-width:1.5}}"
        f".rule{{stroke:{LINE};stroke-width:1}}</style>"
    )


def internal_css() -> str:
    return (
        f"<style>.brand{{font:700 11px {FONT_UI};letter-spacing:1.4px;fill:{MUTED}}}"
        f".title{{font:600 28px {FONT_DISPLAY};fill:{INK}}}.sub{{font:15px {FONT_UI};fill:{MUTED}}}"
        f".head{{font:700 18px {FONT_UI};fill:{INK}}}.text{{font:15px {FONT_UI};fill:{TEXT}}}"
        f".dimtext{{font:13px {FONT_UI};fill:{TEXT}}}.dim{{fill:none;stroke:{LINE_STRONG};stroke-width:1}}"
        f".outline{{fill:{WHITE};stroke:{INK};stroke-width:2}}"
        f".panel{{fill:{PANEL_FILL};stroke:{LINE_STRONG};stroke-width:1.5}}"
        f".feature{{fill:{ACCENT_FILL};stroke:{ACCENT_DARK};stroke-width:1.5}}"
        f".rule{{stroke:{LINE};stroke-width:1}}"
        f".lining{{fill:{CONSTRUCTION_FILL};stroke:{CONSTRUCTION};stroke-width:1;stroke-dasharray:4 3}}"
        f".damper{{fill:{CONSTRUCTION_FILL};stroke:{CONSTRUCTION};stroke-width:1.5}}"
        f".hole{{fill:{WHITE};stroke:{LINE_STRONG};stroke-width:1.5}}</style>"
    )


def panel_css() -> str:
    return (
        f"<style>.brand{{font:700 11px {FONT_UI};letter-spacing:1.4px;fill:{MUTED}}}"
        f".title{{font:600 28px {FONT_DISPLAY};fill:{INK}}}.head{{font:700 19px {FONT_UI};fill:{INK}}}"
        f".text{{font:15px {FONT_UI};fill:{TEXT}}}.small{{font:13px {FONT_UI};fill:{MUTED}}}"
        f".panel{{fill:{WHITE};stroke:{INK};stroke-width:2.5}}"
        f".cut{{fill:{ACCENT_FILL};stroke:{ACCENT_DARK};stroke-width:2}}"
        f".flange{{fill:none;stroke:{LINE_STRONG};stroke-width:1.5;stroke-dasharray:5 4}}"
        f".hole{{fill:{WHITE};stroke:{CRITICAL};stroke-width:1.8}}"
        f".axis{{stroke:{LINE};stroke-width:1;stroke-dasharray:5 5}}"
        f".dim{{stroke:{LINE_STRONG};stroke-width:1.3}}.rule{{stroke:{LINE};stroke-width:1}}</style>"
    )
