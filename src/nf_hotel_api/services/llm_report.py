import json
import re
from typing import Any

import httpx

from nf_hotel_api.domain.metadata import HotelMetadata
from nf_hotel_api.services.public_holidays import PublicHolidayCalendar

_PROMPT_TEMPLATE = """You work as a data analyst and in marketing to optimize hotel operations.
User cannot interact with you so do not ask questions.
Respond in markdown format.
{hotel_context}We have extract descriptive analysis:\n
{descriptive_analysis_data}"""

_HOTEL_CONTEXT_TEMPLATE = """Hotel reference data (room types the bookings refer to):
{room_catalogue}
The column prize_per_nigth is the price the customer actually paid per night.
The column revenue is nights x prize_per_nigth for non-cancelled bookings.
{holidays}"""

# Reasoning models (e.g. Qwen3) may wrap their internal reasoning in
# <think>...</think>; that content must never reach the API response.
_THINK_BLOCK_PATTERN = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


class LLMServiceError(RuntimeError):
    """Raised when the LLM backend cannot produce a report."""


class LLMReportService:
    """Turns descriptive statistics into a marketing/ops narrative via an LLM."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float,
        metadata: HotelMetadata | None = None,
        holiday_calendar: PublicHolidayCalendar | None = None,
    ) -> None:
        self._metadata = metadata
        self._holiday_calendar = holiday_calendar
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds

    async def generate_report(self, descriptive_stats: dict[str, Any]) -> str:
        prompt = self._build_prompt(descriptive_stats)

        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
        }
        headers = {"Authorization": f"Bearer {self._api_key}"}

        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(
                    f"{self._base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMServiceError(f"LLM backend request failed: {exc}") from exc

        data = response.json()
        try:
            raw_content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise LLMServiceError(f"Unexpected LLM response shape: {data}") from exc

        return self._strip_thinking(raw_content)

    def _build_prompt(self, descriptive_stats: dict[str, Any]) -> str:
        hotel_context = (
            _HOTEL_CONTEXT_TEMPLATE.format(
                room_catalogue=self._metadata.describe(),
                holidays=self._holiday_section(descriptive_stats),
            )
            if self._metadata
            else ""
        )
        return _PROMPT_TEMPLATE.format(
            hotel_context=hotel_context,
            descriptive_analysis_data=json.dumps(descriptive_stats, indent=2),
        )

    def _holiday_section(self, descriptive_stats: dict[str, Any]) -> str:
        """Public holidays for the years the bookings' arrival dates span."""
        if self._holiday_calendar is None:
            return ""
        arrival = descriptive_stats.get("arrival_date", {})
        try:
            first_year = int(str(arrival["min"])[:4])
            last_year = int(str(arrival["max"])[:4])
        except (KeyError, ValueError):
            return ""
        return f"Public holidays:\n{self._holiday_calendar.describe(first_year, last_year)}\n"

    @staticmethod
    def _strip_thinking(content: str) -> str:
        return _THINK_BLOCK_PATTERN.sub("", content).strip()
