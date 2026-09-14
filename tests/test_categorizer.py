from datetime import datetime
from pathlib import Path

from smartsort.categorizer import Categorizer
from smartsort.models import ScannedFile


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
