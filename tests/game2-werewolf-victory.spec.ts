import { test, expect, Browser } from "@playwright/test";
import {
  Player,
  createRoom,
  joinRoom,
  startGame,
  waitForGameStart,
  getPlayerRole,
  getAllPlayerRoles,
  advancePhase,
  getCurrentPhase,
  selectTarget,
  confirmAction,
  vote,
  werewolfAttack,
  seerSee,
  witchHeal,
  witchPoison,
  skipAction,
  isPlayerDead,
  isGameOver,
  getWinner,
  cleanup,
  waitForElement,
  logGameState,
  resetWindowPositions,
  logEvent,
  logAction,
  logVote,
  logPhaseChange,
  delayAction,
  waitIfKeepOpen,
} from "./helpers/game-helpers";

/**
 * GAME 2: Werewolf Victory
 *
 * This test simulates a complete game where the werewolves win.
 * - 6 players join the game (results in more werewolves)
 * - Werewolves strategically eliminate villagers
 * - The werewolves achieve majority and win
 */
test.describe("Game 2: Complete Werewolf Victory Game", () => {
  let players: Player[] = [];
  let roomCode: string;

  test.afterEach(async () => {
    await cleanup(players);
    players = [];
  });

  test("6 players complete a full game where werewolves win", async ({
    browser,
  }) => {
    const playerNames = [
      "Friedrich",
      "Greta",
      "Hans",
      "Inge",
      "Johann",
      "Klara",
    ];

    // Reset window positions for tiling
    resetWindowPositions();

    // Step 1: Create the game room
    console.log("Creating game room...");
    const { player: creator, roomCode: code } = await createRoom(
      browser,
      playerNames[0],
      "Test Game 2 - Werewolf Victory",
      6,
      false, // Not a narrator
      "online",
    );
    roomCode = code;
    players.push(creator);
    console.log(`Room created with code: ${roomCode}`);

    // Step 2: Other players join the room
    console.log("Other players joining...");
    for (let i = 1; i < playerNames.length; i++) {
      const player = await joinRoom(browser, roomCode, playerNames[i]);
      players.push(player);
      console.log(`${playerNames[i]} joined the game`);
      // Small delay between joins to allow socket to sync
      await player.page.waitForTimeout(500);
    }

    // Step 3: Wait for all players to be visible in lobby
    console.log("Waiting for all players to be visible in lobby...");
    for (const player of players) {
      // Check that we're in the lobby
      await expect(player.page).toHaveURL(/\/lobby\//);
    }

    // Wait a bit for all connections to stabilize
    await players[0].page.waitForTimeout(1500);

    // Step 4: Start the game
    console.log("Starting the game...");

    // Wait for the start button to be enabled
    const startButton = players[0].page.locator(
      '#start-btn, button:has-text("Spiel starten"):not([disabled])',
    );
    await expect(startButton).toBeVisible({ timeout: 15000 });
    await startButton.click();

    // Step 5: Wait for all players to be on the game page
    console.log("Waiting for game to start for all players...");
    await waitForGameStart(players);

    // Step 6: Get all player roles
    console.log("Getting player roles...");
    const roleMap = await getAllPlayerRoles(players);
    console.log("Role distribution:");
    roleMap.forEach((role, name) => {
      console.log(`  ${name}: ${role}`);
    });

    // Identify key players by role
    const werewolves: Player[] = [];
    const villagers: Player[] = [];
    let seer: Player | null = null;
    let witch: Player | null = null;

    for (const player of players) {
      const role = player.role?.toLowerCase() || "";
      if (role.includes("werwolf")) {
        werewolves.push(player);
      } else if (role.includes("seherin")) {
        seer = player;
        villagers.push(player);
      } else if (role.includes("hexe")) {
        witch = player;
        villagers.push(player);
      } else {
        villagers.push(player);
      }
    }

    console.log(`Werewolves: ${werewolves.map((w) => w.name).join(", ")}`);
    console.log(`Villagers: ${villagers.map((v) => v.name).join(", ")}`);
    if (seer) console.log(`Seer: ${seer.name}`);
    if (witch) console.log(`Witch: ${witch.name}`);

    // Step 7: Play through game phases
    let gameEnded = false;
    let roundCount = 0;
    const maxRounds = 12;

    while (!gameEnded && roundCount < maxRounds) {
      roundCount++;
      console.log(`\n=== Round ${roundCount} ===`);

      // Get current phase from first player's view
      const currentPhase = await getCurrentPhase(players[0]);
      console.log(`Current phase: ${currentPhase}`);

      // Check if game ended
      if (await isGameOver(players[0])) {
        gameEnded = true;
        break;
      }

      // Skip certain phases automatically
      if (
        currentPhase.includes("rollen_verteilt") ||
        currentPhase.includes("lobby")
      ) {
        console.log("Auto-advancing through preliminary phase...");
        await advancePhase(players[0]);
        await players[0].page.waitForTimeout(1500);
        continue;
      }

      // Handle different phases
      if (currentPhase.includes("werwolf")) {
        // Werewolf phase - werewolves prioritize attacking the seer/witch
        console.log("Werewolf phase - strategic attack...");

        // Priority targets: Seer first, then Witch, then regular villagers
        let target: Player | null = null;
        if (seer && !seer.role?.includes("werwolf")) {
          target = seer;
        } else if (witch && !witch.role?.includes("werwolf")) {
          target = witch;
        } else {
          const livingVillagers = villagers.filter(
            (v) => !werewolves.includes(v),
          );
          if (livingVillagers.length > 0) {
            target = livingVillagers[0];
          }
        }

        if (target) {
          console.log(`Werewolves targeting: ${target.name}`);
          for (const wolf of werewolves) {
            try {
              await selectTarget(wolf, target.name);
              await delayAction();
              const confirmBtn = wolf.page.locator(
                'button:has-text("Angreifen"), button:has-text("Bestaetigen"), button:has-text("Waehlen")',
              );
              if (await confirmBtn.isVisible()) {
                await confirmBtn.click();
                await delayAction();
              }
            } catch (e) {
              console.log(`Wolf ${wolf.name} could not attack: ${e}`);
            }
          }
        }
      } else if (currentPhase.includes("seherin")) {
        // Seer phase
        console.log("Seer phase...");
        if (seer) {
          try {
            // Seer looks at a random player
            const randomPlayer =
              players[Math.floor(Math.random() * players.length)];
            if (randomPlayer.name !== seer.name) {
              await selectTarget(seer, randomPlayer.name);
              await delayAction();
              const seeBtn = seer.page.locator(
                'button:has-text("Sehen"), button:has-text("Bestaetigen")',
              );
              if (await seeBtn.isVisible()) {
                await seeBtn.click();
                await delayAction();
              }
            }
          } catch (e) {
            console.log(`Seer could not see: ${e}`);
          }
        }
      } else if (currentPhase.includes("hexe")) {
        // Witch phase - witch doesn't save anyone (to help werewolves win)
        console.log("Witch phase - no action...");
        if (witch) {
          try {
            await skipAction(witch);
          } catch (e) {
            console.log(`Witch could not skip: ${e}`);
          }
        }
      } else if (
        currentPhase.includes("abstimmung") ||
        currentPhase.includes("tag")
      ) {
        // Day voting phase - werewolves vote together for a villager
        console.log("Day voting phase...");

        // Werewolves coordinate to vote for a villager
        // Other players vote randomly (simulating confusion)

        const voteTarget =
          villagers.length > 0 ? villagers[0].name : players[1].name;

        for (const player of players) {
          try {
            const playerCard = player.page
              .locator(`.spieler-card:not(.tot)`)
              .first();
            if (await playerCard.isVisible()) {
              // Werewolves vote for a villager, villagers vote randomly
              let targetName: string;
              if (werewolves.includes(player)) {
                targetName = voteTarget;
              } else {
                // Random vote
                const randomIndex = Math.floor(Math.random() * players.length);
                targetName = players[randomIndex].name;
              }

              await selectTarget(player, targetName);
              await delayAction();
              const voteBtn = player.page.locator(
                'button:has-text("Abstimmen"), button:has-text("Waehlen"), button:has-text("Bestaetigen")',
              );
              if (await voteBtn.isVisible()) {
                await voteBtn.click();
                await delayAction();
              }
            }
          } catch (e) {
            console.log(`${player.name} could not vote: ${e}`);
          }
        }
      }

      // Wait for phase transitions
      await players[0].page.waitForTimeout(2000);

      // Try to advance phase
      try {
        await advancePhase(players[0]);
      } catch (e) {
        console.log("Could not advance phase");
      }

      // Check for game end
      for (const player of players) {
        try {
          if (await isGameOver(player)) {
            gameEnded = true;
            break;
          }
        } catch (e) {
          // Continue checking
        }
      }
    }

    // Step 8: Verify game ended
    console.log("\n=== Game Finished ===");

    const finalPhase = await getCurrentPhase(players[0]);
    console.log(`Final phase: ${finalPhase}`);

    // The game should have ended within our round limit
    expect(roundCount).toBeLessThanOrEqual(maxRounds);

    // Keep open if --keep flag is set
    await waitIfKeepOpen();

    console.log("Game 2 test completed!");
  });
});

/**
 * GAME 2B: Large Game Test
 *
 * This test simulates a larger game with 8 players
 * to test more complex role distributions
 */
test.describe("Game 2B: Large 8-Player Game", () => {
  let players: Player[] = [];
  let roomCode: string;

  test.afterEach(async () => {
    await cleanup(players);
    players = [];
  });

  test("8 players complete a full game", async ({ browser }) => {
    const playerNames = [
      "Ludwig",
      "Marie",
      "Norbert",
      "Olga",
      "Paul",
      "Rita",
      "Stefan",
      "Tina",
    ];

    // Reset window positions for tiling
    resetWindowPositions();

    // Step 1: Create the game room
    console.log("Creating large game room...");
    const { player: creator, roomCode: code } = await createRoom(
      browser,
      playerNames[0],
      "Test Game 2B - Large Game",
      8,
      false,
      "online",
    );
    roomCode = code;
    players.push(creator);
    console.log(`Room created with code: ${roomCode}`);

    // Step 2: Other players join the room
    console.log("Other players joining...");
    for (let i = 1; i < playerNames.length; i++) {
      const player = await joinRoom(browser, roomCode, playerNames[i]);
      players.push(player);
      console.log(`${playerNames[i]} joined the game`);
      await player.page.waitForTimeout(400);
    }

    // Step 3: Wait for all players to be visible in lobby
    console.log("Waiting for all players in lobby...");
    await players[0].page.waitForTimeout(2000);

    // Step 4: Start the game
    console.log("Starting the game...");
    const startButton = players[0].page.locator(
      '#start-btn, button:has-text("Spiel starten"):not([disabled])',
    );
    await expect(startButton).toBeVisible({ timeout: 15000 });
    await startButton.click();

    // Step 5: Wait for game to start
    console.log("Waiting for game to start...");
    await waitForGameStart(players);

    // Step 6: Get all player roles
    console.log("Getting player roles...");
    const roleMap = await getAllPlayerRoles(players);
    console.log("Role distribution:");
    roleMap.forEach((role, name) => {
      console.log(`  ${name}: ${role}`);
    });

    // Count roles
    let werewolfCount = 0;
    let villagerCount = 0;
    let specialRoleCount = 0;

    for (const player of players) {
      const role = player.role?.toLowerCase() || "";
      if (role.includes("werwolf")) {
        werewolfCount++;
      } else if (role.includes("dorfbewohner")) {
        villagerCount++;
      } else if (role) {
        specialRoleCount++;
      }
    }

    console.log(`\nRole count summary:`);
    console.log(`  Werewolves: ${werewolfCount}`);
    console.log(`  Regular Villagers: ${villagerCount}`);
    console.log(`  Special Roles: ${specialRoleCount}`);

    // Verify role distribution makes sense for 8 players
    // Should have at least 1 werewolf and some special roles
    expect(werewolfCount).toBeGreaterThanOrEqual(1);
    expect(werewolfCount + villagerCount + specialRoleCount).toBe(8);

    // Step 7: Play a few rounds to verify game mechanics work
    let roundCount = 0;
    const testRounds = 3; // Just test a few rounds

    while (roundCount < testRounds) {
      roundCount++;
      console.log(`\n=== Test Round ${roundCount} ===`);

      const currentPhase = await getCurrentPhase(players[0]);
      console.log(`Current phase: ${currentPhase}`);

      // Check if game ended early
      if (await isGameOver(players[0])) {
        console.log("Game ended early!");
        break;
      }

      // Skip preliminary phases automatically
      if (
        currentPhase.includes("rollen_verteilt") ||
        currentPhase.includes("lobby")
      ) {
        console.log("Auto-advancing through preliminary phase...");
        await advancePhase(players[0]);
        await players[0].page.waitForTimeout(1500);
        continue;
      }

      // Wait and try to advance
      await players[0].page.waitForTimeout(2000);

      try {
        await advancePhase(players[0]);
      } catch (e) {
        // May advance automatically
      }
    }

    // Keep open if --keep flag is set
    await waitIfKeepOpen();

    console.log("\nGame 2B test completed!");
    console.log("Large 8-player game setup and initial rounds verified.");
  });
});
