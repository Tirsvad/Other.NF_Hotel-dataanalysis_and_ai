"""Regenerates data/holidays.json from the `holidays` package.

The file is an export, not a source of truth: the application reads holidays
straight from the package (services/public_holidays.py). Run this script to
refresh the export - after upgrading the package, or when a new year starts:

    .venv/Scripts/python scripts/update_holidays.py
    .venv/Scripts/python scripts/update_holidays.py --first-year 2022 --last-year 2028

By default it covers 2022 (start of the booking data) up to next year.
`tests/test_public_holidays.py` fails when the file no longer matches the
package, which is the signal to re-run this script.
"""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nf_hotel_api.services.public_holidays import PublicHolidayCalendar  # noqa: E402

OUTPUT = ROOT / "data" / "holidays.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--first-year", type=int, default=2022)
    parser.add_argument("--last-year", type=int, default=date.today().year + 1)
    parser.add_argument("--country", default="KH", help="ISO country code used by the holidays package")
    args = parser.parse_args()

    calendar = PublicHolidayCalendar(args.country)
    document = {
        "country": calendar.country_code,
        "source": f"python-holidays {calendar.package_version()}",
        "first_year": args.first_year,
        "last_year": args.last_year,
        "holidays": [
            {
                "name": period.name,
                "start_date": period.start_date.isoformat(),
                "end_date": period.end_date.isoformat(),
            }
            for period in calendar.periods(args.first_year, args.last_year)
        ],
    }
    OUTPUT.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT} ({len(document['holidays'])} holiday periods, {args.first_year}-{args.last_year})")


if __name__ == "__main__":
    main()
