"""One manufacturing sheet per machined face, using the DXF coordinate origin."""
# ruff: noqa: ISC004
from __future__ import annotations

from html import escape

from lautsprecher_konstruktion.drawings.style import painted, title_block
from lautsprecher_konstruktion.enclosure.layout import bolt_holes
from lautsprecher_konstruktion.services.design import DesignBundle

SURFACE_NAMES = {"front": "Frontplatte", "back": "Rückwand", "partition": "Trennwand"}


def _mm(value: float) -> float:
    return value * 1000


def panel_sheet_surfaces(bundle: DesignBundle) -> tuple[str, ...]:
    return ("front",) + tuple(
        surface for surface in ("back", "partition")
        if any(e.surface == surface for e in bundle.front_elements)
    )


@painted
def render_panel_sheet_svg(bundle: DesignBundle, surface: str) -> str:
    if surface not in SURFACE_NAMES:
        raise ValueError(f"Unknown surface: {surface}")
    cab = bundle.cabinet
    w = _mm(cab.internal_width_m if surface == "partition" else cab.width_m)
    h = _mm(cab.internal_height_m if surface == "partition" else cab.height_m)
    thick = _mm(cab.panel_thickness_m if surface == "partition" else
                cab.effective_front_thickness_m if surface == "front" else
                cab.effective_back_thickness_m)
    ox = _mm(cab.panel_thickness_m) if surface == "partition" else 0.0
    oy = _mm(cab.bottom_thickness_m or cab.panel_thickness_m) if surface == "partition" else 0.0
    scale = min(490 / w, 570 / h)
    px, py = 100.0, 130.0
    pw, ph = w*scale, h*scale
    elements = tuple(e for e in bundle.front_elements if e.surface == surface)
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="900" viewBox="0 0 1200 900">',
        '<style>.title{font:700 28px %FONT_UI%;fill:%INK%}.head{font:700 19px %FONT_UI%;fill:%INK%}'
        '.text{font:15px %FONT_UI%;fill:%TEXT%}.small{font:13px %FONT_UI%;fill:%MUTED%}'
        '.panel{fill:%WHITE%;stroke:%PANEL_STROKE%;stroke-width:2.5}.cut{fill:%SURFACE%;stroke:%ACCENT%;stroke-width:2}'
        '.flange{fill:none;stroke:%MUTED%;stroke-width:1.5;stroke-dasharray:5 4}'
        '.hole{fill:%WHITE%;stroke:%CRITICAL%;stroke-width:1.8}.axis{stroke:%MUTED%;stroke-width:1;stroke-dasharray:5 5}'
        '.dim{stroke:%MUTED%;stroke-width:1.3}.rule{stroke:%RULE%;stroke-width:1}.tb{font:600 12px %FONT_UI%;fill:%MUTED%}.tbt{font:700 13px %FONT_UI%;fill:%INK%}</style>',
        '<rect width="1200" height="900" fill="white"/>',
        f'<text x="45" y="46" class="title">{escape(bundle.project.name)} · {SURFACE_NAMES[surface]}</text>',
        f'<text x="45" y="75" class="text">{escape(bundle.project.revision)} · Einzelteil / Fräsansicht · alle Maße in mm</text>',
        f'<rect x="{px:.2f}" y="{py:.2f}" width="{pw:.2f}" height="{ph:.2f}" class="panel"/>',
        f'<text x="{px}" y="{py-14}" class="small">Ansicht von außen · Ursprung links unten</text>',
        f'<path d="M{px:.2f} {py+ph+18:.2f}v-18h18" class="dim"/>',
        f'<text x="{px+6:.2f}" y="{py+ph+35:.2f}" class="small">0 / 0</text>',
    ]
    for idx, e in enumerate(elements):
        x, y = _mm(e.x_m)-ox, _mm(e.y_m)-oy
        cx, cy = px+x*scale, py+(h-y)*scale
        if e.outer_diameter_m is not None:
            outer = _mm(e.outer_diameter_m)*scale/2
            cut = _mm(e.cutout_diameter_m or e.outer_diameter_m)*scale/2
            parts.append(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{outer:.2f}" class="flange"/>')
            parts.append(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{cut:.2f}" class="cut"/>')
        else:
            ew, eh = _mm(e.width)*scale, _mm(e.height)*scale
            parts.append(f'<rect x="{cx-ew/2:.2f}" y="{cy-eh/2:.2f}" width="{ew:.2f}" height="{eh:.2f}" class="cut"/>')
        for hx, hy, radius in bolt_holes(e):
            bx = px+(_mm(hx)-ox)*scale
            by = py+(h-(_mm(hy)-oy))*scale
            parts.append(f'<circle cx="{bx:.2f}" cy="{by:.2f}" r="{max(2,_mm(radius)*scale):.2f}" class="hole"/>')
        parts.append(f'<path d="M{px:.2f} {cy:.2f}H{cx:.2f} M{cx:.2f} {cy:.2f}V{py+ph:.2f}" class="axis"/>')
        parts.append(f'<text x="{cx+7:.2f}" y="{cy-7:.2f}" class="head">{escape(e.id)}</text>')
        cut_label = (f'Ø {_mm(e.cutout_diameter_m or e.outer_diameter_m):.1f}'
                     if e.outer_diameter_m else f'{_mm(e.width):.1f} × {_mm(e.height):.1f}')
        holes = (f'{e.bolt_count} × Ø {_mm(e.hole_diameter_m):.1f} / LK Ø {_mm(e.bolt_circle_diameter_m):.1f}'
                 if e.bolt_count and e.hole_diameter_m and e.bolt_circle_diameter_m else
                 f'LK Ø {_mm(e.bolt_circle_diameter_m):.1f}; Bohr-Ø fehlt'
                 if e.bolt_count and e.bolt_circle_diameter_m else 'Bohrbild nicht angegeben')
        yy = 184+idx*104
        for offset, line in enumerate((f'{e.id} · {e.type}', f'Mitte X {x:.1f} / Y {y:.1f}',
                                       f'Ausschnitt {cut_label} · Tiefe {_mm(e.mounting_depth_m):.1f}', holes)):
            parts.append(f'<text x="650" y="{yy+offset*21}" class="text">{escape(line)}</text>')
        parts.append(f'<path d="M645 {yy+76}H1150" class="rule"/>')
    parts += [
        f'<path d="M{px:.2f} {py+ph+65:.2f}H{px+pw:.2f} M{px:.2f} {py+ph+58:.2f}v14 '
        f'M{px+pw:.2f} {py+ph+58:.2f}v14" class="dim"/>',
        f'<text x="{px+pw/2:.2f}" y="{py+ph+56:.2f}" text-anchor="middle" class="text">B {w:.1f}</text>',
        f'<text x="{px-40}" y="{py+ph/2:.2f}" text-anchor="middle" class="text" '
        f'transform="rotate(-90 {px-40} {py+ph/2:.2f})">H {h:.1f}</text>',
        '<text x="650" y="126" class="head">Fräsdaten und Positionen</text>',
        f'<text x="650" y="154" class="text">Rohmaß {w:.1f} × {h:.1f} × {thick:.1f}</text>',
        f'<text x="45" y="805" class="small">{escape(SURFACE_NAMES[surface])}: Ansichts- und DXF-Koordinaten stimmen überein. Blau = Ausschnitt, gestrichelt = Flansch, Rot = bekannte Bohrungen.</text>',
        '<text x="45" y="831" class="small">Bei fehlenden Herstellermaßen keine Bohrungen ableiten. Vor CNC-Bearbeitung Chassis und Datenblatt prüfen.</text>',
        title_block(45, 845, 1110, bundle.project.name, bundle.project.revision, 'Einzelteilplan · '+SURFACE_NAMES[surface], 'Maße in mm · DXF-Koordinaten'),
        '</svg>',
    ]
    return ''.join(parts)
