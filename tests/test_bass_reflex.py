import pytest

from lautsprecher_konstruktion.acoustics.bass_reflex import round_port_length


def test_round_port_is_physically_positive() -> None:
    result = round_port_length(
        box_volume_m3=0.050,
        tuning_hz=35.0,
        port_diameter_m=0.10,
    )

    assert result.physical_length_m > 0
    assert result.port_area_m2 == pytest.approx(0.00785398, rel=1e-5)


def test_invalid_port_inputs_are_rejected() -> None:
    with pytest.raises(ValueError):
        round_port_length(
            box_volume_m3=0.0,
            tuning_hz=35.0,
            port_diameter_m=0.10,
        )
