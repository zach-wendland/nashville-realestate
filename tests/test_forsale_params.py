"""Diagnostic script to identify correct ForSale API parameters.

This script tests different parameter name variations to find which ones
the Zillow RapidAPI actually accepts for ForSale listings.
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests
from dotenv import load_dotenv

from api.zillow_fetcher import get_api_key, build_headers, BASE_URL

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def test_parameter_variation(variation_name: str, params: dict) -> dict:
    """
    Test a parameter variation and return results.

    Args:
        variation_name: Name of this parameter variation
        params: Parameters to test

    Returns:
        Dict with result count and sample data
    """
    logging.info(f"\n{'='*80}")
    logging.info(f"Testing: {variation_name}")
    logging.info(f"Parameters: {params}")
    logging.info('='*80)

    try:
        api_key = get_api_key()
        headers = build_headers(api_key)

        response = requests.get(BASE_URL, headers=headers, params=params, timeout=30)

        if response.status_code == 200:
            data = response.json()

            # Extract results
            results = []
            if isinstance(data, dict):
                results = data.get('results', [])
                if not results:
                    results = data.get('props', [])

            result_count = len(results)

            logging.info(f"✓ Response Status: {response.status_code}")
            logging.info(f"✓ Results Count: {result_count}")

            if result_count > 0:
                # Sample first result
                first_result = results[0]
                price = first_result.get('price', 'N/A')
                address = first_result.get('address', 'N/A')
                beds = first_result.get('bedrooms', first_result.get('beds', 'N/A'))

                logging.info(f"✓ Sample Result:")
                logging.info(f"    Address: {address}")
                logging.info(f"    Price: ${price:,}" if isinstance(price, (int, float)) else f"    Price: {price}")
                logging.info(f"    Beds: {beds}")

                # Check if price is in expected range
                if isinstance(price, (int, float)):
                    expected_min = params.get('price_min') or params.get('priceMin') or params.get('saleMinPrice') or params.get('minPrice') or 200000
                    expected_max = params.get('price_max') or params.get('priceMax') or params.get('saleMaxPrice') or params.get('maxPrice') or 800000

                    if expected_min <= price <= expected_max:
                        logging.info(f"✓ Price within expected range ({expected_min:,} - {expected_max:,})")
                    else:
                        logging.warning(f"⚠ Price OUTSIDE expected range ({expected_min:,} - {expected_max:,})")

                return {
                    'variation': variation_name,
                    'success': True,
                    'count': result_count,
                    'sample_price': price,
                    'params': params
                }
            else:
                logging.warning("✗ No results returned")
                return {
                    'variation': variation_name,
                    'success': False,
                    'count': 0,
                    'params': params
                }
        else:
            logging.error(f"✗ HTTP Error: {response.status_code}")
            logging.error(f"  Response: {response.text[:200]}")
            return {
                'variation': variation_name,
                'success': False,
                'error': f"HTTP {response.status_code}",
                'params': params
            }

    except Exception as e:
        logging.error(f"✗ Exception: {e}")
        return {
            'variation': variation_name,
            'success': False,
            'error': str(e),
            'params': params
        }


def main():
    """Test different parameter variations for ForSale listings."""

    # Base parameters (common to all tests)
    base_params = {
        "status_type": "ForSale",
        "location": "37206, Nashville, TN",  # Single location for faster testing
        "bedsMin": 2,
        "bedsMax": 5,
        "bathsMin": 2,
        "page": 1
    }

    # Test variations
    variations = [
        {
            "name": "Variation 1: snake_case (price_min/price_max)",
            "params": {**base_params, "price_min": 200000, "price_max": 800000}
        },
        {
            "name": "Variation 2: camelCase (priceMin/priceMax)",
            "params": {**base_params, "priceMin": 200000, "priceMax": 800000}
        },
        {
            "name": "Variation 3: prefixed like rentals (saleMinPrice/saleMaxPrice)",
            "params": {**base_params, "saleMinPrice": 200000, "saleMaxPrice": 800000}
        },
        {
            "name": "Variation 4: current implementation (minPrice/maxPrice)",
            "params": {**base_params, "minPrice": 200000, "maxPrice": 800000}
        },
        {
            "name": "Variation 5: no price filter (baseline)",
            "params": base_params
        },
    ]

    results = []

    print("\n" + "="*80)
    print("ZILLOW FORSALE PARAMETER DIAGNOSTIC")
    print("="*80)
    print(f"Base Parameters: {base_params}")
    print(f"Testing {len(variations)} variations...")
    print("="*80)

    for variation in variations:
        result = test_parameter_variation(variation['name'], variation['params'])
        results.append(result)

    # Summary
    print("\n" + "="*80)
    print("SUMMARY RESULTS")
    print("="*80)

    successful = [r for r in results if r.get('success')]
    failed = [r for r in results if not r.get('success')]

    print(f"\nSuccessful variations: {len(successful)}/{len(results)}")

    if successful:
        print("\n✓ WORKING PARAMETER VARIATIONS:")
        for r in successful:
            print(f"\n  {r['variation']}")
            print(f"    Results: {r['count']}")
            print(f"    Sample price: ${r['sample_price']:,}" if isinstance(r.get('sample_price'), (int, float)) else f"    Sample price: {r.get('sample_price')}")
            print(f"    Parameters: {r['params']}")

    if failed:
        print("\n✗ FAILED VARIATIONS:")
        for r in failed:
            print(f"\n  {r['variation']}")
            print(f"    Error: {r.get('error', 'No results')}")

    # Recommendation
    print("\n" + "="*80)
    print("RECOMMENDATION")
    print("="*80)

    if successful:
        # Find variation with most results and price filtering working
        best = max(successful, key=lambda x: x['count'])

        print(f"\nUse: {best['variation']}")
        print(f"This returned {best['count']} results")

        # Extract just the price parameters
        price_params = {}
        for key in ['price_min', 'price_max', 'priceMin', 'priceMax', 'saleMinPrice', 'saleMaxPrice', 'minPrice', 'maxPrice']:
            if key in best['params']:
                price_params[key] = best['params'][key]

        print(f"\nUpdate main_unified.py FORSALE_PARAMS with:")
        print(f"    {price_params}")
    else:
        print("\n⚠ No variations worked! Possible issues:")
        print("  - API key may be invalid")
        print("  - Rate limiting may be active")
        print("  - ForSale listings may not be available in this location")
        print("  - Different parameter structure may be required")

    print("\n" + "="*80)


if __name__ == "__main__":
    # Check for API key
    try:
        api_key = os.getenv("ZILLOW_RAPIDAPI_KEY") or os.getenv("RAPIDAPI_KEY")
        if not api_key:
            print("ERROR: No API key found!")
            print("Set ZILLOW_RAPIDAPI_KEY or RAPIDAPI_KEY environment variable")
            sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    main()
