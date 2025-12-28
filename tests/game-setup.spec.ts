import { test, expect, Browser } from "@playwright/test";
import {
  Player,
  createRoom,
  joinRoom,
  startGame,
  waitForGameStart,
  getPlayerRole,
  getAllPlayerRoles,
  cleanup,
  resetWindowPositions,
  logEvent,
  waitIfKeepOpen,
} from "./helpers/game-helpers";

/**
 * GAME SETUP ONLY
 *
 * This test creates a game and gets all players into the game page,
 * then stops without playing any rounds. Useful for:
 * - Testing game creation and role distribution
 * - Verifying socket connections
 * - Debugging game state before gameplay
 */
test.describe("Game Setup Only - No Gameplay", () => {
  let players: Player[] = [];
  let roomCode: string;

  test.afterEach(async () => {
    await cleanup(players);
    players = [];
  });

  test("5 players join game and roles are distributed", async ({ browser }) => {
    const playerNames = ["Alice", "Bob", "Charlie", "Diana", "Eve"];

    // Reset window positions for tiling
    resetWindowPositions();

    logEvent("SETUP", "Creating game room");

    // Step 1: Create the game room
    const { player: creator, roomCode: code } = await createRoom(
      browser,
      playerNames[0],
      "Setup Test Game",
      5,
      true,
      "online",
    );
    roomCode = code;
    players.push(creator);
    logEvent("SETUP", `Room created`, `Code: ${roomCode}`);

    // Step 2: Other players join the room
    logEvent("SETUP", "Other players joining");
    for (let i = 1; i < playerNames.length; i++) {
      const player = await joinRoom(browser, roomCode, playerNames[i]);
      players.push(player);
      logEvent("SETUP", `${playerNames[i]} joined`);
      await player.page.waitForTimeout(500);
    }

    // Step 3: Wait for all players to be visible in lobby
    logEvent("SETUP", "Verifying all players in lobby");
    for (const player of players) {
      for (const name of playerNames) {
        await expect(player.page.locator(`text=${name}`)).toBeVisible({
          timeout: 10000,
        });
      }
    }
    logEvent("SUCCESS", "All players visible in lobby");

    // Step 4: Start the game
    logEvent("SETUP", "Starting game");
    await startGame(players[0]);

    // Step 5: Wait for all players to be on the game page
    logEvent("SETUP", "Waiting for game to start for all players");
    await waitForGameStart(players);
    logEvent("SUCCESS", "All players on game page");

    // Step 6: Get all player roles
    logEvent("SETUP", "Getting player roles");
    const roleMap = await getAllPlayerRoles(players);
    console.log("Role distribution:");
    roleMap.forEach((role, name) => {
      console.log(`  ${name}: ${role}`);
    });
    logEvent("SUCCESS", "Roles assigned");

    // Verify all players have roles
    for (const player of players) {
      expect(player.role).toBeTruthy();
      logEvent("VERIFY", `${player.name} has role: ${player.role}`);
    }

    // Step 7: Just display the game state
    logEvent("INFO", "Game setup complete - stopping here without playing");
    console.log("\n=== GAME SETUP COMPLETE ===");
    console.log(`Room: ${roomCode}`);
    console.log(
      `Players: ${players.map((p) => `${p.name} (${p.role})`).join(", ")}`,
    );
    console.log("==============================\n");

    // Keep browser open for inspection based on --keep flag
    // For setup-only test (flag 0), always keep open for inspection
    await waitIfKeepOpen();
  });
});
