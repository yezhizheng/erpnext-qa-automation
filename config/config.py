"""Runtime configuration for the ERPNext UI test suite."""

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    base_url: str = os.getenv("ERPNEXT_BASE_URL", "http://localhost:8080")
    username: str = os.getenv("ERPNEXT_USERNAME", "administrator")
    password: str = os.getenv("ERPNEXT_PASSWORD", "admin")
    timeout_ms: int = int(os.getenv("ERPNEXT_TIMEOUT_MS", "15000"))


settings = Settings()

