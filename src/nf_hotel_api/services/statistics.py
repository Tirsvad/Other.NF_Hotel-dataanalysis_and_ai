from typing import Any

import pandas as pd


class DescriptiveStatsService:
    """Computes descriptive statistics over cleaned booking data."""

    def compute(self, df: pd.DataFrame) -> dict[str, dict[str, Any]]:
        df = df.drop(columns=["booking_id"], errors="ignore")
        described = df.describe(include="all")
        return {
            str(column): {
                str(stat): self._to_jsonable(value)
                for stat, value in described[column].items()
                if pd.notna(value)
            }
            for column in described.columns
        }

    @staticmethod
    def _to_jsonable(value: Any) -> Any:
        if isinstance(value, pd.Timestamp):
            return value.isoformat()
        if hasattr(value, "item"):
            return value.item()
        return value
