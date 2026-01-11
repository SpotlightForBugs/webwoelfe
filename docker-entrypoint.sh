#!/bin/sh
set -e

# Ensure FLASK_APP is set for Flask CLI
export FLASK_APP=${FLASK_APP:-app.py}

echo "Applying database migrations (if any)..."
if command -v flask >/dev/null 2>&1; then
  if flask db upgrade; then
    echo "Database migrations applied."
  else
    echo "No migrations to apply or migration step failed; continuing."
  fi
else
  echo "Flask CLI not found; skipping migrations."
fi

# Execute the main container command (Gunicorn)
exec "$@"
