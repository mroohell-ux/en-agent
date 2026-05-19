from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
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
        CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, user_id TEXT, created_at TEXT);
        CREATE TABLE IF NOT EXISTS cards (id TEXT PRIMARY KEY, session_id TEXT, target TEXT, type TEXT, topic TEXT);
        CREATE TABLE IF NOT EXISTS answers (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, card_id TEXT, user_answer TEXT, score INTEGER, created_at TEXT);
        CREATE TABLE IF NOT EXISTS known_items (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, type TEXT, text TEXT, normalized_text TEXT, source_card_id TEXT, strength INTEGER DEFAULT 1, created_at TEXT, last_seen_at TEXT);
        CREATE TABLE IF NOT EXISTS weak_items (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, type TEXT, text TEXT, mistake_example TEXT, correction TEXT, explanation TEXT, wrong_count INTEGER DEFAULT 0, right_count INTEGER DEFAULT 0, next_review_at TEXT, priority TEXT);
        CREATE TABLE IF NOT EXISTS round_summaries (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, summary_json TEXT, created_at TEXT);
        CREATE TABLE IF NOT EXISTS review_items (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, item_type TEXT, text TEXT, prompt TEXT, next_review_at TEXT, status TEXT);
        """
    )
    conn.commit()
    conn.close()


def normalize(text: str) -> str:
    return " ".join(text.lower().split())


def get_memory(user_id: str) -> dict:
    conn = get_conn(); cur = conn.cursor()
    known = [dict(r) for r in cur.execute("SELECT * FROM known_items WHERE user_id=?", (user_id,)).fetchall()]
    weak = [dict(r) for r in cur.execute("SELECT * FROM weak_items WHERE user_id=?", (user_id,)).fetchall()]
    due = [dict(r) for r in cur.execute("SELECT * FROM review_items WHERE user_id=? AND next_review_at <= ?", (user_id, datetime.utcnow().isoformat())).fetchall()]
    conn.close()
    return {
        "knownTopics": [k["text"] for k in known if k["type"] == "TOPIC"],
        "knownPatterns": [k["text"] for k in known if k["type"] == "PATTERN"],
        "knownChunks": [k["text"] for k in known if k["type"] == "CHUNK"],
        "weakGrammarPoints": [w["text"] for w in weak if w["type"] == "GRAMMAR"],
        "weakPatterns": [w["text"] for w in weak if w["type"] == "PATTERN"],
        "dueReviewItems": due,
    }


def save_known(user_id: str, item_type: str, text: str, source_card_id: str) -> None:
    conn = get_conn(); cur = conn.cursor(); now = datetime.utcnow().isoformat()
    cur.execute("INSERT INTO known_items (user_id,type,text,normalized_text,source_card_id,created_at,last_seen_at) VALUES (?,?,?,?,?,?,?)", (user_id,item_type,text,normalize(text),source_card_id,now,now))
    conn.commit(); conn.close()


def save_review(user_id: str, item_type: str, text: str, prompt: str, days: int = 1) -> None:
    conn = get_conn(); cur = conn.cursor()
    cur.execute("INSERT INTO review_items (user_id,item_type,text,prompt,next_review_at,status) VALUES (?,?,?,?,?,?)", (user_id,item_type,text,prompt,(datetime.utcnow()+timedelta(days=days)).isoformat(),"due"))
    conn.commit(); conn.close()
