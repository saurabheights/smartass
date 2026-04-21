# smartass/tray/__main__.py
"""Smartass tray entrypoint."""

import logging
import sys
from logging.handlers import RotatingFileHandler

from smartass.core import paths
from smartass.tray.app import run_tray


def _configure_logging() -> None:
    paths.ensure_user_dirs()
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    handler = RotatingFileHandler(
        paths.cache_dir() / "tray.log", maxBytes=1_000_000, backupCount=5
    )
    handler.setFormatter(fmt)
    root.addHandler(handler)
    stderr = logging.StreamHandler(sys.stderr)
    stderr.setFormatter(fmt)
    root.addHandler(stderr)


def main() -> None:
    _configure_logging()
    sys.exit(run_tray())


if __name__ == "__main__":
    main()
