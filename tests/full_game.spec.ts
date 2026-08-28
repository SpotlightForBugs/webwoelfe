/**
 * ============================================================================
 * WEBWÖLFE - FULL GAME SIMULATION TEST
 * ============================================================================
 *
 * Simulates an entire Werwolf game from start to finish, including:
 * - Room creation and player joining
 * - All game phases (night/day cycles)
 * - Role-based actions (werewolf kills, seer visions, etc.)
 * - Day voting and executions
 * - Game end detection
 *
 * Usage:
 *   PLAYERS=8 npx playwright test tests/full_game.spec.ts --headed --timeout=0
 *   ./full_game.sh 8
 *
 * Environment Variables:
 *   PLAYERS - Number of players (default: 8)
 *   BASE_URL - Server URL (default: http://localhost:5001)
 *   HL - Headless mode for non-host players (default: false)
 */

import { test, BrowserContext, Page, chromium } from "@playwright/test";

// ============================================================================
// CONFIGURATION
// ============================================================================

const PLAYER_COUNT = parseInt(process.env.PLAYERS || "8", 10);
const BASE_URL = process.env.BASE_URL || "http://127.0.0.1:5001";
const HEADLESS_OTHERS = process.env.HL === "1" || process.env.HL === "true";
// Auto-advance phases are driven by the audio_fertig mechanism (no server-side fallback timer)
// Test only sleeps briefly for UI responsiveness
const PHASE_DELAY_MS = 250; // Reduced for rapidfire
const AUDIO_WAIT_MS = 250; // Reduced for rapidfire

// Randomization settings for edge case discovery
const RANDOM_SEED = process.env.SEED
  ? parseInt(process.env.SEED, 10)
  : Date.now();
const SKIP_ACTION_CHANCE = 0.0; // Strict mode: never skip
const WRONG_TARGET_CHANCE = 0.0; // Strict mode: always valid target
const SELF_TARGET_CHANCE = 0.0; // Strict mode: never self
const DOUBLE_ACTION_CHANCE = 0.0; // Strict mode: no double actions
const RANDOM_VOTE_CHANCE = 0.0; // Strict mode: smart voting

// Seeded random for reproducibility
let randomState = RANDOM_SEED;
function seededRandom(): number {
  randomState = (randomState * 1103515245 + 12345) & 0x7fffffff;
  return randomState / 0x7fffffff;
}

function randomChoice<T>(arr: T[]): T {
  // REMOVE RANDOMNESS: Always pick first item
  return arr[0];
}

function shouldSkipAction(): boolean {
  return seededRandom() < SKIP_ACTION_CHANCE;
}

function shouldTargetWrong(): boolean {
  return seededRandom() < WRONG_TARGET_CHANCE;
}

function shouldTargetSelf(): boolean {
  return seededRandom() < SELF_TARGET_CHANCE;
}

function shouldDoubleAction(): boolean {
  return seededRandom() < DOUBLE_ACTION_CHANCE;
}

function shouldRandomVote(): boolean {
  return seededRandom() < RANDOM_VOTE_CHANCE;
}

/**
 * Get a random target for a role action with edge case testing
 */
function getRandomTarget(
  players: PlayerWindow[],
  actor: PlayerWindow,
  preferAlive: boolean = true,
): PlayerWindow {
  // Edge case: target self
  if (shouldTargetSelf()) {
    return actor;
  }

  // Edge case: target dead player
  if (shouldTargetWrong() && !preferAlive) {
    const deadPlayers = players.filter((p) => !p.isAlive && p !== actor);
    if (deadPlayers.length > 0) {
      return randomChoice(deadPlayers);
    }
  }

  // Normal: random alive player (excluding self)
  const targets = players.filter(
    (p) => p !== actor && (preferAlive ? p.isAlive : true),
  );
  return targets.length > 0 ? randomChoice(targets) : actor;
}

// Player names
const PLAYER_NAMES = [
  //TODO: Generate those automatically so that we always have enough unique names.
  "Wolfgang",
  "Maria",
  "Hans",
  "Greta",
  "Friedrich",
  "Anna",
  "Klaus",
  "Sophie",
  "Heinrich",
  "Elisabeth",
  "Otto",
  "Margarethe",
  "Wilhelm",
  "Helene",
  "Karl",
  "Emma",
  "Ludwig",
  "Charlotte",
  "Franz",
  "Katharina",
  "Johann",
  "Frieda",
  "Anton",
  "Gertrude",
  "Maximilian",
  "Therese",
  "Rudolf",
  "Johanna",
  "Hermann",
  "Luise",
];

