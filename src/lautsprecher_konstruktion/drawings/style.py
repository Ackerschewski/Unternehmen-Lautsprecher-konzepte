"""Central colour roles of all technical drawings (ACK Studio software family on warm paper).

Renderers write role sentinels such as ``%INK%`` instead of hex values; :func:`painted` resolves them when
the drawing is returned. Colour never carries geometry information on its own: every distinction also exists
as line style, label or position, so the sheets stay readable in monochrome print.
"""
from __future__ import annotations

import re
from collections.abc import Callable
from functools import wraps
from typing import Final

from lautsprecher_konstruktion.ui import tokens

_SOFTWARE: Final = tokens.AREAS["software"]
_DEEP: Final = _SOFTWARE["accent"]  # #172d46
_PANEL: Final = "#213b56"  # website software panel
_LINE: Final = "#4c6a83"  # website software line
_LIGHT: Final = "#adcadb"  # website light software accent
_WHITE: Final = "#ffffff"


def _mix(a: str, b: str, share: float) -> str:
    return tokens._mix(a, b, share)


ROLES: Final[dict[str, str]] = {
    "WHITE": _WHITE,
    "INK": _DEEP,  # titles, outlines
    "TEXT": _PANEL,  # body text
    "MUTED": _LINE,  # dimension text and dimension lines
    "RULE": _mix(_LINE, _WHITE, 0.7),  # separators
    "PANEL": _mix(_LIGHT, _WHITE, 0.6),  # sheet material fill
    "PANEL_STROKE": _PANEL,
    "SURFACE": _mix(_LIGHT, _WHITE, 0.85),  # flanges and light surfaces
    "ACCENT": _mix(_DEEP, _LIGHT, 0.3),  # selected cuts and highlights (software blue)
    "ACCENT_FILL": _mix(_LIGHT, _WHITE, 0.4),  # drivers, ports and other functional parts
    "OCHRE": tokens.AREAS["construction"]["accent"],  # damping and material information only
    "OCHRE_FILL": tokens.AREAS["construction"]["band"],
    "CRITICAL": _mix(tokens.AREAS["jewelry"]["accent"], "#c0392b", 0.35),  # drill holes, warnings
    "OK": tokens.AREAS["apparel"]["accent"],
    "OK_FILL": tokens.AREAS["apparel"]["band"],
}

_SENTINEL = re.compile(r"%([A-Z_]+)%")


def hex_for(role: str) -> str:
    return ROLES[role]


def paint(svg: str) -> str:
    """Resolve role sentinels in a drawing."""
    return _SENTINEL.sub(lambda m: ROLES.get(m.group(1), m.group(0)), svg)


def painted[**P, R: (str, list[str])](function: Callable[P, R]) -> Callable[P, R]:
    """Decorator for renderers returning SVG text (or a list of SVG texts) with role sentinels."""
    @wraps(function)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        result = function(*args, **kwargs)
        if isinstance(result, list):
            return [paint(item) for item in result]
        return paint(result)
    return wrapper


TITLE_BLOCK_CSS: Final = (".tb{font:600 12px sans-serif;fill:%MUTED%}.tbt{font:700 13px sans-serif;fill:%INK%}")


def title_block(x: float, y: float, width: float, project: str, revision: str, sheet: str, note: str) -> str:
    """Discreet ACK Studio title block: project, revision, sheet type, unit/scale note."""
    from html import escape
    cells = (("Projekt", project), ("Revision", revision), ("Blatt", sheet), ("Maßstab/Einheit", note))
    step = width / len(cells)
    parts = [f'<line x1="{x}" y1="{y}" x2="{x + width}" y2="{y}" stroke="%RULE%" stroke-width="1"/>']
    for index, (label, value) in enumerate(cells):
        cx = x + index * step
        parts.append(f'<text x="{cx:.1f}" y="{y + 16:.1f}" class="tb">{label}</text>')
        parts.append(f'<text x="{cx:.1f}" y="{y + 34:.1f}" class="tbt">{escape(value)}</text>')
    parts.append(f'<text x="{x + width:.1f}" y="{y + 52:.1f}" text-anchor="end" class="tb">ACK Studio</text>')
    return "".join(parts)
