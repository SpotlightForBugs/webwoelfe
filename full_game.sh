#!/bin/bash
# ============================================================================
# Webwölfe - Full Game Simulation Script (RANDOM MODE)
# ============================================================================
# Spawns multiple browser windows, auto-creates a game, and simulates
# an entire game with RANDOM actions for edge case discovery.
#
# Usage: ./full_game.sh <number_of_players> [--hl] [--seed=SEED]
#        ./full_game.sh 8              # Simulates a game with 8 players
#        ./full_game.sh 15             # Simulates a game with 15 players
#        ./full_game.sh 8 --hl         # 8 players, only one window visible
#        ./full_game.sh 8 --seed=12345 # Reproducible run with specific seed
#
# Options:
#   --hl           Headless mode for all players except the first window
#   --seed=SEED    Use specific random seed for reproducibility
#
# Random Behaviors for Edge Case Discovery:
#   - 20% chance to skip actions (test timeout handling)
#   - 10% chance to target dead/invalid players
#   - 5% chance to try self-targeting
#   - 10% chance to attempt duplicate actions
#   - 40% chance for completely random voting
#
#
# Requirements:
# - Node.js installed
# - Playwright installed (npx playwright install chromium)
# - Flask app running on localhost:5001
# ============================================================================

set -e

# Parse arguments
PLAYERS=""
HL_FLAG=""
SEED=""
PORT=5001

# ============================================================================
# KILL EXISTING PROCESSES
# ============================================================================
echo "🔪 Beende laufende Prozesse..."

# Kill any existing Python/Flask processes on our port
kill_by_port() {
    local port=$1
    echo "   Pruefe Port $port..."
    
    if command -v lsof &> /dev/null; then
        # Unix/Linux/MacOS
        EXISTING_PIDS=$(lsof -ti:$port 2>/dev/null || true)
        if [ -n "$EXISTING_PIDS" ]; then
            echo "   Beende Prozesse auf Port $port: $EXISTING_PIDS"
            echo "$EXISTING_PIDS" | xargs kill -9 2>/dev/null || true
        fi
    elif command -v netstat &> /dev/null; then
        # Windows (Git Bash)
        # Find PIDs listening on the port. 
        # Output format: TCP 0.0.0.0:5001 0.0.0.0:0 LISTENING 12345
        # We extract the last column (PID)
        PIDS=$(netstat -ano | grep ":$port " | grep "LISTENING" | awk '{print $NF}' | sort -u | tr -d '\r')
        
        for pid in $PIDS; do
            if [ -n "$pid" ] && [ "$pid" != "0" ]; then
                echo "   Beende Windows-Prozess PID $pid auf Port $port"
                taskkill //F //PID "$pid" 2>/dev/null || true
            fi
        done
    fi
}

kill_by_port $PORT

# Additional cleanup for python processes if port check failed
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    # Windows
    taskkill //F //IM "python.exe" //FI "WINDOWTITLE eq app.py" 2>/dev/null || true
else
    # Unix
    pkill -f "python.*app.py" 2>/dev/null || true
fi

echo "✓ Bestehende Prozesse beendet"

# delete the db file to start fresh
if [ -f "instance/webwoelfe.db" ]; then
    rm instance/webwoelfe.db
    echo "🗑️  Alte Datenbankdatei gelöscht"
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
        --seed=*)
            SEED="${arg#*=}"
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

echo ""
echo "🐺 Webwölfe - Full Game Simulation (RANDOM MODE)"
echo "==================================="
echo "Spieleranzahl: $PLAYERS"
if [ -n "$SEED" ]; then
    echo "Random Seed: $SEED"
fi
echo ""

# Check if Flask app is running, start it if not
SERVER_PID=""
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

# Cleanup-Funktion um Server und Browser zu beenden
cleanup() {
    echo ""
    echo "🛑 Räume auf..."

    if [ -n "$SERVER_PID" ]; then
        echo "   Beende Flask-Server (PID: $SERVER_PID / Port: $PORT)..."
        # Try graceful kill of wrapper first
        kill $SERVER_PID 2>/dev/null || true
        # Ensure deep kill by port (handles Windows python.exe)
        kill_by_port $PORT
    fi

    # Kill any remaining Chromium/Playwright processes
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        taskkill //F //IM "chromium.exe" 2>/dev/null || true
        taskkill //F //IM "chrome.exe" 2>/dev/null || true
        taskkill //F //IM "node.exe" 2>/dev/null || true
    else
        pkill -f "chromium" 2>/dev/null || true
        pkill -f "playwright" 2>/dev/null || true
    fi

    echo "✓ Alle Prozesse beendet"
}
trap cleanup EXIT INT TERM

# Check if Playwright is installed
if ! command -v npx &> /dev/null; then
    echo "❌ npx nicht gefunden. Installiere Node.js"
    exit 1
fi

# Run the Playwright full game simulation script
echo ""
echo "🚀 Starte Browser-Fenster und Spielsimulation..."
if [ -n "$HL_FLAG" ]; then
    echo "   (Headless-Modus: Ein Fenster sichtbar, Rest headless)"
fi


PLAYERS=$PLAYERS HL=$HL_FLAG SEED=$SEED npx playwright test tests/full_game.spec.ts --headed --timeout=0

