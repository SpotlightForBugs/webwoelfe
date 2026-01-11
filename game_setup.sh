#!/bin/bash
# ============================================================================
# Webwölfe - Game Setup Script
# ============================================================================
# Spawns multiple browser windows, auto-creates a game, and stays open for testing
#
# Usage: ./game_setup.sh <number_of_players> [--hl]
#        ./game_setup.sh 8          # Creates a game with 8 players
#        ./game_setup.sh 15         # Creates a game with 15 players
#        ./game_setup.sh 8 --hl     # 8 players, only one window visible
#
# Options:
#   --hl    Headless mode for all players except the first window
#
# Requirements:
# - Node.js installed
# - Playwright installed (npx playwright install chromium)
# - Flask app running on localhost:5000
# ============================================================================

set -e

# Parse arguments
PLAYERS=""
HL_FLAG=""

# delete the db file to start fresh (only in development, not in Docker/production)
if [ -z "$DOCKER_CONTAINER" ] && [ -z "$COOLIFY_DEPLOYMENT" ]; then
    if [ -f "instance/webwoelfe.db" ]; then
        rm instance/webwoelfe.db
        echo "🗑️  Alte Datenbankdatei gelöscht (Development Mode)"
    fi
else
    echo "📦 Production/Docker Mode: Datenbankdatei wird beibehalten"
fi

# Build TypeScript if node_modules exists
if [ -d "node_modules" ]; then
    echo "🔨 Building TypeScript modules..."
    npm run build
    if [ $? -ne 0 ]; then
        echo "⚠️  TypeScript build failed, continuing anyway..."
    else
        echo "✅ TypeScript build completed"
    fi
elif command -v npm &> /dev/null; then
    echo "📦 Installing npm dependencies and building..."
    npm install && npm run build
else
    echo "⚠️  Node.js/npm not found, skipping TypeScript build"
fi

# operating system aware venv activation
if [ -f ".venv/Scripts/activate" ]; then
    # Windows
    source .venv/Scripts/activate
elif [ -f "venv/bin/activate" ]; then
    # Unix/Linux/MacOS
    source venv/bin/activate
fi


for arg in "$@"; do
    case $arg in
        --hl)
            HL_FLAG="1"
            ;;
        *)
            if [ -z "$PLAYERS" ]; then
                PLAYERS="$arg"
            fi
            ;;
    esac
done

# Default to 8 players if not specified
PLAYERS=${PLAYERS:-8}

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
    export FLASK_DEBUG=1
    export PORT=$PORT
    # Auto-create database tables since we delete the db file for fresh tests
    export AUTO_DB_CREATE_ALL=1
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
if [ -n "$HL_FLAG" ]; then
    echo "   (Headless-Modus: Ein Fenster sichtbar, Rest headless)"
fi
echo ""

PLAYERS=$PLAYERS HL=$HL_FLAG npx playwright test tests/game_setup.spec.ts --headed --timeout=0
