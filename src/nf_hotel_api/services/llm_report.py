import json
import re
from typing import Any

import httpx

from nf_hotel_api.domain.metadata import HotelMetadata

_PROMPT_TEMPLATE = """You work as a data analyst and in marketing to optimize hotel operations.
User cannot interact with you so do not ask questions.
Respond in markdown format.
{hotel_context}We have extract descriptive analysis:\n
{descriptive_analysis_data}"""

_HOTEL_CONTEXT_TEMPLATE = """Hotel reference data (room types the bookings refer to):
{room_catalogue}
The column prize_per_nigth is the price the customer actually paid per night.
The column revenue is nights x prize_per_nigth for non-cancelled bookings.
"""

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
    ) -> None:
        self._metadata = metadata
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds

    async def generate_report(self, descriptive_stats: dict[str, Any]) -> str:
        hotel_context = (
            _HOTEL_CONTEXT_TEMPLATE.format(room_catalogue=self._metadata.describe())
            if self._metadata
            else ""
        )
        prompt = _PROMPT_TEMPLATE.format(
            hotel_context=hotel_context,
            descriptive_analysis_data=json.dumps(descriptive_stats, indent=2),
        )

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

    @staticmethod
    def _strip_thinking(content: str) -> str:
        return _THINK_BLOCK_PATTERN.sub("", content).strip()
