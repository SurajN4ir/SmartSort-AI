"""The main Overview flow: select a folder, analyze it, review, and apply.

This view is a small internal state machine. Each step renders fresh
widgets into a shared container rather than trying to keep one fixed
layout updated in place, which keeps each screen's code independent.
"""

from __future__ import annotations

import time
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from smartsort import local_config
from smartsort.categorizer import Categorizer
from smartsort.config import CATEGORY_ICONS
from smartsort.database import Database
from smartsort.gui import theme
from smartsort.gui.widgets import (
    Card,
    CategoryRow,
    PrimaryButton,
    ProgressStep,
    SecondaryButton,
    StatTile,
)
from smartsort.models import OrganizePlan, PlannedMove, format_size, pluralize
from smartsort.organizer import FileOrganizer
from smartsort.planner import OrganizationPlanner
from smartsort.scanner import FileScanner
from smartsort.semantic import SemanticClassifier, SemanticUnavailable

MAX_ANIMATED_MOVES = 60


class OverviewView(ctk.CTkFrame):
    def __init__(self, master, database: Database):
        super().__init__(master, fg_color="transparent")
        self.database = database
        self.scanner = FileScanner()
        self.categorizer = Categorizer()
        self.planner = OrganizationPlanner()
        self.organizer = FileOrganizer(database)

        self.selected_folder: Path | None = None
        self.plan: OrganizePlan | None = None
        self.review_filter: str | None = None
        self.row_vars: dict[int, ctk.BooleanVar] = {}
        self._scheduled: list[str] = []
        self.smart_mode = ctk.BooleanVar(value=False)
        self.smart_notice: str | None = None

        self.container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=36, pady=28)

        self.show_select()

    # -- helpers ----------------------------------------------------------

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

    def reset(self) -> None:
        self.selected_folder = None
        self.plan = None
        self.review_filter = None
        self.row_vars = {}
        self.show_select()

    def refresh_select_screen(self) -> None:
        """Re-render the select screen so it picks up a newly added API key.

        Only does anything if the user is still on that screen -- never
        interrupts an in-progress scan/review/apply flow.
        """

        if self.selected_folder is None and self.plan is None:
            self.show_select()

    # -- step 1: select -----------------------------------------------------

    def show_select(self) -> None:
        self.clear()

        wrapper = ctk.CTkFrame(self.container, fg_color="transparent")
        wrapper.pack(expand=True, pady=(60, 0))

        card = Card(wrapper, width=460, corner_radius=18)
        card.pack()
        card.grid_propagate(False)
        card.configure(width=460, height=360)

        ctk.CTkLabel(card, text="◈", font=theme.font(34)).pack(pady=(40, 6))
        ctk.CTkLabel(
            card, text="What should we organize?", font=theme.heading_font(18)
        ).pack(pady=(0, 4))
        ctk.CTkLabel(
            card,
            text="Choose a folder and SmartSort will propose\na tidy structure for it.",
            font=theme.font(12),
            text_color=theme.TEXT_SECONDARY,
            justify="center",
        ).pack(pady=(0, 20))

        PrimaryButton(card, text="Choose Folder", width=200, command=self.choose_folder).pack()

        key_available = local_config.has_api_key()
        toggle = ctk.CTkCheckBox(
            card,
            text="✦ Smart Organize (AI)",
            variable=self.smart_mode,
            state="normal" if key_available else "disabled",
            font=theme.font(12, "bold"),
            checkbox_width=18,
            checkbox_height=18,
        )
        toggle.pack(pady=(22, 2))
        if not key_available:
            self.smart_mode.set(False)
        hint_text = (
            "Groups files by meaning, not just file type (uses your Anthropic API key)."
            if key_available
            else "Add an Anthropic API key in Settings to enable meaning-based grouping."
        )
        ctk.CTkLabel(
            card, text=hint_text, font=theme.font(10), text_color=theme.TEXT_MUTED, wraplength=380
        ).pack()

        ctk.CTkLabel(
            card,
            text="Your files stay yours. Nothing moves without your approval.",
            font=theme.font(11),
            text_color=theme.TEXT_MUTED,
        ).pack(pady=(16, 0))

    def choose_folder(self) -> None:
        folder = filedialog.askdirectory(title="Choose a folder to organize")
        if not folder:
            return
        self.selected_folder = Path(folder)
        self.show_scanning()

    # -- step 2: scanning ----------------------------------------------------

    def show_scanning(self) -> None:
        self.clear()

        wrapper = ctk.CTkFrame(self.container, fg_color="transparent")
        wrapper.pack(expand=True, pady=(70, 0))

        card = Card(wrapper, width=460)
        card.pack()
        card.grid_propagate(False)
        card.configure(width=460, height=280)

        ctk.CTkLabel(
            card, text="Analyzing your folder...", font=theme.heading_font(16)
        ).pack(pady=(30, 4), padx=30, anchor="w")
        ctk.CTkLabel(
            card, text=str(self.selected_folder), font=theme.font(11), text_color=theme.TEXT_MUTED
        ).pack(pady=(0, 16), padx=30, anchor="w")

        progress = ctk.CTkProgressBar(card, width=380, progress_color=theme.ACCENT)
        progress.pack(padx=30, pady=(0, 20))
        progress.set(0)

        steps_frame = ctk.CTkFrame(card, fg_color="transparent")
        steps_frame.pack(padx=30, fill="x")

        if self.smart_mode.get():
            step_labels = ["Scanning files", "Detecting file types", "Asking AI for smarter categories"]
        else:
            step_labels = ["Scanning files", "Detecting file types", "Grouping into categories"]
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

        self.smart_notice = None
        if self.smart_mode.get() and scanned:
            classified = self._classify_with_ai(scanned)
        else:
            classified = self.categorizer.classify_all(scanned)

        self.plan = self.planner.generate_plan(self.selected_folder, classified)
        self.row_vars = {id(m): ctk.BooleanVar(value=True) for m in self.plan.moves}

        if not self.plan.moves:
            self.show_empty_result()
        else:
            self.show_proposal()

    def _classify_with_ai(self, scanned) -> list:
        try:
            classifier = SemanticClassifier(api_key=local_config.get_api_key())
            guesses = classifier.classify_batch([f.name for f in scanned])
            return self.categorizer.classify_with_guesses(scanned, guesses)
        except SemanticUnavailable as exc:
            self.smart_notice = str(exc)
        except Exception:
            self.smart_notice = "Smart Organize hit an unexpected error -- used standard rules instead."
        return self.categorizer.classify_all(scanned)

    def show_select_error(self, message: str) -> None:
        self.clear()
        wrapper = ctk.CTkFrame(self.container, fg_color="transparent")
        wrapper.pack(expand=True, pady=(90, 0))
        ctk.CTkLabel(wrapper, text="Couldn't read that folder", font=theme.heading_font(16)).pack()
        ctk.CTkLabel(wrapper, text=message, font=theme.font(12), text_color=theme.TEXT_SECONDARY).pack(pady=(6, 20))
        SecondaryButton(wrapper, text="Try another folder", command=self.reset).pack()

    def show_empty_result(self) -> None:
        self.clear()
        wrapper = ctk.CTkFrame(self.container, fg_color="transparent")
        wrapper.pack(expand=True, pady=(90, 0))
        ctk.CTkLabel(wrapper, text="✦ Already tidy", font=theme.heading_font(18)).pack()
        ctk.CTkLabel(
            wrapper,
            text="This folder has nothing SmartSort can organize right now.",
            font=theme.font(12),
            text_color=theme.TEXT_SECONDARY,
        ).pack(pady=(6, 20))
        SecondaryButton(wrapper, text="Choose another folder", command=self.reset).pack()

    # -- step 3: proposal -----------------------------------------------------

    def show_proposal(self) -> None:
        self.clear()
        plan = self.plan

        header = ctk.CTkFrame(self.container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 18))
        ctk.CTkLabel(header, text="✦ Organization proposal", font=theme.heading_font(20)).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text=f"I found {plan.total_files} files that can be organized into {plan.total_categories} groups.",
            font=theme.font(13),
            text_color=theme.TEXT_SECONDARY,
        ).pack(anchor="w", pady=(4, 0))

        ai_count = sum(1 for m in plan.moves if m.is_ai_suggested)
        if ai_count:
            ctk.CTkLabel(
                header,
                text=f"✦ Smart Organize grouped {pluralize(ai_count, 'file')} by meaning, not just type.",
                font=theme.font(11, "bold"),
                text_color=theme.ACCENT,
            ).pack(anchor="w", pady=(6, 0))
        if self.smart_notice:
            ctk.CTkLabel(
                header,
                text=f"⚠ {self.smart_notice}",
                font=theme.font(11),
                text_color=theme.WARNING,
                wraplength=700,
                justify="left",
            ).pack(anchor="w", pady=(6, 0))

        stats_row = ctk.CTkFrame(self.container, fg_color="transparent")
        stats_row.pack(fill="x", pady=(0, 20))
        StatTile(stats_row, str(plan.total_files), "Files found").pack(side="left", padx=(0, 12))
        StatTile(stats_row, str(plan.total_categories), "Categories").pack(side="left", padx=(0, 12))
        total_size = format_size(sum(m.size for m in plan.moves))
        StatTile(stats_row, total_size, "Total size").pack(side="left")

        for category, moves in sorted(plan.categories.items(), key=lambda kv: -len(kv[1])):
            icon = CATEGORY_ICONS.get(category, "📁")
            names = [m.name for m in moves]
            row = CategoryRow(
                self.container,
                icon=icon,
                name=category,
                file_count=len(moves),
                preview_names=names,
                on_review=lambda c=category: self.show_review(filter_category=c),
            )
            row.pack(fill="x", pady=6)

        footer = ctk.CTkFrame(self.container, fg_color="transparent")
        footer.pack(fill="x", pady=(20, 0))
        SecondaryButton(footer, text="Choose another folder", command=self.reset).pack(side="left")
        PrimaryButton(
            footer, text="Review Changes", width=180, command=lambda: self.show_review(None)
        ).pack(side="right")

    # -- step 4: review -----------------------------------------------------

    def show_review(self, filter_category: str | None) -> None:
        self.clear()
        self.review_filter = filter_category
        plan = self.plan

        header = ctk.CTkFrame(self.container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(header, text="Review changes", font=theme.heading_font(20)).pack(anchor="w")

        moves = plan.moves if filter_category is None else plan.categories.get(filter_category, [])
        count_label = ctk.CTkLabel(
            self.container,
            text=f"{pluralize(len(moves), 'file')} will be moved" + (f" — {filter_category}" if filter_category else ""),
            font=theme.font(13),
            text_color=theme.TEXT_SECONDARY,
        )
        count_label.pack(anchor="w", pady=(0, 14))

        toolbar = ctk.CTkFrame(self.container, fg_color="transparent")
        toolbar.pack(fill="x", pady=(0, 10))

        select_all_var = ctk.BooleanVar(value=all(self.row_vars[id(m)].get() for m in moves) if moves else True)

        def toggle_all():
            value = select_all_var.get()
            for m in moves:
                self.row_vars[id(m)].set(value)
                if id(m) in self.row_checkboxes:
                    self.row_checkboxes[id(m)].select() if value else self.row_checkboxes[id(m)].deselect()

        ctk.CTkCheckBox(
            toolbar, text="Select all", variable=select_all_var, command=toggle_all,
            font=theme.font(12), checkbox_width=18, checkbox_height=18,
        ).pack(side="left")

        if filter_category:
            SecondaryButton(
                toolbar, text="Show all files", width=120, height=30,
                command=lambda: self.show_review(None),
            ).pack(side="right")

        table = Card(self.container)
        table.pack(fill="both", expand=True)
        table.grid_columnconfigure(1, weight=1)

        self.row_checkboxes: dict[int, ctk.CTkCheckBox] = {}

        header_row = ctk.CTkFrame(table, fg_color="transparent")
        header_row.pack(fill="x", padx=16, pady=(14, 6))
        ctk.CTkLabel(header_row, text="FROM  →  TO", font=theme.font(11, "bold"), text_color=theme.TEXT_MUTED).pack(side="left")
        ctk.CTkLabel(header_row, text="CATEGORY", font=theme.font(11, "bold"), text_color=theme.TEXT_MUTED).pack(side="right", padx=(0, 4))

        for move in moves:
            self._build_review_row(table, move)

        footer = ctk.CTkFrame(self.container, fg_color="transparent")
        footer.pack(fill="x", pady=(18, 4))
        SecondaryButton(footer, text="Cancel", command=self.show_proposal).pack(side="left")
        PrimaryButton(
            footer, text="Apply Changes", width=180, command=self.show_applying
        ).pack(side="right")

    def _build_review_row(self, table: ctk.CTkFrame, move: PlannedMove) -> None:
        row = ctk.CTkFrame(table, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=4)
        row.grid_columnconfigure(1, weight=1)

        var = self.row_vars[id(move)]
        checkbox = ctk.CTkCheckBox(
            row, text="", variable=var, width=18, checkbox_width=18, checkbox_height=18,
            command=lambda: setattr(move, "selected", var.get()),
        )
        checkbox.grid(row=0, column=0, padx=(0, 10))
        if var.get():
            checkbox.select()
        self.row_checkboxes[id(move)] = checkbox

        rel_source = self._relative(move.source)
        rel_dest = self._relative(move.destination)
        path_label = ctk.CTkLabel(
            row,
            text=f"{rel_source}   →   {rel_dest}",
            font=theme.font(12),
            text_color=theme.TEXT_PRIMARY,
            anchor="w",
        )
        path_label.grid(row=0, column=1, sticky="w")

        badge_label = ctk.CTkLabel(row, text="", font=theme.font(10, "bold"), text_color=theme.ACCENT)
        badge_label.grid(row=0, column=2, padx=(8, 4))
        self._set_confidence_badge(badge_label, move)

        size_label = ctk.CTkLabel(
            row, text=format_size(move.size), font=theme.font(11), text_color=theme.TEXT_MUTED
        )
        size_label.grid(row=0, column=3, padx=(8, 10))

        categories = sorted({m.category for m in self.plan.moves} | {move.category})
        category_menu = ctk.CTkOptionMenu(
            row,
            values=categories,
            width=130,
            height=28,
            fg_color=theme.CARD_HOVER,
            button_color=theme.ACCENT,
            button_hover_color=theme.ACCENT_HOVER,
            font=theme.font(11),
            command=lambda new_value, m=move, lbl=path_label, badge=badge_label: self._change_category(m, new_value, lbl, badge),
        )
        category_menu.set(move.category)
        category_menu.grid(row=0, column=4)

    def _set_confidence_badge(self, badge_label: ctk.CTkLabel, move: PlannedMove) -> None:
        if move.is_ai_suggested and move.confidence is not None:
            badge_label.configure(text=f"✦ {round(move.confidence * 100)}%")
        else:
            badge_label.configure(text="")

    def _change_category(
        self, move: PlannedMove, new_category: str, path_label: ctk.CTkLabel, badge_label: ctk.CTkLabel
    ) -> None:
        self.planner.retarget(self.plan, move, new_category)
        self._set_confidence_badge(badge_label, move)
        rel_source = self._relative(move.source)
        rel_dest = self._relative(move.destination)
        path_label.configure(text=f"{rel_source}   →   {rel_dest}")

    def _relative(self, path: Path, max_len: int = 42) -> str:
        try:
            text = str(path.relative_to(self.selected_folder.parent))
        except ValueError:
            text = str(path)
        if len(text) <= max_len:
            return text
        # Truncate from the front so the filename (the most useful part for
        # picking a row out of the list) always stays visible.
        return "…" + text[-(max_len - 1):]

    # -- step 5: applying -----------------------------------------------------

    def show_applying(self) -> None:
        self.clear()
        moves = self.plan.selected_moves

        wrapper = ctk.CTkFrame(self.container, fg_color="transparent")
        wrapper.pack(expand=True, pady=(50, 0))

        card = Card(wrapper, width=480)
        card.pack()
        card.grid_propagate(False)
        card.configure(width=480, height=min(560, 140 + 30 * max(1, len(moves))))

        ctk.CTkLabel(card, text="Organizing your files...", font=theme.heading_font(16)).pack(pady=(26, 16))

        list_frame = ctk.CTkScrollableFrame(card, width=420, height=min(360, 30 * max(1, len(moves))), fg_color="transparent")
        list_frame.pack(padx=20, fill="both", expand=True)

        rows: dict[int, ProgressStep] = {}
        for move in moves:
            step = ProgressStep(list_frame, move.name)
            step.pack(fill="x", pady=3)
            rows[id(move)] = step

        self._schedule(200, lambda: self._run_apply(moves, rows, card))

    def _run_apply(self, moves: list[PlannedMove], rows: dict[int, ProgressStep], card: ctk.CTkFrame) -> None:
        animate = len(moves) <= MAX_ANIMATED_MOVES
        delay = 0.08 if animate else 0.0

        def on_progress(move: PlannedMove, success: bool) -> None:
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

        self.plan.moves = moves + [m for m in self.plan.moves if not m.selected]
        result = self.organizer.apply(self.plan, progress_callback=on_progress)
        self._schedule(300, lambda: self.show_done(result))

    # -- step 6: done -----------------------------------------------------

    def show_done(self, result) -> None:
        self.clear()
        wrapper = ctk.CTkFrame(self.container, fg_color="transparent")
        wrapper.pack(expand=True, pady=(60, 0))

        card = Card(wrapper, width=440)
        card.pack()
        card.grid_propagate(False)
        card.configure(width=440, height=320)

        ctk.CTkLabel(card, text="✦", font=theme.font(30), text_color=theme.SUCCESS).pack(pady=(34, 6))
        ctk.CTkLabel(card, text="All sorted.", font=theme.heading_font(18)).pack()

        stats = ctk.CTkFrame(card, fg_color="transparent")
        stats.pack(pady=22)
        ctk.CTkLabel(
            stats, text=f"{pluralize(result.moved_count, 'file')} organized", font=theme.font(13), text_color=theme.TEXT_SECONDARY
        ).pack()
        ctk.CTkLabel(
            stats, text=f"{pluralize(result.folders_created, 'folder')} created", font=theme.font(13), text_color=theme.TEXT_SECONDARY
        ).pack(pady=(4, 0))
        error_color = theme.DANGER if result.error_count else theme.TEXT_SECONDARY
        ctk.CTkLabel(
            stats, text=pluralize(result.error_count, 'error'), font=theme.font(13), text_color=error_color
        ).pack(pady=(4, 0))

        PrimaryButton(card, text="Done", width=160, command=self.reset).pack(pady=(10, 0))
