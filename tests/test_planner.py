from datetime import datetime
from pathlib import Path

from smartsort.categorizer import Categorizer
from smartsort.models import ScannedFile
from smartsort.planner import OrganizationPlanner


def make_classified(name: str, category: str, root: Path):
    categorizer = Categorizer(rules={})
    scanned = ScannedFile(
        name=name,
        path=root / name,
        extension=Path(name).suffix.lower(),
        size=10,
        modified_time=datetime.now(),
    )
    classified = categorizer.classify(scanned)
    classified.category = category
    return classified


def test_plan_groups_files_by_category(tmp_path):
    classified = [
        make_classified("resume.pdf", "Documents", tmp_path),
        make_classified("photo.jpg", "Images", tmp_path),
        make_classified("notes.txt", "Documents", tmp_path),
    ]
    plan = OrganizationPlanner().generate_plan(tmp_path, classified)

    assert plan.total_files == 3
    assert plan.total_categories == 2
    assert len(plan.categories["Documents"]) == 2
    assert len(plan.categories["Images"]) == 1


def test_plan_destinations_are_under_category_folder(tmp_path):
    classified = [make_classified("resume.pdf", "Documents", tmp_path)]
    plan = OrganizationPlanner().generate_plan(tmp_path, classified)

    move = plan.moves[0]
    assert move.destination == tmp_path / "Documents" / "resume.pdf"


def test_plan_resolves_collision_with_existing_file(tmp_path):
    (tmp_path / "Documents").mkdir()
    (tmp_path / "Documents" / "resume.pdf").write_text("existing")

    classified = [make_classified("resume.pdf", "Documents", tmp_path)]
    plan = OrganizationPlanner().generate_plan(tmp_path, classified)

    assert plan.moves[0].destination == tmp_path / "Documents" / "resume (1).pdf"


def test_plan_resolves_collision_between_two_planned_moves(tmp_path):
    classified = [
        make_classified("resume.pdf", "Documents", tmp_path / "a"),
        make_classified("resume.pdf", "Documents", tmp_path / "b"),
    ]
    plan = OrganizationPlanner().generate_plan(tmp_path, classified)

    destinations = {m.destination for m in plan.moves}
    assert destinations == {
        tmp_path / "Documents" / "resume.pdf",
        tmp_path / "Documents" / "resume (1).pdf",
    }


def test_selected_moves_excludes_deselected():
    from smartsort.models import OrganizePlan, PlannedMove

    classified = make_classified("resume.pdf", "Documents", Path("."))
    plan = OrganizePlan(root=Path("."))
    plan.moves = [
        PlannedMove(classified, Path("a"), Path("b"), "Documents", selected=True),
        PlannedMove(classified, Path("c"), Path("d"), "Documents", selected=False),
    ]
    assert len(plan.selected_moves) == 1
