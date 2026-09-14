"""Duplicate cleanup flow: scan (recursively), review which copy to keep, move the rest aside.

Mirrors the same select -> scan -> review -> apply -> done shape as the
Overview tab, and reuses the exact same FileOrganizer/Database plumbing --
so a cleanup session shows up in History and can be undone exactly like an
organize session can.
"""

from __future__ import annotations

import time
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from smartsort.database import Database
from smartsort.duplicates import DuplicateGroup, build_cleanup_plan, find_duplicates
from smartsort.gui import theme
from smartsort.gui.widgets import Card, PrimaryButton, ProgressStep, SecondaryButton, StatTile
from smartsort.models import format_size, pluralize
from smartsort.organizer import FileOrganizer
from smartsort.scanner import FileScanner

MAX_ANIMATED_MOVES = 60


class DuplicatesView(ctk.CTkFrame):
    def __init__(self, master, database: Database):
        super().__init__(master, fg_color="transparent")
        self.database = database
        self.scanner = FileScanner(recursive=True)
        self.organizer = FileOrganizer(database)

        self.selected_folder: Path | None = None
        self.groups: list[DuplicateGroup] = []
        self.group_include_vars: dict[int, ctk.BooleanVar] = {}
        self.group_keep_vars: dict[int, ctk.StringVar] = {}
        self._scheduled: list[str] = []

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.center_host = ctk.CTkFrame(self, fg_color="transparent")
        self.center_host.grid_rowconfigure(0, weight=1)
        self.center_host.grid_columnconfigure(0, weight=1)

        self.show_select()

    # -- helpers ----------------------------------------------------------

    def _use_scrollable(self) -> ctk.CTkScrollableFrame:
        self.center_host.grid_forget()
        self.container.grid(row=0, column=0, sticky="nsew", padx=36, pady=28)
        return self.container

    def _use_centered(self) -> ctk.CTkFrame:
        self.container.grid_forget()
        self.center_host.grid(row=0, column=0, sticky="nsew")
        return self.center_host

    def _schedule(self, delay_ms: int, callback) -> None:
        after_id = self.after(delay_ms, callback)
        self._scheduled.append(after_id)

    def _cancel_scheduled(self) -> None:
        for after_id in self._scheduled:
            try:
                self.after_cancel(after_id)
            except ValueError:
                pass
        self._scheduled = []

    def clear(self) -> None:
        self._cancel_scheduled()
        for widget in self.container.winfo_children():
            widget.destroy()
        for widget in self.center_host.winfo_children():
            widget.destroy()

    def reset(self) -> None:
        self.selected_folder = None
        self.groups = []
        self.group_include_vars = {}
        self.group_keep_vars = {}
        self.show_select()

    # -- step 1: select -----------------------------------------------------

    def show_select(self) -> None:
        self.clear()
        host = self._use_centered()

        card = Card(host, width=460, corner_radius=18)
        card.grid(row=0, column=0)
        card.grid_propagate(False)
        card.configure(width=460, height=310)

        ctk.CTkLabel(card, text="⧉", font=theme.font(34)).pack(pady=(40, 6))
        ctk.CTkLabel(card, text="Find duplicate files", font=theme.heading_font(18)).pack(pady=(0, 4))
        ctk.CTkLabel(
            card,
            text="Scans a folder and everything inside it for files\nwith identical content.",
            font=theme.font(12),
            text_color=theme.TEXT_SECONDARY,
            justify="center",
        ).pack(pady=(0, 20))

        PrimaryButton(card, text="Choose Folder", width=200, command=self.choose_folder).pack()

        ctk.CTkLabel(
            card,
            text="Duplicates are moved into a Duplicates folder for review --\nnothing is ever deleted automatically.",
            font=theme.font(11),
            text_color=theme.TEXT_MUTED,
            justify="center",
        ).pack(pady=(24, 0))

    def choose_folder(self) -> None:
        folder = filedialog.askdirectory(title="Choose a folder to scan for duplicates")
        if not folder:
            return
        self.selected_folder = Path(folder)
        self.show_scanning()

    # -- step 2: scanning ----------------------------------------------------

    def show_scanning(self) -> None:
        self.clear()
        host = self._use_centered()

        card = Card(host, width=460)
        card.grid(row=0, column=0)
        card.grid_propagate(False)
        card.configure(width=460, height=280)

        ctk.CTkLabel(
            card, text="Scanning for duplicates...", font=theme.heading_font(16)
        ).pack(pady=(30, 4), padx=30, anchor="w")
        ctk.CTkLabel(
            card, text=str(self.selected_folder), font=theme.font(11), text_color=theme.TEXT_MUTED
        ).pack(pady=(0, 16), padx=30, anchor="w")

        progress = ctk.CTkProgressBar(card, width=380, progress_color=theme.ACCENT)
        progress.pack(padx=30, pady=(0, 20))
        progress.set(0)

        steps_frame = ctk.CTkFrame(card, fg_color="transparent")
        steps_frame.pack(padx=30, fill="x")

        step_labels = ["Scanning files", "Comparing file sizes", "Checking file content"]
        steps = [ProgressStep(steps_frame, text) for text in step_labels]
        for step in steps:
            step.pack(fill="x", pady=3)

        self._schedule(80, lambda: self._animate_scan(progress, steps, 0))

    def _animate_scan(self, progress: ctk.CTkProgressBar, steps: list[ProgressStep], index: int) -> None:
        if index > 0:
            steps[index - 1].set_done()
        if index >= len(steps) - 1:
            steps[-1].set_active()
            progress.set(0.9)
            self._schedule(150, self.run_scan)
            return

        steps[index].set_active()
        progress.set((index + 1) / (len(steps) + 0.5))
        self._schedule(220, lambda: self._animate_scan(progress, steps, index + 1))

    def run_scan(self) -> None:
        try:
            scanned = self.scanner.scan(self.selected_folder)
        except (FileNotFoundError, NotADirectoryError) as exc:
            self.show_select_error(str(exc))
            return

        self.groups = find_duplicates(scanned)
        self.group_include_vars = {i: ctk.BooleanVar(value=True) for i in range(len(self.groups))}
        self.group_keep_vars = {i: ctk.StringVar(value=str(g.keep.path)) for i, g in enumerate(self.groups)}

        if not self.groups:
            self.show_empty_result()
        else:
            self.show_results()

    def show_select_error(self, message: str) -> None:
        self.clear()
        host = self._use_centered()
        wrapper = ctk.CTkFrame(host, fg_color="transparent")
        wrapper.grid(row=0, column=0)
        ctk.CTkLabel(wrapper, text="Couldn't read that folder", font=theme.heading_font(16)).pack()
        ctk.CTkLabel(wrapper, text=message, font=theme.font(12), text_color=theme.TEXT_SECONDARY).pack(pady=(6, 20))
        SecondaryButton(wrapper, text="Try another folder", command=self.reset).pack()

    def show_empty_result(self) -> None:
        self.clear()
        host = self._use_centered()
        wrapper = ctk.CTkFrame(host, fg_color="transparent")
        wrapper.grid(row=0, column=0)
        ctk.CTkLabel(wrapper, text="✦ No duplicates found", font=theme.heading_font(18)).pack()
        ctk.CTkLabel(
            wrapper,
            text="Every file in this folder (and its subfolders) is unique.",
            font=theme.font(12),
            text_color=theme.TEXT_SECONDARY,
        ).pack(pady=(6, 20))
        SecondaryButton(wrapper, text="Choose another folder", command=self.reset).pack()

    # -- step 3: results / review -----------------------------------------------------

    def show_results(self) -> None:
        self.clear()
        self._use_scrollable()

        header = ctk.CTkFrame(self.container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 18))
        ctk.CTkLabel(header, text="✦ Duplicates found", font=theme.heading_font(20)).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text=f"Found {pluralize(len(self.groups), 'group')} of duplicate files. Pick which copy to keep in each.",
            font=theme.font(13),
            text_color=theme.TEXT_SECONDARY,
        ).pack(anchor="w", pady=(4, 0))

        total_wasted = sum(g.wasted_bytes for g in self.groups)
        total_dupe_files = sum(len(g.duplicates) for g in self.groups)

        stats_row = ctk.CTkFrame(self.container, fg_color="transparent")
        stats_row.pack(fill="x", pady=(0, 20))
        StatTile(stats_row, str(len(self.groups)), "Duplicate groups").pack(side="left", padx=(0, 12))
        StatTile(stats_row, str(total_dupe_files), "Extra copies").pack(side="left", padx=(0, 12))
        StatTile(
            stats_row, format_size(total_wasted), "Space to reclaim", accent=theme.SUCCESS
        ).pack(side="left")

        for index, group in enumerate(self.groups):
            self._build_group_card(index, group)

        footer = ctk.CTkFrame(self.container, fg_color="transparent")
        footer.pack(fill="x", pady=(20, 4))
        SecondaryButton(footer, text="Choose another folder", command=self.reset).pack(side="left")
        PrimaryButton(
            footer, text="Clean Up Duplicates", width=200, command=self.show_applying
        ).pack(side="right")

    def _build_group_card(self, index: int, group: DuplicateGroup) -> None:
        card = Card(self.container)
        card.pack(fill="x", pady=6)

        top_row = ctk.CTkFrame(card, fg_color="transparent")
        top_row.pack(fill="x", padx=18, pady=(14, 8))

        include_var = self.group_include_vars[index]
        ctk.CTkCheckBox(
            top_row, text="", variable=include_var, width=18, checkbox_width=18, checkbox_height=18,
        ).pack(side="left", padx=(0, 10))

        ctk.CTkLabel(
            top_row,
            text=f"{pluralize(len(group.files), 'copy', 'copies')} found  ·  "
            f"{format_size(group.wasted_bytes)} can be reclaimed",
            font=theme.font(13, "bold"),
            text_color=theme.TEXT_PRIMARY,
        ).pack(side="left")

        keep_var = self.group_keep_vars[index]
        status_labels: dict[str, ctk.CTkLabel] = {}

        def refresh_statuses() -> None:
            for scanned in group.files:
                label = status_labels[str(scanned.path)]
                if scanned is group.keep:
                    label.configure(text="kept in place", text_color=theme.SUCCESS)
                else:
                    label.configure(text="→ Duplicates/", text_color=theme.WARNING)

        for scanned in group.files:
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=(46, 18), pady=2)
            ctk.CTkRadioButton(
                row,
                text=self._display_path(scanned.path),
                variable=keep_var,
                value=str(scanned.path),
                font=theme.font(11),
                command=lambda i=index, s=scanned, refresh=refresh_statuses: self._set_keep(i, s, refresh),
            ).pack(side="left")

            status_label = ctk.CTkLabel(row, text="", font=theme.font(10, "bold"), width=90, anchor="e")
            status_label.pack(side="right")
            status_labels[str(scanned.path)] = status_label

            ctk.CTkLabel(
                row, text=format_size(scanned.size), font=theme.font(10), text_color=theme.TEXT_MUTED, width=60, anchor="e"
            ).pack(side="right", padx=(0, 10))

        refresh_statuses()
        ctk.CTkLabel(card, text="", height=6).pack()

    def _set_keep(self, index: int, scanned, refresh_callback) -> None:
        self.groups[index].keep = scanned
        refresh_callback()

    def _display_path(self, path: Path, max_len: int = 60) -> str:
        try:
            text = str(path.relative_to(self.selected_folder))
        except ValueError:
            text = str(path)
        if len(text) <= max_len:
            return text
        return "…" + text[-(max_len - 1):]

    # -- step 4: applying -----------------------------------------------------

    def show_applying(self) -> None:
        self.clear()
        host = self._use_centered()
        included_groups = [g for i, g in enumerate(self.groups) if self.group_include_vars[i].get()]
        plan = build_cleanup_plan(self.selected_folder, included_groups)
        moves = plan.moves

        if not moves:
            card = Card(host, width=440)
            card.grid(row=0, column=0)
            ctk.CTkLabel(card, text="Nothing selected", font=theme.heading_font(16)).pack(pady=(30, 6))
            ctk.CTkLabel(
                card,
                text="No duplicate groups were checked in for cleanup.",
                font=theme.font(12),
                text_color=theme.TEXT_SECONDARY,
            ).pack(pady=(0, 20))
            SecondaryButton(card, text="Back", command=self.show_results).pack(pady=(0, 30))
            return

        card = Card(host, width=480)
        card.grid(row=0, column=0)
        card.grid_propagate(False)
        card.configure(width=480, height=min(560, 140 + 30 * max(1, len(moves))))

        ctk.CTkLabel(card, text="Cleaning up duplicates...", font=theme.heading_font(16)).pack(pady=(26, 16))

        list_frame = ctk.CTkScrollableFrame(
            card, width=420, height=min(360, 30 * max(1, len(moves))), fg_color="transparent"
        )
        list_frame.pack(padx=20, fill="both", expand=True)

        rows: dict[int, ProgressStep] = {}
        for move in moves:
            step = ProgressStep(list_frame, move.name)
            step.pack(fill="x", pady=3)
            rows[id(move)] = step

        self._schedule(200, lambda: self._run_apply(plan, rows))

    def _run_apply(self, plan, rows: dict[int, ProgressStep]) -> None:
        moves = plan.moves
        animate = len(moves) <= MAX_ANIMATED_MOVES
        delay = 0.08 if animate else 0.0

        def on_progress(move, success: bool) -> None:
            step = rows.get(id(move))
            if step:
                if success:
                    step.set_done()
                else:
                    step.status_label.configure(text="✕", text_color=theme.DANGER)
                    step.text_label.configure(text_color=theme.DANGER)
            self.update_idletasks()
            if delay:
                time.sleep(delay)

        result = self.organizer.apply(plan, progress_callback=on_progress, kind="dedupe")
        self._schedule(300, lambda: self.show_done(result))

    # -- step 5: done -----------------------------------------------------

    def show_done(self, result) -> None:
        self.clear()
        host = self._use_centered()
        card = Card(host, width=460)
        card.grid(row=0, column=0)
        card.grid_propagate(False)
        card.configure(width=460, height=340)

        ctk.CTkLabel(card, text="✦", font=theme.font(30), text_color=theme.SUCCESS).pack(pady=(34, 6))
        ctk.CTkLabel(card, text="Duplicates cleaned up.", font=theme.heading_font(18)).pack()

        stats = ctk.CTkFrame(card, fg_color="transparent")
        stats.pack(pady=22)
        ctk.CTkLabel(
            stats,
            text=f"{pluralize(result.moved_count, 'file')} moved to Duplicates/",
            font=theme.font(13),
            text_color=theme.TEXT_SECONDARY,
        ).pack()
        error_color = theme.DANGER if result.error_count else theme.TEXT_SECONDARY
        ctk.CTkLabel(
            stats, text=pluralize(result.error_count, "error"), font=theme.font(13), text_color=error_color
        ).pack(pady=(4, 0))
        ctk.CTkLabel(
            stats,
            text="Nothing was deleted -- review the Duplicates folder,\nthen remove it yourself once you're sure.",
            font=theme.font(11),
            text_color=theme.TEXT_MUTED,
            justify="center",
        ).pack(pady=(10, 0))

        PrimaryButton(card, text="Done", width=160, command=self.reset).pack(pady=(14, 0))
