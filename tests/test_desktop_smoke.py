import os

import pytest

pytest.importorskip("win32gui")

from workspace_launcher.desktop import list_displays, list_windows


@pytest.mark.skipif(os.name != "nt", reason="Windows desktop only")
def test_displays_are_visible() -> None:
    displays = list_displays()
    assert displays
    assert any(item.width > 0 and item.height > 0 for item in displays)


@pytest.mark.skipif(os.name != "nt", reason="Windows desktop only")
def test_window_list_returns_windows() -> None:
    windows = list_windows()
    assert isinstance(windows, list)
    assert windows
    assert all(item.exe_name for item in windows)
