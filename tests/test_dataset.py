"""Guards the bundled synthetic dataset against the hotel's real constraints."""
from pathlib import Path

import pandas as pd
import pytest

from nf_hotel_api.core.config import get_settings
from nf_hotel_api.repositories.booking_repository import CsvBookingRepository
from nf_hotel_api.repositories.metadata_repository import JsonHotelMetadataRepository
from nf_hotel_api.services.cleaning import DataCleaningService


@pytest.fixture(scope="module")
def metadata():
    return JsonHotelMetadataRepository(get_settings().metadata_path).load()


@pytest.fixture(scope="module")
def clean_bookings(metadata) -> pd.DataFrame:
    settings = get_settings()
    raw = CsvBookingRepository(settings.default_data_path, settings.csv_separator).load()
    return DataCleaningService(metadata).clean(raw)


def test_arrivals_are_within_2022_to_2025(clean_bookings):
    assert clean_bookings["arrival_date"].min() >= pd.Timestamp(2022, 1, 1)
    assert clean_bookings["arrival_date"].max() <= pd.Timestamp(2025, 12, 31)


def test_only_known_room_types_are_used(clean_bookings, metadata):
    assert set(clean_bookings["assigned_room_type"]) <= set(metadata.room_types)


def test_hotel_is_never_overbooked(clean_bookings, metadata):
    """Non-cancelled bookings must fit in the rooms the hotel actually has."""
    stays = clean_bookings[clean_bookings["is_canceled"] == 0]
    for code, room in metadata.room_types.items():
        of_type = stays[stays["assigned_room_type"] == code]
        nights = (of_type["stays_in_weekend_nights"] + of_type["stays_in_week_nights"]).astype(int)
        # +1 on arrival, -1 on the day after the last night; the running sum is the occupancy.
        starts = of_type["arrival_date"].value_counts()
        ends = (of_type["arrival_date"] + pd.to_timedelta(nights, unit="D")).value_counts()
        change = starts.sub(ends, fill_value=0).sort_index()
        assert change.cumsum().max() <= room.room_count, f"room type {code} overbooked"


def test_prices_are_present_and_non_negative(clean_bookings):
    assert clean_bookings["prize_per_nigth"].notna().all()
    assert (clean_bookings["prize_per_nigth"] >= 0).all()
