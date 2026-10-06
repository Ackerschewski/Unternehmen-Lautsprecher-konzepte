"""Design tokens of the ACK Studio design package (Basis-Ackerschewski-Design-System, packages/ack-studio).

The package defines one light theme with four area accents. This program is a construction tool and uses
the area "construction". Status is expressed with a glyph and text (never colour alone), as the package
prescribes; it defines no status colours. A snapshot of the package tokens lives in docs/design/ and a test
keeps this module in sync with it.
"""
from __future__ import annotations

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
DEFAULT_AREA: Final = "construction"

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
    """Blend colour a towards b by share (0..1)."""
    channels = [round(int(a[i:i + 2], 16) * (1 - share) + int(b[i:i + 2], 16) * share) for i in (1, 3, 5)]
    return "#" + "".join(f"{c:02x}" for c in channels)


def theme(mode: str = "light") -> dict[str, str]:
    """Semantic roles of the light theme in the current area (mode is accepted for compatibility)."""
    a = AREAS[_area]
    return {
        "background": PAPER, "surface": PAPER, "surfaceElevated": a["panel"], "panel": a["panel"], "band": a["band"],
        "textPrimary": INK, "textSecondary": MUTED, "border": LINE, "borderStrong": MUTED,
        "accent": a["accent"], "onAccent": ON_ACCENT,
        "accentHover": _mix(a["accent"], "#000000", 0.18), "accentPressed": _mix(a["accent"], "#000000", 0.32),
        "accentSubtle": a["band"], "disabledText": _mix(MUTED, PAPER, 0.45), "disabledSurface": a["panel"],
    }


def _channel(value: int) -> float:
    c = value / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(color: str) -> float:
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast(a: str, b: str) -> float:
    """WCAG contrast ratio of two #RRGGBB colours."""
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def status_line(role: str, text: str) -> str:
    """Status as glyph plus text; colour is never the only signal."""
    return f"{STATUS_GLYPH[role]} {text}"
