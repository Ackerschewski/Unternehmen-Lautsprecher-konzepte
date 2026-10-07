"""Simple orthographic SVG views from the resolved design geometry."""
from __future__ import annotations

from html import escape

from lautsprecher_konstruktion.drawings.style import PAPER, special_css
from lautsprecher_konstruktion.enclosure.layout import bolt_holes
from lautsprecher_konstruktion.services.design import DesignBundle


def render_view_svg(bundle: DesignBundle, view: str) -> str:
    if bundle.baffle_mode is not None:
        from lautsprecher_konstruktion.drawings.baffle_svg import render_baffle_svg
        return render_baffle_svg(bundle)
    if bundle.front_horn is not None:
        from lautsprecher_konstruktion.drawings.front_horn_svg import render_front_horn_svg
        return render_front_horn_svg(bundle)
    if bundle.tapped_horn is not None:
        from lautsprecher_konstruktion.drawings.tapped_horn_svg import render_tapped_horn_svg
        return render_tapped_horn_svg(bundle)
    cab = bundle.cabinet
    w,h,d,t = (v*1000 for v in (cab.width_m,cab.height_m,cab.depth_m,cab.panel_thickness_m))
    if view in ("front", "back", "partition"):
        a,b = (cab.internal_width_m*1000,cab.internal_height_m*1000) if view == "partition" else (w,h)
    elif view in ("side","section"):
        a,b = d,h
    else:
        raise ValueError("unknown view")
    scale = min(550/a, 660/b)
    x,y = 80,65
    body = [f'<rect x="{x}" y="{y}" width="{a*scale}" height="{b*scale}" class="panel"/>']
    if view in ("front", "back", "partition"):
        for e in bundle.front_elements:
            if e.surface != view:
                continue
            local_x=e.x_m*1000-(t if view == "partition" else 0)
            local_y=e.y_m*1000-((cab.bottom_thickness_m or cab.panel_thickness_m)*1000 if view == "partition" else 0)
            cx=x+local_x*scale
            cy=y+(b-local_y)*scale
            if e.outer_diameter_m is not None:
                r=(e.cutout_diameter_m or e.outer_diameter_m)*500*scale
                body.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" class="cut"/>')
            else:
                ew,eh=e.width*1000*scale,e.height*1000*scale
                body.append(f'<rect x="{cx-ew/2}" y="{cy-eh/2}" width="{ew}" height="{eh}" class="cut"/>')
            for hx,hy,hr in bolt_holes(e):
                offset=t if view == "partition" else 0
                bottom=(cab.bottom_thickness_m or cab.panel_thickness_m)*1000 if view == "partition" else 0
                body.append(f'<circle cx="{x+(hx*1000-offset)*scale}" cy="{y+(b-hy*1000+bottom)*scale}" r="{hr*1000*scale}" class="drill"/>')
            body.append(f'<text x="{cx}" y="{cy+5}" text-anchor="middle">{escape(e.id)}</text>')
    if view == "section":
        inside_x=x+t*scale
        inside_y=y+t*scale
        body.append(f'<rect x="{inside_x}" y="{inside_y}" width="{(d-2*t)*scale}" height="{(h-2*t)*scale}" class="inner"/>')
        for e in bundle.front_elements:
            if e.mounting_depth_m:
                ey=y+(h-e.y_m*1000)*scale
                eh=e.height*1000*scale
                body.append(f'<rect x="{x+t*scale}" y="{ey-eh/2}" width="{e.mounting_depth_m*1000*scale}" height="{eh}" class="depth"/>')
        if bundle.brace:
            for i in range(bundle.brace.quantity):
                bx=inside_x+(i+1)*(d-2*t)*scale/(bundle.brace.quantity+1)
                body.append(f'<rect x="{bx}" y="{inside_y}" width="{t*scale}" height="{(h-2*t)*scale}" class="brace"/>')
    body.append(f'<text x="{x}" y="{y+b*scale+32}">{a:.1f} x {b:.1f} mm | Material {t:.1f} mm</text>')
    title={"front":"Frontplatte","back":"Rückwand","partition":"Trennwand",
           "side":"Seitenansicht","section":"Schnitt"}[view]
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 820" width="800" height="820">'
        f'<rect width="800" height="820" fill="{PAPER}"/>'
        + special_css()
        + f'<text x="40" y="34" class="title">{title}</text>'
        + ''.join(body)
        + '</svg>'
    )
