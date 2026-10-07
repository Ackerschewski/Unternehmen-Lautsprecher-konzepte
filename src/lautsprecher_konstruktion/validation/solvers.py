"""Descriptors of all registered solvers: equations, sources, limits and the trust level that is granted.

The granted level is a decision, not a measurement: it must not exceed what the reference cases earn
(checked by the tests), and it can be lower when a model contains approximations that matter to the user.
"""
from __future__ import annotations

from lautsprecher_konstruktion.enclosure.registry import registry
from lautsprecher_konstruktion.validation.trust import ModelLimitation, SolverDescriptor, TrustLevel

CONVENTIONS = (
    "Vb = Netto-Innenvolumen (brutto minus Verdrängung). F3 = −3-dB-Punkt gegen den Pegel im Band 150–300 Hz (Median); "
    "beim Bandpass gegen das Maximum. Fb = Helmholtz-Frequenz des Ports mit Mündungskorrektur. SPL = Halbraum (2π), 1 m, 2,83 V "
    "bzw. angegebene Leistung. Einheiten intern SI."
)
SMALL_SIGNAL = ModelLimitation("Aussteuerung", "Linearisiertes Kleinsignalmodell: Treibernichtlinearität, Erwärmung und Kompression sind nicht enthalten.")
HALF_SPACE = ModelLimitation("Abstrahlung", "Halbraum-Monopol ohne Kantenbeugung, Raum und Richtwirkung.")
LOSSES = ModelLimitation("Verluste", "Gehäuse- und Portverluste sind Standardannahmen (Q-Werte), keine Messwerte.")

_LINE_LIMITS = (
    SMALL_SIGNAL, HALF_SPACE,
    ModelLimitation("Wellenausbreitung", "Nur ebene Wellen in segmentierten Kanälen; Querresonanzen und Biegungsverluste fehlen."),
    ModelLimitation("Dämmung", "Die Dämmwirkung ist ein pauschaler Dämpfungsfaktor je Zone, ohne Schallgeschwindigkeitsänderung."),
    ModelLimitation("Mundlast", "Strahlungsimpedanz des freien Rohrendes für kleine ka; Wandnähe und Faltung des Mundes sind nicht berücksichtigt."),
    ModelLimitation("Geometrie", "Der Berechnungskern ist gegen geschlossene Formeln geprüft; die Ableitung der Segmente aus dem Gehäuse (Faltung, Verjüngung) nur auf Konsistenz."),
)


def _d(solver_id: str, family: str, trust: TrustLevel, equations: str, sources: tuple[str, ...],
       limitations: tuple[ModelLimitation, ...]) -> SolverDescriptor:
    return SolverDescriptor(solver_id, family, "1", trust, equations, sources, limitations, CONVENTIONS)


_SMALL72 = "Small (1972), Closed-Box Loudspeaker Systems, J. AES 20"
_SMALL73 = "Small (1973), Vented-Box Loudspeaker Systems, J. AES 21"
_THIELE = "Thiele (1971), Loudspeakers in Vented Boxes, J. AES 19"
_OLSON = "Olson (1951), Elements of Acoustical Engineering"
_BERANEK = "Beranek (1954), Acoustics"
_LEVINE = "Levine und Schwinger (1948), On the radiation of sound from an unflanged circular pipe, Phys. Rev. 73"

_E = TrustLevel.EXPERIMENTAL
_F = TrustLevel.FORMULA_VERIFIED
_R = TrustLevel.REFERENCE_VERIFIED


