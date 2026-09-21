from typing import Any

from pydantic import BaseModel, Field


class Booking(BaseModel):
    """A single hotel booking record, mirroring nf_hotel_bookings.csv.

    Fields are intentionally loosely typed (str for dates/free-form values)
    because incoming JSON is treated as *raw* data that still needs to pass
    through the cleaning pipeline before analysis.
    """

    booking_id: int
    hotel: str
    is_canceled: int
    lead_time: int
    arrival_date_week_number: int
    booking_date: str
    arrival_date: str
    arrival_date_day_of_month: int
    stays_in_weekend_nights: int
    stays_in_week_nights: int
    adults: int
    children: int
    babies: int
    meal: str
    country: str
    market_segment: str
    is_repeated_guest: int
    previous_cancellations: int
    assigned_room_type: str
    booking_changes: int
    deposit_type: str
    agent: int
    customer_type: str
    required_car_parking_spaces: int
    total_of_special_requests: int
    # Optional: when omitted (or wrong) it is derived from assigned_room_type.
    # Spelling mirrors the CSV column header.
    prize_per_nigth: float | None = None


class BookingBatch(BaseModel):
    """Payload for submitting raw booking records as JSON."""

    records: list[Booking] = Field(..., min_length=1)


class ReportResponse(BaseModel):
    """Result of a full analytics report: stats + LLM narrative."""

    descriptive_stats: dict[str, dict[str, Any]]
    llm_report: str
