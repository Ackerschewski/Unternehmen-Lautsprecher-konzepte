"""Second manufacturing sheet: dimensioned inner components from DesignBundle."""
# ruff: noqa: ISC004
from __future__ import annotations

import re
from html import escape

from lautsprecher_konstruktion.drawings.style import painted, title_block
from lautsprecher_konstruktion.enclosure.folded_line import STUFFING_LABELS
from lautsprecher_konstruktion.services.design import DesignBundle


def _mm(value: float) -> float:
    return value*1000


def _dimension(x1: float, x2: float, y: float, caption: str) -> str:
    return (f'<path d="M{x1:.1f} {y-7:.1f}v14 M{x1:.1f} {y:.1f}H{x2:.1f} '
            f'M{x2:.1f} {y-7:.1f}v14" class="dim"/>'
            f'<text x="{(x1+x2)/2:.1f}" y="{y-9:.1f}" text-anchor="middle" '
            f'class="dimtext">{escape(caption)}</text>')


@painted
def render_internal_dimensions_svg(bundle: DesignBundle, *, screen: bool = False) -> str:
    """Interior sheet. ``screen=True`` crops the view to the section drawing (same geometry, larger on screen)."""
    if bundle.baffle_mode is not None:
        from lautsprecher_konstruktion.drawings.baffle_svg import render_baffle_svg
        return render_baffle_svg(bundle)
    if bundle.front_horn is not None:
        from lautsprecher_konstruktion.drawings.front_horn_svg import render_front_horn_svg
        return render_front_horn_svg(bundle)
    if bundle.tapped_horn is not None:
        from lautsprecher_konstruktion.drawings.tapped_horn_svg import render_tapped_horn_svg
        return render_tapped_horn_svg(bundle)
    if bundle.folded_line is not None and bundle.folded_line.horn is not None:
        from lautsprecher_konstruktion.drawings.rear_horn_svg import render_rear_horn_svg
        return render_rear_horn_svg(bundle)
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
    sheet_height = max(1100, int(row+31+len(bundle.panels)*28+155))
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="{sheet_height}" viewBox="0 0 1200 {sheet_height}">',
        '<style>.title{font-weight:700;font-size:27px;font-family:%FONT_UI%;fill:%INK%}.sub{font-weight:400;font-size:15px;font-family:%FONT_UI%;fill:%MUTED%}'
        '.head{font-weight:700;font-size:18px;font-family:%FONT_UI%;fill:%INK%}.text{font-weight:400;font-size:15px;font-family:%FONT_UI%;fill:%TEXT%}'
        '.dimtext{font-weight:400;font-size:13px;font-family:%FONT_UI%;fill:%TEXT%}.dim{fill:none;stroke:%MUTED%;stroke-width:1}'
        '.outline{fill:white;stroke:%INK%;stroke-width:2}.panel{fill:%PANEL%;stroke:%PANEL_STROKE%;stroke-width:1.5}'
        '.feature{fill:%ACCENT_FILL%;stroke:%ACCENT%;stroke-width:1.5}.rule{stroke:%RULE%;stroke-width:1}'
        '.lining{fill:%OCHRE_FILL%;stroke:%OCHRE%;stroke-width:1;stroke-dasharray:4 3}'
        '.damper{fill:%OCHRE_FILL%;stroke:%OCHRE%;stroke-width:1.5}.hole{fill:%WHITE%;stroke:%MUTED%;stroke-width:1.5}'
        '.tb{font-weight:600;font-size:12px;font-family:%FONT_UI%;fill:%MUTED%}.tbt{font-weight:700;font-size:13px;font-family:%FONT_UI%;fill:%INK%}'
        f'</style><rect width="1200" height="{sheet_height}" fill="white"/>',
        f'<text x="45" y="43" class="title">{escape(bundle.project.name)} · Innenaufbau</text>',
        f'<text x="45" y="70" class="sub">{escape(bundle.project.revision)} · Maße in mm · Tiefe ab Innenseite Front · Querschnitt schematisch · gestrichelt: Schallweg der Linie</text>',
        f'<text x="{x}" y="{y-17}" class="head">Seitenschnitt und Tiefenpositionen</text>',
        f'<rect x="{x}" y="{y}" width="{sd:.1f}" height="{sh:.1f}" class="outline"/>',
    ]
    for xx,yy,ww,hh in ((x,y,ft,sh),(back,y,bt,sh),(front,y,back-front,tt),
                        (front,y+sh-bot,back-front,bot)):
        parts.append(f'<rect x="{xx:.1f}" y="{yy:.1f}" width="{ww:.1f}" height="{hh:.1f}" class="panel"/>')
    if bundle.damping is not None:
        lt = _mm(bundle.damping.thickness_m)*scale
        parts.append(f'<rect x="{back-lt:.1f}" y="{y+tt:.1f}" width="{lt:.1f}" height="{sh-tt-bot:.1f}" class="lining"/>')
        parts.append(f'<text x="{back-lt/2+4:.1f}" y="{y+sh/2:.1f}" text-anchor="middle" class="dimtext" '
                     f'transform="rotate(-90 {back-lt/2+4:.1f} {y+sh/2:.1f})">'
                     f'Dämmung {_mm(bundle.damping.thickness_m):.0f}</text>')
    if bundle.folded_line is not None:
        line = bundle.folded_line
        wall = _mm(c.panel_thickness_m)*scale
        magnet = _mm(bundle.project.driver.mounting_depth_m or 0.0)*scale
        # Stuffing zones (rule-of-thumb levels) behind the partitions' channels, drawn first.
        top = y+tt
        for index, channel_h in enumerate(line.channel_heights_m):
            level = line.stuffing[index] if line.stuffing else 'none'
            if level != 'none':
                x0 = front+(magnet+8 if index == 0 else 0)
                opacity = {'light': .25, 'medium': .45, 'heavy': .65}[level]
                parts.append(f'<rect x="{x0:.1f}" y="{top:.1f}" width="{back-x0:.1f}" '
                             f'height="{_mm(channel_h)*scale:.1f}" fill="%OCHRE%" '
                             f'fill-opacity="{opacity}" class="stuffing"/>')
            top += _mm(channel_h)*scale+wall
        yy = y+tt
        for index, channel_h in enumerate(line.channel_heights_m[:-1]):
            gap = _mm(line.gap_m(index))*scale
            yy += _mm(channel_h)*scale
            xx = front if index%2 == 0 else front+gap
            parts.append(f'<rect x="{xx:.1f}" y="{yy:.1f}" '
                         f'width="{back-front-gap:.1f}" height="{wall:.1f}" class="panel"/>')
            parts.append(f'<text x="{xx+4:.1f}" y="{yy-5:.1f}" class="dimtext">'
                         f'F{index+1} · {_mm(channel_h):.1f} mm · Spalt {_mm(line.gap_m(index)):.0f} mm</text>')
            yy += wall
        # Acoustic path through the channels (dashed), from the driver chamber to the mouth.
        top = y+tt
        centres = []
        for channel_h in line.channel_heights_m:
            centres.append(top+_mm(channel_h)*scale/2)
            top += _mm(channel_h)*scale+wall
        points = [(front+magnet+8, centres[0])]
        for index in range(len(centres)-1):
            gap = _mm(line.gap_m(index))*scale
            end_x = back-gap/2 if index%2 == 0 else front+gap/2
            points += [(end_x, centres[index]), (end_x, centres[index+1])]
        last_x = front+6 if (len(centres)-1)%2 == 1 else back-6
        points.append((last_x, centres[-1]))
        path = " ".join(f"{px:.1f},{py:.1f}" for px, py in points)
        parts.append(f'<polyline points="{path}" fill="none" stroke="%ACCENT%" stroke-width="2" '
                     'stroke-dasharray="7 5"/>')
        parts.append(f'<text x="{back-4:.1f}" y="{y+tt+14:.1f}" text-anchor="end" class="dimtext">'
                     f'Treiberkammer · {_mm(line.channel_heights_m[0]):.0f} mm</text>')
        parts.append(f'<text x="{back-4:.1f}" y="{centres[-1]-5:.1f}" text-anchor="end" class="dimtext">'
                     f'Mündung vorn · {line.channel_areas_m2[-1]*10000:.0f} cm²</text>')
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
                xx = px  # the duct passes through the partition; L includes its thickness
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
        if element.type == 'port':  # L includes the wall the port passes through
            xx = x if element.surface == 'front' else back+bt-depth
        if element.type == 'port' and bundle.vent_damper is not None:
            # Resistive vent: a plain hole through the wall (L = wall thickness), damping material inside.
            wall_px = ft if element.surface == 'front' else bt
            hole_x = x if element.surface == 'front' else back
            pad = 8.0
            pad_x = front if element.surface == 'front' else back-pad
            parts.append(f'<rect x="{hole_x:.1f}" y="{cy-opening/2:.1f}" width="{wall_px:.1f}" height="{opening:.1f}" class="hole"/>')
            parts.append(f'<rect x="{pad_x:.1f}" y="{cy-opening/2:.1f}" width="{pad:.1f}" height="{opening:.1f}" class="damper"/>')
            parts.append(f'<text x="{(front+8 if element.surface == "front" else back-pad-5):.1f}" y="{cy-opening/2-7:.1f}" '
                         f'text-anchor="{"start" if element.surface == "front" else "end"}" class="dimtext">'
                         f'{escape(element.id)} · Einsatz {bundle.vent_damper.specific_resistance_rayl:.0f} Rayl</text>')
            continue
        parts.append(f'<rect x="{xx:.1f}" y="{cy-opening/2:.1f}" width="{depth:.1f}" height="{opening:.1f}" class="feature"/>')
        parts.append(f'<text x="{xx+5:.1f}" y="{cy-opening/2-7:.1f}" class="dimtext">{escape(element.id)}</text>')
        if (element.type == 'port' and bundle.port and bundle.port.shape == 'slot'
                and bundle.folded_line is None):
            wall = _mm(c.panel_thickness_m)*scale
            for yy in (cy-opening/2-wall,cy+opening/2):
                parts.append(f'<rect x="{front:.1f}" y="{yy:.1f}" width="{max(depth-ft,0.0):.1f}" height="{wall:.1f}" class="panel"/>')
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
            # W2: signed extent, negative when its motor points into the coupler (magnet to magnet)
            for xx, extent in ((front, depth), (ring_x+ring_t, _mm(k.w2_extent_m)*scale)):
                parts.append(f'<path d="M{xx:.1f} {cy-cut/2:.1f}L{xx+extent:.1f} {cy-cut/4:.1f}L{xx+extent:.1f} {cy+cut/4:.1f}L{xx:.1f} {cy+cut/2:.1f}Z" class="feature"/>')
            parts.append(f'<text x="{front+5:.1f}" y="{cy-cut/2-8:.1f}" class="dimtext">W1</text>')
            parts.append(f'<text x="{ring_x+ring_t+5:.1f}" y="{cy-cut/2-8:.1f}" class="dimtext">W2</text>')
        parts.append(_dimension(front,ring_x,y+sh+72,f'Koppelrohr {_mm(k.length_m):.1f}'))
    for index, depth in enumerate(bundle.brace_depths_m, start=1):
        bx = front+_mm(depth)*scale
        # Window brace: the section through the opening shows only the border strips (top and bottom).
        strip = min(_mm(bundle.brace.border_m if bundle.brace else c.panel_thickness_m)*scale, (sh-tt-bot)/3)
        for yy in (y+tt, y+sh-bot-strip):
            parts.append(f'<rect x="{bx:.1f}" y="{yy:.1f}" width="{_mm(c.panel_thickness_m)*scale:.1f}" height="{strip:.1f}" class="feature"/>')
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
                     f'Umlenkspalte {", ".join(f"{_mm(line.gap_m(i)):.0f}" for i in range(line.fold_count))} mm, abwechselnd hinten/vorn',
                     'Dämmung (Richtwert): '+', '.join(f'K{i+1} {STUFFING_LABELS[x]}' for i,x in enumerate(line.stuffing)),
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
            info.extend((f'{"Kardioid-Rückvent" if bundle.vent_damper and bundle.vent_damper.surface == "back" else "Aperiodischer Vent"} Soll: {bundle.port_resistance_pa_s_m3:.0f} Pa·s/m³',
                         'Dämpfungseinsatz einsetzen; Widerstand am Prototyp messen'))
            if bundle.vent_damper is not None:
                v = bundle.vent_damper
                info.append(f'Einsatz über {v.area_m2*10000:.1f} cm² Loch: ≈ {v.specific_resistance_rayl:.0f} Rayl (Pa·s/m)')
                if v.qtc_effective is not None:
                    info.append(f'Qtc geschlossen {v.qtc_closed:.2f} → mit Vent ≈ {v.qtc_effective:.2f} (QL {v.ql:.2f})')
    if bundle.rear_port:
        p = bundle.rear_port
        info.extend((f'Port BR2 Rückkammer: Ø {_mm(p.diameter_m or 0):.1f}',
                     f'Kanal physisch {_mm(p.physical_length_m):.1f} lang',
                     f'Fb2 {p.tuning_hz:.1f} Hz · Fläche {p.area_m2*10000:.1f} cm²'))
    if bundle.damping:
        dm = bundle.damping
        info.extend((f'Dämmung Rückwand {_mm(dm.thickness_m):.0f} mm + Seiten hinter dem Chassis',
                     f'≈ {dm.area_m2:.2f} m² Wolle/Schaum; {_mm(dm.clearance_to_driver_m):.0f} mm Abstand zum Magneten'))
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
    parts.append(title_block(45, sheet_height-110, 1110, bundle.project.name, bundle.project.revision, 'Innenaufbau', 'Maße in mm · Maßstab schematisch'))
    parts.append('</svg>')
    svg = ''.join(parts)
    if screen:
        # Screen reading view: only the section with its dimension chains; tables and notes stay on the print sheet.
        x0, y0 = 20.0, 85.0
        crop_w, crop_h = max(470.0, x+sd+130-x0), y+sh+105-y0
        svg = re.sub(r'<svg [^>]*>',
                     f'<svg xmlns="http://www.w3.org/2000/svg" width="{crop_w:.0f}" height="{crop_h:.0f}" '
                     f'viewBox="{x0:.0f} {y0:.0f} {crop_w:.0f} {crop_h:.0f}">', svg, count=1)
    return svg
