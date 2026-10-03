import pytest

from lautsprecher_konstruktion.acoustics.sealed import solve_sealed
from lautsprecher_konstruktion.drivers.models import Driver


def test_sealed_reference_calculation() -> None:
    driver = Driver(
        manufacturer="Test",
        model="Reference",
        fs_hz=30.0,
        qts=0.35,
        vas_m3=0.050,
    )

    result = solve_sealed(driver, 0.707)

    assert result.box_volume_l == pytest.approx(16.23, rel=0.01)
    assert result.resonance_hz == pytest.approx(60.6, rel=0.01)
    assert result.f3_hz == pytest.approx(result.resonance_hz, rel=0.01)


def test_qtc_must_exceed_qts() -> None:
    driver = Driver(
        manufacturer="Test",
        model="Reference",
        fs_hz=30.0,
        qts=0.5,
        vas_m3=0.050,
    )
    with pytest.raises(ValueError):
        solve_sealed(driver, 0.5)
