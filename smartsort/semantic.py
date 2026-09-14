"""Optional AI-assisted classification -- SmartSort's V2 layer.

V1's Categorizer sorts purely by file extension, which is fast, free, and
completely offline. This module adds an opt-in second stage on top of it:
given a batch of filenames, ask an LLM to propose a more meaningful nested
folder path (e.g. "University/Machine Learning/Assignments" instead of a
flat "Documents"), along with a confidence score.

Nothing here runs unless the caller explicitly asks for it and an API key
is available -- the rule-based pipeline works completely standalone, and
this module never touches the filesystem or the classification of a file
unless a usable suggestion was actually returned for it.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MODEL = "claude-haiku-4-5-20251001"
MAX_BATCH_SIZE = 40
MAX_PATH_DEPTH = 4
PREVIEW_CHARS = 400

# Extensions cheap and safe to read as plain text for a content preview.
# Deliberately excludes binary document formats (pdf/docx/...) -- reading
# those needs a real parser, which is a bigger dependency than this V1/V2
# pipeline otherwise carries. Filename + a text preview is still a solid
# signal for the very common case of notes, READMEs, code, and data files.
TEXT_PREVIEW_EXTENSIONS = {
    ".txt", ".md", ".csv", ".json", ".py", ".js", ".ts", ".tsx", ".jsx",
    ".html", ".css", ".yml", ".yaml", ".ini", ".cfg", ".log", ".sql", ".sh",
}

SYSTEM_PROMPT = f"""You help a desktop app organize files into folders.

You will receive a JSON object describing a batch of files to organize:
- "files": a list of {{"name": <filename>, "preview": <optional short text \
snippet from inside the file>}}. Use the preview when present -- it is \
often a much stronger signal than the filename alone.
- "existing_folders" (optional): folder names this location already has \
from previous organizing. Reuse one of these instead of inventing a \
near-duplicate (e.g. don't create "University " or "College" if \
"University" is already listed) whenever it genuinely fits.

For each file, propose a short folder path that groups related files \
together meaningfully -- by topic, project, subject, or context implied by \
the name and preview -- rather than just by file type. Look for patterns \
across the batch (similar prefixes, shared project or course names, dates, \
people, teams) and keep related files under a consistent path.

Rules:
- Each path is a list of 1 to {MAX_PATH_DEPTH} folder names, ordered broad \
to specific (e.g. ["University", "Machine Learning", "Assignments"]).
- If a file gives no useful signal beyond its type, fall back to one \
simple, generic folder such as "Documents", "Images", or "Videos".
- confidence is your own estimate from 0.0 to 1.0 of how meaningful (not \
just type-based) the suggested path is.
- Reply with ONLY a JSON array, no prose, no markdown fences, in exactly \
this shape:
[{{"file": "<original filename>", "path": ["<folder>", "..."], "confidence": <0-1>}}]"""


def read_preview(path: Path, max_chars: int = PREVIEW_CHARS) -> str | None:
    """A short text snippet from inside a file, or None if not applicable.

    Only reads formats that are safe to decode as plain text -- anything
    else (images, binaries, PDFs, archives) is skipped entirely rather than
    risk reading garbage or a slow/large parse.
    """

    if path.suffix.lower() not in TEXT_PREVIEW_EXTENSIONS:
        return None
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as handle:
            text = handle.read(max_chars)
    except OSError:
        return None
    text = text.strip()
    return text or None


@dataclass
class SemanticGuess:
    path: tuple[str, ...]
    confidence: float


class SemanticUnavailable(Exception):
    """Raised when semantic classification can't run right now.

    Callers are expected to catch this and fall back to the rule-based
    Categorizer -- it is not a programming error, just an unmet
    precondition (no key, no package, or a failed API call).
    """


class SemanticClassifier:
    def __init__(self, api_key: str | None = None, model: str = DEFAULT_MODEL):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        self._client = None

    @property
    def client(self):
        if self._client is None:
            if not self.api_key:
                raise SemanticUnavailable(
                    "No Anthropic API key configured. Set it in Settings or "
                    "via the ANTHROPIC_API_KEY environment variable."
                )
            try:
                import anthropic
            except ImportError as exc:
                raise SemanticUnavailable(
                    "The 'anthropic' package is required for Smart Organize. "
                    "Install it with: pip install anthropic"
                ) from exc
            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    def classify_batch(
        self,
        filenames: list[str],
        previews: dict[str, str] | None = None,
        existing_folders: list[str] | None = None,
    ) -> dict[str, SemanticGuess]:
        """Best-effort semantic guesses keyed by filename.

        ``previews`` (filename -> short text snippet) and
        ``existing_folders`` (folder names already present at the target
        location) are both optional extra context -- omitting them still
        works, just with a weaker signal than filenames alone.

        Filenames the model didn't return a usable guess for are simply
        absent from the result -- callers should fall back to the
        rule-based category for those.
        """

        results: dict[str, SemanticGuess] = {}
        for start in range(0, len(filenames), MAX_BATCH_SIZE):
            chunk = filenames[start : start + MAX_BATCH_SIZE]
            try:
                results.update(self._classify_chunk(chunk, previews, existing_folders))
            except SemanticUnavailable:
                raise
            except Exception:
                # A single bad batch (rate limit, malformed reply, network
                # hiccup) shouldn't take down the whole scan -- those files
                # just keep their rule-based category instead.
                continue
        return results

    def _build_payload(
        self,
        filenames: list[str],
        previews: dict[str, str] | None,
        existing_folders: list[str] | None,
    ) -> dict:
        files_payload = []
        for name in filenames:
            entry = {"name": name}
            preview = previews.get(name) if previews else None
            if preview:
                entry["preview"] = preview
            files_payload.append(entry)

        payload: dict = {"files": files_payload}
        if existing_folders:
            payload["existing_folders"] = list(existing_folders)
        return payload

    def _classify_chunk(
        self,
        filenames: list[str],
        previews: dict[str, str] | None,
        existing_folders: list[str] | None,
    ) -> dict[str, SemanticGuess]:
        payload = self._build_payload(filenames, previews, existing_folders)
        message = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": json.dumps(payload)}],
        )
        text = "".join(block.text for block in message.content if hasattr(block, "text"))
        return parse_response(text, filenames)


def parse_response(text: str, filenames: list[str]) -> dict[str, SemanticGuess]:
    """Pure parsing logic, kept separate from the network call so it's easy to test."""

    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        return {}
    try:
        items = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
    if not isinstance(items, list):
        return {}

    valid_names = set(filenames)
    results: dict[str, SemanticGuess] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        name = item.get("file")
        path = item.get("path")
        if name not in valid_names or not isinstance(path, list) or not path:
            continue

        clean_path = tuple(str(p).strip() for p in path if str(p).strip())[:MAX_PATH_DEPTH]
        if not clean_path:
            continue

        try:
            confidence = max(0.0, min(1.0, float(item.get("confidence", 0.5))))
        except (TypeError, ValueError):
            confidence = 0.5

        results[name] = SemanticGuess(path=clean_path, confidence=confidence)

    return results
