from smartsort.database import Database


def test_create_session_returns_incrementing_ids(tmp_path):
    db = Database(tmp_path / "test.db")
    first = db.create_session("C:/Downloads", total_files=5, total_categories=2)
    second = db.create_session("C:/Downloads", total_files=3, total_categories=1)
    assert second == first + 1
    db.close()


def test_record_move_and_retrieve(tmp_path):
    db = Database(tmp_path / "test.db")
    session_id = db.create_session("C:/Downloads", total_files=1, total_categories=1)
    db.record_move(session_id, "resume.pdf", "C:/Downloads/resume.pdf", "C:/Downloads/Documents/resume.pdf", "Documents", 1024)

    moves = db.get_moves(session_id)
    assert len(moves) == 1
    assert moves[0].file_name == "resume.pdf"
    assert moves[0].category == "Documents"
    db.close()


def test_finalize_session_sets_status(tmp_path):
    db = Database(tmp_path / "test.db")
    session_id = db.create_session("C:/Downloads", total_files=2, total_categories=1)
    db.finalize_session(session_id, moved_count=2, error_count=0)

    session = db.get_session(session_id)
    assert session.status == "completed"
    assert session.moved_count == 2

    db.finalize_session(session_id, moved_count=1, error_count=1)
    session = db.get_session(session_id)
    assert session.status == "completed_with_errors"
    db.close()


def test_list_sessions_orders_newest_first(tmp_path):
    db = Database(tmp_path / "test.db")
    first = db.create_session("A", total_files=1, total_categories=1)
    second = db.create_session("B", total_files=1, total_categories=1)

    sessions = db.list_sessions()
    assert sessions[0].id == second
    assert sessions[1].id == first
    db.close()


def test_mark_session_undone_flags_session_and_moves(tmp_path):
    db = Database(tmp_path / "test.db")
    session_id = db.create_session("C:/Downloads", total_files=1, total_categories=1)
    db.record_move(session_id, "a.txt", "src/a.txt", "dst/a.txt", "Documents", 1)

    db.mark_session_undone(session_id)

    session = db.get_session(session_id)
    assert session.undone is True
    assert session.status == "undone"
    moves = db.get_moves(session_id)
    assert all(m.undone for m in moves)
    db.close()
