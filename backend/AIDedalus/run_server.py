"""Run the Flask backend locally.

This exists because aiagent.py is designed to be importable (tests, scripts) and
may not include an app.run() guard.

Usage:
  py backend/AIDedalus/run_server.py

Environment:
  - PORT (default 5000)
  - HOST (default 0.0.0.0)
  - FLASK_DEBUG (1/0)
"""

from __future__ import annotations

import os

import aiagent


def main() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "0").strip().lower() in {"1", "true", "yes", "on"}

    # Print a friendly line so it's obvious the server started.
    print(f"Starting backend on http://{host}:{port} (debug={debug})")
    aiagent.app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()

