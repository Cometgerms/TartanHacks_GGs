# TartanHacks_GGs
TartanHacks Project for team GGs

## Project Structure

This project consists of a **Node.js frontend** and a **Python backend**.

```
TartanHacks_GGs/
├── frontend/          # Node.js frontend with Express
│   ├── server.js      # Express server
│   ├── package.json   # Node dependencies
│   └── public/        # Static files (HTML, CSS, JS)
├── backend/           # Python Flask backend
│   ├── app.py         # Flask API server
│   └── requirements.txt  # Python dependencies
└── README.md          # This file
```

## Quick Start

### Prerequisites
- Node.js (v14 or higher)
- Python (v3.7 or higher)
- pip (Python package manager)

### Setup Backend (Python)

1. Navigate to the backend directory:
```bash
cd backend
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the backend server:
```bash
python app.py
```

The backend will be available at `http://localhost:5000`

### Setup Frontend (Node.js)

1. Open a new terminal and navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Run the frontend server:
```bash
npm start
```

The frontend will be available at `http://localhost:3000`

## Usage

1. Start both servers (backend and frontend)
2. Open your browser and navigate to `http://localhost:3000`
3. The web interface will show:
   - Server status for both frontend and backend
   - Ability to fetch data from the backend
   - Ability to send data to the backend

## API Endpoints

### Backend (Python Flask) - Port 5000

- `GET /` - Welcome message
- `GET /api/health` - Health check endpoint
- `GET /api/data` - Get sample data
- `POST /api/data` - Post data to the server

### Frontend (Node.js) - Port 3000

- `GET /` - Main web interface
- `GET /api/frontend-health` - Frontend health check

## Features

- **Frontend**: Express.js server serving static HTML/CSS/JS
- **Backend**: Flask REST API with CORS enabled
- **Communication**: Frontend can fetch and send data to backend
- **Interactive UI**: Modern, responsive web interface
- **Status Monitoring**: Real-time server status checks

## Technology Stack

- **Frontend**: Node.js, Express.js, HTML, CSS, JavaScript
- **Backend**: Python, Flask, Flask-CORS
- **Communication**: REST API, JSON

## Development

- Both servers support hot-reloading during development
- Frontend communicates with backend via HTTP requests
- CORS is enabled on the backend to allow cross-origin requests
