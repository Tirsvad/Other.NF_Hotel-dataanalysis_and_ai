"""Generates the synthetic NF Hotel booking dataset (data/nf_hotel_bookings.csv).

These are NOT real bookings. The hotel is small (see room_count per room type
in data/hotel_metadata.json), so the simulation never sells more rooms of a
type than the hotel has on any night. Demand follows the calendar in the
metadata file (events near the hotel) and on Cambodian public holidays from
the `holidays` package.

Every multiplier below is a modelling ASSUMPTION, not a measurement - change
the constants and re-run to test other scenarios:

    .venv/Scripts/python scripts/generate_bookings.py

The output is reproducible (fixed seed). A small share of deliberately dirty
rows (duplicates, impossible guest counts, blanks) is added at the end so the
cleaning pipeline has something to do; set DIRTY_SHARE = 0 to disable.
"""
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nf_hotel_api.domain.metadata import HotelMetadata  # noqa: E402
from nf_hotel_api.services.public_holidays import PublicHolidayCalendar  # noqa: E402

SEED = 2022
FIRST_ARRIVAL = date(2022, 1, 1)
LAST_ARRIVAL = date(2025, 12, 31)
OUTPUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "nf_hotel_bookings.csv"
METADATA_FILE = ROOT / "data" / "hotel_metadata.json"

# --- Demand model (assumptions) -------------------------------------------
BASE_REQUESTS_PER_DAY = 5.5  # booking requests arriving per day in a normal week
MONTH_FACTOR = {  # cool/dry season busiest, rainy season quietest
    1: 1.25, 2: 1.2, 3: 1.05, 4: 0.9, 5: 0.85, 6: 0.8,
    7: 0.85, 8: 0.85, 9: 0.8, 10: 0.95, 11: 1.2, 12: 1.3,
}
WEEKDAY_FACTOR = {0: 0.95, 1: 0.95, 2: 0.95, 3: 1.0, 4: 1.15, 5: 1.2, 6: 1.0}
# Holiday effect on demand for a Phnom Penh hotel. Matched on the holiday name
# as spelled by the `holidays` package.
HOLIDAY_FACTORS = [
    ("Water Festival", 1.8),  # Phnom Penh hosts the biggest celebrations
    ("Khmer New Year", 0.75),  # capital empties as people travel to the provinces
    ("Pchum Ben", 0.8),  # same: family and pagoda visits in home provinces
]
OTHER_HOLIDAY_FACTOR = 1.15
# Event effect, matched on the event name (first match wins).
EVENT_FACTORS = [
    ("ASEAN Summits", 2.2),
    ("SEA Games", 2.5),
    ("ASEAN Para Games", 1.7),
    ("Half Marathon", 1.3),
    ("AFC Challenge League", 1.3),
]
OTHER_EVENT_FACTOR = 1.2

# --- Guests and stays -----------------------------------------------------
STAY_NIGHTS = [1, 2, 3, 4, 5, 6, 7, 10]
STAY_WEIGHTS = [0.33, 0.30, 0.17, 0.08, 0.05, 0.03, 0.03, 0.01]
COUNTRIES = {
    "Cambodia": 0.24, "China": 0.14, "Vietnam": 0.08, "United States": 0.08,
    "France": 0.06, "United Kingdom": 0.06, "Australia": 0.05, "Japan": 0.05,
    "South Korea": 0.05, "Thailand": 0.04, "Germany": 0.04, "Singapore": 0.03,
    "Malaysia": 0.03, "Other": 0.05,
}
SEGMENTS = {"Online TA": 0.45, "Direct": 0.20, "Offline TA/TO": 0.12,
            "Corporate": 0.09, "Groups": 0.08, "Complementary": 0.01}
