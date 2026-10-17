"""Konfigurasi lewat environment variable. Default-nya cukup untuk development."""
import os
from dataclasses import dataclass


@dataclass
class Settings:
    db_path: str = os.getenv("TL_DB_PATH", "trade_lens.db")
    display_tz: str = os.getenv("TL_DISPLAY_TZ", "Asia/Jakarta")
    lookback_hours: int = int(os.getenv("TL_LOOKBACK_HOURS", "5"))
    enable_worker: bool = os.getenv("TL_ENABLE_WORKER", "1") == "1"
    user_agent: str = os.getenv(
        "TL_USER_AGENT",
        "trade-lens/0.1 (open source; ganti dengan kontak kamu)",
    )
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "").strip()
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip() or "gemini-3.5-flash-lite"
    # Legacy names remain as aliases because the existing route reads them.
    huggingface_token: str = os.getenv("GEMINI_API_KEY", "").strip()
    ai_model: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip() or "gemini-3.5-flash-lite"


settings = Settings()
