from datetime import date

from pydantic import BaseModel, Field, model_validator


class RoomType(BaseModel):
    """One kind of room the hotel offers."""

    size: str
    standard_price_per_night: float = Field(..., ge=0)
    # None = not known yet; anything that needs the count (e.g. occupancy)
    # must be skipped rather than guess.
    room_count: int | None = Field(default=None, ge=0)


class Address(BaseModel):
    street: str
    city: str
    country: str

    def __str__(self) -> str:
        return f"{self.street}, {self.city}, {self.country}"


class NearbyEvent(BaseModel):
    """An event in Phnom Penh close enough to the hotel to affect bookings."""

    name: str
    start_date: date
    end_date: date
    venue: str
    source_url: str

    @model_validator(mode="after")
    def _end_not_before_start(self) -> "NearbyEvent":
        if self.end_date < self.start_date:
            raise ValueError(f"{self.name}: end_date is before start_date")
        return self

    def covers(self, day: date) -> bool:
        return self.start_date <= day <= self.end_date

    def describe(self) -> str:
        if self.start_date == self.end_date:
            return f"{self.start_date.isoformat()}: {self.name} ({self.venue})"
        return (
            f"{self.start_date.isoformat()} to {self.end_date.isoformat()}: "
            f"{self.name} ({self.venue})"
        )


class HotelMetadata(BaseModel):
    """Reference data about the hotel that is not part of the booking records.

    ``room_types`` is keyed by the ``assigned_room_type`` code used in the CSV.
    Public holidays are deliberately not stored here; see
    ``services.public_holidays.PublicHolidayCalendar``.
    """

    hotel: str
    address: Address | None = None
    currency: str = "USD"
    room_types: dict[str, RoomType]
    nearby_events: list[NearbyEvent] = []

    def describe(self) -> str:
        """Plain-text summary of the hotel, its rooms and events, for the LLM prompt."""
        lines = [f"Hotel: {self.hotel}" + (f", {self.address}" if self.address else "")]
        for code, room in self.room_types.items():
            count = "unknown" if room.room_count is None else str(room.room_count)
            lines.append(
                f"- Room type {code}: {room.size}, standard price "
                f"{room.standard_price_per_night:g} {self.currency} per night, "
                f"number of rooms in hotel: {count}"
            )
        if self.nearby_events:
            lines.append("Events in Phnom Penh near the hotel:")
            lines.extend(f"- {event.describe()}" for event in self.nearby_events)
        return "\n".join(lines)
