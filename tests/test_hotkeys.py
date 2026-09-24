import os
import time

import pytest

pytest.importorskip("win32gui")

from workspace_launcher.hotkeys import HotkeyListener


@pytest.mark.skipif(os.name != "nt", reason="Windows hotkeys only")
def test_ctrl_alt_number_reaches_the_listener() -> None:
    listener = HotkeyListener(lambda _slot: None)
    listener.start()
    try:
        listener.set_slots({1})
        time.sleep(0.3)
        assert 1 in listener._slots
        _tap_ctrl_alt_1()
        slot = listener.events.get(timeout=2)
        assert slot == 1
    finally:
        listener.stop()


def _tap_ctrl_alt_1() -> None:
    import ctypes

    user32 = ctypes.windll.user32
    key_up = 0x0002
    control = 0x11
    alt = 0x12
    number_one = 0x31
    user32.keybd_event(control, 0, 0, 0)
    user32.keybd_event(alt, 0, 0, 0)
    user32.keybd_event(number_one, 0, 0, 0)
    user32.keybd_event(number_one, 0, key_up, 0)
    user32.keybd_event(alt, 0, key_up, 0)
    user32.keybd_event(control, 0, key_up, 0)
