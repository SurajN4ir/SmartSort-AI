"""A small local, per-user settings file (currently just the optional API key).

This lives under the user's home directory next to the SQLite database --
never inside the project folder -- so it's never at risk of being committed
or shared alongside the code.
"""

from __future__ import annotations

import json
import os

from smartsort.config import APP_DATA_DIR

CONFIG_PATH = APP_DATA_DIR / "config.json"


def _read() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _write(data: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(data, indent=2))


def get_api_key() -> str | None:
    stored = _read().get("anthropic_api_key")
    return stored or os.environ.get("ANTHROPIC_API_KEY")


def set_api_key(key: str) -> None:
    data = _read()
    if key:
        data["anthropic_api_key"] = key
    else:
        data.pop("anthropic_api_key", None)
    _write(data)


def has_api_key() -> bool:
    return bool(get_api_key())
