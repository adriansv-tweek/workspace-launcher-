# Workspace Launcher

Workspace Launcher is a local Windows application. Arrange your windows, save that layout as a named workspace, and restore it later.

Nothing is sent off the machine. There is no cloud backend.

## Status

This is the first functional MVP.

What works:

- capture the current monitors and normal application windows
- save, restore, update, rename, and delete workspaces
- launch a missing application from its saved executable path
- move and resize windows back onto the saved monitor
- local JSON storage that survives a restart
- Ctrl+Alt+1 through Ctrl+Alt+9 for the first nine workspaces
- dark or light appearance, remembered locally
- optional start when you sign in to Windows

What is not in this version:

- Chrome tab capture or restore
- changing the shortcut from the menu
- a system tray, so signing in still opens the window
- cloud sync or account features

## Requirements

- Windows 11
- Python 3.12 or newer

## Setup

From the repository root, in PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## Run

```powershell
python -m workspace_launcher
```

1. Open the applications you want and arrange the windows.
2. Click the large **+** and give the workspace a name.
3. Move or close some windows.
4. Open **My Workspaces** from the menu icon and click the workspace.

`Ctrl+Alt+1` restores the first workspace, `Ctrl+Alt+2` the second, and so on, even when another application is in front. A successful restore does not show a dialog. Problems are written to the log.

**Launch at Windows startup** in Settings registers this Python command for the current user. It does not require administrator rights. The window still opens at login; there is no tray icon yet.

Workspaces are stored in `%LOCALAPPDATA%\WorkspaceLauncher\workspaces.json`.

Optional log level (default `INFO`):

```powershell
$env:WORKSPACE_LAUNCHER_LOG_LEVEL = "DEBUG"
python -m workspace_launcher
```

Window titles are written at DEBUG. INFO logs application names, displays, and restore results.

## Checks

```powershell
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

## How a snapshot is stored

A workspace is structured state, not a screenshot:

- monitors: Windows device name, hardware device id, friendly name, bounds, primary flag
- windows: executable path and name, window class, title, show state (normal, maximized, minimized), and position relative to the monitor

The launcher's own window is not included. Shell, tool, cloaked, and empty windows are skipped.

## Restore

1. Match each saved window to a running window by executable path, then executable name. Title breaks ties when one app has several windows.
2. If nothing matches and the executable still exists, start that executable once and wait up to 8 seconds for a window.
3. Place the window on the monitor with the same hardware id. If that monitor is gone, use the monitor that overlaps the old bounds, then the primary monitor.
4. One failed application does not stop the rest. The restore dialog lists what succeeded and what failed.

## Limitations

- A second window of an app that only keeps one process (Chrome, Teams, and similar) may not open again. The first matching window is moved; further saved windows of that same executable are reported as not restored.
- Store apps hosted by `ApplicationFrameHost.exe` can be moved if they are already open. They are not launched.
- Some elevated windows cannot be moved from a non-elevated launcher.
- Titles change, so matching falls back to "the first unused window of this executable".
- Monitor numbers (`DISPLAY1`, `DISPLAY2`) are not trusted on their own. Hardware device id is preferred, with a primary-monitor fallback.
- Hotkeys are fixed to Ctrl+Alt+1–9 in the order workspaces were created. There is no hotkey editor.

## Chrome later

Tab order needs a Chrome extension and native messaging. This MVP only restores the Chrome window through the normal Windows APIs. Keyboard scripting of Chrome is intentionally not used.

## Layout

```text
workspace_launcher/
  app.py            startup
  ui.py             capture and workspace list
  service.py        capture, restore, rename, delete
  capture.py        read the current desktop
  restore.py        launch and move windows
  desktop.py        Win32 monitors, windows, process start
  matching.py       monitor and window matching rules
  storage.py        local JSON file
  hotkeys.py        Ctrl+Alt+1..9
  models.py         snapshot data
```

## Manual check

1. Put two applications on different monitors.
2. Capture a workspace named "Test Workspace".
3. Close one application and move the other.
4. Restore "Test Workspace".
5. Quit Workspace Launcher, start it again, and confirm the workspace is still listed.
6. Update, rename, and delete that workspace.
