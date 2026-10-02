"""Readable multi-view construction drawing from the resolved cabinet geometry."""
# ruff: noqa: ISC004
from __future__ import annotations

from html import escape

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


def render_assembly_svg(bundle: DesignBundle) -> str:
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
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="1020" '
        'viewBox="0 0 1200 1020">',
        '<defs><pattern id="material" width="8" height="8" patternUnits="userSpaceOnUse" '
        'patternTransform="rotate(45)"><rect width="8" height="8" fill="#e1e9ed"/>'
        '<path d="M0 0V8" stroke="#a4b5bf" stroke-width="2"/></pattern></defs>',
        '<style>.title{font:700 27px sans-serif;fill:#122737}.subtitle{font:14px sans-serif;fill:#426071}'
        '.label{font:700 19px sans-serif;fill:#122737}.note{font:15px sans-serif;fill:#263c49}'
        '.small{font:13px sans-serif;fill:#426071}.panel{fill:url(#material);stroke:#1e3949;stroke-width:2}'
        '.outline{fill:#fff;stroke:#1e3949;stroke-width:2}.flange{fill:#f3f7f9;stroke:#215a77;stroke-width:2}'
        '.cutout{fill:none;stroke:#177ba5;stroke-width:2.2}.drill{fill:#fff;stroke:#b44b32;stroke-width:1.5}'
        '.id{font:700 13px sans-serif;fill:#163c52}.dimension{fill:none;stroke:#516877;stroke-width:1.2}'
        '.dimension-text{font:14px sans-serif;fill:#254253}.component{fill:#dceef7;stroke:#0875a6;stroke-width:2}'
        '.brace{fill:#d7e6dc;stroke:#3a7555;stroke-width:1.6}.warning{font:700 14px sans-serif;fill:#a12c20}'
        '</style>',
        '<rect width="1200" height="1020" fill="#fff"/>',
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
    partition_x = None
    if bundle.partition_front_depth_m is not None:
        partition_x = inner_x+_mm(bundle.partition_front_depth_m)*scale
        driver = next((e for e in bundle.front_elements if e.surface == "partition" and e.type != "port"),None)
        opening_y = top_y+fh-_mm(driver.y_m)*scale if driver else top_y+fh/2
        opening_h = _mm(driver.cutout_diameter_m or driver.height)*scale if driver else 0
        upper = max(0,opening_y-opening_h/2-inner_y)
        lower_y = opening_y+opening_h/2
        parts.append(f'<rect x="{partition_x:.1f}" y="{inner_y:.1f}" '
                     f'width="{_mm(cab.panel_thickness_m)*scale:.1f}" height="{upper:.1f}" class="panel"/>')
        parts.append(f'<rect x="{partition_x:.1f}" y="{lower_y:.1f}" '
                     f'width="{_mm(cab.panel_thickness_m)*scale:.1f}" '
                     f'height="{max(0,inner_y+inner_h-lower_y):.1f}" class="panel"/>')
        parts.append(f'<text x="{(inner_x+partition_x)/2:.1f}" y="{top_y+fh/2:.1f}" '
                     f'text-anchor="middle" class="small">Frontkammer {_mm(bundle.front_chamber_volume_m3 or 0):.1f} l</text>')
        parts.append(f'<text x="{(partition_x+rear_x)/2:.1f}" y="{top_y+fh/2:.1f}" '
                     f'text-anchor="middle" class="small">Rückkammer {_mm(bundle.rear_chamber_volume_m3 or 0):.1f} l</text>')
        parts.append(_dim(inner_x,partition_x,top_y+fh+67,
                          f"Frontkammer {_mm(bundle.partition_front_depth_m):.1f}"))
        parts.append(_dim(partition_x+_mm(cab.panel_thickness_m)*scale,rear_x,
                          top_y+fh+67,"Rückkammer"))
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
        cy = top_y+fh-_mm(element.y_m)*scale
        eh = _mm(element.cutout_diameter_m or element.height)*scale
        depth = _mm(element.mounting_depth_m)*scale
        if element.surface == "front":
            if element.type == "port":
                if bundle.port is not None and bundle.port.shape == "slot":
                    wall=_mm(cab.panel_thickness_m)*scale
                    parts.append(f'<rect x="{inner_x:.1f}" y="{cy-eh/2-wall:.1f}" '
                                 f'width="{depth:.1f}" height="{wall:.1f}" class="panel"/>')
                    parts.append(f'<rect x="{inner_x:.1f}" y="{cy+eh/2:.1f}" '
                                 f'width="{depth:.1f}" height="{wall:.1f}" class="panel"/>')
                parts.append(f'<rect x="{inner_x:.1f}" y="{cy-eh/2:.1f}" '
                             f'width="{depth:.1f}" height="{eh:.1f}" class="component"/>')
                parts.append(f'<text x="{inner_x+depth+8:.1f}" y="{cy+4:.1f}" '
                             f'class="id">{escape(element.id)} · L {element.mounting_depth_m*1000:.0f}</text>')
            else:
                parts.append(f'<path d="M{inner_x:.1f} {cy-eh/2:.1f} '
                             f'L{inner_x+depth:.1f} {cy-eh*.25:.1f} '
                             f'L{inner_x+depth:.1f} {cy+eh*.25:.1f} '
                             f'L{inner_x:.1f} {cy+eh/2:.1f} Z" class="component"/>')
                parts.append(f'<text x="{inner_x+depth+8:.1f}" y="{cy+4:.1f}" '
                             f'class="id">{escape(element.id)} · Tiefe {element.mounting_depth_m*1000:.0f}</text>')
        elif element.surface == "back":
            parts.append(f'<path d="M{rear_x:.1f} {cy-eh/2:.1f} '
                         f'L{rear_x-depth:.1f} {cy-eh*.25:.1f} '
                         f'L{rear_x-depth:.1f} {cy+eh*.25:.1f} '
                         f'L{rear_x:.1f} {cy+eh/2:.1f} Z" class="component"/>')
            parts.append(f'<text x="{rear_x-depth-5:.1f}" y="{cy-eh/2-9:.1f}" '
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
        depth = _mm(w1.mounting_depth_m)*scale
        cut = _mm(k.driver_cutout_m)*scale
        parts.append(f'<path d="M{ring_x+ring_t:.1f} {cy-cut/2:.1f}L{ring_x+ring_t+depth:.1f} {cy-cut/4:.1f}L{ring_x+ring_t+depth:.1f} {cy+cut/4:.1f}L{ring_x+ring_t:.1f} {cy+cut/2:.1f}Z" class="component"/>')
        parts.append(f'<text x="{ring_x+ring_t+8:.1f}" y="{cy-cut/2-9:.1f}" class="id">W2 · Isobarik</text>')
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
    if bundle.radiator:
        parts.append(f'<text x="{note_x}" y="{note_y+52}" class="note">Passivmembran: '
                     f'{bundle.radiator.added_mass_kg*1000:.1f} g Zusatzmasse</text>')
    if bundle.warnings:
        parts.append(f'<text x="{note_x}" y="{note_y+78}" class="warning">'
                     f'{escape(bundle.warnings[0][:105])}</text>')
    parts.append('</svg>')
    return ''.join(parts)
