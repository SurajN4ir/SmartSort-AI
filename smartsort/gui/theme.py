"""Shared color tokens and fonts for the SmartSort GUI.

Colors are given as (light, dark) tuples wherever CustomTkinter accepts them,
so the whole app follows the OS/appearance-mode toggle consistently.
"""

from __future__ import annotations

import customtkinter as ctk

BG = ("#f4f5f8", "#0f1117")
SIDEBAR_BG = ("#ebedf3", "#0b0d12")
CARD_BG = ("#ffffff", "#171a22")
CARD_HOVER = ("#eef0f6", "#1e2229")
CARD_BORDER = ("#e2e5ec", "#232733")
TEXT_PRIMARY = ("#12141a", "#f3f4f6")
TEXT_SECONDARY = ("#565c6b", "#9aa0ac")
TEXT_MUTED = ("#8a8f9c", "#666c78")

ACCENT = "#3b82f6"
ACCENT_HOVER = "#2f6fe0"
ACCENT_SOFT = ("#e6edff", "#16233d")
SUCCESS = "#22c55e"
SUCCESS_SOFT = ("#e5f9ec", "#0f2a1a")
WARNING = "#f59e0b"
DANGER = "#ef4444"
DANGER_HOVER = "#dc3d3d"

FONT_FAMILY = "Segoe UI"


def font(size: int = 13, weight: str = "normal") -> ctk.CTkFont:
    return ctk.CTkFont(family=FONT_FAMILY, size=size, weight=weight)


def heading_font(size: int = 22) -> ctk.CTkFont:
    return ctk.CTkFont(family=FONT_FAMILY, size=size, weight="bold")
