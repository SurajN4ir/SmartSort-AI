from datetime import datetime, timedelta
from pathlib import Path

from smartsort.duplicates import DUPLICATES_FOLDER, build_cleanup_plan, find_duplicates
from smartsort.models import ScannedFile


def make_file(path: Path, content: bytes, modified_time: datetime) -> ScannedFile:
    path.write_bytes(content)
    return ScannedFile(
        name=path.name,
        path=path,
        extension=path.suffix,
        size=len(content),
        modified_time=modified_time,
    )


def test_find_duplicates_groups_identical_content(tmp_path):
    now = datetime.now()
    a = make_file(tmp_path / "a.txt", b"same content", now)
    b = make_file(tmp_path / "b.txt", b"same content", now + timedelta(seconds=1))
    c = make_file(tmp_path / "c.txt", b"different", now)

    groups = find_duplicates([a, b, c])

    assert len(groups) == 1
    assert {f.name for f in groups[0].files} == {"a.txt", "b.txt"}


def test_find_duplicates_keeps_oldest_by_default(tmp_path):
    now = datetime.now()
    older = make_file(tmp_path / "older.txt", b"dup", now)
    newer = make_file(tmp_path / "newer.txt", b"dup", now + timedelta(minutes=5))

    [group] = find_duplicates([older, newer])

    assert group.keep is older
    assert group.duplicates == [newer]


def test_find_duplicates_ignores_singletons(tmp_path):
    now = datetime.now()
    a = make_file(tmp_path / "a.txt", b"unique-a", now)
    b = make_file(tmp_path / "b.txt", b"unique-b", now)

    assert find_duplicates([a, b]) == []


def test_find_duplicates_ignores_empty_files(tmp_path):
    now = datetime.now()
    a = make_file(tmp_path / "a.txt", b"", now)
    b = make_file(tmp_path / "b.txt", b"", now)

    assert find_duplicates([a, b]) == []


def test_find_duplicates_does_not_hash_files_with_different_sizes(tmp_path):
    now = datetime.now()
    a = make_file(tmp_path / "a.txt", b"short", now)
    b = make_file(tmp_path / "b.txt", b"a much longer piece of content", now)

    assert find_duplicates([a, b]) == []


def test_find_duplicates_handles_three_way_duplicate_group(tmp_path):
    now = datetime.now()
    files = [
        make_file(tmp_path / f"copy{i}.txt", b"triplicate", now + timedelta(seconds=i))
        for i in range(3)
    ]

    [group] = find_duplicates(files)

    assert len(group.files) == 3
    assert len(group.duplicates) == 2
    assert group.wasted_bytes == 2 * len(b"triplicate")


def test_groups_sorted_by_wasted_space_descending(tmp_path):
    now = datetime.now()
    small = [make_file(tmp_path / f"s{i}.txt", b"x", now) for i in range(2)]
    big = [make_file(tmp_path / f"b{i}.txt", b"y" * 100, now) for i in range(2)]

    groups = find_duplicates(small + big)

    assert groups[0].wasted_bytes > groups[1].wasted_bytes


def test_build_cleanup_plan_moves_duplicates_into_duplicates_folder(tmp_path):
    now = datetime.now()
    keep = make_file(tmp_path / "original.txt", b"dup", now)
    extra = make_file(tmp_path / "copy.txt", b"dup", now + timedelta(seconds=1))
    from smartsort.duplicates import DuplicateGroup

    group = DuplicateGroup(files=[keep, extra], keep=keep)
    plan = build_cleanup_plan(tmp_path, [group])

    assert plan.total_files == 1
    move = plan.moves[0]
    assert move.source == extra.path
    assert move.destination == tmp_path / DUPLICATES_FOLDER / "copy.txt"
    assert move.category == DUPLICATES_FOLDER


def test_build_cleanup_plan_resolves_name_collisions(tmp_path):
    now = datetime.now()
    (tmp_path / "sub1").mkdir()
    (tmp_path / "sub2").mkdir()
    keep = make_file(tmp_path / "sub1" / "same.txt", b"dup", now)
    extra1 = make_file(tmp_path / "sub2" / "same.txt", b"dup", now + timedelta(seconds=1))
    extra2_dir = tmp_path / "sub3"
    extra2_dir.mkdir()
    extra2 = make_file(extra2_dir / "same.txt", b"dup", now + timedelta(seconds=2))

    from smartsort.duplicates import DuplicateGroup

    group = DuplicateGroup(files=[keep, extra1, extra2], keep=keep)
    plan = build_cleanup_plan(tmp_path, [group])

    destinations = {m.destination for m in plan.moves}
    assert destinations == {
        tmp_path / DUPLICATES_FOLDER / "same.txt",
        tmp_path / DUPLICATES_FOLDER / "same (1).txt",
    }
