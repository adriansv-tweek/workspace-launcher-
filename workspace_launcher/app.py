"""Application entry point."""

from __future__ import annotations

import ctypes
import logging

from workspace_launcher.desktop import enable_dpi_awareness
from workspace_launcher.logging_config import configure_logging

logger = logging.getLogger("workspace_launcher")

_ERROR_ALREADY_EXISTS = 183


def main() -> int:
    """Start the application and return a process exit code."""
    configure_logging()
    if _already_running():
        logger.error("Workspace Launcher is already running.")
        _tell_user("Workspace Launcher is already running.")
        return 1
    enable_dpi_awareness()
    logger.info("Workspace Launcher started.")
    try:
        from workspace_launcher.ui import run_ui

        return run_ui()
    except Exception:
        logger.exception("Workspace Launcher failed to start.")
        return 1


def _already_running() -> bool:
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateMutexW(None, False, "Local\\WorkspaceLauncher.SingleInstance")
    return kernel32.GetLastError() == _ERROR_ALREADY_EXISTS


def _tell_user(message: str) -> None:
    ctypes.windll.user32.MessageBoxW(None, message, "Workspace Launcher", 0x40)


if __name__ == "__main__":
    raise SystemExit(main())
