"""Workspace capture, restore, and file operations used by the UI."""

from __future__ import annotations

import logging

from workspace_launcher.capture import capture_workspace
from workspace_launcher.models import RestoreItem, Workspace
from workspace_launcher.restore import restore_workspace
from workspace_launcher.storage import StorageError, WorkspaceStore

logger = logging.getLogger("workspace_launcher.service")


class WorkspaceService:
    def __init__(self, store: WorkspaceStore | None = None) -> None:
        self.store = store or WorkspaceStore()

    def list_workspaces(self) -> list[Workspace]:
        return self.store.list_workspaces()

    def capture(self, name: str) -> Workspace:
        displays, windows = capture_workspace()
        workspace = self.store.save_new(name, displays, windows)
        logger.info('Captured workspace "%s"', workspace.name)
        return workspace

    def update_snapshot(self, workspace_id: str) -> Workspace:
        displays, windows = capture_workspace()
        workspace = self.store.replace_snapshot(workspace_id, displays, windows)
        logger.info('Updated workspace "%s"', workspace.name)
        return workspace

    def restore(self, workspace_id: str) -> list[RestoreItem]:
        workspace = self.store.get(workspace_id)
        return restore_workspace(workspace)

    def restore_slot(self, slot: int) -> list[RestoreItem] | None:
        workspace = self.store.get_by_slot(slot)
        if workspace is None:
            logger.info("No workspace is assigned to Ctrl+Alt+%s", slot)
            return None
        logger.info('Hotkey restoring workspace "%s"', workspace.name)
        return restore_workspace(workspace)

    def rename(self, workspace_id: str, name: str) -> Workspace:
        workspace = self.store.rename(workspace_id, name)
        logger.info('Renamed workspace to "%s"', workspace.name)
        return workspace

    def delete(self, workspace_id: str) -> None:
        workspace = self.store.get(workspace_id)
        self.store.delete(workspace_id)
        logger.info('Deleted workspace "%s"', workspace.name)


__all__ = ["StorageError", "WorkspaceService"]
