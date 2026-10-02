from pathlib import Path

from lautsprecher_konstruktion.drivers.catalog import DriverCatalog


def test_example_catalog_loads() -> None:
    path = Path(__file__).parents[1] / "data" / "drivers.example.csv"
    catalog = DriverCatalog.load_csv(path)
    assert len(catalog.drivers) == 1
    assert catalog.drivers[0].model == "Demo Woofer"
    assert catalog.search("demo")
