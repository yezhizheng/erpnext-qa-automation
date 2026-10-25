"""Deterministic-enough data factories used by UI tests."""

from datetime import datetime
from secrets import token_hex


class DataGenerator:
    @staticmethod
    def item_code(prefix: str = "UI-ITEM") -> str:
        return f"{prefix}-{datetime.now():%Y%m%d%H%M%S}-{token_hex(2).upper()}"

    @staticmethod
    def item_name() -> str:
        return f"Form Experience Item {datetime.now():%Y%m%d%H%M%S}"

    @staticmethod
    def long_text(length: int = 1200) -> str:
        return "体验测试长文本 " * ((length // 8) + 1)

