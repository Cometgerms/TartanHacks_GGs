# Backend (Python Flask)

## Setup

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

## Running

Start the Flask server:
```bash
python app.py
```

The backend will run on `http://localhost:5000`

## API Endpoints

- `GET /` - Welcome message
- `GET /api/health` - Health check endpoint
- `GET /api/data` - Get sample data
- `POST /api/data` - Post data to the server
