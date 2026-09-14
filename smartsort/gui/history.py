"""History view: past organize sessions, with drill-down and undo."""

from __future__ import annotations

import customtkinter as ctk

from smartsort.database import Database, SessionRecord
from smartsort.gui import theme
from smartsort.gui.widgets import Card, DangerButton, SecondaryButton
from smartsort.models import format_size, pluralize
from smartsort.organizer import FileOrganizer


class HistoryView(ctk.CTkFrame):
    def __init__(self, master, database: Database):
        super().__init__(master, fg_color="transparent")
        self.database = database
        self.organizer = FileOrganizer(database)
        self.selected_session_id: int | None = None

        self.container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=36, pady=28)

        self.refresh()

    def refresh(self) -> None:
        if self.selected_session_id is not None:
            self.show_detail(self.selected_session_id)
        else:
            self.show_list()

    def clear(self) -> None:
        for widget in self.container.winfo_children():
            widget.destroy()

    def show_list(self) -> None:
        self.clear()
        self.selected_session_id = None

        ctk.CTkLabel(self.container, text="History", font=theme.heading_font(20)).pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(
            self.container,
            text="Every folder SmartSort has organized, and what changed.",
            font=theme.font(13),
            text_color=theme.TEXT_SECONDARY,
        ).pack(anchor="w", pady=(0, 20))

        sessions = self.database.list_sessions()
        if not sessions:
            empty = Card(self.container)
            empty.pack(fill="x", pady=10)
            ctk.CTkLabel(
                empty, text="Nothing organized yet.", font=theme.font(13), text_color=theme.TEXT_SECONDARY
            ).pack(pady=30)
            return

        last_day = None
        for session in sessions:
            day = session.created_at.split("T")[0]
            if day != last_day:
                ctk.CTkLabel(
                    self.container, text=day, font=theme.font(11, "bold"), text_color=theme.TEXT_MUTED
                ).pack(anchor="w", pady=(14, 6))
                last_day = day
            self._build_session_row(session)

    def _build_session_row(self, session: SessionRecord) -> None:
        card = Card(self.container)
        card.pack(fill="x", pady=5)
        card.grid_columnconfigure(0, weight=1)

        info = ctk.CTkFrame(card, fg_color="transparent")
        info.grid(row=0, column=0, sticky="w", padx=18, pady=14)

        folder_name = session.folder_path.rstrip("\\/").split("/")[-1].split("\\")[-1]
        ctk.CTkLabel(info, text=folder_name or session.folder_path, font=theme.font(14, "bold")).pack(anchor="w")

        status_text, status_color = self._status_display(session)
        detail = f"{pluralize(session.moved_count, 'file')} organized · {pluralize(session.total_categories, 'category', 'categories')}"
        ctk.CTkLabel(
            info, text=detail, font=theme.font(11), text_color=theme.TEXT_SECONDARY
        ).pack(anchor="w", pady=(2, 0))

        badge = ctk.CTkLabel(
            card, text=status_text, font=theme.font(11, "bold"), text_color=status_color
        )
        badge.grid(row=0, column=1, padx=(0, 10))

        SecondaryButton(
            card, text="Details  ›", width=90, height=30,
            command=lambda sid=session.id: self.show_detail(sid),
        ).grid(row=0, column=2, padx=(0, 18))

    @staticmethod
    def _status_display(session: SessionRecord) -> tuple[str, str]:
        if session.undone:
            return "↺ Undone", theme.TEXT_MUTED
        if session.error_count:
            return "⚠ Partial", theme.WARNING
        return "✓ Completed", theme.SUCCESS

    def show_detail(self, session_id: int) -> None:
        self.clear()
        self.selected_session_id = session_id
        session = self.database.get_session(session_id)
        moves = self.database.get_moves(session_id)

        if session is None:
            self.show_list()
            return

        top = ctk.CTkFrame(self.container, fg_color="transparent")
        top.pack(fill="x", pady=(0, 4))
        SecondaryButton(top, text="‹ Back", width=80, height=30, command=self.show_list).pack(anchor="w")

        header = ctk.CTkFrame(self.container, fg_color="transparent")
        header.pack(fill="x", pady=(16, 20))
        ctk.CTkLabel(header, text=session.folder_path, font=theme.heading_font(18)).pack(anchor="w")
        status_text, status_color = self._status_display(session)
        ctk.CTkLabel(
            header,
            text=f"{session.created_at}   ·   {status_text}",
            font=theme.font(12),
            text_color=status_color,
        ).pack(anchor="w", pady=(4, 0))

        if not session.undone and session.moved_count:
            DangerButton(
                header, text="Undo this organization", command=lambda: self._undo(session_id)
            ).pack(anchor="w", pady=(12, 0))

        table = Card(self.container)
        table.pack(fill="both", expand=True)

        for move in moves:
            row = ctk.CTkFrame(table, fg_color="transparent")
            row.pack(fill="x", padx=18, pady=6)
            row.grid_columnconfigure(0, weight=1)

            text = f"{move.file_name}   →   {move.category}/"
            color = theme.TEXT_MUTED if move.undone else theme.TEXT_PRIMARY
            ctk.CTkLabel(row, text=text, font=theme.font(12), text_color=color, anchor="w").grid(row=0, column=0, sticky="w")
            ctk.CTkLabel(
                row, text=format_size(move.size), font=theme.font(11), text_color=theme.TEXT_MUTED
            ).grid(row=0, column=1, padx=(10, 0))

    def _undo(self, session_id: int) -> None:
        self.organizer.undo(session_id)
        self.show_detail(session_id)
