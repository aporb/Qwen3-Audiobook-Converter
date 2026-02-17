#!/bin/bash
# VoxCraft — Local Development Start
cd "$(dirname "$0")"

# Install frontend dependencies if needed
if [ ! -d "frontend/node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm run install:all
fi

# Install root dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing root dependencies..."
    npm install
fi

npm run dev
