#!/bin/bash
# Start VoxCraft in development mode on macOS

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
VENV_PATH="$PROJECT_ROOT/.venv/bin/activate"

# Check if virtual environment exists
if [ ! -f "$VENV_PATH" ]; then
    echo "❌ Virtual environment not found at $VENV_PATH"
    echo "Please create it first: python3 -m venv .venv"
    exit 1
fi

# Activate virtual environment
echo "🐍 Activating virtual environment..."
source "$VENV_PATH"

# Set environment variables for local dev (no license required)
export VOXCRAFT_DEPLOYMENT_MODE=local
export VOXCRAFT_LICENSE_REQUIRED=false
export VOXCRAFT_DEFAULT_ENGINE=openai

# Optional: Set OpenAI API key if you have one
# export OPENAI_API_KEY="your-key-here"

cd "$SCRIPT_DIR"

echo "🚀 Starting VoxCraft development servers..."
echo "   Backend: http://localhost:8000"
echo "   Frontend: http://localhost:5173"
echo ""

# Run both backend and frontend concurrently
npm run dev
