"""Appearance and per-user Windows startup preference."""

from __future__ import annotations

import json
import sys
import winreg
from pathlib import Path

from workspace_launcher.storage import default_store_path

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_RUN_VALUE = "WorkspaceLauncher"
_APPEARANCES = {"dark", "light"}


def settings_path() -> Path:
    return default_store_path().parent / "settings.json"


def load_appearance(path: Path | None = None) -> str:
    file_path = path or settings_path()
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "dark"
    appearance = payload.get("appearance") if isinstance(payload, dict) else None
    if appearance in _APPEARANCES:
        return str(appearance)
    return "dark"


def save_appearance(appearance: str, path: Path | None = None) -> None:
    if appearance not in _APPEARANCES:
        raise ValueError(f"Unknown appearance: {appearance}")
    file_path = path or settings_path()
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        json.dumps({"appearance": appearance}, indent=2),
        encoding="utf-8",
    )


def startup_command() -> str:
    return f'"{sys.executable}" -m workspace_launcher'


def launch_at_startup() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as key:
            winreg.QueryValueEx(key, _RUN_VALUE)
            return True
    except OSError:
        return False


def set_launch_at_startup(enabled: bool) -> None:
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        _RUN_KEY,
        0,
        winreg.KEY_SET_VALUE,
    ) as key:
        if enabled:
            winreg.SetValueEx(key, _RUN_VALUE, 0, winreg.REG_SZ, startup_command())
            return
        try:
            winreg.DeleteValue(key, _RUN_VALUE)
        except OSError:
            return
