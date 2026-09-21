from fastapi import APIRouter, Depends, HTTPException, status

from nf_hotel_api.api.deps import get_report_service
from nf_hotel_api.core.config import Settings, get_settings
from nf_hotel_api.core.security import require_api_key
from nf_hotel_api.domain.schemas import BookingBatch, ReportResponse
from nf_hotel_api.repositories.booking_repository import (
    CsvBookingRepository,
    JsonBookingRepository,
)
from nf_hotel_api.services.llm_report import LLMServiceError
from nf_hotel_api.services.report import ReportService

router = APIRouter(
    prefix="/report",
    tags=["report"],
    dependencies=[Depends(require_api_key)],
)


@router.post("/from-file", response_model=ReportResponse)
async def generate_report_from_file(
    report_service: ReportService = Depends(get_report_service),
    settings: Settings = Depends(get_settings),
) -> ReportResponse:
    """Generate the analytics report from the bundled nf_hotel_bookings.csv file."""
    repository = CsvBookingRepository(settings.default_data_path, settings.csv_separator)
    try:
        return await report_service.generate(repository)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except LLMServiceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post("/from-json", response_model=ReportResponse)
async def generate_report_from_json(
    batch: BookingBatch,
    report_service: ReportService = Depends(get_report_service),
) -> ReportResponse:
    """Generate the analytics report from booking records supplied as JSON."""
    records = [record.model_dump() for record in batch.records]
    repository = JsonBookingRepository(records)
    try:
        return await report_service.generate(repository)
    except LLMServiceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
