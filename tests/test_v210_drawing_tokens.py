"""Drawings take their colours from one central token module and carry an ACK Studio title block."""
import re
from pathlib import Path

import pytest

from lautsprecher_konstruktion.drawings import style
from lautsprecher_konstruktion.drawings.dimension_svg import render_dimension_svg
from lautsprecher_konstruktion.drawings.internal_dimensions_svg import (
    render_internal_dimensions_svg,
)
from lautsprecher_konstruktion.drawings.master_sheet_svg import render_master_sheet_svg
from lautsprecher_konstruktion.drawings.panel_sheet_svg import render_panel_sheet_svg
from lautsprecher_konstruktion.project.demo import demo_project
from lautsprecher_konstruktion.services.design import calculate_project
from lautsprecher_konstruktion.ui import tokens

ROOT = Path(__file__).resolve().parents[1] / "src" / "lautsprecher_konstruktion"
HEX = re.compile(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b")


def test_no_hex_colours_outside_the_central_drawing_tokens() -> None:
    offenders = []
    for folder in ("drawings", "export"):
        for path in (ROOT / folder).glob("*.py"):
            if path.name == "style.py":
                continue
            text = re.sub(r"url\(#\w+\)", "", path.read_text(encoding="utf-8"))
            if HEX.search(text):
                offenders.append(path.name)
    assert not offenders, offenders


def test_roles_are_valid_and_readable_on_paper() -> None:
    for role, value in style.ROLES.items():
        if role != "FONT_UI":
            assert re.fullmatch(r"#[0-9a-f]{6}", value), role
    for text_role in ("INK", "TEXT", "MUTED", "CRITICAL", "OCHRE", "OK", "ACCENT"):
        assert tokens.contrast(style.ROLES[text_role], "#ffffff") >= 4.5, text_role
    assert style.ROLES["INK"] == tokens.AREAS["software"]["accent"]


def test_paint_resolves_every_sentinel_and_keeps_unknown_text() -> None:
    assert style.paint("fill:%INK%;x:%UNKNOWN%") == f"fill:{style.ROLES['INK']};x:%UNKNOWN%"


@pytest.fixture(scope="module")
def bundle():
    return calculate_project(demo_project())


def test_sheets_have_no_leftover_sentinels_and_a_title_block(bundle) -> None:
    for render in (render_dimension_svg, render_internal_dimensions_svg, render_master_sheet_svg):
        svg = render(bundle)
        assert not re.search(r"%[A-Z_]+%", svg), render.__name__
    for render in (render_dimension_svg, render_internal_dimensions_svg):
        svg = render(bundle)
        assert "ACK Studio" in svg and "Revision" in svg and "Maßstab/Einheit" in svg
    panel = render_panel_sheet_svg(bundle, "front")
    assert "ACK Studio" in panel and not re.search(r"%[A-Z_]+%", panel)


def test_geometry_does_not_depend_on_colour_roles(bundle) -> None:
    svg = render_internal_dimensions_svg(bundle)
    recoloured = HEX.sub("#000000", svg)
    assert re.findall(r"<rect[^>]*width=\"[\d.]+\"", svg) == re.findall(r"<rect[^>]*width=\"[\d.]+\"", recoloured)
