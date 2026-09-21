import secrets

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from nf_hotel_api.core.config import Settings, get_settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class ApiKeyAuthenticator:
    """Validates inbound requests against the configured API key.

    Uses a constant-time comparison to avoid leaking key length/content via
    response-time side channels.
    """

    def __call__(
        self,
        api_key: str | None = Security(_api_key_header),
        settings: Settings = Depends(get_settings),
    ) -> None:
        if not api_key or not secrets.compare_digest(api_key, settings.api_key):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing API key",
            )


require_api_key = ApiKeyAuthenticator()
