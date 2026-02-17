# VoxCraft

A full-stack web application for audiobook conversion with a modern React frontend and Python backend.

## Overview

VoxCraft provides a user-friendly web interface for converting text documents to audiobooks using MLX TTS (Apple Silicon optimized). It features a modern React frontend and FastAPI backend.

## Features

- 🌐 **Web Interface**: Modern React UI for easy conversion
- 🚀 **FastAPI Backend**: High-performance Python API
- 🍎 **MLX Optimized**: Uses Apple's MLX framework for fast inference on Apple Silicon
- 📊 **Progress Tracking**: Real-time conversion progress
- 🎨 **Modern UI**: Clean, responsive design
- 🐳 **Docker Support**: Easy deployment with Docker Compose

## Architecture

```
voxcraft/
├── backend/           # FastAPI Python backend
│   ├── main.py       # API entry point
│   └── ...
├── frontend/          # React JavaScript frontend
│   ├── src/
│   └── ...
├── docker-compose.yml # Docker orchestration
├── Dockerfile        # Container definition
└── package.json      # Node.js scripts
```

## Quick Start

### Using Docker (Recommended)

```bash
cd voxcraft

# Start all services
docker-compose up

# Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
```

### Development Mode

```bash
cd voxcraft

# Install frontend dependencies
npm run install:all

# Start both frontend and backend
npm run dev
```

This will start:
- Backend API on `http://localhost:8000`
- Frontend dev server on `http://localhost:3000`

## Prerequisites

### System Requirements

- **Docker** (for containerized deployment)
- **Node.js** 18+ and **npm** (for development)
- **Python** 3.9+ (for development)
- **Apple Silicon Mac** (for MLX TTS - optimized for M1/M2/M3)

### Installing Dependencies

**Backend:**
```bash
cd voxcraft/backend
pip install -r requirements.txt
```

**Frontend:**
```bash
cd voxcraft/frontend
npm install
```

## Usage

1. **Open the web interface**: Navigate to `http://localhost:3000`
2. **Upload a document**: Supported formats include PDF, EPUB, TXT
3. **Select voice options**: Choose from available TTS voices
4. **Start conversion**: Click convert and wait for processing
5. **Download audiobook**: Get your M4B or MP3 file

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/convert` | POST | Upload and convert document |
| `/api/status/{job_id}` | GET | Check conversion progress |
| `/api/download/{job_id}` | GET | Download completed audiobook |
| `/api/voices` | GET | List available voices |

## Configuration

### Backend Configuration

Edit environment variables in `docker-compose.yml`:

```yaml
environment:
  - MLX_MODEL_PATH=/app/models
  - MAX_CONCURRENT_JOBS=2
  - OUTPUT_FORMAT=m4b
```

### Frontend Configuration

Create `.env` in `frontend/`:

```env
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000/ws
```

## Development

### Backend Development

```bash
cd voxcraft/backend
uvicorn main:app --reload --port 8000
```

### Frontend Development

```bash
cd voxcraft/frontend
npm start
```

## Data Storage

- **Uploads**: `data/uploads/`
- **Processed Audio**: `data/output/`
- **Cache**: `data/cache/`

## Troubleshooting

### "Cannot connect to backend"

- Ensure Docker containers are running: `docker-compose ps`
- Check backend logs: `docker-compose logs backend`
- Verify ports 3000 and 8000 are available

### "MLX not found"

VoxCraft requires Apple Silicon (M1/M2/M3) for MLX TTS. On non-Apple hardware, the converter will fall back to CPU processing.

### Frontend build fails

```bash
cd voxcraft/frontend
rm -rf node_modules package-lock.json
npm install
npm run build
```

## Production Deployment

```bash
cd voxcraft

# Build production images
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Or use the start script
./start.sh
```

## Technology Stack

- **Backend**: Python, FastAPI, MLX, Uvicorn
- **Frontend**: React, JavaScript/TypeScript, modern CSS
- **Container**: Docker, Docker Compose
- **TTS Engine**: MLX TTS (Apple Silicon optimized)

## License

MIT License - See parent project for details.

## Contributing

This is part of the Audiobook Converter Suite. Please refer to the main project README for contribution guidelines.
