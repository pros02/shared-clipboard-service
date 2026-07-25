"""Development entry point for the Phase 0 scaffolding.

Wires together config loading and logging so the scaffolding can be smoke
tested end to end. The real GUI bootstrap arrives in a later phase.
"""
from __future__ import annotations

from cbs import platform
from cbs.config.settings import load_settings
from cbs.logging_setup import configure_logging


def main() -> None:
    config_path = platform.get_config_dir() / "config.json"
    settings = load_settings(config_path)
    logger = configure_logging(settings.log_level, platform.get_log_dir())

    logger.info("Shared Clipboard Service scaffolding starting")
    logger.info("client_id=%s client_name=%s", settings.client_id, settings.client_name)
    logger.info("Settings loaded from %s", config_path)
    logger.info("Logs are written locally only, under %s", platform.get_log_dir())
    if not settings.nas_shared_folder:
        logger.warning("NAS shared folder is not configured yet")
    logger.warning("GUI is not implemented yet (Phase 0 scaffolding only)")


if __name__ == "__main__":
    main()
