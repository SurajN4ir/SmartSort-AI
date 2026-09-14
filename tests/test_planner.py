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


def test_plan_builds_nested_destination_for_subpath(tmp_path):
    classified = [make_classified("ML_Final.pdf", "University", tmp_path)]
    classified[0].subpath = ("Machine Learning", "Assignments")
    classified[0].source = "ai"
    classified[0].confidence = 0.9

    plan = OrganizationPlanner().generate_plan(tmp_path, classified)

    move = plan.moves[0]
    assert move.destination == tmp_path / "University" / "Machine Learning" / "Assignments" / "ML_Final.pdf"
    assert move.subpath == ("Machine Learning", "Assignments")
    assert move.confidence == 0.9
    assert move.source_kind == "ai"
    assert move.is_ai_suggested is True


def test_plan_groups_by_top_level_category_only(tmp_path):
    a = make_classified("a.pdf", "University", tmp_path)
    a.subpath = ("Course A",)
    b = make_classified("b.pdf", "University", tmp_path)
    b.subpath = ("Course B",)

    plan = OrganizationPlanner().generate_plan(tmp_path, [a, b])

    assert plan.total_categories == 1
    assert len(plan.categories["University"]) == 2


def test_retarget_collapses_to_flat_category(tmp_path):
    classified = [make_classified("ML_Final.pdf", "University", tmp_path)]
    classified[0].subpath = ("Machine Learning",)
    classified[0].source = "ai"
    classified[0].confidence = 0.8

    plan = OrganizationPlanner().generate_plan(tmp_path, classified)
    move = plan.moves[0]

    OrganizationPlanner().retarget(plan, move, "Documents")

    assert move.category == "Documents"
    assert move.subpath == ()
    assert move.source_kind == "manual"
    assert move.confidence is None
    assert move.destination == tmp_path / "Documents" / "ML_Final.pdf"


def test_selected_moves_excludes_deselected():
    from smartsort.models import OrganizePlan, PlannedMove

    classified = make_classified("resume.pdf", "Documents", Path("."))
    plan = OrganizePlan(root=Path("."))
    plan.moves = [
        PlannedMove(classified, Path("a"), Path("b"), "Documents", selected=True),
        PlannedMove(classified, Path("c"), Path("d"), "Documents", selected=False),
    ]
    assert len(plan.selected_moves) == 1
