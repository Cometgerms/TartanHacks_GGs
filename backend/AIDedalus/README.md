# AI Dedalus Agent (Backend)

This folder contains a small Flask service that behaves like an **AI audio-processing agent**.

## What it does

- Maintains a simple in-memory **chat session** (`session_id`)
- Accepts **text + optional audio file**
- If the user sends audio-effect commands (e.g. `\\reverb();`) **without** an audio file, it asks the user to upload audio
- If the user sends **supported** effect commands **with** an audio file, it returns a downstream **code payload** (pseudo-code)

All assistant replies are forced to **English** via a system prompt.

## Environment

Create `backend/.env` (already present in this repo) with at least:

- `API_KEY=...` (Dedalus Labs API key)
- `UPLOAD_FOLDER=uploads`

Optional:

- `DEDALUS_MODEL=gpt-4.1-mini`
- `AGENT_SYSTEM_PROMPT=...`

> `.env` is ignored by git via `backend/.gitignore`.

## API

### `POST /chat`
JSON body:
- `text` (required)
- `session_id` (optional)

Returns:
- `reply`
- `session_id`
- `messages`

### `POST /aiagent`
`multipart/form-data`:
- `text` (required)
- `session_id` (optional)
- `audio` (optional file)

Returns:
- `reply`
- `need_audio` (when effect commands are present but no audio)
- `downstream.payload` (when audio+effects are present)

## Quick run (Windows)

```bat
py -m pip install -r backend\requirements.txt
py backend\AIDedalus\aiagent.py
```

Then open:
- `GET http://localhost:5000/health`

