"""Backend-side upload test.

This bypasses the frontend and proves whether Flask receives the multipart file part.
Run:
  py backend/AIDedalus/test_upload_debug.py

Expected:
  - debug_uploads.files_keys contains "audio"
  - debug_uploads.has_audio is True
  - audio_path is non-empty
"""

from __future__ import annotations

import os
import sys


def main() -> int:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    sys.path.insert(0, os.path.join(repo_root, "backend", "AIDedalus"))

    import aiagent  # noqa: WPS433

    aiagent.DEBUG_UPLOADS = True
    client = aiagent.app.test_client()

    sid_resp = client.post("/api/chat", json={"text": "hello"})
    if sid_resp.status_code != 200:
        print("chat init failed", sid_resp.status_code, sid_resp.get_data(as_text=True))
        return 1

    session_id = sid_resp.get_json()["session_id"]

    audio_path = os.path.join(repo_root, "backend", "AIDedalus", "test", "test_Man.mp3")
    if not os.path.exists(audio_path):
        print("missing test file:", audio_path)
        return 2

    with open(audio_path, "rb") as f:
        resp = client.post(
            "/api/aiagent",
            data={
                "text": "make it hollow",
                "session_id": session_id,
                "audio": (f, "Man.wav"),
            },
            content_type="multipart/form-data",
        )

    print("status:", resp.status_code)
    try:
        data = resp.get_json()
    except Exception:
        print("non-json response:")
        print(resp.get_data(as_text=True))
        return 3

    print("need_audio:", data.get("need_audio"))
    print("audio_path:", data.get("audio_path"))
    print("debug_uploads:", data.get("debug_uploads"))
    print("reply:")
    print(data.get("reply"))

    dbg = data.get("debug_uploads") or {}
    files_keys = dbg.get("files_keys") or []
    if "audio" not in files_keys:
        print("\nFAIL: backend did NOT receive the 'audio' file part.")
        return 4

    if not data.get("audio_path"):
        print("\nFAIL: backend received audio part but did not persist audio_path.")
        return 5

    print("\nPASS: backend received audio upload correctly.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

