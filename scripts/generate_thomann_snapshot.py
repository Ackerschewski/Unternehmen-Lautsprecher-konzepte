"""Reproducible, manually checked Thomann catalog snapshot (no live scraping)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATE = "2026-10-02"

# Name|EUR; only regular new-stock products with a visible shop price.
GROUPS = {
    "visaton": ("https://www.thomann.de/de/visaton_lautsprecher_komponenten.html", """
BG 20 - 8 Ohm|35
FRS 8M|13.70
W 200 8 Ohm|30
W 130 X|54
B 100|88
HTH 8.7|64
FRS 10 WP-8 Black|47
BG 17 8 Ohm|21.80
FR 58|8.20
FRS 10 WP 4 Ohm Black|47
BF 45 / 4 Ohm|15.80
Dx 10-4|60
FRS 7-8 Ohm|11.70
W250-8|49
FRS 5 X|11.60
FRS 7-4 Ohm|11.70
KT 100 V|25
BF 45 / 8 Ohms|15.80
WF 130 ND|119
FRWS 4 ND|13
PAW 38|255
FRS 10 WP 4 Ohm WH|47
PAW 30 ND|259
FRS 5|10.70
FRS 10 WP-8 White|47
"""),
    "faitalpro": ("https://www.thomann.de/de/faitalpro_lautsprecher_komponenten.html?ls=50&pg=1", """
6FE200 8 Ohms|39
8FE200 8 Ohms|44
4FE35 8 Ohms|19
15PR400 8 Ohms|219
4FE32 8 Ohms|29
6PR160 8 Ohms|109
18FH510 8 Ohms|269
10HP1020 8 Ohms|269
15HX500 8 Ohms|549
18XL1700 8 Ohms|549
6HX150 8 Ohms|198
12HP1060 8 Ohms|339
8PR200 8 Ohms|159
6RS140 8 Ohms|115
21XL3000 8 Ohms|1049
18HP1060 8 Ohms|389
18XL1600 8 Ohms|549
8HX200 8 Ohms|329
10HX240 8 Ohms|389
HF141 8 Ohms|259
15XL1400 8 Ohms|489
12HX500 8 Ohms|549
12XL1200 8 Ohms|398
"""),
    "eminence": ("https://www.thomann.de/de/eminence.html", """
Legend 1028K|159
GA10-SC64|139
GA-SC64|165
Kappa-12A|185
Legend BP102-8|129
Legend 1518|179
Legend 1058|125
APT80 V2|59
Kappa Pro-10A|189
Kappalite 3012LF|313
Delta-15LFC|198
Delta-12B - 16 Ohm|145
Kappa Pro-15A|209
Kappa Pro-15LF-2|249
Delta-15LFA|179
Kappa-15LFA|229
Delta-15A|175
Delta-12LFA|165
Delta-12A 8 Ohm|149
Alpha-6A - 8 Ohm|89
Beta-8A|109
Beta-10A|123
Alpha-10A - 8 Ohm|115
Kappa Pro-18LFA|298
"""),
    "mixed": ("https://www.thomann.de/de/lautsprecher_komponenten.html", """
