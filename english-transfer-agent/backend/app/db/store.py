from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "english_agent.db"
logger = logging.getLogger(__name__)


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

        CREATE TABLE IF NOT EXISTS article_sources (
            id TEXT PRIMARY KEY,
            lesson_id TEXT,
            title TEXT,
            url TEXT,
            site TEXT,
            raw_text TEXT,
            published_at TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS article_lessons (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            level TEXT,
            source_id TEXT,
            main_idea TEXT,
            key_points_json TEXT,
            retell_task_json TEXT,
            ielts_tasks_json TEXT,
            progress_json TEXT,
            lesson_json TEXT,
            created_at TEXT,
            updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS teacher_questions (
            id TEXT PRIMARY KEY,
            lesson_id TEXT,
            type TEXT,
            question TEXT,
            question_json TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS useful_language_items (
            id TEXT PRIMARY KEY,
            lesson_id TEXT,
            category TEXT,
            text TEXT,
            item_json TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS speaking_answers (
            id TEXT PRIMARY KEY,
            lesson_id TEXT,
            task_type TEXT,
            task_id TEXT,
            attempt_number INTEGER,
            transcript TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS teacher_corrections (
            id TEXT PRIMARY KEY,
            answer_id TEXT,
            lesson_id TEXT,
            task_type TEXT,
            task_id TEXT,
            score INTEGER,
            correction_json TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS lesson_mistakes (
            id TEXT PRIMARY KEY,
            lesson_id TEXT,
            answer_id TEXT,
            type TEXT,
            original TEXT,
            correction TEXT,
            mistake_json TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS lesson_summaries (
            id TEXT PRIMARY KEY,
            lesson_id TEXT,
            summary_json TEXT,
            created_at TEXT
        );
        """
    )
    _ensure_column(cur, "sessions", "topic", "TEXT")
    _ensure_column(cur, "cards", "card_json", "TEXT")
    _ensure_column(cur, "cards", "created_at", "TEXT")
    _ensure_column(cur, "answers", "attempt_number", "INTEGER")
    _ensure_column(cur, "answers", "evaluation_json", "TEXT")
    conn.commit()
    conn.close()
    logger.info("SQLite schema ready at %s", DB_PATH)


def _ensure_column(cur: sqlite3.Cursor, table: str, column: str, column_type: str) -> None:
    existing_columns = {row[1] for row in cur.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in existing_columns:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
        logger.warning("Added missing SQLite column %s.%s (%s)", table, column, column_type)
