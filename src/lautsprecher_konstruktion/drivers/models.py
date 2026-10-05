from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator


class Driver(BaseModel):
    """Validated loudspeaker driver data. Core convention: SI units only."""

    manufacturer: str
    model: str
    driver_type: Literal["woofer", "midwoofer", "midrange", "tweeter", "fullrange", "subwoofer", "passive_radiator", "compression_driver", "coaxial_driver"] = "woofer"
    fs_hz: float = Field(gt=0)
    qts: float = Field(gt=0)
    # Tweeter datasheets often omit Vas; never invent a value to fill a catalog row.
    vas_m3: float | None = Field(default=None, gt=0)

    qes: float | None = Field(default=None, gt=0)
    qms: float | None = Field(default=None, gt=0)
    re_ohm: float | None = Field(default=None, gt=0)
    le_h: float | None = Field(default=None, ge=0)
    sd_m2: float | None = Field(default=None, gt=0)
    xmax_m: float | None = Field(default=None, gt=0)
    power_rms_w: float | None = Field(default=None, gt=0)
    displacement_m3: float = Field(default=0.0, ge=0)
    nominal_impedance_ohm: float | None = Field(default=None, gt=0)
    outer_diameter_m: float | None = Field(default=None, gt=0)
    cutout_diameter_m: float | None = Field(default=None, gt=0)
    mounting_depth_m: float | None = Field(default=None, gt=0)
    nominal_size_m: float | None = Field(default=None, gt=0)
    moving_mass_kg: float | None = Field(default=None, gt=0)
    compliance_m_n: float | None = Field(default=None, gt=0)
    mechanical_resistance_n_s_m: float | None = Field(default=None, gt=0)
    force_factor_tm: float | None = Field(default=None, gt=0)
    xmech_m: float | None = Field(default=None, gt=0)
    sensitivity_db_1w_1m: float | None = None
    bolt_circle_diameter_m: float | None = Field(default=None, gt=0)
    bolt_count: int | None = Field(default=None, ge=0)
    bolt_hole_diameter_m: float | None = Field(default=None, gt=0)
    recommended_enclosure: str | None = None
    recommended_volume_m3: float | None = Field(default=None, gt=0)
    recommended_tuning_hz: float | None = Field(default=None, gt=0)
    min_frequency_hz: float | None = Field(default=None, gt=0)
    max_frequency_hz: float | None = Field(default=None, gt=0)
    price: float | None = Field(default=None, ge=0)
    currency: str | None = None
    product_url: HttpUrl | None = None
    datasheet_url: HttpUrl | None = None
    data_source_date: date | None = None

    source_name: str | None = None
    source_url: HttpUrl | None = None
    source_document: str | None = None

    @model_validator(mode="after")
    def validate_q_relationships(self) -> Driver:
        if self.qes is not None and self.qms is not None:
            calculated = (self.qes * self.qms) / (self.qes + self.qms)
            tolerance = max(0.02, self.qts * 0.08)
            if abs(calculated - self.qts) > tolerance:
                raise ValueError(
                    f"Qts={self.qts:.4f} is inconsistent with Qes/Qms "
                    f"(derived {calculated:.4f})."
                )
        return self

    def require_vas_m3(self) -> float:
        """Vas in m3; calculations that need it fail with a clear message instead of a TypeError."""
        if self.vas_m3 is None:
            raise ValueError(f"Vas fehlt für {self.manufacturer} {self.model}; Berechnung nicht möglich.")
        return self.vas_m3

    @property
    def vas_l(self) -> float | None:
        return None if self.vas_m3 is None else self.vas_m3 * 1000.0

    @property
    def xmax_mm(self) -> float | None:
        return None if self.xmax_m is None else self.xmax_m * 1000.0
