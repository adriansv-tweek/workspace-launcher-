"""Local JSON storage for workspaces."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from workspace_launcher.models import DisplaySnapshot, WindowSnapshot, Workspace

STORE_VERSION = 1
HOTKEY_SLOTS = range(1, 10)


class StorageError(Exception):
    """A workspace could not be saved or loaded."""


def default_store_path() -> Path:
    root = os.environ.get("LOCALAPPDATA")
    base = Path(root) if root else Path.home() / "AppData" / "Local"
    return base / "WorkspaceLauncher" / "workspaces.json"


class WorkspaceStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_store_path()

    def list_workspaces(self) -> list[Workspace]:
        return self._read()

    def get(self, workspace_id: str) -> Workspace:
        for workspace in self._read():
            if workspace.id == workspace_id:
                return workspace
        raise StorageError(f'Workspace "{workspace_id}" does not exist.')

    def get_by_slot(self, slot: int) -> Workspace | None:
        for workspace in self._read():
            if workspace.hotkey_slot == slot:
                return workspace
        return None

    def save_new(
        self,
        name: str,
        displays: list[DisplaySnapshot],
        windows: list[WindowSnapshot],
    ) -> Workspace:
        clean_name = _validate_name(name)
        workspaces = self._read()
        if _name_taken(workspaces, clean_name):
            raise StorageError(f'A workspace named "{clean_name}" already exists.')
        now = _now()
        workspace = Workspace(
            id=uuid.uuid4().hex,
            name=clean_name,
            hotkey_slot=_next_slot(workspaces),
            created_at=now,
            updated_at=now,
            displays=displays,
            windows=windows,
        )
        workspaces.append(workspace)
        self._write(workspaces)
        return workspace

    def replace_snapshot(
        self,
        workspace_id: str,
        displays: list[DisplaySnapshot],
        windows: list[WindowSnapshot],
    ) -> Workspace:
        workspaces = self._read()
        workspace = _require(workspaces, workspace_id)
        workspace.displays = displays
        workspace.windows = windows
        workspace.updated_at = _now()
        self._write(workspaces)
        return workspace

    def rename(self, workspace_id: str, name: str) -> Workspace:
        clean_name = _validate_name(name)
        workspaces = self._read()
        if _name_taken(workspaces, clean_name, ignore_id=workspace_id):
            raise StorageError(f'A workspace named "{clean_name}" already exists.')
        workspace = _require(workspaces, workspace_id)
        workspace.name = clean_name
        workspace.updated_at = _now()
        self._write(workspaces)
        return workspace

    def delete(self, workspace_id: str) -> None:
        workspaces = self._read()
        kept = [item for item in workspaces if item.id != workspace_id]
        if len(kept) == len(workspaces):
            raise StorageError(f'Workspace "{workspace_id}" does not exist.')
        self._write(kept)

    def _read(self) -> list[Workspace]:
        if not self.path.exists():
            return []
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            self._quarantine()
            raise StorageError(
                f"Workspace file is malformed and was moved aside: {self.path}"
            ) from exc
        if not isinstance(payload, dict) or not isinstance(
            payload.get("workspaces"), list
        ):
            self._quarantine()
            raise StorageError(
                f"Workspace file is malformed and was moved aside: {self.path}"
            )
        try:
            return [Workspace.from_dict(item) for item in payload["workspaces"]]
        except (KeyError, TypeError, ValueError) as exc:
            self._quarantine()
            raise StorageError(
                f"Workspace file is malformed and was moved aside: {self.path}"
            ) from exc

    def _write(self, workspaces: list[Workspace]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": STORE_VERSION,
            "workspaces": [item.to_dict() for item in workspaces],
        }
        temporary = self.path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temporary.replace(self.path)

    def _quarantine(self) -> None:
        if not self.path.exists():
            return
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        broken = self.path.with_name(f"{self.path.name}.broken-{stamp}")
        try:
            self.path.replace(broken)
        except OSError:
            return


def _validate_name(name: str) -> str:
    clean = name.strip()
    if not clean:
        raise StorageError("Workspace name cannot be empty.")
    if len(clean) > 80:
        raise StorageError("Workspace name must be 80 characters or fewer.")
    return clean


def _name_taken(
    workspaces: list[Workspace],
    name: str,
    ignore_id: str | None = None,
) -> bool:
    folded = name.casefold()
    return any(
        item.name.casefold() == folded and item.id != ignore_id for item in workspaces
    )


def _next_slot(workspaces: list[Workspace]) -> int | None:
    used = {item.hotkey_slot for item in workspaces}
    for slot in HOTKEY_SLOTS:
        if slot not in used:
            return slot
    return None


def _require(workspaces: list[Workspace], workspace_id: str) -> Workspace:
    for workspace in workspaces:
        if workspace.id == workspace_id:
            return workspace
    raise StorageError(f'Workspace "{workspace_id}" does not exist.')


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
