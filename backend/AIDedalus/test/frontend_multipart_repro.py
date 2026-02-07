"""Reproduce the browser multipart upload against the running Flask server.

Run:
  py backend\AIDedalus\test\frontend_multipart_repro.py

It requires the Flask app to be running on http://localhost:5000.
"""

from __future__ import annotations

from pathlib import Path

import requests


def main() -> None:
    audio_path = Path(__file__).resolve().parent / "test_Man.mp3"
    if not audio_path.exists():
        raise SystemExit(f"Missing test audio: {audio_path}")

    r = requests.post("http://localhost:5000/api/chat", json={"text": "hello"}, timeout=30)
    r.raise_for_status()
    sid = r.json()["session_id"]

    with audio_path.open("rb") as f:
        rr = requests.post(
            "http://localhost:5000/api/aiagent",
            data={"text": "make this hollow and distorted", "session_id": sid},
            files={"audio": (audio_path.name, f, "audio/mpeg")},
            timeout=300,
        )

    print("status:", rr.status_code)
    j = rr.json()
    print("need_audio:", j.get("need_audio"))
    print("audio_path:", j.get("audio_path"))
    print("requested_effects:", j.get("requested_effects"))
    print("known_effects:", j.get("known_effects"))
    print("reply:", j.get("reply"))


if __name__ == "__main__":
    main()
