from fastapi.testclient import TestClient

from nf_hotel_api.api.deps import get_llm_service
from nf_hotel_api.main import app

API_KEY = "test-api-key"


class _FakeLLMService:
    async def generate_report(self, descriptive_stats: dict) -> str:
        return "## Fake Report"


app.dependency_overrides[get_llm_service] = lambda: _FakeLLMService()
client = TestClient(app)


def test_health_check_is_public():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_report_endpoint_rejects_missing_api_key():
    response = client.post("/api/v1/report/from-file")
    assert response.status_code == 401


def test_report_endpoint_rejects_wrong_api_key():
    response = client.post(
        "/api/v1/report/from-file", headers={"X-API-Key": "wrong-key"}
    )
    assert response.status_code == 401


def test_report_from_file_returns_stats_and_llm_report():
    response = client.post(
        "/api/v1/report/from-file", headers={"X-API-Key": API_KEY}
    )
    assert response.status_code == 200
    body = response.json()
    assert "booking_id" not in body["descriptive_stats"]
    assert body["llm_report"] == "## Fake Report"


def test_report_from_json_returns_stats_and_llm_report(dirty_bookings_df):
    records = dirty_bookings_df.to_dict(orient="records")
    response = client.post(
        "/api/v1/report/from-json",
        headers={"X-API-Key": API_KEY},
        json={"records": records},
    )
    assert response.status_code == 200
    body = response.json()
    assert "booking_id" not in body["descriptive_stats"]
    assert body["llm_report"] == "## Fake Report"
