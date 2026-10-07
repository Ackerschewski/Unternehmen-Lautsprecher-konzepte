"""ACK Studio design tokens for the loudspeaker application.

The product belongs to the ACK Studio *software* world. Construction ochre remains
available as a secondary technical colour, but it is not the default interaction
accent. Dark mode uses a neutral charcoal/navy hierarchy rather than one flat blue
surface.
"""
from __future__ import annotations

import colorsys
from typing import Final

PAPER: Final = "#fbfaf7"
INK: Final = "#282723"
MUTED: Final = "#65615d"
LINE: Final = "#e2ddd5"
ON_ACCENT: Final = "#ffffff"

AREAS: Final[dict[str, dict[str, str]]] = {
    "jewelry": {"accent": "#471b28", "panel": "#f5ecee", "band": "#f1e5e8"},
    "apparel": {"accent": "#293b30", "panel": "#eef2ec", "band": "#e7ede4"},
    "construction": {"accent": "#735419", "panel": "#f7f1e4", "band": "#f0e7d0"},
    "software": {"accent": "#172d46", "panel": "#edf2f7", "band": "#e4edf5"},
}
DEFAULT_AREA: Final = "software"

SOFTWARE_DARK_ACCENT: Final = "#adcadb"
SOFTWARE_LINE: Final = "#4c6a83"
CONSTRUCTION_SECONDARY: Final = "#a17c2d"

SPACING: Final = (4, 8, 12, 16, 24, 32, 48, 64, 80)
RADIUS_CONTROL: Final = 8
RADIUS_CARD: Final = 14
RADIUS_BADGE: Final = 4
TOUCH_TARGET: Final = 44

UI_FONT: Final = "Inter"
DISPLAY_FONT: Final = "Cormorant Garamond"
UI_FALLBACK: Final = "Arial, sans-serif"
DISPLAY_FALLBACK: Final = "Georgia, serif"

STATUS_GLYPH: Final = {"success": "✓", "warning": "⚠", "danger": "✕", "info": "ℹ"}

_area = DEFAULT_AREA


def set_area(area: str) -> None:
    global _area
    if area not in AREAS:
        raise ValueError(f"unknown area: {area}")
    _area = area


def area() -> str:
    return _area


def _mix(a: str, b: str, share: float) -> str:
    channels = [
        round(int(a[i:i + 2], 16) * (1 - share) + int(b[i:i + 2], 16) * share)
        for i in (1, 3, 5)
    ]
    return "#" + "".join(f"{c:02x}" for c in channels)


DARK_BACKGROUND: Final = "#11161d"
DARK_PAPER: Final = DARK_BACKGROUND  # compatibility alias for existing tests/settings
DARK_SURFACE: Final = "#151c25"
DARK_PANEL: Final = "#1b2530"
DARK_BAND: Final = "#223141"
DARK_INK: Final = "#f0f3f6"
DARK_MUTED: Final = "#a7b2bf"
DARK_LINE: Final = "#344455"
MODES: Final = ("light", "dark")


def _lighten(color: str, backgrounds: tuple[str, ...], minimum: float = 4.5) -> str:
    h, lightness, sat = colorsys.rgb_to_hls(*(int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)))
    result = color
    while min(contrast(result, bg) for bg in backgrounds) < minimum and lightness < 0.95:
        lightness += 0.01
        result = "#" + "".join(
            f"{round(c * 255):02x}" for c in colorsys.hls_to_rgb(h, lightness, sat)
        )
    return result


def theme(mode: str = "light") -> dict[str, str]:
    """Return semantic roles for the selected ACK Studio product world."""
    a = AREAS[_area]
    green = AREAS["apparel"]["accent"]
    burgundy = AREAS["jewelry"]["accent"]
    if mode == "dark":
        grounds = (DARK_BACKGROUND, DARK_SURFACE, DARK_PANEL, DARK_BAND)
        accent = SOFTWARE_DARK_ACCENT if _area == "software" else _lighten(a["accent"], grounds, 4.8)
        return {
            "background": DARK_BACKGROUND,
            "surface": DARK_SURFACE,
            "surfaceElevated": DARK_PANEL,
            "panel": DARK_PANEL,
            "band": DARK_BAND,
            "textPrimary": DARK_INK,
            "textSecondary": DARK_MUTED,
            "border": DARK_LINE,
            "borderStrong": SOFTWARE_LINE,
            "accent": accent,
            "onAccent": DARK_BACKGROUND,
            "accentHover": _mix(accent, "#ffffff", 0.12),
            "accentPressed": _mix(accent, DARK_BACKGROUND, 0.18),
            "accentSubtle": DARK_BAND,
            "disabledText": _mix(DARK_MUTED, DARK_BACKGROUND, 0.50),
            "disabledSurface": DARK_PANEL,
            "paper": PAPER,
            "success": _lighten(green, grounds, 4.8),
            "danger": _lighten(burgundy, grounds, 4.8),
            "warning": _lighten(CONSTRUCTION_SECONDARY, grounds, 4.8),
            "constructionAccent": CONSTRUCTION_SECONDARY,
            "docSurface": PAPER,
            "docBand": AREAS["software"]["band"],
            "docInk": AREAS["software"]["accent"],
            "docMuted": MUTED,
            "docLine": LINE,
            "docAccent": AREAS["software"]["accent"],
        }
    return {
        "background": PAPER,
        "surface": PAPER,
        "surfaceElevated": AREAS["software"]["panel"] if _area == "software" else a["panel"],
        "panel": AREAS["software"]["panel"] if _area == "software" else a["panel"],
        "band": AREAS["software"]["band"] if _area == "software" else a["band"],
        "textPrimary": INK,
        "textSecondary": MUTED,
        "border": LINE,
        "borderStrong": SOFTWARE_LINE if _area == "software" else MUTED,
        "accent": a["accent"],
        "onAccent": ON_ACCENT,
        "accentHover": _mix(a["accent"], "#000000", 0.12),
        "accentPressed": _mix(a["accent"], "#000000", 0.24),
        "accentSubtle": AREAS["software"]["band"] if _area == "software" else a["band"],
        "disabledText": _mix(MUTED, PAPER, 0.45),
        "disabledSurface": AREAS["software"]["panel"] if _area == "software" else a["panel"],
        "paper": PAPER,
        "success": green,
        "danger": burgundy,
        "warning": CONSTRUCTION_SECONDARY,
        "constructionAccent": CONSTRUCTION_SECONDARY,
        "docSurface": PAPER,
        "docBand": AREAS["software"]["band"],
        "docInk": AREAS["software"]["accent"],
        "docMuted": MUTED,
        "docLine": LINE,
        "docAccent": AREAS["software"]["accent"],
    }


def _channel(value: int) -> float:
    c = value / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(color: str) -> float:
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast(a: str, b: str) -> float:
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def status_line(role: str, text: str) -> str:
    return f"{STATUS_GLYPH[role]} {text}"
