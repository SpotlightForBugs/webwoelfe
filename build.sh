#!/bin/bash
# Pre-deployment build script
# Builds all TypeScript modules before starting the server

echo "🔧 Running pre-deployment build..."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "⚠️  Node.js not found, skipping TypeScript build"
    exit 0
fi

# Check if npm dependencies are installed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing npm dependencies..."
    npm install
fi

# Build TypeScript modules
echo "🏗️  Building TypeScript modules..."
npm run build

if [ $? -eq 0 ]; then
    echo "✅ TypeScript build completed successfully"
else
    echo "❌ TypeScript build failed"
    exit 1
fi

echo "✨ Pre-deployment build completed!"
