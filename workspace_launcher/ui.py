"""Minimal dark window for capturing and restoring workspaces."""

from __future__ import annotations

import logging
import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox

from workspace_launcher.hotkeys import HotkeyListener
from workspace_launcher.service import StorageError, WorkspaceService
from workspace_launcher.settings import (
    launch_at_startup,
    load_appearance,
    save_appearance,
    set_launch_at_startup,
)

logger = logging.getLogger("workspace_launcher.ui")

_FONT = "Segoe UI"
_DWMWA_USE_IMMERSIVE_DARK_MODE = 20


@dataclass(frozen=True)
class Theme:
    bg: str
    fg: str
    muted: str
    hover: str
    field: str


THEMES = {
    "dark": Theme(
        bg="#141414",
        fg="#f2f2f2",
        muted="#8a8a8a",
        hover="#222222",
        field="#1c1c1c",
    ),
    "light": Theme(
        bg="#f3f3f3",
        fg="#1a1a1a",
        muted="#6a6a6a",
        hover="#e6e6e6",
        field="#ffffff",
    ),
}


def run_ui() -> int:
    root = tk.Tk()
    root.title("Workspace Launcher")
    root.geometry("440x640")
    root.minsize(380, 520)
    AppWindow(root)
    root.mainloop()
    return 0


class Mark(tk.Canvas):
    """A small geometric icon drawn to match the current theme."""

    def __init__(self, parent: tk.Misc, kind: str, size: int, command=None) -> None:
        super().__init__(
            parent,
            width=size,
            height=size,
            highlightthickness=0,
            bd=0,
        )
        self.kind = kind
        self.size = size
        self._role = "icon"
        if command is not None:
            self.bind("<Button-1>", lambda _event: command())

    def redraw(self, color: str, background: str) -> None:
        self.configure(bg=background)
        self.delete("all")
        _draw_mark(self, self.kind, self.size, color)


class SelectMark(tk.Canvas):
    def __init__(self, parent: tk.Misc, selected) -> None:
        super().__init__(parent, width=18, height=18, highlightthickness=0, bd=0)
        self._selected = selected
        self._role = "select"

    def redraw(self, theme: Theme) -> None:
        self.configure(bg=theme.bg)
        self.delete("all")
        if self._selected():
            self.create_oval(3, 3, 15, 15, fill=theme.fg, outline=theme.fg)
        else:
            self.create_oval(3, 3, 15, 15, outline=theme.muted, width=1)


class Switch(tk.Canvas):
    def __init__(self, parent: tk.Misc, enabled) -> None:
        super().__init__(parent, width=40, height=22, highlightthickness=0, bd=0)
        self._enabled = enabled
        self._role = "switch"

    def redraw(self, theme: Theme) -> None:
        self.configure(bg=theme.bg)
        self.delete("all")
        on = bool(self._enabled())
        track = theme.fg if on else theme.hover
        knob = theme.bg if on else theme.muted
        self.create_oval(1, 2, 21, 20, fill=track, outline=track)
        self.create_oval(19, 2, 39, 20, fill=track, outline=track)
        self.create_rectangle(11, 2, 29, 20, fill=track, outline=track)
        knob_x = 20 if on else 2
        self.create_oval(knob_x, 4, knob_x + 16, 18, fill=knob, outline=knob)


