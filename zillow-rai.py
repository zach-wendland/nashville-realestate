import requests
import pandas as pd
from time import sleep
from typing import Any, Dict, Iterable, List

BASE_URL = "https://zillow-com1.p.rapidapi.com/propertyExtendedSearch"
API_KEY = "dfc421ade8msh736fe4d0243bddcp12f9dejsn9617d64ab9ee"
API_HOST = "zillow-com1.p.rapidapi.com"
PAGE_MAX = 3  # RapidAPI proxy throttles at higher page numbers
PAGE_DELAY = 5  # seconds – avoid rate limits

HEADERS = {
    "x-rapidapi-key": API_KEY,
    "x-rapidapi-host": API_HOST,
}


def fetch_page(params: Dict[str, Any], page_num: int) -> Dict[str, Any]:
    safe_page = max(0, min(int(page_num), PAGE_MAX))
    query = {**params, "page": safe_page}
    response = requests.get(BASE_URL, headers=HEADERS, params=query, timeout=30)
    response.raise_for_status()
    return response.json()


def extract_results(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return payload

    if isinstance(payload, dict):
        for key in ("results", "props", "matchingResults"):
            data = payload.get(key)
            if isinstance(data, list) and data:
                return data
        nested = payload.get("data")
        if isinstance(nested, dict):
            data = nested.get("props")
            if isinstance(data, list) and data:
                return data
    return []


def iterate_pages(params: Dict[str, Any], max_pages: int = PAGE_MAX) -> Iterable[Dict[str, Any]]:
    total_hint = None
    for page in range(0, max_pages + 1):
        print(f"Fetching page {page} for params: {params['location']}")
        sleep(PAGE_DELAY)
        try:
            payload = fetch_page(params, page)
        except requests.exceptions.HTTPError as err:
            status = err.response.status_code if err.response is not None else "unknown"
            print(f"Request failed with status {status}.")
            if status == 429:
                print("Hit RapidAPI rate limit, stopping pagination for this location.")
                break
            raise
        page_results = extract_results(payload)

        if not page_results:
            print("No more results returned by API.")
            break

        yield from page_results

        if isinstance(payload, dict):
            total_hint = payload.get("totalPages", total_hint)
            if isinstance(total_hint, int) and page >= total_hint:
                break


def split_locations(loc_string: str, limit: int = 5) -> List[str]:
    if not loc_string:
        return []
    return [chunk.strip() for chunk in loc_string.split(";") if chunk.strip()][:limit]


def main() -> None:
    base_params = {
        "status_type": "ForRent",
        "rentMinPrice": 1900,
        "rentMaxPrice": 3000,
        "bedsMin": 1,
        "bedsMax": 2,
        "sqftMin": 700,
    }

    location_spec = "37209, Nashville, TN; Midtown, Nashville, TN; 37203, Nashville, TN; "
    locations = split_locations(location_spec)

    rows: List[Dict[str, Any]] = []
    for location in locations or ["N/A"]:
        params = {**base_params, "location": location}
        for record in iterate_pages(params):
            record.setdefault("queryLocation", location)
            rows.append(record)

    if not rows:
        print("No records returned for the current filter set.")
        return

    df = pd.DataFrame(rows)
    pd.set_option("display.max_rows", None)
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", None)
    print(df)
    df.to_csv("nashville-zillow.csv")

if __name__ == "__main__":
    main()
