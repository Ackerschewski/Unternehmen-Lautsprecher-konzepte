"""Second manufacturing sheet: dimensioned inner components from DesignBundle."""
# ruff: noqa: ISC004
from __future__ import annotations

from html import escape

from lautsprecher_konstruktion.services.design import DesignBundle


def _mm(value: float) -> float:
    return value*1000


def _dimension(x1: float, x2: float, y: float, caption: str) -> str:
    return (f'<path d="M{x1:.1f} {y-7:.1f}v14 M{x1:.1f} {y:.1f}H{x2:.1f} '
            f'M{x2:.1f} {y-7:.1f}v14" class="dim"/>'
            f'<text x="{(x1+x2)/2:.1f}" y="{y-9:.1f}" text-anchor="middle" '
            f'class="dimtext">{escape(caption)}</text>')


def render_internal_dimensions_svg(bundle: DesignBundle) -> str:
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
    d, h = _mm(c.depth_m), _mm(c.height_m)
    scale = min(550/max(d,1), 360/max(h,1))
    x, y = 90.0, 125.0
    sd, sh = d*scale, h*scale
    ft, bt = _mm(c.effective_front_thickness_m)*scale, _mm(c.effective_back_thickness_m)*scale
    tt = _mm(c.top_thickness_m or c.panel_thickness_m)*scale
    bot = _mm(c.bottom_thickness_m or c.panel_thickness_m)*scale
    front, back = x+ft, x+sd-bt
    row = max(670,y+sh+195)
    sheet_height = max(1100, int(row+31+len(bundle.panels)*28+85))
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="{sheet_height}" viewBox="0 0 1200 {sheet_height}">',
        '<style>.title{font:700 27px sans-serif;fill:#193448}.sub{font:15px sans-serif;fill:#496373}'
        '.head{font:700 18px sans-serif;fill:#193448}.text{font:15px sans-serif;fill:#284455}'
        '.dimtext{font:13px sans-serif;fill:#254a60}.dim{fill:none;stroke:#5c7889;stroke-width:1}'
        '.outline{fill:white;stroke:#193448;stroke-width:2}.panel{fill:#dce9ed;stroke:#34576a;stroke-width:1.5}'
        '.feature{fill:#c5e7f5;stroke:#16749a;stroke-width:1.5}.rule{stroke:#c8d6dd;stroke-width:1}'
        f'</style><rect width="1200" height="{sheet_height}" fill="white"/>',
        f'<text x="45" y="43" class="title">{escape(bundle.project.name)} · Innenaufbau</text>',
        f'<text x="45" y="70" class="sub">{escape(bundle.project.revision)} · Maße in mm · Tiefe ab Innenseite Front · Querschnitt schematisch</text>',
        f'<text x="{x}" y="{y-17}" class="head">Seitenschnitt und Tiefenpositionen</text>',
        f'<rect x="{x}" y="{y}" width="{sd:.1f}" height="{sh:.1f}" class="outline"/>',
    ]
    for xx,yy,ww,hh in ((x,y,ft,sh),(back,y,bt,sh),(front,y,back-front,tt),
                        (front,y+sh-bot,back-front,bot)):
        parts.append(f'<rect x="{xx:.1f}" y="{yy:.1f}" width="{ww:.1f}" height="{hh:.1f}" class="panel"/>')
    if bundle.folded_line is not None:
        line = bundle.folded_line
        yy = y+tt
        gap = _mm(line.turn_gap_m)*scale
        wall = _mm(c.panel_thickness_m)*scale
        for index, channel_h in enumerate(line.channel_heights_m[:-1]):
            yy += _mm(channel_h)*scale
            xx = front if index%2 == 0 else front+gap
            parts.append(f'<rect x="{xx:.1f}" y="{yy:.1f}" '
                         f'width="{back-front-gap:.1f}" height="{wall:.1f}" class="panel"/>')
            parts.append(f'<text x="{xx+4:.1f}" y="{yy-5:.1f}" class="dimtext">'
                         f'F{index+1} · {_mm(channel_h):.1f} mm</text>')
            yy += wall
    if bundle.partition_front_depth_m is not None:
        px = front+_mm(bundle.partition_front_depth_m)*scale
        driver = next((e for e in bundle.front_elements if e.surface == 'partition' and e.type != 'port'), None)
        cy = y+sh-_mm(driver.y_m)*scale if driver else y+sh/2
        opening = _mm(driver.cutout_diameter_m or driver.height)*scale if driver else 0
        openings = sorted((y+sh-_mm(e.y_m)*scale-_mm(e.cutout_diameter_m or e.height)*scale/2,
                           y+sh-_mm(e.y_m)*scale+_mm(e.cutout_diameter_m or e.height)*scale/2)
                          for e in bundle.front_elements if e.surface == 'partition')
        cursor = y+tt
        for start,end in openings+[(y+sh-bot,y+sh-bot)]:
            if start > cursor:
                parts.append(f'<rect x="{px:.1f}" y="{cursor:.1f}" '
                             f'width="{_mm(c.panel_thickness_m)*scale:.1f}" '
                             f'height="{start-cursor:.1f}" class="panel"/>')
            cursor = max(cursor,end)
        if driver:
            depth = _mm(driver.mounting_depth_m)*scale
            parts.append(f'<path d="M{px:.1f} {cy-opening/2:.1f}L{px+depth:.1f} {cy-opening/4:.1f}L{px+depth:.1f} {cy+opening/4:.1f}L{px:.1f} {cy+opening/2:.1f}Z" class="feature"/>')
            parts.append(f'<text x="{px+6:.1f}" y="{cy-opening/2-8:.1f}" class="dimtext">{escape(driver.id)}</text>')
        for element in bundle.front_elements:
            if element.surface == 'partition' and element.type == 'port':
                py = y+sh-_mm(element.y_m)*scale
                eh = _mm(element.cutout_diameter_m or element.height)*scale
                depth = _mm(element.mounting_depth_m)*scale
                xx = px+_mm(c.panel_thickness_m)*scale
                parts.append(f'<rect x="{xx:.1f}" y="{py-eh/2:.1f}" '
                             f'width="{depth:.1f}" height="{eh:.1f}" class="feature"/>')
                parts.append(f'<text x="{xx+5:.1f}" y="{py-eh/2-7:.1f}" '
                             f'class="dimtext">{escape(element.id)} intern</text>')
        parts.append(_dimension(front,px,y+sh+72,f'Frontkammer {_mm(bundle.partition_front_depth_m):.1f}'))
        rear = c.internal_depth_m-bundle.partition_front_depth_m-c.panel_thickness_m
        parts.append(_dimension(px+_mm(c.panel_thickness_m)*scale,back,y+sh+72,f'Rückkammer {_mm(rear):.1f}'))
    for element in bundle.front_elements:
        if element.surface not in {'front', 'back'} or (bundle.coupler and element.id == 'W1'):
            continue
        cy = y+sh-_mm(element.y_m)*scale
        opening = _mm(element.cutout_diameter_m or element.height)*scale
        depth = _mm(element.mounting_depth_m)*scale
        xx = front if element.surface == 'front' else back-depth
        parts.append(f'<rect x="{xx:.1f}" y="{cy-opening/2:.1f}" width="{depth:.1f}" height="{opening:.1f}" class="feature"/>')
        parts.append(f'<text x="{xx+5:.1f}" y="{cy-opening/2-7:.1f}" class="dimtext">{escape(element.id)}</text>')
        if (element.type == 'port' and bundle.port and bundle.port.shape == 'slot'
                and bundle.folded_line is None):
            wall = _mm(c.panel_thickness_m)*scale
            for yy in (cy-opening/2-wall,cy+opening/2):
                parts.append(f'<rect x="{front:.1f}" y="{yy:.1f}" width="{depth:.1f}" height="{wall:.1f}" class="panel"/>')
    if bundle.coupler:
        k = bundle.coupler
        driver = next((e for e in bundle.front_elements if e.id == 'W1'), None)
        cy = y+sh-_mm(driver.y_m)*scale if driver else y+sh/2
        oh, ih = _mm(k.outer_diameter_m)*scale, _mm(k.inner_diameter_m)*scale
        length = _mm(k.length_m)*scale
        wall = (oh-ih)/2
        for yy in (cy-oh/2,cy+ih/2):
            parts.append(f'<rect x="{front:.1f}" y="{yy:.1f}" width="{length:.1f}" height="{wall:.1f}" class="feature"/>')
        ring_x = front+length
        ring_t = _mm(k.ring_thickness_m)*scale
        for yy in (cy-oh/2,cy+_mm(k.driver_cutout_m)*scale/2):
            parts.append(f'<rect x="{ring_x:.1f}" y="{yy:.1f}" width="{ring_t:.1f}" height="{(oh-_mm(k.driver_cutout_m)*scale)/2:.1f}" class="feature"/>')
        if driver:
            cut = _mm(k.driver_cutout_m)*scale
            depth = _mm(driver.mounting_depth_m)*scale
            for xx in (front, ring_x+ring_t):
                parts.append(f'<path d="M{xx:.1f} {cy-cut/2:.1f}L{xx+depth:.1f} {cy-cut/4:.1f}L{xx+depth:.1f} {cy+cut/4:.1f}L{xx:.1f} {cy+cut/2:.1f}Z" class="feature"/>')
            parts.append(f'<text x="{front+5:.1f}" y="{cy-cut/2-8:.1f}" class="dimtext">W1</text>')
            parts.append(f'<text x="{ring_x+ring_t+5:.1f}" y="{cy-cut/2-8:.1f}" class="dimtext">W2</text>')
        parts.append(_dimension(front,ring_x,y+sh+72,f'Koppelrohr {_mm(k.length_m):.1f}'))
    for index, depth in enumerate(bundle.brace_depths_m, start=1):
        bx = front+_mm(depth)*scale
        parts.append(f'<rect x="{bx:.1f}" y="{y+tt:.1f}" width="{_mm(c.panel_thickness_m)*scale:.1f}" height="{sh-tt-bot:.1f}" class="feature"/>')
        parts.append(f'<text x="{bx+4:.1f}" y="{y+tt+18:.1f}" class="dimtext">B{index}</text>')
        parts.append(_dimension(front,bx,y+sh+105+index*28,f'B{index} {_mm(depth):.1f}'))
    parts.append(_dimension(x,x+sd,y+sh+37,f'Außentiefe {d:.1f}'))
    parts.append(_dimension(front,back,y+sh+145+len(bundle.brace_depths_m)*28,
                            f'Innentiefe {_mm(c.internal_depth_m):.1f}'))
    parts.append('<text x="720" y="130" class="head">Volumenbilanz</text>')
    volume_lines = (
        f'Brutto innen: {c.gross_internal_volume_m3*1000:.2f} l',
        f'Verdrängung gesamt: {bundle.total_displacement_m3*1000:.2f} l',
        f'Netto akustisch: {bundle.target_net_volume_m3*1000:.2f} l',
        f'Innen B × H: {_mm(c.internal_width_m):.1f} × {_mm(c.internal_height_m):.1f}',
    )
    for i,text in enumerate(volume_lines):
        parts.append(f'<text x="720" y="{163+i*27}" class="text">{escape(text)}</text>')
    parts.append('<text x="720" y="285" class="head">Einbauten</text>')
    info: list[str] = []
    if bundle.folded_line is not None:
        line = bundle.folded_line
        info.extend((f'Linienweg {_mm(line.path_length_m):.1f} mm · Viertelwelle {line.estimated_quarter_wave_hz:.1f} Hz',
                     f'Umlenkspalte {line.turn_gap_m*1000:.1f} mm, abwechselnd hinten/vorn',
                     *(f'Kanal {i+1}: Höhe {_mm(height):.1f} mm · Fläche {area*10000:.1f} cm²'
                       for i,(height,area) in enumerate(zip(line.channel_heights_m,line.channel_areas_m2,strict=True)))))
    if bundle.port:
        p = bundle.port
        section = (f'Ø {_mm(p.diameter_m):.1f}' if p.diameter_m else
                   f'{_mm(p.width_m or 0.0):.1f} × {_mm(p.height_m or 0.0):.1f}')
        if bundle.folded_line is not None and bundle.folded_line.family != 'mltl':
            info.extend((f'Mündung BR1: {section}',
                         f'Frontöffnung {_mm(p.physical_length_m):.1f} mm durch Plattenstärke',
                         f'Öffnungsfläche {p.area_m2*10000:.1f} cm²'))
        else:
            info.extend((f'Port BR1: {section}', f'Kanal physisch {_mm(p.physical_length_m):.1f} lang',
                         f'Öffnungsfläche {p.area_m2*10000:.1f} cm²'))
        if p.shape == 'slot' and bundle.folded_line is None:
            info.append(f'Kanalwände: Plattenstärke {_mm(c.panel_thickness_m):.1f}')
        if bundle.port_resistance_pa_s_m3 is not None:
            info.extend((f'Aperiodischer Vent Soll: {bundle.port_resistance_pa_s_m3:.0f} Pa·s/m³',
                         'Dämpfungseinsatz einsetzen; Widerstand am Prototyp messen'))
    if bundle.rear_port:
        p = bundle.rear_port
        info.extend((f'Port BR2 Rückkammer: Ø {_mm(p.diameter_m or 0):.1f}',
                     f'Kanal physisch {_mm(p.physical_length_m):.1f} lang',
                     f'Fb2 {p.tuning_hz:.1f} Hz · Fläche {p.area_m2*10000:.1f} cm²'))
    if bundle.brace:
        b = bundle.brace
        info.extend((f'{b.quantity} Fensterstrebe(n) B1…B{b.quantity}',
                     f'Rohmaß {_mm(b.outer_width_m):.1f} × {_mm(b.outer_height_m):.1f} × {_mm(b.thickness_m):.1f}',
                     f'Öffnung {_mm(b.outer_width_m-2*b.border_m):.1f} × {_mm(b.outer_height_m-2*b.border_m):.1f}',
                     f'Rand umlaufend {_mm(b.border_m):.1f}'))
    if bundle.coupler:
        k = bundle.coupler
        info.extend((f'Koppelrohr: Innen Ø {_mm(k.inner_diameter_m):.1f}, Außen Ø {_mm(k.outer_diameter_m):.1f}',
                     f'Länge {_mm(k.length_m):.1f}; Ring {_mm(k.ring_thickness_m):.1f} dick',
                     f'Ring-Ausschnitt Ø {_mm(k.driver_cutout_m):.1f}; zwei gleiche Chassis'))
    if bundle.partition_front_depth_m is not None:
        info.append(f'Trennwand: {_mm(c.internal_width_m):.1f} × {_mm(c.internal_height_m):.1f} × {_mm(c.panel_thickness_m):.1f}')
    for i,text in enumerate(info):
        parts.append(f'<text x="720" y="{317+i*25}" class="text">{escape(text)}</text>')
    parts.append(f'<text x="45" y="{row:.1f}" class="head">Platten und Zuschnitt (Rohmaße)</text>')
    for index,panel in enumerate(bundle.panels):
        yy = row+31+index*28
        panel_text = (f'{panel.quantity} × {panel.name}: {_mm(panel.width_m):.1f} × '
                      f'{_mm(panel.height_m):.1f} × {_mm(panel.thickness_m):.1f}')
        parts.append(f'<text x="49" y="{yy:.1f}" class="text">{escape(panel_text)}</text>')
        parts.append(f'<path d="M45 {yy+7:.1f}H1155" class="rule"/>')
    parts.append(f'<text x="45" y="{sheet_height-32}" class="sub">Bohrbilder nur dort übernehmen, wo Herstellerdaten vorliegen. Material, Dichtungen und reale Maße vor Fertigung prüfen.</text>')
    parts.append('</svg>')
    return ''.join(parts)
