"""Example: call POST /api/v1/report/from-file.

This endpoint takes no request body - it always analyzes the bundled
data/nf_hotel_bookings.csv on the server. Only the API key is required.

Usage:
    API_KEY=your-key python examples/call_from_file_report.py
    API_KEY=your-key python examples/call_from_file_report.py --base-url http://localhost:8000
"""

import argparse
import json
import os
import sys

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8000")
    args = parser.parse_args()

    api_key = os.environ.get("API_KEY")
    if not api_key:
        print("Set the API_KEY environment variable first.", file=sys.stderr)
        raise SystemExit(1)

    response = httpx.post(
        f"{args.base_url}/api/v1/report/from-file",
        headers={"X-API-Key": api_key},
        timeout=180.0,
    )
    response.raise_for_status()

    report = response.json()
    print("=== descriptive_stats ===")
    print(json.dumps(report["descriptive_stats"], indent=2))
    print("\n=== llm_report ===")
    print(report["llm_report"])


if __name__ == "__main__":
    main()
