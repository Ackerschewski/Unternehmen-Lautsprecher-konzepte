from __future__ import annotations

from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A3, landscape
from reportlab.pdfgen.canvas import Canvas

from lautsprecher_konstruktion.drawings.dimension_svg import dimension_rows
from lautsprecher_konstruktion.drawings.panel_sheet_svg import panel_sheet_surfaces
from lautsprecher_konstruktion.enclosure.layout import bolt_holes
from lautsprecher_konstruktion.export.bom import BomItem, priced_subtotal
from lautsprecher_konstruktion.export.pricing import budget_cost
from lautsprecher_konstruktion.services.design import DesignBundle

PAGE_W, PAGE_H = landscape(A3)
INK = HexColor('#172735')
BLUE = HexColor('#166b91')
MUTED = HexColor('#687782')


def _header(c: Canvas, title: str, bundle: DesignBundle, number: int) -> None:
    c.setFillColor(INK)
    c.setFont('Helvetica-Bold', 19)
    c.drawString(42, PAGE_H-48, title)
    c.setFont('Helvetica', 9)
    c.setFillColor(MUTED)
    c.drawRightString(PAGE_W-42, PAGE_H-45, bundle.project.revision)
    c.setStrokeColor(BLUE)
    c.setLineWidth(1.5)
    c.line(42, PAGE_H-60, PAGE_W-42, PAGE_H-60)
    c.setFont('Helvetica', 8)
    c.drawString(42, 24, bundle.project.name[:90])
    c.drawRightString(PAGE_W-42, 24, str(number))
    c.setFillColor(INK)


def _lines(c: Canvas, lines: list[str], x: float, y: float, step: float = 21) -> float:
    c.setFont('Helvetica', 10)
    for line in lines:
        c.drawString(x, y, line[:155])
        y -= step
    return y


def _table(c: Canvas, headers: tuple[str, ...], rows: list[tuple[str, ...]],
           widths: tuple[float, ...], y: float) -> None:
    x0 = 42.0
    c.setFillColor(BLUE)
    c.rect(x0, y-6, sum(widths), 22, fill=1, stroke=0)
    c.setFillColor(HexColor('#ffffff'))
    c.setFont('Helvetica-Bold', 9)
    x = x0
    for title, width in zip(headers, widths, strict=True):
        c.drawString(x+5, y+1, title)
        x += width
    c.setFillColor(INK)
    c.setFont('Helvetica', 8.5)
    y -= 25
    for idx, row in enumerate(rows):
        if y < 65:
            break
        if idx % 2 == 0:
            c.setFillColor(HexColor('#edf3f6'))
            c.rect(x0, y-5, sum(widths), 20, fill=1, stroke=0)
        c.setFillColor(INK)
        x = x0
        for value, width in zip(row, widths, strict=True):
            max_chars = max(5, int(width/5.0))
            display = value if len(value) <= max_chars else value[:max_chars-3]+'...'
            c.drawString(x+5, y+1, display)
            x += width
        y -= 20


