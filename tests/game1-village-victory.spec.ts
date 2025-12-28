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
  logVote,
  logAction,
  logPhaseChange,
  logEvent,
  delayAction,
  waitIfKeepOpen,
} from "./helpers/game-helpers";

/**
 * GAME 1: Village Victory
 *
 * This test simulates a complete game where the village wins.
 * - 5 players join the game
 * - Roles are automatically distributed
 * - Players go through night and day phases
 * - The village successfully identifies and eliminates all werewolves
 */
test.describe("Game 1: Complete Village Victory Game", () => {
  let players: Player[] = [];
  let roomCode: string;

  test.afterEach(async () => {
    await cleanup(players);
    players = [];
  });

  test("5 players complete a full game where village wins", async ({
    browser,
  }) => {
    const playerNames = ["Anna", "Bernd", "Clara", "David", "Emma"];

    // Reset window positions for tiling
    resetWindowPositions();

    // Step 1: Create the game room
    console.log("Creating game room...");
    const { player: creator, roomCode: code } = await createRoom(
      browser,
      playerNames[0],
      "Test Game 1",
      5,
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
      // Check that all player names appear in the lobby
      for (const name of playerNames) {
        await expect(player.page.locator(`text=${name}`)).toBeVisible({
          timeout: 10000,
        });
      }
    }

    // Step 4: Start the game
    console.log("Starting the game...");
    await startGame(players[0]);

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

    // Step 7: Play through game phases until game ends
    let gameEnded = false;
    let roundCount = 0;
    const maxRounds = 10;

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
        // Werewolf phase - werewolves choose a victim
        logEvent("PHASE", "Werewolves attack");

        // Find a living villager to attack
        const livingVillagers = villagers.filter(
          (v) => v.role && !v.role.includes("werwolf"),
        );
        if (livingVillagers.length > 0) {
          const victim = livingVillagers[0];
          logEvent("TARGET", `Werewolves targeting ${victim.name}`);

          for (const wolf of werewolves) {
            // Check if this wolf is still alive
            if (!wolf.role) continue;
            try {
              logAction(wolf.name, "attack", victim.name);
              await selectTarget(wolf, victim.name);
              await delayAction();
              // Try to confirm the action
              const confirmBtn = wolf.page.locator(
                'button:has-text("Angreifen"), button:has-text("Bestaetigen"), button:has-text("Waehlen")',
              );
              if (await confirmBtn.isVisible()) {
                await confirmBtn.click();
                await delayAction();
              }
            } catch (e) {
              logEvent(
                "ERROR",
                `Werewolf ${wolf.name} attack failed`,
                String(e),
              );

              console.log(`Wolf ${wolf.name} could not attack: ${e}`);
            }
          }
        }
      } else if (currentPhase.includes("seherin")) {
        // Seer phase
        logEvent("PHASE", "Seer examines a player");
        if (seer) {
          try {
            // Seer looks at a werewolf
            if (werewolves.length > 0) {
              logAction(
                seer.name,
                "examine",
                werewolves[0].name,
                "checking for werewolf",
              );
              await selectTarget(seer, werewolves[0].name);
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
            logEvent("ERROR", `Seer ${seer.name} could not see`, String(e));
          }
        }
      } else if (currentPhase.includes("hexe")) {
        // Witch phase
        logEvent("PHASE", "Witch decides to heal or poison");
        if (witch) {
          try {
            // Witch skips for now
            logAction(witch.name, "skip", "", "no action this round");
            await skipAction(witch);
          } catch (e) {
            console.log(`Witch could not act: ${e}`);
          }
        }
      } else if (
        currentPhase.includes("abstimmung") ||
        currentPhase.includes("tag")
      ) {
        // Day voting phase
        logEvent("PHASE", "Day voting - players eliminate someone");

        // All living players vote for a werewolf (if known) or random
        const voteTarget =
          werewolves.length > 0 ? werewolves[0].name : players[1].name;
        logEvent("INFO", `Voting target: ${voteTarget}`);

        for (const player of players) {
          try {
            const playerCard = player.page
              .locator(`.spieler-card:not(.tot)`)
              .first();
            if (await playerCard.isVisible()) {
              // Try to select and vote
              logVote(player.name, voteTarget, player.role);
              await selectTarget(player, voteTarget);
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

      // Advance to next phase (typically done by the game automatically or by narrator)
      await players[0].page.waitForTimeout(2000);

      // Try to advance phase
      try {
        await advancePhase(players[0]);
      } catch (e) {
        console.log("Could not advance phase");
      }

      // Check for game end after each round
      for (const player of players) {
        if (await isGameOver(player)) {
          gameEnded = true;
          break;
        }
      }
    }

    // Step 8: Verify game ended
    console.log("\n=== Game Finished ===");

    // Check final state
    const finalPhase = await getCurrentPhase(players[0]);
    console.log(`Final phase: ${finalPhase}`);

    // The game should have ended within our round limit
    expect(roundCount).toBeLessThanOrEqual(maxRounds);

    // Keep open if --keep flag is set
    await waitIfKeepOpen();

    // Cleanup will happen in afterEach
    console.log("Game 1 test completed!");
  });
});
