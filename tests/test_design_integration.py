from pathlib import Path

from lautsprecher_konstruktion.drivers.models import Driver
from lautsprecher_konstruktion.export.package import export_project_package
from lautsprecher_konstruktion.project.models import (
    CrossoverConfig,
    EnclosureConfig,
    SpeakerProject,
)
from lautsprecher_konstruktion.services.design import calculate_project


def _driver() -> Driver:
    return Driver(
        manufacturer="Test",
        model="Woofer 8",
        fs_hz=32.0,
        qts=0.36,
        vas_m3=0.058,
        re_ohm=5.8,
        le_h=0.0011,
        nominal_impedance_ohm=8.0,
        cutout_diameter_m=0.230,
        mounting_depth_m=0.115,
        displacement_m3=0.0018,
    )


def test_bass_reflex_project_produces_manufacturing_package(tmp_path: Path) -> None:
    project = SpeakerProject(
        name="Integration Test",
        driver=_driver(),
        enclosure=EnclosureConfig(
            enclosure_type="bass_reflex",
            target_volume_l=45.0,
            tuning_hz=35.0,
            external_width_mm=340.0,
            external_height_mm=560.0,
            panel_thickness_mm=18.0,
            port_type="round",
            port_diameter_mm=80.0,
            brace_quantity=1,
        ),
        crossover=CrossoverConfig(
            enabled=True,
            topology="butterworth_2",
            crossover_hz=2500.0,
            woofer_impedance_ohm=8.0,
            tweeter_impedance_ohm=8.0,
            tweeter_attenuation_db=2.0,
            add_woofer_zobel=True,
        ),
    )

    bundle = calculate_project(project)
    assert bundle.port is not None
    assert bundle.crossover is not None
    assert len(bundle.crossover.components) >= 8
    assert bundle.cabinet.depth_m > 0.2

    package = export_project_package(bundle, tmp_path)
    assert (package / "fertigungsunterlagen.pdf").exists()
    assert (package / "gehaeuse_zeichnung.svg").exists()
    assert (package / "frontplatte.dxf").exists()
    assert (package / "frequenzweiche_schema.svg").exists()
    assert (package / "stueckliste.csv").exists()
    assert (package / "zuschnittliste.csv").exists()
    assert (package / "project.json").exists()
