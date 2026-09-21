import os

# Force (not setdefault): an API_KEY already set in the shell/IDE/.env must not
# leak into the tests, or the authenticated API tests fail with 401.
os.environ["API_KEY"] = "test-api-key"

import pandas as pd
import pytest

from nf_hotel_api.domain.metadata import HotelMetadata, RoomType


@pytest.fixture
def dirty_bookings_df() -> pd.DataFrame:
    """A small, deliberately messy DataFrame exercising every cleaning rule."""
    return pd.DataFrame(
        [
            {
                "booking_id": 1,
                "hotel": "NF Hotel",
                "is_canceled": 0,
                "lead_time": "10",
                "arrival_date_week_number": 1,
                "booking_date": "2024-01-01",
                "arrival_date": "2024-02-01",
                "arrival_date_day_of_month": 1,
                "stays_in_weekend_nights": 1,
                "stays_in_week_nights": 2,
                "adults": 2,
                "children": 0,
                "babies": 0,
                "meal": "BB",
                "country": "Portugal",
                "market_segment": "Direct",
                "is_repeated_guest": 0,
                "previous_cancellations": 0,
                "assigned_room_type": "A",
                "booking_changes": 0,
                "deposit_type": "No Deposit",
                "agent": 0,
                "customer_type": "Contract (Single)",
                "required_car_parking_spaces": 0,
                "total_of_special_requests": 0,
            },
            {
                # Exact duplicate of booking 1 except the id -> must be removed.
                "booking_id": 2,
                "hotel": "NF Hotel",
                "is_canceled": 0,
                "lead_time": "10",
                "arrival_date_week_number": 1,
                "booking_date": "2024-01-01",
                "arrival_date": "2024-02-01",
                "arrival_date_day_of_month": 1,
                "stays_in_weekend_nights": 1,
                "stays_in_week_nights": 2,
                "adults": 2,
                "children": 0,
                "babies": 0,
                "meal": "BB",
                "country": "Portugal",
                "market_segment": "Direct",
                "is_repeated_guest": 0,
                "previous_cancellations": 0,
                "assigned_room_type": "A",
                "booking_changes": 0,
                "deposit_type": "No Deposit",
                "agent": 0,
                "customer_type": "Contract (Single)",
                "required_car_parking_spaces": 0,
                "total_of_special_requests": 0,
            },
            {
                # Wrong/empty data: bogus adults count, blank meal, zero guests overall.
                "booking_id": 3,
                "hotel": "NF Hotel",
                "is_canceled": 1,
                "lead_time": -5,
                "arrival_date_week_number": 2,
                "booking_date": "2024-01-05",
                "arrival_date": "not-a-date",
                "arrival_date_day_of_month": 5,
                "stays_in_weekend_nights": 0,
                "stays_in_week_nights": 1,
                "adults": 55,
                "children": 0,
                "babies": 0,
                "meal": "",
                "country": "Unknown",
                "market_segment": "Groups",
                "is_repeated_guest": 0,
                "previous_cancellations": 0,
                "assigned_room_type": "C",
                "booking_changes": 0,
                "deposit_type": "Non Refund",
                "agent": 9,
                "customer_type": "Group Contract",
                "required_car_parking_spaces": 0,
                "total_of_special_requests": 1,
            },
        ]
    )


@pytest.fixture
def hotel_metadata() -> HotelMetadata:
    return HotelMetadata(
        hotel="NF Hotel",
        currency="USD",
        room_types={
            "A": RoomType(size="Small", standard_price_per_night=20, room_count=10),
            "B": RoomType(size="Large", standard_price_per_night=25, room_count=5),
        },
    )
