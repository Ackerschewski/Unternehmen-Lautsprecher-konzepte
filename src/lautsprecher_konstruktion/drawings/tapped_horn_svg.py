"""Manufacturing sheet for a folded tapped horn: path, taps, area law, F1 and drill pattern."""
# ruff: noqa: ISC004
from __future__ import annotations

from html import escape
from math import cos, pi, sin
from textwrap import wrap

import numpy as np

from lautsprecher_konstruktion.services.design import DesignBundle


def _sep_y(sep, x: float) -> float:
    xs = [p[0] for p in sep.points_m]
    ys = [p[1] for p in sep.points_m]
    return float(np.interp(x, xs, ys))


def render_tapped_horn_svg(bundle: DesignBundle) -> str:
    horn=bundle.tapped_horn
    if horn is None or horn.details is None:
        raise ValueError('Kein Tapped-Horn')
    det=horn.details
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
    scale=min(520/h,330/d,300/w)
    fx,fy=70,160
    sx,sy=520,160
    px,py=1050,160
    top_t=(cab.top_thickness_m or cab.panel_thickness_m)*1000*scale
    iy=sy+top_t                                   # inner top
    front=sx+cab.effective_front_thickness_m*1000*scale
    back=sx+(d-(cab.back_thickness_m or cab.panel_thickness_m)*1000)*scale

    def X(x_m: float) -> float:
        return front+x_m*1000*scale

    def Y(y_m: float) -> float:
        return iy+y_m*1000*scale

    inner_h=cab.internal_height_m*1000*scale
    mouth_top=Y(cab.internal_height_m)-horn.mouth_height_m*1000*scale-10*scale
    parts=[
        '<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1330" viewBox="0 0 1600 1330">',
        '<style>.title{font:700 30px Arial;fill:#153346}.head{font:700 20px Arial;fill:#153346}'
        '.text{font:16px Arial;fill:#27485b}.small{font:14px Arial;fill:#50697a}.tiny{font:12px Arial;fill:#254a60}'
        '.panel{fill:#dce8ed;stroke:#264c60;stroke-width:2}.cut{fill:#f2fbfd;stroke:#067ba0;stroke-width:2}'
        '.dim{stroke:#526f80;stroke-width:1.5;fill:none}.rule{stroke:#a8c0ca;stroke-width:1}'
        '.chan{fill:#eef7fb}.mouth{fill:#d9efd9;stroke:#2f7d32;stroke-width:1.5}'
        '.path{fill:none;stroke:#16749a;stroke-width:1.6;stroke-dasharray:7 5}'
        '.law{fill:none;stroke:#16749a;stroke-width:2}.built{fill:none;stroke:#c05a1c;stroke-width:2}'
        '.axis{stroke:#6d8795;stroke-width:1;fill:none}.tap{fill:#c0392b;stroke:none}'
        '</style><rect width="1600" height="1330" fill="white"/>',
        f'<text x="50" y="50" class="title">{escape(bundle.project.name)} · Tapped-Horn-Fertigung</text>',
        f'<text x="50" y="80" class="text">{escape(bundle.project.revision)} · Maße in mm · '
        'W1 horizontal in F1, Magnet im oberen Kanal, Membran zum Lauf 2 · Front links</text>',
        '<text x="70" y="130" class="head">Vorderansicht</text>',
        f'<rect x="{fx}" y="{fy}" width="{w*scale:.1f}" height="{h*scale:.1f}" class="panel"/>',
        f'<rect x="{fx+(w-horn.mouth_width_m*1000)*scale/2:.1f}" '
        f'y="{fy+(h-(cab.bottom_thickness_m or cab.panel_thickness_m)*1000-10-horn.mouth_height_m*1000)*scale:.1f}" '
        f'width="{horn.mouth_width_m*1000*scale:.1f}" '
        f'height="{horn.mouth_height_m*1000*scale:.1f}" class="mouth"/>',
        f'<text x="{fx}" y="{fy+h*scale+27:.1f}" class="text">B {w:.1f} · H {h:.1f}</text>',
        '<text x="520" y="130" class="head">Seitenschnitt · Lauf 1 … Lauf '+str(len(det.runs))+'</text>',
        f'<rect x="{sx}" y="{sy}" width="{d*scale:.1f}" height="{h*scale:.1f}" class="panel"/>',
        f'<rect x="{front:.1f}" y="{iy:.1f}" width="{back-front:.1f}" height="{inner_h:.1f}" class="chan"/>',
        f'<rect x="{sx:.1f}" y="{mouth_top:.1f}" width="{cab.effective_front_thickness_m*1000*scale:.1f}" '
        f'height="{horn.mouth_height_m*1000*scale:.1f}" class="mouth"/>',
    ]
    for sep in det.septa:
        up=[(X(x),Y(y)) for x,y in sep.points_m]
        low=[(x,y+t*scale) for x,y in reversed(up)]
        parts.append('<polygon points="'+' '.join(f'{x:.1f},{y:.1f}' for x,y in up+low)+'" class="panel"/>')
        parts.append(f'<text x="{up[-1][0]+3:.1f}" y="{up[-1][1]-3:.1f}" class="tiny">F{sep.index}</text>')
    # driver in F1: cutout, magnet above (run 1), flange on top
    f1y=Y(det.septa[0].points_m[0][1])
    cx=X(horn.driver_depth_from_front_m)
    mount=(driver.mounting_depth_m or 0)*1000*scale
    parts.append(f'<rect x="{cx-cut*scale/2:.1f}" y="{f1y-2:.1f}" width="{cut*scale:.1f}" '
                 f'height="{t*scale+4:.1f}" fill="white"/>')
    parts.append(f'<rect x="{cx-outer*scale/2:.1f}" y="{f1y-mount:.1f}" width="{outer*scale:.1f}" '
                 f'height="{mount:.1f}" class="cut"/>')
    parts.append(f'<text x="{cx:.1f}" y="{f1y-mount/2:.1f}" text-anchor="middle" class="tiny">W1</text>')
    # centre line and taps
    pts=[]
    for run in det.runs:
        k=run.index
        top_y=(lambda x,k=k: _sep_y(det.septa[k-2],x)+cab.panel_thickness_m) if k>1 else (lambda x: 0.0)
        bot_y=(lambda x,k=k: _sep_y(det.septa[k-1],x)) if k<len(det.runs) else (lambda x: cab.internal_height_m)
        for xx in (run.x_start_m,run.x_end_m):
            pts.append((X(xx),Y((top_y(xx)+bot_y(xx))/2)))
        xm=(run.x_start_m+run.x_end_m)/2
        parts.append(f'<text x="{X(xm)-30:.1f}" y="{Y((top_y(xm)+bot_y(xm))/2)-3:.1f}" class="tiny">'
                     f'L{k} {run.h_start_m*1000:.0f}→{run.h_end_m*1000:.0f}</text>')
    parts.append('<polyline points="'+' '.join(f'{x:.1f},{y:.1f}' for x,y in pts)+'" class="path"/>')
    r1=det.runs[0]
    y_run1=Y((0.0+_sep_y(det.septa[0],horn.driver_depth_from_front_m))/2)
    parts.append(f'<circle cx="{cx:.1f}" cy="{y_run1:.1f}" r="4" class="tap"/>'
                 f'<text x="{cx+6:.1f}" y="{y_run1+14:.1f}" class="tiny">Tap hinten s={horn.rear_tap_s_m*1000:.0f}</text>')
    r2=det.runs[1]
    y_run2=Y((_sep_y(det.septa[0],horn.driver_depth_from_front_m)+cab.panel_thickness_m
              +_sep_y(det.septa[1],horn.driver_depth_from_front_m))/2)
    parts.append(f'<circle cx="{cx:.1f}" cy="{y_run2:.1f}" r="4" class="tap"/>'
                 f'<text x="{cx+6:.1f}" y="{y_run2+14:.1f}" class="tiny">Tap vorn s={horn.front_tap_s_m*1000:.0f}</text>')
    del r1,r2
    parts.append(f'<text x="{front+4:.1f}" y="{iy+12:.1f}" class="tiny">geschlossenes Ende (s=0)</text>')
    parts.append(f'<text x="{sx:.1f}" y="{sy+h*scale+20:.1f}" class="small">Mündung {horn.mouth_width_m*1000:.0f}×'
                 f'{horn.mouth_height_m*1000:.0f} vorn unten</text>')
    parts.append(f'<text x="{sx}" y="{sy+h*scale+43:.1f}" class="text">T {d:.1f} · F1 Länge {baffle_len:.1f} · '
                 f'Umlenkspalte {" / ".join(f"{g*1000:.0f}" for g in det.turn_gaps_m[1:])}</text>')
    # F1 plan
    parts+= [
        '<text x="1050" y="130" class="head">F1 Draufsicht · Ursprung vorne links</text>',
        f'<rect x="{px}" y="{py}" width="{inside_w*scale:.1f}" '
        f'height="{baffle_len*scale:.1f}" class="panel"/>',
        f'<circle cx="{px+inside_w*scale/2:.1f}" '
        f'cy="{py+horn.driver_depth_from_front_m*1000*scale:.1f}" r="{cut*scale/2:.1f}" class="cut"/>',
        f'<circle cx="{px+inside_w*scale/2:.1f}" '
        f'cy="{py+horn.driver_depth_from_front_m*1000*scale:.1f}" r="{outer*scale/2:.1f}" class="dim"/>',
        f'<text x="{px}" y="{py+baffle_len*scale+27:.1f}" class="text">F1 '
        f'{inside_w:.1f} × {baffle_len:.1f} × {t:.1f}</text>',
    ]
    # area law plot
    gx,gy,gw,gh=1050.0,430.0,380.0,190.0
    smax=det.length_m
    amax=max(det.profile_area_m2)*1.1
    parts.append(f'<text x="{gx}" y="{gy-20}" class="head">Flächenverlauf S(s) mit Taps</text>')
    parts.append(f'<path d="M{gx} {gy}V{gy+gh}H{gx+gw}" class="axis"/>')
    parts.append('<polyline points="'+' '.join(f'{gx+s/smax*gw:.1f},{gy+gh-a/amax*gh:.1f}'
                 for s,a in zip(det.profile_s_m,det.profile_area_m2,strict=True))+'" class="law"/>')
    built=[]
    for run in det.runs:
        built.append((run.s_start_m,det.width_m*run.h_start_m))
        built.append((run.s_end_m,det.width_m*run.h_end_m))
    parts.append('<polyline points="'+' '.join(f'{gx+s/smax*gw:.1f},{gy+gh-a/amax*gh:.1f}' for s,a in built)
                 +'" class="built"/>')
    for s_tap,label in ((horn.rear_tap_s_m,'hinten'),(horn.front_tap_s_m,'vorn')):
        xx=gx+s_tap/smax*gw
        parts.append(f'<path d="M{xx:.1f} {gy}V{gy+gh}" class="axis" stroke-dasharray="4 3"/>'
                     f'<text x="{xx+3:.1f}" y="{gy+12}" class="tiny">Tap {label}</text>')
    parts.append(f'<text x="{gx}" y="{gy+gh+18}" class="tiny">0 = geschlossenes Ende</text>'
                 f'<text x="{gx+gw}" y="{gy+gh+18}" text-anchor="end" class="tiny">s = {det.length_m*1000:.0f} mm (Mündung)</text>')
    parts.append(f'<text x="{gx}" y="{gy+gh+36}" class="tiny">blau: Gesetz · orange: gebaute Kanalflächen</text>')
    parts+= [
        '<path d="M50 760H1550" class="rule"/>',
        '<text x="55" y="800" class="head">Fertigung / Bohrbild / Akustik</text>',
        f'<text x="55" y="840" class="text">W1 in F1: X {inside_w/2:.1f}, '
        f'Y {horn.driver_depth_from_front_m*1000:.1f} · Ausschnitt Ø {cut:.1f} · Flansch Ø {outer:.1f}</text>',
        f'<text x="55" y="868" class="text">Lochkreis Ø {bolt:.1f} · '
        f'{driver.bolt_count or 0} Bohrungen Ø {hole:.1f}; fehlende Herstellermaße am Treiber prüfen</text>',
        f'<text x="55" y="896" class="text">Kanalhöhen: Lauf 1 {horn.upper_height_m*1000:.1f} (konstant), Mündungslauf '
        f'{horn.lower_height_m*1000:.1f} · Weg {horn.path_length_m*1000:.1f} · '
        f'c/2L {horn.half_wave_hz:.1f} Hz · ¼λ {horn.quarter_wave_hz:.1f} Hz</text>',
        f'<text x="55" y="924" class="text">Mündung BR1: '
        f'{horn.mouth_width_m*1000:.1f} × {horn.mouth_height_m*1000:.1f} '
        f'· Mittelpunkt X {bundle.front_elements[0].x_m*1000:.1f}, '
        f'Y {bundle.front_elements[0].y_m*1000:.1f}</text>',
    ]
    info=(f'Querschnitt: konstant {det.throat_area_m2*1e4:.0f} cm² bis zum Treiber, dann exponentiell auf '
          f'{det.mouth_area_m2*1e4:.0f} cm² (Flare-fc {horn.cutoff_hz:.1f} Hz); Tap-Abstand '
          f'{horn.tap_spacing_m*1000:.0f} mm; je Septum {det.facets_per_septum} gerade Teilbrett(er), Abweichung gebaut/Gesetz '
          f'max. {det.max_area_deviation*100:.1f} %. Grenzen: ebene Wellen, Tap-Lage nicht optimiert, am Prototyp '
          'bzw. in Hornresp prüfen.')
    row=956
    for i,line in enumerate(wrap(info,175)):
        parts.append(f'<text x="55" y="{row+i*19}" class="small">{escape(line)}</text>')
    row+=len(wrap(info,175))*19+10
    for i,run in enumerate(det.runs):
        direction='vorn→hinten' if run.x_end_m>run.x_start_m else 'hinten→vorn'
        parts.append(f'<text x="55" y="{row+i*19}" class="tiny">L{run.index} {direction}: s {run.s_start_m*1000:.0f}–'
                     f'{run.s_end_m*1000:.0f} · Höhe {run.h_start_m*1000:.0f}→{run.h_end_m*1000:.0f} · '
                     f'Fläche {det.width_m*run.h_start_m*1e4:.0f}→{det.width_m*run.h_end_m*1e4:.0f} cm²</text>')
    row+=len(det.runs)*19+12
    if driver.bolt_count and bolt and hole:
        for i in range(driver.bolt_count):
            angle=2*pi*i/driver.bolt_count
            hx=inside_w/2+bolt*cos(angle)/2
            hy=horn.driver_depth_from_front_m*1000+bolt*sin(angle)/2
            parts.append(f'<circle cx="{px+hx*scale:.1f}" cy="{py+hy*scale:.1f}" '
                         f'r="{max(2,hole*scale/2):.1f}" fill="white" stroke="#ba593b"/>')
            parts.append(f'<text x="{55+(i%4)*375}" y="{row+(i//4)*21}" class="small">'
                         f'Bohrung {i+1}: X {hx:.1f} Y {hy:.1f}</text>')
    parts.append('</svg>')
    return ''.join(parts)
