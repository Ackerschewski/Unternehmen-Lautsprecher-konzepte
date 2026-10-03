from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from lautsprecher_konstruktion.crossover.measurements import FrequencyResponseData, ImpedanceData
from lautsprecher_konstruktion.drivers.models import Driver
from lautsprecher_konstruktion.enclosure.layout import FrontElement


class EnclosureConfig(BaseModel):
    enclosure_type: str = "sealed"
    target_qtc: float = Field(default=0.707, gt=0)
    target_volume_l: float | None = Field(default=None, gt=0)
    tuning_hz: float | None = Field(default=None, gt=0)
    port_type: Literal["round", "slot"] = "round"
    port_diameter_mm: float = Field(default=75.0, gt=0)
    slot_width_mm: float = Field(default=200.0, gt=0)
    slot_height_mm: float = Field(default=30.0, gt=0)
    rear_volume_l: float = Field(default=25.0, gt=0)
    rear_tuning_hz: float | None = Field(default=None, gt=0)
    rear_port_diameter_mm: float = Field(default=75.0, gt=0)
    aperiodic_resistance_pa_s_m3: float | None = Field(default=None, gt=0)
    baffle_wing_depth_mm: float = Field(default=150.0, ge=0)
    cardioid_delay_ms: float = Field(default=0.5, ge=0, le=10)
    isobaric_wiring: Literal["series", "parallel"] = "series"
    isobaric_gap_mm: float = Field(default=20.0, ge=10.0)
    radiator_sd_cm2: float = Field(default=350.0, gt=0)
    radiator_mms_g: float = Field(default=80.0, gt=0)
    radiator_fs_hz: float = Field(default=20.0, gt=0)
    radiator_qms: float = Field(default=5.0, gt=0)
    radiator_xmax_mm: float = Field(default=12.0, gt=0)
    radiator_cutout_mm: float = Field(default=230.0, gt=0)
    radiator_depth_mm: float = Field(default=60.0, gt=0)
    input_power_w: float = Field(default=1.0, gt=0)
    ql: float | None = Field(default=None, gt=0)
    qa: float | None = Field(default=None, gt=0)
    qp: float | None = Field(default=None, gt=0)

    external_width_mm: float = Field(default=350.0, gt=0)
    external_height_mm: float = Field(default=600.0, gt=0)
    panel_thickness_mm: float = Field(default=18.0, gt=0)
    front_thickness_mm: float | None = Field(default=None, gt=0)
    back_thickness_mm: float | None = Field(default=None, gt=0)
    top_thickness_mm: float | None = Field(default=None, gt=0)
    bottom_thickness_mm: float | None = Field(default=None, gt=0)
    front_layers: int = Field(default=1, ge=1, le=3)
    additional_displacement_l: float = Field(default=0.0, ge=0)

    brace_quantity: int = Field(default=1, ge=0)
    brace_border_mm: float = Field(default=35.0, gt=0)

    @model_validator(mode="after")
    def check_enclosure_type(self) -> EnclosureConfig:
        from lautsprecher_konstruktion.enclosure.registry import registry
        if self.enclosure_type not in {entry.id for entry in registry.all()}:
            raise ValueError(f"Unbekannter Gehäusetyp: {self.enclosure_type}")
        return self


class CrossoverConfig(BaseModel):
    enabled: bool = True
    topology: Literal["first_order", "butterworth_2", "linkwitz_riley_2"] = "butterworth_2"
    crossover_hz: float = Field(default=2500.0, gt=0)
    woofer_impedance_ohm: float = Field(default=8.0, gt=0)
    tweeter_impedance_ohm: float = Field(default=8.0, gt=0)
    tweeter_attenuation_db: float = Field(default=0.0, ge=0)
    add_woofer_zobel: bool = False
    round_to_standard_values: bool = False
    woofer_frd: FrequencyResponseData | None = None
    tweeter_frd: FrequencyResponseData | None = None
    woofer_zma: ImpedanceData | None = None
    tweeter_zma: ImpedanceData | None = None


class ProjectAccessory(BaseModel):
    category: str
    reference: str
    description: str
    quantity: int = Field(ge=1)
    specification: str = ""
    notes: str = ""
    unit_price_eur: float | None = Field(default=None, ge=0)
    price_source_url: str = ""


class SpeakerProject(BaseModel):
    schema_version: int = 3
    name: str = "Neues Lautsprecherprojekt"
    revision: str = "V-02.05.00"
    material: str = "Birke Multiplex"
    driver: Driver
    additional_drivers: tuple[Driver, ...] = ()
    tweeter_name: str = "Tweeter"
    enclosure: EnclosureConfig = EnclosureConfig()
    crossover: CrossoverConfig = CrossoverConfig()
    front_elements: tuple[FrontElement, ...] = ()
    accessories: tuple[ProjectAccessory, ...] = ()
    notes: str = ""

    @model_validator(mode="before")
    @classmethod
    def migrate_v1(cls, data: object) -> object:
        if isinstance(data, dict) and data.get("schema_version", 1) < 3:
            return {**data, "schema_version": 3}
        return data
