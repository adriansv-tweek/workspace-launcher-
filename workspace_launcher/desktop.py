"""Windows display, window, and process helpers.

Only normal application windows are returned. The shell, tool windows, cloaked
windows, and this process are left out.
"""

from __future__ import annotations

import ctypes
import logging
import os
import subprocess
import sys
from ctypes import wintypes
from pathlib import Path

import win32api
import win32con
import win32gui
import win32process

from workspace_launcher.models import DisplaySnapshot, LiveWindow

logger = logging.getLogger("workspace_launcher.desktop")

# Hosts and shell UI that are not useful to launch or capture.
_SKIP_EXES = {
    "textinputhost.exe",
    "searchhost.exe",
    "startmenuexperiencehost.exe",
    "shellexperiencehost.exe",
    "lockapp.exe",
}
_SKIP_CLASSES = {
    "Progman",
    "Shell_TrayWnd",
    "Shell_SecondaryTrayWnd",
}
# Launching the frame host starts the wrong process for a Store app.
_UNLAUNCHABLE_EXES = _SKIP_EXES | {"applicationframehost.exe"}

_DWMWA_CLOAKED = 14
_SW_SHOWMAXIMIZED = 3
_SW_SHOWMINIMIZED = 2
_SW_SHOWMINNOACTIVE = 7


def enable_dpi_awareness() -> None:
    """Use physical pixels so saved positions match the real monitors."""
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        logger.warning("Could not enable per-monitor DPI awareness.")


def list_displays() -> list[DisplaySnapshot]:
    displays: list[DisplaySnapshot] = []
    for handle, _hdc, _rect in win32api.EnumDisplayMonitors():
        info = win32api.GetMonitorInfo(handle)
        left, top, right, bottom = info["Monitor"]
        device_name = str(info["Device"])
        device_id, friendly = _display_identity(device_name)
        displays.append(
            DisplaySnapshot(
                device_name=device_name,
                device_id=device_id,
                friendly_name=friendly,
                left=int(left),
                top=int(top),
                width=int(right - left),
                height=int(bottom - top),
                is_primary=bool(info["Flags"] & 1),
            )
        )
    return displays


def list_windows() -> list[LiveWindow]:
    displays = list_displays()
    own_pid = os.getpid()
    found: list[LiveWindow] = []

    def visit(hwnd: int, _param: object) -> bool:
        window = _describe_window(hwnd, own_pid, displays)
        if window is not None:
            found.append(window)
        return True

    win32gui.EnumWindows(visit, None)
    return found


def move_window(
    hwnd: int, x: int, y: int, width: int, height: int, show_state: str
) -> None:
    if not win32gui.IsWindow(hwnd):
        raise OSError("Window no longer exists.")
    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    flags = win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE
    try:
        # pywin32 returns None on success and raises on failure.
        win32gui.SetWindowPos(hwnd, 0, x, y, width, height, flags)
    except Exception as exc:
        raise OSError(f"Could not move window {hwnd}.") from exc
    if show_state == "maximized":
        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
    elif show_state == "minimized":
        win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)


def launch_executable(exe_path: str) -> None:
    """Start an application by its executable path. No shell is used."""
    path = Path(exe_path)
    if path.name.casefold() in _UNLAUNCHABLE_EXES:
        raise OSError(f"{path.name} cannot be launched directly.")
    if not path.is_file():
        raise OSError(f"Executable not found: {exe_path}")
    subprocess.Popen(
        [str(path)],
        cwd=str(path.parent),
        close_fds=True,
    )


def _display_identity(device_name: str) -> tuple[str, str]:
    try:
        device = win32api.EnumDisplayDevices(device_name, 0)
    except Exception:
        logger.debug("No display device details for %s", device_name)
        return "", device_name
    return str(device.DeviceID or ""), str(device.DeviceString or device_name)


