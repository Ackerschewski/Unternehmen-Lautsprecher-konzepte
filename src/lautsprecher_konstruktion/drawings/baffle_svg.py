"""Manufacturing sheet for wall, flat and U-frame baffles (no fictitious box)."""
# ruff: noqa: ISC004
from __future__ import annotations

from html import escape

from lautsprecher_konstruktion.enclosure.layout import bolt_holes
from lautsprecher_konstruktion.services.design import DesignBundle
from lautsprecher_konstruktion.drawings.style import PAPER, special_css


def render_baffle_svg(bundle: DesignBundle) -> str:
    mode = bundle.baffle_mode
    if mode not in {"infinite_baffle","open_baffle","dipole"}:
        raise ValueError("Keine Schallwandkonstruktion")
    c = bundle.cabinet
    w,h,t = c.width_m*1000,c.height_m*1000,c.panel_thickness_m*1000
    wing = bundle.baffle_wing_depth_m*1000
    scale = min(430/w,520/h)
    x,y = 95,145
    fw,fh = w*scale,h*scale
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1500" height="1040" viewBox="0 0 1500 1040">',
        special_css(),
        f'<rect width="1500" height="1040" fill="{PAPER}"/>',
        f'<text x="60" y="50" class="title">{escape(bundle.project.name)} · Schallwand-Fertigungsblatt</text>',
        f'<text x="60" y="81" class="text">{escape(bundle.project.revision)} · '
        f'{escape(mode)} · alle Maße in mm · X/Y ab linker unterer Ecke</text>',
        '<text x="95" y="124" class="head">Vorderansicht / Ausschnitte</text>',
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{fw:.1f}" height="{fh:.1f}" class="wall"/>',
    ]
    for e in bundle.front_elements:
        cx=x+e.x_m*1000*scale
        cy=y+(h-e.y_m*1000)*scale
        if e.outer_diameter_m is not None:
            lines.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" '
                         f'r="{e.outer_diameter_m*500*scale:.1f}" class="flange"/>')
            lines.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" '
                         f'r="{(e.cutout_diameter_m or e.outer_diameter_m)*500*scale:.1f}" class="cut"/>')
        else:
            ew,eh=e.width*1000*scale,e.height*1000*scale
            lines.append(f'<rect x="{cx-ew/2:.1f}" y="{cy-eh/2:.1f}" '
                         f'width="{ew:.1f}" height="{eh:.1f}" class="cut"/>')
        for hx,hy,radius in bolt_holes(e):
            lines.append(f'<circle cx="{x+hx*1000*scale:.1f}" '
                         f'cy="{y+(h-hy*1000)*scale:.1f}" '
                         f'r="{max(2,radius*1000*scale):.1f}" class="hole"/>')
        lines.append(f'<text x="{cx+6:.1f}" y="{cy-8:.1f}" class="small">{escape(e.id)}</text>')
    lines.extend((
        f'<text x="{x+fw/2:.1f}" y="{y+fh+31:.1f}" text-anchor="middle" class="text">Breite {w:.1f}</text>',
        f'<text x="{x-25:.1f}" y="{y+fh/2:.1f}" class="text" '
        f'transform="rotate(-90 {x-25:.1f} {y+fh/2:.1f})" text-anchor="middle">Höhe {h:.1f}</text>',
        '<text x="675" y="124" class="head">Draufsicht / Bauform</text>',
    ))
    px,py = 720.0,215.0
    pt = max(9.0,t*scale)
    woofer = next((e for e in bundle.front_elements if e.id == "W1"),None)
    driver_depth = (woofer.mounting_depth_m*1000 if woofer else 0.0)
    plan_scale = min(430/w, 270/max(wing+t,driver_depth+t,1.0))
    plan_w = w*plan_scale
    pt = max(9.0,t*plan_scale)

    if mode == "infinite_baffle":
        # Schematic only: the room behind the wall is not part of the cut list and not to scale.
        lines.append(f'<rect x="{px-60:.1f}" y="{py:.1f}" width="60" height="{pt:.1f}" class="wallhatch"/>')
        lines.append(f'<rect x="{px+plan_w:.1f}" y="{py:.1f}" width="60" height="{pt:.1f}" class="wallhatch"/>')
        rear_h = max(120.0,driver_depth*plan_scale+30)
        lines.append(f'<rect x="{px-60:.1f}" y="{py+pt:.1f}" width="{plan_w+120:.1f}" height="{rear_h:.1f}" class="air"/>')
        lines.append(f'<text x="{px+plan_w/2:.1f}" y="{py+pt+rear_h+22:.1f}" text-anchor="middle" class="text">'
                     f'Rückraum ≥ {bundle.target_net_volume_m3*1000:.0f} l, luftdicht (schematisch, nicht maßstäblich)</text>')
        lines.append(f'<text x="{px+plan_w/2:.1f}" y="{py+pt+rear_h+44:.1f}" text-anchor="middle" class="small">'
                     '≥ 10 × Vas (Small): Qtc steigt höchstens um 5 %</text>')
    lines.append(f'<rect x="{px:.1f}" y="{py:.1f}" width="{plan_w:.1f}" height="{pt:.1f}" class="wall"/>')
    plan_bottom = py+pt
    if woofer is not None:
        cxp = px+woofer.x_m*1000*plan_scale
        cut_w = (woofer.cutout_diameter_m or woofer.outer_diameter_m or 0)*1000*plan_scale
        dd = driver_depth*plan_scale
        lines.append(f'<rect x="{cxp-cut_w/2:.1f}" y="{py-1:.1f}" width="{cut_w:.1f}" height="{pt+2:.1f}" fill="white" stroke="none"/>')
        lines.append(f'<path d="M{cxp-cut_w/2:.1f} {py+pt:.1f}L{cxp-cut_w/4:.1f} {py+pt+dd:.1f}H{cxp+cut_w/4:.1f}L{cxp+cut_w/2:.1f} {py+pt:.1f}Z" class="part"/>')
        lines.append(f'<text x="{cxp:.1f}" y="{py+pt+dd/2+4:.1f}" text-anchor="middle" class="small">W1 · Tiefe {driver_depth:.0f}</text>')
        plan_bottom = max(plan_bottom,py+pt+dd)
    if mode == "dipole":
        length = wing*plan_scale
        for xx in (px,px+plan_w-pt):
            lines.append(f'<rect x="{xx:.1f}" y="{py+pt:.1f}" width="{pt:.1f}" height="{length:.1f}" class="wall"/>')
        plan_bottom = max(plan_bottom,py+pt+length)
        lines.append(f'<path d="M{px+plan_w+14:.1f} {py+pt:.1f}v{length:.1f}M{px+plan_w+8:.1f} {py+pt:.1f}h12M{px+plan_w+8:.1f} {py+pt+length:.1f}h12" class="dimline"/>')
        lines.append(f'<text x="{px+plan_w+22:.1f}" y="{py+pt+length/2:.1f}" class="small">Flügel {wing:.0f}</text>')
    if mode != "infinite_baffle" and woofer is not None:
        # Shortest side path: front surface to the nearest edge, around the wing/edge, back to the rear.
        near_left = woofer.x_m <= bundle.cabinet.width_m/2
        edge_x = px-7 if near_left else px+plan_w+7  # runs along the outside of the edge / wing
        length = wing*plan_scale
        cxp = px+woofer.x_m*1000*plan_scale
        y_back = py+pt+length+10
        lines.append(f'<path d="M{cxp:.1f} {py-10:.1f}H{edge_x:.1f}V{y_back:.1f}H{cxp:.1f}" class="path"/>')
        plan_bottom = max(plan_bottom,py+pt+length+14)
    lines.append(f'<path d="M{px:.1f} {py-26:.1f}H{px+plan_w:.1f}M{px:.1f} {py-32:.1f}v12M{px+plan_w:.1f} {py-32:.1f}v12" class="dimline"/>')
    lines.append(f'<text x="{px+plan_w/2:.1f}" y="{py-34:.1f}" text-anchor="middle" class="small">Breite {w:.0f} · Platte {t:.0f}</text>')
    if mode == "dipole":
        lines.append(f'<text x="{px:.1f}" y="{plan_bottom+28:.1f}" class="text">'
                     f'2 × Seitenflügel, Tiefe ab Schallwandrückseite {wing:.1f}</text>')
        lines.append(f'<text x="{px:.1f}" y="{plan_bottom+52:.1f}" class="small">'
                     'Seitenflügel stumpf/leimfest ansetzen; nach hinten offen.</text>')
        plan_bottom += 52
    elif mode == "infinite_baffle":
        plan_bottom = py+pt+max(120.0,driver_depth*plan_scale+30)+44
        lines.append(f'<text x="{px-60:.1f}" y="{plan_bottom+24:.1f}" class="small">'
                     'Wand und Rückraum gehören zur Installation, nicht zum Zuschnitt.</text>')
        plan_bottom += 24
    else:
        lines.append(f'<text x="{px:.1f}" y="{plan_bottom+28:.1f}" class="text">'
                     'Freistehende flache Schallwand; Vorder- und Rückseite offen.</text>')
        plan_bottom += 28
    head_y = max(445.0,plan_bottom+48)
    lines.append(f'<text x="675" y="{head_y:.1f}" class="head">Akustisch wirksamer Umweg</text>')
    if bundle.baffle_path_m is None:
        lines.append(f'<text x="675" y="{head_y+30:.1f}" class="text">Entfällt: Wand trennt Vorder- und Rückseite (2π-Abstrahlung).</text>')
    else:
        c_s = 343.0
        path_m = bundle.baffle_path_m
        lines.append(f'<text x="675" y="{head_y+30:.1f}" class="text">'
                     f'Front → Rückseite: {path_m*1000:.1f} mm (kürzester Weg um die Kante, Näherung)</text>')
        lines.append(f'<text x="675" y="{head_y+56:.1f}" class="small">'
                     f'Dipol: −3 dB bei c/(4·D) = {c_s/(4*path_m):.0f} Hz · Maximum {c_s/(2*path_m):.0f} Hz · '
                     f'erste Auslöschung {c_s/path_m:.0f} Hz</text>')
        lines.append(f'<text x="675" y="{head_y+80:.1f}" class="small">'
                     'Darunter 6 dB/Okt Abfall: Entzerrung (Linkwitz-Transformation/DSP) nötig.</text>')
    lines.append('<text x="60" y="760" class="head">Einbaukoordinaten und Ausschnitte</text>')
    for index,e in enumerate(bundle.front_elements):
        yy=792+index*28
        cut=(f"Ø {e.cutout_diameter_m*1000:.1f}" if e.cutout_diameter_m else
             f"{e.width*1000:.1f} × {e.height*1000:.1f}")
        lines.append(f'<text x="65" y="{yy}" class="text">{escape(e.id)} · '
                     f'X {e.x_m*1000:.1f} · Y {e.y_m*1000:.1f} · Ausschnitt {cut} · '
                     f'Tiefe {e.mounting_depth_m*1000:.1f}</text>')
        if e.bolt_count and e.bolt_circle_diameter_m and e.hole_diameter_m:
            lines.append(f'<text x="800" y="{yy}" class="small">'
                         f'{e.bolt_count} × Ø {e.hole_diameter_m*1000:.1f} '
                         f'auf LK Ø {e.bolt_circle_diameter_m*1000:.1f}</text>')
    row=805+len(bundle.front_elements)*28+30
    lines.append(f'<path d="M60 {row-28}H1440" class="rule"/>')
    lines.append(f'<text x="60" y="{row}" class="head">Zuschnitt</text>')
    for index,panel in enumerate(bundle.panels):
        yy=row+29+index*27
        lines.append(f'<text x="65" y="{yy}" class="text">{panel.quantity} × '
                     f'{escape(panel.name)} · {panel.width_m*1000:.1f} × '
                     f'{panel.height_m*1000:.1f} × {panel.thickness_m*1000:.1f} mm</text>')
    lines.append('<text x="60" y="1008" class="small">Treibermaße und Bohrbild am Original prüfen. '
                 'Freistehende Schallwand standsicher befestigen; rückseitigen Bauraum prüfen.</text>')
    lines.append('</svg>')
    return ''.join(lines)
