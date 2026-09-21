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


def test_bundled_metadata_has_address_room_counts_and_events():
    from nf_hotel_api.core.config import get_settings

    metadata = JsonHotelMetadataRepository(get_settings().metadata_path).load()

    assert str(metadata.address) == "Street 172, Phnom Penh, Cambodia"
    assert metadata.room_types["A"].room_count == 10
    assert metadata.room_types["B"].room_count == 10
    assert all(e.source_url.startswith("https://") for e in metadata.nearby_events)


def test_bundled_metadata_does_not_store_public_holidays():
    from nf_hotel_api.core.config import get_settings

    assert "public_holidays" not in get_settings().metadata_path.read_text(encoding="utf-8")


def test_event_rejects_end_before_start():
    from datetime import date

    from nf_hotel_api.domain.metadata import NearbyEvent

    with pytest.raises(ValueError):
        NearbyEvent(
            name="Bad", start_date=date(2024, 5, 2), end_date=date(2024, 5, 1),
            venue="x", source_url="https://example.com",
        )


def test_describe_includes_address_and_events():
    from datetime import date

    from nf_hotel_api.domain.metadata import Address, NearbyEvent

    metadata = HotelMetadata(
        hotel="NF Hotel",
        address=Address(street="Street 172", city="Phnom Penh", country="Cambodia"),
        room_types={"A": RoomType(size="Small", standard_price_per_night=20, room_count=10)},
        nearby_events=[
            NearbyEvent(
                name="Trade fair", start_date=date(2024, 11, 6), end_date=date(2024, 11, 6),
                venue="DIECC", source_url="https://example.com",
            )
        ],
    )

    text = metadata.describe()

    assert "Street 172, Phnom Penh, Cambodia" in text
    assert "2024-11-06: Trade fair (DIECC)" in text
