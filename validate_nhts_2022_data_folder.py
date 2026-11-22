"""Validate the local 2022 NextGen NHTS V2.1 public-use data folder.

The audit deliberately separates three kinds of information:

1. Raw local files in ``Data`` (the objects being validated).
2. Official FHWA/NHTS documentation and published control totals (evidence).
3. ``NHTS_2022_complete_data_dictionary.xlsx`` (optional reference only).

The reference-only workbook never contributes to the overall PASS/FAIL result.
Run with the Python environment that provides pandas, openpyxl, and pypdf.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from pypdf import PdfReader


SCRIPT_VERSION = "1.0.0"

OFFICIAL_SOURCES = {
    "FHWA NHTS overview": "https://www.fhwa.dot.gov/policyinformation/nhts.cfm",
    "FHWA latest NextGen NHTS data": "https://www.fhwa.dot.gov/policyinformation/nextgen-nhts-data.cfm",
    "NHTS 2022 downloads": "https://nhts.ornl.gov/downloads",
    "NHTS 2022 documentation": "https://nhts.ornl.gov/documentation",
    "NHTS 2022 FAQ": "https://nhts.ornl.gov/faq",
    "NHTS 2022 User's Guide": (
        "https://nhts.ornl.gov/assets/2022/doc/"
        "2022%20NextGen%20NHTS%20User's%20Guide%20V201_PubUse.pdf"
    ),
}

FILES = {
    "Household": "hhv2pub.csv",
    "Person": "perv2pub.csv",
    "Vehicle": "vehv2pub.csv",
    "Trip": "tripv2pub.csv",
    "Long Distance": "ldtv2pub.csv",
}

KEYS = {
    "Household": ["HOUSEID"],
    "Person": ["HOUSEID", "PERSONID"],
    "Vehicle": ["HOUSEID", "VEHID"],
    "Trip": ["HOUSEID", "PERSONID", "TRIPID"],
    "Long Distance": ["HOUSEID", "PERSONID"],
}

DICTIONARY_MARKERS = {
    "Household": "HH",
    "Person": "PER",
    "Vehicle": "VEH",
    "Trip": "TRIP",
    "Long Distance": "LDT",
}

WEIGHTS = {
    "Household": "WTHHFIN",
    "Person": "WTPERFIN",
    "Vehicle": "WTHHFIN",
    "Trip": "WTTRDFIN",
    "Long Distance": "WTPERFIN",
}

# Published in Tables 10 and 11 of the official 2022 NHTS User's Guide.
OFFICIAL_CONTROLS = [
    ("Households", 7_893, 127_544_707.0),
    ("Persons", 16_997, 305_560_925.0),
    ("Personally Owned Vehicle", 14_684, 232_837_104.0),
    ("Trips (Annualized)", 31_074, 253_754_536_507.0),
    ("Workers", 7_783, 158_009_510.0),
    ("Drivers", 13_434, 231_803_889.0),
    ("Person Trips", 31_074, 253_754_536_507.0),
    ("Person Miles of Travel", 31_060, 3_184_397_491_594.0),
    ("Vehicle Trips", 20_490, 160_953_195_395.0),
    ("Vehicle Miles of Travel", 20_487, 1_848_031_458_832.0),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("Data"))
    parser.add_argument("--output-dir", type=Path, default=Path("data_validation"))
    parser.add_argument(
        "--reference-dictionary",
        type=Path,
        default=Path("NHTS_2022_complete_data_dictionary.xlsx"),
        help="Optional convenience workbook; explicitly excluded from evidence and PASS/FAIL.",
    )
    parser.add_argument(
        "--online",
        action="store_true",
        help="Also test whether the official government documentation URLs are reachable.",
    )
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def check(status: str, area: str, test: str, observed: Any, expected: Any, note: str = "") -> dict[str, Any]:
    return {
        "status": status,
        "area": area,
        "test": test,
        "observed": observed,
        "expected": expected,
        "note": note,
    }


def status_equal(observed: Any, expected: Any) -> str:
    return "PASS" if observed == expected else "FAIL"


def status_close(observed: float, expected: float, tolerance: float = 1.0) -> str:
    return "PASS" if abs(float(observed) - float(expected)) <= tolerance else "FAIL"


def source_reachability(enabled: bool) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for name, url in OFFICIAL_SOURCES.items():
        if not enabled:
            rows.append(
                {
                    "source": name,
                    "url": url,
                    "status": "NOT_RUN",
                    "http_status": "",
                    "final_url": "",
                    "note": "Use --online to test reachability; source still identifies the evidence basis.",
                }
            )
            continue
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "NHTS-local-validation/1.0"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                rows.append(
                    {
                        "source": name,
                        "url": url,
                        "status": "PASS" if 200 <= response.status < 400 else "WARN",
                        "http_status": response.status,
                        "final_url": response.geturl(),
                        "note": "Official source was reachable at validation time.",
                    }
                )
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            rows.append(
                {
                    "source": name,
                    "url": url,
                    "status": "WARN",
                    "http_status": "",
                    "final_url": "",
                    "note": f"Reachability check failed without affecting local data validity: {exc}",
                }
            )
    return pd.DataFrame(rows)


def inventory_files(data_dir: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for path in sorted(p for p in data_dir.iterdir() if p.is_file()):
        row: dict[str, Any] = {
            "file": path.name,
            "extension": path.suffix.lower(),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "read_status": "PASS",
            "rows_or_pages": "",
            "columns_or_sheets": "",
            "note": "",
        }
        try:
            if path.suffix.lower() == ".csv":
                frame = pd.read_csv(path, low_memory=False)
                row["rows_or_pages"] = len(frame)
                row["columns_or_sheets"] = len(frame.columns)
            elif path.suffix.lower() == ".xlsx":
                book = pd.ExcelFile(path)
                row["columns_or_sheets"] = " | ".join(book.sheet_names)
                row["rows_or_pages"] = sum(
                    len(pd.read_excel(path, sheet_name=sheet)) for sheet in book.sheet_names
                )
            elif path.suffix.lower() == ".pdf":
                row["rows_or_pages"] = len(PdfReader(path).pages)
                row["columns_or_sheets"] = "PDF pages"
            else:
                row["note"] = "Hashed but no format-specific parse test was defined."
        except Exception as exc:  # report every file even when one is malformed
            row["read_status"] = "FAIL"
            row["note"] = f"{type(exc).__name__}: {exc}"
        rows.append(row)
    return pd.DataFrame(rows)


def load_tables(data_dir: Path) -> dict[str, pd.DataFrame]:
    return {
        table: pd.read_csv(data_dir / filename, low_memory=False)
        for table, filename in FILES.items()
    }


def validate_required_files(data_dir: Path) -> list[dict[str, Any]]:
    required = list(FILES.values()) + [
        "NHTS_2022_Codebook_V2.1.xlsx",
        "NHTS_2022_Data_Dictionary_V2.1.xlsx",
        "Citation.pdf",
    ]
    rows = []
    for filename in required:
        exists = (data_dir / filename).is_file()
        rows.append(check("PASS" if exists else "FAIL", "required files", filename, exists, True))
    return rows


def validate_tables(tables: dict[str, pd.DataFrame]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for table, frame in tables.items():
        key = KEYS[table]
        missing_key_columns = sorted(set(key) - set(frame.columns))
        rows.append(
            check(
                status_equal(missing_key_columns, []),
                table,
                "required key columns present",
                "; ".join(missing_key_columns) or "none missing",
                "none missing",
            )
        )
        if missing_key_columns:
            continue
        missing_key_rows = int(frame[key].isna().any(axis=1).sum())
        duplicate_key_rows = int(frame.duplicated(key, keep=False).sum())
        duplicate_rows = int(frame.duplicated(keep=False).sum())
        rows.extend(
            [
                check(status_equal(missing_key_rows, 0), table, "rows with missing key", missing_key_rows, 0),
                check(status_equal(duplicate_key_rows, 0), table, "rows in duplicate keys", duplicate_key_rows, 0),
                check(status_equal(duplicate_rows, 0), table, "exact duplicate rows", duplicate_rows, 0),
            ]
        )

        houseid_valid = frame["HOUSEID"].notna() & frame["HOUSEID"].astype("Int64").astype(str).str.fullmatch(r"\d{10}")
        houseid_invalid = int((~houseid_valid).sum())
        rows.append(check(status_equal(houseid_invalid, 0), table, "10-digit HOUSEID format", houseid_invalid, 0))

        for identifier in ("PERSONID", "VEHID", "TRIPID"):
            if identifier in key:
                numeric = pd.to_numeric(frame[identifier], errors="coerce")
                invalid = int((numeric.isna() | (numeric < 0) | (numeric > 99) | (numeric % 1 != 0)).sum())
                rows.append(
                    check(
                        status_equal(invalid, 0),
                        table,
                        f"{identifier} is a two-digit-compatible nonnegative integer",
                        invalid,
                        0,
                        "CSV storage may omit leading zeroes.",
                    )
                )
    return rows


def validate_schema(
    tables: dict[str, pd.DataFrame], data_dir: Path
) -> tuple[pd.DataFrame, pd.DataFrame]:
    dictionary_path = data_dir / "NHTS_2022_Data_Dictionary_V2.1.xlsx"
    codebook_path = data_dir / "NHTS_2022_Codebook_V2.1.xlsx"
    dictionary = pd.read_excel(dictionary_path, sheet_name="Dictionary")
    schema_rows: list[dict[str, Any]] = []
    codebook_rows: list[dict[str, Any]] = []

    for table, frame in tables.items():
        marker = DICTIONARY_MARKERS[table]
        documented = set(
            dictionary.loc[
                dictionary[marker].astype(str).str.strip().ne(""), "NAME"
            ].dropna().astype(str)
        )
        actual = set(frame.columns.astype(str))
        missing_from_dictionary = sorted(actual - documented)
        extra_in_dictionary = sorted(documented - actual)

        codebook = pd.read_excel(codebook_path, sheet_name=table)
        codebook_variables = set(codebook["Name"].dropna().astype(str))
        missing_from_codebook = sorted(actual - codebook_variables)
        extra_in_codebook = sorted(codebook_variables - actual)

        schema_rows.extend(
            [
                check(
                    status_equal(missing_from_dictionary, []),
                    table,
                    "CSV columns absent from official V2.1 data dictionary",
                    "; ".join(missing_from_dictionary) or "none",
                    "none",
                ),
                check(
                    status_equal(extra_in_dictionary, []),
                    table,
                    "dictionary columns absent from CSV",
                    "; ".join(extra_in_dictionary) or "none",
                    "none",
                ),
                check(
                    status_equal(missing_from_codebook, []),
                    table,
                    "CSV columns absent from official V2.1 codebook",
                    "; ".join(missing_from_codebook) or "none",
                    "none",
                ),
                check(
                    status_equal(extra_in_codebook, []),
                    table,
                    "codebook columns absent from CSV",
                    "; ".join(extra_in_codebook) or "none",
                    "none",
                ),
            ]
        )

        codebook["variable"] = codebook["Name"].ffill()
        frequency_sums = codebook.groupby("variable", dropna=True)["Frequency"].sum()
        weighted_sums = codebook.groupby("variable", dropna=True)["Weighted"].sum()
        expected_rows = len(frame)
        expected_weight = float(pd.to_numeric(frame[WEIGHTS[table]], errors="coerce").sum())
        for variable in sorted(codebook_variables):
            observed_frequency = float(frequency_sums.loc[variable])
            observed_weight = float(weighted_sums.loc[variable])
            codebook_rows.append(
                {
                    "table": table,
                    "variable": variable,
                    "frequency_sum": observed_frequency,
                    "expected_rows": expected_rows,
                    "frequency_status": status_close(observed_frequency, expected_rows, 0.01),
                    "weighted_sum": observed_weight,
                    "expected_weight_sum": expected_weight,
                    "weighted_status": status_close(observed_weight, expected_weight, 1.0),
                }
            )

    return pd.DataFrame(schema_rows), pd.DataFrame(codebook_rows)


def validate_relationships(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    household_ids = set(tables["Household"]["HOUSEID"])
    person_index = pd.MultiIndex.from_frame(tables["Person"][["HOUSEID", "PERSONID"]])
    vehicle_index = pd.MultiIndex.from_frame(tables["Vehicle"][["HOUSEID", "VEHID"]])
    rows: list[dict[str, Any]] = []

    def add(name: str, child_rows: int, orphans: int, expected: str) -> None:
        rows.append(
            {
                "relationship": name,
                "eligible_child_rows": child_rows,
                "orphan_rows": orphans,
                "status": status_equal(orphans, 0),
                "expected_link": expected,
            }
        )

    person = tables["Person"]
    vehicle = tables["Vehicle"]
    trip = tables["Trip"]
    long_distance = tables["Long Distance"]

    add(
        "Person -> Household",
        len(person),
        int((~person["HOUSEID"].isin(household_ids)).sum()),
        "HOUSEID",
    )
    add(
        "Vehicle -> Household",
        len(vehicle),
        int((~vehicle["HOUSEID"].isin(household_ids)).sum()),
        "HOUSEID",
    )
    add(
        "Trip -> Household",
        len(trip),
        int((~trip["HOUSEID"].isin(household_ids)).sum()),
        "HOUSEID",
    )
    trip_person = pd.MultiIndex.from_frame(trip[["HOUSEID", "PERSONID"]])
    add(
        "Trip -> Person",
        len(trip),
        int((~trip_person.isin(person_index)).sum()),
        "HOUSEID + PERSONID",
    )
    ldt_person = pd.MultiIndex.from_frame(long_distance[["HOUSEID", "PERSONID"]])
    add(
        "Long Distance -> Person",
        len(long_distance),
        int((~ldt_person.isin(person_index)).sum()),
        "HOUSEID + PERSONID",
    )

    valid_vehicle_rows = trip["VEHID"].gt(0)
    trip_vehicle = pd.MultiIndex.from_frame(trip.loc[valid_vehicle_rows, ["HOUSEID", "VEHID"]])
    add(
        "Trip with positive VEHID -> Vehicle",
        int(valid_vehicle_rows.sum()),
        int((~trip_vehicle.isin(vehicle_index)).sum()),
        "HOUSEID + VEHID",
    )

    missing_people_in_ldt = int((~person_index.isin(ldt_person)).sum())
    rows.append(
        {
            "relationship": "Person <-> Long Distance roster equality",
            "eligible_child_rows": len(person),
            "orphan_rows": missing_people_in_ldt,
            "status": status_equal(missing_people_in_ldt, 0),
            "expected_link": "one Long Distance roster row for every person",
        }
    )
    return pd.DataFrame(rows)


def calculate_controls(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    household = tables["Household"]
    person = tables["Person"]
    vehicle = tables["Vehicle"]
    trip = tables["Trip"]

    pmt = trip["TRPMILES"].ge(0)
    vehicle_trip = trip["DRVR_FLG"].eq(1)
    vmt = trip["VMT_MILE"].ge(0)
    observed = {
        "Households": (len(household), household["WTHHFIN"].sum()),
        "Persons": (len(person), person["WTPERFIN"].sum()),
        "Personally Owned Vehicle": (len(vehicle), vehicle["WTHHFIN"].sum()),
        "Trips (Annualized)": (len(trip), trip["WTTRDFIN"].sum()),
        "Workers": (
            int(person["WORKER"].eq(1).sum()),
            person.loc[person["WORKER"].eq(1), "WTPERFIN"].sum(),
        ),
        "Drivers": (
            int(person["DRIVER"].eq(1).sum()),
            person.loc[person["DRIVER"].eq(1), "WTPERFIN"].sum(),
        ),
        "Person Trips": (len(trip), trip["WTTRDFIN"].sum()),
        "Person Miles of Travel": (
            int(pmt.sum()),
            (trip.loc[pmt, "TRPMILES"] * trip.loc[pmt, "WTTRDFIN"]).sum(),
        ),
        "Vehicle Trips": (
            int(vehicle_trip.sum()),
            trip.loc[vehicle_trip, "WTTRDFIN"].sum(),
        ),
        "Vehicle Miles of Travel": (
            int(vmt.sum()),
            (trip.loc[vmt, "VMT_MILE"] * trip.loc[vmt, "WTTRDFIN"]).sum(),
        ),
    }

    rows = []
    for metric, expected_cases, expected_weighted in OFFICIAL_CONTROLS:
        observed_cases, observed_weighted = observed[metric]
        case_status = status_equal(int(observed_cases), expected_cases)
        weight_status = status_close(float(observed_weighted), expected_weighted, 1.0)
        rows.append(
            {
                "metric": metric,
                "observed_cases": int(observed_cases),
                "official_cases": expected_cases,
                "case_difference": int(observed_cases) - expected_cases,
                "case_status": case_status,
                "observed_weighted_total": float(observed_weighted),
                "official_weighted_total": expected_weighted,
                "weighted_difference": float(observed_weighted) - expected_weighted,
                "weighted_status": weight_status,
                "overall_status": "PASS" if case_status == weight_status == "PASS" else "FAIL",
                "official_source": OFFICIAL_SOURCES["NHTS 2022 User's Guide"],
            }
        )
    return pd.DataFrame(rows)


def validate_citation(data_dir: Path) -> pd.DataFrame:
    path = data_dir / "Citation.pdf"
    text = "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
    expectations = {
        "names Federal Highway Administration": "Federal Highway Administration" in text,
        "names 2022 NextGen National Household Travel Survey": (
            "2022 NextGen National Household Travel Survey" in " ".join(text.split())
        ),
        "names U.S. Department of Transportation": "U.S. Department of Transportation" in text,
        "links to nhts.ornl.gov": "nhts.ornl.gov" in text,
    }
    return pd.DataFrame(
        [
            {
                "test": test,
                "observed": result,
                "expected": True,
                "status": "PASS" if result else "FAIL",
                "official_cross_check": OFFICIAL_SOURCES["NHTS 2022 downloads"],
            }
            for test, result in expectations.items()
        ]
    )


def compare_reference_only(reference_path: Path, tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Compare the convenience workbook without treating it as evidence."""
    if not reference_path.is_file():
        return pd.DataFrame(
            [
                {
                    "status": "NOT_FOUND",
                    "test": "reference-only workbook exists",
                    "observed": False,
                    "expected": True,
                    "evidence_role": "NONE — excluded from validation result",
                }
            ]
        )
    try:
        all_fields = pd.read_excel(reference_path, sheet_name="All fields")
        reference_pairs = set(
            zip(
                all_fields["Table"].astype(str),
                all_fields["Original field name"].astype(str),
            )
        )
        actual_pairs = {
            (table, str(column))
            for table, frame in tables.items()
            for column in frame.columns
        }
        return pd.DataFrame(
            [
                {
                    "status": status_equal(len(all_fields), sum(len(frame.columns) for frame in tables.values())),
                    "test": "reference field-occurrence row count",
                    "observed": len(all_fields),
                    "expected": sum(len(frame.columns) for frame in tables.values()),
                    "evidence_role": "NONE — excluded from validation result",
                },
                {
                    "status": status_equal(reference_pairs, actual_pairs),
                    "test": "reference table-field pairs match local CSVs",
                    "observed": len(reference_pairs),
                    "expected": len(actual_pairs),
                    "evidence_role": "NONE — excluded from validation result",
                },
            ]
        )
    except Exception as exc:
        return pd.DataFrame(
            [
                {
                    "status": "ERROR",
                    "test": "reference-only workbook readable",
                    "observed": f"{type(exc).__name__}: {exc}",
                    "expected": "readable",
                    "evidence_role": "NONE — excluded from validation result",
                }
            ]
        )


def markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    display = frame[columns].copy()
    header = "| " + " | ".join(columns) + " |"
    divider = "| " + " | ".join(["---"] * len(columns)) + " |"
    body = []
    for _, row in display.iterrows():
        values = [str(row[column]).replace("|", "\\|").replace("\n", " ") for column in columns]
        body.append("| " + " | ".join(values) + " |")
    return "\n".join([header, divider, *body])


def write_report(
    output_path: Path,
    overall: str,
    generated_at: str,
    inventory: pd.DataFrame,
    table_checks: pd.DataFrame,
    schema_checks: pd.DataFrame,
    relationships: pd.DataFrame,
    controls: pd.DataFrame,
    codebook_checks: pd.DataFrame,
    citation_checks: pd.DataFrame,
    sources: pd.DataFrame,
    reference_checks: pd.DataFrame,
) -> None:
    failures = pd.concat(
        [
            table_checks.loc[table_checks["status"].eq("FAIL")],
            schema_checks.loc[schema_checks["status"].eq("FAIL")],
        ],
        ignore_index=True,
    )
    codebook_failures = int(
        ((codebook_checks["frequency_status"] == "FAIL") | (codebook_checks["weighted_status"] == "FAIL")).sum()
    )
    lines = [
        "# 2022 NextGen NHTS V2.1 local data validation",
        "",
        f"**Overall result: {overall}**  ",
        f"Generated (UTC): {generated_at}  ",
        f"Validator version: {SCRIPT_VERSION}",
        "",
        "## Scope and evidence rule",
        "",
        "The `Data` folder was checked for file readability, required files, table grain and keys, schema coverage, cross-table relationships, official control totals, codebook consistency, and citation content. The official FHWA/NHTS pages and the official User's Guide are the evidence basis.",
        "",
        "`NHTS_2022_complete_data_dictionary.xlsx` was used only as an optional convenience cross-check. It did not supply any expected value and is excluded from the overall result.",
        "",
        "## File inventory",
        "",
        markdown_table(inventory, ["file", "bytes", "sha256", "read_status", "rows_or_pages", "columns_or_sheets"]),
        "",
        "## Official control totals",
        "",
        markdown_table(
            controls.round({"observed_weighted_total": 3, "weighted_difference": 3}),
            ["metric", "observed_cases", "official_cases", "observed_weighted_total", "official_weighted_total", "overall_status"],
        ),
        "",
        "All weighted comparisons allow an absolute tolerance of 1 because the User's Guide publishes rounded whole-number totals.",
        "",
        "## Cross-table relationships",
        "",
        markdown_table(relationships, ["relationship", "eligible_child_rows", "orphan_rows", "status", "expected_link"]),
        "",
        "## Schema and codebook summary",
        "",
        f"- Schema failures: {int(schema_checks['status'].eq('FAIL').sum())}",
        f"- Table/key failures: {int(table_checks['status'].eq('FAIL').sum())}",
        f"- Codebook variable-total failures: {codebook_failures} across {len(codebook_checks)} documented variables",
        f"- Citation-content failures: {int(citation_checks['status'].eq('FAIL').sum())}",
        f"- Other combined failures: {len(failures)}",
        "",
        "## Government sources",
        "",
    ]
    for name, url in OFFICIAL_SOURCES.items():
        lines.append(f"- [{name}]({url})")
    lines.extend(
        [
            "",
            "The official User's Guide defines the core table grains and identifiers, explains the special negative codes, and publishes the control totals used above. The NHTS documentation page identifies the V2.1 codebook and data dictionary, while the downloads page identifies the V2.1 CSV release and recommended citation.",
            "",
            "## Online reachability",
            "",
            markdown_table(sources, ["source", "status", "http_status", "final_url", "note"]),
            "",
            "A reachability warning means the network check failed or was not run; it does not invalidate locally reproduced data checks.",
            "",
            "## Reference-only comparison (not evidence)",
            "",
            markdown_table(reference_checks, list(reference_checks.columns)),
            "",
            "## Interpretation",
            "",
            (
                "The folder is internally consistent and reproduces the official published NHTS control totals. "
                "It is suitable as the source data for the proposal-stage exploratory analysis. "
                "This audit establishes file integrity and release consistency; it does not by itself establish "
                "that any later analytical sample, recoding, model, or causal interpretation is valid."
                if overall == "PASS"
                else "At least one mandatory validation failed. Review the detailed CSV outputs before analysis."
            ),
            "",
        ]
    )
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    data_dir = args.data_dir.resolve()
    output_dir = args.output_dir.resolve()
    reference_path = args.reference_dictionary.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    generated_at = datetime.now(timezone.utc).isoformat()
    required_checks = pd.DataFrame(validate_required_files(data_dir))
    if (required_checks["status"] == "FAIL").any():
        required_checks.to_csv(output_dir / "required_file_validation.csv", index=False)
        missing = required_checks.loc[required_checks["status"].eq("FAIL"), "test"].tolist()
        print(f"FAIL: required files are missing: {missing}", file=sys.stderr)
        return 2

    inventory = inventory_files(data_dir)
    tables = load_tables(data_dir)
    table_checks = pd.DataFrame(validate_tables(tables))
    schema_checks, codebook_checks = validate_schema(tables, data_dir)
    relationships = validate_relationships(tables)
    controls = calculate_controls(tables)
    citation_checks = validate_citation(data_dir)
    sources = source_reachability(args.online)
    reference_checks = compare_reference_only(reference_path, tables)

    mandatory_failure = any(
        [
            bool(required_checks["status"].eq("FAIL").any()),
            bool(inventory["read_status"].eq("FAIL").any()),
            bool(table_checks["status"].eq("FAIL").any()),
            bool(schema_checks["status"].eq("FAIL").any()),
            bool(relationships["status"].eq("FAIL").any()),
            bool(controls["overall_status"].eq("FAIL").any()),
            bool(citation_checks["status"].eq("FAIL").any()),
            bool(codebook_checks["frequency_status"].eq("FAIL").any()),
            bool(codebook_checks["weighted_status"].eq("FAIL").any()),
        ]
    )
    overall = "FAIL" if mandatory_failure else "PASS"

    outputs = {
        "required_file_validation.csv": required_checks,
        "file_inventory.csv": inventory,
        "table_key_validation.csv": table_checks,
        "schema_validation.csv": schema_checks,
        "relationship_validation.csv": relationships,
        "official_control_totals.csv": controls,
        "codebook_consistency.csv": codebook_checks,
        "citation_validation.csv": citation_checks,
        "government_source_reachability.csv": sources,
        "reference_only_comparison.csv": reference_checks,
    }
    for filename, frame in outputs.items():
        frame.to_csv(output_dir / filename, index=False)

    manifest = {
        "validator_version": SCRIPT_VERSION,
        "generated_at_utc": generated_at,
        "data_directory": str(data_dir),
        "output_directory": str(output_dir),
        "overall_status": overall,
        "evidence_sources": OFFICIAL_SOURCES,
        "reference_only_file": str(reference_path),
        "reference_only_excluded_from_result": True,
        "output_files": [*outputs.keys(), "validation_manifest.json", "validation_report.md"],
    }
    (output_dir / "validation_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    write_report(
        output_dir / "validation_report.md",
        overall,
        generated_at,
        inventory,
        table_checks,
        schema_checks,
        relationships,
        controls,
        codebook_checks,
        citation_checks,
        sources,
        reference_checks,
    )

    print(f"Overall status: {overall}")
    print(f"Validated data directory: {data_dir}")
    print(f"Report: {output_dir / 'validation_report.md'}")
    print(f"Mandatory failures: {int(mandatory_failure)}")
    print(f"Reference-only file excluded from result: {reference_path}")
    return 1 if mandatory_failure else 0


if __name__ == "__main__":
    raise SystemExit(main())
