from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from nf_hotel_api.api.v1.router import api_router
from nf_hotel_api.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="NF Hotel Analytics API",
    description="Secure API for descriptive statistics and LLM-generated reports over NF Hotel bookings.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["X-API-Key", "Content-Type"],
)

app.include_router(api_router)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
