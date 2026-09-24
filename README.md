# Workspace Launcher

Workspace Launcher is a local Windows desktop application. The aim is to let you arrange a workspace the way you want it, save that arrangement as a named profile, and restore it later.

Nothing is sent off the machine. There is no cloud backend and no dependency on internal work systems.

## Status

The project is in the **setup / foundation** phase.

What works now:

- a small Python package
- console startup with logging
- an editable install so the app can be run the same way from this repository

What is not implemented yet:

- workspace capture and restore
- window, monitor, or process handling
- Chrome tabs
- hotkeys
- saved profiles

Those will be added incrementally after this foundation.

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

`".[dev]"` installs the app plus pytest and ruff. Use `python -m pip install -e .` if you only want to run the app.

If activation is blocked by execution policy, call the venv Python directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

## Run

With the virtual environment activated:

```powershell
python -m workspace_launcher
```

The same entry point is also installed as `workspace-launcher`.

Optional log level (default `INFO`):

```powershell
$env:WORKSPACE_LAUNCHER_LOG_LEVEL = "DEBUG"
python -m workspace_launcher
```

A successful start prints two info lines and exits with code 0. There is no window yet.

## Checks

```powershell
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

## Layout

```text
workspace_launcher/
  app.py             application entry point
  logging_config.py  console logging
  __main__.py        python -m workspace_launcher
tests/
  test_startup.py
pyproject.toml
```

New areas (Windows APIs, capture, restore, storage, hotkeys, Chrome) should be added as real modules when the work starts, not as empty placeholders.

## Direction

The likely stack is Python on Windows 11, talking to Windows APIs directly (probably through `pywin32` once window work begins), with local JSON storage at first. Chrome support, if it comes, would be a later extension plus native messaging.

That direction is not locked in. The UI toolkit is also undecided; this phase stays on the console so we do not pick a GUI framework before we need one.

Runtime dependencies are empty on purpose. `pywin32` and a UI library wait until a feature needs them.

## Privacy and security

This foundation does not read your windows, processes, browser, or files, and it does not open network connections.

Later features will see personal workspace details (window titles, paths, maybe tab URLs). That data should stay on this machine. Logging and storage of it should be decided explicitly before those features are built.
