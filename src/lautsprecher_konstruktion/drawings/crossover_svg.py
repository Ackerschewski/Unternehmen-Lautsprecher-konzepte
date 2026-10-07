from __future__ import annotations

from html import escape

from lautsprecher_konstruktion.crossover.passive import CrossoverDesign
from lautsprecher_konstruktion.drawings.style import painted


@painted
def render_crossover_svg(design: CrossoverDesign) -> str:
    """Render a workshop-oriented passive crossover overview.

    This is intentionally a readable connection drawing, not an EDA/netlist format.
    """
    width = 1100
    row_height = 86
    if design.ways == 3:
        branches = [
            ("Woofer / Tiefpass", [c for c in design.components if c.branch.split()[0] == "woofer"]),
            ("Mitteltöner / Bandpass", [c for c in design.components if c.branch.split()[0] == "midrange"]),
            ("Tweeter / Hochpass", [c for c in design.components if c.branch.split()[0] == "tweeter"]),
        ]
    else:
        branches = [
            ("Woofer / Tiefpass", [c for c in design.components if "woofer" in c.branch]),
            ("Tweeter / Hochpass", [c for c in design.components if "tweeter" in c.branch]),
            ("Pegel / Korrektur", [
                c for c in design.components
                if "attenuation" in c.branch or "zobel" in c.branch
            ]),
        ]
    split_text = f'{design.crossover_hz:.0f} Hz'
    if design.ways == 3 and design.upper_crossover_hz:
        split_text += f' / {design.upper_crossover_hz:.0f} Hz'
    active = [(name, components) for name, components in branches if components]
    height = 150 + row_height * max(len(active), 1)

    parts = [
        (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">'),
        ('<style>.wire{stroke:%INK%;stroke-width:2;fill:none}.box{fill:%WHITE%;stroke:%INK%;stroke-width:1.5}'
        '.title{font:bold 22px sans-serif}.label{font:bold 14px sans-serif}'
        '.txt{font:13px sans-serif}.note{font:12px sans-serif;fill:%MUTED%}</style>'),
        f'<text x="30" y="34" class="title">{escape(design.name)} — {split_text}</text>',
        ('<text x="30" y="62" class="note">Elektrischer Startentwurf auf Basis nominaler '
        'resistiver Lasten; finale Abstimmung mit Messdaten.</text>'),
    ]

    y = 105
    for branch_name, components in active:
        parts.append(f'<text x="30" y="{y+25}" class="label">{escape(branch_name)}</text>')
        start_x = 210
        wire_y = y + 20
        parts.append(f'<line x1="{start_x-40}" y1="{wire_y}" x2="{start_x}" '
                     f'y2="{wire_y}" class="wire"/>')
        x = start_x
        for component in components:
            box_w = 155
            parts.append(
                f'<rect x="{x}" y="{y-4}" width="{box_w}" height="48" rx="5" class="box"/>'
            )
            parts.append(
                f'<text x="{x+box_w/2}" y="{y+15}" text-anchor="middle" class="label">'
                f'{escape(component.reference)}</text>'
            )
            parts.append(
                f'<text x="{x+box_w/2}" y="{y+34}" text-anchor="middle" class="txt">'
                f'{escape(component.display_value)}</text>'
            )
            parts.append(
                f'<line x1="{x+box_w}" y1="{wire_y}" x2="{x+box_w+35}" '
                f'y2="{wire_y}" class="wire"/>'
            )
            parts.append(
                f'<text x="{x}" y="{y+61}" class="note">'
                f'{escape(component.kind)} · {escape(component.connection)}</text>'
            )
            x += box_w + 35
        y += row_height

    parts.append('</svg>')
    return "".join(parts)
