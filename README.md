# TartanHacks — Audio AI Agent (Dedalus-powered)

A TartanHacks project with:

- **Frontend**: 
- **Backend**: 

## Team

- Alan
- Raymond
- Liam
- Zack

The agent keeps a chat session, understands effect commands like `\\reverb();`, and can generate a downstream “processing code payload” you can forward to a future processing backend.

---

## Features

- Chat-style interaction (**session_id** based)
- Text + optional audio input
- Effect command parsing: e.g. `\\distortion(); \\reverb();`
---

## Project structure (current)

[//]: # (live update project structure diagram here)

```
root
├── backend
│   ├── AIDedalus
│   │   ├── aiagent.py  # main Flask app
│   │   ├── smoke_test.py  # backend logic test (no server)
│   │   └── test
│   │       └── chattest.py  # Dedalus connectivity test
│   ├── requirements.txt
│   └── .env  # not included in repo, configure with your API key
├── frontend
│   ├── src
│   │   ├── App.js  # main React app
│   │   └── ... other React components
│   ├── package.json
│   └── ... other CRA files
├── README.md  # this file
```

---

## Prerequisites

- **Node.js** 16+ (works with CRA / react-scripts)
- **Python** 3.9+ recommended

[//]: # (> Note: The current agent backend does not require ffmpeg because it does not do waveform processing itself yet.)

---

## Backend setup (Windows)

1) Configure secrets in `backend/.env`:

```env
API_KEY=YOUR_DEDALUS_KEY
UPLOAD_FOLDER=uploads
# Optional:
# DEDALUS_MODEL=gpt-4.1-mini
# AGENT_SYSTEM_PROMPT=...
```

2) Install Python deps:

```bat
py -m pip install -r backend\requirements.txt
```

3) Run the backend:

```bat
py backend\AIDedalus\aiagent.py
```

Backend listens on `http://localhost:5000`.

[//]: # (### Useful endpoints)

[//]: # ()
[//]: # (- `GET /health` — shows whether Dedalus is available + API key configured)

[//]: # (- `POST /chat` — JSON chat endpoint)

[//]: # (- `POST /aiagent` — multipart form endpoint &#40;text + optional audio&#41;)

---

## Frontend setup (Windows)

```bat
cd frontend
npm install
npm start
```

Frontend runs on `http://localhost:3000` and proxies API requests to `http://localhost:5000` (see `frontend/package.json`).

---

## Tests / sanity checks

- Dedalus connectivity test (modified from Dedalus website; requires `API_KEY` and internet):

```bat
py backend\AIDedalus\test\chattest.py
```


- Backend smoke test (no running server required):

```bat
py backend\AIDedalus\smoke_test.py
```


---
