"""Capture the current desktop as a workspace snapshot."""

from __future__ import annotations

import logging

from workspace_launcher.desktop import list_displays, list_windows
from workspace_launcher.models import DisplaySnapshot, LiveWindow, WindowSnapshot

logger = logging.getLogger("workspace_launcher.capture")


def capture_workspace() -> tuple[list[DisplaySnapshot], list[WindowSnapshot]]:
    displays = list_displays()
    windows = [_snapshot(window) for window in list_windows()]
    logger.info("Found %d displays", len(displays))
    logger.info("Found %d relevant windows", len(windows))
    for window in windows:
        logger.info(
            "Captured %s (%s, %s)",
            window.exe_name or window.label,
            window.show_state,
            window.monitor_device_name or "unknown display",
        )
        logger.debug("Window title: %s", window.title)
    return displays, windows


def _snapshot(window: LiveWindow) -> WindowSnapshot:
    return WindowSnapshot(
        exe_path=window.exe_path,
        exe_name=window.exe_name,
        window_class=window.window_class,
        title=window.title,
        monitor_device_id=window.monitor_device_id,
        monitor_device_name=window.monitor_device_name,
        offset_x=window.offset_x,
        offset_y=window.offset_y,
        width=window.width,
        height=window.height,
        show_state=window.show_state,
    )
