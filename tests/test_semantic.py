import json

import pytest

from smartsort.semantic import (
    MAX_BATCH_SIZE,
    MAX_PATH_DEPTH,
    PREVIEW_CHARS,
    SemanticClassifier,
    SemanticGuess,
    SemanticUnavailable,
    parse_response,
    read_preview,
)


def test_parse_response_extracts_valid_entries():
    filenames = ["ML_Assignment_Final.pdf", "vacation.png"]
    text = json.dumps(
        [
            {"file": "ML_Assignment_Final.pdf", "path": ["University", "Machine Learning"], "confidence": 0.92},
            {"file": "vacation.png", "path": ["Trips", "2026"], "confidence": 0.6},
        ]
    )

    results = parse_response(text, filenames)

    assert results["ML_Assignment_Final.pdf"].path == ("University", "Machine Learning")
    assert results["ML_Assignment_Final.pdf"].confidence == 0.92
    assert results["vacation.png"].path == ("Trips", "2026")


def test_parse_response_handles_prose_around_json():
    filenames = ["report.pdf"]
    text = 'Sure, here you go:\n[{"file": "report.pdf", "path": ["Work"], "confidence": 0.5}]\nHope that helps!'

    results = parse_response(text, filenames)

    assert results["report.pdf"].path == ("Work",)


def test_parse_response_ignores_unknown_filenames():
    filenames = ["a.txt"]
    text = json.dumps([{"file": "not_in_batch.txt", "path": ["X"], "confidence": 0.5}])

    results = parse_response(text, filenames)

    assert results == {}


def test_parse_response_skips_entries_with_empty_path():
    filenames = ["a.txt"]
    text = json.dumps([{"file": "a.txt", "path": [], "confidence": 0.5}])

    results = parse_response(text, filenames)

    assert results == {}


def test_parse_response_clamps_confidence_to_valid_range():
    filenames = ["a.txt"]
    text = json.dumps([{"file": "a.txt", "path": ["X"], "confidence": 5}])

    results = parse_response(text, filenames)

    assert results["a.txt"].confidence == 1.0


def test_parse_response_defaults_confidence_when_missing_or_invalid():
    filenames = ["a.txt", "b.txt"]
    text = json.dumps(
        [
            {"file": "a.txt", "path": ["X"]},
            {"file": "b.txt", "path": ["X"], "confidence": "not-a-number"},
        ]
    )

    results = parse_response(text, filenames)

    assert results["a.txt"].confidence == 0.5
    assert results["b.txt"].confidence == 0.5


def test_parse_response_truncates_overly_deep_paths():
    filenames = ["a.txt"]
    deep_path = [f"level{i}" for i in range(MAX_PATH_DEPTH + 3)]
    text = json.dumps([{"file": "a.txt", "path": deep_path, "confidence": 0.5}])

    results = parse_response(text, filenames)

    assert len(results["a.txt"].path) == MAX_PATH_DEPTH


def test_parse_response_returns_empty_for_malformed_json():
    assert parse_response("not json at all", ["a.txt"]) == {}


def test_parse_response_returns_empty_when_no_array_present():
    assert parse_response("I couldn't find a pattern.", ["a.txt"]) == {}


def test_classify_batch_raises_semantic_unavailable_without_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    classifier = SemanticClassifier(api_key=None)

    with pytest.raises(SemanticUnavailable):
        classifier.classify_batch(["a.txt"])


def test_classify_batch_splits_into_chunks(monkeypatch):
    classifier = SemanticClassifier(api_key="fake-key")
    seen_chunks = []

    def fake_chunk(filenames, previews, existing_folders):
        seen_chunks.append(list(filenames))
        return {name: SemanticGuess(path=("X",), confidence=0.5) for name in filenames}

    monkeypatch.setattr(classifier, "_classify_chunk", fake_chunk)

    filenames = [f"file{i}.txt" for i in range(MAX_BATCH_SIZE + 5)]
    results = classifier.classify_batch(filenames)

    assert len(seen_chunks) == 2
    assert len(seen_chunks[0]) == MAX_BATCH_SIZE
    assert len(seen_chunks[1]) == 5
    assert len(results) == len(filenames)


def test_classify_batch_skips_failing_chunk_without_raising(monkeypatch):
    classifier = SemanticClassifier(api_key="fake-key")

    def flaky_chunk(filenames, previews, existing_folders):
        if filenames[0] == "bad.txt":
            raise RuntimeError("network hiccup")
        return {name: SemanticGuess(path=("X",), confidence=0.5) for name in filenames}

    monkeypatch.setattr(classifier, "_classify_chunk", flaky_chunk)

    results = classifier.classify_batch(["bad.txt", "good.txt"])

    # Both filenames were requested as one chunk here, so a single failure
    # means neither gets a guess -- callers fall back to rule-based for both.
    assert results == {}


def test_build_payload_includes_previews_and_existing_folders():
    classifier = SemanticClassifier(api_key="fake-key")

    payload = classifier._build_payload(
        ["a.txt", "b.jpg"],
        previews={"a.txt": "meeting notes for project x"},
        existing_folders=["University", "Football"],
    )

    assert payload["files"] == [
        {"name": "a.txt", "preview": "meeting notes for project x"},
        {"name": "b.jpg"},
    ]
    assert payload["existing_folders"] == ["University", "Football"]


def test_build_payload_omits_optional_keys_when_absent():
    classifier = SemanticClassifier(api_key="fake-key")

    payload = classifier._build_payload(["a.txt"], previews=None, existing_folders=None)

    assert payload == {"files": [{"name": "a.txt"}]}


def test_read_preview_returns_text_for_supported_extension(tmp_path):
    file_path = tmp_path / "notes.txt"
    file_path.write_text("Meeting notes for the ML project.")

    assert read_preview(file_path) == "Meeting notes for the ML project."


def test_read_preview_returns_none_for_unsupported_extension(tmp_path):
    file_path = tmp_path / "photo.jpg"
    file_path.write_bytes(b"\x00\x01\x02")

    assert read_preview(file_path) is None


def test_read_preview_returns_none_for_empty_file(tmp_path):
    file_path = tmp_path / "empty.txt"
    file_path.write_text("   ")

    assert read_preview(file_path) is None


def test_read_preview_truncates_long_content(tmp_path):
    file_path = tmp_path / "big.txt"
    file_path.write_text("x" * (PREVIEW_CHARS * 3))

    preview = read_preview(file_path)

    assert len(preview) == PREVIEW_CHARS


def test_read_preview_returns_none_for_missing_file(tmp_path):
    assert read_preview(tmp_path / "does_not_exist.txt") is None
