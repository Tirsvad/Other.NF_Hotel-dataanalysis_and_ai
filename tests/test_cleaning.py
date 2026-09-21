import pandas as pd

from nf_hotel_api.services.cleaning import DataCleaningService


def test_clean_removes_duplicate_bookings(dirty_bookings_df, hotel_metadata):
    result = DataCleaningService(hotel_metadata).clean(dirty_bookings_df)

    # booking 2 is a duplicate of booking 1 (ignoring booking_id) and must go.
    assert result["booking_id"].tolist() == [1]


def test_clean_coerces_dates_and_drops_unparseable_rows(hotel_metadata):
    df = pd.DataFrame(
        [
            {"booking_id": 1, "booking_date": "2024-01-01", "arrival_date": "2024-02-01"},
            {"booking_id": 2, "booking_date": "2024-01-01", "arrival_date": "garbage"},
        ]
    )

    result = DataCleaningService(hotel_metadata)._fix_wrong_format(df)
    assert pd.api.types.is_datetime64_any_dtype(result["arrival_date"])

    cleaned = DataCleaningService(hotel_metadata)._clean_empty_cells(result)
    assert cleaned["booking_id"].tolist() == [1]


def test_clean_replaces_blank_categoricals_with_unknown_placeholder(hotel_metadata):
    df = pd.DataFrame([{"hotel": "NF Hotel", "meal": "", "country": "Portugal"}])

    result = DataCleaningService(hotel_metadata)._clean_empty_cells(df)

    assert result.loc[0, "meal"] == "Unknown"
    assert result.loc[0, "country"] == "Portugal"


def test_clean_caps_implausible_guest_counts_and_fixes_zero_guest_rows(hotel_metadata):
    df = pd.DataFrame(
        [
            {"adults": 55, "children": 0, "babies": 0},
            {"adults": 0, "children": 0, "babies": 0},
        ]
    )

    result = DataCleaningService(hotel_metadata)._fix_wrong_data(df)

    assert result.loc[0, "adults"] <= 10
    assert result.loc[1, "adults"] == 1


def test_clean_parses_day_first_and_iso_dates_without_dropping_rows(hotel_metadata):
    df = pd.DataFrame(
        [
            {"booking_id": 1, "booking_date": "13-07-2018", "arrival_date": "02-06-2018"},
            {"booking_id": 2, "booking_date": "2018-07-14", "arrival_date": "2018-06-03"},
        ]
    )

    result = DataCleaningService(hotel_metadata).clean(df)

    assert result["booking_id"].tolist() == [1, 2]
    assert result.loc[0, "booking_date"] == pd.Timestamp(2018, 7, 13)
    assert result.loc[0, "arrival_date"] == pd.Timestamp(2018, 6, 2)
    assert result.loc[1, "arrival_date"] == pd.Timestamp(2018, 6, 3)


def test_add_pricing_keeps_price_paid_and_fills_missing_from_standard_price(hotel_metadata):
    df = pd.DataFrame(
        [
            {"assigned_room_type": "A", "prize_per_nigth": 15},  # discounted, kept
            {"assigned_room_type": "B", "prize_per_nigth": None},  # missing -> 25
            {"assigned_room_type": "A", "prize_per_nigth": -3},  # invalid -> 20
            {"assigned_room_type": "A", "prize_per_nigth": 0},  # free stay, kept
            {"assigned_room_type": "C", "prize_per_nigth": None},  # not in metadata
        ]
    )

    result = DataCleaningService(hotel_metadata)._add_pricing(df)

    assert result["prize_per_nigth"].iloc[:4].tolist() == [15, 25, 20, 0]
    assert pd.isna(result.loc[4, "prize_per_nigth"])
    assert result["room_size"].tolist() == ["Small", "Large", "Small", "Small", "Unknown"]


def test_add_pricing_revenue_is_nights_times_price_paid_and_zero_when_canceled(hotel_metadata):
    df = pd.DataFrame(
        [
            {"assigned_room_type": "A", "is_canceled": 0, "prize_per_nigth": 15,
             "stays_in_weekend_nights": 1, "stays_in_week_nights": 2},
            {"assigned_room_type": "B", "is_canceled": 0,
             "stays_in_weekend_nights": 0, "stays_in_week_nights": 3},
            {"assigned_room_type": "B", "is_canceled": 1,
             "stays_in_weekend_nights": 2, "stays_in_week_nights": 2},
        ]
    )

    result = DataCleaningService(hotel_metadata)._add_pricing(df)

    assert result["revenue"].tolist() == [45, 75, 0]


def test_clean_adds_pricing_columns_to_full_pipeline(dirty_bookings_df, hotel_metadata):
    result = DataCleaningService(hotel_metadata).clean(dirty_bookings_df)

    assert result.loc[0, "prize_per_nigth"] == 20
    assert result.loc[0, "room_size"] == "Small"
    assert result.loc[0, "revenue"] == 60  # 3 nights x $20
