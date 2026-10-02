"""Multi-view manufacturing sheet with explicit dimensions and drill coordinates."""
# ruff: noqa: ISC004
from __future__ import annotations

from html import escape

from lautsprecher_konstruktion.enclosure.layout import bolt_holes
from lautsprecher_konstruktion.services.design import DesignBundle


def _text(x: float, y: float, value: str, css: str = "text") -> str:
    return f'<text x="{x:.1f}" y="{y:.1f}" class="{css}">{escape(value)}</text>'


def _line(x1: float, y1: float, x2: float, y2: float, css: str = "dim") -> str:
    return f'<path d="M{x1:.1f} {y1:.1f}L{x2:.1f} {y2:.1f}" class="{css}"/>'


def _horizontal_dim(x: float, y: float, length: float, caption: str) -> str:
    return (_line(x, y, x+length, y)+_line(x, y-7, x, y+7)+
            _line(x+length, y-7, x+length, y+7)+
            f'<text x="{x+length/2:.1f}" y="{y-10:.1f}" text-anchor="middle" '
            f'class="dimlabel">{escape(caption)}</text>')


def _vertical_dim(x: float, y: float, length: float, caption: str) -> str:
    return (_line(x, y, x, y+length)+_line(x-7, y, x+7, y)+
            _line(x-7, y+length, x+7, y+length)+
            f'<text x="{x-10:.1f}" y="{y+length/2:.1f}" text-anchor="middle" '
            f'transform="rotate(-90 {x-10:.1f} {y+length/2:.1f})" '
            f'class="dimlabel">{escape(caption)}</text>')


def _face(bundle: DesignBundle, surface: str, x: float, y: float,
          scale: float, w_mm: float, h_mm: float) -> str:
    shapes = [f'<rect x="{x:.1f}" y="{y:.1f}" width="{w_mm*scale:.1f}" '
              f'height="{h_mm*scale:.1f}" class="outline"/>']
    for element in bundle.front_elements:
        if element.surface != surface:
            continue
        cx = x + element.x_m*1000*scale
        cy = y + (h_mm-element.y_m*1000)*scale
        if element.outer_diameter_m:
            shapes.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" '
                          f'r="{element.outer_diameter_m*500*scale:.1f}" class="flange"/>')
            shapes.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" '
                          f'r="{(element.cutout_diameter_m or element.outer_diameter_m)*500*scale:.1f}" '
                          'class="cut"/>')
        else:
            ew, eh = element.width*1000*scale, element.height*1000*scale
            shapes.append(f'<rect x="{cx-ew/2:.1f}" y="{cy-eh/2:.1f}" '
                          f'width="{ew:.1f}" height="{eh:.1f}" class="cut"/>')
        shapes.append(_line(x, cy, cx, cy, "axis"))
        shapes.append(_line(cx, cy, cx, y+h_mm*scale, "axis"))
        for hx, hy, radius in bolt_holes(element):
            hole_x = x+hx*1000*scale
            hole_y = y+(h_mm-hy*1000)*scale
            shapes.append(f'<circle cx="{hole_x:.1f}" cy="{hole_y:.1f}" '
                          f'r="{max(2, radius*1000*scale):.1f}" class="hole"/>')
        shapes.append(_text(cx+7, cy-8, element.id, "callout"))
    shapes.append(_horizontal_dim(x, y+h_mm*scale+38, w_mm*scale, f"B {w_mm:.1f}"))
    shapes.append(_vertical_dim(x-37, y, h_mm*scale, f"H {h_mm:.1f}"))
    return "".join(shapes)


