"""Status banner text of a design: type, size, key acoustic figure and only real warnings or errors."""
from __future__ import annotations

from lautsprecher_konstruktion.enclosure.registry import registry
from lautsprecher_konstruktion.services.automatic import SpeakerDesign
from lautsprecher_konstruktion.validation.solvers import trust_of
from lautsprecher_konstruktion.validation.trust import TrustLevel


def key_figure(design: SpeakerDesign) -> str:
    """F3, tuning (Fb) and Qtc where the model provides them; empty when nothing was calculated."""
    bundle = design.bundle
    parts: list[str] = []
    if bundle.sealed is not None:
        parts += [f"F3 {bundle.sealed.f3_hz:.0f} Hz", f"Qtc {bundle.sealed.target_qtc:.2f}".replace(".", ",")]
    elif bundle.vented_response is not None and bundle.vented_response.f3_hz is not None:
        parts.append(f"F3 {bundle.vented_response.f3_hz:.0f} Hz")
        if bundle.port is not None and bundle.port.tuning_hz:
            parts.append(f"Fb {bundle.port.tuning_hz:.0f} Hz")
    return " · ".join(parts)


def banner(design: SpeakerDesign) -> tuple[str, str]:
    """(role, text): zero counters are never shown, errors lock the export and say why."""
    bundle = design.bundle
    cab = bundle.cabinet
    parts = [registry.get(design.project.enclosure.enclosure_type).label,
             f"{cab.width_m*1000:.0f}×{cab.height_m*1000:.0f}×{cab.depth_m*1000:.0f} mm"]
    figure = key_figure(design)
    parts.append(figure if figure else "Tiefbass nicht berechenbar")
    experimental = trust_of(design.project.enclosure.enclosure_type) is TrustLevel.EXPERIMENTAL
    if experimental:
        parts.append("experimentelles Modell")
    errors = [issue.message for issue in bundle.issues if issue.severity == "error"]
    warnings = len(bundle.warnings)
    if errors:
        parts.append(f"{len(errors)} Fehler · Export gesperrt: {errors[0]}")
    if warnings:
        parts.append(f"{warnings} Hinweis" + ("e" if warnings != 1 else ""))
    role = "danger" if errors else "warning" if warnings or experimental else "success"
    return role, " · ".join(parts)