# Price paid vs the standard price of the room type (assumption).
SEGMENT_PRICE_FACTOR = {"Corporate": 0.9, "Groups": 0.9, "Offline TA/TO": 0.95, "Complementary": 0.0}
PEAK_PRICE_FACTOR = 1.15  # applied when the arrival date has a demand factor >= 1.5
PEAK_DEMAND_THRESHOLD = 1.5
LARGE_ROOM_PREFERENCE = 0.85  # parties of 3+ or with children who ask for a large room

DIRTY_SHARE = 0.02


def demand_factor(day: date, metadata: HotelMetadata, holiday_names: dict[date, str]) -> float:
    factor = MONTH_FACTOR[day.month] * WEEKDAY_FACTOR[day.weekday()]
    holiday = holiday_names.get(day)
    if holiday:
        factor *= next((f for key, f in HOLIDAY_FACTORS if key in holiday), OTHER_HOLIDAY_FACTOR)
    for event in metadata.nearby_events:
        if event.covers(day):
            factor *= next((f for key, f in EVENT_FACTORS if key in event.name), OTHER_EVENT_FACTOR)
            break
    return factor


def pick(rng: np.random.Generator, weights: dict[str, float]) -> str:
    keys = list(weights)
    probabilities = np.array(list(weights.values()), dtype=float)
    return str(rng.choice(keys, p=probabilities / probabilities.sum()))


def simulate(metadata: HotelMetadata, rng: np.random.Generator) -> pd.DataFrame:
    days = (LAST_ARRIVAL - FIRST_ARRIVAL).days + 1
    horizon = days + 30  # stays that begin near the end run past LAST_ARRIVAL
    capacity = {code: room.room_count for code, room in metadata.room_types.items()}
    if any(count is None for count in capacity.values()):
        raise SystemExit("room_count must be set for every room type in hotel_metadata.json")
    booked = {code: np.zeros(horizon, dtype=int) for code in capacity}
    holiday_names = PublicHolidayCalendar().for_years(FIRST_ARRIVAL.year, LAST_ARRIVAL.year)
    small, large = "A", "B"

    rows = []
    for offset in range(days):
        arrival = FIRST_ARRIVAL + timedelta(days=offset)
        factor = demand_factor(arrival, metadata, holiday_names)
        for _ in range(rng.poisson(BASE_REQUESTS_PER_DAY * factor)):
            adults = int(rng.choice([1, 2, 3, 4], p=[0.25, 0.55, 0.12, 0.08]))
            children = int(rng.choice([0, 1, 2], p=[0.85, 0.10, 0.05])) if adults >= 2 else 0
            babies = int(rng.random() < 0.02)
            wants_large = adults >= 3 or children > 0
            preferred = large if rng.random() < (LARGE_ROOM_PREFERENCE if wants_large else 0.2) else small
            nights = int(rng.choice(STAY_NIGHTS, p=STAY_WEIGHTS))
            segment = pick(rng, SEGMENTS)
            if segment == "Corporate":
                nights = min(nights, 4)
            deposit = pick(rng, {"No Deposit": 0.90, "Non Refund": 0.07, "Refundable": 0.03})
            lead_mean = 45 if factor >= 1.3 else 22
            lead_time = int(min(rng.exponential(lead_mean), 365))
            cancel_probability = 0.20 * (0.3 if deposit == "Non Refund" else 1.0)
            is_canceled = int(rng.random() < cancel_probability)

            stay = slice(offset, offset + nights)
            assigned = None
            for code in (preferred, small if preferred == large else large):
                if (booked[code][stay] < capacity[code]).all():
                    assigned = code
                    break
            if assigned is None and not is_canceled:
                continue  # sold out on at least one night: request turned away
            if assigned is None:  # a cancelled request keeps its preferred type
                assigned = preferred
            if not is_canceled:
                booked[assigned][stay] += 1

            stay_dates = [arrival + timedelta(days=n) for n in range(nights)]
            weekend_nights = sum(d.weekday() >= 5 for d in stay_dates)
            standard = metadata.room_types[assigned].standard_price_per_night
            price = standard * SEGMENT_PRICE_FACTOR.get(segment, 1.0)
            if factor >= PEAK_DEMAND_THRESHOLD and segment != "Complementary":
                price *= PEAK_PRICE_FACTOR
            rows.append(
                {
                    "hotel": metadata.hotel,
                    "is_canceled": is_canceled,
                    "lead_time": lead_time,
                    "arrival_date_week_number": arrival.isocalendar()[1],
                    "booking_date": arrival - timedelta(days=lead_time),
                    "arrival_date": arrival,
                    "arrival_date_day_of_month": arrival.day,
                    "stays_in_weekend_nights": weekend_nights,
                    "stays_in_week_nights": nights - weekend_nights,
                    "adults": adults,
                    "children": children,
                    "babies": babies,
                    "meal": pick(rng, {"BB": 0.70, "HB": 0.10, "FB": 0.02, "SC": 0.18}),
                    "country": pick(rng, COUNTRIES),
                    "market_segment": segment,
                    "is_repeated_guest": int(rng.random() < 0.08),
                    "previous_cancellations": int(rng.random() < 0.04),
                    "assigned_room_type": assigned,
                    "booking_changes": int(rng.choice([0, 1, 2], p=[0.88, 0.09, 0.03])),
                    "deposit_type": deposit,
                    "agent": int(rng.choice([0, 9, 14, 28, 40, 240], p=[0.35, 0.15, 0.15, 0.1, 0.1, 0.15])),
                    "customer_type": "Group Contract" if segment == "Groups" else pick(
                        rng, {"No Contract (Single)": 0.75, "No Contract (Group)": 0.17, "Contract (Single)": 0.08}
                    ),
                    "required_car_parking_spaces": int(rng.random() < 0.05),
                    "total_of_special_requests": int(rng.choice([0, 1, 2, 3], p=[0.55, 0.28, 0.12, 0.05])),
                    "prize_per_nigth": round(price, 2),
                }
            )

    df = pd.DataFrame(rows)
    df = df.sort_values(["booking_date", "arrival_date"], kind="stable").reset_index(drop=True)
    df.insert(0, "booking_id", np.arange(1, len(df) + 1))
    return df


