#!/usr/bin/env python3
"""Run the API from any working directory.

This script sets the app-dir to dev-indexer_1 so 'uvicorn' can be launched
from the repository root (or elsewhere) without PYTHONPATH tweaks.
"""

import os
import sys
import subprocess


def main() -> int:
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app_dir = os.path.join(repo_root, "dev-indexer_1")
    # Default host/port can be overridden via env
    host = os.environ.get("HOST", "127.0.0.1")
    port = os.environ.get("PORT", "8000")
    # Default env for smooth local bring-up
    env = os.environ.copy()
    env.setdefault("STRICT_ENV", "false")
    env.setdefault("SKIP_AUDIO_IMPORTS", "1")

    args = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--app-dir",
        app_dir,
        "--host",
        host,
        "--port",
        port,
    ]
    # Forward extra args
    if "--reload" in sys.argv:
        args.append("--reload")
    return subprocess.run(args, cwd=repo_root, env=env).returncode


if __name__ == "__main__":
    raise SystemExit(main())
