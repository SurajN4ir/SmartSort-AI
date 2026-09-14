"""Plain data structures shared across the scanning/planning/organizing pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class ScannedFile:
    """A single file discovered by the scanner, before any categorization."""

    name: str
    path: Path
    extension: str
    size: int
    modified_time: datetime

    @property
    def size_display(self) -> str:
        return format_size(self.size)


@dataclass
class ClassifiedFile:
    """A scanned file with a category assigned by the categorization engine.

    ``category`` is the top-level folder (e.g. "Documents", "University") and
    stays a flat string so the existing grouping/icon/dropdown logic never
    has to know about nesting. ``subpath`` holds any additional folder
    levels below it (e.g. ("Machine Learning", "Assignments")) and is empty
    for plain rule-based results. ``confidence``/``source`` record where a
    classification came from, for optional display in the UI.
    """

    scanned: ScannedFile
    category: str
    subpath: tuple[str, ...] = ()
    confidence: float | None = None
    source: str = "rule"

    @property
    def name(self) -> str:
        return self.scanned.name

    @property
    def path(self) -> Path:
        return self.scanned.path

    @property
    def size(self) -> int:
        return self.scanned.size

    @property
    def category_path(self) -> tuple[str, ...]:
        return (self.category, *self.subpath)


@dataclass
class PlannedMove:
    """A single proposed relocation: source path -> destination path."""

    classified: ClassifiedFile
    source: Path
    destination: Path
    category: str
    subpath: tuple[str, ...] = ()
    confidence: float | None = None
    source_kind: str = "rule"
    selected: bool = True

    @property
    def name(self) -> str:
        return self.classified.name

    @property
    def size(self) -> int:
        return self.classified.size

    @property
    def is_ai_suggested(self) -> bool:
        return self.source_kind == "ai"


@dataclass
class OrganizePlan:
    """The full set of proposed moves for one scanned folder."""

    root: Path
    moves: list[PlannedMove] = field(default_factory=list)
    skipped: list[ScannedFile] = field(default_factory=list)

    @property
    def categories(self) -> dict[str, list[PlannedMove]]:
        grouped: dict[str, list[PlannedMove]] = {}
        for move in self.moves:
            grouped.setdefault(move.category, []).append(move)
        return grouped

    @property
    def selected_moves(self) -> list[PlannedMove]:
        return [m for m in self.moves if m.selected]

    @property
    def total_files(self) -> int:
        return len(self.moves)

    @property
    def total_categories(self) -> int:
        return len(self.categories)


@dataclass
class ApplyResult:
    """Outcome of executing an OrganizePlan."""

    session_id: int
    moved: list[PlannedMove] = field(default_factory=list)
    errors: list[tuple[PlannedMove, str]] = field(default_factory=list)

    @property
    def moved_count(self) -> int:
        return len(self.moved)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def folders_created(self) -> int:
        return len({m.destination.parent for m in self.moved})


def pluralize(count: int, singular: str, plural: str | None = None) -> str:
    noun = singular if count == 1 else (plural or f"{singular}s")
    return f"{count} {noun}"


def format_size(num_bytes: int) -> str:
    """Human-readable file size, e.g. 1536 -> '1.5 KB'."""

    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"
