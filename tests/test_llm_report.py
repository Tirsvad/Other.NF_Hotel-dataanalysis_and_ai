import httpx
import pytest

from nf_hotel_api.services.llm_report import LLMReportService, LLMServiceError


def test_strip_thinking_removes_think_block():
    raw = "<think>internal reasoning that must not leak</think>## Report\nBody text"
    assert LLMReportService._strip_thinking(raw) == "## Report\nBody text"


def test_strip_thinking_is_noop_when_no_think_block():
    raw = "## Report\nBody text"
    assert LLMReportService._strip_thinking(raw) == raw


class _FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("POST", "http://fake/chat/completions")
            raise httpx.HTTPStatusError(
                "error", request=request, response=httpx.Response(self.status_code, request=request)
            )

    def json(self) -> dict:
        return self._payload


class _FakeAsyncClient:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self._status_code = status_code

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, *args) -> None:
        return None

    async def post(self, *args, **kwargs) -> _FakeResponse:
        return _FakeResponse(self._payload, self._status_code)


@pytest.mark.asyncio
async def test_generate_report_strips_thinking_and_returns_content(monkeypatch):
    payload = {
        "choices": [
            {"message": {"content": "<think>hidden</think>## Insights\nBook more direct."}}
        ]
    }
    monkeypatch.setattr(
        "nf_hotel_api.services.llm_report.httpx.AsyncClient",
        lambda timeout: _FakeAsyncClient(payload),
    )

    service = LLMReportService(
        base_url="http://fake/v1", api_key="k", model="m", timeout_seconds=1.0
    )
    report = await service.generate_report({"adults": {"mean": 2}})

    assert report == "## Insights\nBook more direct."


@pytest.mark.asyncio
async def test_generate_report_raises_llm_service_error_on_bad_response(monkeypatch):
    monkeypatch.setattr(
        "nf_hotel_api.services.llm_report.httpx.AsyncClient",
        lambda timeout: _FakeAsyncClient({"unexpected": "shape"}),
    )

    service = LLMReportService(
        base_url="http://fake/v1", api_key="k", model="m", timeout_seconds=1.0
    )

    with pytest.raises(LLMServiceError):
        await service.generate_report({"adults": {"mean": 2}})


def _service_with_context(**kwargs):
    from nf_hotel_api.domain.metadata import HotelMetadata, RoomType
    from nf_hotel_api.services.public_holidays import PublicHolidayCalendar

    metadata = HotelMetadata(
        hotel="NF Hotel",
        room_types={"A": RoomType(size="Small", standard_price_per_night=20, room_count=10)},
    )
    return LLMReportService(
        base_url="http://fake/v1", api_key="k", model="m", timeout_seconds=1.0,
        metadata=metadata, holiday_calendar=PublicHolidayCalendar(), **kwargs,
    )


def test_prompt_lists_public_holidays_for_the_years_in_the_data():
    stats = {"arrival_date": {"min": "2024-01-03T00:00:00", "max": "2024-12-30T00:00:00"}}

    prompt = _service_with_context()._build_prompt(stats)

    assert "Public holidays:" in prompt
    assert "2024-04-13 to 2024-04-16" in prompt
    assert "2023-" not in prompt.split("We have extract")[0]


def test_prompt_skips_holidays_when_arrival_dates_are_unknown():
    prompt = _service_with_context()._build_prompt({"adults": {"mean": 2}})

    assert "Public holidays" not in prompt
    assert "Room type A: Small" in prompt
