"""Entry point for python -m gws."""

import os
os.environ.setdefault("PYTHONUNBUFFERED", "1")

from gws.cli import app

if __name__ == "__main__":
    app()
