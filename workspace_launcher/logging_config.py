"""Console logging for Workspace Launcher.

Log level comes from the environment so nothing is tied to a specific machine.
Output stays on the console; this foundation does not write log files.
"""

import logging
import os

LOG_LEVEL_ENV = "WORKSPACE_LAUNCHER_LOG_LEVEL"
_DEFAULT_LEVEL = "INFO"


def configure_logging() -> None:
    """Configure process-wide console logging once."""
    requested = os.environ.get(LOG_LEVEL_ENV, _DEFAULT_LEVEL).upper()
    level = getattr(logging, requested, None)
    if not isinstance(level, int):
        level = logging.INFO
        unknown_level = requested
    else:
        unknown_level = None

    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )
    else:
        root.setLevel(level)

    if unknown_level is not None:
        logging.getLogger("workspace_launcher").warning(
            "Unknown %s=%r; using INFO.",
            LOG_LEVEL_ENV,
            unknown_level,
        )
