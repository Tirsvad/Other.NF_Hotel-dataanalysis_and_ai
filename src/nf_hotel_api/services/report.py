from nf_hotel_api.domain.schemas import ReportResponse
from nf_hotel_api.repositories.booking_repository import BookingRepository
from nf_hotel_api.services.cleaning import DataCleaningService
from nf_hotel_api.services.llm_report import LLMReportService
from nf_hotel_api.services.statistics import DescriptiveStatsService


class ReportService:
    """Application-layer use case: raw bookings -> full analytics report."""

    def __init__(
        self,
        cleaning_service: DataCleaningService,
        stats_service: DescriptiveStatsService,
        llm_service: LLMReportService,
    ) -> None:
        self._cleaning_service = cleaning_service
        self._stats_service = stats_service
        self._llm_service = llm_service

    async def generate(self, repository: BookingRepository) -> ReportResponse:
        raw_df = repository.load()
        clean_df = self._cleaning_service.clean(raw_df)
        descriptive_stats = self._stats_service.compute(clean_df)
        llm_report = await self._llm_service.generate_report(descriptive_stats)
        return ReportResponse(descriptive_stats=descriptive_stats, llm_report=llm_report)
