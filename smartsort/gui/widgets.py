"""Small reusable UI building blocks shared across views."""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from smartsort.gui import theme
from smartsort.models import pluralize


class Card(ctk.CTkFrame):
    """A rounded, bordered container used throughout the app."""

    def __init__(self, master, **kwargs):
        kwargs.setdefault("fg_color", theme.CARD_BG)
        kwargs.setdefault("corner_radius", 14)
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", theme.CARD_BORDER)
        super().__init__(master, **kwargs)


class StatTile(Card):
    """A small metric card, e.g. '248 files scanned'."""

    def __init__(self, master, value: str, label: str, accent: str | None = None, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)

        value_color = accent or theme.TEXT_PRIMARY
        self.value_label = ctk.CTkLabel(
            self, text=value, font=theme.font(28, "bold"), text_color=value_color
        )
        self.value_label.grid(row=0, column=0, sticky="w", padx=18, pady=(16, 0))

        self.caption_label = ctk.CTkLabel(
            self, text=label, font=theme.font(12), text_color=theme.TEXT_SECONDARY
        )
        self.caption_label.grid(row=1, column=0, sticky="w", padx=18, pady=(0, 16))

    def set_value(self, value: str) -> None:
        self.value_label.configure(text=value)


class PrimaryButton(ctk.CTkButton):
    def __init__(self, master, **kwargs):
        kwargs.setdefault("fg_color", theme.ACCENT)
        kwargs.setdefault("hover_color", theme.ACCENT_HOVER)
        kwargs.setdefault("font", theme.font(13, "bold"))
        kwargs.setdefault("height", 40)
        kwargs.setdefault("corner_radius", 8)
        super().__init__(master, **kwargs)


class SecondaryButton(ctk.CTkButton):
    def __init__(self, master, **kwargs):
        kwargs.setdefault("fg_color", "transparent")
        kwargs.setdefault("hover_color", theme.CARD_HOVER)
        kwargs.setdefault("text_color", theme.TEXT_PRIMARY)
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", theme.CARD_BORDER)
        kwargs.setdefault("font", theme.font(13, "bold"))
        kwargs.setdefault("height", 40)
        kwargs.setdefault("corner_radius", 8)
        super().__init__(master, **kwargs)


class DangerButton(ctk.CTkButton):
    def __init__(self, master, **kwargs):
        kwargs.setdefault("fg_color", "transparent")
        kwargs.setdefault("hover_color", theme.DANGER_HOVER)
        kwargs.setdefault("text_color", theme.DANGER)
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", theme.DANGER)
        kwargs.setdefault("font", theme.font(12, "bold"))
        kwargs.setdefault("height", 32)
        kwargs.setdefault("corner_radius", 6)
        super().__init__(master, **kwargs)


class CategoryRow(Card):
    """One collapsible-looking row in the organization proposal list."""

    def __init__(
        self,
        master,
        icon: str,
        name: str,
        file_count: int,
        preview_names: list[str],
        on_review: Callable[[], None],
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(1, weight=1)

        icon_label = ctk.CTkLabel(self, text=icon, font=theme.font(22))
        icon_label.grid(row=0, column=0, rowspan=2, padx=(18, 12), pady=16, sticky="n")

        name_label = ctk.CTkLabel(
            self, text=name, font=theme.font(15, "bold"), text_color=theme.TEXT_PRIMARY
        )
        name_label.grid(row=0, column=1, sticky="w", pady=(16, 0))

        preview_text = ", ".join(preview_names[:3])
        if file_count > 3:
            preview_text += f", +{file_count - 3} more"
        preview_label = ctk.CTkLabel(
            self, text=preview_text, font=theme.font(12), text_color=theme.TEXT_SECONDARY
        )
        preview_label.grid(row=1, column=1, sticky="w", pady=(2, 16))

        count_label = ctk.CTkLabel(
            self, text=pluralize(file_count, "file"), font=theme.font(12), text_color=theme.TEXT_MUTED
        )
        count_label.grid(row=0, column=2, sticky="e", padx=(12, 12), pady=(16, 0))

        review_btn = SecondaryButton(self, text="Review  ›", width=90, height=30, command=on_review)
        review_btn.grid(row=1, column=2, sticky="e", padx=(12, 18), pady=(2, 16))


class ProgressStep(ctk.CTkFrame):
    """A single labelled step in a checklist-style progress animation."""

    def __init__(self, master, text: str, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(1, weight=1)

        self.status_label = ctk.CTkLabel(
            self, text="○", font=theme.font(14), text_color=theme.TEXT_MUTED, width=20
        )
        self.status_label.grid(row=0, column=0, sticky="w")

        self.text_label = ctk.CTkLabel(
            self, text=text, font=theme.font(13), text_color=theme.TEXT_SECONDARY, anchor="w"
        )
        self.text_label.grid(row=0, column=1, sticky="w", padx=(8, 0))

    def set_active(self) -> None:
        self.status_label.configure(text="◐", text_color=theme.ACCENT)
        self.text_label.configure(text_color=theme.TEXT_PRIMARY)

    def set_done(self) -> None:
        self.status_label.configure(text="✓", text_color=theme.SUCCESS)
        self.text_label.configure(text_color=theme.TEXT_PRIMARY)
