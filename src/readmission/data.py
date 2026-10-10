"""Load, clean, and report quality metrics for the source dataset."""

from __future__ import annotations

import csv
import json
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "configs" / "config.yaml"
IDENTIFIER_COLUMNS = {"encounter_id", "patient_nbr"}


def _config() -> dict[str, Any]:
    """Read the project configuration."""
    with CONFIG_PATH.open(encoding="utf-8") as file:
        return yaml.safe_load(file)


def download_raw(dest: str | Path) -> Path:
    """Save the UCI archive to the exact ZIP path supplied by the caller."""
    destination = Path(dest)
    destination.parent.mkdir(parents=True, exist_ok=True)
    url = _config()["dataset"]["download_url"]
    try:
        with urlopen(url, timeout=30) as response:
            archive = response.read()
    except (OSError, URLError, TimeoutError) as error:
        raise RuntimeError(
            f"Could not download the UCI dataset; check the network and try again: {error}"
        ) from error

    if not zipfile.is_zipfile(BytesIO(archive)):
        raise RuntimeError("The UCI download was not a valid ZIP archive.")
    destination.write_bytes(archive)
    return destination


def load_raw(path: str | Path) -> pd.DataFrame:
    """Load the encounter CSV and print its basic quality counts."""
    frame = pd.read_csv(path, na_values=["?"], keep_default_na=False, low_memory=False)
    missing = frame.isna().mean().mul(100).round(2)
    print(f"Raw shape: {frame.shape[0]:,} rows x {frame.shape[1]:,} columns")
    print(f"Duplicate rows: {frame.duplicated().sum():,}")
    print(f"Duplicate encounter_id rows: {frame['encounter_id'].duplicated().sum():,}")
    print("Missing percentage by column:")
    print(missing.to_string())
    return frame


