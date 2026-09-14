"""Executes an OrganizePlan on disk, and can undo a previously applied session."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

from smartsort.database import Database
from smartsort.models import ApplyResult, OrganizePlan, PlannedMove

MoveProgressCallback = Callable[[PlannedMove, bool], None]


class FileOrganizer:
    """Moves files according to a plan, recording every move for later undo."""

    def __init__(self, database: Database):
        self.database = database

    def apply(
        self, plan: OrganizePlan, progress_callback: MoveProgressCallback | None = None
    ) -> ApplyResult:
        moves = plan.selected_moves
        session_id = self.database.create_session(
            folder_path=str(plan.root),
            total_files=len(moves),
            total_categories=len({m.category for m in moves}),
        )
        result = ApplyResult(session_id=session_id)

        for move in moves:
            try:
                move.destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(move.source), str(move.destination))
                self.database.record_move(
                    session_id=session_id,
                    file_name=move.name,
                    source_path=str(move.source),
                    dest_path=str(move.destination),
                    category=move.category,
                    size=move.size,
                )
                result.moved.append(move)
                if progress_callback:
                    progress_callback(move, True)
            except OSError as exc:
                result.errors.append((move, str(exc)))
                if progress_callback:
                    progress_callback(move, False)

        self.database.finalize_session(session_id, result.moved_count, result.error_count)
        return result

    def undo(self, session_id: int) -> tuple[int, int]:
        """Move files back to their original locations. Returns (restored, failed)."""

        moves = [m for m in self.database.get_moves(session_id) if not m.undone]
        restored = 0
        failed = 0

        for move in moves:
            source = Path(move.dest_path)
            destination = Path(move.source_path)
            try:
                if source.exists():
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(source), str(destination))
                restored += 1
            except OSError:
                failed += 1

        self.database.mark_session_undone(session_id)
        return restored, failed