def _describe_window(
    hwnd: int,
    own_pid: int,
    displays: list[DisplaySnapshot],
) -> LiveWindow | None:
    try:
        if not win32gui.IsWindowVisible(hwnd) or _is_cloaked(hwnd):
            return None
        title = win32gui.GetWindowText(hwnd).strip()
        if not title:
            return None
        window_class = win32gui.GetClassName(hwnd)
        if window_class in _SKIP_CLASSES:
            return None
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        owner = win32gui.GetWindow(hwnd, win32con.GW_OWNER)
        tool = bool(style & win32con.WS_EX_TOOLWINDOW)
        app = bool(style & win32con.WS_EX_APPWINDOW)
        if tool and not app:
            return None
        if owner and not app:
            return None
        _thread, pid = win32process.GetWindowThreadProcessId(hwnd)
        exe_path = _process_path(pid)
        if _is_workspace_launcher(pid, exe_path, title, own_pid):
            logger.debug("Skipped Workspace Launcher window hwnd %s.", hwnd)
            return None
        exe_name = Path(exe_path).name if exe_path else ""
        if exe_name.casefold() in _SKIP_EXES:
            return None
        show_state, left, top, width, height = _bounds(hwnd)
        if show_state != "minimized" and (width < 40 or height < 40):
            return None
        monitor = _monitor_for_window(hwnd, displays)
    except Exception:
        logger.debug("Skipped hwnd %s", hwnd, exc_info=True)
        return None

    monitor_id = monitor.device_id if monitor else ""
    monitor_name = monitor.device_name if monitor else ""
    origin_x = monitor.left if monitor else 0
    origin_y = monitor.top if monitor else 0
    return LiveWindow(
        hwnd=int(hwnd),
        exe_path=exe_path,
        exe_name=exe_name,
        window_class=window_class,
        title=title,
        monitor_device_id=monitor_id,
        monitor_device_name=monitor_name,
        offset_x=left - origin_x,
        offset_y=top - origin_y,
        width=width,
        height=height,
        show_state=show_state,
    )


def _bounds(hwnd: int) -> tuple[str, int, int, int, int]:
    placement = win32gui.GetWindowPlacement(hwnd)
    show_cmd = int(placement[1])
    if show_cmd in {_SW_SHOWMINIMIZED, _SW_SHOWMINNOACTIVE} or win32gui.IsIconic(hwnd):
        show_state = "minimized"
        left, top, right, bottom = placement[4]
    elif show_cmd == _SW_SHOWMAXIMIZED:
        show_state = "maximized"
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    else:
        show_state = "normal"
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    return show_state, int(left), int(top), int(right - left), int(bottom - top)


def _monitor_for_window(
    hwnd: int, displays: list[DisplaySnapshot]
) -> DisplaySnapshot | None:
    try:
        handle = win32api.MonitorFromWindow(hwnd, win32con.MONITOR_DEFAULTTONEAREST)
        info = win32api.GetMonitorInfo(handle)
        device_name = str(info["Device"])
    except Exception:
        return _primary_display(displays)
    for display in displays:
        if display.device_name == device_name:
            return display
    return _primary_display(displays)


def _primary_display(displays: list[DisplaySnapshot]) -> DisplaySnapshot | None:
    for display in displays:
        if display.is_primary:
            return display
    return displays[0] if displays else None


def _is_workspace_launcher(pid: int, exe_path: str, title: str, own_pid: int) -> bool:
    """Exclude this app by process id and by its own executable path.

    The path check is paired with the window title so other programs that share
    the same Python executable are still captured.
    """
    if pid == own_pid:
        return True
    if not exe_path:
        return False
    same_image = os.path.normcase(os.path.abspath(exe_path)) == os.path.normcase(
        os.path.abspath(sys.executable)
    )
    exe_name = Path(exe_path).name.casefold()
    named_launcher = title == "Workspace Launcher" and exe_name in {
        "python.exe",
        "pythonw.exe",
    }
    return (same_image and title == "Workspace Launcher") or named_launcher


def _process_path(pid: int) -> str:
    handle = None
    try:
        handle = win32api.OpenProcess(
            win32con.PROCESS_QUERY_LIMITED_INFORMATION, False, pid
        )
        return str(win32process.GetModuleFileNameEx(handle, 0))
    except Exception:
        logger.debug("Could not read process path for pid %s", pid)
        return ""
    finally:
        if handle is not None:
            win32api.CloseHandle(handle)


def _is_cloaked(hwnd: int) -> bool:
    cloaked = wintypes.DWORD()
    result = ctypes.windll.dwmapi.DwmGetWindowAttribute(
        hwnd,
        _DWMWA_CLOAKED,
        ctypes.byref(cloaked),
        ctypes.sizeof(cloaked),
    )
    return result == 0 and cloaked.value != 0
