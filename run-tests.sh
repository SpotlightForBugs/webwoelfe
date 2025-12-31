#!/bin/bash

# Run Playwright tests for Webwölfe game
# This script activates the virtual environment and runs the tests
# Usage: ./run-tests.sh [0|1|2|3|all] [--keep] [--delay N]  
#   0 = Setup only (creates game, doesn't play)
#   1 = Game 1 (Village Victory)
#   2 = Game 2 (Werewolf Victory)
#   3 = Werewolf Vote (focused voting test)
#   all = Run everything except 0 (default)
#   --keep = Keep browser open when tests complete
#   --delay N = Delay N seconds between actions (default: 0)

set -e

# Show help function
show_help() {
  echo "Usage: ./run-tests.sh [OPTIONS] [TEST_TYPE]"
  echo ""
  echo "TEST_TYPE:"
  echo "  0         Setup only (creates game, doesn't play)"
  echo "  1         Game 1 (Village Victory)"
  echo "  2         Game 2 (Werewolf Victory)"
  echo "  3         Werewolf Vote (focused voting test)"
  echo "  500       Massive Player Full Game Test (default: 100 players)"
  echo "  stress    Wizard + Mass Player Stress Tests"
  echo "  all       Run everything except 0 (default)"
  echo ""
  echo "OPTIONS:"
  echo "  -h, --help   Show this help message"
  echo "  --keep       Keep browser open when tests complete"
  echo "  --delay N    Delay N seconds between actions (default: 0)"
  echo "  -n N         Number of players for 500 test (default: 100, max recommended: 200)"
  exit 0
}

# Activate virtual environment
# Check multiple possible venv locations for cross-platform compatibility
if [ -f ".venv/Scripts/activate" ]; then
  source .venv/Scripts/activate
elif [ -f ".venv/bin/activate" ]; then
  source .venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
  source venv/Scripts/activate
elif [ -f "venv/bin/activate" ]; then
  source venv/bin/activate
else
  echo "Warning: No virtual environment found, continuing without activation..."
fi
# Parse arguments
KEEP_OPEN=false
DELAY=0
TEST_TYPE="all"
PLAYER_COUNT=100

for arg in "$@"; do
  case $arg in
    -h|--help)
      show_help
      ;;
    0|1|2|3|500|stress|all)
      TEST_TYPE="$arg"
      ;;
    --keep)
      KEEP_OPEN=true
      ;;
    --delay|-n)
      # Next iteration will have the value
      ;;
    *)
      # Check if the previous argument was --delay or -n
      if [ "$prev_arg" = "--delay" ]; then
        DELAY="$arg"
      elif [ "$prev_arg" = "-n" ]; then
        PLAYER_COUNT="$arg"
      fi
      ;;
  esac
  prev_arg="$arg"
done

# Flag 0 (setup) always keeps browser open for inspection
if [ "$TEST_TYPE" == "0" ]; then
  KEEP_OPEN=true
fi

# Clear old database files to ensure fresh test data
echo "Cleaning old database files..."
rm -f webwoelfe.db instance/webwoelfe.db 2>/dev/null || true
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Kill stale Flask processes
echo "Killing stale Flask processes..."
pkill -f "flask run" 2>/dev/null || true
pkill -f "python.*app.py" 2>/dev/null || true
pkill -f "gunicorn" 2>/dev/null || true

# Convert delay from seconds to milliseconds
DELAY_MS=$((DELAY * 1000))

# Set environment variables for tests
export TEST_KEEP_OPEN=$KEEP_OPEN
export TEST_ACTION_DELAY=$DELAY_MS

# Run tests with optional filter
if [ "$TEST_TYPE" == "0" ]; then
  echo "Starting Playwright tests for Setup Only (Game creation without gameplay)..."
  echo "Note: Browser will stay open for inspection (flag 0 always keeps open)"
  npx playwright test game-setup
elif [ "$TEST_TYPE" == "1" ]; then
  echo "Starting Playwright tests for Game 1 (Village Victory)..."
  [ "$KEEP_OPEN" = true ] && echo "Browser will stay open when tests complete"
  if [ "$DELAY" != "0" ]; then echo "Action delay: ${DELAY}s"; fi
  npx playwright test game1-village
elif [ "$TEST_TYPE" == "2" ]; then
  echo "Starting Playwright tests for Game 2 (Werewolf Victory)..."
  [ "$KEEP_OPEN" = true ] && echo "Browser will stay open when tests complete"
  if [ "$DELAY" != "0" ]; then echo "Action delay: ${DELAY}s"; fi
  npx playwright test game2-werewolf
elif [ "$TEST_TYPE" == "3" ]; then
  echo "Starting Playwright tests for Werewolf Vote (Focused Voting Test)..."
  [ "$KEEP_OPEN" = true ] && echo "Browser will stay open when tests complete"
  if [ "$DELAY" != "0" ]; then echo "Action delay: ${DELAY}s"; fi
  npx playwright test werewolf-vote
elif [ "$TEST_TYPE" == "500" ]; then
  echo "=== MASSIVE PLAYER TEST ==="
  echo "$PLAYER_COUNT players ($((PLAYER_COUNT - 1)) headless + 1 headful)"
  echo "This may take a while..."
  [ "$KEEP_OPEN" = true ] && echo "Browser will stay open when tests complete"
  PLAYER_COUNT=$PLAYER_COUNT npx playwright test massive-500-full-game --project=massive --timeout=1800000 --reporter=line
elif [ "$TEST_TYPE" == "stress" ]; then
  echo "=== STRESS TESTS (Wizard + Mass Players) ==="
  [ "$KEEP_OPEN" = true ] && echo "Browser will stay open when tests complete"
  npx playwright test massive-500-players --timeout=300000 --reporter=line
else
  echo "Starting Playwright tests (skipping setup)..."
  [ "$KEEP_OPEN" = true ] && echo "Browser will stay open when tests complete"
  if [ "$DELAY" != "0" ]; then echo "Action delay: ${DELAY}s"; fi
  # Run all tests EXCEPT game-setup (test 0): includes game1, game2, and werewolf-vote
  npx playwright test --grep "Village|Werewolf"
fi
