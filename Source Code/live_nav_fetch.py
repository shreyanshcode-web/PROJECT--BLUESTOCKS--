from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "Datasets" / "raw"
BASE_URL = "https://api.mfapi.in/mf/{scheme_code}"

SCHEMES = {
    "125497": "HDFC Top 100 Direct",
    "119551": "SBI Bluechip",
    "120503": "ICICI Bluechip",
    "118632": "Nippon Large Cap",
    "119092": "Axis Bluechip",
    "120841": "Kotak Bluechip",
}


def fetch_scheme(scheme_code: str) -> dict:
    url = BASE_URL.format(scheme_code=scheme_code)
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError(f"Unexpected response type for {scheme_code}: {type(payload)}")
    return payload


def flatten_payload(
    scheme_code: str, requested_name: str, payload: dict, fetched_at_utc: str
) -> pd.DataFrame:
    meta = payload.get("meta") or {}
    data = payload.get("data") or []
    if not isinstance(data, list) or not data:
        raise ValueError(f"No NAV history rows returned for {scheme_code}")

    rows = []
    source_url = BASE_URL.format(scheme_code=scheme_code)
    for item in data:
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "requested_scheme_code": scheme_code,
                "requested_scheme_name": requested_name,
                "scheme_code": str(meta.get("scheme_code", scheme_code)),
                "scheme_name": meta.get("scheme_name"),
                "fund_house": meta.get("fund_house"),
                "scheme_type": meta.get("scheme_type"),
                "scheme_category": meta.get("scheme_category"),
                "date": item.get("date"),
                "nav": item.get("nav"),
                "fetched_at_utc": fetched_at_utc,
                "source_url": source_url,
            }
        )

    frame = pd.DataFrame(rows)
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce", dayfirst=True).dt.date
    frame["nav"] = pd.to_numeric(frame["nav"], errors="coerce")
    return frame


def save_scheme_csv(scheme_code: str, frame: pd.DataFrame) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RAW_DIR / f"live_nav_{scheme_code}.csv"
    frame.to_csv(output_path, index=False)
    return output_path


def main() -> int:
    fetched_at_utc = datetime.now(timezone.utc).isoformat()
    frames = []

    for scheme_code, requested_name in SCHEMES.items():
        payload = fetch_scheme(scheme_code)
        frame = flatten_payload(scheme_code, requested_name, payload, fetched_at_utc)
        output_path = save_scheme_csv(scheme_code, frame)
        frames.append(frame)

        latest_row = frame.sort_values("date").tail(1).iloc[0]
        print(
            f"Saved {len(frame)} rows for {requested_name} ({scheme_code}) "
            f"to {output_path}. Latest NAV: {latest_row['nav']} on {latest_row['date']}."
        )

    combined = pd.concat(frames, ignore_index=True)
    combined_path = RAW_DIR / "live_nav_combined.csv"
    combined.to_csv(combined_path, index=False)
    print(f"Saved combined NAV extract with {len(combined)} rows to {combined_path}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
