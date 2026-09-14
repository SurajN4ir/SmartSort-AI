"""Settings view: appearance and a transparent look at the classification rules."""

from __future__ import annotations

import customtkinter as ctk

from smartsort import local_config
from smartsort.config import CATEGORY_ICONS, CATEGORY_RULES
from smartsort.gui import theme
from smartsort.gui.widgets import Card, PrimaryButton, SecondaryButton


class SettingsView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")

        container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=36, pady=28)

        ctk.CTkLabel(container, text="Settings", font=theme.heading_font(20)).pack(anchor="w", pady=(0, 20))

        smart_card = Card(container)
        smart_card.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(
            smart_card, text="✦ Smart Organize (AI)", font=theme.font(14, "bold")
        ).pack(anchor="w", padx=20, pady=(16, 2))
        ctk.CTkLabel(
            smart_card,
            text="Optional. Adds an AI classification pass that groups files by meaning\n"
            "(project, topic, subject) instead of just file type. Uses the Anthropic API\n"
            "with your own key -- stored only on this computer, never in this project.",
            font=theme.font(12),
            text_color=theme.TEXT_SECONDARY,
            justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 12))

        key_row = ctk.CTkFrame(smart_card, fg_color="transparent")
        key_row.pack(fill="x", padx=20, pady=(0, 8))

        self.key_entry = ctk.CTkEntry(
            key_row, placeholder_text="sk-ant-...", width=280, show="•"
        )
        self.key_entry.pack(side="left", padx=(0, 10))
        if local_config.has_api_key():
            self.key_entry.configure(placeholder_text="•••••••••••••••••••• (already set)")

        PrimaryButton(key_row, text="Save", width=90, height=32, command=self._save_key).pack(side="left")
        SecondaryButton(key_row, text="Remove", width=90, height=32, command=self._remove_key).pack(side="left", padx=(8, 0))

        self.key_status = ctk.CTkLabel(smart_card, text="", font=theme.font(11))
        self.key_status.pack(anchor="w", padx=20, pady=(0, 16))
        self._refresh_status()

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

    def _save_key(self) -> None:
        key = self.key_entry.get().strip()
        if not key:
            return
        local_config.set_api_key(key)
        self.key_entry.delete(0, "end")
        self.key_entry.configure(placeholder_text="•••••••••••••••••••• (already set)")
        self._refresh_status()

    def _remove_key(self) -> None:
        local_config.set_api_key("")
        self.key_entry.delete(0, "end")
        self.key_entry.configure(placeholder_text="sk-ant-...")
        self._refresh_status()

    def _refresh_status(self) -> None:
        if local_config.has_api_key():
            self.key_status.configure(text="✓ Key configured -- Smart Organize is available.", text_color=theme.SUCCESS)
        else:
            self.key_status.configure(text="Not configured -- Smart Organize is off.", text_color=theme.TEXT_MUTED)

    @staticmethod
    def _set_appearance(value: str) -> None:
        ctk.set_appearance_mode(value)
