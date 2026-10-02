from __future__ import annotations

import json

import pytest

from lautsprecher_konstruktion.enclosure.registry import registry
from lautsprecher_konstruktion.export.package import export_project_package
from lautsprecher_konstruktion.library.store import ComponentLibrary
from lautsprecher_konstruktion.optimization.profiles import PROFILES
from lautsprecher_konstruktion.project.models import SpeakerProject
from lautsprecher_konstruktion.services.automatic import AutomaticDesignRequest, automatic_design
from lautsprecher_konstruktion.services.design import calculate_project


@pytest.fixture
def library(tmp_path):
    return ComponentLibrary(user_root=tmp_path / "user")


def test_library_search_import_and_deactivate(library, tmp_path):
    assert library.drivers("midwoofer")
    assert any(not item.is_test_data for item in library.entries("drivers"))
    assert any(item.is_test_data for item in library.entries("drivers"))
    first = library.entries("drivers", "130 mm")[0]
    library.set_active(first.id, False)
    assert not library.entries("drivers", "130 mm")
    library.set_active(first.id, True)
    assert library.entries("drivers", "130 mm")
    path = tmp_path / "custom.json"
    driver = first.driver.model_copy(update={"manufacturer": "Eigene Messung", "model": "Test 1"})
    path.write_text(json.dumps([driver.model_dump(mode="json")]), encoding="utf-8")
    assert library.import_file(path, "drivers") == 1
    assert library.entries("drivers", "Test 1")


def test_profiles_and_registry_have_explicit_limits(tmp_path):
    assert PROFILES["deep_bass"].weights["bass"] > PROFILES["compact"].weights["bass"]
    assert PROFILES["compact"].weights["size"] > PROFILES["neutral"].weights["size"]
    assert registry.get("bass_reflex").status == "SUPPORTED"
    assert registry.get("horn_tapped").status == "PLANNED"
    result = automatic_design(AutomaticDesignRequest(enclosure_preference="horn_tapped"),
                              ComponentLibrary(user_root=tmp_path / "user"))
    assert result.status == "impossible" and "PLANNED" in result.rejection_reasons[0]


def test_bookshelf_design_fit_score_project_export(library, tmp_path):
    request = AutomaticDesignRequest(project_name="Mein Regal", max_width_m=.23,
        max_height_m=.42, max_depth_m=.31)
    result = automatic_design(request, library)
    assert result.status == "ok" and 1 <= len(result.designs) <= 3
    for design in result.designs:
        assert design.bundle.cabinet.width_m <= request.max_width_m
        assert design.bundle.cabinet.height_m <= request.max_height_m
        assert design.bundle.cabinet.depth_m <= request.max_depth_m
        assert design.tweeter is not None and design.provisional_crossover
        assert design.breakdown and 0 <= design.score <= 100
        assert design.bom and all(issue.severity != "error" for issue in design.bundle.issues)
    top = result.designs[0]
    assert top.project.name.startswith("Mein Regal")
    loaded = SpeakerProject.model_validate_json(top.project.model_dump_json())
    assert calculate_project(loaded).cabinet == top.bundle.cabinet
    package = export_project_package(top.bundle, tmp_path)
    assert (package / "fertigung" / "fertigungsunterlagen.pdf").is_file()
    assert (package / "zeichnungen" / "gesamtzeichnung.svg").is_file()


def test_automatic_crossover_uses_standard_values_and_shared_bom(library):
    design = automatic_design(AutomaticDesignRequest(), library).designs[0]
    assert design.project.additional_drivers
    assert design.project.crossover.round_to_standard_values
    assert design.bundle.crossover is not None
    assert all(component.target_value_si is not None
               for component in design.bundle.crossover.components)
    descriptions = [item.description for item in design.bom]
    assert design.project.additional_drivers[0].model in " ".join(descriptions)
    assert any(item.category == "Hardware" for item in design.bom)


def test_component_csv_import_uses_si_columns(library, tmp_path):
    driver = library.drivers("midwoofer")[0]
    row = driver.model_dump(mode="json")
    row["manufacturer"] = "Eigene Messung"
    row["model"] = "CSV-Import"
    path = tmp_path / "measured.csv"
    import csv
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=row.keys(), delimiter=";")
        writer.writeheader()
        writer.writerow({key: "" if value is None else value for key, value in row.items()})
    assert library.import_file(path, "drivers") == 1
    assert library.entries("drivers", "CSV-Import")[0].driver.vas_m3 == driver.vas_m3


@pytest.mark.parametrize("kind", ("sealed", "bass_reflex", "passive_radiator", "bandpass_4"))
def test_supported_subwoofer_families(library, kind):
    result = automatic_design(AutomaticDesignRequest(speaker_type="Subwoofer",
        enclosure_preference=kind, max_width_m=.4, max_height_m=.6, max_depth_m=.65), library)
    assert result.status == "ok", result.rejection_reasons
    assert result.designs[0].project.enclosure.enclosure_type == kind


def test_impossible_request_rejected_with_suggestions(library):
    request = AutomaticDesignRequest(speaker_type="Subwoofer", max_width_m=.3,
        max_height_m=.3, max_depth_m=.2, sound_profile="deep_bass",
        target_f3_hz=20, target_spl_db=140)
    result = automatic_design(request, library)
    assert result.status == "impossible" and not result.designs
    assert result.rejection_reasons and result.suggested_constraint_changes
    assert any("Innenvolumen" in reason for reason in result.rejection_reasons)
    assert any("Zielpegel" in reason for reason in result.rejection_reasons)


def test_optional_outer_volume_constraint_is_hard_limit(library):
    request = AutomaticDesignRequest(max_outer_volume_l=16,
        max_width_m=.3, max_height_m=.5, max_depth_m=.4)
    result = automatic_design(request, library)
    assert result.status == "ok"
    assert all(d.bundle.cabinet.width_m*d.bundle.cabinet.height_m*
               d.bundle.cabinet.depth_m*1000 <= 16 for d in result.designs)


def test_automatic_design_can_be_cancelled(library):
    result = automatic_design(AutomaticDesignRequest(), library, cancelled=lambda: True)
    assert result.status == "cancelled" and not result.designs


def test_missing_tweeter_and_priced_budget_selection(tmp_path, library):
    empty = ComponentLibrary(bundled_root=tmp_path / "empty", user_root=tmp_path / "user2")
    woofer = library.drivers("midwoofer")[0]
    from lautsprecher_konstruktion.library.store import LibraryEntry
    empty.upsert(LibraryEntry(id="only:woofer", category="drivers", manufacturer="TESTDATEN",
        model=woofer.model, driver=woofer, is_test_data=True))
    result = automatic_design(AutomaticDesignRequest(way_count=2), empty)
    assert result.status == "impossible"
    assert any("Hocht�ner" in reason for reason in result.rejection_reasons)
    budget_result = automatic_design(AutomaticDesignRequest(budget=500), library)
    assert budget_result.status == "ok"
    assert budget_result.designs
    assert all(design.total_price_eur is not None and design.total_price_eur <= 500
               for design in budget_result.designs)
