import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from app.core.config import settings


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(settings.database_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    Path(settings.database_path).parent.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                title TEXT NOT NULL,
                chunk_count INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS questions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                document_id TEXT NOT NULL,
                topic TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                type TEXT NOT NULL,
                question TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS attempts (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                document_id TEXT NOT NULL,
                question_id TEXT NOT NULL,
                question_type TEXT NOT NULL,
                topic TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                score REAL NOT NULL,
                feedback TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )


def add_document(doc: dict[str, Any]) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO documents (id, user_id, filename, title, chunk_count, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                doc["id"],
                doc["user_id"],
                doc["filename"],
                doc["title"],
                doc["chunk_count"],
                utc_now(),
            ),
        )


def list_documents(user_id: str) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM documents WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_document(document_id: str, user_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM documents WHERE id = ? AND user_id = ?",
            (document_id, user_id),
        ).fetchone()
    return dict(row) if row else None


def previous_question_texts(user_id: str, document_id: str, limit: int = 30) -> list[str]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT question FROM questions
            WHERE user_id = ? AND document_id = ?
            ORDER BY created_at DESC LIMIT ?
            """,
            (user_id, document_id, limit),
        ).fetchall()
    return [row["question"] for row in rows]


def add_questions(questions: list[dict[str, Any]]) -> None:
    with connect() as conn:
        conn.executemany(
            """
            INSERT INTO questions
            (id, user_id, document_id, topic, difficulty, type, question, payload, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    q["id"],
                    q["user_id"],
                    q["document_id"],
                    q["topic"],
                    q["difficulty"],
                    q["type"],
                    q["question"],
                    json.dumps(q),
                    utc_now(),
                )
                for q in questions
            ],
        )


def get_question(question_id: str, user_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT payload FROM questions WHERE id = ? AND user_id = ?",
            (question_id, user_id),
        ).fetchone()
    return json.loads(row["payload"]) if row else None


def add_attempt(attempt: dict[str, Any]) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO attempts
            (id, user_id, document_id, question_id, question_type, topic, difficulty, score, feedback, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                attempt["id"],
                attempt["user_id"],
                attempt["document_id"],
                attempt["question_id"],
                attempt["question_type"],
                attempt["topic"],
                attempt["difficulty"],
                float(attempt["score"]),
                attempt["feedback"],
                utc_now(),
            ),
        )


def attempts_for_user(user_id: str) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM attempts WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]
