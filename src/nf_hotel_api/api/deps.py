from functools import lru_cache

from fastapi import Depends

from nf_hotel_api.core.config import Settings, get_settings
from nf_hotel_api.domain.metadata import HotelMetadata
from nf_hotel_api.repositories.metadata_repository import JsonHotelMetadataRepository
from nf_hotel_api.services.cleaning import DataCleaningService
from nf_hotel_api.services.llm_report import LLMReportService
from nf_hotel_api.services.report import ReportService
from nf_hotel_api.services.statistics import DescriptiveStatsService


@lru_cache
def get_hotel_metadata() -> HotelMetadata:
    return JsonHotelMetadataRepository(get_settings().metadata_path).load()


def get_cleaning_service(
    metadata: HotelMetadata = Depends(get_hotel_metadata),
) -> DataCleaningService:
    return DataCleaningService(metadata)


@lru_cache
def get_stats_service() -> DescriptiveStatsService:
    return DescriptiveStatsService()


def get_llm_service(
    settings: Settings = Depends(get_settings),
    metadata: HotelMetadata = Depends(get_hotel_metadata),
) -> LLMReportService:
    return LLMReportService(
        metadata=metadata,
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        timeout_seconds=settings.llm_timeout_seconds,
    )


def get_report_service(
    cleaning_service: DataCleaningService = Depends(get_cleaning_service),
    stats_service: DescriptiveStatsService = Depends(get_stats_service),
    llm_service: LLMReportService = Depends(get_llm_service),
) -> ReportService:
    return ReportService(cleaning_service, stats_service, llm_service)
