"""Enhanced diagnostic to test different status_type values for sale listings."""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests
from dotenv import load_dotenv

from api.zillow_fetcher import get_api_key, build_headers, BASE_URL

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')


def test_status_type(status_value: str) -> dict:
    """Test a status_type value."""
    params = {
        "status_type": status_value,
        "location": "Nashville, TN",
        "bedsMin": 2,
        "page": 1
    }

    print(f"\nTesting status_type='{status_value}'...")

    try:
        api_key = get_api_key()
        headers = build_headers(api_key)
        response = requests.get(BASE_URL, headers=headers, params=params, timeout=30)

        if response.status_code == 200:
            data = response.json()
            results = data.get('results', []) or data.get('props', [])
            count = len(results)

            if count > 0:
                first = results[0]
                print(f"  [SUCCESS] Found {count} results")
                print(f"  Sample: {first.get('address', 'N/A')} - ${first.get('price', 'N/A'):,}" if isinstance(first.get('price'), (int, float)) else f"  Sample: {first.get('address', 'N/A')}")
                return {'status': status_value, 'success': True, 'count': count}
            else:
                print(f"  [FAIL] 0 results")
                return {'status': status_value, 'success': False, 'count': 0}
        else:
            print(f"  [ERROR] HTTP {response.status_code}")
            return {'status': status_value, 'success': False, 'error': response.status_code}

    except Exception as e:
        print(f"  [ERROR] {e}")
        return {'status': status_value, 'success': False, 'error': str(e)}


def main():
    print("="*80)
    print("ZILLOW STATUS_TYPE DIAGNOSTIC")
    print("="*80)
    print("Testing different status_type values to find the correct one for sales...")

    # Test various possibilities
    status_types_to_test = [
        "ForSale",          # Current implementation
        "For Sale",         # With space
        "for-sale",         # Lowercase with dash
        "forsale",          # Lowercase no space
        "FORSALE",          # Uppercase
        "sale",             # Just "sale"
        "Sale",             # Capitalized
        "buy",              # Alternative: buy
        "Buy",              # Alternative: Buy
        "ForRent",          # Baseline: we know this works
    ]

    results = []
    for status in status_types_to_test:
        result = test_status_type(status)
        results.append(result)

    # Summary
    print("\n" + "="*80)
    print("RESULTS SUMMARY")
    print("="*80)

    successful = [r for r in results if r.get('success')]

    if successful:
        print(f"\n[SUCCESS] Found {len(successful)} working status_type values:")
        for r in successful:
            print(f"  - '{r['status']}' returned {r['count']} results")

        # Identify sale-related ones
        sale_related = [r for r in successful if 'sale' in r['status'].lower() or 'buy' in r['status'].lower()]
        if sale_related:
            best = max(sale_related, key=lambda x: x['count'])
            print(f"\n[RECOMMENDATION] Use status_type='{best['status']}'")
            print(f"  This returned {best['count']} ForSale listings")
        else:
            print("\n[WARNING] Only ForRent worked - API may not support ForSale listings!")
    else:
        print("\n[FAIL] No status_type values returned results")
        print("Possible issues:")
        print("  - API key invalid")
        print("  - Rate limiting")
        print("  - Different API endpoint needed for sales")

    print("\n" + "="*80)


if __name__ == "__main__":
    if not (os.getenv("ZILLOW_RAPIDAPI_KEY") or os.getenv("RAPIDAPI_KEY")):
        print("ERROR: No API key found!")
        sys.exit(1)
    main()
