"""Tiny smoke test for the Flask app without needing the Dedalus SDK.

It uses Flask's test client so it doesn't need a running server.

Run:
  py backend\AIDedalus\smoke_test.py

Expected:
  - /chat returns 200 and an English-ish reply
  - /aiagent with effect commands but no audio returns need_audio=True
"""

from __future__ import annotations

from io import BytesIO

from aiagent import app


def main() -> None:
    client = app.test_client()

    # health
    r = client.get("/health")
    assert r.status_code == 200, r.data

    # chat
    r = client.post("/chat", json={"text": "Hi"})
    assert r.status_code == 200, r.data
    data = r.get_json()
    assert "reply" in data
    sid = data["session_id"]

    # aiagent: effect commands but no audio => ask for upload
    r = client.post(
        "/aiagent",
        data={"text": "\\reverb();", "session_id": sid},
        content_type="multipart/form-data",
    )
    assert r.status_code == 200, r.data
    data = r.get_json()
    assert data.get("need_audio") is True

    # aiagent: effect commands + audio => downstream payload
    fake_wav = BytesIO(b"RIFF....WAVEfmt ")
    r = client.post(
        "/aiagent",
        data={
            "text": "\\reverb(); \\distortion();",
            "session_id": sid,
            "audio": (fake_wav, "test.wav"),
        },
        content_type="multipart/form-data",
    )
    assert r.status_code == 200, r.data
    data = r.get_json()
    payload = (data.get("downstream") or {}).get("payload")
    assert payload and "generated_code" in payload

    print("smoke_test: OK")


if __name__ == "__main__":
    main()

