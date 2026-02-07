# AI Dedalus Agent (Backend)

This folder contains a small Flask service that behaves like an **AI audio-processing agent**.

## Team

- Alan
- Raymond
- Liam
- Zack

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

## System Requirements

### FFmpeg (Required for MP3/M4A files)

The audio engine requires **ffmpeg** to process non-WAV audio files (MP3, M4A, etc.).

**Windows:**
1. Download ffmpeg from https://ffmpeg.org/download.html or https://www.gyan.dev/ffmpeg/builds/
2. Extract the zip file
3. Add the `bin` folder to your PATH environment variable:
   - Right-click "This PC" → Properties → Advanced system settings → Environment Variables
   - Under "System variables", find "Path" and click Edit
   - Click New and add the path to ffmpeg's bin folder (e.g., `C:\ffmpeg\bin`)
   - Click OK to save
4. Open a new terminal and verify: `ffmpeg -version`

**Mac:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt-get install ffmpeg  # Ubuntu/Debian
sudo yum install ffmpeg      # CentOS/RHEL
```

### Python Dependencies

Install all required packages:
```bash
cd backend
pip install -r requirements.txt
```

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

## Quick run (macOS)

```bash
python3 -m pip install -r backend/requirements.txt
python3 backend/AIDedalus/aiagent.py
```

Then open:
- `GET http://localhost:5000/health`

### Notes (macOS)

- If you want `audio_engine.py` to convert non-WAV inputs, it calls **ffmpeg**.
  You can install it with:

```bash
brew install ffmpeg
```
