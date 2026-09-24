"""Workspace snapshots stored on this machine."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class DisplaySnapshot:
    device_name: str
    device_id: str
    friendly_name: str
    left: int
    top: int
    width: int
    height: int
    is_primary: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DisplaySnapshot:
        return cls(
            device_name=str(data["device_name"]),
            device_id=str(data.get("device_id", "")),
            friendly_name=str(data.get("friendly_name", "")),
            left=int(data["left"]),
            top=int(data["top"]),
            width=int(data["width"]),
            height=int(data["height"]),
            is_primary=bool(data.get("is_primary", False)),
        )


@dataclass
class WindowSnapshot:
    exe_path: str
    exe_name: str
    window_class: str
    title: str
    monitor_device_id: str
    monitor_device_name: str
    offset_x: int
    offset_y: int
    width: int
    height: int
    show_state: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WindowSnapshot:
        return cls(
            exe_path=str(data.get("exe_path", "")),
            exe_name=str(data.get("exe_name", "")),
            window_class=str(data.get("window_class", "")),
            title=str(data.get("title", "")),
            monitor_device_id=str(data.get("monitor_device_id", "")),
            monitor_device_name=str(data.get("monitor_device_name", "")),
            offset_x=int(data.get("offset_x", 0)),
            offset_y=int(data.get("offset_y", 0)),
            width=int(data.get("width", 0)),
            height=int(data.get("height", 0)),
            show_state=str(data.get("show_state", "normal")),
        )

    @property
    def label(self) -> str:
        if self.exe_name:
            return self.exe_name.removesuffix(".exe")
        return self.title or "Unknown window"


@dataclass
class LiveWindow:
    hwnd: int
    exe_path: str
    exe_name: str
    window_class: str
    title: str
    monitor_device_id: str
    monitor_device_name: str
    offset_x: int
    offset_y: int
    width: int
    height: int
    show_state: str


@dataclass
class Workspace:
    id: str
    name: str
    hotkey_slot: int | None
    created_at: str
    updated_at: str
    displays: list[DisplaySnapshot]
    windows: list[WindowSnapshot]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "hotkey_slot": self.hotkey_slot,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "displays": [item.to_dict() for item in self.displays],
            "windows": [item.to_dict() for item in self.windows],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Workspace:
        slot = data.get("hotkey_slot")
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            hotkey_slot=int(slot) if slot else None,
            created_at=str(data.get("created_at", "")),
            updated_at=str(data.get("updated_at", "")),
            displays=[
                DisplaySnapshot.from_dict(item) for item in data.get("displays", [])
            ],
            windows=[
                WindowSnapshot.from_dict(item) for item in data.get("windows", [])
            ],
        )

    @property
    def hotkey_label(self) -> str:
        if not self.hotkey_slot:
            return ""
        return f"Ctrl+Alt+{self.hotkey_slot}"

    @property
    def apps_summary(self) -> str:
        names: list[str] = []
        for window in self.windows:
            label = window.label
            if label and label not in names:
                names.append(label)
        return " · ".join(names)


@dataclass
class RestoreItem:
    label: str
    ok: bool
    detail: str
