#!/bin/bash

# delete the db file to start fresh (only in development, not in Docker/production)
if [ -z "$DOCKER_CONTAINER" ] && [ -z "$COOLIFY_DEPLOYMENT" ]; then
    if [ -f "instance/webwoelfe.db" ]; then
        rm instance/webwoelfe.db
        echo "[CLEAN] Alte Datenbankdatei gelöscht (Development Mode)"
    fi
else
    echo "[INFO] Production/Docker Mode: Datenbankdatei wird beibehalten"
fi

# operating system aware venv activation
if [ -f ".venv/Scripts/activate" ]; then
    # Windows
    source .venv/Scripts/activate
elif [ -f "venv/bin/activate" ]; then
    # Unix/Linux/MacOS
    source venv/bin/activate
fi



# Check if Flask app is running, start it if not
SERVER_PID=""
PORT=5001
if ! curl -s http://localhost:$PORT > /dev/null 2>&1; then
    echo "[START] Starte Flask-Server auf Port $PORT..."
    
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
        echo "[ERROR] Flask-Server konnte nicht gestartet werden"
        exit 1
    fi
else
    echo "✓ Flask-App läuft bereits auf Port $PORT"
fi

# Cleanup-Funktion um Server zu beenden
cleanup() {
    if [ -n "$SERVER_PID" ]; then
        echo ""
        echo "[STOP] Beende Flask-Server (PID: $SERVER_PID)..."
        kill $SERVER_PID 2>/dev/null || true
    fi
}
trap cleanup EXIT

# Keep script running - wait for the server process
if [ -n "$SERVER_PID" ]; then
    echo "[INFO] Server läuft auf http://localhost:$PORT"
    echo "   Drücke Ctrl+C zum Beenden..."
    wait $SERVER_PID
fi
