"""Tiny integration test for AudioEngine wiring through aiagent.

Run:
  py backend\AIDedalus\test\audioengine_integration_test.py

It avoids external tools (ffmpeg/demucs) by generating a small WAV on the fly.
"""

from __future__ import annotations

from io import BytesIO

import os
import sys

# Ensure imports work when running this file directly.
THIS_DIR = os.path.dirname(__file__)
AIDEDALUS_DIR = os.path.abspath(os.path.join(THIS_DIR, ".."))
if AIDEDALUS_DIR not in sys.path:
    sys.path.insert(0, AIDEDALUS_DIR)

import numpy as np
import soundfile as sf

from aiagent import app


def _make_test_wav_bytes(sr: int = 16000, seconds: float = 1.0) -> BytesIO:
    t = np.linspace(0, seconds, int(sr * seconds), endpoint=False)
    x = 0.1 * np.sin(2 * np.pi * 440.0 * t)
    audio = np.stack([x, x], axis=1).astype(np.float32)

    bio = BytesIO()
    sf.write(bio, audio, sr, format="WAV", subtype="PCM_16")
    bio.seek(0)
    return bio


def main() -> None:
    client = app.test_client()

    r = client.post("/chat", json={"text": "Hi"})
    assert r.status_code == 200, r.data
    sid = r.get_json()["session_id"]

    wav = _make_test_wav_bytes()
    r = client.post(
        "/aiagent",
        data={
            "text": "\\reverb(); \\distortion(); \\lufs_measure();",
            "session_id": sid,
            "audio": (wav, "tone.wav"),
        },
        content_type="multipart/form-data",
    )
    assert r.status_code == 200, r.data
    data = r.get_json()

    assert data["audio_engine"]["ran"] is True
    assert data["output_audio_path"], "Expected a processed output WAV path"

    payload = data["downstream"]["payload"]
    assert payload and payload["audio_engine_plan"]["calls"], "Expected a plan with calls"

    print("audioengine_integration_test: OK")


if __name__ == "__main__":
    main()
