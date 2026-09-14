"""Rule-based categorization engine.

Deliberately simple for V1: a file's category is decided purely by its
extension. This is the seam where a future semantic/ML classifier can be
substituted without touching the scanner, planner, or GUI.
"""

from __future__ import annotations

from smartsort.config import CATEGORY_RULES, DEFAULT_CATEGORY
from smartsort.models import ClassifiedFile, ScannedFile


class Categorizer:
    def __init__(self, rules: dict[str, str] | None = None):
        self.rules = rules if rules is not None else CATEGORY_RULES

    def categorize_extension(self, extension: str) -> str:
        return self.rules.get(extension.lower(), DEFAULT_CATEGORY)

    def classify(self, scanned: ScannedFile) -> ClassifiedFile:
        category = self.categorize_extension(scanned.extension)
        return ClassifiedFile(scanned=scanned, category=category)

    def classify_all(self, files: list[ScannedFile]) -> list[ClassifiedFile]:
        return [self.classify(f) for f in files]
