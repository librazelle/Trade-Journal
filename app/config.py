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
    huggingface_token: str = os.getenv("HF_TOKEN", "").strip()
    ai_model: str = os.getenv("TL_AI_MODEL", "Qwen/Qwen2.5-7B-Instruct").strip() or "Qwen/Qwen2.5-7B-Instruct"


settings = Settings()
