"""Settings view: appearance and a transparent look at the classification rules."""

from __future__ import annotations

import customtkinter as ctk

from smartsort.config import CATEGORY_ICONS, CATEGORY_RULES
from smartsort.gui import theme
from smartsort.gui.widgets import Card


class SettingsView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")

        container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=36, pady=28)

        ctk.CTkLabel(container, text="Settings", font=theme.heading_font(20)).pack(anchor="w", pady=(0, 20))

        appearance_card = Card(container)
        appearance_card.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(
            appearance_card, text="Appearance", font=theme.font(14, "bold")
        ).pack(anchor="w", padx=20, pady=(16, 2))
        ctk.CTkLabel(
            appearance_card, text="Switch between light and dark mode.",
            font=theme.font(12), text_color=theme.TEXT_SECONDARY,
        ).pack(anchor="w", padx=20, pady=(0, 12))

        appearance_switch = ctk.CTkSegmentedButton(
            appearance_card,
            values=["Light", "Dark", "System"],
            command=self._set_appearance,
        )
        appearance_switch.set(ctk.get_appearance_mode())
        appearance_switch.pack(anchor="w", padx=20, pady=(0, 18))

        rules_card = Card(container)
        rules_card.pack(fill="x")
        ctk.CTkLabel(
            rules_card, text="Classification rules", font=theme.font(14, "bold")
        ).pack(anchor="w", padx=20, pady=(16, 2))
        ctk.CTkLabel(
            rules_card,
            text="V1 sorts by file extension. This is the full rule table SmartSort uses today.",
            font=theme.font(12),
            text_color=theme.TEXT_SECONDARY,
        ).pack(anchor="w", padx=20, pady=(0, 14))

        grouped: dict[str, list[str]] = {}
        for ext, category in sorted(CATEGORY_RULES.items()):
            grouped.setdefault(category, []).append(ext)

        for category, extensions in grouped.items():
            row = ctk.CTkFrame(rules_card, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=4)
            icon = CATEGORY_ICONS.get(category, "📁")
            ctk.CTkLabel(row, text=f"{icon}  {category}", font=theme.font(12, "bold"), width=160, anchor="w").pack(side="left")
            ctk.CTkLabel(
                row, text=", ".join(extensions), font=theme.font(11), text_color=theme.TEXT_SECONDARY, anchor="w"
            ).pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(rules_card, text="", height=6).pack()

    @staticmethod
    def _set_appearance(value: str) -> None:
        ctk.set_appearance_mode(value)
