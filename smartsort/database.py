"""SQLite-backed persistence for scan sessions and applied moves.

SmartSort keeps a small local database so that organizing isn't a one-shot,
forgettable operation: every applied session is recorded with enough detail
to show a history screen and to undo it later.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from smartsort.config import DATABASE_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    folder_path TEXT NOT NULL,
    created_at TEXT NOT NULL,
    total_files INTEGER NOT NULL,
    total_categories INTEGER NOT NULL,
    moved_count INTEGER NOT NULL DEFAULT 0,
    error_count INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'completed',
    undone INTEGER NOT NULL DEFAULT 0,
    kind TEXT NOT NULL DEFAULT 'organize'
);

CREATE TABLE IF NOT EXISTS moves (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES sessions(id),
    file_name TEXT NOT NULL,
    source_path TEXT NOT NULL,
    dest_path TEXT NOT NULL,
    category TEXT NOT NULL,
    size INTEGER NOT NULL,
    undone INTEGER NOT NULL DEFAULT 0
);
"""


@dataclass
class SessionRecord:
    id: int
    folder_path: str
    created_at: str
    total_files: int
    total_categories: int
    moved_count: int
    error_count: int
    status: str
    undone: bool
    kind: str = "organize"


@dataclass
class MoveRecord:
    id: int
    session_id: int
    file_name: str
    source_path: str
    dest_path: str
    category: str
    size: int
    undone: bool


class Database:
    def __init__(self, db_path: Path | str = DATABASE_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.db_path)
        self._connection.row_factory = sqlite3.Row
        self._connection.executescript(SCHEMA)
        self._migrate()
        self._connection.commit()

    def _migrate(self) -> None:
        """Add columns introduced after a user's database already existed."""

        columns = {row["name"] for row in self._connection.execute("PRAGMA table_info(sessions)")}
        if "kind" not in columns:
            self._connection.execute(
                "ALTER TABLE sessions ADD COLUMN kind TEXT NOT NULL DEFAULT 'organize'"
            )

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> "Database":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    def create_session(
        self, folder_path: str, total_files: int, total_categories: int, kind: str = "organize"
    ) -> int:
        cursor = self._connection.execute(
            """
            INSERT INTO sessions (folder_path, created_at, total_files, total_categories, kind)
            VALUES (?, ?, ?, ?, ?)
            """,
            (folder_path, datetime.now().isoformat(timespec="seconds"), total_files, total_categories, kind),
        )
        self._connection.commit()
        return cursor.lastrowid

    def record_move(
        self,
        session_id: int,
        file_name: str,
        source_path: str,
        dest_path: str,
        category: str,
        size: int,
    ) -> None:
        self._connection.execute(
            """
            INSERT INTO moves (session_id, file_name, source_path, dest_path, category, size)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session_id, file_name, source_path, dest_path, category, size),
        )
        self._connection.commit()

    def finalize_session(self, session_id: int, moved_count: int, error_count: int) -> None:
        status = "completed" if error_count == 0 else "completed_with_errors"
        self._connection.execute(
            """
            UPDATE sessions SET moved_count = ?, error_count = ?, status = ?
            WHERE id = ?
            """,
            (moved_count, error_count, status, session_id),
        )
        self._connection.commit()

    def list_sessions(self) -> list[SessionRecord]:
        rows = self._connection.execute(
            "SELECT * FROM sessions ORDER BY created_at DESC, id DESC"
        ).fetchall()
        return [self._row_to_session(row) for row in rows]

    def get_session(self, session_id: int) -> SessionRecord | None:
        row = self._connection.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        return self._row_to_session(row) if row else None

    def get_moves(self, session_id: int) -> list[MoveRecord]:
        rows = self._connection.execute(
            "SELECT * FROM moves WHERE session_id = ? ORDER BY id", (session_id,)
        ).fetchall()
        return [self._row_to_move(row) for row in rows]

    def mark_session_undone(self, session_id: int) -> None:
        self._connection.execute(
            "UPDATE moves SET undone = 1 WHERE session_id = ?", (session_id,)
        )
        self._connection.execute(
            "UPDATE sessions SET undone = 1, status = 'undone' WHERE id = ?", (session_id,)
        )
        self._connection.commit()

    @staticmethod
    def _row_to_session(row: sqlite3.Row) -> SessionRecord:
        return SessionRecord(
            id=row["id"],
            folder_path=row["folder_path"],
            created_at=row["created_at"],
            total_files=row["total_files"],
            total_categories=row["total_categories"],
            moved_count=row["moved_count"],
            error_count=row["error_count"],
            status=row["status"],
            undone=bool(row["undone"]),
            kind=row["kind"] if "kind" in row.keys() else "organize",
        )

    @staticmethod
    def _row_to_move(row: sqlite3.Row) -> MoveRecord:
        return MoveRecord(
            id=row["id"],
            session_id=row["session_id"],
            file_name=row["file_name"],
            source_path=row["source_path"],
            dest_path=row["dest_path"],
            category=row["category"],
            size=row["size"],
            undone=bool(row["undone"]),
        )
