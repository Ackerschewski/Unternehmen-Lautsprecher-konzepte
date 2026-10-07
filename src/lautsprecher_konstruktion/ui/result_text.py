"""HTML text blocks for the result view (details and bill of materials); pure functions, no widgets."""
from __future__ import annotations

from html import escape

from lautsprecher_konstruktion.enclosure.registry import registry
from lautsprecher_konstruktion.export.pricing import budget_cost
from lautsprecher_konstruktion.presentation import component_text, de, price_kind
from lautsprecher_konstruktion.services.automatic import SpeakerDesign
from lautsprecher_konstruktion.services.price_status import price_info


def details_html(design: SpeakerDesign, budget_eur: float) -> str:
    bundle = design.bundle
    c = bundle.cabinet
    f3 = bundle.sealed.f3_hz if bundle.sealed else (
        bundle.vented_response.f3_hz if bundle.vented_response else None)
    lines = [f"<h2>{escape(design.label)}</h2>",
        f"<p><b>Gehäuse:</b> {escape(registry.get(design.project.enclosure.enclosure_type).label)} · "
        f"{c.width_m*1000:.0f} × {c.height_m*1000:.0f} × {c.depth_m*1000:.0f} mm<br>"
        f"<b>Netto:</b> {bundle.target_net_volume_m3*1000:.1f} l · "
        f"<b>F3:</b> {f3:.1f} Hz</p>" if f3 else "<p>F3 nicht berechenbar</p>",
        f"<p><b>Tieftöner:</b> {escape(design.woofer.manufacturer)} {escape(design.woofer.model)}<br>"
        f"<b>Hochtöner:</b> {escape(design.tweeter.model) if design.tweeter else '–'}<br>"
        f"<b>Chassispreis:</b> {design.price:.2f} €</p>" if design.price is not None else
        f"<p><b>Tieftöner:</b> {escape(design.woofer.manufacturer)} {escape(design.woofer.model)}<br>"
        f"<b>Hochtöner:</b> {escape(design.tweeter.model) if design.tweeter else '–'}<br>"
        "<b>Chassispreis:</b> nicht verfügbar</p>"]
    lines.append("<p><b>Gesamtkalkulation inkl. 15 % Reserve:</b> "+
        (f"{design.total_price_eur:.2f} €" if design.total_price_eur is not None else
         "nicht vollständig bepreist")+"</p>")
    if budget_eur and design.total_price_eur is not None:
        lines.append(f"<p><b>Budget noch frei:</b> "
                     f"{budget_eur-design.total_price_eur:.2f} €</p>")
    if design.breakdown:
        lines.append(f"<h3>Teilbewertung · {design.score:.0f}/100 aus {len(design.breakdown)} "
                     "bewerteten Kriterien</h3><p>Keine Qualitätsfreigabe: nicht belegbare Kriterien "
                     "fließen nicht ein.</p>")
        names = {"bass": "Tiefbass", "size": "Kompaktheit", "headroom": "Auslenkungsreserve",
            "port": "Portreserve", "delay": "Gruppenlaufzeit", "flatness": "Linearität",
            "cost": "Budgetreserve", "target_curve": "Nähe zur Zielkurve"}
        for metric in design.breakdown:
            lines.append(f"<p><b>{names.get(metric.name, metric.name)}</b> "
                f"{metric.value:.0f}/100 "
                f"(Gewicht {metric.weight:g})<br>{escape(metric.evidence)}</p>")
        missing = {"headroom", "port", "delay", "flatness"}-{
            metric.name for metric in design.breakdown}
        if bundle.port is None:
            missing.discard("port")
        if missing:
            lines.append("<p><i>Nicht bewertet: "+", ".join(names[key] for key in sorted(missing))+
                ". Nicht verfügbare Werte werden nicht ergänzt.</i></p>")
    lines.append("<h3>Warum dieser Entwurf?</h3><ul>"+
        "".join(f"<li>{escape(reason)}</li>" for reason in design.reasons)+"</ul>")
    if design.provisional_crossover:
        lines.append("<p><b>Vorläufiger Frequenzweichenentwurf:</b> Für eine Endabstimmung "
            "sind FRD/ZMA-Messungen am aufgebauten Lautsprecher nötig.</p>")
    if bundle.warnings:
        lines.append("<h3>Hinweise</h3><ul>"+
            "".join(f"<li>{escape(message)}</li>" for message in bundle.warnings)+"</ul>")
    return "".join(lines)


def bom_html(design: SpeakerDesign) -> str:
    """German bill of materials with price status per line and honest coverage summary."""
    info = price_info(design.bom)
    planned_total = budget_cost(design.bom)

    def money(value: float | None) -> str:
        return f"{de(value, 2)} €" if value is not None else "–"

    rows = "".join(
        f"<tr><td>{escape(item.reference)}</td><td>{escape(component_text(item.description))}</td>"
        f"<td align='right'>{item.quantity}</td><td align='right'>{money(item.unit_price_eur)}</td>"
        f"<td align='right'>{money(item.line_total_eur)}</td>"
        f"<td>{escape(price_kind(item.price_kind) if item.unit_price_eur is not None else 'Preis fehlt')}</td></tr>"
        for item in design.bom)
    budget = (f"<p><b>Budgetansatz inkl. 15 % Reserve: {money(planned_total)}</b></p>"
              if planned_total is not None else "<p>Budgetansatz nicht vollständig belegbar.</p>")
    return (
        "<h2>Stückliste</h2><table border='1' cellpadding='5'>"
        "<tr><th>Ref.</th><th>Bauteil</th><th>Anzahl</th><th>Einzelpreis</th><th>Position</th><th>Preisart</th></tr>"
        + rows + "</table>"
        f"<p><b>Bekannte Teilsumme: {money(info.subtotal_eur)}</b> · {escape(info.label_de())}</p>"
        + budget
        + "<p>Händlerpreise und Planpreise sind getrennt gekennzeichnet. Versand und Arbeitszeit "
          "sind nicht kalkuliert. Preisquellen stehen im CSV-Export.</p>")


def data_quality(design: SpeakerDesign) -> tuple[str, str]:
    """Headline and hint for the data-quality card, derived from what the project really contains."""
    cross = design.bundle.project.crossover
    needs_tweeter = design.tweeter is not None
    has_frd = cross.woofer_frd is not None and (not needs_tweeter or cross.tweeter_frd is not None)
    has_zma = cross.woofer_zma is not None and (not needs_tweeter or cross.tweeter_zma is not None)
    if has_frd and has_zma:
        return "FRD + ZMA vorhanden", "Weiche und Summe stützen sich auf Messdaten der Chassis."
    if has_frd or has_zma:
        return "FRD/ZMA unvollständig", "Nur ein Teil der Messdaten liegt vor; Weichenaussagen sind eingeschränkt."
    if design.provisional_crossover:
        return "nur T/S-Daten · vorläufige Weiche", "Ohne FRD/ZMA ist keine Aussage über 20 Hz–20 kHz belegt; nur Tiefton und Gehäuse sind berechnet."
    return "nur T/S-Daten", "Tiefton und Gehäuse sind berechnet; ohne FRD/ZMA bleibt der Frequenzgang oberhalb des Tieftons unbelegt."
