"""Directory scanning: turns a folder on disk into a list of ScannedFile records."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from datetime import datetime
from pathlib import Path

from smartsort.models import ScannedFile

ProgressCallback = Callable[[int, int], None]


class FileScanner:
    """Walks a directory and collects lightweight metadata for each file found.

    Only files directly inside the target directory are collected by default.
    SmartSort organizes a single messy folder (e.g. Downloads) rather than
    reaching into subfolders the user may have already organized themselves.
    """

    def __init__(self, recursive: bool = False):
        self.recursive = recursive

    def scan(
        self, directory: Path, progress_callback: ProgressCallback | None = None
    ) -> list[ScannedFile]:
        directory = Path(directory)
        if not directory.exists():
            raise FileNotFoundError(f"Directory does not exist: {directory}")
        if not directory.is_dir():
            raise NotADirectoryError(f"Not a directory: {directory}")

        entries = list(self._iter_entries(directory))
        total = len(entries)
        results: list[ScannedFile] = []

        for index, entry in enumerate(entries, start=1):
            try:
                results.append(self._read_entry(entry))
            except (OSError, PermissionError):
                # Skip files that vanish or are locked mid-scan rather than aborting.
                pass
            if progress_callback:
                progress_callback(index, total)

        return results

    def _iter_entries(self, directory: Path) -> Iterator[Path]:
        if self.recursive:
            for path in directory.rglob("*"):
                if path.is_file():
                    yield path
        else:
            for path in directory.iterdir():
                if path.is_file():
                    yield path

    def _read_entry(self, path: Path) -> ScannedFile:
        stat = path.stat()
        return ScannedFile(
            name=path.name,
            path=path,
            extension=path.suffix.lower(),
            size=stat.st_size,
            modified_time=datetime.fromtimestamp(stat.st_mtime),
        )