class AppWindow:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.service = WorkspaceService()
        self.appearance = load_appearance()
        self.theme = THEMES[self.appearance]
        self._return_to = "home"
        self.home = tk.Frame(root)
        self.workspaces = tk.Frame(root)
        self.settings = tk.Frame(root)
        self.surface = tk.Frame(root)
        self._build_home()
        self._build_workspaces()
        self._build_settings()
        self._show_home()
        self._apply_theme()
        self.hotkeys = HotkeyListener(lambda _slot: None)
        self.hotkeys.start()
        self._refresh_hotkeys()
        self.root.after(50, self._drain_hotkeys)
        self.root.protocol("WM_DELETE_WINDOW", self._close)

    def _build_home(self) -> None:
        header = tk.Frame(self.home)
        header.pack(fill="x", padx=12, pady=(12, 0))
        self._icon(header, "menu", self._show_workspaces).pack(side="left")
        self._icon(header, "gear", self._open_settings).pack(side="right")
        body = tk.Frame(self.home)
        body.pack(fill="both", expand=True)
        tk.Frame(body).pack(expand=True)
        plus = Mark(body, "plus", 96, self._capture)
        plus.pack()
        caption = tk.Label(
            body,
            text="Capture current\nworkspace",
            font=(_FONT, 12),
            justify="center",
        )
        caption.pack(pady=(18, 0))
        tk.Frame(body).pack(expand=True)
        self._mark(header, "bg")
        self._mark(body, "bg")
        self._mark(caption, "muted")

    def _build_workspaces(self) -> None:
        header = tk.Frame(self.workspaces)
        header.pack(fill="x", padx=12, pady=(12, 4))
        self._icon(header, "back", self._show_home).pack(side="left")
        title = tk.Label(header, text="My Workspaces", font=(_FONT, 15))
        title.pack(side="left", padx=6)
        self._icon(header, "gear", self._open_settings).pack(side="right")
        self.list_host = tk.Frame(self.workspaces)
        self.list_host.pack(fill="both", expand=True, padx=8, pady=(8, 16))
        self._mark(header, "bg")
        self._mark(title, "fg")
        self._mark(self.list_host, "bg")

    def _build_settings(self) -> None:
        header = tk.Frame(self.settings)
        header.pack(fill="x", padx=12, pady=(12, 4))
        self._icon(header, "back", self._back_from_settings).pack(side="left")
        title = tk.Label(header, text="Settings", font=(_FONT, 15))
        title.pack(side="left", padx=6)
        body = tk.Frame(self.settings)
        body.pack(fill="both", expand=True, padx=28, pady=20)
        appearance = tk.Label(body, text="Appearance", font=(_FONT, 11))
        appearance.pack(anchor="w", pady=(8, 10))
        self._choice_row(body, "Dark", "dark").pack(fill="x", pady=4)
        self._choice_row(body, "Light", "light").pack(fill="x", pady=4)
        startup_label = tk.Label(body, text="Startup", font=(_FONT, 11))
        startup_label.pack(anchor="w", pady=(28, 10))
        self.startup_var = tk.BooleanVar(value=launch_at_startup())
        startup = tk.Frame(body)
        startup.pack(fill="x", pady=4)
        startup_text = tk.Label(
            startup, text="Launch at Windows startup", font=(_FONT, 12), anchor="w"
        )
        startup_text.pack(side="left", fill="x", expand=True)
        self.startup_switch = Switch(startup, lambda: self.startup_var.get())
        self.startup_switch.pack(side="right")
        for widget in (startup, startup_text, self.startup_switch):
            widget.bind("<Button-1>", lambda _event: self._toggle_startup())
        self._mark(header, "bg")
        self._mark(title, "fg")
        self._mark(body, "bg")
        self._mark(appearance, "muted")
        self._mark(startup_label, "muted")
        self._mark(startup, "bg")
        self._mark(startup_text, "fg")

    def _icon(self, parent: tk.Misc, kind: str, command) -> Mark:
        return Mark(parent, kind, 36, command)

    def _choice_row(self, parent: tk.Misc, text: str, value: str) -> tk.Frame:
        row = tk.Frame(parent)
        mark = SelectMark(row, lambda value=value: self.appearance == value)
        mark.pack(side="left", padx=(0, 12))
        label = tk.Label(row, text=text, font=(_FONT, 12), anchor="w")
        label.pack(side="left", fill="x", expand=True, ipady=6)
        self._mark(row, "bg")
        self._mark(label, "fg")
        for widget in (row, label, mark):
            widget.bind(
                "<Button-1>",
                lambda _event, selected=value: self._select_appearance(selected),
            )
        return row

    def _show_home(self) -> None:
        self._hide_surface()
        self.workspaces.pack_forget()
        self.settings.pack_forget()
        self.home.pack(fill="both", expand=True)
        self._return_to = "home"

    def _show_workspaces(self) -> None:
        self._hide_surface()
        self.home.pack_forget()
        self.settings.pack_forget()
        self._reload_list()
        self.workspaces.pack(fill="both", expand=True)
        self._return_to = "workspaces"

    def _open_settings(self) -> None:
        self._hide_surface()
        self.home.pack_forget()
        self.workspaces.pack_forget()
        self.startup_var.set(launch_at_startup())
        self.settings.pack(fill="both", expand=True)
        self._paint(self.settings)

    def _back_from_settings(self) -> None:
        if self._return_to == "workspaces":
            self._show_workspaces()
        else:
            self._show_home()

    def _capture(self) -> None:
        name = self._ask_text("Capture workspace", "Workspace name")
        if not name:
            return
        try:
            self.service.capture(name)
        except StorageError as exc:
            messagebox.showerror("Could not save", str(exc), parent=self.root)
            return
        self._refresh_hotkeys()

    def _reload_list(self) -> None:
        for child in self.list_host.winfo_children():
            child.destroy()
        try:
            workspaces = self.service.list_workspaces()
        except StorageError as exc:
            label = tk.Label(
                self.list_host, text=str(exc), wraplength=360, justify="left"
            )
            label.pack(anchor="w", padx=16, pady=12)
            self._mark(label, "muted")
            self._paint(label)
            return
        self._refresh_hotkeys()
        if not workspaces:
            label = tk.Label(self.list_host, text="No workspaces yet.")
            label.pack(anchor="w", padx=16, pady=12)
            self._mark(label, "muted")
            self._paint(label)
            return
        for workspace in workspaces:
            self._add_workspace_row(workspace)

    def _add_workspace_row(self, workspace) -> None:
        row = tk.Frame(self.list_host)
        row.pack(fill="x", pady=2)
        row.grid_columnconfigure(0, weight=1)
        name = tk.Label(row, text=workspace.name, font=(_FONT, 13), anchor="w")
        name.grid(row=0, column=0, sticky="ew", padx=(16, 8), pady=14)
        shortcut = tk.Label(
            row,
            text=workspace.hotkey_label,
            font=(_FONT, 11),
            anchor="e",
        )
        shortcut.grid(row=0, column=1, sticky="e", padx=(8, 4))
        more = Mark(
            row,
            "more",
            32,
            lambda workspace_id=workspace.id: self._open_menu(workspace_id, more),
        )
        more.grid(row=0, column=2, sticky="e", padx=(0, 8))
        self._mark(row, "bg")
        self._mark(name, "fg")
        self._mark(shortcut, "muted")
        targets = (row, name, shortcut)
        for widget in targets:
            widget.bind(
                "<Button-1>",
                lambda _event, workspace_id=workspace.id: self._restore(workspace_id),
            )
        self._bind_row_hover(row, targets, more)
        self._paint(row)

    def _bind_row_hover(self, row: tk.Frame, targets: tuple, more: Mark) -> None:
        def enter(_event) -> None:
            self._paint_row(row, targets, more, self.theme.hover)

        def leave(event) -> None:
            pointer = row.winfo_containing(event.x_root, event.y_root)
            if pointer is not None and (
                pointer is row or str(pointer).startswith(str(row))
            ):
                return
            self._paint_row(row, targets, more, self.theme.bg)

        for widget in (*targets, more):
            widget.bind("<Enter>", enter, add="+")
            widget.bind("<Leave>", leave, add="+")

    def _paint_row(self, row, targets, more: Mark, background: str) -> None:
        row.configure(bg=background)
        for widget in targets:
            if widget is row:
                continue
            role = getattr(widget, "_role", "fg")
            color = self.theme.muted if role == "muted" else self.theme.fg
            widget.configure(bg=background, fg=color)
        more.redraw(self.theme.fg, background)

    def _open_menu(self, workspace_id: str, anchor: tk.Widget) -> None:
        if getattr(self, "_menu", None) is not None:
            self._close_menu()
        menu = tk.Toplevel(self.root)
        menu.overrideredirect(True)
        menu.configure(bg=self.theme.field)
        self._menu = menu
        items = (
            ("Open workspace", lambda: self._restore(workspace_id)),
            ("Update snapshot", lambda: self._update(workspace_id)),
            ("Rename", lambda: self._rename(workspace_id)),
            ("Change shortcut", None),
            ("Delete", lambda: self._delete(workspace_id)),
        )
        for label, command in items:
            item = tk.Label(
                menu,
                text=label,
                font=(_FONT, 11),
                bg=self.theme.field,
                fg=self.theme.muted if command is None else self.theme.fg,
                anchor="w",
                padx=16,
                pady=8,
            )
            item.pack(fill="x")
            if command is None:
                continue

            def invoke(action=command, row=item) -> None:
                self._close_menu()
                action()

            def hover_on(_event, row=item) -> None:
                row.configure(bg=self.theme.hover)

            def hover_off(_event, row=item) -> None:
                row.configure(bg=self.theme.field)

            item.bind("<Button-1>", lambda _event, call=invoke: call())
            item.bind("<Enter>", hover_on)
            item.bind("<Leave>", hover_off)
        menu.update_idletasks()
        x = anchor.winfo_rootx() + anchor.winfo_width() - menu.winfo_width()
        y = anchor.winfo_rooty() + anchor.winfo_height() - 4
        menu.geometry(f"+{x}+{y}")
        menu.bind("<Escape>", lambda _event: self._close_menu())
        menu.focus_set()

        def dismiss(event) -> None:
            if not menu.winfo_exists():
                return
            if str(event.widget).startswith(str(menu)):
                return
            self._close_menu()

        self._menu_bind = self.root.bind("<Button-1>", dismiss, add="+")

    def _close_menu(self) -> None:
        bind_id = getattr(self, "_menu_bind", None)
        if bind_id:
            self.root.unbind("<Button-1>", bind_id)
            self._menu_bind = None
        menu = getattr(self, "_menu", None)
        self._menu = None
        if menu is not None and menu.winfo_exists():
            menu.destroy()

    def _restore(self, workspace_id: str) -> None:
        self._close_menu()
        try:
            results = self.service.restore(workspace_id)
        except StorageError as exc:
            messagebox.showerror("Could not restore", str(exc), parent=self.root)
            return
        failed = [item for item in results if not item.ok]
        if failed:
            logger.warning("Restore finished with %d problem(s).", len(failed))

    def _update(self, workspace_id: str) -> None:
        self._close_menu()
        if not self._ask_confirm(
            "Update workspace",
            "Replace the saved windows with the current layout?",
            "Update",
        ):
            return
        try:
            self.service.update_snapshot(workspace_id)
        except StorageError as exc:
            messagebox.showerror("Could not update", str(exc), parent=self.root)
            return
        self._reload_list()

    def _rename(self, workspace_id: str) -> None:
        self._close_menu()
        name = self._ask_text("Rename workspace", "New name")
        if not name:
            return
        try:
            self.service.rename(workspace_id, name)
        except StorageError as exc:
            messagebox.showerror("Could not rename", str(exc), parent=self.root)
            return
        self._reload_list()

    def _delete(self, workspace_id: str) -> None:
        self._close_menu()
        if not self._ask_confirm(
            "Delete workspace", "Delete this workspace?", "Delete"
        ):
            return
        try:
            self.service.delete(workspace_id)
        except StorageError as exc:
            messagebox.showerror("Could not delete", str(exc), parent=self.root)
            return
        self._reload_list()

    def _ask_text(self, title: str, label: str) -> str | None:
        return self._ask(title, label, accept="Save", entry=True)

    def _ask_confirm(self, title: str, message: str, accept: str) -> bool:
        return self._ask(title, message, accept=accept, entry=False) is not None

    def _ask(self, title: str, message: str, *, accept: str, entry: bool) -> str | None:
        self._close_menu()
        self._clear(self.surface)
        result: dict[str, str | None] = {"value": None}
        done = tk.BooleanVar(value=False)
        heading = tk.Label(self.surface, text=title, font=(_FONT, 16))
        heading.pack(anchor="w", padx=32, pady=(72, 8))
        prompt = tk.Label(self.surface, text=message, font=(_FONT, 12))
        prompt.pack(anchor="w", padx=32)
        field = None
        if entry:
            field = tk.Entry(
                self.surface,
                font=(_FONT, 13),
                relief="flat",
                highlightthickness=0,
                bd=0,
            )
            field.pack(fill="x", padx=32, pady=(18, 0), ipady=8)
            field.focus_set()
            self._mark(field, "field")
        actions = tk.Frame(self.surface)
        actions.pack(anchor="e", padx=32, pady=28)
        cancel = tk.Label(actions, text="Cancel", font=(_FONT, 12), padx=8)
        save = tk.Label(actions, text=accept, font=(_FONT, 12), padx=8)
        cancel.pack(side="left", padx=(0, 16))
        save.pack(side="left")
        self._mark(self.surface, "bg")
        self._mark(heading, "fg")
        self._mark(prompt, "muted")
        self._mark(actions, "bg")
        self._mark(cancel, "muted")
        self._mark(save, "fg")

        def accept_value(_event=None) -> None:
            result["value"] = field.get() if field is not None else ""
            done.set(True)

        def cancel_value(_event=None) -> None:
            done.set(True)

        save.bind("<Button-1>", accept_value)
        cancel.bind("<Button-1>", cancel_value)
        self.surface.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.surface.lift()
        self._paint(self.surface)
        self._titlebar(self.root, self.appearance == "dark")
        if field is not None:
            field.focus_set()
            field.bind("<Return>", accept_value)
        self.surface.bind("<Escape>", cancel_value)
        self.root.bind("<Escape>", cancel_value)
        self.root.wait_variable(done)
        self.root.unbind("<Escape>")
        self._hide_surface()
        return result["value"]

    def _hide_surface(self) -> None:
        if self.surface.winfo_ismapped():
            self.surface.place_forget()

    def _clear(self, widget: tk.Widget) -> None:
        for child in widget.winfo_children():
            child.destroy()

    def _select_appearance(self, appearance: str) -> None:
        if appearance not in THEMES or appearance == self.appearance:
            return
        save_appearance(appearance)
        self.appearance = appearance
        self.theme = THEMES[appearance]
        self._apply_theme()

    def _toggle_startup(self) -> None:
        self.startup_var.set(not self.startup_var.get())
        try:
            set_launch_at_startup(bool(self.startup_var.get()))
        except OSError:
            logger.exception("Could not update the Windows startup entry.")
            self.startup_var.set(launch_at_startup())
            messagebox.showerror(
                "Startup",
                "Could not change the Windows startup setting.",
                parent=self.root,
            )
        self.startup_switch.redraw(self.theme)

    def _refresh_hotkeys(self) -> None:
        try:
            slots = {
                item.hotkey_slot
                for item in self.service.list_workspaces()
                if item.hotkey_slot
            }
        except StorageError:
            logger.warning("Could not load workspaces for hotkeys.")
            return
        self.hotkeys.set_slots(slots)

    def _drain_hotkeys(self) -> None:
        seen: set[int] = set()
        while True:
            try:
                slot = self.hotkeys.events.get_nowait()
            except Exception:
                break
            if slot not in seen:
                seen.add(slot)
                self._on_hotkey(slot)
        if self.root.winfo_exists():
            self.root.after(50, self._drain_hotkeys)

    def _on_hotkey(self, slot: int) -> None:
        try:
            results = self.service.restore_slot(slot)
        except StorageError as exc:
            logger.error("Hotkey restore failed: %s", exc)
            return
        if results is None:
            return
        failed = [item for item in results if not item.ok]
        if failed:
            logger.warning("Hotkey restore finished with %d problem(s).", len(failed))

    def _apply_theme(self) -> None:
        self.root.configure(bg=self.theme.bg)
        self._paint(self.home)
        self._paint(self.workspaces)
        self._paint(self.settings)
        if self.surface.winfo_exists():
            self._paint(self.surface)
        self._titlebar(self.root, self.appearance == "dark")

    def _paint(self, widget: tk.Misc) -> None:
        role = getattr(widget, "_role", "bg")
        if role == "icon":
            widget.redraw(self.theme.fg, self.theme.bg)
        elif role == "select":
            widget.redraw(self.theme)
        elif role == "switch":
            widget.redraw(self.theme)
        elif role == "field":
            widget.configure(
                bg=self.theme.field,
                fg=self.theme.fg,
                insertbackground=self.theme.fg,
                selectbackground=self.theme.hover,
                selectforeground=self.theme.fg,
            )
        elif role == "muted":
            widget.configure(bg=self.theme.bg, fg=self.theme.muted)
        elif role == "fg":
            widget.configure(bg=self.theme.bg, fg=self.theme.fg)
        else:
            try:
                widget.configure(bg=self.theme.bg)
            except tk.TclError:
                return
        for child in widget.winfo_children():
            self._paint(child)

    def _titlebar(self, window: tk.Misc, dark: bool) -> None:
        window.update_idletasks()
        try:
            import ctypes

            hwnd = ctypes.c_void_p(int(window.winfo_id()))
            value = ctypes.c_int(1 if dark else 0)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                _DWMWA_USE_IMMERSIVE_DARK_MODE,
                ctypes.byref(value),
                ctypes.sizeof(value),
            )
        except Exception:
            logger.debug("Could not set the window title bar color.", exc_info=True)

    def _close(self) -> None:
        self._close_menu()
        self.hotkeys.stop()
        self.root.destroy()

    @staticmethod
    def _mark(widget: tk.Widget, role: str) -> None:
        widget._role = role  # type: ignore[attr-defined]


