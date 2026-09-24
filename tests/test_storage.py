import json

import pytest

from workspace_launcher.models import DisplaySnapshot, WindowSnapshot
from workspace_launcher.storage import StorageError, WorkspaceStore


def _window(name: str = "notepad.exe") -> WindowSnapshot:
    return WindowSnapshot(
        exe_path=f"C:\\Windows\\System32\\{name}",
        exe_name=name,
        window_class="Notepad",
        title="notes",
        monitor_device_id="MONITOR\\TEST",
        monitor_device_name="\\\\.\\DISPLAY1",
        offset_x=10,
        offset_y=20,
        width=800,
        height=600,
        show_state="normal",
    )


def _display() -> DisplaySnapshot:
    return DisplaySnapshot(
        device_name="\\\\.\\DISPLAY1",
        device_id="MONITOR\\TEST",
        friendly_name="Test",
        left=0,
        top=0,
        width=1920,
        height=1080,
        is_primary=True,
    )


def test_create_load_update_rename_delete(tmp_path) -> None:
    store = WorkspaceStore(tmp_path / "workspaces.json")
    created = store.save_new("Basis", [_display()], [_window()])
    assert created.hotkey_slot == 1
    assert store.get(created.id).name == "Basis"

    second = store.save_new("Linje", [_display()], [_window("chrome.exe")])
    assert second.hotkey_slot == 2

    updated = store.replace_snapshot(
        created.id, [_display()], [_window(), _window("code.exe")]
    )
    assert len(updated.windows) == 2
    assert updated.name == "Basis"

    renamed = store.rename(created.id, "Basis 2")
    assert renamed.name == "Basis 2"
    assert store.get_by_slot(1).name == "Basis 2"

    store.delete(second.id)
    assert len(store.list_workspaces()) == 1
    with pytest.raises(StorageError):
        store.get(second.id)


def test_duplicate_and_empty_names(tmp_path) -> None:
    store = WorkspaceStore(tmp_path / "workspaces.json")
    store.save_new("Basis", [], [])
    with pytest.raises(StorageError):
        store.save_new(" basis ", [], [])
    with pytest.raises(StorageError):
        store.save_new("   ", [], [])


def test_malformed_file_is_moved_aside(tmp_path) -> None:
    path = tmp_path / "workspaces.json"
    path.write_text("{", encoding="utf-8")
    store = WorkspaceStore(path)
    with pytest.raises(StorageError):
        store.list_workspaces()
    assert not path.exists()
    assert list(tmp_path.glob("workspaces.json.broken-*"))


def test_round_trip_shape(tmp_path) -> None:
    store = WorkspaceStore(tmp_path / "workspaces.json")
    store.save_new("Test Workspace", [_display()], [_window()])
    payload = json.loads((tmp_path / "workspaces.json").read_text(encoding="utf-8"))
    assert payload["version"] == 1
    assert payload["workspaces"][0]["windows"][0]["exe_name"] == "notepad.exe"
