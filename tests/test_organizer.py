from datetime import datetime
from pathlib import Path

from smartsort.database import Database
from smartsort.models import ClassifiedFile, OrganizePlan, PlannedMove, ScannedFile
from smartsort.organizer import FileOrganizer


def make_move(root: Path, filename: str, category: str) -> PlannedMove:
    source = root / filename
    source.write_text("content")
    scanned = ScannedFile(
        name=filename,
        path=source,
        extension=Path(filename).suffix,
        size=source.stat().st_size,
        modified_time=datetime.now(),
    )
    classified = ClassifiedFile(scanned=scanned, category=category)
    destination = root / category / filename
    return PlannedMove(classified=classified, source=source, destination=destination, category=category)


def test_apply_moves_file_and_records_history(tmp_path):
    db = Database(tmp_path / "test.db")
    move = make_move(tmp_path, "resume.pdf", "Documents")
    plan = OrganizePlan(root=tmp_path, moves=[move])

    organizer = FileOrganizer(db)
    result = organizer.apply(plan)

    assert result.moved_count == 1
    assert result.error_count == 0
    assert (tmp_path / "Documents" / "resume.pdf").exists()
    assert not (tmp_path / "resume.pdf").exists()

    session = db.get_session(result.session_id)
    assert session.moved_count == 1
    db.close()


def test_apply_skips_deselected_moves(tmp_path):
    db = Database(tmp_path / "test.db")
    move = make_move(tmp_path, "resume.pdf", "Documents")
    move.selected = False
    plan = OrganizePlan(root=tmp_path, moves=[move])

    organizer = FileOrganizer(db)
    result = organizer.apply(plan)

    assert result.moved_count == 0
    assert (tmp_path / "resume.pdf").exists()
    db.close()


def test_apply_defaults_session_kind_to_organize(tmp_path):
    db = Database(tmp_path / "test.db")
    move = make_move(tmp_path, "resume.pdf", "Documents")
    plan = OrganizePlan(root=tmp_path, moves=[move])

    organizer = FileOrganizer(db)
    result = organizer.apply(plan)

    assert db.get_session(result.session_id).kind == "organize"
    db.close()


def test_apply_records_custom_session_kind(tmp_path):
    db = Database(tmp_path / "test.db")
    move = make_move(tmp_path, "resume.pdf", "Duplicates")
    plan = OrganizePlan(root=tmp_path, moves=[move])

    organizer = FileOrganizer(db)
    result = organizer.apply(plan, kind="dedupe")

    assert db.get_session(result.session_id).kind == "dedupe"
    db.close()


def test_undo_restores_file_to_original_location(tmp_path):
    db = Database(tmp_path / "test.db")
    move = make_move(tmp_path, "resume.pdf", "Documents")
    plan = OrganizePlan(root=tmp_path, moves=[move])

    organizer = FileOrganizer(db)
    result = organizer.apply(plan)
    assert (tmp_path / "Documents" / "resume.pdf").exists()

    restored, failed = organizer.undo(result.session_id)

    assert restored == 1
    assert failed == 0
    assert (tmp_path / "resume.pdf").exists()
    assert not (tmp_path / "Documents" / "resume.pdf").exists()

    session = db.get_session(result.session_id)
    assert session.undone is True
    db.close()
