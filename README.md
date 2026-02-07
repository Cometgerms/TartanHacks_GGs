# 🎵 TartanHacks — Audio AI Agent (Dedalus)


![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=for-the-badge&logo=python)
![React](https://img.shields.io/badge/React-Vite-61DAFB?style=for-the-badge&logo=react)
![Status](https://img.shields.io/badge/Status-Active-success?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)

> **A cutting-edge audio processing agent powered by multimodal AI.**  
> *Built for TartanHacks 2026*

---

## Overview

This project leverages **Dedalus multimodal AI** to interpret user intent (via text or image) and intelligently modify audio files using **Pedalboard** and **FFmpeg**.

- **Frontend**: React (Vite) + Anime.js for a fluid, interactive UI.
- **Backend**: Flask + AI Agent logic for dynamic audio processing chains.

---

## 👥 The Team

**Alan**

**Raymond**

**Liam**

**Zack** 


---

## ✨ Key Features

-  **Natural Language Control**: Tell the agent "make it sound like a radio from the 50s" and it figures out the DSP chain.
-  **Multimodal Context**: Upload an image (e.g., a rainy street) to inspire the audio effects.
-  **Intelligent DSP**: Automatically calls audio processing functions (Reverb, Distortion, EQ) based on interpreted needs.
-  **Modern UI**: A "fancy," anime.js-powered interface that reacts to your interactions.

---

## 📂 Project Structure

```text
.
├── backend/
│   ├── AIDedalus/
│   │   ├── aiagent.py         # The brain: Interprets prompts -> Code
│   │   ├── audio_engine.py    # The muscle: Applies DSP effects
│   │   ├── pedalboard_worker.py
│   │   ├── run_server.py      # Flask entry point
│   │   └── test/
│   ├── uploads/               # Temporary storage for processing
│   ├── .env                   # Configuration & Secrets
│   └── requirements.txt       # Backend dependencies
├── frontend/
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── assets/            # Static assets
│   │   └── App.jsx            # Main UI Logic
│   ├── package.json
│   └── vite.config.js
└── README.md
```

---

## 🛠️ Getting Started

### Prerequisites

*   **Node.js** (v18+)
*   **Python** (v3.9+)
*   **FFmpeg** (Must be installed and added to system PATH)

###  Backend Setup

1.  **Configure Secrets**: Create `backend/.env` based on the example.
    ```env
    API_KEY=YOUR_DEDALUS_KEY
    UPLOAD_FOLDER=uploads
    ```

2.  **Install Dependencies**:
    ```bash
    py -m pip install -r backend/requirements.txt
    ```

3.  **Launch Server**:
    ```bash
    py backend/AIDedalus/run_server.py
    ```
    *Server runs at `http://localhost:5000`*

### Frontend Setup

1.  **Install & Run**:
    ```bash
    cd frontend
    npm install
    npm run dev
    ```
    *App runs at `http://localhost:5173`*

---

##  Testing

Run the connectivity sanity check to ensure the AI agent is reachable:

```bash
py backend/AIDedalus/test/chattest.py
```

---

*Made with ❤️ at TartanHacks 2026*
