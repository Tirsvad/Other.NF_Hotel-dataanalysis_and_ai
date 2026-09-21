from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import pandas as pd


class BookingRepository(ABC):
    """Abstraction over "where booking records come from"."""

    @abstractmethod
    def load(self) -> pd.DataFrame:
        """Return the raw (unclean) bookings as a DataFrame."""


class CsvBookingRepository(BookingRepository):
    """Loads bookings from the on-disk NF Hotel CSV export."""

    def __init__(self, path: Path, separator: str = ";") -> None:
        self._path = path
        self._separator = separator

    def load(self) -> pd.DataFrame:
        if not self._path.exists():
            raise FileNotFoundError(f"Booking data file not found: {self._path}")
        return pd.read_csv(self._path, sep=self._separator)


class JsonBookingRepository(BookingRepository):
    """Loads bookings from JSON records supplied directly by the caller."""

    def __init__(self, records: list[dict[str, Any]]) -> None:
        self._records = records

    def load(self) -> pd.DataFrame:
        return pd.DataFrame.from_records(self._records)