def _draw_mark(canvas: tk.Canvas, kind: str, size: int, color: str) -> None:
    center = size / 2
    if kind == "menu":
        for offset in (-5, 0, 5):
            canvas.create_line(
                center - 7,
                center + offset,
                center + 7,
                center + offset,
                fill=color,
                width=1.4,
                capstyle=tk.ROUND,
            )
    elif kind == "back":
        canvas.create_line(
            center + 4,
            center - 6,
            center - 4,
            center,
            center + 4,
            center + 6,
            fill=color,
            width=1.4,
            capstyle=tk.ROUND,
            joinstyle=tk.ROUND,
        )
    elif kind == "gear":
        _draw_gear(canvas, center, color)
    elif kind == "more":
        for offset in (-6, 0, 6):
            canvas.create_oval(
                center - 1.4,
                center + offset - 1.4,
                center + 1.4,
                center + offset + 1.4,
                fill=color,
                outline=color,
            )
    elif kind == "plus":
        arm = size * 0.16
        canvas.create_line(
            center - arm,
            center,
            center + arm,
            center,
            fill=color,
            width=1.5,
            capstyle=tk.ROUND,
        )
        canvas.create_line(
            center,
            center - arm,
            center,
            center + arm,
            fill=color,
            width=1.5,
            capstyle=tk.ROUND,
        )


def _draw_gear(canvas: tk.Canvas, center: float, color: str) -> None:
    import math

    for step in range(8):
        angle = step * math.pi / 4
        canvas.create_line(
            center + math.cos(angle) * 5.4,
            center + math.sin(angle) * 5.4,
            center + math.cos(angle) * 7.6,
            center + math.sin(angle) * 7.6,
            fill=color,
            width=2.2,
            capstyle=tk.ROUND,
        )
    canvas.create_oval(
        center - 5.2,
        center - 5.2,
        center + 5.2,
        center + 5.2,
        outline=color,
        width=1.4,
    )
    canvas.create_oval(
        center - 1.8,
        center - 1.8,
        center + 1.8,
        center + 1.8,
        outline=color,
        width=1.2,
    )
