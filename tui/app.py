# maps · cassette.help · MIT
"""
urwid TUI for felt.
Text-only — names, ages, timestamps. No photos.
Useful for terminal workflow integration.

Keybindings:
 1/2/3/4 — switch to likes / pings / matches / discovery tab
 Enter — expand selected item (show bio + desires)
 r — refresh current tab
 q / ESC — quit
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import urwid

from feeld.client import FeeldClient
from feeld.queries import (
    fetch_likes_received,
    fetch_pings_received,
    fetch_matches,
    fetch_discovery,
)

# -- Palette -----------------------------------------------------------------

PALETTE = [
    ("banner", "yellow", "dark gray"),
    ("header", "light cyan", "dark blue"),
    ("tab_active", "yellow,bold", ""),
    ("tab_inactive", "dark gray", ""),
    ("item_name", "yellow", ""),
    ("item_meta", "dark gray", ""),
    ("item_time", "brown", ""),
    ("item_bio", "light gray", ""),
    ("selected", "black", "yellow"),
    ("footer", "dark gray", ""),
    ("error", "light red", ""),
    ("loading", "dark gray", ""),
]

TABS = ["likes", "pings", "matches", "discovery"]


class FeeldTUI:
    def __init__(self):
        self.client = FeeldClient()
        self.active_tab = 0
        self.data = {tab: None for tab in TABS}

        self._build_ui()

    def _build_ui(self):
        self.tab_buttons = []
        for i, tab in enumerate(TABS):
            btn = urwid.Text(f" {tab} ", align="center")
            self.tab_buttons.append(btn)

        self.tabs_widget = urwid.Columns([
            urwid.AttrMap(btn, "tab_inactive") for btn in self.tab_buttons
        ])

        self.list_walker = urwid.SimpleFocusListWalker([
            urwid.Text(("loading", " loading..."))
        ])
        self.list_box = urwid.ListBox(self.list_walker)

        self.status_text = urwid.Text(
            ("footer", " felt | 1 likes 2 pings 3 matches 4 discovery r refresh q quit"),
            align="left",
        )

        self.frame = urwid.Frame(
            body=self.list_box,
            header=urwid.Pile([
                urwid.AttrMap(urwid.Text(" felt", align="left"), "banner"),
                self.tabs_widget,
            ]),
            footer=urwid.AttrMap(self.status_text, "footer"),
        )

    def _update_tabs(self):
        cols = []
        for i, tab in enumerate(TABS):
            style = "tab_active" if i == self.active_tab else "tab_inactive"
            marker = f"[{tab}]" if i == self.active_tab else f" {tab} "
            cols.append(urwid.AttrMap(urwid.Text(marker, align="center"), style))
        self.tabs_widget.contents = [(w, self.tabs_widget.options()) for w in cols]

    def _render_items(self, tab: str):
        items = self.data.get(tab)

        if items is None:
            return [urwid.Text(("loading", " loading..."))]

        if len(items) == 0:
            return [urwid.Text(("item_meta", " nothing here"))]

        rows = []
        for item in items:
            if tab == "matches":
                name = item.get("name", "—")
                msg = item.get("latestMessage", "")
                name_line = urwid.AttrMap(
                    urwid.Text(f" {name}"),
                    "item_name",
                    focus_map="selected",
                )
                meta_line = urwid.Text(
                    ("item_meta", f" {msg[:60] if msg else '—'}"),
                )
                rows.append(urwid.Pile([name_line, meta_line]))
            else:
                # likes, pings, discovery all return profile dicts
                name = item.get("imaginaryName", "—")
                age = item.get("age", "")
                gender = item.get("gender", "")
                desires = item.get("desires", [])
                distance = item.get("distance", {})
                km = distance.get("km", "")

                label = f"{name}" + (f", {age}" if age else "")
                meta = []
                if gender:
                    meta.append(gender)
                if desires:
                    meta.append(", ".join(desires[:2]))
                if km is not None:
                    meta.append(f"{km}km")

                name_line = urwid.AttrMap(
                    urwid.Text(f" {label}"),
                    "item_name",
                    focus_map="selected",
                )
                meta_text = " " + " · ".join(meta) if meta else " —"
                rows.append(urwid.Pile([
                    name_line,
                    urwid.Text(("item_meta", meta_text)),
                ]))
            rows.append(urwid.Divider("─"))

        return rows

    def _load_tab(self, tab: str):
        if self.data[tab] is not None:
            self._refresh_list()
            return

        self.list_walker[:] = [urwid.Text(("loading", f" loading {tab}..."))]

        try:
            if tab == "likes":
                self.data[tab] = fetch_likes_received(self.client)
            elif tab == "pings":
                self.data[tab] = fetch_pings_received(self.client)
            elif tab == "matches":
                self.data[tab] = fetch_matches(self.client)
            elif tab == "discovery":
                self.data[tab] = fetch_discovery(self.client)
        except Exception as e:
            self.data[tab] = []
            self.list_walker[:] = [urwid.Text(("error", f" error: {e}"))]
            return

        self._refresh_list()

    def _refresh_list(self):
        tab = TABS[self.active_tab]
        rows = self._render_items(tab)
        self.list_walker[:] = rows
        if rows:
            try:
                self.list_box.focus_position = 0
            except Exception:
                pass

    def _switch_tab(self, idx: int):
        self.active_tab = idx % len(TABS)
        self._update_tabs()
        self._load_tab(TABS[self.active_tab])

    def handle_input(self, key):
        if key in ("q", "Q", "esc"):
            raise urwid.ExitMainLoop()
        elif key == "1":
            self._switch_tab(0)
        elif key == "2":
            self._switch_tab(1)
        elif key == "3":
            self._switch_tab(2)
        elif key == "4":
            self._switch_tab(3)
        elif key == "r":
            tab = TABS[self.active_tab]
            self.data[tab] = None  # Force reload
            self._load_tab(tab)

    def run(self):
        self._update_tabs()
        self._load_tab(TABS[self.active_tab])
        loop = urwid.MainLoop(
            self.frame,
            PALETTE,
            unhandled_input=self.handle_input,
        )
        loop.run()


def run_tui():
    """Entry point called by CLI."""
    app = FeeldTUI()
    app.run()


if __name__ == "__main__":
    run_tui()
