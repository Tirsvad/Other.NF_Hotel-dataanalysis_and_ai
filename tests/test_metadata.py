import pytest

from nf_hotel_api.domain.metadata import HotelMetadata, RoomType
from nf_hotel_api.repositories.metadata_repository import JsonHotelMetadataRepository


def test_bundled_metadata_file_defines_small_and_large_room_prices():
    from nf_hotel_api.core.config import get_settings

    metadata = JsonHotelMetadataRepository(get_settings().metadata_path).load()

    assert metadata.room_types["A"].size == "Small"
    assert metadata.room_types["A"].standard_price_per_night == 20
    assert metadata.room_types["B"].size == "Large"
    assert metadata.room_types["B"].standard_price_per_night == 25


def test_repository_raises_when_file_is_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        JsonHotelMetadataRepository(tmp_path / "nope.json").load()


def test_describe_lists_prices_and_marks_unknown_room_counts():
    metadata = HotelMetadata(
        hotel="NF Hotel",
        room_types={
            "A": RoomType(size="Small", standard_price_per_night=20, room_count=10),
            "B": RoomType(size="Large", standard_price_per_night=25),
        },
    )

    text = metadata.describe()

    assert "Room type A: Small, standard price 20 USD per night, number of rooms in hotel: 10" in text
    assert "Room type B: Large, standard price 25 USD per night, number of rooms in hotel: unknown" in text
