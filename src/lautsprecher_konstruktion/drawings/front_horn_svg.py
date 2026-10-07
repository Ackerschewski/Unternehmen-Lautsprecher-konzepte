"""Dimensioned front horn: sectioned exponential contour, rear cabinet and trapezoid blanks."""
# ruff: noqa: ISC004
from __future__ import annotations

from html import escape
from textwrap import wrap

from lautsprecher_konstruktion.drawings.style import painted
from lautsprecher_konstruktion.enclosure.layout import bolt_holes
from lautsprecher_konstruktion.services.design import DesignBundle


@painted
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
    # horn border points from the mouth (x=mx) to the throat; heights per section border
    xs=[throat_x]
    for section in reversed(horn.section_lengths_m):
        xs.append(xs[-1]-section*1000*scale)
    heights=list(horn.section_heights_m)                # throat .. mouth
    upper=[(x,mid-hh*1000*scale/2) for x,hh in zip(xs,heights,strict=True)]
    lower=[(x,mid+hh*1000*scale/2) for x,hh in zip(xs,heights,strict=True)]
    outline=' '.join(f'{x:.1f},{y:.1f}' for x,y in upper+lower[::-1])
    parts=[
        '<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1330" viewBox="0 0 1600 1330">',
        '<style>.title{font-weight:700;font-size:31px;font-family:Arial;fill:%INK%}.head{font-weight:700;font-size:20px;font-family:Arial;fill:%INK%}'
        '.text{font-weight:400;font-size:16px;font-family:Arial;fill:%TEXT%}.small{font-weight:400;font-size:14px;font-family:Arial;fill:%MUTED%}'
        '.box{fill:%SURFACE%;stroke:%TEXT%;stroke-width:2}.horn{fill:%SURFACE%;stroke:%ACCENT%;stroke-width:2}'
        '.cut{fill:none;stroke:%ACCENT%;stroke-width:2}.rule{stroke:%RULE%;stroke-width:1}'
        '.tick{stroke:%ACCENT%;stroke-width:1;stroke-dasharray:4 3}'
        '</style><rect width="1600" height="1330" fill="white"/>',
        f'<text x="55" y="49" class="title">{escape(bundle.project.name)} · Front-Horn-Fertigung</text>',
        f'<text x="55" y="80" class="text">{escape(bundle.project.revision)} · alle Maße in mm · '
        f'Horn vor der Frontplatte, Rückkammer geschlossen · {len(horn.section_lengths_m)} Abschnitte</text>',
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
        f'<polygon points="{outline}" class="horn"/>',
    ]
    for (ux,uy),(lx,ly) in zip(upper,lower,strict=True):
        parts.append(f'<path d="M{ux:.1f} {uy:.1f}V{ly:.1f}" class="tick"/>')
    # driver on the throat, rear side towards the closed cabinet
    driver=bundle.project.driver
    dia=(driver.outer_diameter_m or driver.cutout_diameter_m or 0)*1000*scale
    depth=(driver.mounting_depth_m or 0)*1000*scale
    if dia:
        parts.append(f'<path d="M{throat_x:.1f} {mid-dia/2:.1f}L{throat_x+depth:.1f} {mid-dia/4:.1f}'
                     f'L{throat_x+depth:.1f} {mid+dia/4:.1f}L{throat_x:.1f} {mid+dia/2:.1f}Z" class="cut"/>')
        parts.append(f'<text x="{throat_x+depth+6:.1f}" y="{mid+5:.1f}" class="small">W1</text>')
    parts += [
        f'<text x="{mx:.1f}" y="{upper[-1][1]-12:.1f}" class="text">Mundhöhe {mouth_h:.1f}</text>',
        f'<text x="{throat_x+7:.1f}" y="{upper[0][1]-12:.1f}" class="text">Hals {throat:.1f} × {throat:.1f}</text>',
        f'<text x="{(mx+throat_x)/2:.1f}" y="{sy+h*scale+30:.1f}" '
        f'text-anchor="middle" class="text">Horn axial {length:.1f}</text>',
        f'<text x="{(throat_x+back_x)/2:.1f}" y="{sy+h*scale+30:.1f}" '
        f'text-anchor="middle" class="text">Rückgehäuse {d:.1f}</text>',
        '<path d="M55 700H1545" class="rule"/>',
        '<text x="60" y="737" class="head">Horn-Trapezplatten / Zuschnitt</text>',
    ]
    ratio=horn.area_ratio
    summary=(f'Hals {horn.throat_area_m2*1e4:.0f} cm² · Mündung {horn.mouth_area_m2*1e4:.0f} cm² · '
             f'Flächenverhältnis {ratio:.2f} · Flare m {horn.flare_per_m:.2f} 1/m · '
             f'Soll-Grenzfrequenz {horn.target_cutoff_hz:.1f} Hz (fc = m·c/4π = {horn.cutoff_hz:.1f} Hz) · '
             f'Länge L = c·ln(S_M/S_T)/(4π·fc)')
    parts.append(f'<text x="60" y="768" class="text">{escape(summary)}</text>')
    row=796
    for i,(a,b,c_,dd,length_i) in enumerate(zip(horn.section_widths_m,horn.section_widths_m[1:],
                                                horn.section_heights_m,horn.section_heights_m[1:],
                                                horn.section_lengths_m,strict=False)):
        top=horn.panels[2*i]
        side=horn.panels[2*i+1]
        text=(f'Abschnitt {i+1} (axial {length_i*1000:.1f}): 2 × oben/unten Breite {a*1000:.1f}→{b*1000:.1f}, '
              f'Schräge {top.height_m*1000:.1f} · 2 × seitlich Höhe {c_*1000:.1f}→{dd*1000:.1f}, '
              f'Schräge {side.height_m*1000:.1f} · Stärke {cab.panel_thickness_m*1000:.1f}')
        parts.append(f'<text x="60" y="{row+i*24}" class="text">{escape(text)}</text>')
    row+=len(horn.section_lengths_m)*24+8
    limits=(f'Grenzen: jeder Abschnitt ist ein Pyramidenstumpf aus ebenen Brettern; die gebaute Fläche weicht '
            f'zwischen den Abschnittsgrenzen bis {horn.max_area_deviation()*100:.1f} % vom Exponentialgesetz ab '
            f'(Berechnung nutzt die gebaute Fläche). Hals/Membranfläche = {horn.decompression:.2f}: '
            'der Hals ist durch den Treiberrahmen vorgegeben, es gibt keine Kompressionskammer. '
            'Gehrungen am realen Plattenstoß prüfen; Rohmaße sind Rechteck-Rohlinge.')
    for i,line in enumerate(wrap(limits,170)):
        parts.append(f'<text x="60" y="{row+i*20}" class="small">{escape(line)}</text>')
    row+=len(wrap(limits,170))*20+14
    parts.append(f'<path d="M55 {row}H1545" class="rule"/>')
    parts.append(f'<text x="60" y="{row+35}" class="head">Treiber und Lochbild hinter dem Hornhals</text>')
    base=row+66
    for index,e in enumerate(bundle.front_elements):
        yy=base+index*28
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
