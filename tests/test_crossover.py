import pytest

from lautsprecher_konstruktion.crossover.passive import (
    first_order_two_way,
    l_pad,
    second_order_butterworth_two_way,
    second_order_linkwitz_riley_two_way,
)


def test_first_order_reference_values() -> None:
    design = first_order_two_way(1000.0, 8.0, 8.0)
    inductor, capacitor = design.components
    assert inductor.value_si * 1000 == pytest.approx(1.273, rel=0.01)
    assert capacitor.value_si * 1e6 == pytest.approx(19.89, rel=0.01)


def test_second_order_butterworth_reference_values() -> None:
    design = second_order_butterworth_two_way(1000.0, 8.0, 8.0)
    woofer_l = design.components[0]
    woofer_c = design.components[1]
    assert woofer_l.value_si * 1000 == pytest.approx(1.80, rel=0.01)
    assert woofer_c.value_si * 1e6 == pytest.approx(14.07, rel=0.01)


def test_linkwitz_riley_2_reference_values() -> None:
    design = second_order_linkwitz_riley_two_way(1000.0, 8.0, 8.0)
    assert design.components[0].value_si * 1000 == pytest.approx(2.546, rel=0.01)
    assert design.components[1].value_si * 1e6 == pytest.approx(9.947, rel=0.01)


def test_l_pad_keeps_nominal_input_impedance() -> None:
    series, parallel = l_pad(8.0, 6.0206)
    load_parallel = 1.0 / (1.0 / 8.0 + 1.0 / parallel.value_si)
    assert series.value_si + load_parallel == pytest.approx(8.0, rel=1e-5)
