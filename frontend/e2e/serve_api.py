"""Disposable, no-model evidence database for browser integration tests."""

import asyncio
import tempfile
from pathlib import Path
from typing import Any

import uvicorn

from evoteam.api import create_app
from evoteam.demo import run_demo
from evoteam.settings import Settings

if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="evoteam-browser-test-") as directory:
        database = Path(directory) / "evidence.sqlite3"
        asyncio.run(run_demo(database))
        settings = Settings(**dict[str, Any](_env_file=None, database_url=f"sqlite:///{database}"))
        uvicorn.run(create_app(settings), host="127.0.0.1", port=8765)
