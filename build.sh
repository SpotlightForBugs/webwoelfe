#!/bin/bash
# Pre-deployment build script
# Builds all TypeScript modules before starting the server

echo "[BUILD] Running pre-deployment build..."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "[WARN] Node.js not found, skipping TypeScript build"
    exit 0
fi

# Check if npm dependencies are installed
if [ ! -d "node_modules" ]; then
    echo "[PKG] Installing npm dependencies..."
    npm install
fi

# Build TypeScript modules
echo "[BUILD] Building TypeScript modules..."
npm run build

if [ $? -eq 0 ]; then
    echo "[OK] TypeScript build completed successfully"
else
    echo "[ERROR] TypeScript build failed"
    exit 1
fi

echo "[DONE] Pre-deployment build completed!"
