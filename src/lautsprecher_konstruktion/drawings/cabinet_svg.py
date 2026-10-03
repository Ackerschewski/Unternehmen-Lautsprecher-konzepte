from __future__ import annotations

from dataclasses import dataclass
from html import escape

from lautsprecher_konstruktion.enclosure.layout import FrontElement, bolt_holes
from lautsprecher_konstruktion.enclosure.ports import PortDesign
from lautsprecher_konstruktion.enclosure.rectangular import CabinetDimensions


@dataclass(frozen=True)
class CabinetDrawingInput:
    cabinet: CabinetDimensions
    driver_cutout_diameter_m: float | None = None
    driver_center_x_m: float | None = None
    driver_center_y_m: float | None = None
    port: PortDesign | None = None
    front_elements: tuple[FrontElement, ...] = ()
    title: str = "Lautsprechergehäuse"


def _mm(value_m: float) -> float:
    return value_m * 1000.0


def _dimension_horizontal(x1: float, x2: float, y: float, text: str) -> str:
    mid = (x1 + x2) / 2.0
    return (
        f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" class="dim"/>'
        f'<line x1="{x1}" y1="{y-5}" x2="{x1}" y2="{y+5}" class="dim"/>'
        f'<line x1="{x2}" y1="{y-5}" x2="{x2}" y2="{y+5}" class="dim"/>'
        f'<text x="{mid}" y="{y-4}" text-anchor="middle" class="txt">{escape(text)}</text>'
    )


def _dimension_vertical(x: float, y1: float, y2: float, text: str) -> str:
    mid = (y1 + y2) / 2.0
    return (
        f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2}" class="dim"/>'
        f'<line x1="{x-5}" y1="{y1}" x2="{x+5}" y2="{y1}" class="dim"/>'
        f'<line x1="{x-5}" y1="{y2}" x2="{x+5}" y2="{y2}" class="dim"/>'
        f'<text x="{x-7}" y="{mid}" text-anchor="middle" class="txt" '
        f'transform="rotate(-90 {x-7} {mid})">{escape(text)}</text>'
    )


def render_cabinet_svg(spec: CabinetDrawingInput) -> str:
    c = spec.cabinet
    w, h, d = _mm(c.width_m), _mm(c.height_m), _mm(c.depth_m)
    scale = min(360.0 / max(w, 1.0), 420.0 / max(h, 1.0), 300.0 / max(d, 1.0))
    fw, fh, fd = w * scale, h * scale, d * scale

    ox, oy = 90.0, 90.0
    side_x = ox + fw + 150.0
    top_y = oy + fh + 150.0
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="900" viewBox="0 0 1200 900">',
        ('<style>.obj{fill:none;stroke:#111;stroke-width:2}.cut{fill:none;stroke:#555;stroke-width:1.5}'
        '.dim{stroke:#666;stroke-width:1}.txt{font:13px sans-serif;fill:#222}'
        '.title{font:bold 22px sans-serif;fill:#111}.label{font:bold 15px sans-serif;fill:#111}</style>'),
        f'<text x="40" y="35" class="title">{escape(spec.title)}</text>',
        f'<text x="{ox}" y="{oy-20}" class="label">Vorderansicht</text>',
        f'<rect x="{ox}" y="{oy}" width="{fw}" height="{fh}" class="obj"/>',
    ]

    if spec.front_elements:
        for element in spec.front_elements:
            cx = ox + _mm(element.x_m)*scale
            cy = oy + fh - _mm(element.y_m)*scale
            if element.outer_diameter_m is not None:
                radius = _mm(element.cutout_diameter_m or element.outer_diameter_m)*scale/2
                parts.append(f'<circle cx="{cx}" cy="{cy}" r="{radius}" class="cut"/>')
            else:
                ew, eh = _mm(element.width)*scale, _mm(element.height)*scale
                parts.append(f'<rect x="{cx-ew/2}" y="{cy-eh/2}" width="{ew}" height="{eh}" class="cut"/>')
            parts.append(f'<text x="{cx}" y="{cy+5}" text-anchor="middle" class="txt">{escape(element.id)}</text>')
            for bx, by, br in bolt_holes(element):
                parts.append(f'<circle cx="{ox+_mm(bx)*scale}" cy="{oy+fh-_mm(by)*scale}" r="{_mm(br)*scale}" class="cut"/>')
    elif spec.driver_cutout_diameter_m:
        dia = _mm(spec.driver_cutout_diameter_m) * scale
        cx = ox + (
            _mm(spec.driver_center_x_m) * scale
            if spec.driver_center_x_m is not None
            else fw / 2.0
        )
        cy = oy + (
            _mm(spec.driver_center_y_m) * scale
            if spec.driver_center_y_m is not None
            else fh * 0.38
        )
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="{dia/2}" class="cut"/>')
        parts.append(
            f'<text x="{cx}" y="{cy+dia/2+18}" text-anchor="middle" class="txt">'
            f'Treiberausschnitt Ø {_mm(spec.driver_cutout_diameter_m):.1f} mm</text>'
        )

    if spec.port is not None and not spec.front_elements:
        if spec.port.shape == "round" and spec.port.diameter_m:
            pd = _mm(spec.port.diameter_m) * scale
            px = ox + fw / 2.0
            py = oy + fh - pd / 2.0 - 18.0
            parts.append(f'<circle cx="{px}" cy="{py}" r="{pd/2}" class="cut"/>')
        elif spec.port.shape == "slot" and spec.port.width_m and spec.port.height_m:
            pw = _mm(spec.port.width_m) * scale
            ph = _mm(spec.port.height_m) * scale
            px = ox + (fw - pw) / 2.0
            py = oy + fh - ph - 18.0
            parts.append(f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" class="cut"/>')

    parts.append(_dimension_horizontal(ox, ox + fw, oy + fh + 35, f"{w:.1f} mm"))
    parts.append(_dimension_vertical(ox - 35, oy, oy + fh, f"{h:.1f} mm"))

    parts.extend([
        f'<text x="{side_x}" y="{oy-20}" class="label">Seitenansicht</text>',
        f'<rect x="{side_x}" y="{oy}" width="{fd}" height="{fh}" class="obj"/>',
        _dimension_horizontal(side_x, side_x + fd, oy + fh + 35, f"{d:.1f} mm"),
        _dimension_vertical(side_x - 35, oy, oy + fh, f"{h:.1f} mm"),
        f'<text x="{ox}" y="{top_y-20}" class="label">Draufsicht</text>',
        f'<rect x="{ox}" y="{top_y}" width="{fw}" height="{fd}" class="obj"/>',
        _dimension_horizontal(ox, ox + fw, top_y + fd + 35, f"{w:.1f} mm"),
        _dimension_vertical(ox - 35, top_y, top_y + fd, f"{d:.1f} mm"),
        f'<text x="{side_x}" y="{top_y}" class="txt">Plattenstärke: {_mm(c.panel_thickness_m):.1f} mm</text>',
        '</svg>',
    ])
    return "".join(parts)
