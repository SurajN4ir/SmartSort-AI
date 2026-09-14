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

DEFAULT_MODEL = "claude-haiku-4-5-20251001"
MAX_BATCH_SIZE = 40
MAX_PATH_DEPTH = 4

SYSTEM_PROMPT = f"""You help a desktop app organize files into folders.

Given a JSON array of filenames, propose a short folder path for each one \
that groups related files together meaningfully -- by topic, project, \
subject, or context implied by the name -- rather than just by file type. \
Look for patterns across the batch (similar prefixes, shared project or \
course names, dates, people, teams) and keep related files under a \
consistent path.

Rules:
- Each path is a list of 1 to {MAX_PATH_DEPTH} folder names, ordered broad \
to specific (e.g. ["University", "Machine Learning", "Assignments"]).
- If a filename gives no useful signal beyond its file type, fall back to \
one simple, generic folder such as "Documents", "Images", or "Videos".
- confidence is your own estimate from 0.0 to 1.0 of how meaningful (not \
just type-based) the suggested path is.
- Reply with ONLY a JSON array, no prose, no markdown fences, in exactly \
this shape:
[{{"file": "<original filename>", "path": ["<folder>", "..."], "confidence": <0-1>}}]"""


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

    def classify_batch(self, filenames: list[str]) -> dict[str, SemanticGuess]:
        """Best-effort semantic guesses keyed by filename.

        Filenames the model didn't return a usable guess for are simply
        absent from the result -- callers should fall back to the
        rule-based category for those.
        """

        results: dict[str, SemanticGuess] = {}
        for start in range(0, len(filenames), MAX_BATCH_SIZE):
            chunk = filenames[start : start + MAX_BATCH_SIZE]
            try:
                results.update(self._classify_chunk(chunk))
            except SemanticUnavailable:
                raise
            except Exception:
                # A single bad batch (rate limit, malformed reply, network
                # hiccup) shouldn't take down the whole scan -- those files
                # just keep their rule-based category instead.
                continue
        return results

    def _classify_chunk(self, filenames: list[str]) -> dict[str, SemanticGuess]:
        message = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": json.dumps(filenames)}],
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