def _drawing(c: Canvas, bundle: DesignBundle) -> None:
    cab = bundle.cabinet
    scale = min(310/(cab.width_m*1000), 440/(cab.height_m*1000), 280/(cab.depth_m*1000))
    fw, fh, fd = cab.width_m*1000*scale, cab.height_m*1000*scale, cab.depth_m*1000*scale
    x, y = 85, 145
    c.setStrokeColor(INK)
    c.setLineWidth(1.4)
    c.rect(x, y, fw, fh)
    for e in bundle.front_elements:
        if e.surface != 'front':
            continue
        ex, ey = x+e.x_m*1000*scale, y+e.y_m*1000*scale
        if e.outer_diameter_m is not None:
            c.circle(ex, ey, (e.cutout_diameter_m or e.outer_diameter_m)*500*scale)
        else:
            ew, eh = e.width*1000*scale, e.height*1000*scale
            c.rect(ex-ew/2, ey-eh/2, ew, eh)
        c.setFont('Helvetica', 8)
        c.drawCentredString(ex, ey+4, e.id)
        for hx,hy,hr in bolt_holes(e):
            c.circle(x+hx*1000*scale,y+hy*1000*scale,hr*1000*scale)
    sx = x+fw+100
    c.rect(sx, y, fd, fh)
    ft=cab.effective_front_thickness_m*1000*scale
    bt=cab.effective_back_thickness_m*1000*scale
    tt=(cab.top_thickness_m or cab.panel_thickness_m)*1000*scale
    bottom=(cab.bottom_thickness_m or cab.panel_thickness_m)*1000*scale
    c.setFillColor(HexColor('#dce7ed'))
    for px,py,pw,ph in ((sx,y,ft,fh),(sx+fd-bt,y,bt,fh),
                        (sx+ft,y+fh-tt,fd-ft-bt,tt),(sx+ft,y,fd-ft-bt,bottom)):
        c.rect(px,py,pw,ph,fill=1,stroke=1)
    c.setFillColor(INK)
    inner_x=sx+ft
    rear_x=sx+fd-bt
    partition_x=None
    if bundle.partition_front_depth_m is not None:
        partition_x=inner_x+bundle.partition_front_depth_m*1000*scale
        driver=next((e for e in bundle.front_elements if e.surface=='partition' and e.type!='port'),None)
        cy=y+(driver.y_m*1000 if driver else cab.height_m*500)*scale
        opening=(driver.cutout_diameter_m or driver.height)*1000*scale if driver else 0
        c.setFillColor(HexColor('#dce7ed'))
        c.rect(partition_x,y+bottom,cab.panel_thickness_m*1000*scale,
               max(0,cy-opening/2-y-bottom),fill=1,stroke=1)
        c.rect(partition_x,cy+opening/2,cab.panel_thickness_m*1000*scale,
               max(0,y+fh-tt-cy-opening/2),fill=1,stroke=1)
        c.setFillColor(INK)
        c.setFont('Helvetica',8)
        c.drawString(inner_x+5,y+fh/2,'Frontkammer')
        c.drawString(partition_x+12,y+fh/2,'Rueckkammer')
    c.setFillColor(HexColor('#dceff8'))
    for e in bundle.front_elements:
        cy=y+e.y_m*1000*scale
        opening=(e.cutout_diameter_m or e.height)*1000*scale
        depth=e.mounting_depth_m*1000*scale
        if e.surface=='front':
            if e.type=='port' and bundle.port is not None and bundle.port.shape=='slot':
                wall=cab.panel_thickness_m*1000*scale
                c.setFillColor(HexColor('#dce7ed'))
                c.rect(inner_x,cy-opening/2-wall,depth,wall,fill=1,stroke=1)
                c.rect(inner_x,cy+opening/2,depth,wall,fill=1,stroke=1)
                c.setFillColor(HexColor('#dceff8'))
            c.rect(inner_x,cy-opening/2,depth,opening,fill=1,stroke=1)
        elif e.surface=='back':
            c.rect(rear_x-depth,cy-opening/2,depth,opening,fill=1,stroke=1)
        elif partition_x is not None:
            c.rect(partition_x,cy-opening/2,depth,opening,fill=1,stroke=1)
    c.setFillColor(INK)
    if bundle.brace:
        c.setFillColor(HexColor('#dceadd'))
        for depth in bundle.brace_depths_m:
            bx=inner_x+depth*1000*scale
            c.rect(bx,y+bottom,cab.panel_thickness_m*1000*scale,
                   min(bundle.brace.border_m*1000*scale,fh/4),fill=1,stroke=1)
            c.rect(bx,y+fh-tt-min(bundle.brace.border_m*1000*scale,fh/4),
                   cab.panel_thickness_m*1000*scale,
                   min(bundle.brace.border_m*1000*scale,fh/4),fill=1,stroke=1)
        c.setFillColor(INK)
    if bundle.coupler:
        k=bundle.coupler
        woofer=next((e for e in bundle.front_elements if e.id=='W1' and e.surface=='front'),None)
        if woofer:
            cy=y+woofer.y_m*1000*scale
            outer=k.outer_diameter_m*1000*scale
            inner=k.inner_diameter_m*1000*scale
            length=k.length_m*1000*scale
            ring_x=inner_x+length
            ring_t=k.ring_thickness_m*1000*scale
            wall=(outer-inner)/2
            c.setFillColor(HexColor('#dce7ed'))
            for yy in (cy-outer/2,cy+inner/2):
                c.rect(inner_x,yy,length,wall,fill=1,stroke=1)
            for yy in (cy-outer/2,cy+k.driver_cutout_m*500*scale):
                c.rect(ring_x,yy,ring_t,(outer-k.driver_cutout_m*1000*scale)/2,fill=1,stroke=1)
            c.setFillColor(INK)
            c.setFont('Helvetica',8)
            c.drawString(ring_x+ring_t+4,cy+outer/2+5,'W2 / Isobarik')
    c.setFont('Helvetica-Bold', 11)
    c.drawString(x, y+fh+22, 'Vorderansicht')
    c.drawString(sx, y+fh+22, 'Seitenschnitt / Innenaufbau')
    c.setFont('Helvetica', 10)
    c.drawString(x, y-32, f'B {cab.width_m*1000:.1f} mm   H {cab.height_m*1000:.1f} mm')
    c.drawString(sx, y-32, f'T {cab.depth_m*1000:.1f} mm')
    c.drawString(sx, y-51, f'Materialstärke {cab.panel_thickness_m*1000:.1f} mm')


