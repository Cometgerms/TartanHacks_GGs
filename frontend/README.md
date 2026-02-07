# Audio Processing Frontend

React-based frontend for the audio processing application.

## Features

- Upload audio files
- Process audio (normalize, trim, get info)
- Download processed files
- Clean and modern UI

## Setup

1. Install Node.js dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm start
```

The app will open at `http://localhost:3000`

## Configuration

The frontend connects to the backend API at `http://localhost:5000` by default.

To change the API URL, create a `.env` file:
```
REACT_APP_API_URL=http://your-backend-url:5000
```

## Build for Production

```bash
npm run build
```

This creates an optimized production build in the `build` folder.

## Project Structure

```
frontend/
├── public/
│   └── index.html          # HTML template
├── src/
│   ├── components/         # React components
│   │   ├── AudioUpload.js
│   │   ├── AudioProcessor.js
│   │   └── FileList.js
│   ├── services/          # API services
│   │   └── api.js
│   ├── App.js             # Main app component
│   ├── App.css            # App styles
│   ├── index.js           # Entry point
│   └── index.css          # Global styles
└── package.json           # Dependencies and scripts
```

## Available Scripts

- `npm start` - Start development server
- `npm build` - Create production build
- `npm test` - Run tests
- `npm eject` - Eject from Create React App (one-way operation)
