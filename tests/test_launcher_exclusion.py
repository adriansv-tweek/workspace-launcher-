import sys

from workspace_launcher.desktop import _is_workspace_launcher


def test_own_process_is_excluded() -> None:
    assert _is_workspace_launcher(12, sys.executable, "Workspace Launcher", 12)


def test_same_python_with_our_title_is_excluded() -> None:
    assert _is_workspace_launcher(99, sys.executable, "Workspace Launcher", 12)


def test_other_python_window_is_kept() -> None:
    assert not _is_workspace_launcher(99, sys.executable, "Notes", 12)


def test_python_window_with_the_app_title_is_excluded() -> None:
    assert _is_workspace_launcher(
        99, r"C:\Python312\python.exe", "Workspace Launcher", 12
    )


def test_other_application_is_kept() -> None:
    assert not _is_workspace_launcher(40, r"C:\Apps\Notes.exe", "Notes", 12)
