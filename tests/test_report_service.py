import pytest

from nf_hotel_api.repositories.booking_repository import JsonBookingRepository
from nf_hotel_api.services.cleaning import DataCleaningService
from nf_hotel_api.services.report import ReportService
from nf_hotel_api.services.statistics import DescriptiveStatsService


class _FakeLLMService:
    async def generate_report(self, descriptive_stats: dict) -> str:
        assert "booking_id" not in descriptive_stats
        return "## Fake Report"


@pytest.mark.asyncio
async def test_generate_produces_stats_and_llm_report(dirty_bookings_df, hotel_metadata):
    repository = JsonBookingRepository(dirty_bookings_df.to_dict(orient="records"))
    service = ReportService(
        cleaning_service=DataCleaningService(hotel_metadata),
        stats_service=DescriptiveStatsService(),
        llm_service=_FakeLLMService(),
    )

    result = await service.generate(repository)

    assert result.llm_report == "## Fake Report"
    assert "adults" in result.descriptive_stats
    assert "booking_id" not in result.descriptive_stats
