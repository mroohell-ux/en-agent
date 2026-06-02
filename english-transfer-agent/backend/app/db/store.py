from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "english_agent.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            topic TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS cards (
            id TEXT PRIMARY KEY,
            session_id TEXT,
            target TEXT,
            type TEXT,
            topic TEXT,
            card_json TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            card_id TEXT,
            attempt_number INTEGER,
            user_answer TEXT,
            score INTEGER,
            evaluation_json TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS round_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            summary_json TEXT,
            created_at TEXT
        );
        """
    )
    _ensure_column(cur, "answers", "attempt_number", "INTEGER")
    conn.commit()
    conn.close()


def _ensure_column(cur: sqlite3.Cursor, table: str, column: str, column_type: str) -> None:
    existing_columns = {row[1] for row in cur.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in existing_columns:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
