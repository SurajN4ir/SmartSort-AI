import pytest

from smartsort.scanner import FileScanner


def test_scan_finds_top_level_files(tmp_path):
    (tmp_path / "resume.pdf").write_text("content")
    (tmp_path / "photo.jpg").write_bytes(b"\x00" * 100)
    subdir = tmp_path / "subfolder"
    subdir.mkdir()
    (subdir / "nested.txt").write_text("nested")

    scanner = FileScanner(recursive=False)
    results = scanner.scan(tmp_path)

    names = {f.name for f in results}
    assert names == {"resume.pdf", "photo.jpg"}


def test_scan_recursive_includes_subfolders(tmp_path):
    (tmp_path / "top.txt").write_text("top")
    subdir = tmp_path / "subfolder"
    subdir.mkdir()
    (subdir / "nested.txt").write_text("nested")

    scanner = FileScanner(recursive=True)
    results = scanner.scan(tmp_path)

    names = {f.name for f in results}
    assert names == {"top.txt", "nested.txt"}


def test_scan_reports_extension_and_size(tmp_path):
    file_path = tmp_path / "notes.TXT"
    file_path.write_text("hello world")

    scanner = FileScanner()
    [result] = scanner.scan(tmp_path)

    assert result.extension == ".txt"
    assert result.size == len("hello world")


def test_scan_missing_directory_raises():
    scanner = FileScanner()
    with pytest.raises(FileNotFoundError):
        scanner.scan("Z:/does/not/exist")


def test_scan_progress_callback_invoked(tmp_path):
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "b.txt").write_text("b")

    calls = []
    scanner = FileScanner()
    scanner.scan(tmp_path, progress_callback=lambda done, total: calls.append((done, total)))

    assert calls == [(1, 2), (2, 2)]
