from __future__ import annotations

import os
from dataclasses import dataclass
from time import sleep
from typing import Any, Dict, Iterable, List, Optional, Sequence

import pandas as pd
import requests

BASE_URL = "https://zillow-com1.p.rapidapi.com/propertyExtendedSearch"
API_HOST = "zillow-com1.p.rapidapi.com"
DEFAULT_RATE_LIMIT_SECONDS = 5
DEFAULT_MAX_PAGES = 1
DEFAULT_RETRIES = 3


class ZillowAPIError(RuntimeError):
    """Raised for unrecoverable errors when talking to the Zillow proxy API."""


def get_api_key() -> str:
    key = os.getenv("ZILLOW_RAPIDAPI_KEY") or os.getenv("RAPIDAPI_KEY")
    if not key:
        raise ZillowAPIError(
            "RapidAPI key not provided. Set ZILLOW_RAPIDAPI_KEY or RAPIDAPI_KEY environment variable."
        )
    return key


def build_headers(api_key: str) -> Dict[str, str]:
    return {"x-rapidapi-key": api_key, "x-rapidapi-host": API_HOST}


def _safe_page_number(page_num: int) -> int:
    try:
        return max(1, int(page_num))
    except (TypeError, ValueError):
        return 1


def fetch_page(
    session: requests.Session,
    params: Dict[str, Any],
    page_num: int,
    retries: int = DEFAULT_RETRIES,
    cooldown: float = DEFAULT_RATE_LIMIT_SECONDS,
) -> Dict[str, Any]:
    safe_page = _safe_page_number(page_num)
    request_params = {**params, "page": safe_page}
    for attempt in range(1, retries + 1):
        try:
            response = session.get(BASE_URL, params=request_params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response else "UNKNOWN"
            print(f"HTTP error ({status}) on page {safe_page}, attempt {attempt}")
            if status == 429 and attempt < retries:
                sleep(cooldown * attempt)
                continue
            raise ZillowAPIError(f"HTTP error while fetching page {safe_page}") from exc
        except requests.RequestException as exc:
            print(f"Network error on page {safe_page}, attempt {attempt}: {exc}")
            if attempt < retries:
                sleep(cooldown * attempt)
                continue
            raise ZillowAPIError(f"Network error while fetching page {safe_page}") from exc
    raise ZillowAPIError(f"Failed to fetch page {safe_page} after {retries} attempts")


def _extract_results(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    candidates = (
        payload.get("results"),
        payload.get("props"),
        payload.get("matchingResults"),
        payload.get("data", {}).get("props") if isinstance(payload.get("data"), dict) else None,
    )
    for candidate in candidates:
        if isinstance(candidate, list):
            return [item for item in candidate if isinstance(item, dict)]
    return []


def iterate_pages(
    session: requests.Session,
    params: Dict[str, Any],
    max_pages: int = DEFAULT_MAX_PAGES,
    rate_limit_wait: float = DEFAULT_RATE_LIMIT_SECONDS,
) -> List[Dict[str, Any]]:
    aggregated: List[Dict[str, Any]] = []
    for page in range(1, max_pages + 1):
        print(f"Fetching page {page}")
        payload = fetch_page(session, params, page)
        results = _extract_results(payload)
        if not results:
            print(f"No results returned for page {page}; stopping pagination.")
            break
        aggregated.extend(results)

        total_pages = payload.get("totalPages") if isinstance(payload, dict) else None
        if isinstance(total_pages, int) and page >= total_pages:
            print(f"Reached last page hinted by API ({total_pages}).")
            break
        sleep(rate_limit_wait)
    return aggregated


def split_locations(raw_locations: str, limit: int = 5) -> List[str]:
    if not raw_locations:
        return []
    cleaned = [chunk.strip() for chunk in raw_locations.split(";") if chunk.strip()]
    return cleaned[:limit]


def collect_properties(
    base_params: Dict[str, Any],
    locations: Sequence[Optional[str]],
    max_pages: int = DEFAULT_MAX_PAGES,
) -> List[Dict[str, Any]]:
    api_key = get_api_key()
    aggregated: List[Dict[str, Any]] = []
    with requests.Session() as session:
        session.headers.update(build_headers(api_key))
        for location in locations or [None]:
            params = dict(base_params)
            if location:
                params["location"] = location
                print(f"Collecting data for location: {location}")
            else:
                print("Collecting data with base parameters (no explicit location)")
            results = iterate_pages(session, params, max_pages=max_pages)
            print(f"Retrieved {len(results)} records for {location or 'base query'}")
            aggregated.extend(results)
    return aggregated


def _flatten_mapping(prefix: str, mapping: Dict[str, Any]) -> Dict[str, Any]:
    flattened: Dict[str, Any] = {}
    for key, value in mapping.items():
        if isinstance(value, dict):
            nested = _flatten_mapping(f"{prefix}{key}__", value)
            flattened.update(nested)
        else:
            flattened[f"{prefix}{key}"] = value
    return flattened


def _augment_with_units(base_rows: List[Dict[str, Any]], records: Sequence[Dict[str, Any]]) -> None:
    for row, record in zip(base_rows, records):
        units = record.get("units")
        if not isinstance(units, list):
            continue
        for index, unit in enumerate(units, start=1):
            if not isinstance(unit, dict):
                continue
            flat_unit = _flatten_mapping("", unit)
            for key, value in flat_unit.items():
                col_name = f"{key}_{index}"
                row[col_name] = value


def records_to_dataframe(records: Sequence[Dict[str, Any]]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame()

    base_rows: List[Dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        flat_record = _flatten_mapping("", {k: v for k, v in record.items() if k != "units"})
        base_rows.append(flat_record)

    _augment_with_units(base_rows, records)
    return pd.DataFrame(base_rows)


@dataclass(frozen=True)
class FetchConfig:
    base_params: Dict[str, Any]
    locations: Sequence[Optional[str]]
    max_pages: int = DEFAULT_MAX_PAGES


def fetch_dataframe(config: FetchConfig) -> pd.DataFrame:
    records = collect_properties(config.base_params, config.locations, max_pages=config.max_pages)
    print(f"Total aggregated results: {len(records)}")
    return records_to_dataframe(records)
