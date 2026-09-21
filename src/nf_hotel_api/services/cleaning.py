import pandas as pd

from nf_hotel_api.domain.metadata import HotelMetadata

_DATE_COLUMNS = ("booking_date", "arrival_date")

_NUMERIC_COLUMNS = (
    "booking_id",
    "is_canceled",
    "lead_time",
    "arrival_date_week_number",
    "arrival_date_day_of_month",
    "stays_in_weekend_nights",
    "stays_in_week_nights",
    "adults",
    "children",
    "babies",
    "is_repeated_guest",
    "previous_cancellations",
    "booking_changes",
    "agent",
    "required_car_parking_spaces",
    "total_of_special_requests",
)

_CATEGORICAL_COLUMNS = (
    "hotel",
    "meal",
    "country",
    "market_segment",
    "assigned_room_type",
    "deposit_type",
    "customer_type",
)

# Accepted date layouts: ISO (JSON payloads) and day-first (the CSV export).
_DATE_FORMATS = ("%Y-%m-%d", "%d-%m-%Y")

_PRICE_COLUMN = "prize_per_nigth"

_EMPTY_MARKERS = ("", "nan", "null", "none", "n/a", "na")

# Bookings with more occupants than this in a single field are treated as
# data-entry errors (e.g. "55 adults" in one room) rather than real guests.
_MAX_PLAUSIBLE_ADULTS = 10
_MAX_PLAUSIBLE_CHILDREN = 5


class DataCleaningService:
    """Cleans raw booking data before it is analyzed.

    Each private method covers one classic pandas cleaning concern, run in
    a fixed order via :meth:`clean`. Once the data is clean, :meth:`_add_pricing`
    derives room size and revenue using the hotel metadata.
    """

    def __init__(self, metadata: HotelMetadata) -> None:
        self._metadata = metadata

    def clean(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df = self._fix_wrong_format(df)
        df = self._clean_empty_cells(df)
        df = self._fix_wrong_data(df)
        df = self._remove_duplicates(df)
        df = self._add_pricing(df)
        return df.reset_index(drop=True)

    def _fix_wrong_format(self, df: pd.DataFrame) -> pd.DataFrame:
        """Coerce columns into their expected dtype (dates, numbers)."""
        for column in _DATE_COLUMNS:
            if column in df.columns:
                df[column] = self._parse_dates(df[column])

        for column in _NUMERIC_COLUMNS:
            if column in df.columns:
                df[column] = pd.to_numeric(df[column], errors="coerce")

        if _PRICE_COLUMN in df.columns:
            df[_PRICE_COLUMN] = pd.to_numeric(df[_PRICE_COLUMN], errors="coerce")

        for column in _CATEGORICAL_COLUMNS:
            if column in df.columns:
                df[column] = df[column].astype("string").str.strip()

        return df

    @staticmethod
    def _parse_dates(series: pd.Series) -> pd.Series:
        """Parse each value with the first matching layout in ``_DATE_FORMATS``.

        A single ``pd.to_datetime`` call would infer one layout from the first
        value and turn every date in the other layout into NaT, which would
        then silently drop those rows.
        """
        parsed = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")
        for date_format in _DATE_FORMATS:
            candidate = pd.to_datetime(series, format=date_format, errors="coerce")
            parsed = parsed.fillna(candidate)
        return parsed

    def _clean_empty_cells(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize placeholder/blank values to NA, then fill sensibly."""
        for column in _CATEGORICAL_COLUMNS:
            if column not in df.columns:
                continue
            lowered = df[column].str.lower()
            df.loc[lowered.isin(_EMPTY_MARKERS), column] = pd.NA
            df[column] = df[column].fillna("Unknown")

        for column in _NUMERIC_COLUMNS:
            if column in df.columns:
                df[column] = df[column].fillna(0)

        df = df.dropna(subset=[c for c in _DATE_COLUMNS if c in df.columns])
        return df

    def _fix_wrong_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Correct implausible values without discarding the whole row."""
        if "adults" in df.columns:
            df["adults"] = df["adults"].clip(lower=0, upper=_MAX_PLAUSIBLE_ADULTS)
        if "children" in df.columns:
            df["children"] = df["children"].clip(lower=0, upper=_MAX_PLAUSIBLE_CHILDREN)
        if "babies" in df.columns:
            df["babies"] = df["babies"].clip(lower=0, upper=_MAX_PLAUSIBLE_CHILDREN)

        # A booking with zero occupants in every guest field is invalid;
        # treat it as a single adult rather than dropping the record.
        guest_columns = [c for c in ("adults", "children", "babies") if c in df.columns]
        if guest_columns:
            no_guests = (df[guest_columns].sum(axis=1) == 0)
            if "adults" in df.columns:
                df.loc[no_guests, "adults"] = 1

        for column in ("lead_time", "booking_changes", "previous_cancellations", "agent"):
            if column in df.columns:
                df[column] = df[column].clip(lower=0)

        return df

    def _remove_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Drop repeated bookings, ignoring the (non-business) id column."""
        subset = [c for c in df.columns if c != "booking_id"]
        return df.drop_duplicates(subset=subset, keep="first")

    def _add_pricing(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add room size and revenue, and fill in missing prices.

        ``prize_per_nigth`` in the data is the price the customer actually
        paid, so it is kept as-is. Only a missing or negative price is replaced
        with the room type's standard price from the hotel metadata. Room types
        outside the metadata get no size and no invented price.
        """
        if "assigned_room_type" not in df.columns:
            return df

        room_types = self._metadata.room_types
        room_type = df["assigned_room_type"].astype("string").str.upper()
        standard_price = room_type.map(
            {code: room.standard_price_per_night for code, room in room_types.items()}
        ).astype("float64")

        paid_price = df.get(_PRICE_COLUMN, pd.Series(float("nan"), index=df.index))
        df[_PRICE_COLUMN] = paid_price.where(paid_price >= 0).fillna(standard_price)
        df["room_size"] = room_type.map(
            {code: room.size for code, room in room_types.items()}
        ).fillna("Unknown")

        nights_columns = [
            c for c in ("stays_in_weekend_nights", "stays_in_week_nights") if c in df.columns
        ]
        if nights_columns:
            # Cancelled bookings bring in no money.
            billable = df["is_canceled"] == 0 if "is_canceled" in df.columns else True
            df["revenue"] = df[nights_columns].sum(axis=1) * df[_PRICE_COLUMN] * billable
        return df
