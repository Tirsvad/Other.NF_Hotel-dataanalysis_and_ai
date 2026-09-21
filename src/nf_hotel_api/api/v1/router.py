from fastapi import APIRouter

from nf_hotel_api.api.v1.endpoints import report

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(report.router)
