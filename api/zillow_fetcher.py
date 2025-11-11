from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from time import sleep
from typing import Any, Dict, Iterable, List, Optional, Sequence

import pandas as pd
import requests

from api.rate_limiter import AdaptiveRateLimiter, RateLimitConfig, get_rate_limiter
from api.request_cache import RequestCache, get_request_cache

BASE_URL = "https://zillow-com1.p.rapidapi.com/propertyExtendedSearch"
API_HOST = "zillow-com1.p.rapidapi.com"
DEFAULT_RATE_LIMIT_SECONDS = 5
DEFAULT_MAX_PAGES = 5
DEFAULT_RETRIES = 4


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


def _extract_error_message(response: Optional[requests.Response]) -> str:
    if response is None:
        return ""

    try:
        payload = response.json()
    except ValueError:
        payload = None

    if isinstance(payload, dict):
        for key in ("message", "detail", "error", "errors", "title"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
            if isinstance(value, list):
                first = next((item for item in value if isinstance(item, str) and item.strip()), None)
                if first:
                    return first.strip()
    text = response.text.strip()
    return text[:200] if text else ""


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
    use_rate_limiter: bool = True,
) -> Dict[str, Any]:
    safe_page = _safe_page_number(page_num)
    request_params = {**params, "page": safe_page}

    # Use adaptive rate limiter if enabled
    if use_rate_limiter:
        limiter = get_rate_limiter(RateLimitConfig(
            tokens_per_second=1.0 / cooldown,
            max_retries=retries,
            base_backoff=cooldown
        ))

        def _make_request():
            response = session.get(BASE_URL, params=request_params, timeout=30)
            if response.status_code == 404:
                logging.info(f"No results for page {safe_page}; treating response as empty.")
                # Don't raise, return response
            return response

        try:
            response = limiter.execute_with_retry(_make_request, f"Page {safe_page}")
            if response.status_code == 404:
                return {"results": []}
            return response.json()
        except requests.HTTPError as exc:
            response_obj = exc.response
            status = response_obj.status_code if response_obj else "UNKNOWN"
            detail = _extract_error_message(response_obj)
            message = f"HTTP error while fetching page {safe_page}"
            if isinstance(status, int) and status in {401, 403}:
                message += " (check RapidAPI key or subscription status)"
            if detail:
                message = f"{message}: {detail}"
            raise ZillowAPIError(message) from exc

    # Fallback to original logic if rate limiter disabled
    for attempt in range(1, retries + 1):
        try:
            response = session.get(BASE_URL, params=request_params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as exc:
            response_obj = exc.response
            status = response_obj.status_code if response_obj else "UNKNOWN"
            logging.warning(f"HTTP error ({status}) on page {safe_page}, attempt {attempt}")
            if status == 404:
                logging.info(f"No results for page {safe_page}; treating response as empty.")
                return {"results": []}
            if status == 429 and attempt < retries:
                sleep(cooldown * attempt)
                continue
            detail = _extract_error_message(response_obj)
            message = f"HTTP error while fetching page {safe_page}"
            if isinstance(status, int) and status in {401, 403}:
                message += " (check RapidAPI key or subscription status)"
            if detail:
                message = f"{message}: {detail}"
            raise ZillowAPIError(message) from exc
        except requests.RequestException as exc:
            logging.warning(f"Network error on page {safe_page}, attempt {attempt}: {exc}")
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
    use_rate_limiter: bool = True,
) -> List[Dict[str, Any]]:
    aggregated: List[Dict[str, Any]] = []
    for page in range(1, max_pages + 1):
        logging.info(f"Fetching page {page}")
        payload = fetch_page(session, params, page, use_rate_limiter=use_rate_limiter)
        results = _extract_results(payload)
        if not results:
            logging.info(f"No results returned for page {page}; stopping pagination.")
            break
        aggregated.extend(results)

        total_pages = payload.get("totalPages") if isinstance(payload, dict) else None
        if isinstance(total_pages, int) and page >= total_pages:
            logging.info(f"Reached last page hinted by API ({total_pages}).")
            break

        # Only sleep if not using rate limiter (rate limiter handles pacing)
        if not use_rate_limiter:
            sleep(rate_limit_wait)
    return aggregated


def split_locations(raw_locations: str, limit: int | None = None) -> List[str]:
    """Split a semicolon-delimited `raw_locations` string into a list of cleaned locations.

    Args:
        raw_locations: semicolon-separated locations (e.g. "37206, Nashville, TN; Midtown, Nashville, TN; ...").
        limit: maximum number of locations to return. If None, return all parsed locations.
    """
    if not raw_locations:
        return []
    cleaned = [chunk.strip() for chunk in raw_locations.split(";") if chunk.strip()]
    if limit is None:
        return cleaned
    return cleaned[:limit]


def collect_properties(
    base_params: Dict[str, Any],
    locations: Sequence[Optional[str]],
    max_pages: int = DEFAULT_MAX_PAGES,
    use_cache: bool = True,
    cache_ttl: int = 3600,
) -> List[Dict[str, Any]]:
    api_key = get_api_key()
    aggregated: List[Dict[str, Any]] = []

    # Initialize cache if enabled
    cache = None
    if use_cache:
        from pathlib import Path
        cache_dir = Path(__file__).resolve().parents[1] / ".api_cache"
        cache = get_request_cache(
            max_size=1000,
            ttl_seconds=cache_ttl,
            disk_cache_dir=cache_dir
        )

    with requests.Session() as session:
        session.headers.update(build_headers(api_key))
        for location in locations or [None]:
            params = dict(base_params)
            if location:
                params["location"] = location
                logging.info(f"Collecting data for location: {location}")
            else:
                logging.info("Collecting data with base parameters (no explicit location)")

            # Create cache key with all relevant parameters
            cache_params = {**params, "max_pages": max_pages}

            # Check cache first
            if cache:
                cached_results = cache.get(cache_params)
                if cached_results is not None:
                    logging.info(f"Using cached results for {location or 'base query'} ({len(cached_results)} records)")
                    aggregated.extend(cached_results)
                    continue

            # Cache miss - fetch from API
            results = iterate_pages(session, params, max_pages=max_pages)
            logging.info(f"Retrieved {len(results)} records for {location or 'base query'}")

            # Store in cache
            if cache:
                cache.put(cache_params, results)

            aggregated.extend(results)

    # Log cache statistics
    if cache:
        stats = cache.get_stats()
        logging.info(
            f"Cache stats: {stats['hits']} hits, {stats['misses']} misses, "
            f"{stats['hit_rate']:.1f}% hit rate"
        )

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
    logging.info(f"Total aggregated results: {len(records)}")
    return records_to_dataframe(records)
