"""Runtime configuration shared by ERPNext UI and API tests."""

from dataclasses import dataclass
import os

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    base_url: str = os.getenv("ERPNEXT_BASE_URL", "http://localhost:8080")
    username: str = os.getenv("ERPNEXT_USERNAME", "administrator")
    password: str = os.getenv("ERPNEXT_PASSWORD", "")
    timeout_ms: int = int(os.getenv("ERPNEXT_TIMEOUT_MS", "15000"))


settings = Settings()

