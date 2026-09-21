import json

from nf_hotel_api.services.cleaning import DataCleaningService
from nf_hotel_api.services.statistics import DescriptiveStatsService


def test_compute_drops_booking_id(dirty_bookings_df, hotel_metadata):
    clean_df = DataCleaningService(hotel_metadata).clean(dirty_bookings_df)
    stats = DescriptiveStatsService().compute(clean_df)

    assert "booking_id" not in stats


def test_compute_output_is_json_serializable(dirty_bookings_df, hotel_metadata):
    clean_df = DataCleaningService(hotel_metadata).clean(dirty_bookings_df)
    stats = DescriptiveStatsService().compute(clean_df)

    # Must not raise: every value has to be a plain JSON-compatible type.
    json.dumps(stats)


def test_compute_includes_numeric_and_categorical_columns(dirty_bookings_df, hotel_metadata):
    clean_df = DataCleaningService(hotel_metadata).clean(dirty_bookings_df)
    stats = DescriptiveStatsService().compute(clean_df)

    assert "mean" in stats["adults"]
    assert "top" in stats["meal"] or "unique" in stats["meal"]
