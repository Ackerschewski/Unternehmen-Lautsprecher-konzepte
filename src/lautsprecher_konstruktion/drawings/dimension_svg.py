"""Dimension schedule generated from the same resolved geometry as the cut files.

Coordinates are measured from the lower left outside corner of the named face.
The schedule intentionally does not invent screw circles or tolerances when these
are absent from the selected manufacturer's data.
"""
# ruff: noqa: ISC004
from __future__ import annotations

from html import escape

from lautsprecher_konstruktion.drawings.style import painted, title_block
from lautsprecher_konstruktion.enclosure.layout import FrontElement, bolt_holes
from lautsprecher_konstruktion.services.design import DesignBundle


def _mm(value: float) -> float:
    return value * 1000


def _line(x1: float, y1: float, x2: float, y2: float) -> str:
    return f'<path d="M{x1:.1f} {y1:.1f}L{x2:.1f} {y2:.1f}" class="dim"/>'


def _h_dim(x1: float, x2: float, y: float, label: str) -> str:
    return (_line(x1, y, x2, y) + _line(x1, y-6, x1, y+6) +
            _line(x2, y-6, x2, y+6) +
            f'<text x="{(x1+x2)/2:.1f}" y="{y-8:.1f}" text-anchor="middle" class="dimtext">{escape(label)}</text>')


def _v_dim(x: float, y1: float, y2: float, label: str) -> str:
    return (_line(x, y1, x, y2) + _line(x-6, y1, x+6, y1) +
            _line(x-6, y2, x+6, y2) +
            f'<text x="{x-8:.1f}" y="{(y1+y2)/2:.1f}" text-anchor="middle" '
            f'transform="rotate(-90 {x-8:.1f} {(y1+y2)/2:.1f})" class="dimtext">{escape(label)}</text>')


def _face(parts: list[str], elements: tuple[FrontElement, ...], face: str,
          x: float, y: float, w: float, h: float, scale: float) -> None:
    parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w*scale:.1f}" height="{h*scale:.1f}" class="outline"/>')
    for element in elements:
        if element.surface != face:
            continue
        cx, cy = x+_mm(element.x_m)*scale, y+(h-_mm(element.y_m))*scale
        if element.outer_diameter_m:
            parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{_mm(element.outer_diameter_m)*scale/2:.1f}" class="flange"/>')
            parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{_mm(element.cutout_diameter_m or element.outer_diameter_m)*scale/2:.1f}" class="cut"/>')
        else:
            ew, eh = _mm(element.width)*scale, _mm(element.height)*scale
            parts.append(f'<rect x="{cx-ew/2:.1f}" y="{cy-eh/2:.1f}" width="{ew:.1f}" height="{eh:.1f}" class="cut"/>')
        for hx, hy, radius in bolt_holes(element):
            parts.append(f'<circle cx="{x+_mm(hx)*scale:.1f}" cy="{y+(h-_mm(hy))*scale:.1f}" r="{max(1.5,_mm(radius)*scale):.1f}" class="hole"/>')
        parts.extend((_line(x, cy, cx, cy), _line(cx, cy, cx, y+h*scale)))
        parts.append(f'<text x="{cx+5:.1f}" y="{cy-7:.1f}" class="id">{escape(element.id)}</text>')


def dimension_rows(bundle: DesignBundle) -> tuple[tuple[str, str, float, float, str, float], ...]:
    """ID, surface, centre X/Y, cutout, mounting depth; all values in mm."""
    rows = []
    for e in bundle.front_elements:
        cut = (f'Ø {_mm(e.cutout_diameter_m):.1f}' if e.cutout_diameter_m else
               f'{_mm(e.width):.1f} × {_mm(e.height):.1f}')
        rows.append((e.id, e.surface, _mm(e.x_m), _mm(e.y_m), cut, _mm(e.mounting_depth_m)))
    return tuple(rows)


