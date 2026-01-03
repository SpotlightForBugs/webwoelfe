#!/bin/bash

# Run the server in development mode with auto-reload on port 8888

set -e
export FLASK_APP=app.py
export FLASK_ENV=development
export PORT=8888
if [ -d "venv" ]; then
  source venv/bin/activate
else
  echo "Warning: No virtual environment found, continuing without activation..."
fi

# clear old database files
echo "Cleaning old database files..."
rm -f webwoelfe.db instance/webwoelfe.db 2>/dev/null || true
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

python app.py
if [ -d "venv" ]; then
  deactivate
fi
