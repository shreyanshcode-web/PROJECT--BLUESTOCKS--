from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "Datasets" / "raw"
DOCUMENTATION_DIR = PROJECT_ROOT / "Documentation"
SUMMARY_PATH = DOCUMENTATION_DIR / "data_quality_summary.md"
EXPECTED_PROVIDED_DATASETS = 10


@dataclass
class DatasetProfile:
    path: Path
    frame: pd.DataFrame
    anomalies: list[str]


COLUMN_ALIASES = {
    "scheme_code": [
        "scheme_code",
        "scheme code",
        "amfi_code",
        "amfi code",
        "amfi_scheme_code",
        "amfi scheme code",
        "code",
        "schemeid",
        "scheme_id",
    ],
    "fund_house": [
        "fund_house",
        "fund house",
        "amc",
        "amc_name",
        "amc name",
        "asset_management_company",
        "fund_family",
    ],
    "category": [
        "category",
        "scheme_category",
        "scheme category",
        "fund_category",
        "amfi_category",
    ],
    "sub_category": [
        "sub_category",
        "sub category",
        "subcategory",
        "scheme_sub_category",
        "scheme sub category",
        "fund_sub_category",
        "amfi_sub_category",
    ],
    "risk_grade": [
        "risk_grade",
        "risk grade",
        "risk_category",
        "risk category",
        "riskometer",
        "risk_level",
        "risk level",
        "scheme_risk",
        "risk_rating",
    ],
}


def normalize_name(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).strip().lower())


def clean_code_series(series: pd.Series) -> pd.Series:
    return (
        series.dropna()
        .astype(str)
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
    )


def find_column(frame: pd.DataFrame, aliases: Iterable[str]) -> str | None:
    normalized_columns = {normalize_name(column): column for column in frame.columns}

    for alias in aliases:
        normalized_alias = normalize_name(alias)
        if normalized_alias in normalized_columns:
            return normalized_columns[normalized_alias]

    for column in frame.columns:
        normalized_column = normalize_name(column)
        for alias in aliases:
            normalized_alias = normalize_name(alias)
            if normalized_alias and (
                normalized_alias in normalized_column
                or normalized_column in normalized_alias
            ):
                return column

    return None


def read_csv(path: Path) -> pd.DataFrame:
    encodings = ("utf-8", "utf-8-sig", "latin1")
    last_error: UnicodeDecodeError | None = None

    for encoding in encodings:
        try:
            return pd.read_csv(path, encoding=encoding, low_memory=False)
        except UnicodeDecodeError as exc:
            last_error = exc

    if last_error:
        raise last_error
    raise ValueError(f"Could not read {path}")


def detect_anomalies(frame: pd.DataFrame) -> list[str]:
    anomalies: list[str] = []

    if frame.empty:
        anomalies.append("Dataset is empty.")

    duplicated_columns = frame.columns[frame.columns.duplicated()].tolist()
    if duplicated_columns:
        anomalies.append(f"Duplicate column names: {duplicated_columns}")

    unnamed_columns = [
        column for column in frame.columns if str(column).lower().startswith("unnamed")
    ]
    if unnamed_columns:
        anomalies.append(f"Unnamed index-like columns present: {unnamed_columns}")

    whitespace_columns = [
        column for column in frame.columns if str(column) != str(column).strip()
    ]
    if whitespace_columns:
        anomalies.append(f"Column names contain leading/trailing spaces: {whitespace_columns}")

    duplicate_rows = int(frame.duplicated().sum())
    if duplicate_rows:
        anomalies.append(f"Duplicate rows: {duplicate_rows}")

    all_null_columns = frame.columns[frame.isna().all()].tolist()
    if all_null_columns:
        anomalies.append(f"All-null columns: {all_null_columns}")

    high_null_columns = []
    if len(frame):
        null_ratios = frame.isna().mean()
        high_null_columns = [
            f"{column} ({ratio:.1%})"
            for column, ratio in null_ratios.items()
            if ratio >= 0.5 and ratio < 1
        ]
    if high_null_columns:
        anomalies.append(f"Columns with >=50% null values: {high_null_columns}")

    for column in frame.columns:
        normalized_column = normalize_name(column)
        if "date" not in normalized_column:
            continue
        non_null = frame[column].dropna()
        if non_null.empty:
            continue
        parsed = pd.to_datetime(non_null, errors="coerce", format="mixed")
        if parsed.isna().sum():
            dayfirst_parsed = pd.to_datetime(
                non_null, errors="coerce", format="mixed", dayfirst=True
            )
            if dayfirst_parsed.isna().sum() < parsed.isna().sum():
                parsed = dayfirst_parsed
        invalid_count = int(parsed.isna().sum())
        if invalid_count:
            anomalies.append(f"Date column '{column}' has {invalid_count} unparsable values.")

    return anomalies or ["No obvious anomalies found."]


