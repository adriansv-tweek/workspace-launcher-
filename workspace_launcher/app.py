"""Application entry point.

This foundation build only proves that the project starts. Workspace capture,
restore, and the rest of the product are not implemented here.
"""

import logging

from workspace_launcher.logging_config import configure_logging

logger = logging.getLogger("workspace_launcher")


def main() -> int:
    """Start the application and return a process exit code."""
    configure_logging()
    logger.info("Workspace Launcher started (foundation build).")
    logger.info("Workspace capture and restore are not implemented yet.")
    return 0
