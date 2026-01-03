#!/bin/bash
# ============================================================================
# Webwölfe - Game Setup Script
# ============================================================================
# Spawns multiple browser windows, auto-creates a game, and stays open for testing
#
# Usage: ./game_setup.sh <number_of_players>
#        ./game_setup.sh 8          # Creates a game with 8 players
#        ./game_setup.sh 15         # Creates a game with 15 players
#
# Requirements:
# - Node.js installed
# - Playwright installed (npx playwright install chromium)
# - Flask app running on localhost:5000
# ============================================================================

set -e

# Default to 8 players if not specified
PLAYERS=${1:-8}

if [ "$PLAYERS" -lt 5 ]; then
    echo "⚠️  Mindestens 5 Spieler benötigt. Setze auf 5."
    PLAYERS=5
fi

echo "🐺 Webwölfe - Game Setup"
echo "========================"
echo "Spieleranzahl: $PLAYERS"
echo ""

# Check if Flask app is running, start it if not
SERVER_PID=""
PORT=5001
if ! curl -s http://localhost:$PORT > /dev/null 2>&1; then
    echo "🚀 Starte Flask-Server auf Port $PORT..."
    
    # Aktiviere venv falls vorhanden
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    fi
    
    # Starte Server im Hintergrund mit gevent
    export FLASK_APP=app.py
    export FLASK_ENV=development
    export PORT=$PORT
    python app.py &
    SERVER_PID=$!
    
    # Warte bis Server bereit ist
    echo -n "   Warte auf Server"
    for i in {1..30}; do
        if curl -s http://localhost:$PORT > /dev/null 2>&1; then
            echo ""
            echo "✓ Flask-Server gestartet (PID: $SERVER_PID)"
            break
        fi
        echo -n "."
        sleep 0.5
    done
    
    if ! curl -s http://localhost:$PORT > /dev/null 2>&1; then
        echo ""
        echo "❌ Flask-Server konnte nicht gestartet werden"
        exit 1
    fi
else
    echo "✓ Flask-App läuft bereits auf Port $PORT"
fi

# Cleanup-Funktion um Server zu beenden
cleanup() {
    if [ -n "$SERVER_PID" ]; then
        echo ""
        echo "🛑 Beende Flask-Server (PID: $SERVER_PID)..."
        kill $SERVER_PID 2>/dev/null || true
    fi
}
trap cleanup EXIT

# Check if Playwright is installed
if ! command -v npx &> /dev/null; then
    echo "❌ npx nicht gefunden. Installiere Node.js"
    exit 1
fi

# Run the Playwright setup script
echo ""
echo "🚀 Starte Browser-Fenster..."
echo ""

PLAYERS=$PLAYERS npx playwright test tests/game_setup.spec.ts --headed --timeout=0