def _section(bundle: DesignBundle, x: float, y: float, scale: float,
             d_mm: float, h_mm: float) -> str:
    cab = bundle.cabinet
    fw, bw = cab.effective_front_thickness_m*1000*scale, cab.effective_back_thickness_m*1000*scale
    top = (cab.top_thickness_m or cab.panel_thickness_m)*1000*scale
    bottom = (cab.bottom_thickness_m or cab.panel_thickness_m)*1000*scale
    width, height = d_mm*scale, h_mm*scale
    parts = [f'<rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" '
             f'height="{height:.1f}" class="outline"/>']
    for rx, ry, rw, rh in ((x,y,fw,height), (x+width-bw,y,bw,height),
                           (x+fw,y,width-fw-bw,top),
                           (x+fw,y+height-bottom,width-fw-bw,bottom)):
        parts.append(f'<rect x="{rx:.1f}" y="{ry:.1f}" width="{rw:.1f}" '
                     f'height="{rh:.1f}" class="material"/>')
    if bundle.partition_front_depth_m is not None:
        px = x+fw+bundle.partition_front_depth_m*1000*scale
        driver = next((e for e in bundle.front_elements if e.surface == "partition" and e.type != "port"), None)
        center_y = y+(h_mm-driver.y_m*1000)*scale if driver else y+height/2
        opening = (driver.cutout_diameter_m or driver.height)*1000*scale if driver else 0
        wall = cab.panel_thickness_m*1000*scale
        for segment_y, segment_h in ((y+top, center_y-opening/2-y-top),
                                     (center_y+opening/2, y+height-bottom-center_y-opening/2)):
            if segment_h > 0:
                parts.append(f'<rect x="{px:.1f}" y="{segment_y:.1f}" '
                             f'width="{wall:.1f}" height="{segment_h:.1f}" class="material"/>')
        if driver:
            depth = driver.mounting_depth_m*1000*scale
            parts.append(f'<path d="M{px:.1f} {center_y-opening/2:.1f}L{px+depth:.1f} '
                         f'{center_y-opening/4:.1f}L{px+depth:.1f} {center_y+opening/4:.1f}'
                         f'L{px:.1f} {center_y+opening/2:.1f}Z" class="component"/>')
            parts.append(_text(px+5,center_y-opening/2-8,driver.id,"callout"))
        parts.append(_horizontal_dim(x+fw, y+height+70,
            bundle.partition_front_depth_m*1000*scale,
            f"Frontkammer-T {bundle.partition_front_depth_m*1000:.1f}"))
    for index, depth in enumerate(bundle.brace_depths_m):
        bx = x+fw+depth*1000*scale
        border = bundle.brace.border_m*1000*scale if bundle.brace else 0
        for yy in (y+top,y+height-bottom-border):
            parts.append(f'<rect x="{bx:.1f}" y="{yy:.1f}" '
                         f'width="{cab.panel_thickness_m*1000*scale:.1f}" '
                         f'height="{border:.1f}" class="brace"/>')
        parts.append(_text(bx+5,y+top+22,f"B{index+1}","small"))
    for element in bundle.front_elements:
        if element.surface not in {"front", "back"}:
            continue
        if bundle.coupler and element.id == "W1":
            continue
        cy = y+(h_mm-element.y_m*1000)*scale
        radius = (element.cutout_diameter_m or element.height)*500*scale
        depth = element.mounting_depth_m*1000*scale
        start = x+fw if element.surface == "front" else x+width-bw
        end = start+depth if element.surface == "front" else start-depth
        if element.type == "port":
            parts.append(f'<rect x="{min(start,end):.1f}" y="{cy-radius:.1f}" '
                         f'width="{abs(end-start):.1f}" height="{2*radius:.1f}" '
                         'class="component"/>')
        else:
            parts.append(f'<path d="M{start:.1f} {cy-radius:.1f}L{end:.1f} '
                         f'{cy-radius*.55:.1f}L{end:.1f} {cy+radius*.55:.1f}'
                         f'L{start:.1f} {cy+radius:.1f}Z" class="component"/>')
        parts.append(_text(min(start,end)+5,cy-radius-8,element.id,"callout"))
    if bundle.coupler:
        k = bundle.coupler
        driver = next((e for e in bundle.front_elements if e.id == "W1"), None)
        cy = y+(h_mm-driver.y_m*1000)*scale if driver else y+height/2
        outer = k.outer_diameter_m*1000*scale
        inner = k.inner_diameter_m*1000*scale
        length = k.length_m*1000*scale
        wall = (outer-inner)/2
        front_x = x+fw
        for yy in (cy-outer/2,cy+inner/2):
            parts.append(f'<rect x="{front_x:.1f}" y="{yy:.1f}" width="{length:.1f}" '
                         f'height="{wall:.1f}" class="component"/>')
        ring_x = front_x+length
        ring_t = k.ring_thickness_m*1000*scale
        cut = k.driver_cutout_m*1000*scale
        for yy in (cy-outer/2,cy+cut/2):
            parts.append(f'<rect x="{ring_x:.1f}" y="{yy:.1f}" width="{ring_t:.1f}" '
                         f'height="{(outer-cut)/2:.1f}" class="component"/>')
        parts.append(_text(front_x+5,cy-outer/2-8,"K1 / W1 + W2","callout"))
    parts.append(_horizontal_dim(x, y+height+38, width, f"T {d_mm:.1f}"))
    parts.append(_horizontal_dim(x+fw, y+height+105, width-fw-bw,
                                 f"Innen-T {cab.internal_depth_m*1000:.1f}"))
    return "".join(parts)


