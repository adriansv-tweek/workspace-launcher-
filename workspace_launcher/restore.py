"""Restore a saved workspace onto the current desktop."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from workspace_launcher.desktop import (
    launch_executable,
    list_displays,
    list_windows,
    move_window,
)
from workspace_launcher.matching import (
    match_display,
    match_windows,
    placement_on_display,
)
from workspace_launcher.models import LiveWindow, RestoreItem, WindowSnapshot, Workspace

logger = logging.getLogger("workspace_launcher.restore")

_LAUNCH_TIMEOUT_SECONDS = 8.0
_POLL_SECONDS = 0.4


def restore_workspace(workspace: Workspace) -> list[RestoreItem]:
    logger.info('Restoring workspace "%s"', workspace.name)
    current_displays = list_displays()
    live = list_windows()
    known = {window.hwnd for window in live}
    pairs = match_windows(workspace.windows, live)
    results: list[RestoreItem] = []
    launched: set[str] = set()

    for saved, matched in pairs:
        if matched is not None:
            results.append(_place(saved, matched, workspace, current_displays))
            continue
        results.append(
            _launch_and_place(saved, workspace, current_displays, known, launched)
        )
    return results


def _place(
    saved: WindowSnapshot,
    live: LiveWindow,
    workspace: Workspace,
    current_displays: list,
) -> RestoreItem:
    target, how = match_display(saved, workspace.displays, current_displays)
    if target is None:
        logger.warning("No display available for %s", saved.label)
        return RestoreItem(saved.label, False, "No display is available.")
    x, y, width, height = placement_on_display(saved, target)
    try:
        move_window(live.hwnd, x, y, width, height, saved.show_state)
    except OSError as exc:
        logger.warning("Could not move %s: %s", saved.label, exc)
        return RestoreItem(saved.label, False, str(exc))
    logger.info(
        "Matched %s and moved it to %s (%s)",
        saved.label,
        target.friendly_name or target.device_name,
        how,
    )
    return RestoreItem(
        saved.label, True, f"Moved to {target.friendly_name or target.device_name}."
    )


def _launch_and_place(
    saved: WindowSnapshot,
    workspace: Workspace,
    current_displays: list,
    known: set[int],
    launched: set[str],
) -> RestoreItem:
    key = saved.exe_path.casefold()
    if not saved.exe_path:
        logger.warning("No executable path for %s", saved.label)
        return RestoreItem(saved.label, False, "No executable path was saved.")
    if key in launched:
        logger.warning("No extra window appeared for %s", saved.label)
        return RestoreItem(
            saved.label, False, "The application did not open another window."
        )
    if not Path(saved.exe_path).is_file():
        logger.warning("Executable missing for %s: %s", saved.label, saved.exe_path)
        return RestoreItem(saved.label, False, "Executable no longer exists.")

    logger.info("Starting %s", saved.label)
    launched.add(key)
    try:
        launch_executable(saved.exe_path)
    except OSError as exc:
        logger.warning("Could not start %s: %s", saved.label, exc)
        return RestoreItem(saved.label, False, str(exc))

    logger.info("Waiting for %s window", saved.label)
    appeared = _wait_for_new_window(saved, known)
    if appeared is None:
        return RestoreItem(saved.label, False, "The window did not appear in time.")
    known.add(appeared.hwnd)
    return _place(saved, appeared, workspace, current_displays)


def _wait_for_new_window(saved: WindowSnapshot, known: set[int]) -> LiveWindow | None:
    deadline = time.monotonic() + _LAUNCH_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        fresh = [window for window in list_windows() if window.hwnd not in known]
        pairs = match_windows([saved], fresh)
        if pairs and pairs[0][1] is not None:
            return pairs[0][1]
        time.sleep(_POLL_SECONDS)
    logger.warning("Timed out waiting for %s", saved.label)
    return None
