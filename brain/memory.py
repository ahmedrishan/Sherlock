"""SQLite-based local memory persistence for Sherlock (Mini Jarvis).

Provides short-term session conversation history tracking and long-term
user fact / preference storage using standard Python sqlite3.
"""

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import config
from utils.logger import get_logger

logger = get_logger(__name__)


class MemoryManager:
    """Manages short-term conversation turns and long-term user facts via SQLite."""

    def __init__(self, db_path: str | Path | None = None):
        """Initializes MemoryManager and prepares the database schema."""
        if db_path is None:
            base_dir = getattr(config, "BASE_DIR", Path(__file__).resolve().parent.parent)
            db_path = Path(base_dir) / "data" / "memory.db"

        self.db_path = Path(db_path)
        os.makedirs(self.db_path.parent, exist_ok=True)
        logger.info(f"Initializing MemoryManager with DB at: {self.db_path}")
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Returns a connected sqlite3 database object."""
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Creates table schemas if they do not exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_facts (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at DATETIME
                )
            """)
            conn.commit()

    def add_turn(self, role: str, content: str) -> None:
        """Records a user or assistant conversation message turn.

        Args:
            role (str): Sender role (e.g. 'user', 'assistant').
            content (str): Transcribed or synthesized message content.
        """
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO conversations (timestamp, role, content) VALUES (?, ?, ?)",
                (now, role, content),
            )
            conn.commit()
        logger.debug(f"Recorded turn [{role}]: '{content[:40]}...'")

    def get_recent_history(self, limit: int = 6) -> list[dict[str, str]]:
        """Retrieves the last N conversation turns in chronological order.

        Args:
            limit (int): Maximum number of recent turns to retrieve.

        Returns:
            list[dict[str, str]]: List of dicts in format [{"role": ..., "content": ...}].
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT role, content FROM conversations ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            rows = cursor.fetchall()

        # Reverse to return in chronological order
        return [{"role": row[0], "content": row[1]} for row in reversed(rows)]

    def set_fact(self, key: str, value: str) -> None:
        """Inserts or updates a long-term key-value user fact/preference.

        Args:
            key (str): Fact key identifier (e.g. 'home_city').
            value (str): Preference value (e.g. 'Trivandrum').
        """
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO user_facts (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
                """,
                (key, value, now),
            )
            conn.commit()
        logger.info(f"Updated user fact: '{key}' = '{value}'")

    def get_all_facts(self) -> dict[str, str]:
        """Returns all stored long-term user facts as a dictionary.

        Returns:
            dict[str, str]: Dictionary mapping fact keys to values.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM user_facts")
            rows = cursor.fetchall()
        return {row[0]: row[1] for row in rows}

    def clear_short_term_memory(self) -> None:
        """Clears short-term session conversation history while retaining long-term facts."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM conversations")
            conn.commit()
        logger.info("Short-term conversation history cleared.")
