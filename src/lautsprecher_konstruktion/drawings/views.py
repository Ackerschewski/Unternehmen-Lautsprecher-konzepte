"""Simple orthographic SVG views from the resolved design geometry."""
from __future__ import annotations

from html import escape

from lautsprecher_konstruktion.drawings.style import (
    ACCENT_DARK,
    FONT_UI,
    INK,
    MUTED,
    PAPER,
    TEXT,
    special_css,
)
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
    x,y = 110,70
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
            size = (f"Ø{(e.cutout_diameter_m or e.outer_diameter_m)*1000:.0f}" if e.outer_diameter_m is not None
                    else f"{e.width*1000:.0f}×{e.height*1000:.0f}")
            body.append(f'<text x="{cx}" y="{cy-3}" text-anchor="middle" class="id">{escape(e.id)}</text>')
            body.append(f'<text x="{cx}" y="{cy+15}" text-anchor="middle" class="dimtext">'
                        f'{size} · x {local_x:.0f} · y {local_y:.0f} mm</text>')
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
    pw, ph = a*scale, b*scale
    # overall dimension chains: width below, height left (same numbers as the labels, never rescaled)
    yb, xl = y+ph+26, x-34
    body.append(f'<path d="M{x} {yb}H{x+pw}M{x} {yb-6}V{yb+6}M{x+pw} {yb-6}V{yb+6}" class="dim"/>')
    body.append(f'<text x="{x+pw/2}" y="{yb+22}" text-anchor="middle" class="label">{a:.0f} mm</text>')
    body.append(f'<path d="M{xl} {y}V{y+ph}M{xl-6} {y}H{xl+6}M{xl-6} {y+ph}H{xl+6}" class="dim"/>')
    body.append(f'<text x="{xl-10}" y="{y+ph/2}" text-anchor="middle" class="label" '
                f'transform="rotate(-90 {xl-10} {y+ph/2})">{b:.0f} mm</text>')
    body.append(f'<text x="{x}" y="{yb+48}" class="subtitle">Material {t:.0f} mm · Maße in mm vom Plattenrand</text>')
    title={"front":"Frontplatte","back":"Rückwand","partition":"Trennwand",
           "side":"Seitenansicht","section":"Schnitt"}[view]
    canvas_w, canvas_h = round(x+pw+60), round(y+ph+90)  # tight canvas: the view fills the screen area
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {canvas_w} {canvas_h}" width="{canvas_w}" height="{canvas_h}">'
        f'<rect width="{canvas_w}" height="{canvas_h}" fill="{PAPER}"/>'
        + special_css()
        # screen reading sizes: labels stay legible when the view is fitted into the window
        + (f"<style>.dimtext{{font:20px {FONT_UI};fill:{TEXT}}}.id{{font:700 22px {FONT_UI};fill:{ACCENT_DARK}}}"
           f".label{{font:700 24px {FONT_UI};fill:{INK}}}.subtitle{{font:18px {FONT_UI};fill:{MUTED}}}"
           f".title{{font:600 34px {FONT_UI};fill:{INK}}}</style>")
        + f'<text x="40" y="34" class="title">{title}</text>'
        + ''.join(body)
        + '</svg>'
    )
