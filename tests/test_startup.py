import logging

from workspace_launcher.logging_config import LOG_LEVEL_ENV, configure_logging


def test_unknown_log_level_falls_back_to_info(monkeypatch, caplog) -> None:
    monkeypatch.setenv(LOG_LEVEL_ENV, "NOT_A_LEVEL")
    caplog.set_level(logging.WARNING)
    configure_logging()
    assert logging.getLogger("workspace_launcher").getEffectiveLevel() == logging.INFO
    assert "NOT_A_LEVEL" in caplog.text
