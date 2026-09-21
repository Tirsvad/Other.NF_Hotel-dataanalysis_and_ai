from dataclasses import dataclass
from datetime import date, timedelta

import holidays


@dataclass(frozen=True)
class HolidayPeriod:
    """A holiday, or a run of consecutive days with the same holiday name."""

    name: str
    start_date: date
    end_date: date

    def describe(self) -> str:
        if self.start_date == self.end_date:
            return f"{self.start_date.isoformat()}: {self.name}"
        return f"{self.start_date.isoformat()} to {self.end_date.isoformat()}: {self.name}"


class PublicHolidayCalendar:
    """Public holidays looked up in the ``holidays`` package (not stored in metadata).

    Defaults to Cambodia (``KH``), where the hotel is. ``data/holidays.json`` is
    an export of :meth:`periods`, refreshed by ``scripts/update_holidays.py``.
    """

    def __init__(self, country_code: str = "KH") -> None:
        self._country_code = country_code

    @property
    def country_code(self) -> str:
        return self._country_code

    @staticmethod
    def package_version() -> str:
        return holidays.__version__

    def for_years(self, first_year: int, last_year: int) -> dict[date, str]:
        """Return ``{day: holiday name}`` for every holiday from first to last year."""
        calendar = holidays.country_holidays(
            self._country_code, years=range(first_year, last_year + 1), language="en_US"
        )
        return dict(sorted(calendar.items()))

    def name_on(self, day: date) -> str | None:
        return holidays.country_holidays(self._country_code, years=day.year, language="en_US").get(day)

    def periods(self, first_year: int, last_year: int) -> list[HolidayPeriod]:
        """Consecutive days with the same name are merged into one period."""
        periods: list[HolidayPeriod] = []
        for day, name in self.for_years(first_year, last_year).items():
            last = periods[-1] if periods else None
            if last and last.name == name and day - last.end_date == timedelta(days=1):
                periods[-1] = HolidayPeriod(name, last.start_date, day)
            else:
                periods.append(HolidayPeriod(name, day, day))
        return periods

    def describe(self, first_year: int, last_year: int) -> str:
        """One line per holiday period, for the LLM prompt."""
        return "\n".join(f"- {p.describe()}" for p in self.periods(first_year, last_year))
