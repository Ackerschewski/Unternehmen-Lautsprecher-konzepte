"""German presentation layer: user-facing names for internal identifiers.

Internal ids, file formats and calculation data keep their English identifiers; only text shown to the
user goes through these functions.
"""
from __future__ import annotations

import re

PANEL_NAMES: dict[str, str] = {
    "Front": "Frontplatte", "Back": "Rückwand", "Side": "Seitenwand", "Top": "Deckel", "Bottom": "Boden",
    "Brace": "Versteifung", "Partition": "Trennwand",
}
COMPONENT_NAMES: dict[str, str] = {
    "inductor": "Spule", "capacitor": "Kondensator", "resistor": "Widerstand",
}
CONNECTIONS: dict[str, str] = {"series": "in Reihe", "shunt": "parallel"}
ROLES: dict[str, str] = {
    "woofer low-pass": "Tieftöner-Tiefpass", "woofer high-pass": "Tieftöner-Hochpass",
    "midrange high-pass": "Mitteltöner-Hochpass", "midrange low-pass": "Mitteltöner-Tiefpass",
    "tweeter high-pass": "Hochtöner-Hochpass", "tweeter low-pass": "Hochtöner-Tiefpass",
    "woofer zobel": "Tieftöner-Zobel", "woofer": "Tieftöner", "midrange": "Mitteltöner", "tweeter": "Hochtöner",
}
PRICE_KINDS: dict[str, str] = {
    "retail": "Händlerpreis", "Materialreferenz": "Materialreferenz", "Planpreis": "Planpreis", "fehlt": "fehlt",
}
_ALL = {**COMPONENT_NAMES, **CONNECTIONS, **ROLES}
_TOKENS = re.compile(r"(?<!\w)(?:" + "|".join(re.escape(k) for k in sorted(_ALL, key=len, reverse=True)) + r")(?!\w)", re.IGNORECASE)  # whole words only


def panel_name(name: str) -> str:
    """"Front" -> "Frontplatte" (names with a suffix keep it: "Linienfaltung F1" stays as is)."""
    for english, german in PANEL_NAMES.items():
        if name == english:
            return german
        if name.startswith(english + " "):
            return german + name[len(english):]
    return name


def component_text(text: str) -> str:
    """Translate component kinds, connections and filter roles inside a description."""
    return _TOKENS.sub(lambda m: _ALL[m.group(0).lower()], text)


def price_kind(kind: str) -> str:
    return PRICE_KINDS.get(kind, kind)


def de(value: float, decimals: int = 0) -> str:
    """German number format: 1.430 mm, 28,5 Hz."""
    text = f"{value:,.{decimals}f}"
    return text.replace(",", "\x00").replace(".", ",").replace("\x00", ".")
