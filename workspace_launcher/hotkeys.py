"""Global Ctrl+Alt+1 through Ctrl+Alt+9 hotkeys.

Tk's main loop takes Windows messages for its own window and drops WM_HOTKEY
before Python can poll for it. These shortcuts are therefore registered on a
message-only window with its own thread and queue. The UI drains that queue.
"""

from __future__ import annotations

import ctypes
import logging
import queue
import threading
from ctypes import wintypes
from typing import Callable

logger = logging.getLogger("workspace_launcher.hotkeys")

_MOD_CONTROL = 0x0002
_MOD_ALT = 0x0001
_MOD_NOREPEAT = 0x4000
_WM_HOTKEY = 0x0312
_WM_CLOSE = 0x0010
_WM_RELOAD = 0x8000 + 1
_VK_0 = 0x30
_HWND_MESSAGE = wintypes.HWND(-3)

_user32 = ctypes.windll.user32
_kernel32 = ctypes.windll.kernel32
_kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
_kernel32.GetModuleHandleW.restype = wintypes.HINSTANCE
_user32.RegisterClassW.argtypes = [ctypes.c_void_p]
_user32.RegisterClassW.restype = wintypes.ATOM
_user32.UnregisterClassW.argtypes = [wintypes.LPCWSTR, wintypes.HINSTANCE]
_user32.UnregisterClassW.restype = wintypes.BOOL
_user32.DestroyWindow.argtypes = [wintypes.HWND]
_user32.DestroyWindow.restype = wintypes.BOOL

_WNDPROC = ctypes.WINFUNCTYPE(
    ctypes.c_ssize_t,
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
)


class _WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT),
        ("lpfnWndProc", _WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]


_user32.DefWindowProcW.argtypes = [
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
]
_user32.DefWindowProcW.restype = ctypes.c_ssize_t
_user32.RegisterHotKey.argtypes = [
    wintypes.HWND,
    ctypes.c_int,
    wintypes.UINT,
    wintypes.UINT,
]
_user32.RegisterHotKey.restype = wintypes.BOOL
_user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
_user32.UnregisterHotKey.restype = wintypes.BOOL
_user32.PostMessageW.argtypes = [
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
]
_user32.PostMessageW.restype = wintypes.BOOL
_user32.CreateWindowExW.argtypes = [
    wintypes.DWORD,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.DWORD,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.HWND,
    wintypes.HMENU,
    wintypes.HINSTANCE,
    wintypes.LPVOID,
]
_user32.CreateWindowExW.restype = wintypes.HWND
_user32.GetMessageW.argtypes = [
    ctypes.POINTER(wintypes.MSG),
    wintypes.HWND,
    wintypes.UINT,
    wintypes.UINT,
]
_user32.GetMessageW.restype = ctypes.c_int


class HotkeyListener:
    def __init__(self, on_slot: Callable[[int], None]) -> None:
        self._on_slot = on_slot
        self.events: queue.Queue[int] = queue.Queue()
        self._slots: set[int] = set()
        self._wanted: set[int] = set()
        self._lock = threading.Lock()
        self._hwnd: int | None = None
        self._ready = threading.Event()
        self._proc = _WNDPROC(self._wndproc)
        self._class_name = f"WorkspaceLauncherHotkeys-{id(self)}"
        self._thread = threading.Thread(target=self._loop, name="hotkeys", daemon=True)

    def start(self) -> None:
        self._thread.start()
        if not self._ready.wait(timeout=2):
            logger.error("Hotkey listener did not start.")

    def set_slots(self, slots: set[int]) -> None:
        with self._lock:
            self._wanted = {slot for slot in slots if slot in range(1, 10)}
        hwnd = self._hwnd
        if hwnd:
            _user32.PostMessageW(hwnd, _WM_RELOAD, 0, 0)

    def stop(self) -> None:
        hwnd = self._hwnd
        if hwnd:
            _user32.PostMessageW(hwnd, _WM_CLOSE, 0, 0)
        self._thread.join(timeout=2)

    def _loop(self) -> None:
        instance = _kernel32.GetModuleHandleW(None)
        window_class = _WNDCLASSW()
        window_class.lpfnWndProc = self._proc
        window_class.hInstance = instance
        window_class.lpszClassName = self._class_name
        _user32.RegisterClassW(ctypes.byref(window_class))
        hwnd = _user32.CreateWindowExW(
            0,
            self._class_name,
            "Workspace Launcher hotkeys",
            0,
            0,
            0,
            0,
            0,
            _HWND_MESSAGE,
            None,
            instance,
            None,
        )
        self._hwnd = hwnd
        self._ready.set()
        if not hwnd:
            logger.error("Could not create the hotkey window.")
            return
        self._apply_slots()
        message = wintypes.MSG()
        while _user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
            _user32.TranslateMessage(ctypes.byref(message))
            _user32.DispatchMessageW(ctypes.byref(message))
        self._unregister_all()
        _user32.DestroyWindow(hwnd)
        _user32.UnregisterClassW(self._class_name, instance)
        self._hwnd = None

    def _wndproc(self, hwnd: int, msg: int, wparam: int, lparam: int) -> int:
        if msg == _WM_HOTKEY:
            slot = int(wparam)
            logger.info("Hotkey Ctrl+Alt+%s", slot)
            self.events.put(slot)
            return 0
        if msg == _WM_RELOAD:
            self._apply_slots()
            return 0
        if msg == _WM_CLOSE:
            _user32.PostQuitMessage(0)
            return 0
        return int(_user32.DefWindowProcW(hwnd, msg, wparam, lparam))

    def _apply_slots(self) -> None:
        hwnd = self._hwnd
        if not hwnd:
            return
        with self._lock:
            wanted = set(self._wanted)
        for slot in list(self._slots):
            if slot not in wanted:
                _user32.UnregisterHotKey(hwnd, slot)
                self._slots.discard(slot)
        for slot in sorted(wanted):
            if slot in self._slots:
                continue
            ok = _user32.RegisterHotKey(
                hwnd,
                slot,
                _MOD_CONTROL | _MOD_ALT | _MOD_NOREPEAT,
                _VK_0 + slot,
            )
            if ok:
                self._slots.add(slot)
                logger.info("Registered Ctrl+Alt+%s", slot)
            else:
                logger.warning(
                    "Could not register Ctrl+Alt+%s (error %s).",
                    slot,
                    _kernel32.GetLastError(),
                )

    def _unregister_all(self) -> None:
        hwnd = self._hwnd
        if not hwnd:
            return
        for slot in list(self._slots):
            _user32.UnregisterHotKey(hwnd, slot)
        self._slots.clear()
