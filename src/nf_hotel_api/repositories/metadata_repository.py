from pathlib import Path

from nf_hotel_api.domain.metadata import HotelMetadata


class JsonHotelMetadataRepository:
    """Loads hotel reference data (room types, standard prices, room counts)."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> HotelMetadata:
        if not self._path.exists():
            raise FileNotFoundError(f"Hotel metadata file not found: {self._path}")
        return HotelMetadata.model_validate_json(self._path.read_text(encoding="utf-8"))
