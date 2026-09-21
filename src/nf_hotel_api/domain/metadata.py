from pydantic import BaseModel, Field


class RoomType(BaseModel):
    """One kind of room the hotel offers."""

    size: str
    standard_price_per_night: float = Field(..., ge=0)
    # None = not known yet; anything that needs the count (e.g. occupancy)
    # must be skipped rather than guess.
    room_count: int | None = Field(default=None, ge=0)


class HotelMetadata(BaseModel):
    """Reference data about the hotel that is not part of the booking records.

    ``room_types`` is keyed by the ``assigned_room_type`` code used in the CSV.
    """

    hotel: str
    currency: str = "USD"
    room_types: dict[str, RoomType]

    def describe(self) -> str:
        """Plain-text summary of the room catalogue, for the LLM prompt."""
        lines = []
        for code, room in self.room_types.items():
            count = "unknown" if room.room_count is None else str(room.room_count)
            lines.append(
                f"- Room type {code}: {room.size}, standard price "
                f"{room.standard_price_per_night:g} {self.currency} per night, "
                f"number of rooms in hotel: {count}"
            )
        return "\n".join(lines)
