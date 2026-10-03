"""Dimensioned front horn, rear cabinet and four trapezoid blanks."""
# ruff: noqa: ISC004
from __future__ import annotations

from html import escape

from lautsprecher_konstruktion.enclosure.layout import bolt_holes
from lautsprecher_konstruktion.services.design import DesignBundle


def render_front_horn_svg(bundle: DesignBundle) -> str:
    horn=bundle.front_horn
    if horn is None:
        raise ValueError("Kein Front-Horn")
    cab=bundle.cabinet
    w,h,d=[x*1000 for x in (cab.width_m,cab.height_m,cab.depth_m)]
    throat=horn.throat_width_m*1000
    mouth_w,mouth_h=horn.mouth_width_m*1000,horn.mouth_height_m*1000
    length=horn.axial_length_m*1000
    scale=min(420/h,440/(length+d),380/w)
    fx,fy=90.0,165.0
    sx,sy=795.0,165.0
    mid=sy+h*scale/2
    mx=sx
    throat_x=sx+length*scale
    back_x=throat_x+d*scale
    top_mouth=mid-mouth_h*scale/2
    top_throat=mid-throat*scale/2
    parts=[
        '<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1190" viewBox="0 0 1600 1190">',
        '<style>.title{font:700 31px Arial;fill:#173449}.head{font:700 20px Arial;fill:#173449}'
        '.text{font:16px Arial;fill:#244456}.small{font:14px Arial;fill:#496779}'
        '.box{fill:#e0e9ed;stroke:#24485d;stroke-width:2}.horn{fill:#eef7fa;stroke:#087aa2;stroke-width:2}'
        '.cut{fill:none;stroke:#087aa2;stroke-width:2}.rule{stroke:#aabfc9;stroke-width:1}'
        '</style><rect width="1600" height="1190" fill="white"/>',
        f'<text x="55" y="49" class="title">{escape(bundle.project.name)} · Front-Horn-Fertigung</text>',
        f'<text x="55" y="80" class="text">{escape(bundle.project.revision)} · alle Maße in mm · '
        f'Horn vor der Frontplatte, Rückkammer geschlossen</text>',
        '<text x="90" y="137" class="head">Mündungsansicht</text>',
        f'<rect x="{fx:.1f}" y="{fy:.1f}" width="{mouth_w*scale:.1f}" '
        f'height="{mouth_h*scale:.1f}" class="horn"/>',
        f'<rect x="{fx+(mouth_w-throat)*scale/2:.1f}" '
        f'y="{fy+(mouth_h-throat)*scale/2:.1f}" width="{throat*scale:.1f}" '
        f'height="{throat*scale:.1f}" class="cut"/>',
        f'<text x="{fx+mouth_w*scale/2:.1f}" y="{fy+mouth_h*scale+28:.1f}" '
        f'text-anchor="middle" class="text">Mündung {mouth_w:.1f} × {mouth_h:.1f}</text>',
        '<text x="795" y="137" class="head">Seitenschnitt · Horn und geschlossene Rückkammer</text>',
        f'<rect x="{throat_x:.1f}" y="{sy:.1f}" width="{d*scale:.1f}" '
        f'height="{h*scale:.1f}" class="box"/>',
        f'<path d="M{mx:.1f} {top_mouth:.1f}L{throat_x:.1f} {top_throat:.1f}'
        f'L{throat_x:.1f} {2*mid-top_throat:.1f}L{mx:.1f} {2*mid-top_mouth:.1f}Z" '
        f'class="horn"/>',
        f'<text x="{mx+10:.1f}" y="{top_mouth-12:.1f}" class="text">Mundhöhe {mouth_h:.1f}</text>',
        f'<text x="{throat_x+7:.1f}" y="{top_throat-12:.1f}" class="text">Hals {throat:.1f} × {throat:.1f}</text>',
        f'<text x="{(mx+throat_x)/2:.1f}" y="{sy+h*scale+30:.1f}" '
        f'text-anchor="middle" class="text">Horn axial {length:.1f}</text>',
        f'<text x="{(throat_x+back_x)/2:.1f}" y="{sy+h*scale+30:.1f}" '
        f'text-anchor="middle" class="text">Rückgehäuse {d:.1f}</text>',
        '<path d="M55 700H1545" class="rule"/>',
        '<text x="60" y="737" class="head">Horn-Trapezplatten / Zuschnitt</text>',
        f'<text x="60" y="770" class="text">2 × oben/unten: Halsbreite '
        f'{throat:.1f}, Mundbreite {mouth_w:.1f}, Schräge '
        f'{horn.panels[0].height_m*1000:.1f}, Stärke {cab.panel_thickness_m*1000:.1f}</text>',
        f'<text x="60" y="802" class="text">2 × seitlich: Halshöhe '
        f'{throat:.1f}, Mundhöhe {mouth_h:.1f}, Schräge '
        f'{horn.panels[1].height_m*1000:.1f}, Stärke {cab.panel_thickness_m*1000:.1f}</text>',
        f'<text x="60" y="834" class="text">Soll-Grenzfrequenz '
        f'{horn.target_cutoff_hz:.1f} Hz · Mund/Hals-Flächenverhältnis '
        f'{horn.mouth_area_m2/horn.throat_area_m2:.2f}</text>',
        '<text x="60" y="876" class="small">Trapezkanten und Gehrungen am realen Plattenstoß prüfen; '
        'Rohplattenmaße in der Stückliste sind Zuschnitt-Rohlinge.</text>',
        '<path d="M55 900H1545" class="rule"/>',
        '<text x="60" y="935" class="head">Treiber und Lochbild hinter dem Hornhals</text>',
    ]
    for index,e in enumerate(bundle.front_elements):
        yy=966+index*28
        holes=(f'{e.bolt_count} × Ø {e.hole_diameter_m*1000:.1f} / '
               f'LK Ø {e.bolt_circle_diameter_m*1000:.1f}'
               if e.bolt_count and e.hole_diameter_m and e.bolt_circle_diameter_m else
               'Lochbild am Original messen')
        parts.append(f'<text x="65" y="{yy}" class="text">{escape(e.id)} · '
                     f'X {e.x_m*1000:.1f} · Y {e.y_m*1000:.1f} · '
                     f'Ausschnitt Ø {(e.cutout_diameter_m or 0)*1000:.1f} · '
                     f'{escape(holes)}</text>')
        for hole_index,(hx,hy,radius) in enumerate(bolt_holes(e),start=1):
            parts.append(f'<text x="65" y="{yy+hole_index*21}" class="small">'
                         f'{escape(e.id)}-{hole_index}: X {hx*1000:.1f} Y {hy*1000:.1f} '
                         f'Ø {radius*2000:.1f}</text>')
    parts.append('</svg>')
    return ''.join(parts)
