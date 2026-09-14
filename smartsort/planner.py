"""Organization planner: turns classified files into a proposed (but unexecuted) plan."""

from __future__ import annotations

from pathlib import Path

from smartsort.models import ClassifiedFile, OrganizePlan, PlannedMove


class OrganizationPlanner:
    """Builds an OrganizePlan describing where each file would move.

    Nothing on disk is touched here -- this only computes destinations,
    resolving name collisions against both the existing filesystem and
    other moves already placed in the same plan.
    """

    def generate_plan(self, root: Path, classified: list[ClassifiedFile]) -> OrganizePlan:
        root = Path(root)
        plan = OrganizePlan(root=root)
        reserved: set[Path] = set()

        for item in classified:
            category_dir = root.joinpath(*item.category_path)
            destination = self.resolve_destination(category_dir, item.name, reserved)
            reserved.add(destination)
            plan.moves.append(
                PlannedMove(
                    classified=item,
                    source=item.path,
                    destination=destination,
                    category=item.category,
                    subpath=item.subpath,
                    confidence=item.confidence,
                    source_kind=item.source,
                )
            )

        return plan

    def retarget(self, plan: OrganizePlan, move: PlannedMove, new_category: str) -> None:
        """Re-point a single planned move at a different (flat) category folder.

        A manual override always collapses back to a flat, single-level
        category -- if the move came from the semantic classifier with a
        deeper suggested path, that suggestion is discarded in favor of the
        user's explicit choice.
        """

        reserved = {m.destination for m in plan.moves if m is not move}
        category_dir = plan.root / new_category
        move.category = new_category
        move.subpath = ()
        move.source_kind = "manual"
        move.confidence = None
        move.destination = self.resolve_destination(category_dir, move.name, reserved)

    def resolve_destination(
        self, category_dir: Path, filename: str, reserved: set[Path]
    ) -> Path:
        candidate = category_dir / filename
        if candidate not in reserved and not candidate.exists():
            return candidate

        stem = Path(filename).stem
        suffix = Path(filename).suffix
        counter = 1
        while True:
            candidate = category_dir / f"{stem} ({counter}){suffix}"
            if candidate not in reserved and not candidate.exists():
                return candidate
            counter += 1
