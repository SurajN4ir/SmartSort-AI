"""Duplicate file detection.

Groups scanned files that have byte-identical content. A cheap size-based
pre-filter avoids hashing every file -- two files can only be duplicates if
they're already the same size, so hashing only ever runs within a group of
same-sized candidates.

Detection never touches the filesystem beyond reading bytes to hash them --
turning a set of groups into an actual cleanup (moving extra copies out of
the way) is a separate, explicit step handled by build_cleanup_plan.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from smartsort.models import ClassifiedFile, OrganizePlan, PlannedMove, ScannedFile
from smartsort.planner import OrganizationPlanner

HASH_CHUNK_SIZE = 1024 * 1024
DUPLICATES_FOLDER = "Duplicates"


@dataclass
class DuplicateGroup:
    """A set of files with identical content. One is kept in place; the rest are candidates for cleanup."""

    files: list[ScannedFile]
    keep: ScannedFile

    @property
    def duplicates(self) -> list[ScannedFile]:
        return [f for f in self.files if f is not self.keep]

    @property
    def wasted_bytes(self) -> int:
        return sum(f.size for f in self.duplicates)


def _hash_file(path: Path) -> str | None:
    hasher = hashlib.sha256()
    try:
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(HASH_CHUNK_SIZE), b""):
                hasher.update(chunk)
    except OSError:
        return None
    return hasher.hexdigest()


def find_duplicates(files: list[ScannedFile]) -> list[DuplicateGroup]:
    """Finds groups of files with identical content.

    Empty files are skipped -- every empty file is technically "identical"
    to every other, which would just produce noisy, meaningless groups.
    Within each group, the oldest file (by modified time) is kept by
    default; callers/the UI can let the user pick a different one.
    """

    by_size: dict[int, list[ScannedFile]] = {}
    for f in files:
        by_size.setdefault(f.size, []).append(f)

    groups: list[DuplicateGroup] = []
    for size, candidates in by_size.items():
        if size == 0 or len(candidates) < 2:
            continue

        by_hash: dict[str, list[ScannedFile]] = {}
        for f in candidates:
            digest = _hash_file(f.path)
            if digest is None:
                continue
            by_hash.setdefault(digest, []).append(f)

        for hash_files in by_hash.values():
            if len(hash_files) < 2:
                continue
            keeper = min(hash_files, key=lambda f: f.modified_time)
            groups.append(DuplicateGroup(files=hash_files, keep=keeper))

    groups.sort(key=lambda g: -g.wasted_bytes)
    return groups


def build_cleanup_plan(root: Path, groups: list[DuplicateGroup]) -> OrganizePlan:
    """Builds a move plan that relocates every non-kept duplicate into a
    Duplicates/ folder under root, rather than deleting anything -- the
    exact same safe, reviewable, undoable move+apply pipeline used for
    regular organizing.
    """

    planner = OrganizationPlanner()
    plan = OrganizePlan(root=Path(root))
    reserved: set[Path] = set()

    for group in groups:
        for scanned in group.duplicates:
            classified = ClassifiedFile(scanned=scanned, category=DUPLICATES_FOLDER)
            category_dir = plan.root / DUPLICATES_FOLDER
            destination = planner.resolve_destination(category_dir, scanned.name, reserved)
            reserved.add(destination)
            plan.moves.append(
                PlannedMove(
                    classified=classified,
                    source=scanned.path,
                    destination=destination,
                    category=DUPLICATES_FOLDER,
                )
            )

    return plan