def render_master_sheet_svg(bundle: DesignBundle) -> str:
    """All manufacturing references on one scalable drawing; missing data stays explicit."""
    cab = bundle.cabinet
    w, h, d = (value*1000 for value in (cab.width_m,cab.height_m,cab.depth_m))
    scale = min(390/w, 440/h, 470/d)
    faces = bundle.front_elements
    holes = [(e, index, hx, hy, radius) for e in faces
             for index, (hx,hy,radius) in enumerate(bolt_holes(e), start=1)]
    face_rows_y = 830
    hole_rows_y = face_rows_y+72+max(1,len(faces))*34+50
    panel_rows_y = hole_rows_y+64+max(1,len(holes))*27+50
    internals_y = panel_rows_y+64+len(bundle.panels)*29+62
    sheet_h = int(internals_y+220)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1800" height="{sheet_h}" '
             f'viewBox="0 0 1800 {sheet_h}">',
             '<style>.title{font:700 35px Arial;fill:#102c3e}.head{font:700 22px Arial;fill:#163b50}'
             '.text{font:17px Arial;fill:#1b394a}.small{font:15px Arial;fill:#405c6b}'
             '.callout{font:700 16px Arial;fill:#0f536f}.dimlabel{font:16px Arial;fill:#28495a}'
             '.outline{fill:#fff;stroke:#163549;stroke-width:2.4}'
             '.material{fill:#dce6e8;stroke:#254b5e;stroke-width:1.4}'
             '.brace{fill:#c6dccd;stroke:#2c6742;stroke-width:1.4;fill-opacity:.6}'
             '.component{fill:#dceef7;stroke:#0874a2;stroke-width:1.6}'
             '.flange{fill:none;stroke:#56869b;stroke-width:1.5;stroke-dasharray:6 4}'
             '.cut{fill:none;stroke:#087ea8;stroke-width:2}.hole{fill:#fff;stroke:#ad3c2c;stroke-width:2}'
             '.axis{stroke:#9eb3bf;stroke-width:1;stroke-dasharray:5 5}'
             '.dim{stroke:#526d7a;stroke-width:1.3}.rule{stroke:#c6d6dc;stroke-width:1}'
             '.box{fill:#eef3f5;stroke:#527081;stroke-width:1.5}</style>',
             f'<rect width="1800" height="{sheet_h}" fill="white"/>',
             _text(58,57,bundle.project.name,"title"),
             _text(60,88,f"Gesamt-Fertigungszeichnung · {bundle.project.revision} · Maße in mm · "
                   "Bezug je Fläche: linke untere Außenecke","text"),
             _line(55,104,1745,104,"rule"),
             _text(100,143,"Vorderansicht","head"),
             _text(690,143,"Seitenschnitt A–A / Innenaufbau","head"),
             _text(1320,143,"Rückansicht","head"),
             _face(bundle,"front",110,165,scale,w,h),
             _section(bundle,700,165,scale,d,h),
             _face(bundle,"back",1320,165,scale,w,h),
             _text(60,730,f"Außen {w:.1f} × {h:.1f} × {d:.1f} · Innen "
                   f"{cab.internal_width_m*1000:.1f} × {cab.internal_height_m*1000:.1f} × "
                   f"{cab.internal_depth_m*1000:.1f} · Platte {cab.panel_thickness_m*1000:.1f}","head"),
             _text(60,760,"Linien: Blau = Ausschnitt/Chassis, Rot = bekannte Bohrung, "
                   "gestrichelt = Flansch/Bezugsachse. Zeichnung nicht als Bohrschablone skalieren.","small"),
             _line(55,790,1745,790,"rule"),
             _text(60,face_rows_y,"Einbauteile und Fräsmaße","head"),
             _text(60,face_rows_y+30,"ID / Bauteil", "small"),
             _text(310,face_rows_y+30,"Fläche", "small"),
             _text(460,face_rows_y+30,"Mitte X / Y", "small"),
             _text(680,face_rows_y+30,"Ausschnitt", "small"),
             _text(950,face_rows_y+30,"Flansch / Einbautiefe", "small"),
             _text(1280,face_rows_y+30,"Lochkreis / Bohrung", "small")]
    for i,e in enumerate(faces):
        y = face_rows_y+67+i*34
        cut = (f"Ø {e.cutout_diameter_m*1000:.1f}" if e.cutout_diameter_m else
               f"{e.width*1000:.1f} × {e.height*1000:.1f}")
        flange = (f"Ø {e.outer_diameter_m*1000:.1f}" if e.outer_diameter_m else "rechteckig")
        drilling = (f"{e.bolt_count} × Ø {e.hole_diameter_m*1000:.1f} / LK Ø "
                    f"{e.bolt_circle_diameter_m*1000:.1f}"
                    if e.bolt_count and e.bolt_circle_diameter_m and e.hole_diameter_m else
                    f"{e.bolt_count} × / LK Ø {e.bolt_circle_diameter_m*1000:.1f}; Bohr-Ø fehlt"
                    if e.bolt_count and e.bolt_circle_diameter_m else "nicht veröffentlicht")
        parts += [_text(60,y,f"{e.id} · {e.type}"), _text(310,y,e.surface),
                  _text(460,y,f"{e.x_m*1000:.1f} / {e.y_m*1000:.1f}"),
                  _text(680,y,cut),
                  _text(950,y,f"{flange} / T {e.mounting_depth_m*1000:.1f}"),
                  _text(1280,y,drilling), _line(55,y+9,1745,y+9,"rule")]
    if not faces:
        parts.append(_text(60,face_rows_y+68,"Keine Einbauteile erfasst."))
    parts += [_text(60,hole_rows_y,"Einzelkoordinaten sämtlicher dokumentierter Bohrungen","head"),
              _text(60,hole_rows_y+29,"ID / Nr.","small"),
              _text(310,hole_rows_y+29,"Fläche", "small"),
              _text(460,hole_rows_y+29,"X [mm]", "small"),
              _text(680,hole_rows_y+29,"Y [mm]", "small"),
              _text(950,hole_rows_y+29,"Ø [mm]", "small")]
    for i,(e,index,hx,hy,radius) in enumerate(holes):
        y = hole_rows_y+57+i*27
        parts += [_text(60,y,f"{e.id}-{index}"),_text(310,y,e.surface),
                  _text(460,y,f"{hx*1000:.2f}"),_text(680,y,f"{hy*1000:.2f}"),
                  _text(950,y,f"{radius*2000:.1f}"),_line(55,y+7,1745,y+7,"rule")]
    if not holes:
        parts.append(_text(60,hole_rows_y+57,"Kein vollständiges Hersteller-Lochbild vorhanden; vor CNC-Bearbeitung messen."))
    parts += [_text(60,panel_rows_y,"Zuschnittliste · Rohmaße vor Fräsungen","head"),
              _text(60,panel_rows_y+30,"Bauteil", "small"),
              _text(550,panel_rows_y+30,"Anzahl", "small"),
              _text(680,panel_rows_y+30,"Länge × Breite × Dicke [mm]", "small"),
              _text(1260,panel_rows_y+30,"Material", "small")]
    for i,p in enumerate(bundle.panels):
        y=panel_rows_y+62+i*29
        parts += [_text(60,y,p.name),_text(550,y,str(p.quantity)),
                  _text(680,y,f"{p.width_m*1000:.1f} × {p.height_m*1000:.1f} × "
                        f"{p.thickness_m*1000:.1f}"),
                  _text(1260,y,bundle.project.material),_line(55,y+8,1745,y+8,"rule")]
    parts += [_text(60,internals_y,"Innenaufbau und Fertigungshinweise","head"),
              _text(60,internals_y+34,f"Netto {bundle.target_net_volume_m3*1000:.1f} l · "
                    f"Verdrängung {bundle.total_displacement_m3*1000:.1f} l · "
                    f"Streben-Tiefen: {', '.join(f'{v*1000:.1f}' for v in bundle.brace_depths_m) or 'keine'} mm")]
    if bundle.port:
        parts.append(_text(60,internals_y+64,
            f"BR1 {bundle.port.shape}: Querschnitt {bundle.port.area_m2*10000:.1f} cm², "
            f"physische Länge {bundle.port.physical_length_m*1000:.1f} mm"))
    if bundle.rear_port:
        parts.append(_text(850,internals_y+64,
            f"BR2 Rückwand: Ø {(bundle.rear_port.diameter_m or 0)*1000:.1f} mm, "
            f"Länge {bundle.rear_port.physical_length_m*1000:.1f} mm, "
            f"Fb2 {bundle.rear_port.tuning_hz:.1f} Hz"))
    if bundle.coupler:
        k=bundle.coupler
        parts.append(_text(60,internals_y+94,f"Isobarik: Rohr Ø innen {k.inner_diameter_m*1000:.1f}, "
            f"außen {k.outer_diameter_m*1000:.1f}, Länge {k.length_m*1000:.1f}; "
            f"Ringdicke {k.ring_thickness_m*1000:.1f} mm"))
    if bundle.partition_front_depth_m is not None:
        parts.append(_text(60,internals_y+124,
            f"Trennwand: Abstand ab Front-Innenfläche {bundle.partition_front_depth_m*1000:.1f} mm · "
            f"Frontkammer {(bundle.front_chamber_volume_m3 or 0)*1000:.1f} l · "
            f"Rückkammer {(bundle.rear_chamber_volume_m3 or 0)*1000:.1f} l"))
    block_y=sheet_h-75
    parts += [f'<rect x="55" y="{block_y}" width="1690" height="56" class="box"/>',
              _text(70,block_y+22,"LAUTSPRECHER KONSTRUKTION · GESAMT-FERTIGUNGSBLATT","head"),
              _text(70,block_y+44,"Bauteile vor Zuschnitt gegen Datenblatt und Originalteil prüfen. "
                    "Nicht veröffentlichte Lochbilder sind ausdrücklich offen.","small"),
              _text(1490,block_y+30,bundle.project.revision,"head"),"</svg>"]
    return "".join(parts)