def is_live_nav_file(path: Path) -> bool:
    return path.name.lower().startswith("live_nav_")


def list_source_csvs(raw_dir: Path, include_live_nav: bool) -> list[Path]:
    csv_paths = sorted(raw_dir.glob("*.csv"))
    if include_live_nav:
        return csv_paths
    return [path for path in csv_paths if not is_live_nav_file(path)]


def print_profile(profile: DatasetProfile) -> None:
    print(f"\n=== {profile.path.name} ===")
    print(f"shape: {profile.frame.shape}")
    print("dtypes:")
    print(profile.frame.dtypes.to_string())
    print("head:")
    print(profile.frame.head().to_string(index=False))
    print("anomalies:")
    for anomaly in profile.anomalies:
        print(f"- {anomaly}")


def find_dataset(
    profiles: list[DatasetProfile], keyword_options: list[tuple[str, ...]]
) -> DatasetProfile | None:
    for keywords in keyword_options:
        normalized_keywords = [normalize_name(keyword) for keyword in keywords]
        for profile in profiles:
            normalized_stem = normalize_name(profile.path.stem)
            if all(keyword in normalized_stem for keyword in normalized_keywords):
                return profile
    return None


def format_unique_values(series: pd.Series, max_values: int = 100) -> list[str]:
    values = (
        series.dropna()
        .astype(str)
        .str.strip()
        .replace("", pd.NA)
        .dropna()
        .drop_duplicates()
        .sort_values()
        .tolist()
    )
    if len(values) <= max_values:
        return values
    return values[:max_values] + [f"... {len(values) - max_values} more"]


def explore_fund_master(profile: DatasetProfile | None) -> list[str]:
    lines: list[str] = ["## Fund Master Exploration", ""]

    if profile is None:
        lines.append("Fund master dataset was not found.")
        print("\n=== Fund master exploration ===")
        print("Fund master dataset was not found.")
        return lines

    frame = profile.frame
    print(f"\n=== Fund master exploration: {profile.path.name} ===")
    lines.append(f"Source: `{profile.path.name}`")
    lines.append("")

    for label, aliases in (
        ("Fund houses", COLUMN_ALIASES["fund_house"]),
        ("Categories", COLUMN_ALIASES["category"]),
        ("Sub-categories", COLUMN_ALIASES["sub_category"]),
        ("Risk grades", COLUMN_ALIASES["risk_grade"]),
    ):
        column = find_column(frame, aliases)
        if column is None:
            message = f"{label}: column not found."
            print(message)
            lines.append(f"- {message}")
            continue

        values = format_unique_values(frame[column])
        print(f"{label} ({column}):")
        for value in values:
            print(f"- {value}")
        lines.append(f"- {label} from `{column}`: {len(values)} displayed value(s)")
        lines.extend(f"  - {value}" for value in values)

    code_column = find_column(frame, COLUMN_ALIASES["scheme_code"])
    lines.append("")
    lines.append("### AMFI Scheme Code Structure")

    if code_column is None:
        message = "AMFI scheme code column was not found in fund master."
        print(message)
        lines.append(message)
        return lines

    codes = clean_code_series(frame[code_column])
    unique_codes = codes.drop_duplicates()
    numeric_mask = unique_codes.str.fullmatch(r"\d+")
    length_counts = unique_codes.str.len().value_counts().sort_index()
    duplicate_count = int(codes.duplicated().sum())
    leading_zero_count = int(unique_codes.str.startswith("0").sum())

    observations = [
        f"Code column: `{code_column}`",
        f"Rows with codes: {len(codes)}",
        f"Unique codes: {unique_codes.nunique()}",
        f"Duplicate code rows: {duplicate_count}",
        f"Numeric-looking unique codes: {int(numeric_mask.sum())} of {len(unique_codes)}",
        f"Leading-zero unique codes: {leading_zero_count}",
        f"Length distribution: {length_counts.to_dict()}",
        "Recommendation: treat AMFI scheme codes as strings because they are identifiers, not measured numbers.",
    ]

    print("\nAMFI scheme code observations:")
    for observation in observations:
        print(f"- {observation}")
        lines.append(f"- {observation}")

    examples = unique_codes.head(10).tolist()
    if examples:
        print(f"- Examples: {examples}")
        lines.append(f"- Examples: {examples}")

    return lines