def _panel_drawing(c: Canvas, bundle: DesignBundle, surface: str) -> None:
    """Dimensioned machining face; coordinates match the accompanying panel DXF."""
    cab = bundle.cabinet
    w = (cab.internal_width_m if surface == 'partition' else cab.width_m)*1000
    h = (cab.internal_height_m if surface == 'partition' else cab.height_m)*1000
    t = (cab.panel_thickness_m if surface == 'partition' else
         cab.effective_front_thickness_m if surface == 'front' else
         cab.effective_back_thickness_m)*1000
    offset_x = cab.panel_thickness_m*1000 if surface == 'partition' else 0
    offset_y = (cab.bottom_thickness_m or cab.panel_thickness_m)*1000 if surface == 'partition' else 0
    scale = min(440/w, 510/h)
    x0, y0 = 110, 150
    c.setStrokeColor(INK)
    c.setLineWidth(1.5)
    c.rect(x0, y0, w*scale, h*scale)
    c.setFont('Helvetica', 10)
    c.drawString(x0, y0-28, f'Breite {w:.1f} mm')
    c.drawString(x0, y0-45, f'Hoehe {h:.1f} mm  |  Materialstaerke {t:.1f} mm')
    c.drawString(x0, y0-62, 'Ursprung links unten, Ansicht von aussen')
    sx, sy = 660, PAGE_H-105
    c.setFont('Helvetica-Bold', 12)
    c.drawString(sx, sy, f'{surface.upper()} - Ausschnitte')
    sy -= 30
    for element in (e for e in bundle.front_elements if e.surface == surface):
        ex, ey = element.x_m*1000-offset_x, element.y_m*1000-offset_y
        cx, cy = x0+ex*scale, y0+ey*scale
        c.setStrokeColor(BLUE)
        if element.outer_diameter_m is not None:
            diameter = (element.cutout_diameter_m or element.outer_diameter_m)*1000
            c.circle(cx, cy, diameter*scale/2)
            c.setDash(4, 3)
            c.circle(cx, cy, element.outer_diameter_m*500*scale)
            c.setDash()
            cut = f'D {diameter:.1f}'
        else:
            ew, eh = element.width*1000, element.height*1000
            c.rect(cx-ew*scale/2, cy-eh*scale/2, ew*scale, eh*scale)
            cut = f'{ew:.1f} x {eh:.1f}'
        c.setStrokeColor(HexColor('#b7442f'))
        for hx, hy, radius in bolt_holes(element):
            c.circle(x0+(hx*1000-offset_x)*scale,
                     y0+(hy*1000-offset_y)*scale, max(1.5,radius*1000*scale))
        c.setStrokeColor(INK)
        c.setFont('Helvetica-Bold', 9)
        c.drawString(cx+5, cy+5, element.id)
        c.drawString(sx, sy, f'{element.id}: X {ex:.1f} / Y {ey:.1f} mm')
        c.setFont('Helvetica', 9)
        c.drawString(sx, sy-16, f'Ausschnitt {cut} mm  |  Tiefe {element.mounting_depth_m*1000:.1f} mm')
        if element.bolt_count and element.hole_diameter_m and element.bolt_circle_diameter_m:
            note = (f'{element.bolt_count} x D {element.hole_diameter_m*1000:.1f} '
                    f'auf Lochkreis D {element.bolt_circle_diameter_m*1000:.1f} mm')
        elif element.bolt_count and element.bolt_circle_diameter_m:
            note = f'Lochkreis D {element.bolt_circle_diameter_m*1000:.1f} mm; Bohr-Durchmesser fehlt'
        else:
            note = 'Kein Hersteller-Bohrbild hinterlegt'
        c.drawString(sx, sy-32, note)
        sy -= 77


