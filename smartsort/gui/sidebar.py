"""Left navigation rail."""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from smartsort.gui import theme

NAV_ITEMS = [
    ("overview", "⌂", "Overview"),
    ("history", "◷", "History"),
    ("settings", "⚙", "Settings"),
]


class Sidebar(ctk.CTkFrame):
    def __init__(self, master, on_navigate: Callable[[str], None]):
        super().__init__(master, width=210, corner_radius=0, fg_color=theme.SIDEBAR_BG)
        self.grid_propagate(False)
        self.on_navigate = on_navigate
        self.buttons: dict[str, ctk.CTkButton] = {}

        brand = ctk.CTkLabel(
            self, text="◈  SmartSort", font=theme.font(19, "bold"), text_color=theme.TEXT_PRIMARY
        )
        brand.pack(anchor="w", padx=24, pady=(28, 6))

        tagline = ctk.CTkLabel(
            self, text="AI-assisted file organizer",
            font=theme.font(11), text_color=theme.TEXT_MUTED,
        )
        tagline.pack(anchor="w", padx=24, pady=(0, 28))

        nav_frame = ctk.CTkFrame(self, fg_color="transparent")
        nav_frame.pack(fill="x", padx=14)

        for key, icon, label in NAV_ITEMS:
            btn = ctk.CTkButton(
                nav_frame,
                text=f"{icon}   {label}",
                anchor="w",
                height=40,
                corner_radius=8,
                font=theme.font(13),
                fg_color="transparent",
                text_color=theme.TEXT_SECONDARY,
                hover_color=theme.CARD_HOVER,
                command=lambda k=key: self.on_navigate(k),
            )
            btn.pack(fill="x", pady=3)
            self.buttons[key] = btn

        status_frame = ctk.CTkFrame(self, fg_color="transparent")
        status_frame.pack(side="bottom", fill="x", padx=24, pady=22)
        ctk.CTkLabel(
            status_frame, text="●  Ready", font=theme.font(11), text_color=theme.SUCCESS
        ).pack(anchor="w")

    def set_active(self, key: str) -> None:
        for k, btn in self.buttons.items():
            if k == key:
                btn.configure(fg_color=theme.ACCENT, text_color="white", hover_color=theme.ACCENT_HOVER)
            else:
                btn.configure(fg_color="transparent", text_color=theme.TEXT_SECONDARY, hover_color=theme.CARD_HOVER)