def validate_amfi_codes(
    fund_master: DatasetProfile | None, nav_history: DatasetProfile | None
) -> list[str]:
    lines: list[str] = ["", "## AMFI Code Validation", ""]
    print("\n=== AMFI code validation ===")

    if fund_master is None:
        message = "Skipped: fund master dataset was not found."
        print(message)
        lines.append(message)
        return lines

    if nav_history is None:
        message = "Skipped: NAV history dataset was not found."
        print(message)
        lines.append(message)
        return lines

    master_code_column = find_column(fund_master.frame, COLUMN_ALIASES["scheme_code"])
    nav_code_column = find_column(nav_history.frame, COLUMN_ALIASES["scheme_code"])

    if master_code_column is None or nav_code_column is None:
        message = (
            "Skipped: scheme code column missing in "
            f"{fund_master.path.name if master_code_column is None else nav_history.path.name}."
        )
        print(message)
        lines.append(message)
        return lines

    master_codes = set(clean_code_series(fund_master.frame[master_code_column]))
    nav_codes = set(clean_code_series(nav_history.frame[nav_code_column]))
    missing_in_nav = sorted(master_codes - nav_codes)
    extra_in_nav = sorted(nav_codes - master_codes)

    status = "PASS" if not missing_in_nav else "FAIL"
    summary = [
        f"Status: {status}",
        f"Fund master source: `{fund_master.path.name}` using `{master_code_column}`",
        f"NAV history source: `{nav_history.path.name}` using `{nav_code_column}`",
        f"Fund master unique codes: {len(master_codes)}",
        f"NAV history unique codes: {len(nav_codes)}",
        f"Codes missing in NAV history: {len(missing_in_nav)}",
        f"Extra NAV history codes not present in fund master: {len(extra_in_nav)}",
    ]

    for item in summary:
        print(f"- {item}")
        lines.append(f"- {item}")

    if missing_in_nav:
        sample = missing_in_nav[:25]
        print(f"- Missing code sample: {sample}")
        lines.append(f"- Missing code sample: {sample}")

    return lines


def write_summary(
    profiles: list[DatasetProfile],
    dataset_count_note: str,
    fund_master_lines: list[str],
    validation_lines: list[str],
) -> None:
    DOCUMENTATION_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Day 1 Data Quality Summary",
        "",
        "Generated by `data_ingestion.py`.",
        "",
        "## Dataset Inventory",
        "",
        dataset_count_note,
        "",
    ]

    for profile in profiles:
        lines.append(f"### {profile.path.name}")
        lines.append(f"- Shape: {profile.frame.shape}")
        lines.append("- Anomalies:")
        lines.extend(f"  - {anomaly}" for anomaly in profile.anomalies)
        lines.append("")

    lines.extend(fund_master_lines)
    lines.extend(validation_lines)
    SUMMARY_PATH.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"\nWrote data quality summary to {SUMMARY_PATH}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect raw CSV datasets and validate AMFI code coverage."
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=RAW_DIR,
        help="Directory containing provided raw CSV datasets.",
    )
    parser.add_argument(
        "--include-live-nav",
        action="store_true",
        help="Include live_nav_*.csv files in the source CSV inspection.",
    )
    args = parser.parse_args()

    if not args.raw_dir.exists():
        print(f"Raw data directory does not exist: {args.raw_dir}", file=sys.stderr)
        return 1

    csv_paths = list_source_csvs(args.raw_dir, args.include_live_nav)
    if not csv_paths:
        print(
            f"No provided CSV datasets found in {args.raw_dir}. "
            "Place the 10 source CSV files there and rerun this script.",
            file=sys.stderr,
        )
        return 1

    profiles: list[DatasetProfile] = []
    for path in csv_paths:
        frame = read_csv(path)
        profile = DatasetProfile(path=path, frame=frame, anomalies=detect_anomalies(frame))
        profiles.append(profile)
        print_profile(profile)

    if len(profiles) == EXPECTED_PROVIDED_DATASETS:
        dataset_count_note = f"Loaded expected {EXPECTED_PROVIDED_DATASETS} provided CSV datasets."
    else:
        dataset_count_note = (
            f"Loaded {len(profiles)} provided CSV dataset(s); expected "
            f"{EXPECTED_PROVIDED_DATASETS}."
        )
    print(f"\n{dataset_count_note}")

    fund_master = find_dataset(
        profiles,
        [
            ("fund", "master"),
            ("scheme", "master"),
            ("master",),
        ],
    )
    nav_history = find_dataset(
        profiles,
        [
            ("nav", "history"),
            ("navhistory",),
            ("historical", "nav"),
        ],
    )

    fund_master_lines = explore_fund_master(fund_master)
    validation_lines = validate_amfi_codes(fund_master, nav_history)
    write_summary(profiles, dataset_count_note, fund_master_lines, validation_lines)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
