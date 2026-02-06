# TartanHacks_GGs - Audio Processing Application

An audio processing web application with a Node.js frontend and Python backend.

## 🎵 Features

- **Upload Audio Files**: Support for multiple audio formats (WAV, MP3, OGG, FLAC, M4A)
- **Audio Information**: Extract detailed information about audio files
- **Audio Processing**: 
  - Normalize audio volume
  - Trim audio clips
  - Adjust playback speed
  - Modify volume levels
- **Download Results**: Download processed audio files

## 🏗️ Architecture

- **Frontend**: React (Node.js)
  - Modern, responsive UI
  - Real-time processing feedback
  - File upload and download
  
- **Backend**: Flask (Python)
  - RESTful API
  - Audio processing with pydub
  - CORS enabled for cross-origin requests

## 🚀 Quick Start

### Prerequisites

- Node.js (v14 or higher)
- Python 3.8 or higher
- ffmpeg (required for audio processing)

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Install ffmpeg:
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg
```

4. Start the backend server:
```bash
python app.py
```

The backend will run on `http://localhost:5000`

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install Node.js dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm start
```

The frontend will open at `http://localhost:3000`

## 📁 Project Structure

```
TartanHacks_GGs/
├── backend/                 # Python Flask backend
│   ├── app.py              # Main Flask application
│   ├── audio_processor.py  # Audio processing logic
│   ├── requirements.txt    # Python dependencies
│   └── README.md           # Backend documentation
│
├── frontend/               # Node.js React frontend
│   ├── public/            # Static files
│   ├── src/               # React source code
│   │   ├── components/    # React components
│   │   ├── services/      # API services
│   │   ├── App.js         # Main app component
│   │   └── index.js       # Entry point
│   ├── package.json       # Node.js dependencies
│   └── README.md          # Frontend documentation
│
└── README.md              # This file
```

## 🔧 API Endpoints

### Health Check
- `GET /` - Check if the server is running

### File Operations
- `POST /api/upload` - Upload an audio file
- `GET /api/files` - List all uploaded and processed files
- `GET /api/download/<filename>` - Download a processed file

### Audio Processing
- `POST /api/process` - Process an audio file
  - Operations: `info`, `normalize`, `trim`

## 🎨 Usage

1. **Upload an Audio File**
   - Click "Choose Audio File" and select your audio file
   - Click "Upload" to send it to the server

2. **Process the Audio**
   - Select an operation (Get Info, Normalize, or Trim)
   - For trimming, specify start and end times in seconds
   - Click "Process" to apply the operation

3. **Download Processed File**
   - After processing, click "Download Processed File" to save the result

## 🛠️ Technologies Used

### Frontend
- React 18
- Axios for API calls
- CSS3 for styling

### Backend
- Flask 3.0
- Flask-CORS for cross-origin support
- Pydub for audio processing
- FFmpeg for audio format support

## 📝 Development

### Adding New Audio Operations

1. Add the processing logic in `backend/audio_processor.py`
2. Add the API endpoint in `backend/app.py`
3. Update the frontend components to support the new operation

## 🤝 Contributing

This is a TartanHacks project for team GGs.

## 📄 License

ISC License
