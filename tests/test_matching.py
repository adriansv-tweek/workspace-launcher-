from workspace_launcher.matching import (
    match_display,
    match_windows,
    placement_on_display,
)
from workspace_launcher.models import DisplaySnapshot, LiveWindow, WindowSnapshot


def _display(
    device_id: str,
    name: str,
    left: int,
    top: int,
    primary: bool = False,
) -> DisplaySnapshot:
    return DisplaySnapshot(
        device_name=name,
        device_id=device_id,
        friendly_name=device_id,
        left=left,
        top=top,
        width=1920,
        height=1080,
        is_primary=primary,
    )


def _saved(exe: str, title: str, monitor_id: str = "MON-A") -> WindowSnapshot:
    return WindowSnapshot(
        exe_path=f"C:\\Apps\\{exe}",
        exe_name=exe,
        window_class="Window",
        title=title,
        monitor_device_id=monitor_id,
        monitor_device_name="\\\\.\\DISPLAY1",
        offset_x=100,
        offset_y=40,
        width=900,
        height=700,
        show_state="normal",
    )


def _live(hwnd: int, exe: str, title: str) -> LiveWindow:
    return LiveWindow(
        hwnd=hwnd,
        exe_path=f"C:\\Apps\\{exe}",
        exe_name=exe,
        window_class="Window",
        title=title,
        monitor_device_id="",
        monitor_device_name="",
        offset_x=0,
        offset_y=0,
        width=100,
        height=100,
        show_state="normal",
    )


def test_windows_match_by_path_and_title() -> None:
    saved = [
        _saved("chrome.exe", "Mail"),
        _saved("chrome.exe", "Docs"),
        _saved("teams.exe", "Teams"),
    ]
    live = [
        _live(1, "teams.exe", "Teams"),
        _live(2, "chrome.exe", "Docs - Chrome"),
        _live(3, "chrome.exe", "Mail"),
        _live(4, "notepad.exe", "notes"),
    ]
    pairs = match_windows(saved, live)
    assert pairs[0][1].hwnd == 3
    assert pairs[1][1].hwnd == 2
    assert pairs[2][1].hwnd == 1


def test_unmatched_window_is_left_open() -> None:
    pairs = match_windows(
        [_saved("missing.exe", "Gone")], [_live(1, "other.exe", "Other")]
    )
    assert pairs[0][1] is None


def test_monitor_prefers_device_id_over_order() -> None:
    saved_displays = [_display("MON-A", "\\\\.\\DISPLAY1", 0, 0, True)]
    current = [
        _display("MON-B", "\\\\.\\DISPLAY1", 0, 0, True),
        _display("MON-A", "\\\\.\\DISPLAY3", 1920, 0),
    ]
    chosen, how = match_display(_saved("a.exe", "A", "MON-A"), saved_displays, current)
    assert chosen.device_id == "MON-A"
    assert how == "device id"


def test_monitor_falls_back_to_primary_when_disconnected() -> None:
    saved_displays = [_display("MON-GONE", "\\\\.\\DISPLAY9", 5000, 0)]
    current = [_display("MON-PRIMARY", "\\\\.\\DISPLAY1", 0, 0, True)]
    window = _saved("a.exe", "A", "MON-GONE")
    window.monitor_device_name = "\\\\.\\DISPLAY9"
    chosen, how = match_display(window, saved_displays, current)
    assert chosen.device_id == "MON-PRIMARY"
    assert how == "primary fallback"


def test_placement_is_clamped_to_target_monitor() -> None:
    window = _saved("a.exe", "A")
    window.offset_x = 3000
    window.width = 4000
    target = _display("MON-A", "\\\\.\\DISPLAY1", 100, 50, True)
    x, y, width, height = placement_on_display(window, target)
    assert width == target.width
    assert x == target.left
    assert y == target.top + 40
    assert height == 700