def write_pdf_report(path: str | Path, bundle: DesignBundle, bom: tuple[BomItem, ...]) -> None:
    path = Path(path)
    c = Canvas(str(path), pagesize=(PAGE_W, PAGE_H))
    c.setTitle(f'{bundle.project.name} - Fertigungsunterlagen')
    page = 1

    _header(c, 'Projektübersicht', bundle, page)
    cab = bundle.cabinet
    data = [
        f'Projekt: {bundle.project.name}',
        f'Revision: {bundle.project.revision}',
        f'Treiber: {bundle.project.driver.manufacturer} {bundle.project.driver.model}',
        f'Gehäuse: {bundle.project.enclosure.enclosure_type}',
        f'Netto-Volumen: {bundle.target_net_volume_m3*1000:.2f} l',
        f'Außenmaße B x H x T: {cab.width_m*1000:.1f} x {cab.height_m*1000:.1f} x {cab.depth_m*1000:.1f} mm',
        f'Material: {bundle.project.material}',
    ]
    if bundle.port:
        data.extend((f'Abstimmung Fb: {bundle.port.tuning_hz:.1f} Hz',
                     f'Port: {bundle.port.shape}, Fläche {bundle.port.area_m2*10000:.1f} cm², Länge {bundle.port.physical_length_m*1000:.1f} mm'))
    if bundle.rear_port:
        data.append(f'BR2 Rueckkammer: Fb2 {bundle.rear_port.tuning_hz:.1f} Hz, '
                    f'Ø {(bundle.rear_port.diameter_m or 0)*1000:.1f} mm, '
                    f'Laenge {bundle.rear_port.physical_length_m*1000:.1f} mm')
    if bundle.radiator:
        data.append(f'Passivmembran: Zusatzmasse {bundle.radiator.added_mass_kg*1000:.1f} g')
    if bundle.front_chamber_volume_m3 is not None:
        data.append(f'Bandpass: Frontkammer {bundle.front_chamber_volume_m3*1000:.1f} l, Rueckkammer {bundle.rear_chamber_volume_m3*1000:.1f} l')
    if bundle.sealed:
        data.append(f'Geschlossen: Qtc {bundle.sealed.target_qtc:.3f}, F3 {bundle.sealed.f3_hz:.1f} Hz')
    if bundle.vented_response and bundle.vented_response.f3_hz:
        data.append(f'Bassreflex F3 (Modell): {bundle.vented_response.f3_hz:.1f} Hz')
    _lines(c, data, 55, PAGE_H-100)
    c.showPage(); page += 1

    _header(c, 'Gehäusezeichnung', bundle, page)
    _drawing(c, bundle)
    c.showPage(); page += 1

    for surface in panel_sheet_surfaces(bundle):
        _header(c, f'Einzelteilplan: {surface}', bundle, page)
        _panel_drawing(c, bundle, surface)
        c.showPage(); page += 1

    _header(c, 'Massblatt und Einbaukoordinaten', bundle, page)
    _lines(c, [
        'Alle Masse in mm; X ab linker, Y ab unterer Aussenecke der genannten Flaeche.',
        f'Aussen B x H x T: {cab.width_m*1000:.1f} x {cab.height_m*1000:.1f} x {cab.depth_m*1000:.1f}',
        f'Innen B x H x T: {cab.internal_width_m*1000:.1f} x {cab.internal_height_m*1000:.1f} x {cab.internal_depth_m*1000:.1f}',
        (f'Front {cab.effective_front_thickness_m*1000:.1f}; Rueckwand {cab.effective_back_thickness_m*1000:.1f}; '
         f'Deckel {(cab.top_thickness_m or cab.panel_thickness_m)*1000:.1f}; '
         f'Boden {(cab.bottom_thickness_m or cab.panel_thickness_m)*1000:.1f}'),
    ], 55, PAGE_H-99, 19)
    cut_rows = []
    for element, row in zip(bundle.front_elements, dimension_rows(bundle), strict=True):
        flange = f'Ø {element.outer_diameter_m*1000:.1f}' if element.outer_diameter_m else '-'
        holes = (f'{element.bolt_count} x Ø {element.hole_diameter_m*1000:.1f} auf LK Ø {element.bolt_circle_diameter_m*1000:.1f}'
                 if element.bolt_count and element.bolt_circle_diameter_m and element.hole_diameter_m else
                 f'LK Ø {element.bolt_circle_diameter_m*1000:.1f}; Bohr-Ø fehlt'
                 if element.bolt_count and element.bolt_circle_diameter_m else 'keine Bohrdaten')
        cut_rows.append((row[0], row[1], f'{row[2]:.1f}', f'{row[3]:.1f}', row[4], flange,
                         f'{row[5]:.1f}', holes))
    _table(c, ('ID','Flaeche','X Mitte','Y Mitte','Ausschnitt','Flansch','Tiefe','Bohrungen'),
           cut_rows, (65,90,80,80,145,130,70,270), PAGE_H-205)
    extra = []
    if bundle.port:
        extra.append(f'Port: Laenge {bundle.port.physical_length_m*1000:.1f}; Flaeche {bundle.port.area_m2*10000:.1f} cm2.')
    if bundle.rear_port:
        extra.append(f'BR2: Laenge {bundle.rear_port.physical_length_m*1000:.1f}; '
                     f'Flaeche {bundle.rear_port.area_m2*10000:.1f} cm2.')
    if bundle.partition_front_depth_m is not None:
        rear_depth = cab.internal_depth_m-bundle.partition_front_depth_m-cab.panel_thickness_m
        extra.append(f'Kammern: Fronttiefe {bundle.partition_front_depth_m*1000:.1f}; Ruecktiefe {rear_depth*1000:.1f}; Trennwand {cab.panel_thickness_m*1000:.1f}.')
    if bundle.brace:
        extra.append(f'Fensterstreben: {bundle.brace.quantity} x {bundle.brace.thickness_m*1000:.1f} dick; Rand {bundle.brace.border_m*1000:.1f}.')
    extra.append('Vor dem Fräsen Original-Datenblatt und reale Chassis pruefen.')
    _lines(c, extra, 55, PAGE_H-245-len(cut_rows)*20, 18)
    c.showPage(); page += 1

    _header(c, 'Innenaufbau und Volumenbilanz', bundle, page)
    inside = [
        f'Brutto innen: {cab.gross_internal_volume_m3*1000:.2f} l',
        f'Verdrängung gesamt: {bundle.total_displacement_m3*1000:.2f} l',
        f'Netto akustisch: {bundle.target_net_volume_m3*1000:.2f} l',
        f'Innenbreite x Innenhöhe x Innentiefe: {cab.internal_width_m*1000:.1f} x {cab.internal_height_m*1000:.1f} x {cab.internal_depth_m*1000:.1f} mm',
    ]
    if bundle.port:
        p = bundle.port
        opening = (f'Ø {p.diameter_m*1000:.1f} mm' if p.diameter_m else
                   f'{p.width_m*1000:.1f} x {p.height_m*1000:.1f} mm')
        inside.append(f'BR1 Portöffnung: {opening}; Länge {p.physical_length_m*1000:.1f} mm; Fläche {p.area_m2*10000:.1f} cm2')
    if bundle.rear_port:
        p = bundle.rear_port
        inside.append(f'BR2 Portöffnung Rueckwand: Ø {(p.diameter_m or 0)*1000:.1f} mm; '
                      f'Länge {p.physical_length_m*1000:.1f} mm; Fläche {p.area_m2*10000:.1f} cm2')
    if bundle.partition_front_depth_m is not None:
        inside.append(f'Frontkammer-Tiefe ab Front innen: {bundle.partition_front_depth_m*1000:.1f} mm')
        inside.append(f'Trennwand: {cab.internal_width_m*1000:.1f} x {cab.internal_height_m*1000:.1f} x {cab.panel_thickness_m*1000:.1f} mm')
    if bundle.brace:
        b = bundle.brace
        inside.append(f'Fensterstrebe: {b.outer_width_m*1000:.1f} x {b.outer_height_m*1000:.1f} x {b.thickness_m*1000:.1f} mm')
        inside.append(f'Fensteröffnung: {(b.outer_width_m-2*b.border_m)*1000:.1f} x {(b.outer_height_m-2*b.border_m)*1000:.1f} mm')
        inside.extend(f'B{i} Tiefe ab Front innen: {depth*1000:.1f} mm'
                      for i,depth in enumerate(bundle.brace_depths_m, start=1))
    if bundle.coupler:
        k = bundle.coupler
        inside.extend((f'Koppelrohr: innen Ø {k.inner_diameter_m*1000:.1f}; außen Ø {k.outer_diameter_m*1000:.1f}; Länge {k.length_m*1000:.1f} mm',
                       f'Montagering: außen Ø {k.outer_diameter_m*1000:.1f}; Ausschnitt Ø {k.driver_cutout_m*1000:.1f}; Dicke {k.ring_thickness_m*1000:.1f} mm',
                       'W1 und W2 sind identische Chassis; Koppelkammer luftdicht schließen.'))
    _lines(c, inside, 55, PAGE_H-105, 24)
    c.showPage(); page += 1

    _header(c, 'Zuschnittliste', bundle, page)
    cut_rows = [(p.name, str(p.quantity), f'{p.width_m*1000:.1f}', f'{p.height_m*1000:.1f}',
                 f'{p.thickness_m*1000:.1f}', bundle.project.material) for p in bundle.panels]
    if bundle.brace:
        b = bundle.brace
        cut_rows.append(('Fensterstrebe', str(b.quantity), f'{b.outer_width_m*1000:.1f}',
                         f'{b.outer_height_m*1000:.1f}', f'{b.thickness_m*1000:.1f}', bundle.project.material))
    _table(c, ('Bauteil','Anzahl','Länge mm','Breite mm','Dicke mm','Material'), cut_rows,
           (230,70,110,110,110,390), PAGE_H-105)
    c.showPage(); page += 1

    _header(c, 'Stückliste', bundle, page)
    rows = [(i.category,i.reference,i.description,str(i.quantity),i.specification,
             f'{i.unit_price_eur:.2f}' if i.unit_price_eur is not None else '-',
             f'{i.line_total_eur:.2f}' if i.line_total_eur is not None else '-',
             i.price_kind) for i in bom]
    _table(c, ('Kategorie','Ref.','Beschreibung','Anz.','Spezifikation','EUR/St.','EUR','Art'), rows,
           (100,55,205,43,210,75,60,90), PAGE_H-105)
    subtotal, missing = priced_subtotal(bom)
    planned = budget_cost(bom)
    c.setFont('Helvetica', 9)
    c.drawString(55, 55, f'Bekannte Teilsumme {subtotal:.2f} EUR | {missing} Positionen ohne Preis | '
                 f'Budgetansatz inkl. 15% Reserve: {planned:.2f} EUR' if planned is not None else
                 f'Bekannte Teilsumme {subtotal:.2f} EUR | {missing} Positionen ohne Preis')
    c.showPage(); page += 1

    if bundle.crossover:
        _header(c, 'Frequenzweiche', bundle, page)
        c.setFont('Helvetica', 11)
        c.drawString(55, PAGE_H-102, f'{bundle.crossover.name}  |  {bundle.crossover.crossover_hz:.0f} Hz')
        components = [(p.reference,p.kind,p.display_value,p.branch,p.connection) for p in bundle.crossover.components]
        _table(c, ('Ref.','Typ','Sollwert','Zweig','Anschluss'), components,
               (110,180,170,280,280), PAGE_H-140)
        c.showPage(); page += 1

    _header(c, 'Simulation und Warnungen', bundle, page)
    lines = []
    sim = bundle.vented_response
    if sim:
        lines.append(f'Eingangsleistung: {sim.power_w:.1f} W (äquivalente Spannung an Re)')
        lines.append(f'F3: {sim.f3_hz:.1f} Hz' if sim.f3_hz else 'F3: nicht bestimmbar')
        if sim.excursion_mm is not None and sim.port_velocity_m_s is not None:
            import numpy as np
            lines.append(f'Max. Auslenkung: {np.max(sim.excursion_mm):.1f} mm')
            lines.append(f'Max. Portgeschwindigkeit: {np.max(sim.port_velocity_m_s):.1f} m/s')
        else:
            lines.append('Absolute Auslenkung und Portgeschwindigkeit: fehlende Treiberdaten')
    lines.append('')
    lines.append('Warnungen:')
    lines.extend('- '+warning for warning in bundle.warnings[:30])
    if not bundle.warnings:
        lines.append('Keine automatischen Warnungen.')
    _lines(c, lines, 55, PAGE_H-105, 18)
    c.save()
