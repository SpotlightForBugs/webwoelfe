# Webwölfe - Automated Playwright Tests

This directory contains comprehensive Playwright-based automated tests for the Webwölfe game. These tests simulate complete game scenarios with multiple players to ensure the game mechanics work correctly.

## Test Overview

### Test Files

1. **game1-village-victory.spec.ts** - Village Victory Scenario
   - 5 players join a game
   - Tests the complete game flow from lobby through victory
   - Village identifies and eliminates all werewolves
   - Comprehensive assertions on game phases and player roles

2. **game2-werewolf-victory.spec.ts** - Werewolf Victory Scenario
   - 6 players test werewolf victory conditions
   - Tests strategic attacking by werewolves
   - Includes an 8-player large game test
   - Verifies role distribution for different player counts

### Test Helpers

**helpers/game-helpers.ts** - Comprehensive helper functions for game automation:

- `createRoom()` - Creates a new game room
- `joinRoom()` - Joins an existing game room
- `startGame()` - Starts the game from the lobby
- `getPlayerRole()` - Gets the current player's role
- `getAllPlayerRoles()` - Gets all players' roles
- `vote()` - Players vote during day phase
- `werewolfAttack()` - Werewolves select their target
- `seerSee()` - Seer examines a player
- `witchHeal()` / `witchPoison()` - Witch's special actions
- `skipAction()` - Players pass their turn
- `isPlayerDead()` - Checks if a player is dead
- `isGameOver()` - Checks if game has ended
- `getCurrentPhase()` - Gets the current game phase
- `cleanup()` - Cleans up browser contexts

## Running the Tests

### Prerequisites

- Python 3.x with Flask and dependencies (see requirements.txt)
- Node.js with npm
- Virtual environment activated (source venv/bin/activate)

### Run All Tests

```bash
npm test
# or
./run-tests.sh
```

### Run Specific Test

```bash
npm run test:game1    # Run village victory game
npm run test:game2    # Run werewolf victory game
```

### Run in Headed Mode (see browser)

```bash
npm run test:headed
```

### Debug Mode

```bash
npm run test:debug    # Opens interactive debug mode
npm run test:ui       # Opens Playwright UI
```

### View Test Report

```bash
npm run test:report   # Shows the last test report
```

## Test Architecture

### Game Flow

Each test simulates a complete game:

1. **Lobby Phase** - Players join and wait for game start
2. **Role Distribution** - Game assigns roles based on player count
3. **Night Phase** - Werewolves attack, special roles act
4. **Day Phase** - Voting to eliminate a player
5. **End Condition** - Game ends when one team wins

### Multi-Browser Testing

Tests use multiple browser contexts (one per player) to simulate:

- Independent player actions
- Parallel decision-making
- Socket.io communication between players
- Real-time game state updates

### Configuration

**playwright.config.ts**:

- Base URL: `http://localhost:5001`
- Auto-starts Flask server before tests
- Single worker (tests must be sequential due to shared game state)
- Screenshots/videos on failure
- 2-minute timeout per test
- HTML reporter

## Game Test Scenarios

### Game 1: Village Victory (5 Players)

**Players**: Anna, Bernd, Clara, David, Emma

**Typical Role Distribution**:

- Werewolves: ~2
- Seer/Witch/Special Roles: ~2
- Village Dwellers: ~1

**Victory Condition**: Village eliminates all werewolves before they achieve majority.

### Game 2: Werewolf Victory (6 Players)

**Players**: Friedrich, Greta, Hans, Inge, Johann, Klara

**Test Strategy**: Werewolves strategically eliminate key targets (Seer, Witch) to achieve majority.

### Game 2B: Large Game (8 Players)

Tests role distribution scaling and game stability with more players.

## Debugging Failed Tests

### View Screenshots

Failed test screenshots are saved in:

```
test-results/[test-name]/test-failed-1.png
```

### View Videos

Videos of failed tests (if enabled):

```
test-results/[test-name]/video.webm
```

### Enable Trace

Add to test:

```typescript
test.use({ trace: "on" });
```

View trace with:

```bash
npx playwright show-trace test-results/[test-name]/trace.zip
```

### Common Issues

1. **Database Schema Mismatch**
   - Solution: Delete webwoelfe.db and instance/webwoelfe.db
   - Server will recreate with current schema

2. **Server Not Starting**
   - Check Python virtual environment is activated
   - Verify Flask dependencies: `pip list | grep Flask`

3. **Timeout Errors**
   - Game phases may take longer on slow systems
   - Adjust timeout in playwright.config.ts: `timeout: 120000`

4. **Socket Connection Issues**
   - Ensure server is running on port 5001
   - Check network connectivity between test browsers and server

## Performance Notes

- Each test takes 10-30 seconds depending on game complexity
- Parallel tests not recommended (shared game state)
- Memory usage: ~200-400MB per test run
- CPU: Moderate due to browser automation

## Extending Tests

To add new game scenarios:

1. Create new `.spec.ts` file in `tests/` directory
2. Import helpers from `./helpers/game-helpers`
3. Follow the pattern:

   ```typescript
   test.describe("Game X: New Scenario", () => {
     let players: Player[] = [];

     test.afterEach(async () => {
       await cleanup(players);
     });

     test("scenario description", async ({ browser }) => {
       // Your test code
     });
   });
   ```

4. Run with: `npx playwright test gameX`

## CI/CD Integration

For GitHub Actions or similar CI systems:

```yaml
- name: Run Playwright tests
  run: |
    source venv/bin/activate
    npm test

- name: Upload results
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: playwright-report
    path: playwright-report/
```

## Maintenance

- Tests should be run after any game logic changes
- Update tests when adding new roles or phases
- Monitor test execution time for performance regressions
- Review logs when game behavior changes

## Contact & Issues

Report issues with tests in the project repository. Include:

- Test name and error message
- Screenshot/video if available
- System information (OS, Python version, Node version)
- Browser console logs (visible in debug mode)