B&C|18TBX100 8 Ohm|279
B&C|DE 250|93
B&C|21SW152|675
B&C|18DS115|525
RCF|LF18G401|317
Fane|Sovereign 8-225|59
the box|Speaker 15-300/8-A|85
the box|Speaker 12-280/8-A|59
the box|Speaker 12-280/8-W|69
the box|Speaker 10-250/8-A|49
Celestion|CDX1-1070|30
Beyma|CP-21/F Speaker|123
"""),
}

full_driver = {
    "manufacturer": "FaitalPRO", "model": "6FE200 8 Ohms", "driver_type": "midwoofer",
    "nominal_size_m": 0.16, "fs_hz": 120, "qts": 0.67, "qes": 0.75, "qms": 6.2,
    "vas_m3": 0.0036, "re_ohm": 5.9, "le_h": 0.0004, "sd_m2": 0.0131,
    "xmax_m": 0.00467, "power_rms_w": 130, "displacement_m3": 0.00045,
    "nominal_impedance_ohm": 8, "outer_diameter_m": 0.1674,
    "cutout_diameter_m": 0.144, "mounting_depth_m": 0.077,
    "moving_mass_kg": 0.0115, "force_factor_tm": 8.2,
    "bolt_circle_diameter_m": 0.154, "sensitivity_db_1w_1m": 95,
    "min_frequency_hz": 85, "max_frequency_hz": 6000,
    "source_name": "FaitalPRO Herstellerdaten",
    "source_url": "https://faitalpro.com/products/files/6FE200/8/6FE200_datasheet_8.pdf",
    "datasheet_url": "https://faitalpro.com/products/files/6FE200/8/6FE200_datasheet_8.pdf",
    "data_source_date": DATE,
    "source_document": "T/S und Maße aus FaitalPRO-Datenblatt; Preis separat bei Thomann geprüft.",
}

FAITAL_TECH = {"6FE200 8 Ohms": full_driver}
for model, code, values in (
    ("8FE200 8 Ohms", "8FE200", {"nominal_size_m": .2, "fs_hz": 80, "qts": .63,
      "qes": .66, "qms": 13, "vas_m3": .0161, "re_ohm": 5.9, "le_h": .00044, "sd_m2": .0209,
      "xmax_m": .00467, "power_rms_w": 130, "displacement_m3": .0006,
      "outer_diameter_m": .2092, "cutout_diameter_m": .178, "mounting_depth_m": .089,
      "moving_mass_kg": .015, "force_factor_tm": 8.2, "bolt_circle_diameter_m": .1969,
      "sensitivity_db_1w_1m": 95, "min_frequency_hz": 60, "max_frequency_hz": 5000}),
    ("15PR400 8 Ohms", "15PR400", {"nominal_size_m": .38, "fs_hz": 35, "qts": .32,
      "qes": .34, "qms": 6, "vas_m3": .2489, "re_ohm": 5.1, "le_h": .00072, "sd_m2": .0857,
      "xmax_m": .00575, "power_rms_w": 400, "displacement_m3": .0037,
      "outer_diameter_m": .393, "cutout_diameter_m": .356, "mounting_depth_m": .165,
      "moving_mass_kg": .0852, "force_factor_tm": 16.7, "bolt_circle_diameter_m": .374,
      "sensitivity_db_1w_1m": 99, "min_frequency_hz": 35, "max_frequency_hz": 4000}),
    ("4FE35 8 Ohms", "4FE35", {"nominal_size_m": .1, "fs_hz": 100, "qts": .83,
      "qes": 1.04, "qms": 4.2, "vas_m3": .0024, "re_ohm": 6.5, "le_h": .0001, "sd_m2": .00519,
      "xmax_m": .00273, "power_rms_w": 30, "displacement_m3": .00015,
      "outer_diameter_m": .12985, "cutout_diameter_m": .0915, "mounting_depth_m": .0583,
      "moving_mass_kg": .0039, "force_factor_tm": 3.9, "bolt_circle_diameter_m": .11526,
      "sensitivity_db_1w_1m": 91, "min_frequency_hz": 90, "max_frequency_hz": 20000}),
    ("4FE32 8 Ohms", "4FE32", {"nominal_size_m": .1, "fs_hz": 100, "qts": .61,
      "qes": .70, "qms": 4.9, "vas_m3": .0023, "re_ohm": 6.5, "le_h": .00018,
      "sd_m2": .00519, "xmax_m": .00273, "power_rms_w": 30,
      "displacement_m3": .000075, "outer_diameter_m": .12985,
      "cutout_diameter_m": .0915, "mounting_depth_m": .0498,
      "moving_mass_kg": .0042, "force_factor_tm": 4.8,
      "bolt_circle_diameter_m": .11526, "sensitivity_db_1w_1m": 91,
      "min_frequency_hz": 90, "max_frequency_hz": 20000}),
    ("18FH510 8 Ohms", "18FH510", {"nominal_size_m": .46, "fs_hz": 30, "qts": .29,
      "qes": .30, "qms": 13.6, "vas_m3": .4119, "re_ohm": 5.1, "le_h": .00106,
      "sd_m2": .1207, "xmax_m": .00925, "power_rms_w": 600,
      "displacement_m3": .0061, "outer_diameter_m": .46,
      "cutout_diameter_m": .421, "mounting_depth_m": .2015,
      "moving_mass_kg": .139, "force_factor_tm": 21,
      "bolt_circle_diameter_m": .44, "sensitivity_db_1w_1m": 98,
      "min_frequency_hz": 30, "max_frequency_hz": 2500}),
    ("10HP1020 8 Ohms", "10HP1020", {"nominal_size_m": .25, "fs_hz": 60, "qts": .24,
      "qes": .25, "qms": 6.5, "vas_m3": .0161, "re_ohm": 5.5, "le_h": .00085,
      "sd_m2": .0345, "xmax_m": .009, "power_rms_w": 700,
      "displacement_m3": .0022, "outer_diameter_m": .261,
      "cutout_diameter_m": .232, "mounting_depth_m": .1413,
      "moving_mass_kg": .0725, "force_factor_tm": 24.5,
      "bolt_circle_diameter_m": .246, "sensitivity_db_1w_1m": 96,
      "min_frequency_hz": 60, "max_frequency_hz": 2500}),
    ("12HP1060 8 Ohms", "12HP1060", {"nominal_size_m": .3, "fs_hz": 45, "qts": .28,
      "qes": .29, "qms": 12.1, "vas_m3": .0369, "re_ohm": 5,
      "le_h": .00138, "sd_m2": .0518, "xmax_m": .01245, "power_rms_w": 1000,
      "displacement_m3": .0029, "outer_diameter_m": .316,
      "cutout_diameter_m": .282, "mounting_depth_m": .16875,
      "moving_mass_kg": .1269, "force_factor_tm": 24.8,
      "bolt_circle_diameter_m": .2985, "sensitivity_db_1w_1m": 95,
      "min_frequency_hz": 45, "max_frequency_hz": 2500}),
):
    pdf = f"https://faitalpro.com/products/files/{code}/8/{code}_datasheet_8.pdf"
    FAITAL_TECH[model] = {"manufacturer": "FaitalPRO", "model": model,
        "driver_type": "woofer" if code in {"15PR400", "18FH510", "10HP1020", "12HP1060"}
        else "midwoofer",
        "nominal_impedance_ohm": 8, "source_name": "FaitalPRO Herstellerdaten",
        "source_url": pdf, "datasheet_url": pdf, "data_source_date": DATE,
        "source_document": "T/S und Maße aus FaitalPRO-Datenblatt; Preis separat bei Thomann geprüft."
        + (" Korbflansch asymmetrisch; Außenmaß ist Maximalmaß."
           if code in {"4FE35", "4FE32"} else ""), **values}

records = []
for group, (url, lines) in GROUPS.items():
    for line in lines.strip().splitlines():
        fields = line.split("|")
        if group == "mixed":
            maker, model, price = fields
        else:
            maker = {"visaton": "Visaton", "faitalpro": "FaitalPRO", "eminence": "Eminence"}[group]
            model, price = fields
        slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in model).strip("-")
        item = {"id": f"thomann:{maker.lower().replace(' ', '-')}-{slug}",
                "category": "drivers", "manufacturer": maker, "model": model,
                "source": f"Thomann Katalog, Preis geprüft {DATE}; technische Daten unvollständig",
                "price_eur": float(price), "price_checked_on": DATE, "product_url": url,
                "specs": {"data_status": "Katalogeintrag; T/S und Maße vor Berechnung ergänzen"},
                "is_test_data": False}
        if maker == "FaitalPRO" and model in FAITAL_TECH:
            item["driver"] = FAITAL_TECH[model]
            item["product_url"] = ("https://www.thomann.de/de/faitalpro_"+
                                   model.lower().replace(" ", "_")+".htm")
            item["specs"]["data_status"] = "Herstellerdaten vollständig für Entwurfsprüfung"
        records.append(item)

target = ROOT / "data" / "library" / "drivers" / "thomann_2026_10_02.json"
target.write_text(json.dumps({"components": records}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"{len(records)} Thomann-Katalogeinträge nach {target}")
