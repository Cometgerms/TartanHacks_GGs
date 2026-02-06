# Audio Processing Backend

Python Flask backend for audio processing operations.

## Features

- Audio file upload (supports WAV, MP3, OGG, FLAC, M4A)
- Audio information extraction
- Audio normalization
- Audio trimming
- Volume adjustment
- Speed modification

## Setup

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Install ffmpeg (required by pydub):
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
```

3. Run the server:
```bash
python app.py
```

The server will start on `http://localhost:5000`

## API Endpoints

### Health Check
- **GET** `/`
- Returns server status

### Upload Audio
- **POST** `/api/upload`
- Form data: `file` (audio file)
- Returns: Upload confirmation with filename

### Process Audio
- **POST** `/api/process`
- JSON body:
  ```json
  {
    "filename": "audio.wav",
    "operation": "info|normalize|trim",
    "start_time": 0,  // for trim operation
    "end_time": 10    // for trim operation
  }
  ```
- Returns: Processing result

### Download Processed File
- **GET** `/api/download/<filename>`
- Returns: Processed audio file

### List Files
- **GET** `/api/files`
- Returns: List of uploaded and processed files

## Project Structure

```
backend/
├── app.py              # Flask application and API endpoints
├── audio_processor.py  # Audio processing logic
├── requirements.txt    # Python dependencies
├── uploads/           # Uploaded audio files (created automatically)
└── processed/         # Processed audio files (created automatically)
```
