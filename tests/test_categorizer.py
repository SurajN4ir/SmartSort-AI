from datetime import datetime
from pathlib import Path

from smartsort.categorizer import Categorizer
from smartsort.models import ScannedFile
from smartsort.semantic import SemanticGuess


def make_scanned(name: str) -> ScannedFile:
    return ScannedFile(
        name=name,
        path=Path(name),
        extension=Path(name).suffix.lower(),
        size=1024,
        modified_time=datetime.now(),
    )


def test_known_extension_maps_to_expected_category():
    categorizer = Categorizer()
    assert categorizer.categorize_extension(".pdf") == "Documents"
    assert categorizer.categorize_extension(".jpg") == "Images"
    assert categorizer.categorize_extension(".mp4") == "Videos"
    assert categorizer.categorize_extension(".zip") == "Archives"
    assert categorizer.categorize_extension(".exe") == "Applications"


def test_extension_matching_is_case_insensitive():
    categorizer = Categorizer()
    assert categorizer.categorize_extension(".PDF") == "Documents"
    assert categorizer.categorize_extension(".JPG") == "Images"


def test_unknown_extension_falls_back_to_others():
    categorizer = Categorizer()
    assert categorizer.categorize_extension(".xyz123") == "Others"
    assert categorizer.categorize_extension("") == "Others"


def test_classify_attaches_category_to_scanned_file():
    categorizer = Categorizer()
    scanned = make_scanned("resume.pdf")
    classified = categorizer.classify(scanned)
    assert classified.category == "Documents"
    assert classified.name == "resume.pdf"


def test_classify_all_preserves_order():
    categorizer = Categorizer()
    files = [make_scanned("a.pdf"), make_scanned("b.jpg"), make_scanned("c.zip")]
    classified = categorizer.classify_all(files)
    assert [c.category for c in classified] == ["Documents", "Images", "Archives"]


def test_custom_rules_override_defaults():
    categorizer = Categorizer(rules={".pdf": "CustomCategory"})
    assert categorizer.categorize_extension(".pdf") == "CustomCategory"
    assert categorizer.categorize_extension(".jpg") == "Others"


def test_classify_with_guesses_prefers_semantic_guess():
    categorizer = Categorizer()
    scanned = make_scanned("ML_Assignment_Final.pdf")
    guesses = {"ML_Assignment_Final.pdf": SemanticGuess(path=("University", "Machine Learning"), confidence=0.9)}

    [result] = categorizer.classify_with_guesses([scanned], guesses)

    assert result.category == "University"
    assert result.subpath == ("Machine Learning",)
    assert result.confidence == 0.9
    assert result.source == "ai"
    assert result.category_path == ("University", "Machine Learning")


def test_classify_with_guesses_falls_back_to_rules_when_no_guess():
    categorizer = Categorizer()
    scanned = make_scanned("resume.pdf")

    [result] = categorizer.classify_with_guesses([scanned], {})

    assert result.category == "Documents"
    assert result.subpath == ()
    assert result.source == "rule"


def test_classify_with_guesses_mixes_ai_and_rule_results():
    categorizer = Categorizer()
    files = [make_scanned("ML_Assignment_Final.pdf"), make_scanned("photo.jpg")]
    guesses = {"ML_Assignment_Final.pdf": SemanticGuess(path=("University",), confidence=0.7)}

    results = categorizer.classify_with_guesses(files, guesses)

    assert results[0].source == "ai"
    assert results[1].source == "rule"
    assert results[1].category == "Images"