def _verify_terminal_dispositions(mapping_path: Path, terminal_ids: list[int]) -> None:
    """Check selected discharge IDs against the mapping file's descriptions."""
    descriptions: dict[int, str] = {}
    in_dispositions = False
    with mapping_path.open(encoding="utf-8", newline="") as file:
        for row in csv.reader(file):
            if row and row[0].strip() == "discharge_disposition_id":
                in_dispositions = True
                continue
            if not in_dispositions:
                continue
            if not row or not row[0].strip():
                break
            if len(row) < 2:
                continue
            try:
                disposition_id = int(row[0].strip())
            except ValueError:
                continue
            descriptions[disposition_id] = row[1].strip()

    invalid = {
        disposition_id: descriptions.get(disposition_id)
        for disposition_id in terminal_ids
        if not any(
            word in descriptions.get(disposition_id, "").casefold()
            for word in ("expired", "hospice")
        )
    }
    assert not invalid, f"Terminal disposition descriptions do not match: {invalid}"


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Apply the documented cleaning policy and report rows removed per step."""
    config = _config()
    terminal_ids = config["dataset"]["terminal_discharge_ids"]
    _verify_terminal_dispositions(ROOT / config["paths"]["id_mapping"], terminal_ids)

    cleaned = df.copy()
    removed: dict[str, int] = {}

    invalid_gender = cleaned["gender"].isin(["Unknown/Invalid", "Unknown", "Invalid"])
    removed["invalid_gender"] = int(invalid_gender.sum())
    cleaned = cleaned.loc[~invalid_gender].copy()

    terminal = pd.to_numeric(cleaned["discharge_disposition_id"], errors="coerce").isin(
        terminal_ids
    )
    removed["terminal_discharge"] = int(terminal.sum())
    cleaned = cleaned.loc[~terminal].copy()

    duplicate = cleaned.duplicated(keep="first")
    removed["exact_duplicates"] = int(duplicate.sum())
    cleaned = cleaned.loc[~duplicate].copy()

    cleaned[config["dataset"]["target_column"]] = (
        cleaned["readmitted"].eq("<30").astype("int8")
    )
    cleaned = cleaned.drop(columns=["weight"])
    cleaned["payer_code"] = cleaned["payer_code"].fillna("Missing")
    cleaned["medical_specialty"] = cleaned["medical_specialty"].fillna("Missing")
    cleaned["race"] = cleaned["race"].fillna("Unknown")
    for column in ("A1Cresult", "max_glu_serum"):
        cleaned[column] = cleaned[column].replace("None", "Not tested")
    for column in ("diag_1", "diag_2", "diag_3"):
        cleaned[column] = cleaned[column].fillna("Unknown")

    return cleaned, removed


def _class_balance(frame: pd.DataFrame, target: str) -> dict[str, dict[str, float | int]]:
    """Return counts and percentages for each target class."""
    if target in frame:
        labels = frame[target]
    else:
        labels = frame["readmitted"].eq("<30").astype("int8")
    counts = labels.value_counts(dropna=False).sort_index()
    total = len(labels)
    return {
        str(label): {"count": int(count), "percentage": round(float(count / total * 100), 4)}
        for label, count in counts.items()
    }


def _missing_percentages(frame: pd.DataFrame) -> dict[str, float]:
    return {
        column: round(float(percent), 4)
        for column, percent in frame.isna().mean().mul(100).items()
    }


def _outlier_summary(frame: pd.DataFrame, target: str) -> dict[str, dict[str, int | float]]:
    summary: dict[str, dict[str, int | float]] = {}
    for column in frame.select_dtypes(include="number").columns:
        if column in IDENTIFIER_COLUMNS or column == target:
            continue
        values = frame[column].dropna()
        if values.empty:
            continue
        p1 = float(values.quantile(0.01))
        p99 = float(values.quantile(0.99))
        summary[column] = {
            "min": float(values.min()),
            "p1": p1,
            "p99": p99,
            "max": float(values.max()),
            "count_above_p99": int(values.gt(p99).sum()),
        }
    return summary


def build_quality_report(
    raw: pd.DataFrame,
    cleaned: pd.DataFrame,
    rows_removed: dict[str, int],
) -> dict[str, Any]:
    """Build the JSON serializable raw and cleaned data quality report."""
    target = _config()["dataset"]["target_column"]
    encounter_counts = cleaned["patient_nbr"].value_counts()
    multi_encounter_patients = int(encounter_counts.gt(1).sum())
    unique_patients = int(encounter_counts.size)
    prevalence = float(cleaned[target].mean()) if len(cleaned) else 0.0
    raw_missing = _missing_percentages(raw)
    clean_missing = _missing_percentages(cleaned)
    missing_by_column = {
        column: {"raw": raw_missing.get(column), "clean": clean_missing.get(column)}
        for column in dict.fromkeys([*raw_missing, *clean_missing])
    }
    return {
        "row_counts": {"raw": int(len(raw)), "clean": int(len(cleaned))},
        "rows_removed": rows_removed,
        "missing_percentages": missing_by_column,
        "class_balance": {
            "raw": _class_balance(raw, target),
            "clean": _class_balance(cleaned, target),
        },
        "patients": {
            "unique_patients": unique_patients,
            "patients_with_multiple_encounters": multi_encounter_patients,
            "share_with_multiple_encounters": (
                round(multi_encounter_patients / unique_patients, 6) if unique_patients else 0.0
            ),
        },
        "positive_class_share": prevalence,
        "numeric_outliers": _outlier_summary(cleaned, target),
    }


def write_quality_report(
    raw: pd.DataFrame,
    cleaned: pd.DataFrame,
    rows_removed: dict[str, int],
    path: str | Path,
) -> dict[str, Any]:
    """Write the generated quality report and return its data."""
    report = build_quality_report(raw, cleaned, rows_removed)
    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    """Run the raw data quality and cleaning stage."""
    config = _config()
    raw = load_raw(ROOT / config["paths"]["raw_data"])
    cleaned, rows_removed = clean(raw)
    report_path = ROOT / config["paths"]["quality_report"]
    report = write_quality_report(raw, cleaned, rows_removed, report_path)

    clean_path = ROOT / config["paths"]["cleaned_data"]
    clean_path.parent.mkdir(parents=True, exist_ok=True)
    cleaned.to_parquet(clean_path, index=False)

    print("Cleaning steps | Rows removed")
    for step, count in rows_removed.items():
        print(f"{step} | {count:,}")
    print(f"Cleaned shape: {cleaned.shape[0]:,} rows x {cleaned.shape[1]:,} columns")
    print(f"Positive class share: {report['positive_class_share']:.2%}")
    print(f"Quality report: {report_path.relative_to(ROOT)}")
    print(f"Clean parquet: {clean_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