def add_dirty_rows(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Append duplicates and corrupt a few values, like a real messy export."""
    if DIRTY_SHARE <= 0:
        return df
    df = df.copy()
    n = max(1, int(len(df) * DIRTY_SHARE))
    corrupt = df.sample(n, random_state=SEED + 1).index
    half = len(corrupt) // 2
    df.loc[corrupt[:half], "adults"] = rng.choice([20, 55], size=half)
    df.loc[corrupt[half:], ["adults", "children", "babies"]] = 0  # booking without guests
    df["meal"] = df["meal"].astype(object)
    df.loc[df.sample(n // 2, random_state=SEED + 2).index, "meal"] = ""
    # Duplicates are copied last so they are exact copies (same values, new id)
    # of rows as they appear in the export, including any corruption above.
    duplicates = df.sample(n, random_state=SEED)
    df = pd.concat([df, duplicates], ignore_index=True)
    df = df.sort_values(["booking_date", "arrival_date"], kind="stable").reset_index(drop=True)
    df["booking_id"] = np.arange(1, len(df) + 1)
    return df


def main() -> None:
    metadata = HotelMetadata.model_validate_json(METADATA_FILE.read_text(encoding="utf-8"))
    rng = np.random.default_rng(SEED)
    df = add_dirty_rows(simulate(metadata, rng), rng)
    for column in ("booking_date", "arrival_date"):
        df[column] = pd.to_datetime(df[column]).dt.strftime("%d-%m-%Y")
    df.to_csv(OUTPUT, sep=";", index=False)
    print(f"wrote {len(df)} rows to {OUTPUT}")


if __name__ == "__main__":
    main()