def _build() -> tuple[SolverDescriptor, ...]:
    d: list[SolverDescriptor] = [
        _d("sealed", "Geschlossen", _R, "Zweiter Ordnung Hochpass aus Fs, Qts, Vas und Vb; F3 aus dem berechneten Frequenzgang.",
           (_SMALL72,), (SMALL_SIGNAL, HALF_SPACE, LOSSES)),
        _d("bass_reflex", "Bassreflex", _R, "Vierter Ordnung Hochpass aus Treiber, Boxnachgiebigkeit und Portmasse (Netzwerklösung).",
           (_SMALL73, _THIELE), (SMALL_SIGNAL, HALF_SPACE, LOSSES,
                                 ModelLimitation("Port", "Portmündungskorrektur 1,46·r (Standardannahme); Portströmungsverluste und Turbulenz sind nicht modelliert."))),
        _d("aperiodic", "Aperiodisch", _F, "Geschlossenes Gehäuse mit strömungsresistivem Vent; Leckage-Q nach Small.",
           (_SMALL73,), (SMALL_SIGNAL, HALF_SPACE,
                         ModelLimitation("Vent", "Ventmasse wird vernachlässigt; der Widerstand folgt aus einer Auslegungsregel, nicht aus gemessenem Material."))),
        _d("passive_radiator", "Passivmembran", _F, "Bassreflex-Netzwerk, bei dem der Port durch eine Passivmembran (Masse, Nachgiebigkeit, Verlust) ersetzt ist.",
           (_OLSON, "Small (1974), Passive-Radiator Loudspeaker Systems, J. AES 22"), (SMALL_SIGNAL, HALF_SPACE, LOSSES,
                                                                                   ModelLimitation("Membran", "Die Herstellerdaten der Passivmembran (Fs, Qms, Masse) werden als gegeben angenommen."))),
        _d("bandpass_4", "Bandpass 4. Ordnung", _F, "Rückkammer als Nachgiebigkeit, Frontkammer mit Port; abgestrahlt wird der Portfluss.",
           ("Geddes (1989), Loudspeaker bandpass enclosures", _SMALL73), (SMALL_SIGNAL, HALF_SPACE,
                                                                      ModelLimitation("Verluste", "Verlustfrei gerechnet; Kammer- und Portverluste fehlen."))),
        _d("bandpass_6_parallel", "Bandpass 6. Ordnung parallel", _E, "Zwei Kammern mit je einem abstrahlenden Port; die Portflüsse werden kohärent summiert.",
           ("Geddes (1989), Loudspeaker bandpass enclosures",), (SMALL_SIGNAL, HALF_SPACE,
                                                               ModelLimitation("Referenz", "Nur der Grenzfall mit geschlossenem Rückvent ist gegen die 4. Ordnung geprüft, nicht die Kopplung beider Ports."),
                                                               ModelLimitation("Summierung", "Beide Portausgänge werden als gleicher Ort mit fester Laufzeit angenommen."))),
        _d("bandpass_6_series", "Bandpass 6. Ordnung seriell", _E, "Zwei gekoppelte Kammern (Knotenmodell), nur der äußere Port strahlt ab.",
           ("Geddes (1989), Loudspeaker bandpass enclosures",), (SMALL_SIGNAL, HALF_SPACE,
                                                               ModelLimitation("Referenz", "Nur der Grenzfall mit geschlossenem Innenkanal ist gegen die 4. Ordnung geprüft."),
                                                               ModelLimitation("Verluste", "Portverluste mit pauschalem Q = 7."))),
    ]
    iso_limits = (SMALL_SIGNAL, HALF_SPACE, LOSSES,
                  ModelLimitation("Koppelkammer", "Die Nachgiebigkeit der Koppelkammer zwischen den Chassis wird vernachlässigt (ideales Tandem)."))
    d += [
        _d("isobaric_sealed", "Isobarisch geschlossen", _F, "Ersatztreiber (doppelte Masse, halbes Vas, gleiches Fs und Q) in einem geschlossenen Gehäuse.", (_OLSON, _SMALL72), iso_limits),
        _d("compound_push_pull", "Compound / Push-Pull", _F, "Wie isobarisch, mit paralleler Verschaltung und gleichem Ersatztreiber.", (_OLSON, _SMALL72), iso_limits),
        _d("isobaric_vented", "Isobarisch Bassreflex", _F, "Ersatztreiber im Bassreflex-Netzwerk.", (_OLSON, _SMALL73), iso_limits),
    ]
    for solver_id, family in (("transmission_line_closed", "Transmission Line geschlossen"), ("transmission_line_open", "Transmission Line offen"),
                              ("transmission_line_tapered", "Transmission Line verjüngt"), ("tqwt", "TQWT"), ("labyrinth", "Labyrinth")):
        d.append(_d(solver_id, family, _E, "Kettenmatrix ebener Wellen über die gefalteten Kanalabschnitte, Mundlast eines freien Rohrendes.",
                    (_OLSON, _BERANEK, _LEVINE), _LINE_LIMITS))
    d.append(_d("mltl", "Mass Loaded Transmission Line", _E, "Kanal wie Transmission Line, Ausgang als Portmasse mit Verlust.",
                (_OLSON, _BERANEK), (*_LINE_LIMITS, ModelLimitation("Referenz", "Die Portlast des Ausgangs ist nicht gegen eine geschlossene Formel geprüft."))))
    for solver_id, family in (("horn_rear", "Rearloaded Horn"), ("horn_folded", "Folded Horn"), ("horn_scoop", "Scoop"), ("horn_exponential", "Exponentialhorn"),
                              ("horn_tractrix", "Tractrixhorn"), ("horn_conical", "Konisches Horn"), ("horn_hyperbolic", "Hyperbolisches Horn")):
        d.append(_d(solver_id, family, _E, "Segmentiertes Horn als Kette ebener Wellen; Hornkontur aus der Familiengleichung.",
                    (_OLSON, _BERANEK, _LEVINE), (*_LINE_LIMITS, ModelLimitation("Hornkontur", "Die Kontur wird durch Abschnitte angenähert; der Kern ist gegen die Olson-Halsimpedanz geprüft."))))
    d += [
        _d("horn_front", "Frontlasthorn", _E, "Exponentialhorn vor der Membran, geschlossenes Rückvolumen, Mundlast eines freien Rohrendes.",
           (_OLSON, _LEVINE), (SMALL_SIGNAL, HALF_SPACE,
                               ModelLimitation("Wellenausbreitung", "Ebene Wellen; Halsübergang und Richtwirkung des Horns fehlen."),
                               ModelLimitation("Mundlast", "Freies Rohrende; ein Horn vor einer Wand oder in einer Ecke hat eine andere Mundlast."))),
        _d("horn_tapped", "Tapped Horn", _E, "Knotennetz mit zwei Einspeisepunkten der beiden Membranseiten auf dem gefalteten Pfad.",
           (_OLSON,), (SMALL_SIGNAL, HALF_SPACE,
                       ModelLimitation("Referenz", "Es gibt keinen unabhängigen Referenzfall; das Netzmodell ist nur auf Konsistenz geprüft."),
                       ModelLimitation("Verluste", "Pauschaler Dämpfungsfaktor 0,025 im Kanal."))),
        _d("infinite_baffle", "Infinite Baffle", _F, "Treiber mit großem geschlossenem Rückraum (reine Nachgiebigkeit) in einer unendlichen Schallwand.",
           (_SMALL72,), (SMALL_SIGNAL, HALF_SPACE, ModelLimitation("Rückraum", "Der Rückraum wird als dichte, reine Nachgiebigkeit angenommen (mindestens 10·Vas)."))),
        _d("open_baffle", "Open Baffle", _F, "Dipol mit Weglängenunterschied D zwischen Vorder- und Rückseite: Pegel gegen Unendlich-Schallwand |sin(kD/2)|.",
           (_OLSON,), (SMALL_SIGNAL, ModelLimitation("Beugung", "Weg um die Kante als einzelner Weglängenunterschied; Kantenbeugung, Richtwirkung und Raum fehlen."))),
        _d("dipole", "Dipol / H-Frame", _F, "Wie Open Baffle, mit verlängertem Weg durch die Seitenflügel.",
           (_OLSON, "Linkwitz, Dipole Loudspeakers"), (SMALL_SIGNAL, ModelLimitation("Beugung", "Nur der kürzeste Weg um die Kanten; Flügelresonanzen fehlen."))),
        _d("cardioid", "Passiv-Kardioid", _E, "Zwei räumlich getrennte Quellen (Membran und Rückvent) mit fester Verzögerung; Vorder- und Rückpegel.",
           (_OLSON,), (SMALL_SIGNAL, HALF_SPACE,
                       ModelLimitation("Referenz", "Kein unabhängiger Referenzfall; das Zweiquellenmodell ist nur auf Konsistenz geprüft."),
                       ModelLimitation("Richtwirkung", "Nur Vorne/Hinten, nicht das volle Polardiagramm."))),
    ]
    return tuple(d)


SOLVER_DESCRIPTORS: dict[str, SolverDescriptor] = {item.solver_id: item for item in _build()}


def descriptor(enclosure_type: str) -> SolverDescriptor:
    """Descriptor of the solver that handles an enclosure type (the registry id is the solver id)."""
    return SOLVER_DESCRIPTORS[registry.get(enclosure_type).solver_id or enclosure_type]


def trust_of(enclosure_type: str) -> TrustLevel:
    return descriptor(enclosure_type).trust
