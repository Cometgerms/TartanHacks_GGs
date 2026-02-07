# TartanHacks — Audio AI Agent (Dedalus-powered)

A TartanHacks project with:

- **Frontend**: React (Vite) + Anime.js + Modern UI
- **Backend**: Python (Flask) + Dedalus AI + Pedalboard/FFmpeg

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
---

## Project structure (current)

<!-- live update project structure diagram here -->

```
root
├── backend
│   ├── AIDedalus
│   │   ├── aiagent.py        # main agent logic
│   │   ├── audio_engine.py   # audio processing logic
│   │   ├── run_server.py     # Main entry point for Flask server
│   │   ├── pedalboard_worker.py
│   │   └── test
│   ├── requirements.txt
│   └── uploads/              # processed files go here
├── frontend
│   ├── src
│   │   ├── App.jsx           # main React app (Vite)
│   │   └── App.css           # styles
│   ├── package.json
│   ├── vite.config.js
│   └── index.html
├── README.md  # this file
```

---

## Prerequisites

- **Node.js** 18+ (Vite)
- **Python** 3.9+ 
- **FFmpeg** installed and in PATH (required for audio processing)

---

## Backend setup (Windows)

1) Configure secrets in `backend/.env` (create if missing):

```env
API_KEY=YOUR_DEDALUS_KEY
UPLOAD_FOLDER=uploads
# Optional:
# DEDALUS_MODEL=gpt-4.1-mini
```

2) Install Python deps:

```bat
py -m pip install -r backend\requirements.txt
```

3) Run the backend:

```bat
py backend\AIDedalus\run_server.py
```

Backend listens on `http://localhost:5000`.

---

## Frontend setup (Windows)

```bat
cd frontend
npm install
npm run dev
```

Frontend typically runs on `http://localhost:5173` (Vite default) and proxies API requests to `http://localhost:5000` via `vite.config.js`.

---

## Tests / sanity checks

- Dedalus connectivity test:

```bat
py backend\AIDedalus\test\chattest.py
```




---
