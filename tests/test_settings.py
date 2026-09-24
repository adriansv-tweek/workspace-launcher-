from workspace_launcher.settings import (
    launch_at_startup,
    load_appearance,
    save_appearance,
    set_launch_at_startup,
    startup_command,
)


def test_appearance_defaults_to_dark(tmp_path) -> None:
    assert load_appearance(tmp_path / "missing.json") == "dark"


def test_appearance_is_saved(tmp_path) -> None:
    path = tmp_path / "settings.json"
    save_appearance("light", path)
    assert load_appearance(path) == "light"
    save_appearance("dark", path)
    assert load_appearance(path) == "dark"


def test_startup_command_uses_this_interpreter() -> None:
    command = startup_command()
    assert command.startswith('"')
    assert command.endswith("-m workspace_launcher")


def test_startup_toggle_round_trip() -> None:
    previous = launch_at_startup()
    try:
        set_launch_at_startup(not previous)
        assert launch_at_startup() is not previous
    finally:
        set_launch_at_startup(previous)
