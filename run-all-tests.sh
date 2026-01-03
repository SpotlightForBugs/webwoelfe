#!/bin/bash
# Führe alle Tests für Webwölfe aus

echo "=================================="
echo "Webwölfe Test Suite"
echo "=================================="
echo ""

# Prüfe ob python3 verfügbar ist
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 nicht gefunden!"
    exit 1
fi

# Aktiviere virtuelle Umgebung falls vorhanden
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✓ Virtuelle Umgebung aktiviert"
fi

# Installiere Abhängigkeiten falls nötig
echo ""
echo "Prüfe Abhängigkeiten..."
pip3 install -q python-dotenv 2>/dev/null

# Führe Tests aus
echo ""
echo "=================================="
echo "1. Rollen-Tests"
echo "=================================="
python3 -m pytest tests/test_all_roles.py -v --tb=short 2>/dev/null || python3 tests/test_all_roles.py

echo ""
echo "=================================="
echo "2. Spiellogik-Tests"
echo "=================================="
python3 -m pytest tests/test_game_logic_full_cycle.py -v --tb=short 2>/dev/null || python3 -m unittest tests.test_game_logic_full_cycle -v

echo ""
echo "=================================="
echo "3. Phasen-Mapping-Tests"
echo "=================================="
python3 -m pytest tests/test_dynamic_phase_mapping.py -v --tb=short 2>/dev/null || python3 -m unittest tests.test_dynamic_phase_mapping -v

echo ""
echo "=================================="
echo "Alle Tests abgeschlossen!"
echo "=================================="
