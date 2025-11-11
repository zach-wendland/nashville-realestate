"""Test ForSale price parameter names with confirmed working status_type."""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests
from dotenv import load_dotenv

from api.zillow_fetcher import get_api_key, build_headers, BASE_URL

load_dotenv()


def test_price_params(name: str, price_params: dict) -> dict:
    """Test price parameter variation."""
    params = {
        "status_type": "ForSale",
        "location": "Nashville, TN",
        **price_params,
        "page": 1
    }

    print(f"\nTesting: {name}")
    print(f"  Params: {price_params}")

    try:
        api_key = get_api_key()
        headers = build_headers(api_key)
        response = requests.get(BASE_URL, headers=headers, params=params, timeout=30)

        if response.status_code == 200:
            data = response.json()
            results = data.get('results', []) or data.get('props', [])
            count = len(results)

            if count > 0:
                # Check if prices are within range
                prices = [r.get('price') for r in results if r.get('price')]
                if prices:
                    min_p = min(prices)
                    max_p = max(prices)
                    expected_min = list(price_params.values())[0] if len(price_params) == 2 else 0
                    expected_max = list(price_params.values())[1] if len(price_params) == 2 else float('inf')

                    in_range = expected_min <= min_p and max_p <= expected_max * 1.5  # Allow 50% tolerance

                    print(f"  [SUCCESS] {count} results, price range ${min_p:,} - ${max_p:,}")
                    if in_range:
                        print(f"  [VALIDATED] Prices within expected range!")
                        return {'name': name, 'success': True, 'count': count, 'validated': True, 'params': price_params}
                    else:
                        print(f"  [WARNING] Prices outside expected {expected_min:,}-{expected_max:,}")
                        return {'name': name, 'success': True, 'count': count, 'validated': False, 'params': price_params}
                else:
                    print(f"  [SUCCESS] {count} results (no price data)")
                    return {'name': name, 'success': True, 'count': count, 'validated': None, 'params': price_params}
            else:
                print(f"  [FAIL] 0 results - params likely ignored")
                return {'name': name, 'success': False}
        else:
            print(f"  [ERROR] HTTP {response.status_code}")
            return {'name': name, 'success': False}

    except Exception as e:
        print(f"  [ERROR] {e}")
        return {'name': name, 'success': False}


def main():
    print("="*80)
    print("FORSALE PRICE PARAMETER DIAGNOSTIC")
    print("="*80)

    # Test different price parameter names
    tests = [
        ("baseline (no price filter)", {}),
        ("price_min/price_max", {"price_min": 200000, "price_max": 800000}),
        ("priceMin/priceMax", {"priceMin": 200000, "priceMax": 800000}),
        ("minPrice/maxPrice (current)", {"minPrice": 200000, "maxPrice": 800000}),
        ("saleMinPrice/saleMaxPrice", {"saleMinPrice": 200000, "saleMaxPrice": 800000}),
    ]

    results = []
    for name, params in tests:
        result = test_price_params(name, params)
        results.append(result)

    # Summary
    print("\n" + "="*80)
    print("SUMMARY & RECOMMENDATION")
    print("="*80)

    validated = [r for r in results if r.get('validated')]
    successful = [r for r in results if r.get('success')]

    if validated:
        best = validated[0]
        print(f"\n[RECOMMENDED] Use these parameters:")
        print(f"  {best['params']}")
        print(f"  - Returned {best['count']} results")
        print(f"  - Prices validated within expected range")
    elif successful:
        print(f"\n[WARNING] {len(successful)} variations returned results, but none validated price filtering")
        print("Price filters may be ignored by the API")
        for r in successful:
            if r['name'] != "baseline (no price filter)":
                print(f"  - {r['name']}: {r['count']} results")
    else:
        print("\n[FAIL] No working price parameters found")

    print("\n" + "="*80)


if __name__ == "__main__":
    main()
