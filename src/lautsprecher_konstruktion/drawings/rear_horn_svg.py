"""Interior drawing of a folded rear horn: inclined septa, area law, throat and mouth."""
# ruff: noqa: ISC004
from __future__ import annotations

from html import escape
from textwrap import wrap

import numpy as np

from lautsprecher_konstruktion.drawings.style import painted
from lautsprecher_konstruktion.enclosure.horn_geometry import HornDetails, SeptumGeometry
from lautsprecher_konstruktion.services.design import DesignBundle


def _mm(value: float) -> float:
    return value*1000


def _sep_y(sep: SeptumGeometry, x: float) -> float:
    xs = [p[0] for p in sep.points_m]
    ys = [p[1] for p in sep.points_m]
    return float(np.interp(x, xs, ys))


@painted
def horn_septa_svg(horn: HornDetails, inner_x: float, inner_y: float, scale: float, wall_m: float,
                   css: str, labels: bool = True) -> list[str]:
    """Inclined septa of a rear horn as polygons; scale is px/mm, origin = inner front/top corner."""
    parts: list[str] = []
    for sep in horn.septa:
        up = [(inner_x+_mm(x)*scale, inner_y+_mm(y)*scale) for x, y in sep.points_m]
        low = [(x, y+_mm(wall_m)*scale) for x, y in reversed(up)]
        parts.append('<polygon points="'+' '.join(f'{x:.1f},{y:.1f}' for x, y in up+low)+f'" class="{css}"/>')
        if labels:
            mx, my = up[len(up)//2]
            parts.append(f'<text x="{mx+4:.1f}" y="{my-4:.1f}" class="{"id" if css == "panel" else "callout"}">'
                         f'F{sep.index}</text>')
    return parts


@painted
def render_rear_horn_svg(bundle: DesignBundle) -> str:
    line = bundle.folded_line
    if line is None or line.horn is None:
        raise ValueError("Kein Rear-Horn")
    horn = line.horn
    c = bundle.cabinet
    t = c.panel_thickness_m
    d, h = _mm(c.depth_m), _mm(c.height_m)
    scale = min(540/max(h, 1), 300/max(d, 1))
    x0, y0 = 90.0, 125.0
    sd, sh = d*scale, h*scale
    ft, bt = _mm(c.effective_front_thickness_m)*scale, _mm(c.effective_back_thickness_m)*scale
    tt = _mm(c.top_thickness_m or t)*scale
    bot = _mm(c.bottom_thickness_m or t)*scale
    front, back = x0+ft, x0+sd-bt
    top = y0+tt                       # inner top edge
    inner_h = _mm(c.internal_height_m)*scale
    inner_d = _mm(c.internal_depth_m)*scale

    def px(x_m: float) -> float:
        return front+_mm(x_m)*scale

    def py(y_m: float) -> float:
        return top+_mm(y_m)*scale

    row = max(700.0, y0+sh+120)
    sheet_height = int(row+60+len(bundle.panels)*26+90)
    sheet_height = max(sheet_height, 1100)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="{sheet_height}" viewBox="0 0 1200 {sheet_height}">',
        '<style>.title{font:700 27px %FONT_UI%;fill:%INK%}.sub{font:15px %FONT_UI%;fill:%MUTED%}'
        '.head{font:700 18px %FONT_UI%;fill:%INK%}.text{font:15px %FONT_UI%;fill:%TEXT%}'
        '.dimtext{font:12px %FONT_UI%;fill:%TEXT%}.dim{fill:none;stroke:%MUTED%;stroke-width:1}'
        '.outline{fill:white;stroke:%INK%;stroke-width:2}.panel{fill:%PANEL%;stroke:%PANEL_STROKE%;stroke-width:1.2}'
        '.feature{fill:%ACCENT_FILL%;stroke:%ACCENT%;stroke-width:1.5}.rule{stroke:%RULE%;stroke-width:1}'
        '.chan{fill:%SURFACE%;stroke:none}.chamber{fill:%OCHRE_FILL%;stroke:none}.mouth{fill:%OK_FILL%;stroke:%OK%;stroke-width:1.5}'
        '.law{fill:none;stroke:%ACCENT%;stroke-width:2}.built{fill:none;stroke:%OCHRE%;stroke-width:2}'
        '.axis{stroke:%MUTED%;stroke-width:1;fill:none}.path{fill:none;stroke:%ACCENT%;stroke-width:1.6;stroke-dasharray:7 5}'
        '</style>',
        f'<rect width="1200" height="{sheet_height}" fill="white"/>',
        f'<text x="45" y="43" class="title">{escape(bundle.project.name)} · Innenaufbau Horn</text>',
        f'<text x="45" y="70" class="sub">{escape(bundle.project.revision)} · Maße in mm · Seitenschnitt maßstäblich, '
        'Front links · Kanalhöhe = Fläche / Innenbreite · gestrichelt: Schallweg ab Hals</text>',
        f'<text x="{x0}" y="{y0-17}" class="head">Seitenschnitt</text>',
        f'<rect x="{x0}" y="{y0}" width="{sd:.1f}" height="{sh:.1f}" class="outline"/>',
        f'<rect x="{front:.1f}" y="{top:.1f}" width="{inner_d:.1f}" height="{inner_h:.1f}" class="chan"/>',
    ]
    # driver chamber (remaining height above F1)
    sep1 = horn.septa[0]
    ch = [(px(0.0), top), (px(horn.depth_m), top), (px(horn.depth_m), py(_sep_y(sep1, horn.depth_m))),
          (px(0.0), py(_sep_y(sep1, 0.0)))]
    parts.append('<polygon points="'+' '.join(f'{x:.1f},{y:.1f}' for x, y in ch)+'" class="chamber"/>')
    for xx, yy, ww, hh in ((x0, y0, ft, sh), (back, y0, bt, sh), (front, y0, back-front, tt),
                           (front, y0+sh-bot, back-front, bot)):
        parts.append(f'<rect x="{xx:.1f}" y="{yy:.1f}" width="{ww:.1f}" height="{hh:.1f}" class="panel"/>')
    # mouth opening in the front baffle (bottom)
    mouth_h = line.mouth_height_m
    parts.append(f'<rect x="{x0:.1f}" y="{top+inner_h-(mouth_h+0.01)*1000*scale:.1f}" width="{ft:.1f}" '
                 f'height="{mouth_h*1000*scale:.1f}" class="mouth"/>')
    # septa as polygons (upper face polyline, lower face offset by the board thickness)
    for sep in horn.septa:
        up = [(px(x), py(y)) for x, y in sep.points_m]
        low = [(x, y+_mm(t)*scale) for x, y in reversed(up)]
        parts.append('<polygon points="'+' '.join(f'{x:.1f},{y:.1f}' for x, y in up+low)+'" class="panel"/>')
        mid = sep.points_m[len(sep.points_m)//2]
        parts.append(f'<text x="{px(mid[0])+4:.1f}" y="{py(mid[1])-4:.1f}" class="dimtext">F{sep.index}</text>')
    # driver on the front baffle inside the chamber
    driver = bundle.project.driver
    chamber_front = horn.chamber_front_m
    cy = py(chamber_front/2)
    dia = _mm(driver.outer_diameter_m or driver.cutout_diameter_m or 0.0)*scale
    depth = _mm(driver.mounting_depth_m or 0.0)*scale
    parts.append(f'<path d="M{front:.1f} {cy-dia/2:.1f}L{front+depth:.1f} {cy-dia/4:.1f}'
                 f'L{front+depth:.1f} {cy+dia/4:.1f}L{front:.1f} {cy+dia/2:.1f}Z" class="feature"/>')
    parts.append(f'<text x="{front+depth+5:.1f}" y="{cy+4:.1f}" class="dimtext">W1</text>')
    parts.append(f'<text x="{front+6:.1f}" y="{top+14:.1f}" class="dimtext">Kammer {horn.chamber_volume_m3*1000:.0f} l'
                 f' · vorn {_mm(horn.chamber_front_m):.0f} mm</text>')
    # centre line through the runs
    pts = []
    for run in horn.runs:
        k = run.index
        def top_y(x: float, k: int = k) -> float:
            return _sep_y(horn.septa[k-1], x)+t

        def bot_y(x: float, k: int = k) -> float:
            return _sep_y(horn.septa[k], x) if k < len(horn.runs) else c.internal_height_m

        for x in (run.x_start_m, run.x_end_m):
            pts.append((px(x), py((top_y(x)+bot_y(x))/2)))
        mid_x = (run.x_start_m+run.x_end_m)/2
        parts.append(f'<text x="{px(mid_x)-34:.1f}" y="{py((top_y(mid_x)+bot_y(mid_x))/2)-3:.1f}" class="dimtext">'
                     f'L{k} {_mm(run.h_start_m):.0f}→{_mm(run.h_end_m):.0f}</text>')
    parts.append('<polyline points="'+' '.join(f'{x:.1f},{y:.1f}' for x, y in pts)+'" class="path"/>')
    first = pts[0]
    parts.append(f'<text x="{first[0]-4:.1f}" y="{first[1]-8:.1f}" text-anchor="end" class="dimtext">'
                 f'Hals {horn.throat_area_m2*1e4:.0f} cm²</text>')
    parts.append(f'<text x="{x0+ft+4:.1f}" y="{y0+sh+16:.1f}" class="dimtext">'
                 f'Mündung {line.mouth_width_m*1000:.0f}×{mouth_h*1000:.0f} (vorn unten)</text>')
    parts.append(f'<path d="M{x0:.1f} {y0+sh+37:.1f}h{sd:.1f}" class="dim"/>'
                 f'<text x="{x0+sd/2:.1f}" y="{y0+sh+34:.1f}" text-anchor="middle" class="dimtext">'
                 f'Außentiefe {d:.1f} · Innen B×H {_mm(c.internal_width_m):.0f}×{_mm(c.internal_height_m):.0f}</text>')
    # area law plot
    gx, gy, gw, gh = 430.0, 150.0, 250.0, 200.0
    smax = horn.length_m
    amax = max(max(horn.profile_area_m2), horn.mouth_area_m2)*1.05
    parts.append(f'<text x="{gx}" y="{gy-20}" class="head">Flächenverlauf S(s)</text>')
    parts.append(f'<path d="M{gx} {gy}V{gy+gh}H{gx+gw}" class="axis"/>')
    law_pts = ' '.join(f'{gx+s/smax*gw:.1f},{gy+gh-a/amax*gh:.1f}'
                       for s, a in zip(horn.profile_s_m, horn.profile_area_m2, strict=True))
    parts.append(f'<polyline points="{law_pts}" class="law"/>')
    built_pts = []
    for run in horn.runs:
        built_pts.append((run.s_start_m, horn.width_m*run.h_start_m))
        built_pts.append((run.s_end_m, horn.width_m*run.h_end_m))
    parts.append('<polyline points="'+' '.join(f'{gx+s/smax*gw:.1f},{gy+gh-a/amax*gh:.1f}' for s, a in built_pts)
                 +'" class="built"/>')
    parts.append(f'<text x="{gx}" y="{gy+gh+18}" class="dimtext">0 = Hals</text>'
                 f'<text x="{gx+gw}" y="{gy+gh+18}" text-anchor="end" class="dimtext">s = {horn.length_m*1000:.0f} mm</text>')
    parts.append(f'<text x="{gx+6}" y="{gy+12}" class="dimtext">S max {amax/1.05*1e4:.0f} cm²</text>')
    parts.append(f'<text x="{gx}" y="{gy+gh+38}" class="dimtext" fill="%ACCENT%">blau: Gesetz · orange: gebaute Kanalflächen</text>')
    # info block
    ix, iy = 730.0, 130.0
    parts.append(f'<text x="{ix}" y="{iy}" class="head">Horn-Daten</text>')
    info = [
        f'Gesetz: {horn.law_label}',
        f'Hals S_T {horn.throat_area_m2*1e4:.1f} cm² · Mündung S_M {horn.mouth_area_m2*1e4:.1f} cm² '
        f'· S_M/S_T {horn.area_ratio:.2f}',
        f'Weg Hals→Mündung {horn.length_m*1000:.0f} mm · {len(horn.runs)} Läufe · Umlenkspalte '
        + ' / '.join(f'{_mm(g):.0f}' for g in horn.turn_gaps_m[1:]) + ' mm',
        f'Grenzfrequenz fc {horn.cutoff_hz:.1f} Hz (m = {horn.flare_per_m:.2f} 1/m) · Viertelwelle c/4L '
        f'{line.estimated_quarter_wave_hz:.1f} Hz',
        f'Mündungs-Mindestfläche (Umfang = λ bei fc): {horn.mouth_min_area_m2*1e4:.0f} cm² '
        f'→ vorhanden {horn.mouth_area_m2/horn.mouth_min_area_m2*100:.0f} %',
        f'Kompressionskammer {horn.chamber_volume_m3*1000:.0f} l · Kompression Sd/Hals {horn.compression_ratio:.2f}',
        f'Geneigte Böden: je {horn.facets_per_septum} gerade Teilbrett(er); max. Abweichung der gebauten Fläche '
        f'zum Flächengesetz {horn.max_area_deviation*100:.1f} %',
        f'Kleinste Umlenkfläche relativ zum Gesetz: {horn.min_turn_area_ratio*100:.0f} %',
        'Grenzen: ebene Wellen, Böden als Sehnen des Gesetzes, keine Richtwirkung/Mündungsform; am Prototyp messen.',
    ]
    lines_out = [piece for text in info for piece in wrap(text, 56)]
    for i, text in enumerate(lines_out):
        parts.append(f'<text x="{ix}" y="{iy+28+i*21}" class="text">{escape(text)}</text>')
    table_y = iy+28+len(lines_out)*21+24
    parts.append(f'<text x="{ix}" y="{table_y}" class="head">Läufe (ab Hals)</text>')
    for i, run in enumerate(horn.runs):
        direction = 'hinten→vorn' if run.x_end_m < run.x_start_m else 'vorn→hinten'
        text = (f'L{run.index} {direction}: s {run.s_start_m*1000:.0f}–{run.s_end_m*1000:.0f} · '
                f'Höhe {_mm(run.h_start_m):.0f}→{_mm(run.h_end_m):.0f} · '
                f'Fläche {horn.width_m*run.h_start_m*1e4:.0f}→{horn.width_m*run.h_end_m*1e4:.0f} cm²')
        parts.append(f'<text x="{ix}" y="{table_y+24+i*22}" class="dimtext">{escape(text)}</text>')
    parts.append(f'<text x="45" y="{row:.1f}" class="head">Platten und Zuschnitt (Rohmaße)</text>')
    for index, panel in enumerate(bundle.panels):
        yy = row+31+index*26
        text = (f'{panel.quantity} × {panel.name}: {_mm(panel.width_m):.1f} × '
                f'{_mm(panel.height_m):.1f} × {_mm(panel.thickness_m):.1f}')
        parts.append(f'<text x="49" y="{yy:.1f}" class="text">{escape(text)}</text>')
        parts.append(f'<path d="M45 {yy+7:.1f}H1155" class="rule"/>')
    parts.append(f'<text x="45" y="{sheet_height-32}" class="sub">Böden an den Enden auf Gehrung/Neigung zuschneiden; '
                 'Rohmaße sind Rechteck-Rohlinge. Material, Dichtungen und reale Maße vor Fertigung prüfen.</text>')
    parts.append('</svg>')
    return ''.join(parts)
