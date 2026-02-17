#!/bin/bash
# Start VoxCraft in development mode on macOS

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_PATH="$PROJECT_ROOT/.venv/bin/activate"

if [ ! -f "$VENV_PATH" ]; then
  echo "❌ Virtual environment not found at $VENV_PATH"
  echo "Create it with: python3 -m venv .venv"
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "❌ npm is not installed or not in PATH"
  exit 1
fi

free_port() {
  local port="$1"
  local pids

  pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  if [ -z "$pids" ]; then
    return
  fi

  echo "⚠️  Port $port is in use. Stopping process(es): $pids"
  kill $pids 2>/dev/null || true
  sleep 1

  pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  if [ -n "$pids" ]; then
    echo "⚠️  Force-killing process(es) on port $port: $pids"
    kill -9 $pids 2>/dev/null || true
  fi
}

echo "🐍 Activating virtual environment..."
# shellcheck disable=SC1090
source "$VENV_PATH"

# Local dev defaults
export VOXCRAFT_DEPLOYMENT_MODE=local
export VOXCRAFT_LICENSE_REQUIRED=false
export VOXCRAFT_DEFAULT_ENGINE=openai

# Avoid 'address already in use' during restarts
free_port 8000
free_port 5173

cd "$SCRIPT_DIR"

echo "🚀 Starting VoxCraft development servers..."
echo "   Backend:  http://localhost:8000"
echo "   Frontend: http://localhost:5173"
echo ""

npm run dev
