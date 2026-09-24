"""Pure matching rules for monitors and windows.

These functions do not call Windows. Capture and restore use them so the
decisions can be tested without a desktop session.
"""

from __future__ import annotations

from workspace_launcher.models import DisplaySnapshot, LiveWindow, WindowSnapshot

_MIN_APP_SCORE = 70


def match_display(
    saved_windows_monitor: WindowSnapshot,
    saved_displays: list[DisplaySnapshot],
    current: list[DisplaySnapshot],
) -> tuple[DisplaySnapshot | None, str]:
    """Pick the monitor a saved window should return to."""
    saved = _saved_display(saved_windows_monitor, saved_displays)
    if not current:
        return None, "no displays"
    if saved is None:
        primary = _primary(current)
        return (primary or current[0]), "primary fallback"

    by_id = [
        item
        for item in current
        if saved.device_id and item.device_id == saved.device_id
    ]
    if len(by_id) == 1:
        return by_id[0], "device id"

    by_name = [
        item
        for item in current
        if item.device_name
        and item.device_name == saved.device_name
        and _bounds_close(item, saved)
    ]
    if len(by_name) == 1:
        return by_name[0], "device name"

    best: DisplaySnapshot | None = None
    best_area = 0
    for item in current:
        area = _overlap_area(saved, item)
        if area > best_area:
            best = item
            best_area = area
    if best is not None and best_area > 0:
        return best, "overlap"

    primary = _primary(current)
    return (primary or current[0]), "primary fallback"


def placement_on_display(
    window: WindowSnapshot,
    target: DisplaySnapshot,
) -> tuple[int, int, int, int]:
    """Translate a saved offset onto the target monitor, clamped so it stays visible."""
    width = window.width if window.width > 0 else target.width
    height = window.height if window.height > 0 else target.height
    if width > target.width:
        width = target.width
    if height > target.height:
        height = target.height

    x = target.left + window.offset_x
    y = target.top + window.offset_y
    if x < target.left or x + width > target.left + target.width:
        x = target.left
    if y < target.top or y + height > target.top + target.height:
        y = target.top
    return x, y, width, height


def match_windows(
    saved: list[WindowSnapshot],
    live: list[LiveWindow],
) -> list[tuple[WindowSnapshot, LiveWindow | None]]:
    """Greedy match. Each live window is used at most once."""
    used: set[int] = set()
    pairs: list[tuple[WindowSnapshot, LiveWindow | None]] = []
    for item in saved:
        best_index: int | None = None
        best_score = 0
        for index, candidate in enumerate(live):
            if index in used:
                continue
            score = _score(item, candidate)
            if score > best_score:
                best_score = score
                best_index = index
        if best_index is not None and best_score >= _MIN_APP_SCORE:
            used.add(best_index)
            pairs.append((item, live[best_index]))
        else:
            pairs.append((item, None))
    return pairs


def _score(saved: WindowSnapshot, live: LiveWindow) -> int:
    if (
        saved.exe_path
        and live.exe_path
        and saved.exe_path.casefold() == live.exe_path.casefold()
    ):
        score = 100
    elif (
        saved.exe_name
        and live.exe_name
        and saved.exe_name.casefold() == live.exe_name.casefold()
    ):
        score = 70
    else:
        return 0
    if saved.window_class and saved.window_class == live.window_class:
        score += 10
    if saved.title and live.title and saved.title.casefold() == live.title.casefold():
        score += 40
    elif (
        saved.title
        and live.title
        and (
            saved.title.casefold() in live.title.casefold()
            or live.title.casefold() in saved.title.casefold()
        )
    ):
        score += 15
    return score


def _saved_display(
    window: WindowSnapshot,
    displays: list[DisplaySnapshot],
) -> DisplaySnapshot | None:
    for item in displays:
        if window.monitor_device_id and item.device_id == window.monitor_device_id:
            return item
    for item in displays:
        if (
            window.monitor_device_name
            and item.device_name == window.monitor_device_name
        ):
            return item
    return None


def _primary(displays: list[DisplaySnapshot]) -> DisplaySnapshot | None:
    for item in displays:
        if item.is_primary:
            return item
    return None


def _bounds_close(
    left: DisplaySnapshot, right: DisplaySnapshot, tolerance: int = 80
) -> bool:
    return (
        abs(left.left - right.left) <= tolerance
        and abs(left.top - right.top) <= tolerance
        and abs(left.width - right.width) <= tolerance
        and abs(left.height - right.height) <= tolerance
    )


def _overlap_area(saved: DisplaySnapshot, current: DisplaySnapshot) -> int:
    x1 = max(saved.left, current.left)
    y1 = max(saved.top, current.top)
    x2 = min(saved.left + saved.width, current.left + current.width)
    y2 = min(saved.top + saved.height, current.top + current.height)
    if x2 <= x1 or y2 <= y1:
        return 0
    return (x2 - x1) * (y2 - y1)
