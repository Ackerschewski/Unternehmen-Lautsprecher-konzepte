"""Design tokens of the Ackerschewski_code Design System (profile for desktop programs).

Source of truth: repository Basis-Ackerschewski-Design-System (docs/COLORS.md, docs/TYPOGRAPHY.md,
docs/SPACING_AND_LAYOUT.md). A snapshot of its tokens file lives in docs/design/ and a test keeps this
module in sync with it. Colours are semantic roles, never per-component values.
"""
from __future__ import annotations

from typing import Final

ACCENT: Final = "#F27216"
SPACING: Final = (4, 8, 12, 16, 24, 32, 48)
RADIUS_PX: Final = 4

UI_FONT: Final = "Inter"
ACCENT_FONT: Final = "Source Serif 4"
MONO_FONT: Final = "JetBrains Mono"
UI_FALLBACK: Final = "'Segoe UI', 'Helvetica Neue', Arial, sans-serif"
ACCENT_FALLBACK: Final = "Georgia, serif"
MONO_FALLBACK: Final = "Consolas, 'Courier New', monospace"

THEMES: Final[dict[str, dict[str, str]]] = {
    "light": {
        "background": "#F5F5F5", "surface": "#FFFFFF", "surfaceElevated": "#FAFAFA",
        "textPrimary": "#1A1A1A", "textSecondary": "#666666", "border": "#DDDDDD", "accent": ACCENT,
        # derived from the accent; contrast is checked by tests
        "accentHover": "#D9640F", "accentPressed": "#BF570C", "accentSubtle": "#FDEBDD",
        "disabledText": "#9A9A9A", "disabledSurface": "#EDEDED",
    },
    "dark": {
        "background": "#121212", "surface": "#1A1A1A", "surfaceElevated": "#232323",
        "textPrimary": "#F2F2F2", "textSecondary": "#A8A8A8", "border": "#333333", "accent": ACCENT,
        "accentHover": "#FF8230", "accentPressed": "#D9640F", "accentSubtle": "#3A2414",
        "disabledText": "#6E6E6E", "disabledSurface": "#202020",
    },
}

STATUS: Final = {"success": "#22C55E", "warning": "#F59E0B", "danger": "#EF4444", "info": "#3B82F6"}
STATUS_GLYPH: Final = {"success": "✓", "warning": "⚠", "danger": "✕", "info": "ℹ"}


def theme(mode: str) -> dict[str, str]:
    return THEMES["dark" if mode == "dark" else "light"]


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


def text_on(background: str, light: str = "#FFFFFF", dark: str = "#1A1A1A") -> str:
    """The better readable of two text colours on the given background."""
    return light if contrast(background, light) >= contrast(background, dark) else dark


def status_line(role: str, text: str) -> str:
    """Status as glyph plus text; colour is never the only signal."""
    return f"{STATUS_GLYPH[role]} {text}"
