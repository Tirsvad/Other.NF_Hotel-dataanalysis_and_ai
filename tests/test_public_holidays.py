from datetime import date

from nf_hotel_api.services.public_holidays import PublicHolidayCalendar


def test_for_years_covers_the_requested_years_in_date_order():
    result = PublicHolidayCalendar().for_years(2022, 2023)

    assert list(result) == sorted(result)
    assert {d.year for d in result} == {2022, 2023}


def test_khmer_new_year_and_water_festival_2024_match_the_official_calendar():
    calendar = PublicHolidayCalendar().for_years(2024, 2024)

    for day in (date(2024, 4, 13), date(2024, 4, 16)):
        assert "Khmer New Year" in calendar[day]
    for day in (date(2024, 11, 14), date(2024, 11, 16)):
        assert "Water Festival" in calendar[day]
    assert "Peace Day" in calendar[date(2024, 12, 29)]


def test_name_on_returns_none_for_a_normal_day():
    calendar = PublicHolidayCalendar()

    assert calendar.name_on(date(2024, 8, 14)) is None
    assert "Pchum Ben" in calendar.name_on(date(2025, 9, 22))


def test_describe_merges_consecutive_days_into_a_range():
    text = PublicHolidayCalendar().describe(2024, 2024)

    assert "- 2024-04-13 to 2024-04-16: Khmer New Year's Day" in text
    assert "- 2024-11-14 to 2024-11-16: Water Festival" in text
    assert "- 2024-01-01: International New Year Day" in text


def test_holidays_json_is_an_up_to_date_export_of_the_package():
    """Fails when the `holidays` package changed: re-run scripts/update_holidays.py."""
    import json
    from pathlib import Path

    document = json.loads(
        (Path(__file__).resolve().parents[1] / "data" / "holidays.json").read_text(encoding="utf-8")
    )
    calendar = PublicHolidayCalendar(document["country"])

    expected = [
        {"name": p.name, "start_date": p.start_date.isoformat(), "end_date": p.end_date.isoformat()}
        for p in calendar.periods(document["first_year"], document["last_year"])
    ]

    assert document["holidays"] == expected


def test_holidays_json_covers_the_booking_years():
    import json
    from pathlib import Path

    document = json.loads(
        (Path(__file__).resolve().parents[1] / "data" / "holidays.json").read_text(encoding="utf-8")
    )

    assert document["first_year"] <= 2022
    assert document["last_year"] >= 2025
