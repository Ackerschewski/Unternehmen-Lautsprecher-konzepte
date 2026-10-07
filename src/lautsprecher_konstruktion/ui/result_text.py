"""HTML text blocks for the result view (details and bill of materials); pure functions, no widgets."""
from __future__ import annotations

from html import escape

from lautsprecher_konstruktion.enclosure.registry import registry
from lautsprecher_konstruktion.export.pricing import budget_cost
from lautsprecher_konstruktion.export.summary import grouped
from lautsprecher_konstruktion.presentation import component_text, de, price_kind
from lautsprecher_konstruktion.services.automatic import SpeakerDesign
from lautsprecher_konstruktion.services.price_status import price_info
from lautsprecher_konstruktion.services.variant_metrics import (
    METRIC_NAMES_DE,
    coverage_label,
    metrics_of,
    model_status,
)


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
        lines.append(f"<h3>Zielerfüllung {design.score:.0f} % · aus {len(design.breakdown)} belegten Kriterien</h3>"
                     "<p>Keine Qualitätsfreigabe: nicht belegbare Kriterien fließen nicht ein, es gibt keine ergänzten Werte.</p>")
        for metric in design.breakdown:
            lines.append(f"<p><b>{METRIC_NAMES_DE.get(metric.name, metric.name)}</b> {metric.value:.0f}/100 "
                         f"(Gewicht {metric.weight:g})<br>{escape(metric.evidence)}</p>")
        missing = {"headroom", "port", "delay", "flatness"} - {metric.name for metric in design.breakdown}
        if bundle.port is None:
            missing.discard("port")
        if missing:
            lines.append("<p><i>Nicht bewertet: " + ", ".join(METRIC_NAMES_DE[key] for key in sorted(missing))
                         + ". Nicht verfügbare Werte werden nicht ergänzt.</i></p>")
        m = metrics_of(design)
        lines.append(f"<p><b>Zusätzlich, nicht im Score:</b> Datenabdeckung {m.coverage_percent} % · "
                     f"Bauaufwand {m.effort_panels} Platten</p>")
    lines.append("<h3>Warum dieser Entwurf?</h3><ul>"+
        "".join(f"<li>{escape(reason)}</li>" for reason in design.reasons)+"</ul>")
    if design.provisional_crossover:
        lines.append("<p><b>Vorläufiger Frequenzweichenentwurf:</b> Für eine Endabstimmung "
            "sind FRD/ZMA-Messungen am aufgebauten Lautsprecher nötig.</p>")
    if bundle.warnings:
        lines.append("<h3>Hinweise</h3><ul>"+
            "".join(f"<li>{escape(message)}</li>" for message in bundle.warnings)+"</ul>")
    return "".join(lines)


_BADGES = {"retail": ("Händlerpreis", "success"), "Materialreferenz": ("Materialreferenz", "accent"),
           "Planpreis": ("Planpreis", "warning"), "fehlt": ("Preis fehlt", "danger")}


def price_badge(item: object, colors: dict[str, str]) -> str:
    """Coloured badge for the price kind of a BOM position (never colour only: the word is always there)."""
    kind = getattr(item, "price_kind", "retail") if getattr(item, "unit_price_eur", None) is not None else "fehlt"
    text, role = _BADGES.get(kind, (price_kind(kind), "textSecondary"))
    colour = colors.get(role) or colors.get("textSecondary") or "inherit"
    return (f"<span style='color:{colour}; font-weight:600'>● {escape(text)}</span>")


def bom_html(design: SpeakerDesign, colors: dict[str, str] | None = None) -> str:
    """German bill of materials grouped by function, price badge per line, honest coverage summary."""
    colors = colors or {}
    info = price_info(design.bom)
    planned_total = budget_cost(design.bom)

    def money(value: float | None) -> str:
        return f"{de(value, 2)} €" if value is not None else "–"

    body: list[str] = []
    for name, items in grouped(design.bom):
        subtotal = sum(i.line_total_eur for i in items if i.line_total_eur is not None)
        unknown = sum(1 for i in items if i.line_total_eur is None)
        note = f" · {unknown} ohne Preis" if unknown else ""
        body.append(f"<tr><td colspan='6' bgcolor='{colors.get('band', 'transparent')}'><b>{escape(name)}</b> · Zwischensumme "
                    f"{money(subtotal) if subtotal else '–'}{note}</td></tr>")
        for item in items:
            body.append(
                f"<tr><td>{escape(item.reference)}</td><td>{escape(component_text(item.description))}</td>"
                f"<td align='right'>{item.quantity}</td><td align='right'>{money(item.unit_price_eur)}</td>"
                f"<td align='right'>{money(item.line_total_eur)}</td><td>{price_badge(item, colors)}</td></tr>")
    budget = (f"<p><b>Budgetansatz inkl. 15 % Reserve: {money(planned_total)}</b></p>"
              if planned_total is not None else "<p>Budgetansatz nicht vollständig belegbar.</p>")
    return (
        "<h2>Stückliste</h2><table border='1' cellpadding='5' cellspacing='0'>"
        "<tr><th>Ref.</th><th>Bauteil</th><th>Anzahl</th><th>Einzelpreis</th><th>Position</th><th>Preisart</th></tr>"
        + "".join(body) + "</table>"
        f"<p><b>Bekannte Teilsumme: {money(info.subtotal_eur)}</b> · {escape(info.label_de())}</p>"
        + budget
        + "<p>Händlerpreise, Materialreferenzen und Planpreise sind getrennt gekennzeichnet. Versand und Arbeitszeit "
          "sind nicht kalkuliert. Preisquellen stehen im CSV-Export.</p>")


def data_quality(design: SpeakerDesign) -> tuple[str, str]:
    """Headline = data coverage in words and percent; hint = the model status behind it (kept apart on purpose)."""
    percent = metrics_of(design).coverage_percent
    return f"{coverage_label(percent).capitalize()} · {percent} %", f"Datenabdeckung. Modellstatus: {model_status(design)}"