@painted
def render_dimension_svg(bundle: DesignBundle) -> str:
    if bundle.baffle_mode is not None:
        from lautsprecher_konstruktion.drawings.baffle_svg import render_baffle_svg
        return render_baffle_svg(bundle)
    if bundle.front_horn is not None:
        from lautsprecher_konstruktion.drawings.front_horn_svg import render_front_horn_svg
        return render_front_horn_svg(bundle)
    if bundle.tapped_horn is not None:
        from lautsprecher_konstruktion.drawings.tapped_horn_svg import render_tapped_horn_svg
        return render_tapped_horn_svg(bundle)
    c = bundle.cabinet
    w, h, d = (_mm(v) for v in (c.width_m, c.height_m, c.depth_m))
    scale = min(360/w, 440/h, 320/d)
    fx, sy, sx = 105.0, 120.0, 615.0
    fw, fh, sd = w*scale, h*scale, d*scale
    row_y = max(710, sy+fh+192)
    sheet_height = max(1100, int(row_y+49+len(bundle.front_elements)*28+155))
    front = tuple(e for e in bundle.front_elements if e.surface == 'front')
    back = tuple(e for e in bundle.front_elements if e.surface == 'back')
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="{sheet_height}" viewBox="0 0 1200 {sheet_height}">',
        '<style>.title{font:700 27px sans-serif;fill:%INK%}.label{font:700 18px sans-serif;fill:%INK%}'
        '.text{font:15px sans-serif;fill:%TEXT%}.small{font:13px sans-serif;fill:%MUTED%}'
        '.dimtext{font:13px sans-serif;fill:%TEXT%}.id{font:700 14px sans-serif;fill:%INK%}'
        '.outline{fill:white;stroke:%INK%;stroke-width:2}.dim{fill:none;stroke:%MUTED%;stroke-width:1}'
        '.flange{fill:%SURFACE%;stroke:%MUTED%;stroke-width:1.5}.cut{fill:none;stroke:%ACCENT%;stroke-width:2}'
        '.hole{fill:white;stroke:%CRITICAL%;stroke-width:1.4}.panel{fill:%PANEL%;stroke:%PANEL_STROKE%;stroke-width:1.5}'
        '.rule{stroke:%RULE%;stroke-width:1}.tb{font:600 12px sans-serif;fill:%MUTED%}.tbt{font:700 13px sans-serif;fill:%INK%}</style>',
        f'<rect width="1200" height="{sheet_height}" fill="white"/>',
        f'<text x="45" y="43" class="title">{escape(bundle.project.name)} · Maßblatt</text>',
        f'<text x="45" y="70" class="text">{escape(bundle.project.revision)} · Alle Maße in mm · Bezug: linke untere Außenecke der jeweiligen Ansicht</text>',
        f'<text x="{fx:.1f}" y="{sy-16:.1f}" class="label">Frontansicht</text>',
        f'<text x="{sx:.1f}" y="{sy-16:.1f}" class="label">Schnitt: Tiefe und Material</text>',
    ]
    _face(parts, front, 'front', fx, sy, w, h, scale)
    parts.append(_h_dim(fx, fx+fw, sy+fh+32, f'Außenbreite {w:.1f}'))
    parts.append(_v_dim(fx-31, sy, sy+fh, f'Außenhöhe {h:.1f}'))
    parts.append(f'<rect x="{sx}" y="{sy}" width="{sd:.1f}" height="{fh:.1f}" class="outline"/>')
    front_t = _mm(c.effective_front_thickness_m)*scale
    back_t = _mm(c.effective_back_thickness_m)*scale
    top_t = _mm(c.top_thickness_m or c.panel_thickness_m)*scale
    bottom_t = _mm(c.bottom_thickness_m or c.panel_thickness_m)*scale
    for x, y, rw, rh in ((sx, sy, front_t, fh), (sx+sd-back_t, sy, back_t, fh),
                        (sx+front_t, sy, sd-front_t-back_t, top_t),
                        (sx+front_t, sy+fh-bottom_t, sd-front_t-back_t, bottom_t)):
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{rw:.1f}" height="{rh:.1f}" class="panel"/>')
    inner_front, inner_rear = sx+front_t, sx+sd-back_t
    for e in bundle.front_elements:
        if e.surface not in {'front', 'back'}:
            continue
        cy = sy+(h-_mm(e.y_m))*scale
        eh = _mm(e.cutout_diameter_m or e.height)*scale
        depth = _mm(e.mounting_depth_m)*scale
        if e.surface == 'front':
            xx = inner_front
            if e.type == 'port':
                parts.append(f'<rect x="{xx:.1f}" y="{cy-eh/2:.1f}" width="{depth:.1f}" height="{eh:.1f}" class="cut"/>')
            else:
                parts.append(f'<path d="M{xx:.1f} {cy-eh/2:.1f}L{xx+depth:.1f} {cy-eh*.25:.1f}L{xx+depth:.1f} {cy+eh*.25:.1f}L{xx:.1f} {cy+eh/2:.1f}Z" class="flange"/>')
        else:
            xx = inner_rear
            parts.append(f'<path d="M{xx:.1f} {cy-eh/2:.1f}L{xx-depth:.1f} {cy-eh*.25:.1f}L{xx-depth:.1f} {cy+eh*.25:.1f}L{xx:.1f} {cy+eh/2:.1f}Z" class="flange"/>')
        parts.append(f'<text x="{xx+8:.1f}" y="{cy-eh/2-7:.1f}" class="id">{escape(e.id)}</text>')
    if bundle.brace:
        for index, depth in enumerate(bundle.brace_depths_m):
            bx = inner_front+_mm(depth)*scale
            parts.append(f'<rect x="{bx:.1f}" y="{sy+top_t:.1f}" width="{_mm(bundle.brace.thickness_m)*scale:.1f}" height="{min(9,fh/8):.1f}" class="panel"/>')
            parts.append(f'<rect x="{bx:.1f}" y="{sy+fh-bottom_t-min(9,fh/8):.1f}" width="{_mm(bundle.brace.thickness_m)*scale:.1f}" height="{min(9,fh/8):.1f}" class="panel"/>')
            parts.append(f'<text x="{bx+5:.1f}" y="{sy+top_t+28:.1f}" class="id">B{index+1}</text>')
    if bundle.partition_front_depth_m is not None:
        px = sx+front_t+_mm(bundle.partition_front_depth_m)*scale
        parts.append(f'<path d="M{px:.1f} {sy+top_t:.1f}V{sy+fh-bottom_t:.1f}" class="cut"/>')
        parts.append(_h_dim(sx+front_t, px, sy+fh+75,
                            f'Frontkammer {_mm(bundle.partition_front_depth_m):.1f}'))
        rear_depth = c.internal_depth_m-bundle.partition_front_depth_m-c.panel_thickness_m
        parts.append(_h_dim(px+_mm(c.panel_thickness_m)*scale, sx+sd-back_t, sy+fh+104,
                            f'Rückkammer {_mm(rear_depth):.1f}'))
    parts.append(_h_dim(sx, sx+sd, sy+fh+32, f'Außentiefe {d:.1f}'))
    parts.append(_h_dim(sx+front_t, sx+sd-back_t, sy+fh+135,
                        f'Innentiefe {_mm(c.internal_depth_m):.1f}'))
    if bundle.coupler:
        k = bundle.coupler
        cx = sx+front_t+_mm(k.length_m)*scale
        parts.append(_h_dim(sx+front_t, cx, sy+fh+75,
                            f'Koppelrohr {_mm(k.length_m):.1f}'))
        parts.append(_h_dim(cx, cx+_mm(k.ring_thickness_m)*scale, sy+fh+104,
                            f'Ring {_mm(k.ring_thickness_m):.1f}'))
        parts.append(f'<text x="{sx}" y="{sy+fh+180:.1f}" class="small">'
                     f'Isobarik: Rohr innen Ø {_mm(k.inner_diameter_m):.1f}, außen Ø {_mm(k.outer_diameter_m):.1f}; '
                     f'Ring-Ausschnitt Ø {_mm(k.driver_cutout_m):.1f}; W2 hinter Ring montieren.</text>')
    parts.append(_v_dim(sx+sd+32, sy+top_t, sy+fh-bottom_t,
                        f'Innenhöhe {_mm(c.internal_height_m):.1f}'))
    parts.append(f'<text x="{sx}" y="{sy+fh+162:.1f}" class="small">Innenbreite {_mm(c.internal_width_m):.1f} · Front {_mm(c.effective_front_thickness_m):.1f} · Rückwand {_mm(c.effective_back_thickness_m):.1f} · Deckel {_mm(c.top_thickness_m or c.panel_thickness_m):.1f} · Boden {_mm(c.bottom_thickness_m or c.panel_thickness_m):.1f}</text>')
    parts.append(f'<text x="45" y="{row_y}" class="label">Ausschnitte und Einbauorte</text>')
    parts.append(f'<text x="45" y="{row_y+24}" class="small">ID · Fläche · X Mitte · Y Mitte · Ausschnitt · Einbautiefe · Flansch · Bohrungen</text>')
    for index, e in enumerate(bundle.front_elements):
        y = row_y+49+index*28
        cut = f'Ø {_mm(e.cutout_diameter_m):.1f}' if e.cutout_diameter_m else f'{_mm(e.width):.1f} × {_mm(e.height):.1f}'
        flange = f'Ø {_mm(e.outer_diameter_m):.1f}' if e.outer_diameter_m else '–'
        holes = (f'{e.bolt_count} × Ø {_mm(e.hole_diameter_m):.1f} auf Lochkreis Ø {_mm(e.bolt_circle_diameter_m):.1f}'
                 if e.bolt_count and e.bolt_circle_diameter_m and e.hole_diameter_m else
                 f'Lochkreis Ø {_mm(e.bolt_circle_diameter_m):.1f}; Bohr-Ø fehlt'
                 if e.bolt_count and e.bolt_circle_diameter_m else 'nicht angegeben')
        line = (f'{e.id} · {e.surface} · X {_mm(e.x_m):.1f} · Y {_mm(e.y_m):.1f} · '
                f'{cut} · T {_mm(e.mounting_depth_m):.1f} · {flange} · {holes}')
        parts.append(f'<text x="48" y="{y}" class="text">{escape(line)}</text>')
        parts.append(f'<path d="M45 {y+7}H1155" class="rule"/>')
    note_y = row_y+65+len(bundle.front_elements)*28
    parts.append(f'<text x="45" y="{note_y}" class="small">Koordinaten sind Fertigmaße der berechneten Geometrie. Vor dem Fräsen Original-Datenblatt und reale Chassis prüfen.</text>')
    if back:
        parts.append(f'<text x="45" y="{note_y+22}" class="small">Rückwand-Einbauten sind in der Tabelle mit Fläche „back“ gekennzeichnet.</text>')
    parts.append(title_block(45, sheet_height-70, 1110, bundle.project.name, bundle.project.revision, 'Maßblatt', 'Maße in mm · Maßstab schematisch'))
    parts.append('</svg>')
    return ''.join(parts)
