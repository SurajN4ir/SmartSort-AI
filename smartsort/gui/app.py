"""Top-level application window."""

from __future__ import annotations

import customtkinter as ctk

from smartsort.database import Database
from smartsort.gui import theme
from smartsort.gui.history import HistoryView
from smartsort.gui.overview import OverviewView
from smartsort.gui.settings import SettingsView
from smartsort.gui.sidebar import Sidebar


class SmartSortApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("SmartSort")
        self.geometry("1100x700")
        self.minsize(920, 600)
        self.configure(fg_color=theme.BG)

        self.database = Database()

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = Sidebar(self, on_navigate=self.show_view)
        self.sidebar.grid(row=0, column=0, sticky="nsw")

        self.content = ctk.CTkFrame(self, fg_color=theme.BG, corner_radius=0)
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        self.views = {
            "overview": OverviewView(self.content, database=self.database),
            "history": HistoryView(self.content, database=self.database),
            "settings": SettingsView(self.content),
        }
        for view in self.views.values():
            view.grid(row=0, column=0, sticky="nsew")

        self.show_view("overview")
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def show_view(self, name: str) -> None:
        self.views[name].tkraise()
        self.sidebar.set_active(name)
        if name == "history":
            self.views["history"].refresh()
        if name == "overview":
            self.views["overview"].refresh_select_screen()

    def on_close(self) -> None:
        self.database.close()
        self.destroy()


def main() -> None:
    app = SmartSortApp()
    app.mainloop()


if __name__ == "__main__":
    main()
