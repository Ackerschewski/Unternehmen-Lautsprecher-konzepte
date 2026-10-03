"""Manufacturing sheet for a two-run horn with the driver in F1."""
# ruff: noqa: ISC004
from __future__ import annotations

from html import escape
from math import cos, pi, sin

from lautsprecher_konstruktion.services.design import DesignBundle


def render_tapped_horn_svg(bundle: DesignBundle) -> str:
    horn=bundle.tapped_horn
    if horn is None:
        raise ValueError('Kein Tapped-Horn')
    cab=bundle.cabinet
    driver=bundle.project.driver
    w,h,d=[v*1000 for v in (cab.width_m,cab.height_m,cab.depth_m)]
    t=cab.panel_thickness_m*1000
    inside_w=cab.internal_width_m*1000
    baffle_len=horn.baffle_length_m*1000
    cut=(driver.cutout_diameter_m or 0)*1000
    outer=(driver.outer_diameter_m or 0)*1000
    bolt=(driver.bolt_circle_diameter_m or 0)*1000
    hole=(driver.bolt_hole_diameter_m or 0)*1000
    scale=min(480/h,420/d,380/w)
    fx,fy=70,160
    sx,sy=550,160
    px,py=1050,160
    iy=sy+(cab.top_thickness_m or cab.panel_thickness_m)*1000*scale
    f1y=iy+horn.upper_height_m*1000*scale
    front=sx+cab.effective_front_thickness_m*1000*scale
    back=sx+(d-(cab.back_thickness_m or cab.panel_thickness_m)*1000)*scale
    cx=front+horn.driver_depth_from_front_m*1000*scale
    driver_radius=outer*scale/2
    parts=[
        '<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1250" viewBox="0 0 1600 1250">',
        '<style>.title{font:700 30px Arial;fill:#153346}.head{font:700 20px Arial;fill:#153346}'
        '.text{font:16px Arial;fill:#27485b}.small{font:14px Arial;fill:#50697a}'
        '.panel{fill:#dce8ed;stroke:#264c60;stroke-width:2}.cut{fill:#f2fbfd;stroke:#067ba0;stroke-width:2}'
        '.dim{stroke:#526f80;stroke-width:1.5;fill:none}.rule{stroke:#a8c0ca;stroke-width:1}'
        '</style><rect width="1600" height="1250" fill="white"/>',
        f'<text x="50" y="50" class="title">{escape(bundle.project.name)} · Tapped-Horn-Fertigung</text>',
        f'<text x="50" y="80" class="text">{escape(bundle.project.revision)} · Maße in mm · '
        'W1 horizontal in F1, Magnet im oberen Kanal, Membran zum unteren Kanal</text>',
        '<text x="70" y="130" class="head">Vorderansicht</text>',
        f'<rect x="{fx}" y="{fy}" width="{w*scale:.1f}" height="{h*scale:.1f}" class="panel"/>',
        f'<rect x="{fx+(w-horn.mouth_width_m*1000)*scale/2:.1f}" '
        f'y="{fy+(cab.top_thickness_m or cab.panel_thickness_m)*1000*scale+(horn.upper_height_m*1000+t+10)*scale:.1f}" '
        f'width="{horn.mouth_width_m*1000*scale:.1f}" '
        f'height="{horn.mouth_height_m*1000*scale:.1f}" class="cut"/>',
        f'<text x="{fx}" y="{fy+h*scale+27:.1f}" class="text">B {w:.1f} · H {h:.1f}</text>',
        '<text x="550" y="130" class="head">Seitenschnitt · obere und untere Hornstrecke</text>',
        f'<rect x="{sx}" y="{sy}" width="{d*scale:.1f}" height="{h*scale:.1f}" class="panel"/>',
        f'<rect x="{front:.1f}" y="{iy:.1f}" width="{(back-front):.1f}" '
        f'height="{cab.internal_height_m*1000*scale:.1f}" fill="white"/>',
        f'<rect x="{front:.1f}" y="{f1y:.1f}" width="{baffle_len*scale:.1f}" '
        f'height="{t*scale:.1f}" class="panel"/>',
        f'<rect x="{cx-cut*scale/2:.1f}" y="{f1y-2:.1f}" '
        f'width="{cut*scale:.1f}" height="{t*scale+4:.1f}" fill="white"/>',
        f'<rect x="{cx-driver_radius:.1f}" y="{f1y-(driver.mounting_depth_m or 0)*1000*scale:.1f}" '
        f'width="{outer*scale:.1f}" height="{(driver.mounting_depth_m or 0)*1000*scale:.1f}" class="cut"/>',
        f'<path d="M{front+20:.1f} {f1y-18:.1f}H{back-15:.1f}v{(horn.upper_height_m+horn.lower_height_m)*500*scale:.1f}'
        f'H{front+20:.1f}" class="dim"/>',
        f'<text x="{front+7:.1f}" y="{f1y-30:.1f}" class="small">oberer Lauf →</text>',
        f'<text x="{front+7:.1f}" y="{f1y+t*scale+38:.1f}" class="small">← unterer Lauf</text>',
        f'<text x="{sx}" y="{sy+h*scale+27:.1f}" class="text">T {d:.1f} · F1 Länge {baffle_len:.1f} · '
        f'Umlenkspalt {horn.turn_gap_m*1000:.1f}</text>',
        '<text x="1050" y="130" class="head">F1 Draufsicht · Ursprung vorne links</text>',
        f'<rect x="{px}" y="{py}" width="{inside_w*scale:.1f}" '
        f'height="{baffle_len*scale:.1f}" class="panel"/>',
        f'<circle cx="{px+inside_w*scale/2:.1f}" '
        f'cy="{py+baffle_len*scale/2:.1f}" r="{cut*scale/2:.1f}" class="cut"/>',
        f'<circle cx="{px+inside_w*scale/2:.1f}" '
        f'cy="{py+baffle_len*scale/2:.1f}" r="{outer*scale/2:.1f}" class="dim"/>',
        f'<text x="{px}" y="{py+baffle_len*scale+27:.1f}" class="text">F1 '
        f'{inside_w:.1f} × {baffle_len:.1f} × {t:.1f}</text>',
        '<path d="M50 760H1550" class="rule"/>',
        '<text x="55" y="800" class="head">Fertigung / Bohrbild / Akustik</text>',
        f'<text x="55" y="840" class="text">W1 in F1: X {inside_w/2:.1f}, '
        f'Y {baffle_len/2:.1f} · Ausschnitt Ø {cut:.1f} · Flansch Ø {outer:.1f}</text>',
        f'<text x="55" y="875" class="text">Lochkreis Ø {bolt:.1f} · '
        f'{driver.bolt_count or 0} Bohrungen Ø {hole:.1f}; fehlende Herstellermaße am Treiber prüfen</text>',
        f'<text x="55" y="910" class="text">Kanalhöhen: oben {horn.upper_height_m*1000:.1f}, '
        f'unten {horn.lower_height_m*1000:.1f} · Weg {horn.path_length_m*1000:.1f} · '
        f'¼λ {horn.quarter_wave_hz:.1f} Hz</text>',
        f'<text x="55" y="945" class="text">Mündung BR1: '
        f'{horn.mouth_width_m*1000:.1f} × {horn.mouth_height_m*1000:.1f} '
        f'· Mittelpunkt X {bundle.front_elements[0].x_m*1000:.1f}, '
        f'Y {bundle.front_elements[0].y_m*1000:.1f}</text>',
    ]
    if driver.bolt_count and bolt and hole:
        for i in range(driver.bolt_count):
            angle=2*pi*i/driver.bolt_count
            hx=inside_w/2+bolt*cos(angle)/2
            hy=baffle_len/2+bolt*sin(angle)/2
            parts.append(f'<circle cx="{px+hx*scale:.1f}" cy="{py+hy*scale:.1f}" '
                         f'r="{max(2,hole*scale/2):.1f}" fill="white" stroke="#ba593b"/>')
            parts.append(f'<text x="{55+(i%4)*375}" y="{990+(i//4)*23}" class="small">'
                         f'Bohrung {i+1}: X {hx:.1f} Y {hy:.1f}</text>')
    parts.append('</svg>')
    return ''.join(parts)
