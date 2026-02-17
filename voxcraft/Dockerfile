# Stage 1: Build frontend
FROM node:20-slim AS frontend-build

WORKDIR /app/frontend
COPY voxcraft/frontend/package.json voxcraft/frontend/package-lock.json* ./
RUN npm ci

COPY voxcraft/frontend/ .
RUN npm run build

# Stage 2: Python runtime
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for audio processing
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg libsndfile1 && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY voxcraft/backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend code
COPY voxcraft/backend/ backend/
COPY src/mlx_tts_engine.py .

# Copy built frontend as static files
COPY --from=frontend-build /app/frontend/dist static/

# Create data directories
RUN mkdir -p data/uploads data/audio data/projects

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
