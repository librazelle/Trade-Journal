"""SQLite sederhana. Satu koneksi per pemanggilan, aman dipakai dari thread mana pun."""
import sqlite3
from contextlib import contextmanager

from .config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS news (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id TEXT NOT NULL UNIQUE,
    source TEXT NOT NULL,
    tier INTEGER NOT NULL,
    status TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT,
    summary TEXT,
    tags TEXT NOT NULL DEFAULT '',
    impact INTEGER NOT NULL DEFAULT 0,
    published_at TEXT NOT NULL,
    ingested_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_news_published ON news(published_at);

CREATE TABLE IF NOT EXISTS news_ai_summaries (
    news_id INTEGER PRIMARY KEY,
    explanation TEXT NOT NULL,
    model TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS macro_reactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    instrument TEXT NOT NULL,
    release_time TEXT NOT NULL,
    expected_direction TEXT NOT NULL CHECK (expected_direction IN ('up', 'down')),
    price_before REAL NOT NULL,
    price_after_15m REAL NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_macro_reactions_event ON macro_reactions(event_type, instrument);

CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument TEXT NOT NULL DEFAULT 'XAUUSD',
    direction TEXT NOT NULL CHECK (direction IN ('long', 'short')),
    entry_price REAL NOT NULL,
    entry_time TEXT NOT NULL,
    lot REAL,
    sl REAL,
    tp REAL,
    note TEXT NOT NULL DEFAULT '',
    context_json TEXT NOT NULL DEFAULT '[]',
    econ_context_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.db_path, check_same_thread=False, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = _connect()
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(SCHEMA)
        trade_columns = {row[1] for row in conn.execute("PRAGMA table_info(trades)").fetchall()}
        if "econ_context_json" not in trade_columns:
            conn.execute("ALTER TABLE trades ADD COLUMN econ_context_json TEXT NOT NULL DEFAULT '[]'")
        conn.commit()
    finally:
        conn.close()


@contextmanager
def get_db():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