// ============================================================================
// TYPES
// ============================================================================

interface PlayerWindow {
  context: BrowserContext;
  page: Page;
  name: string;
  id?: number;
  rolle?: string;
  isAlive: boolean;
  isHost: boolean;
}

interface GameState {
  phase: string;
  runde: number;
  isEnded: boolean;
  winner?: string;
}

// ============================================================================
// UTILITIES
// ============================================================================

async function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function log(message: string) {
  const timestamp = new Date().toLocaleTimeString("de-DE", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
  // Use process.stdout.write for immediate, unbuffered output
  process.stdout.write(`[${timestamp}] ${message}\n`);
}

// ============================================================================
// MAIN TEST
// ============================================================================

test.describe("Full Game Simulation", () => {
  test(`Simulate complete game with ${PLAYER_COUNT} players`, async () => {
    const players: PlayerWindow[] = [];
    let roomCode = "";
    let gameState: GameState = { phase: "", runde: 0, isEnded: false };

    log(`🐺 Webwölfe - Full Game Simulation `);
    log(`==========================================`);
    log(`Spieleranzahl: ${PLAYER_COUNT}`);
    log(`Base URL: ${BASE_URL}`);
    log(`Headless Others: ${HEADLESS_OTHERS ? "Ja" : "Nein"}`);
    log(`Random Seed: ${RANDOM_SEED} (use SEED=${RANDOM_SEED} to reproduce)`);
    log(`==========================================\n`);

    // Launch browsers with performance optimizations
    const browser = await chromium.launch({
      headless: false,
      args: [
        "--disable-web-security",
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--no-first-run",
        "--disable-extensions",
        "--disable-default-apps",
        "--disable-sync",
        "--disable-translate",
        "--hide-scrollbars",
        "--mute-audio",
        "--no-default-browser-check",
        "--safebrowsing-disable-auto-update",
      ],
    });

    const headlessBrowser = HEADLESS_OTHERS
      ? await chromium.launch({
          headless: true,
          args: [
            "--disable-web-security",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--no-first-run",
            "--disable-extensions",
            "--disable-default-apps",
            "--disable-sync",
            "--disable-translate",
            "--hide-scrollbars",
            "--mute-audio",
            "--no-default-browser-check",
            "--safebrowsing-disable-auto-update",
          ],
        })
      : null;

    // Create shared context for the host (keeps the main window visible)
    const sharedContext = await browser.newContext({ viewport: null });

    try {
      // ========================================================================
      // PHASE 1: Room Creation
      // ========================================================================
      log("📝 Erstelle Raum...");

      const hostContext = sharedContext;
      const hostPage = await hostContext.newPage();

      // Ensure window is maximized/visible (optional, handled by browser usually)

      await hostPage.goto(BASE_URL, { waitUntil: "domcontentloaded" }); // Faster than networkidle

      // Close pre-alpha modal if present
      const closeModalBtn = hostPage.locator("[data-close-modal]").first();
      if (await closeModalBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
        await closeModalBtn.click();
        await hostPage.waitForTimeout(300);
      }

      // Enter host name
      const hostName = PLAYER_NAMES[0];
      await hostPage.fill('input[name="spieler_name"]', hostName);

      // Select online mode
      await hostPage.locator("#modus-select").selectOption("online");

      // Create room
      await hostPage.locator('button:has-text("Spiel erstellen")').click();
      await hostPage.waitForURL(/\/lobby\//);

      // Extract room code
      const url = hostPage.url();
      const urlMatch = url.match(/\/lobby\/([A-Z0-9]+)/i);
      if (urlMatch) {
        roomCode = urlMatch[1];
      }

      log(`✓ Raum erstellt: ${roomCode}`);
      log(`✓ Host: ${hostName}\n`);

      players.push({
        context: hostContext,
        page: hostPage,
        name: hostName,
        isAlive: true,
        isHost: true,
      });

      // ========================================================================
      // PHASE 2: Players Join
      // ========================================================================
      log("👥 Spieler treten bei...");

      // Join players in parallel for faster startup
      const joinPromises: Promise<PlayerWindow>[] = [];

      for (let i = 1; i < PLAYER_COUNT; i++) {
        const playerName =
          PLAYER_NAMES[i % PLAYER_NAMES.length] +
          (i >= PLAYER_NAMES.length
            ? ` ${Math.floor(i / PLAYER_NAMES.length) + 1}`
            : "");

        const joinPromise = (async () => {
          let context: BrowserContext;

          // Each player gets their own context to avoid sharing cookies/sessions.
          // In headless mode we still reuse the headless browser instance, but
          // contexts stay isolated like separate browser profiles.
          if (HEADLESS_OTHERS && headlessBrowser) {
            context = await headlessBrowser.newContext({
              viewport: null,
              // Disable unnecessary features for performance
              javaScriptEnabled: true,
              bypassCSP: true,
              ignoreHTTPSErrors: true,
            });
          } else {
            context = await browser.newContext({
              viewport: null,
              javaScriptEnabled: true,
              bypassCSP: true,
              ignoreHTTPSErrors: true,
            });
          }

          const page = await context.newPage();

          // FAIL ON NETWORK ERRORS (404, 500, etc.)
          page.on("response", (response) => {
            const status = response.status();
            const url = response.url();
            if (status >= 400 && !url.includes("favicon")) {
              console.error(`🚨 HTTP ERROR [${playerName}]: ${status} ${url}`);
              throw new Error(`HTTP Error in ${playerName}: ${status} ${url}`);
            }
          });

          // FAIL ON CONSOLE ERRORS
          page.on("console", (msg) => {
            if (msg.type() === "error") {
              const text = msg.text();
              // Ignore some common noise and handled warnings
              if (
                !text.includes("favicon") &&
                !text.includes("ERR_BLOCKED_BY_CLIENT") &&
                !text.includes("Viewport height is too small") &&
                !text.includes("saveSitzordnung") && // Race condition during navigation
                !text.includes("Failed to fetch")
              ) {
                // Network errors during cleanup
                console.error(`🚨 CONSOLE ERROR [${playerName}]: ${text}`);
                throw new Error(`Console Error in ${playerName}: ${text}`);
              }
            }
          });

          await page.goto(BASE_URL, { waitUntil: "domcontentloaded" }); // Faster than networkidle

          // Close modal if present
          const closeModal = page.locator("[data-close-modal]").first();
          if (
            await closeModal.isVisible({ timeout: 1000 }).catch(() => false)
          ) {
            await closeModal.click();
            await page.waitForTimeout(200);
          }

          // Join via the second card (join form)
          const beitretenCard = page.locator(".card").nth(1);
          await beitretenCard
            .locator('input[name="spieler_name"]')
            .fill(playerName);
          await beitretenCard.locator('input[name="code"]').fill(roomCode);
          await beitretenCard.locator('button:has-text("Beitreten")').click();

          await page.waitForURL(/\/lobby\//);

          log(`  ✓ ${playerName} beigetreten (${i + 1}/${PLAYER_COUNT})`);

          return {
            context,
            page,
            name: playerName,
            isAlive: true,
            isHost: false,
          };
        })();

        joinPromises.push(joinPromise);
      }

      // Wait for all players to join in parallel
      const joinedPlayers = await Promise.all(joinPromises);
      players.push(...joinedPlayers);

      log(`\n✅ Alle ${PLAYER_COUNT} Spieler sind beigetreten!`);
      log(`🎮 RAUMCODE: ${roomCode}\n`);

      // ========================================================================
      // PHASE 3: Start Game
      // ========================================================================
      log("🎮 Starte Spiel...");
      await sleep(1000);

      // Host starts the game
      const startButton = hostPage.locator('button:has-text("Spiel starten")');
      if (await startButton.isVisible({ timeout: 2000 })) {
        await startButton.click();
      }

      // Wait for all players to be in the game (parallel)
      await sleep(2000);
      await Promise.all(
        players.map(async (player) => {
          await player.page.waitForURL(/\/spiel\//, {
            timeout: 15000,
            waitUntil: "domcontentloaded",
          });
        }),
      );

      // Wait for game JS to initialize (window.aktuellePhase must be set)
      await Promise.all(
        players.map(async (player) => {
          try {
            await player.page.waitForFunction(
              () =>
                typeof (window as any).aktuellePhase === "string" &&
                (window as any).aktuellePhase !== "",
              { timeout: 10000 },
            );
          } catch (e) {
            log(
              `⚠️  Game JS not fully initialized for ${player.name} - aktuellePhase not set`,
            );
          }
        }),
      );

      log("✓ Spiel gestartet!\n");

      // ========================================================================
      // PHASE 4: Extract Roles
      // ========================================================================
      log("🎭 Ermittle Rollenverteilung...");
      await sleep(2000);

      await Promise.all(
        players.map(async (player) => {
          try {
            // Primary: read from window.spielerRolle (always available)
            const rolle = await player.page.evaluate(() => {
              return (window as any).spielerRolle || "";
            });
            if (rolle) {
              player.rolle = rolle;
            } else {
              // Fallback: try DOM element
              const rolleElement = player.page.locator(".rolle-badge").first();
              if (
                await rolleElement
                  .isVisible({ timeout: 2000 })
                  .catch(() => false)
              ) {
                const rolleText = await rolleElement.textContent();
                player.rolle =
                  rolleText?.trim().replace(/^(Rolle: |Du bist )/, "") ||
                  "Unbekannt";
              } else {
                player.rolle = "Unbekannt";
              }
            }
            log(`  ${player.name}: ${player.rolle}`);
          } catch (e) {
            player.rolle = "Unbekannt";
            log(`  ${player.name}: Rolle konnte nicht ermittelt werden`);
          }
        }),
      );

      // Categorize players - werewolf pack (kennen sich gegenseitig)
      const WEREWOLF_PACK_ROLES = [
        "werwolf",
        "urwolf",
        "weißer wolf",
        "weisser wolf",
        "wolfsjunge",
        "wolf im schafspelz",
        "polarwolf",
        "teenager werwolf",
        "lupin",
        "wildes kind",
        "werwolfseherin",
      ];

      // Solo-Rollen die alleine agieren (kennen die anderen nicht!)
      const SOLO_WOLF_ROLES = ["einsamer wolf"];
      const SOLO_ROLES = [
        "einsamer wolf",
        "flötenspieler",
        "floetenspieler",
        "vampir",
        "henker",
        "selbstmörder",
      ];

      const werwolfe = players.filter((p) => {
        const rolle = p.rolle?.toLowerCase() || "";
        return WEREWOLF_PACK_ROLES.some((w) => rolle.includes(w));
      });

      // Einsamer Wolf ist SOLO - kennt die anderen Wölfe nicht!
      const einsameWoelfe = players.filter((p) => {
        const rolle = p.rolle?.toLowerCase() || "";
        return SOLO_WOLF_ROLES.some((w) => rolle.includes(w));
      });

      const soloSpieler = players.filter((p) => {
        const rolle = p.rolle?.toLowerCase() || "";
        return SOLO_ROLES.some((w) => rolle.includes(w));
      });

      const dorfbewohner = players.filter(
        (p) =>
          !werwolfe.includes(p) &&
          !soloSpieler.includes(p) &&
          p.rolle !== "Unbekannt",
      );

      log(`\n📊 Teams:`);
      log(
        `  🐺 Werwolf-Rudel: ${werwolfe.map((p) => p.name).join(", ") || "Keine"}`,
      );
      log(
        `  🐺💀 Einsame Wölfe (Solo): ${einsameWoelfe.map((p) => p.name).join(", ") || "Keine"}`,
      );
      log(
        `  🎭 Solo-Rollen: ${soloSpieler.map((p) => p.name).join(", ") || "Keine"}`,
      );
      log(
        `  🏠 Dorf: ${dorfbewohner.map((p) => p.name).join(", ") || "Keine"}\n`,
      );

      // ========================================================================
      // PHASE 5: Game Loop
      // ========================================================================
      log("🔄 Starte Spielschleife...\n");

      let loopCount = 0;
      const MAX_LOOPS = 100; // Safety limit für Loops
      let lastPhase = "";
      let samePhaseCount = 0;
      const MAX_SAME_PHASE = 25; // Max Iterationen in der gleichen Phase (25 * 2s = 50s total)

      while (!gameState.isEnded && loopCount < MAX_LOOPS) {
        loopCount++;

        // Get current phase from host page
        try {
          gameState = await hostPage.evaluate(() => {
            return {
              phase:
                (window as any).aktuellePhase ||
                document.querySelector(".phase-name")?.textContent ||
                "",
              runde: (window as any).aktuelleRunde || 1,
              isEnded: (window as any).spielEnde || false,
              winner: (window as any).gewinner,
            };
          });
        } catch (e) {
          // Try to get phase from visible element
          const phaseElement = hostPage.locator(".phase-name").first();
          if (await phaseElement.isVisible().catch(() => false)) {
            gameState.phase =
              (await phaseElement.textContent())?.toLowerCase() || "";
          }
        }

        const currentPhase = gameState.phase.toLowerCase().replace(/\s+/g, "_");

        // Prüfe ob gleiche Phase wie vorher
        if (currentPhase === lastPhase) {
          samePhaseCount++;
          // In online mode with automatic narrator, phases are controlled by the SERVER.
          // We cannot and should not try to skip phases manually.
          // The server has a 30 second fallback timeout for stuck phases.
          if (samePhaseCount > MAX_SAME_PHASE) {
            log(
              `  ❌ Phase ${currentPhase} stuck for too long (> ${MAX_SAME_PHASE} iterations)!`,
            );
            throw new Error(
              `Game stuck in phase: ${currentPhase} - Auto-advance failed.`,
            );
          }
          // Warte auf Phasenwechsel
          await sleep(2000);
          continue;
        }

        // Neue Phase erkannt
        samePhaseCount = 0;
        lastPhase = currentPhase;

        log(`📍 Phase: ${gameState.phase} (Runde ${gameState.runde})`);

        // Check for game end
        if (gameState.phase === "spiel_ende" || gameState.isEnded) {
          log("\n🏁 Spiel beendet!");
          gameState.isEnded = true;
          break;
        }

        // Wait for role UI and phase mapping to load on client side
        // This ensures action panels are visible before we try to interact
        await sleep(1500);

        // Handle phase-specific actions
        await handlePhase(gameState.phase, players);

        // Wait for phase transition (Server wechselt nach Aktion automatisch)
        await sleep(AUDIO_WAIT_MS);

        // Check if game ended
        const ended = await checkGameEnd(hostPage);
        if (ended) {
          gameState.isEnded = true;
          break;
        }
      }

      // ========================================================================
      // PHASE 6: Game End Summary
      // ========================================================================
      log("\n==========================================");
      log("🎉 SPIEL BEENDET!");
      log("==========================================\n");

      // Get final game state
      try {
        const finalState = await hostPage.evaluate(() => {
          return {
            winner: (window as any).gewinner || "Unbekannt",
            survivors: Array.from(
              document.querySelectorAll(".spieler-card:not(.tot)"),
            )
              .map((el) => el.querySelector(".spieler-name")?.textContent)
              .filter(Boolean),
          };
        });

        log(`🏆 Gewinner: ${finalState.winner}`);
        log(`👥 Überlebende: ${finalState.survivors.join(", ") || "Keine"}`);
      } catch (e) {
        log("Endstand konnte nicht ermittelt werden");
      }

      log(`\n📊 Statistik:`);
      log(`  Loop-Iterationen: ${loopCount}`);
      log(`  Spieler gestartet: ${PLAYER_COUNT}`);
      log(`  Überlebende: ${players.filter((p) => p.isAlive).length}`);

      // Keep windows open for review
      log("\n==========================================");
      log("Fenster bleiben offen für Nachbesprechung.");
      log("Drücke Strg+C zum Beenden.");
      log("==========================================\n");

      // Wait indefinitely
      await new Promise(() => {});
    } catch (error) {
      log(`❌ Fehler: ${error}`);
      throw error;
    }
  });
});

// ============================================================================
// GENERIC PHASE HANDLER - No hardcoded roles, uses standardized UI
// ============================================================================

/**
 * Handles ANY game phase generically by:
 * 1. Checking which players have visible action panels (are active)
 * 2. For active players: reading available actions from the UI
 * 3. Selecting valid targets if needed
 * 4. Clicking the first available action button
 * 5. Waiting for server confirmation
 *
 * This works for ALL roles because the UI is standardized:
 * - Night roles: action panel with role-specific buttons + target selection
 * - Voting: action panel with "Abstimmen" / "Enthalten"
 * - Auto-advance: no action panel visible, just wait
 */
async function handlePhase(
  phase: string,
  players: PlayerWindow[],
): Promise<void> {
  const normalizedPhase = phase.toLowerCase().replace(/[_\s-]/g, "");

  // Auto-advance phases: no player interaction needed, just wait
  if (
    normalizedPhase.includes("start") ||
    normalizedPhase.includes("ende") ||
    normalizedPhase.includes("ergebnis") ||
    normalizedPhase.includes("brummen") ||
    normalizedPhase.includes("enthuellung") ||
    normalizedPhase.includes("rollenverteilt") ||
    normalizedPhase.includes("hinrichtung") ||
    normalizedPhase.includes("verliebteinfo")
  ) {
    log(`  -- Auto-Phase: ${phase}`);
    await sleep(PHASE_DELAY_MS);
    return;
  }

  // Voting phase: all alive players vote
  if (
    normalizedPhase.includes("abstimmung") ||
    normalizedPhase === "tagabstimmung"
  ) {
    await handleVotingPhase(players);
    return;
  }

  // Action phase: find active players and perform their actions
  await handleActionPhase(players, phase);
}

/**
 * Generic voting handler - all alive players vote via standardized action panel.
 */
async function handleVotingPhase(players: PlayerWindow[]): Promise<void> {
  log("  -- Abstimmung: Spieler stimmen ab...");

  const alivePlayers = players.filter((p) => p.isAlive);

  for (const voter of alivePlayers) {
    try {
      // Wait for __testApi to be ready
      const testApi = await getTestApi(voter.page);
      if (!testApi || !testApi.isActive) continue;

      // Get selectable targets
      const targets = (await voter.page.evaluate(() => {
        const api = (window as any).__testApi;
        return api ? api.getSelectablePlayers() : [];
      })) as { id: number; name: string }[];

      // Filter out self and narrators
      const validTargets = targets.filter((t) => t.name !== voter.name);

      if (validTargets.length > 0) {
        // Select a target and vote
        const target = validTargets[0];
        await voter.page.evaluate((targetId) => {
          (window as any).__testApi.selectPlayer(targetId);
        }, target.id);
        await sleep(200);

        // Click Abstimmen button or vote directly
        await voter.page.evaluate((targetId) => {
          (window as any).__testApi.vote(targetId);
        }, target.id);

        log(`    ${voter.name} -> ${target.name}`);
      } else {
        // Abstain
        await voter.page.evaluate(() => {
          (window as any).__testApi.vote(null);
        });
        log(`    ${voter.name} -> Enthalten`);
      }
    } catch (e) {
      log(`    ${voter.name} konnte nicht abstimmen`);
    }

    await sleep(100);
  }
}

/**
 * Generic action handler for ANY role phase.
 * Finds active players and performs their available actions.
 */
async function handleActionPhase(
  players: PlayerWindow[],
  phase: string,
): Promise<void> {
  // Give UI time to update action panels
  await sleep(500);

  // Find all players who are active in this phase
  const activePlayers: PlayerWindow[] = [];
  for (const player of players) {
    if (!player.isAlive) continue;
    try {
      const isActive = await player.page.evaluate(() => {
        const api = (window as any).__testApi;
        return api ? api.isActive : false;
      });
      if (isActive) {
        activePlayers.push(player);
      }
    } catch {
      // Page may have navigated or errored, skip
    }
  }

  if (activePlayers.length === 0) {
    log(`  -- Keine aktiven Spieler für ${phase}, warte...`);
    await sleep(PHASE_DELAY_MS);
    return;
  }

  log(
    `  -- ${phase}: ${activePlayers.length} aktive Spieler (${activePlayers.map((p) => p.name).join(", ")})`,
  );

  for (const player of activePlayers) {
    try {
      await performPlayerAction(player, players);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      log(`    ${player.name}: Aktion fehlgeschlagen: ${msg}`);
    }
    await sleep(300);
  }
}

/**
 * Perform whatever action is available for a player, using the standardized UI.
 * No role knowledge needed - just reads what buttons are visible.
 */
async function performPlayerAction(
  player: PlayerWindow,
  allPlayers: PlayerWindow[],
): Promise<void> {
  const page = player.page;

  // Wait for action panel to be visible
  await page
    .locator('[data-testid="action-panel"]')
    .waitFor({ state: "visible", timeout: 8000 })
    .catch(() => {});

  // Read UI config from the page
  const uiState = await page.evaluate(() => {
    const api = (window as any).__testApi;
    if (!api) return null;
    return {
      actions: api.getVisibleActions(),
      selectablePlayers: api.getSelectablePlayers(),
      uiConfig: api.uiConfig,
      playerId: api.playerId,
    };
  });

  if (!uiState) {
    log(`    ${player.name}: Kein Test-API verfuegbar`);
    return;
  }

  // Determine target selection requirements
  const requiresTarget = uiState.uiConfig?.requires_target ?? false;
  const multiTarget = uiState.uiConfig?.allow_multiple_targets ?? false;
  const minTargets = uiState.uiConfig?.min_targets ?? (requiresTarget ? 1 : 0);
  const allowSelf = uiState.uiConfig?.allow_self_target ?? false;

  // Filter valid targets
  let validTargets = uiState.selectablePlayers.filter(
    (t: { id: number }) => allowSelf || t.id !== uiState.playerId,
  );

  // Select targets if needed
  if (requiresTarget || minTargets > 0) {
    const targetCount = Math.min(
      multiTarget ? minTargets : 1,
      validTargets.length,
    );

    for (let i = 0; i < targetCount; i++) {
      if (validTargets.length === 0) break;
      const target = validTargets[i];
      await page.evaluate((targetId) => {
        (window as any).__testApi.selectPlayer(targetId);
      }, target.id);
      log(`    ${player.name} -> Ziel: ${target.name}`);
      await sleep(300);
    }
  }

  // Wait for buttons to become enabled after target selection
  await sleep(500);

  // Re-read actions (they may have become enabled after target selection)
  const currentActions = await page.evaluate(() => {
    const btns = document.querySelectorAll(
      "#action-buttons button:not([disabled])",
    );
    return Array.from(btns).map((b) => ({
      text: (b as HTMLButtonElement).textContent?.trim() || "",
      testId: b.getAttribute("data-testid") || "",
    }));
  });

  if (currentActions.length === 0) {
    log(`    ${player.name}: Keine verfuegbaren Aktionen`);
    return;
  }

  // Pick the first non-skip action, or skip if that's all there is
  const preferredAction =
    currentActions.find(
      (a) => !a.text.includes("Überspringen") && !a.text.includes("Enthalten"),
    ) || currentActions[0];

  // Click the action button
  if (preferredAction.testId) {
    await page.locator(`[data-testid="${preferredAction.testId}"]`).click();
  } else {
    await page
      .locator(
        `#action-buttons button:not([disabled]):has-text("${preferredAction.text}")`,
      )
      .first()
      .click();
  }

  log(`    ${player.name}: "${preferredAction.text}"`);

  // Wait for server confirmation (aktion_bestaetigt -> showAlert)
  await page
    .locator("#status-nachricht")
    .waitFor({ state: "visible", timeout: 5000 })
    .catch(() => {});

  await sleep(300);
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

async function getTestApi(
  page: Page,
): Promise<{ isActive: boolean; isAlive: boolean; phase: string } | null> {
  try {
    return await page.evaluate(() => {
      const api = (window as any).__testApi;
      if (!api) return null;
      return {
        isActive: api.isActive,
        isAlive: api.isAlive,
        phase: api.phase,
      };
    });
  } catch {
    return null;
  }
}

async function checkGameEnd(hostPage: Page): Promise<boolean> {
  try {
    return await hostPage.evaluate(() => {
      const api = (window as any).__testApi;
      if (api && api.gameEnded) return true;
      const phase = (window as any).aktuellePhase;
      return (window as any).spielEnde === true || phase === "spiel_ende";
    });
  } catch {
    return false;
  }
}
