"""Readable multi-view construction drawing from the resolved cabinet geometry."""
# ruff: noqa: ISC004
from __future__ import annotations

from html import escape
from textwrap import wrap

from lautsprecher_konstruktion.drawings.style import painted
from lautsprecher_konstruktion.enclosure.layout import FrontElement, bolt_holes
from lautsprecher_konstruktion.services.design import DesignBundle


def _mm(value: float) -> float:
    return value * 1000


def _dim(x1: float, x2: float, y: float, label: str) -> str:
    middle = (x1+x2)/2
    return (f'<path d="M{x1:.1f} {y-7:.1f}v14 M{x1:.1f} {y:.1f}H{x2:.1f} '
            f'M{x2:.1f} {y-7:.1f}v14" class="dimension"/>'
            f'<text x="{middle:.1f}" y="{y-11:.1f}" class="dimension-text" '
            f'text-anchor="middle">{escape(label)}</text>')


def _element_front(element: FrontElement, x: float, y: float,
                   h: float, scale: float) -> str:
    cx = x+_mm(element.x_m)*scale
    cy = y+h-_mm(element.y_m)*scale
    if element.outer_diameter_m is not None:
        r = _mm(element.outer_diameter_m)*scale/2
        cut = _mm(element.cutout_diameter_m or element.outer_diameter_m)*scale/2
        shape = (f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" class="flange"/>'
                 f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{cut:.1f}" class="cutout"/>')
    else:
        ew, eh = _mm(element.width)*scale, _mm(element.height)*scale
        shape = (f'<rect x="{cx-ew/2:.1f}" y="{cy-eh/2:.1f}" width="{ew:.1f}" '
                 f'height="{eh:.1f}" class="cutout"/>')
    holes = ''.join(f'<circle cx="{x+_mm(hx)*scale:.1f}" '
                    f'cy="{y+h-_mm(hy)*scale:.1f}" r="{max(2,_mm(hr)*scale):.1f}" '
                    f'class="drill"/>' for hx,hy,hr in bolt_holes(element))
    return shape+holes+f'<text x="{cx:.1f}" y="{cy+5:.1f}" text-anchor="middle" class="id">{escape(element.id)}</text>'


@painted
def render_assembly_svg(bundle: DesignBundle) -> str:
    if bundle.tapped_horn is not None:
        from lautsprecher_konstruktion.drawings.tapped_horn_svg import render_tapped_horn_svg
        return render_tapped_horn_svg(bundle)
    if bundle.baffle_mode is not None:
        from lautsprecher_konstruktion.drawings.baffle_svg import render_baffle_svg
        return render_baffle_svg(bundle)
    if bundle.front_horn is not None:
        from lautsprecher_konstruktion.drawings.front_horn_svg import render_front_horn_svg
        return render_front_horn_svg(bundle)
    cab = bundle.cabinet
    w,h,d = (_mm(v) for v in (cab.width_m,cab.height_m,cab.depth_m))
    scale = min(390/w, 560/h, 570/d)
    front_x, top_y = 65.0, 125.0
    section_x = 520.0
    fw, fh, fd = w*scale, h*scale, d*scale
    ft = _mm(cab.effective_front_thickness_m)*scale
    bt = _mm(cab.effective_back_thickness_m)*scale
    tt = _mm(cab.top_thickness_m or cab.panel_thickness_m)*scale
    bot = _mm(cab.bottom_thickness_m or cab.panel_thickness_m)*scale
    inner_x = section_x+ft
    rear_x = section_x+fd-bt
    inner_y = top_y+tt
    inner_h = fh-tt-bot
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" '
        f'height="{1100 if bundle.folded_line else 1020}" '
        f'viewBox="0 0 1200 {1100 if bundle.folded_line else 1020}">',
        '<defs><pattern id="material" width="8" height="8" patternUnits="userSpaceOnUse" '
        'patternTransform="rotate(45)"><rect width="8" height="8" fill="%SURFACE%"/>'
        '<path d="M0 0V8" stroke="%MUTED%" stroke-width="2"/></pattern></defs>',
        '<style>.title{font-weight:700;font-size:27px;font-family:%FONT_UI%;fill:%INK%}.subtitle{font-weight:400;font-size:14px;font-family:%FONT_UI%;fill:%MUTED%}'
        '.label{font-weight:700;font-size:19px;font-family:%FONT_UI%;fill:%INK%}.note{font-weight:400;font-size:15px;font-family:%FONT_UI%;fill:%INK%}'
        '.small{font-weight:400;font-size:13px;font-family:%FONT_UI%;fill:%MUTED%}.panel{fill:url(#material);stroke:%INK%;stroke-width:2}'
        '.outline{fill:%WHITE%;stroke:%INK%;stroke-width:2}.flange{fill:%SURFACE%;stroke:%TEXT%;stroke-width:2}'
        '.cutout{fill:none;stroke:%ACCENT%;stroke-width:2.2}.drill{fill:%WHITE%;stroke:%CRITICAL%;stroke-width:1.5}'
        '.id{font-weight:700;font-size:13px;font-family:%FONT_UI%;fill:%INK%}.dimension{fill:none;stroke:%MUTED%;stroke-width:1.2}'
        '.dimension-text{font-weight:400;font-size:14px;font-family:%FONT_UI%;fill:%TEXT%}.component{fill:%SURFACE%;stroke:%ACCENT%;stroke-width:2}'
        '.lining{fill:%OCHRE_FILL%;stroke:%OCHRE%;stroke-width:1;stroke-dasharray:4 3}'
        '.damper{fill:%OCHRE_FILL%;stroke:%OCHRE%;stroke-width:1.5}.hole{fill:%WHITE%;stroke:%INK%;stroke-width:2}'
        '.brace{fill:%OK_FILL%;stroke:%OK%;stroke-width:1.6}.warning{font-weight:700;font-size:14px;font-family:%FONT_UI%;fill:%CRITICAL%}'
        '</style>',
        f'<rect width="1200" height="{1100 if bundle.folded_line else 1020}" fill="%WHITE%"/>',
        f'<text x="45" y="45" class="title">{escape(bundle.project.name)}</text>',
        f'<text x="45" y="72" class="subtitle">{escape(bundle.project.revision)} · '
        f'{escape(bundle.project.enclosure.enclosure_type)} · '
        f'Netto {_mm(bundle.target_net_volume_m3):.1f} l · Zeichnung in mm</text>',
        f'<text x="{front_x}" y="{top_y-25}" class="label">Front</text>',
        f'<rect x="{front_x}" y="{top_y}" width="{fw:.1f}" height="{fh:.1f}" class="outline"/>',
    ]
    for element in bundle.front_elements:
        if element.surface == "front":
            parts.append(_element_front(element,front_x,top_y,fh,scale))
    parts += [
        _dim(front_x,front_x+fw,top_y+fh+35,f"B {w:.1f}"),
        f'<text x="{front_x-31}" y="{top_y+fh/2:.1f}" class="dimension-text" '
        f'transform="rotate(-90 {front_x-31} {top_y+fh/2:.1f})" text-anchor="middle">H {h:.1f}</text>',
        f'<text x="{section_x}" y="{top_y-25}" class="label">Seitenschnitt · Innenaufbau</text>',
        f'<rect x="{section_x}" y="{top_y}" width="{fd:.1f}" height="{fh:.1f}" class="outline"/>',
        f'<rect x="{section_x}" y="{top_y}" width="{ft:.1f}" height="{fh:.1f}" class="panel"/>',
        f'<rect x="{rear_x:.1f}" y="{top_y}" width="{bt:.1f}" height="{fh:.1f}" class="panel"/>',
        f'<rect x="{inner_x:.1f}" y="{top_y}" width="{rear_x-inner_x:.1f}" height="{tt:.1f}" class="panel"/>',
        f'<rect x="{inner_x:.1f}" y="{top_y+fh-bot:.1f}" width="{rear_x-inner_x:.1f}" '
        f'height="{bot:.1f}" class="panel"/>',
    ]
    if bundle.damping is not None:
        lt = _mm(bundle.damping.thickness_m)*scale
        parts.append(f'<rect x="{rear_x-lt:.1f}" y="{inner_y:.1f}" width="{lt:.1f}" height="{inner_h:.1f}" class="lining"/>')
        parts.append(f'<text x="{rear_x-lt/2+4:.1f}" y="{inner_y+inner_h/2:.1f}" text-anchor="middle" class="small" '
                     f'transform="rotate(-90 {rear_x-lt/2+4:.1f} {inner_y+inner_h/2:.1f})">'
                     f'Dämmung {_mm(bundle.damping.thickness_m):.0f} mm</text>')
    partition_x = None
    if bundle.folded_line is not None:
        line = bundle.folded_line
        yy = inner_y
        wall = _mm(cab.panel_thickness_m)*scale
        if line.horn is not None:
            from lautsprecher_konstruktion.drawings.rear_horn_svg import horn_septa_svg
            parts.extend(horn_septa_svg(line.horn, inner_x, inner_y, scale, cab.panel_thickness_m, "panel"))
        for index, channel_h in enumerate(line.channel_heights_m[:-1] if line.horn is None else ()):
            gap = _mm(line.gap_m(index))*scale
            yy += _mm(channel_h)*scale
            xx = inner_x if index%2 == 0 else inner_x+gap
            parts.append(f'<rect x="{xx:.1f}" y="{yy:.1f}" '
                         f'width="{rear_x-inner_x-gap:.1f}" height="{wall:.1f}" class="panel"/>')
            parts.append(f'<text x="{xx+7:.1f}" y="{yy-5:.1f}" class="id">'
                         f'F{index+1} · Kanal {channel_h*1000:.1f} mm</text>')
            yy += wall
    if bundle.partition_front_depth_m is not None:
        partition_x = inner_x+_mm(bundle.partition_front_depth_m)*scale
        driver = next((e for e in bundle.front_elements if e.surface == "partition" and e.type != "port"),None)
        opening_y = top_y+fh-_mm(driver.y_m)*scale if driver else top_y+fh/2
        openings = sorted((top_y+fh-_mm(e.y_m)*scale-_mm(e.cutout_diameter_m or e.height)*scale/2,
                           top_y+fh-_mm(e.y_m)*scale+_mm(e.cutout_diameter_m or e.height)*scale/2)
                          for e in bundle.front_elements if e.surface == "partition")
        cursor = inner_y
        for start,end in openings+[(inner_y+inner_h,inner_y+inner_h)]:
            if start > cursor:
                parts.append(f'<rect x="{partition_x:.1f}" y="{cursor:.1f}" '
                             f'width="{_mm(cab.panel_thickness_m)*scale:.1f}" '
                             f'height="{start-cursor:.1f}" class="panel"/>')
            cursor = max(cursor,end)
        parts.append(f'<text x="{(inner_x+partition_x)/2:.1f}" y="{top_y+fh/2:.1f}" '
                     f'text-anchor="middle" class="small">Frontkammer {_mm(bundle.front_chamber_volume_m3 or 0):.1f} l</text>')
        parts.append(f'<text x="{(partition_x+rear_x)/2:.1f}" y="{top_y+fh/2:.1f}" '
                     f'text-anchor="middle" class="small">Rückkammer {_mm(bundle.rear_chamber_volume_m3 or 0):.1f} l</text>')
        parts.append(_dim(inner_x,partition_x,top_y+fh+67,
                          f"Frontkammer {_mm(bundle.partition_front_depth_m):.1f}"))
        parts.append(_dim(partition_x+_mm(cab.panel_thickness_m)*scale,rear_x,
                          top_y+fh+67,
                          f"Rückkammer {_mm(cab.internal_depth_m-bundle.partition_front_depth_m-cab.panel_thickness_m):.1f}"))
        if driver:
            dh = _mm(driver.cutout_diameter_m or driver.height)*scale
            depth = _mm(driver.mounting_depth_m)*scale
            parts.append(f'<path d="M{partition_x:.1f} {opening_y-dh/2:.1f} '
                         f'L{partition_x+depth:.1f} {opening_y-dh*.25:.1f} '
                         f'L{partition_x+depth:.1f} {opening_y+dh*.25:.1f} '
                         f'L{partition_x:.1f} {opening_y+dh/2:.1f} Z" class="component"/>')
            parts.append(f'<text x="{partition_x+8:.1f}" y="{opening_y-10:.1f}" '
                         f'class="id">{escape(driver.id)} innen</text>')
        for element in bundle.front_elements:
            if element.surface == "partition" and element.type == "port":
                cy = top_y+fh-_mm(element.y_m)*scale
                eh = _mm(element.cutout_diameter_m or element.height)*scale
                depth = _mm(element.mounting_depth_m)*scale
                x_port = partition_x  # the duct passes through the partition; L includes its thickness
                parts.append(f'<rect x="{x_port:.1f}" y="{cy-eh/2:.1f}" '
                             f'width="{depth:.1f}" height="{eh:.1f}" class="component"/>')
                parts.append(f'<text x="{x_port+5:.1f}" y="{cy-eh/2-7:.1f}" '
                             f'class="id">{escape(element.id)} intern · L {_mm(element.mounting_depth_m):.0f}</text>')
    for element in bundle.front_elements:
        cy = top_y+fh-_mm(element.y_m)*scale
        eh = _mm(element.cutout_diameter_m or element.height)*scale
        depth = _mm(element.mounting_depth_m)*scale
        if element.type == "port" and bundle.vent_damper is not None and element.surface in {"front", "back"}:
            # Resistive vent (aperiodic / cardioid): a hole through the wall, damping material behind it.
            pad = 8.0
            hole_x, wall_px = (section_x, ft) if element.surface == "front" else (rear_x, bt)
            pad_x = inner_x if element.surface == "front" else rear_x-pad
            parts.append(f'<rect x="{hole_x:.1f}" y="{cy-eh/2:.1f}" width="{wall_px:.1f}" height="{eh:.1f}" class="hole"/>')
            parts.append(f'<rect x="{pad_x:.1f}" y="{cy-eh/2:.1f}" width="{pad:.1f}" height="{eh:.1f}" class="damper"/>')
            label_x = inner_x+pad+6 if element.surface == "front" else rear_x-pad-6
            parts.append(f'<text x="{label_x:.1f}" y="{cy+4:.1f}" text-anchor="{"start" if element.surface == "front" else "end"}" '
                         f'class="id">{escape(element.id)} · Einsatz ≈ {bundle.vent_damper.specific_resistance_rayl:.0f} Rayl</text>')
        elif element.surface == "front":
            if element.type == "port":
                if (bundle.port is not None and bundle.port.shape == "slot"
                        and bundle.folded_line is None):
                    wall=_mm(cab.panel_thickness_m)*scale
                    slot_len = max(depth-ft, 0.0)
                    parts.append(f'<rect x="{inner_x:.1f}" y="{cy-eh/2-wall:.1f}" '
                                 f'width="{slot_len:.1f}" height="{wall:.1f}" class="panel"/>')
                    parts.append(f'<rect x="{inner_x:.1f}" y="{cy+eh/2:.1f}" '
                                 f'width="{slot_len:.1f}" height="{wall:.1f}" class="panel"/>')
                # Port length L includes the front panel: the duct starts at the outer face.
                parts.append(f'<rect x="{section_x:.1f}" y="{cy-eh/2:.1f}" '
                             f'width="{depth:.1f}" height="{eh:.1f}" class="component"/>')
                parts.append(f'<text x="{section_x+depth+8:.1f}" y="{cy+4:.1f}" '
                             f'class="id">{escape(element.id)} · L {element.mounting_depth_m*1000:.0f}</text>')
            else:
                parts.append(f'<path d="M{inner_x:.1f} {cy-eh/2:.1f} '
                             f'L{inner_x+depth:.1f} {cy-eh*.25:.1f} '
                             f'L{inner_x+depth:.1f} {cy+eh*.25:.1f} '
                             f'L{inner_x:.1f} {cy+eh/2:.1f} Z" class="component"/>')
                parts.append(f'<text x="{inner_x+depth+8:.1f}" y="{cy+4:.1f}" '
                             f'class="id">{escape(element.id)} · Tiefe {element.mounting_depth_m*1000:.0f}</text>')
        elif element.surface == "back":
            if element.type == "port":
                # The duct ends flush with the outer face of the back wall (L includes its thickness).
                parts.append(f'<rect x="{rear_x+bt-depth:.1f}" y="{cy-eh/2:.1f}" '
                             f'width="{depth:.1f}" height="{eh:.1f}" class="component"/>')
            else:
                parts.append(f'<path d="M{rear_x:.1f} {cy-eh/2:.1f} '
                             f'L{rear_x-depth:.1f} {cy-eh*.25:.1f} '
                             f'L{rear_x-depth:.1f} {cy+eh*.25:.1f} '
                             f'L{rear_x:.1f} {cy+eh/2:.1f} Z" class="component"/>')
            parts.append(f'<text x="{rear_x+(bt if element.type == "port" else 0)-depth-5:.1f}" y="{cy-eh/2-9:.1f}" '
                         f'class="id">{escape(element.id)} Rückwand</text>')
    if bundle.coupler:
        k = bundle.coupler
        w1 = next(e for e in bundle.front_elements if e.id == 'W1' and e.surface == 'front')
        cy = top_y+fh-_mm(w1.y_m)*scale
        outer = _mm(k.outer_diameter_m)*scale
        inner = _mm(k.inner_diameter_m)*scale
        length = _mm(k.length_m)*scale
        wall = (outer-inner)/2
        ring_x = inner_x+length
        ring_t = _mm(k.ring_thickness_m)*scale
        for yy in (cy-outer/2, cy+inner/2):
            parts.append(f'<rect x="{inner_x:.1f}" y="{yy:.1f}" width="{length:.1f}" height="{wall:.1f}" class="panel"/>')
        for yy in (cy-outer/2,cy+_mm(k.driver_cutout_m)*scale/2):
            ring_height=(outer-_mm(k.driver_cutout_m)*scale)/2
            parts.append(f'<rect x="{ring_x:.1f}" y="{yy:.1f}" width="{ring_t:.1f}" height="{ring_height:.1f}" class="panel"/>')
        depth = _mm(k.w2_extent_m)*scale  # signed: negative = W2 motor points into the coupler
        cut = _mm(k.driver_cutout_m)*scale
        parts.append(f'<path d="M{ring_x+ring_t:.1f} {cy-cut/2:.1f}L{ring_x+ring_t+depth:.1f} {cy-cut/4:.1f}L{ring_x+ring_t+depth:.1f} {cy+cut/4:.1f}L{ring_x+ring_t:.1f} {cy+cut/2:.1f}Z" class="component"/>')
        pair_label = ("W2 umgedreht · Polung umkehren" if
                      bundle.project.enclosure.enclosure_type == "compound_push_pull" else
                      "W2 · Isobarik")
        parts.append(f'<text x="{ring_x+ring_t+8:.1f}" y="{cy-cut/2-9:.1f}" '
                     f'class="id">{pair_label}</text>')
        parts.append(_dim(inner_x,ring_x,top_y+fh+67,f"Koppelrohr {_mm(k.length_m):.1f}"))
        parts.append(f'<text x="{section_x}" y="{top_y+fh+156:.1f}" class="small">'
                     f'Koppelkammer: innen Ø {_mm(k.inner_diameter_m):.1f}, außen Ø {_mm(k.outer_diameter_m):.1f}; '
                     f'Montagering {_mm(k.ring_thickness_m):.1f} mm</text>')
    if bundle.brace:
        for index, depth in enumerate(bundle.brace_depths_m):
            bx=inner_x+_mm(depth)*scale
            stripe = max(3,_mm(bundle.brace.border_m)*scale)
            parts.append(f'<rect x="{bx:.1f}" y="{inner_y:.1f}" width="{_mm(bundle.brace.thickness_m)*scale:.1f}" '
                         f'height="{min(stripe,inner_h/3):.1f}" class="brace"/>')
            parts.append(f'<rect x="{bx:.1f}" y="{inner_y+inner_h-min(stripe,inner_h/3):.1f}" '
                         f'width="{_mm(bundle.brace.thickness_m)*scale:.1f}" '
                         f'height="{min(stripe,inner_h/3):.1f}" class="brace"/>')
            parts.append(f'<text x="{bx+8:.1f}" y="{inner_y+27:.1f}" class="small">B{index+1}</text>')
    parts.append(_dim(section_x,section_x+fd,top_y+fh+35,f"T {d:.1f}"))
    parts.append(_dim(inner_x,rear_x,top_y+fh+101,
                      f"Innen {_mm(cab.internal_depth_m):.1f}"))
    parts.append(f'<text x="{section_x}" y="{top_y+fh+135:.1f}" class="note">'
                 f'Front {cab.effective_front_thickness_m*1000:.1f} · Rückwand '
                 f'{cab.effective_back_thickness_m*1000:.1f} · Deckel {tt/scale:.1f} · '
                 f'Boden {bot/scale:.1f} mm</text>')
    # A small rear elevation makes back-mounted passive radiators visible.
    if any(e.surface == "back" for e in bundle.front_elements):
        back_scale = min(190/w,200/h)
        bx,by = 65.0,775.0
        parts += [f'<text x="{bx}" y="{by-17}" class="label">Rückwand</text>',
                  f'<rect x="{bx}" y="{by}" width="{w*back_scale:.1f}" '
                  f'height="{h*back_scale:.1f}" class="outline"/>']
        for element in bundle.front_elements:
            if element.surface == "back":
                parts.append(_element_front(element,bx,by,h*back_scale,back_scale))
    note_x = 520.0
    note_y = 870.0
    parts += [f'<text x="{note_x}" y="{note_y}" class="label">Bauteile und Prüfung</text>',
              f'<text x="{note_x}" y="{note_y+27}" class="note">'
              f'{len(bundle.front_elements)} Einbauteile · '
              f'{bundle.brace.quantity if bundle.brace else 0} Fensterstreben · '
              f'{len(bundle.warnings)} Hinweise</text>']
    if bundle.port:
        parts.append(f'<text x="{note_x}" y="{note_y+52}" class="note">Port: '
                     f'{bundle.port.shape}, {_mm(bundle.port.physical_length_m):.1f} mm lang, '
                     f'{bundle.port.area_m2*10000:.1f} cm²</text>')
    if bundle.port_resistance_pa_s_m3 is not None:
        parts.append(f'<text x="{note_x}" y="{note_y+77}" class="note">'
                     f'BR1 Vent: Dämmwiderstand Soll '
                     f'{bundle.port_resistance_pa_s_m3:.0f} Pa·s/m³; am Prototyp messen</text>')
    if bundle.folded_line is not None:
        line = bundle.folded_line
        parts.append(f'<text x="{note_x}" y="{note_y+105}" class="note">'
                     f'Linienweg {line.path_length_m*1000:.1f} mm · '
                     f'{line.fold_count} Faltungen · Umlenkspalt max. {line.turn_gap_m*1000:.1f} mm</text>')
    if bundle.rear_port:
        parts.append(f'<text x="{note_x}" y="{note_y+77}" class="note">BR2 Rückkammer: '
                     f'Ø {_mm(bundle.rear_port.diameter_m or 0):.1f}, '
                     f'L {_mm(bundle.rear_port.physical_length_m):.1f}, '
                     f'Fb {bundle.rear_port.tuning_hz:.1f} Hz</text>')
    if bundle.radiator:
        parts.append(f'<text x="{note_x}" y="{note_y+52}" class="note">Passivmembran: '
                     f'{bundle.radiator.added_mass_kg*1000:.1f} g Zusatzmasse</text>')
    if bundle.warnings:
        y = note_y+(135 if bundle.folded_line is not None else
                    105 if bundle.rear_port or bundle.port_resistance_pa_s_m3 is not None else 78)
        headline = next((i.message for i in bundle.issues if i.severity != "info"), bundle.warnings[0])
        for index, text in enumerate(wrap(headline, width=64)[:2]):
            parts.append(f'<text x="{note_x}" y="{y+index*19}" class="warning">'
                         f'{escape(text)}</text>')
    parts.append('</svg>')
    return ''.join(parts)
