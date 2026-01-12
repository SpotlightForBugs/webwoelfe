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
// Server hat 30 Sekunden Delay für automatische Phasen (PHASE_WECHSEL_DELAY in app.py)
// Test wartet nur kurz für UI-Interaktionen
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
const PLAYER_NAMES = [ //TODO: Generate those automatically so that we always have enough unique names.
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
  console.log(`[${timestamp}] ${message}`);
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

      await hostPage.goto(BASE_URL, { waitUntil: 'domcontentloaded' }); // Faster than networkidle

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
      const joinPromises = [];

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
              if (!text.includes("favicon") &&
                !text.includes("ERR_BLOCKED_BY_CLIENT") &&
                !text.includes("Viewport height is too small") &&
                !text.includes("saveSitzordnung") &&  // Race condition during navigation
                !text.includes("Failed to fetch")) {  // Network errors during cleanup
                console.error(`🚨 CONSOLE ERROR [${playerName}]: ${text}`);
                throw new Error(`Console Error in ${playerName}: ${text}`);
              }
            }
          });

          await page.goto(BASE_URL, { waitUntil: 'domcontentloaded' }); // Faster than networkidle

          // Close modal if present
          const closeModal = page.locator("[data-close-modal]").first();
          if (await closeModal.isVisible({ timeout: 1000 }).catch(() => false)) {
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

      // Wait for all players to be in the game
      await sleep(2000);
      for (const player of players) {
        await player.page.waitForURL(/\/spiel\//, {
          timeout: 15000,  // Increased timeout for slower servers
          waitUntil: 'domcontentloaded' // Don't wait for external resources (fonts, CDN, etc.)
        });

        // VERIFY VILLAGE 3D (TS-based) - Wait for async initialization (optional feature)
        try {
          await player.page.waitForFunction(
            () => {
              const v3d = (window as any).village3d;
              return v3d !== undefined && typeof v3d.setPlayers === 'function';
            },
            { timeout: 3000 }
          );
          // log(`✓ Village3D (TS) initialized for ${player.name}`);
        } catch (e) {
          log(`⚠️  Village3D (TS) not initialized for ${player.name} (non-critical, continuing...)`);
        }
      }

      log("✓ Spiel gestartet!\n");



      // ========================================================================
      // PHASE 4: Extract Roles
      // ========================================================================
      log("🎭 Ermittle Rollenverteilung...");
      await sleep(2000);

      for (const player of players) {
        try {
          // Extract role from the game page
          const rolleElement = player.page
            .locator(".rolle-badge")
            .first();
          if (
            await rolleElement.isVisible({ timeout: 2000 }).catch(() => false)
          ) {
            const rolleText = await rolleElement.textContent();
            player.rolle =
              rolleText?.trim().replace(/^(Rolle: |Du bist )/, "") ||
              "Unbekannt";
          } else {
            // Try getting from page variable
            player.rolle = await player.page.evaluate(() => {
              return (window as any).spielerRolle || "Unbekannt";
            });
          }
          log(`  ${player.name}: ${player.rolle}`);
        } catch (e) {
          player.rolle = "Unbekannt";
          log(`  ${player.name}: Rolle konnte nicht ermittelt werden`);
        }
      }

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
            log(`  ❌ Phase ${currentPhase} stuck for too long (> ${MAX_SAME_PHASE} iterations)!`);
            throw new Error(`Game stuck in phase: ${currentPhase} - Auto-advance failed.`);
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
        await handlePhase(
          gameState.phase,
          players,
          werwolfe,
          einsameWoelfe,
          dorfbewohner,
        );

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
      await new Promise(() => { });
    } catch (error) {
      log(`❌ Fehler: ${error}`);
      throw error;
    }
  });
});

// ============================================================================
// PHASE HANDLERS
// ============================================================================

async function handlePhase(
  phase: string,
  players: PlayerWindow[],
  werwolfe: PlayerWindow[],
  einsameWoelfe: PlayerWindow[],
  dorfbewohner: PlayerWindow[],
): Promise<void> {
  const normalizedPhase = phase.toLowerCase().replace(/[_\s-]/g, "");

  // ========================================================================
  // AUTO-ADVANCE PHASES (no player interaction needed)
  // ========================================================================

  // Verliebte Info - special validation phase
  if (normalizedPhase.includes("verliebteinfo")) {
    log(`  💕 Verliebte-Info-Phase: Validiere Sichtbarkeit...`);
    await sleep(PHASE_DELAY_MS);
    await validateVerliebteVisibility(players);
    return;
  }

  if (
    normalizedPhase.includes("start") ||
    normalizedPhase.includes("ende") ||
    normalizedPhase.includes("ergebnis") ||
    normalizedPhase.includes("brummen") ||
    normalizedPhase.includes("enthuellung") ||
    normalizedPhase.includes("rollenverteilt")
  ) {
    log(`  ⏭️ Auto-Phase: ${phase}`);
    await sleep(PHASE_DELAY_MS);
    return;
  }

  // ========================================================================
  // FIRST NIGHT PHASES
  // ========================================================================

  // Dieb - steals a role
  if (normalizedPhase.includes("dieb")) {
    await handleDiebPhase(players);
    return;
  }

  // Doppelgänger - copies a role
  if (
    normalizedPhase.includes("doppelgaenger") ||
    normalizedPhase.includes("doppelgänger")
  ) {
    await handleDoppelgaengerPhase(players);
    return;
  }

  // Amor - creates love pair
  if (normalizedPhase.includes("amor")) {
    await handleAmorPhase(players);
    return;
  }

  // Dunkler Priester - marks someone
  if (
    normalizedPhase.includes("priester") ||
    normalizedPhase.includes("dunkel")
  ) {
    await handlePriesterPhase(players);
    return;
  }

  // Wildes Kind - chooses a role model
  if (
    normalizedPhase.includes("wildeskind") ||
    normalizedPhase.includes("wildes")
  ) {
    await handleWildesKindPhase(players);
    return;
  }

  // Wolfsjunge - chooses a role model
  if (normalizedPhase.includes("wolfsjunge")) {
    await handleWolfsjungePhase(players);
    return;
  }

  // Hund - chooses to be wolf or villager
  if (normalizedPhase.includes("hund") && !normalizedPhase.includes("baeren")) {
    await handleHundPhase(players);
    return;
  }

  // Group knowledge phases (Schwestern, Brüder, Freimaurer, Flüchtlinge)
  if (
    normalizedPhase.includes("schwestern") ||
    normalizedPhase.includes("brueder") ||
    normalizedPhase.includes("freimaurer") ||
    normalizedPhase.includes("fluechtlinge")
  ) {
    log(`  👥 Gruppenphase: ${phase} (Info-only)`);
    await sleep(PHASE_DELAY_MS);
    return;
  }

  // ========================================================================
  // SEER VARIANTS
  // ========================================================================

  if (
    normalizedPhase.includes("seherin") ||
    normalizedPhase.includes("seherlehrling") ||
    normalizedPhase.includes("aurenseherin") ||
    normalizedPhase.includes("paranormal")
  ) {
    await handleSeherVariantPhase(players, phase);
    return;
  }

  if (normalizedPhase.includes("medium")) {
    await handleMediumPhase(players);
    return;
  }

  if (normalizedPhase.includes("tratschweib")) {
    await handleTratschweibPhase(players);
    return;
  }

  if (normalizedPhase.includes("werwolfseherin")) {
    await handleWerwolfseherinPhase(players, werwolfe);
    return;
  }

  // ========================================================================
  // HEALER VARIANTS
  // ========================================================================

  if (
    normalizedPhase.includes("heiler") ||
    normalizedPhase.includes("leibwaechter")
  ) {
    await handleHeilerVariantPhase(players, dorfbewohner, phase);
    return;
  }

  if (
    normalizedPhase.includes("hure") ||
    normalizedPhase.includes("prostituierte") ||
    normalizedPhase.includes("nutte")
  ) {
    await handleHurePhase(players, phase);
    return;
  }

  // ========================================================================
  // WEREWOLF VARIANTS
  // ========================================================================

  if (
    normalizedPhase.includes("werwolf") ||
    normalizedPhase === "werwolfphase"
  ) {
    await handleWerwolfPhase(werwolfe, dorfbewohner);
    return;
  }

  if (
    normalizedPhase.includes("einsamerwolf") ||
    normalizedPhase.includes("einsamer")
  ) {
    await handleEinsamerWolfPhase(einsameWoelfe, dorfbewohner);
    return;
  }

  if (normalizedPhase.includes("urwolf")) {
    await handleUrwolfPhase(players, dorfbewohner);
    return;
  }

  if (
    normalizedPhase.includes("weisserwolf") ||
    normalizedPhase.includes("weisser")
  ) {
    await handleWeisserWolfPhase(players, werwolfe);
    return;
  }

  if (normalizedPhase.includes("mordlustiger")) {
    await handleMordlustigerPhase(players);
    return;
  }

  // ========================================================================
  // HEXE VARIANTS
  // ========================================================================

  if (
    normalizedPhase.includes("hexe") &&
    !normalizedPhase.includes("hexenmeister")
  ) {
    await handleHexePhase(players);
    return;
  }

  if (normalizedPhase.includes("hexenmeister")) {
    await handleHexenmeisterPhase(players);
    return;
  }

  if (normalizedPhase.includes("giftmischerin")) {
    await handleGiftmischerinPhase(players);
    return;
  }

  if (
    normalizedPhase.includes("kraeuterweib") ||
    normalizedPhase.includes("kräuterweib")
  ) {
    await handleKraeuterweibPhase(players);
    return;
  }

  if (normalizedPhase.includes("zauberer")) {
    await handleZaubererPhase(players);
    return;
  }

  if (normalizedPhase.includes("sandmann")) {
    await handleSandmannPhase(players);
    return;
  }

  // ========================================================================
  // OTHER NIGHT ROLES
  // ========================================================================

  if (normalizedPhase.includes("zahnarzt")) {
    await handleZahnarztPhase(players);
    return;
  }

  if (normalizedPhase.includes("rabe")) {
    await handleRabePhase(players);
    return;
  }

  if (
    normalizedPhase.includes("floetenspieler") ||
    normalizedPhase.includes("flötenspieler")
  ) {
    await handleFloetenspielerPhase(players);
    return;
  }

  if (normalizedPhase.includes("vampir")) {
    await handleVampirPhase(players);
    return;
  }

  if (normalizedPhase.includes("zombie")) {
    await handleZombiePhase(players);
    return;
  }

  if (normalizedPhase.includes("pyromane")) {
    await handlePyromanePhase(players);
    return;
  }

  if (normalizedPhase.includes("tonks")) {
    await handleTonksPhase(players);
    return;
  }

  if (normalizedPhase.includes("buddler")) {
    await handleBuddlerPhase(players);
    return;
  }

  if (normalizedPhase.includes("henker")) {
    await handleHenkerPhase(players);
    return;
  }

  // Group recognition phases (no action required - just skip)
  if (
    normalizedPhase.includes("drei_brueder") ||
    normalizedPhase.includes("drei_brüder") ||
    normalizedPhase.includes("zwei_schwestern") ||
    normalizedPhase.includes("freimaurer") ||
    normalizedPhase.includes("flüchtlinge") ||
    normalizedPhase.includes("fluechtlinge")
  ) {
    log(`  👥 Gruppen-Erkennungs-Phase (${phase}): Warten auf Auto-Skip...`);
    await sleep(PHASE_DELAY_MS);
    return;
  }

  // ========================================================================
  // DAY PHASES
  // ========================================================================

  // Combined phase: diskussion_abstimmung - handle both chat AND voting
  if (
    normalizedPhase.includes("diskussion") &&
    normalizedPhase.includes("abstimmung")
  ) {
    await handleDiskussionPhase(players);
    await handleAbstimmungPhase(players, werwolfe);
    return;
  }

  if (normalizedPhase.includes("diskussion")) {
    await handleDiskussionPhase(players);
    return;
  }

  if (
    normalizedPhase.includes("abstimmung") &&
    !normalizedPhase.includes("ergebnis")
  ) {
    await handleAbstimmungPhase(players, werwolfe);
    return;
  }

  if (normalizedPhase.includes("jaeger") || normalizedPhase.includes("jäger")) {
    await handleJaegerPhase(players, werwolfe);
    return;
  }

  if (normalizedPhase.includes("kamikaze")) {
    await handleKamikazePhase(players, werwolfe);
    return;
  }

  // ========================================================================
  // UNKNOWN PHASE
  // ========================================================================
  log(`  ⚠️ Unbekannte Phase: ${phase} - warte...`);
  await sleep(PHASE_DELAY_MS);
}

async function handleWerwolfPhase(
  werwolfe: PlayerWindow[],
  dorfbewohner: PlayerWindow[],
): Promise<void> {
  log("  🐺 Werwolf-Phase: Wähle Opfer... ()");

  // Random: Sometimes skip the entire phase (only for testing timeout handling)
  // DISABLED: This causes stuck phases! The server requires votes.
  // if (shouldSkipAction()) {
  //   log("    ⚠️ [RANDOM] Wölfe überspringen diese Runde (Test: Timeout-Handling)");
  //   return;
  // }

  const aliveWolves = werwolfe.filter((w) => w.isAlive);
  if (aliveWolves.length === 0) {
    log("    Keine lebenden Werwölfe!");
    return;
  }

  // VALIDATION: Werewolves must see each other (and themselves!)
  await validateWerwolfVisibility(werwolfe, aliveWolves);

  // Valid targets: alive non-werwolf players only
  const validTargets = dorfbewohner.filter((p) => p.isAlive);
  if (validTargets.length === 0) {
    log("    Keine gültigen Ziele für Werwölfe!");
    return;
  }

  // For edge case testing, keep track of ALL players (including dead and wolves for invalid target tests)
  const allPlayers = dorfbewohner.concat(werwolfe);

  for (const wolf of aliveWolves) {
    let target: PlayerWindow;
    let isInvalidTarget = false;

    // Random targeting strategy - first try invalid, then retry with valid
    if (shouldTargetSelf()) {
      target = wolf; // Try to target self (will fail)
      isInvalidTarget = true;
      log(`    ⚠️ [RANDOM] ${wolf.name} versucht sich selbst zu wählen`);
    } else if (shouldTargetWrong()) {
      // Target a dead player or another wolf (will fail)
      const wrongTargets = allPlayers.filter(
        (p) => !p.isAlive || werwolfe.includes(p),
      );
      if (wrongTargets.length > 0) {
        target = randomChoice(wrongTargets);
        isInvalidTarget = true;
        log(
          `    ⚠️ [RANDOM] ${wolf.name} wählt ungültiges Ziel: ${target.name} (tot: ${!target.isAlive}, wolf: ${werwolfe.includes(target)})`,
        );
      } else {
        target = randomChoice(validTargets);
      }
    } else {
      // Normal random target from valid targets
      target = randomChoice(validTargets);
    }

    let success = await selectTargetAndConfirm(
      wolf.page,
      target.name,
      ["Töten", "Wählen", "Angreifen"],
    );

    // If the action failed (invalid target), retry with a valid target
    if (!success && isInvalidTarget && validTargets.length > 0) {
      log(`    🔄 ${wolf.name} Server hat abgelehnt, wähle gültiges Ziel...`);
      await sleep(500);
      const validTarget = randomChoice(validTargets);
      success = await selectTargetAndConfirm(
        wolf.page,
        validTarget.name,
        ["Töten", "Wählen", "Angreifen"],
      );
      if (success) {
        log(`    ✓ ${wolf.name} stimmt für ${validTarget.name}`);
      }
    } else if (success) {
      log(`    ${wolf.name} stimmt für ${target.name}`);
    } else {
      log(`    ⚠️ ${wolf.name} konnte nicht abstimmen (kein Button gefunden)`);
    }

    // Random: Try double action (will be rejected by server, that's fine)
    if (shouldDoubleAction()) {
      log(
        `    ⚠️ [RANDOM] ${wolf.name} versucht erneut zu wählen (wird abgelehnt)`,
      );
      await selectTargetAndConfirm(
        wolf.page,
        randomChoice(validTargets).name,
        ["Töten", "Wählen"],
      );
    }

    await sleep(300); // Random delay
  }
}

// ============================================================================
// FIRST NIGHT ROLE HANDLERS
// ============================================================================

async function handleDiebPhase(players: PlayerWindow[]): Promise<void> {
  log("  🎭 Dieb-Phase: Wähle eine Rolle zu stehlen...");

  const dieb = findPlayerByRole(players, ["Dieb"]);
  if (!dieb) {
    log("    Kein Dieb im Spiel");
    return;
  }

  try {
    // Strategy 1: Wait for action buttons area
    let actionPanel = dieb.page.locator('#action-panel, .action-panel').first();
    let waitedForPanel = false;
    
    if (!(await actionPanel.isVisible({ timeout: 2000 }).catch(() => false))) {
      log("    ℹ️ Action-Panel nicht direkt sichtbar, suche alternative Buttons...");
    } else {
      waitedForPanel = true;
      log("    ℹ️ Action-Panel gefunden");
    }

    // Get all buttons and filter for role choices
    const allButtons = await dieb.page.locator('button').all();
    const roleChoiceButtons: { element: any; text: string }[] = [];

    // Common action button texts to exclude
    const actionButtonTexts = [
      'Bestätigen', 'Bestätigung', 'Confirm',
      'Überspringen', 'Skip', 'Weiter', 'Continue', 'Next',
      'Nichts tun', 'Do nothing', 'Abbrechen', 'Cancel',
      'OK', 'Ja', 'Nein', 'Yes', 'No',
      'Senden', 'Send', 'Ablehnen', 'Accept', 'Annehmen',
      'Heilen', 'Heal', 'Töten', 'Kill', 'Vergiften', 'Poison',
      'Wählen', 'Choose'  // Generic choice button - usually paired with role selection
    ];

    for (const btn of allButtons) {
      const isVisible = await btn.isVisible({ timeout: 300 }).catch(() => false);
      if (!isVisible) continue;

      const text = (await btn.textContent({ timeout: 300 }).catch(() => '')) || '';
      const trimmedText = text.trim();
      
      if (!trimmedText) continue;

      // Check if this looks like a generic action button
      const isGenericAction = actionButtonTexts.some(action => 
        trimmedText.toLowerCase().includes(action.toLowerCase())
      );

      if (isGenericAction) {
        // Skip generic action buttons, unless it's just "Wählen" and it's alone
        if (trimmedText.toLowerCase() === 'wählen' && roleChoiceButtons.length === 0) {
          // Might be a "choose" button for selected role - skip for now
          continue;
        }
        continue;
      }

      // Check that button is in action area or not in erzähler/sidebar
      const isInActionArea = await btn.evaluate(el => {
        let parent = el.parentElement;
        let depth = 0;
        while (parent && depth < 6) {
          if (parent.id === 'action-buttons' || parent.className?.includes('action')) {
            return true;
          }
          if (parent.id?.includes('erzaehler') || parent.className?.includes('sidebar')) {
            return false;
          }
          parent = parent.parentElement;
          depth++;
        }
        return true; // Assume valid if no specific area detected
      });

      if (isInActionArea) {
        roleChoiceButtons.push({ element: btn, text: trimmedText });
      }
    }

    log(`    ℹ️ Gefundene Rollenwahlbuttons: ${roleChoiceButtons.length}`);
    if (roleChoiceButtons.length > 0) {
      roleChoiceButtons.forEach((btn, i) => log(`      ${i + 1}. ${btn.text}`));
    }

    if (roleChoiceButtons.length < 1) {
      // Even if we don't find role buttons, try to find ANY clickable element that might be a choice
      log(`    ⚠️ Keine Rollen-Buttons gefunden, versuche alternative Findung...`);
      
      // Try clicking on any card or element that represents a choice
      const cards = await dieb.page.locator('[data-role], .role-option, .choice-button').all();
      if (cards.length >= 2) {
        log(`    ℹ️ Gefundene ${cards.length} Role-Cards, wähle eines...`);
        const choice = randomChoice(cards);
        await choice.click();
        await sleep(1000);
      } else {
        log(`    ⚠️ Keine Rollenwahloptionen gefunden - Phase wird übersprungen`);
        await sleep(PHASE_DELAY_MS);
        return;
      }
    } else {
      // We found role buttons - select randomly
      if (roleChoiceButtons.length >= 2) {
        const choice = randomChoice(roleChoiceButtons);
        log(`    ✓ Dieb wählt: "${choice.text}"`);
        await choice.element.click();
        await sleep(800);
      } else if (roleChoiceButtons.length === 1) {
        // Only one button - might be a confirmation after showing two roles
        log(`    ℹ️ Nur ein Button gefunden: "${roleChoiceButtons[0].text}", klicke...`);
        await roleChoiceButtons[0].element.click();
        await sleep(800);
      }
    }

    // After selection, look for confirmation button
    const confirmButtons = await dieb.page.locator(
      'button:has-text("Bestätigen"), button:has-text("Confirm"), button:has-text("OK"), button.btn-primary, button:has-text("Wählen")'
    ).all();

    let confirmed = false;
    for (const btn of confirmButtons) {
      const isVisible = await btn.isVisible({ timeout: 500 }).catch(() => false);
      const text = await btn.textContent({ timeout: 300 }).catch(() => '');
      
      if (isVisible && text) {
        // Prefer "Bestätigen" or "OK" - skip "Wählen" if we have it
        if (text.toLowerCase().includes('bestätig') || text.toLowerCase().includes('ok') || text.toLowerCase().includes('confirm')) {
          log(`    ✓ Klicke Bestätigungsbutton: "${text.trim()}"`);
          await btn.click();
          confirmed = true;
          await sleep(500);
          break;
        }
      }
    }

    if (!confirmed) {
      log(`    ℹ️ Kein Bestätigungsbutton gefunden - Aktion möglicherweise bereits abgeschlossen`);
    }

  } catch (e) {
    const errorMsg = e instanceof Error ? e.message : String(e);
    log(`    ⚠️ Fehler bei Dieb-Phase: ${errorMsg}`);
  }

  await sleep(PHASE_DELAY_MS);
}

async function handleDoppelgaengerPhase(
  players: PlayerWindow[],
): Promise<void> {
  log("  👤 Doppelgänger-Phase: Wähle Spieler zum Kopieren... ()");

  const doppelgaenger = findPlayerByRole(players, ["Doppelgänger"]);
  if (!doppelgaenger) {
    log("    Kein Doppelgänger im Spiel");
    return;
  }

  if (shouldSkipAction()) {
    log("    ⚠️ [RANDOM] Doppelgänger überspringt");
    return;
  }

  const target = getRandomTarget(players, doppelgaenger);
  await selectTargetAndConfirm(doppelgaenger.page, target.name, [
    "Ziel wählen",
    "Wählen",
  ]);
  log(`    Doppelgänger kopiert ${target.name}`);
}

async function handlePriesterPhase(players: PlayerWindow[]): Promise<void> {
  log("  ⛪ Dunkler Priester-Phase: Verliebe zwei Spieler... ()");

  const priester = findPlayerByRole(players, ["Dunkler Priester", "Priester"]);
  if (!priester) {
    log("    Kein Dunkler Priester im Spiel");
    return;
  }

  if (shouldSkipAction()) {
    log("    ⚠️ [RANDOM] Priester überspringt");
    return;
  }

  // Dunkler Priester needs to select TWO players to make them fall in love
  const otherPlayers = players.filter((p) => p !== priester && p.isAlive);
  if (otherPlayers.length < 2) {
    log("    Zu wenige Spieler für Dunkler Priester");
    return;
  }

  // Select two different random players
  const shuffled = [...otherPlayers].sort(() => seededRandom() - 0.5);
  const target1 = shuffled[0];
  const target2 = shuffled[1];

  try {
    // Dunkler Priester muss 2 Spieler auswählen (wie Amor)
    // Klicke auf ersten Spieler
    const card1 = priester.page.locator(
      `.spieler-card[data-name="${target1.name}"]`,
    );
    if (await card1.isVisible({ timeout: 2000 }).catch(() => false)) {
      await card1.click();
      log(`    Erster Liebhaber ausgewählt: ${target1.name}`);
      await sleep(500);
    } else {
      // Fallback: Suche nach Text
      const card1Alt = priester.page
        .locator(`.spieler-card:has-text("${target1.name}")`)
        .first();
      if (await card1Alt.isVisible({ timeout: 1000 }).catch(() => false)) {
        await card1Alt.click();
        log(`    Erster Liebhaber ausgewählt: ${target1.name}`);
        await sleep(500);
      }
    }

    // Klicke auf zweiten Spieler
    const card2 = priester.page.locator(
      `.spieler-card[data-name="${target2.name}"]`,
    );
    if (await card2.isVisible({ timeout: 2000 }).catch(() => false)) {
      await card2.click();
      log(`    Zweiter Liebhaber ausgewählt: ${target2.name}`);
      await sleep(500);
    } else {
      // Fallback: Suche nach Text
      const card2Alt = priester.page
        .locator(`.spieler-card:has-text("${target2.name}")`)
        .first();
      if (await card2Alt.isVisible({ timeout: 1000 }).catch(() => false)) {
        await card2Alt.click();
        log(`    Zweiter Liebhaber ausgewählt: ${target2.name}`);
        await sleep(500);
      }
    }

    // Warte kurz bis die UI aktualisiert ist (2/2 Spieler ausgewählt)
    await sleep(800);

    // Jetzt sollte der "Verlieben" Button erscheinen
    const actionBtn = priester.page.locator('button:has-text("Verlieben")').first();
    if (await actionBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await actionBtn.click();
      log(`    🖤 Dunkler Priester verliebt ${target1.name} und ${target2.name}`);
    } else {
      // Fallback: Hole IDs aus den Karten und sende direkt via Socket
      log("    Button nicht gefunden, versuche direkte Socket-Aktion...");

      const id1 = await priester.page
        .locator(`.spieler-card[data-name="${target1.name}"]`)
        .getAttribute("data-id")
        .catch(() => null);
      const id2 = await priester.page
        .locator(`.spieler-card[data-name="${target2.name}"]`)
        .getAttribute("data-id")
        .catch(() => null);

      if (id1 && id2) {
        await priester.page.evaluate(
          ([playerId1, playerId2]) => {
            if ((window as any).socket) {
              (window as any).socket.emit("aktion_ausfuehren", {
                aktion: "priester_verlieben",
                ziel_id: [parseInt(playerId1), parseInt(playerId2)],
              });
            }
          },
          [id1, id2],
        );
        log(
          `    🖤 Dunkler Priester verliebt ${target1.name} (ID:${id1}) und ${target2.name} (ID:${id2}) via Socket`,
        );
      } else {
        log(`    ❌ Konnte Spieler-IDs nicht finden`);
      }
    }
  } catch (error) {
    log(`    ❌ Fehler bei Dunkler Priester: ${error}`);
  }
}

async function handleWildesKindPhase(players: PlayerWindow[]): Promise<void> {
  log("  🐕 Wildes Kind-Phase: Wähle Vorbild... ()");

  const wildesKind = findPlayerByRole(players, ["Wildes Kind"]);
  if (!wildesKind) {
    log("    Kein Wildes Kind im Spiel");
    return;
  }

  if (shouldSkipAction()) {
    log("    ⚠️ [RANDOM] Wildes Kind überspringt");
    return;
  }

  const target = getRandomTarget(players, wildesKind);
  await selectTargetAndConfirm(wildesKind.page, target.name, [
    "Vorbild wählen",
    "Wählen",
  ]);
  log(`    Wildes Kind wählt ${target.name} als Vorbild`);
}

async function handleWolfsjungePhase(players: PlayerWindow[]): Promise<void> {
  log("  🐺👦 Wolfsjunge-Phase: Wähle Vorbild... ()");

  const wolfsjunge = findPlayerByRole(players, ["Wolfsjunge"]);
  if (!wolfsjunge) {
    log("    Kein Wolfsjunge im Spiel");
    return;
  }

  if (shouldSkipAction()) {
    log("    ⚠️ [RANDOM] Wolfsjunge überspringt");
    return;
  }

  const target = getRandomTarget(players, wolfsjunge);
  await selectTargetAndConfirm(wolfsjunge.page, target.name, [
    "Vorbild wählen",
    "Wählen",
  ]);
  log(`    Wolfsjunge wählt ${target.name} als Vorbild`);
}

async function handleHundPhase(players: PlayerWindow[]): Promise<void> {
  log("  🐶 Hund-Phase: Wähle Herrchen... ()");

  const hund = findPlayerByRole(players, ["Hund"]);
  if (!hund) {
    log("    Kein Hund im Spiel");
    return;
  }

  if (shouldSkipAction()) {
    log("    ⚠️ [RANDOM] Hund überspringt");
    return;
  }

  const target = getRandomTarget(players, hund);
  await selectTargetAndConfirm(hund.page, target.name, [
    "Herrchen wählen",
    "Wählen",
  ]);
  log(`    Hund wählt ${target.name} als Herrchen`);
}

// ============================================================================
// SEER VARIANT HANDLERS
// ============================================================================

async function handleSeherVariantPhase(
  players: PlayerWindow[],
  phase: string,
): Promise<void> {
  const roleNames = phase.toLowerCase().includes("aurenseherin")
    ? ["Aurenseherin"]
    : phase.toLowerCase().includes("seherlehrling")
      ? ["Seherlehrling"]
      : phase.toLowerCase().includes("paranormal")
        ? ["Paranormaler Ermittler"]
        : ["Seherin"];

  log(`  👁️ ${roleNames[0]}-Phase: Wähle Spieler zum Sehen... ()`);

  const seher = findPlayerByRole(players, roleNames);
  if (!seher) {
    log(`    Keine ${roleNames[0]} im Spiel`);
    return;
  }

  // Random: Sometimes skip
  if (shouldSkipAction()) {
    log(`    ⚠️ [RANDOM] ${roleNames[0]} überspringt (Test: Keine Aktion)`);
    return;
  }

  const target = getRandomTarget(players, seher, !shouldTargetWrong());
  const success = await selectTargetAndConfirm(seher.page, target.name, [
    "Aura sehen",
    "Vision",
    "Sehen",
    "Wählen",
    "Prüfen",
  ]);
  if (success) {
    log(
      `    ${roleNames[0]} sieht ${target.name} (am Leben: ${target.isAlive})`,
    );
  } else {
    log(`    ${roleNames[0]} konnte niemanden sehen`);
  }

  // Random: Try double action
  if (shouldDoubleAction()) {
    log(`    ⚠️ [RANDOM] ${roleNames[0]} versucht erneut zu sehen`);
    const target2 = getRandomTarget(players, seher);
    await selectTargetAndConfirm(seher.page, target2.name, ["Sehen", "Wählen"]);
  }
}

async function handleMediumPhase(players: PlayerWindow[]): Promise<void> {
  log("  👻 Medium-Phase: Kontaktiere Tote... ()");

  const medium = findPlayerByRole(players, ["Medium"]);
  if (!medium) {
    log("    Kein Medium im Spiel");
    return;
  }

  if (shouldSkipAction()) {
    log("    ⚠️ [RANDOM] Medium überspringt");
    return;
  }

  // Medium sees a dead player (or tries an alive one for edge case)
  const deadPlayers = players.filter((p) => !p.isAlive);
  if (deadPlayers.length === 0 && !shouldTargetWrong()) {
    log("    Keine Toten zum Kontaktieren");
    return;
  }

  const target =
    deadPlayers.length > 0 && !shouldTargetWrong()
      ? randomChoice(deadPlayers)
      : getRandomTarget(players, medium); // Edge case: target alive
  await selectTargetAndConfirm(medium.page, target.name, [
    "Geist befragen",
    "Wählen",
  ]);
  log(`    Medium kontaktiert ${target.name} (am Leben: ${target.isAlive})`);
}

async function handleTratschweibPhase(players: PlayerWindow[]): Promise<void> {
  log("  🗣️ Tratschweib-Phase: Automatische Information... ()");

  const tratschweib = findPlayerByRole(players, ["Tratschweib"]);
  if (!tratschweib) {
    log("    Kein Tratschweib im Spiel");
    return;
  }

  // Tratschweib doesn't need to take any action - it's automatic
  // Just wait a moment for the information to appear
  await sleep(1000);
  log(`    Tratschweib erhält automatisch Information über zwei Spieler`);
}

async function handleWerwolfseherinPhase(
  players: PlayerWindow[],
  werwolfe: PlayerWindow[],
): Promise<void> {
  log("  👁️🐺 Werwolfseherin-Phase: Sieht mit den Wölfen... ()");

  const werwolfseherin = findPlayerByRole(players, ["Werwolfseherin"]);
  if (!werwolfseherin) {
    log("    Keine Werwolfseherin im Spiel");
    return;
  }

  if (shouldSkipAction()) {
    log("    ⚠️ [RANDOM] Werwolfseherin überspringt");
    return;
  }

  // She sees another wolf (or edge case: any player)
  const otherWolves = werwolfe.filter((w) => w !== werwolfseherin && w.isAlive);
  const target =
    otherWolves.length === 0 || shouldTargetWrong()
      ? getRandomTarget(players, werwolfseherin)
      : randomChoice(otherWolves);

  await selectTargetAndConfirm(werwolfseherin.page, target.name, [
    "Sehen",
    "Wählen",
  ]);
  log(`    Werwolfseherin sieht ${target.name}`);
}

// ============================================================================
// HEALER VARIANT HANDLERS
// ============================================================================

async function handleHeilerVariantPhase(
  players: PlayerWindow[],
  dorfbewohner: PlayerWindow[],
  phase: string,
): Promise<void> {
  const roleNames = phase.toLowerCase().includes("leibwaechter")
    ? ["Leibwächter"]
    : ["Heiler"];

  log(
    `  💉 ${roleNames[0]}-Phase: Wähle Spieler zum Schützen... ()`,
  );

  const heiler = findPlayerByRole(players, roleNames);
  if (!heiler) {
    log(`    Kein ${roleNames[0]} im Spiel`);
    return;
  }

  // Random: Sometimes skip
  if (shouldSkipAction()) {
    log(`    ⚠️ [RANDOM] ${roleNames[0]} überspringt (Test: Keine Heilung)`);
    return;
  }

  // Random target from all players (not just dorfbewohner for edge cases)
  const target = getRandomTarget(players, heiler, !shouldTargetWrong());
  await selectTargetAndConfirm(heiler.page, target.name, [
    "Schützen",
    "Heilen",
    "Wählen",
  ]);
  log(
    `    ${roleNames[0]} schützt ${target.name} (am Leben: ${target.isAlive})`,
  );
}

async function handleHurePhase(players: PlayerWindow[], phaseName?: string): Promise<void> {
  log("  💋 Hure/Prostituierte-Phase: Besuche Spieler... ()");

  // If phase name is provided, try to match specific variant first
  let hure: PlayerWindow | undefined;
  if (phaseName) {
    const normalizedPhaseName = phaseName.toLowerCase().replace(/_/g, "");
    if (normalizedPhaseName.includes("hure")) {
      hure = findPlayerByRole(players, ["Hure"]);
    } else if (normalizedPhaseName.includes("nutte")) {
      hure = findPlayerByRole(players, ["Nutte"]);
    } else if (normalizedPhaseName.includes("prostituierte")) {
      hure = findPlayerByRole(players, ["Prostituierte"]);
    }
  }
  
  // Fallback to any matching role
  if (!hure) {
    hure = findPlayerByRole(players, ["Hure", "Prostituierte", "Nutte"]);
  }
  
  if (!hure) {
    log("    Keine Hure im Spiel");
    return;
  }

  log(`    Gefunden: ${hure.name} (${hure.rolle})`);

  if (shouldSkipAction()) {
    log("    ⚠️ [RANDOM] Hure überspringt");
    return;
  }

  const target = getRandomTarget(players, hure, !shouldTargetWrong());
  await selectTargetAndConfirm(hure.page, target.name, ["Besuchen", "Wählen"]);
  log(`    ${hure.rolle} besucht ${target.name} (am Leben: ${target.isAlive})`);
}

// ============================================================================
// WEREWOLF VARIANT HANDLERS
// ============================================================================

async function handleEinsamerWolfPhase(
  einsameWoelfe: PlayerWindow[],
  dorfbewohner: PlayerWindow[],
): Promise<void> {
  log("  🐺💀 Einsamer Wolf-Phase: Eigene Tötung... ()");

  const aliveEinsameWoelfe = einsameWoelfe.filter((w) => w.isAlive);
  if (aliveEinsameWoelfe.length === 0) {
    log("    Kein lebender Einsamer Wolf");
    return;
  }

  if (shouldSkipAction()) {
    log("    ⚠️ [RANDOM] Einsamer Wolf überspringt");
    return;
  }

  const allPlayers = [...dorfbewohner, ...einsameWoelfe];

  for (const wolf of aliveEinsameWoelfe) {
    const target = getRandomTarget(allPlayers, wolf, !shouldTargetWrong());
    await selectTargetAndConfirm(wolf.page, target.name, [
      "Töten",
      "Angreifen",
      "Wählen",
    ]);
    log(
      `    ${wolf.name} (Einsamer Wolf) greift ${target.name} an (am Leben: ${target.isAlive})`,
    );
  }
}

async function handleUrwolfPhase(
  players: PlayerWindow[],
  _dorfbewohner: PlayerWindow[],
): Promise<void> {
  log("  🐺⚡ Urwolf-Phase: Verwandle oder töte... ()");

  const urwolf = findPlayerByRole(players, ["Urwolf"]);
  if (!urwolf) {
    log("    Kein Urwolf im Spiel");
    return;
  }

  if (shouldSkipAction()) {
    log("    ⚠️ [RANDOM] Urwolf überspringt");
    return;
  }

  // Random target from all players
  const target = getRandomTarget(players, urwolf, !shouldTargetWrong());
  await selectTargetAndConfirm(urwolf.page, target.name, [
    "Infizieren",
    "Wählen",
  ]);
  log(
    `    Urwolf versucht ${target.name} zu infizieren (am Leben: ${target.isAlive})`,
  );
}

async function handleWeisserWolfPhase(
  players: PlayerWindow[],
  werwolfe: PlayerWindow[],
): Promise<void> {
  log("  🐺⚪ Weißer Wolf-Phase: Töte Mitwolf... ()");

  const weisserWolf = findPlayerByRole(players, ["Weißer Wolf"]);
  if (!weisserWolf) {
    log("    Kein Weißer Wolf im Spiel");
    return;
  }

  if (shouldSkipAction()) {
    log("    ⚠️ [RANDOM] Weißer Wolf überspringt");
    return;
  }

  // White wolf kills another wolf (or edge case: anyone)
  const otherWolves = werwolfe.filter((w) => w !== weisserWolf && w.isAlive);

  // Random decision to kill or not
  if (seededRandom() > 0.5) {
    const target =
      otherWolves.length === 0 || shouldTargetWrong()
        ? getRandomTarget(players, weisserWolf)
        : randomChoice(otherWolves);
    await selectTargetAndConfirm(weisserWolf.page, target.name, [
      "Töten",
      "Wählen",
    ]);
    log(`    Weißer Wolf tötet ${target.name}`);
  } else {
    log("    Weißer Wolf überspringt diese Nacht");
  }
}

async function handleMordlustigerPhase(players: PlayerWindow[]): Promise<void> {
  log("  🔪 Mordlustiger-Phase: Zusätzliche Tötung... ()");

  const mordlustiger = findPlayerByRole(players, ["Mordlustiger"]);
  if (!mordlustiger) {
    log("    Kein Mordlustiger im Spiel");
    return;
  }

  if (shouldSkipAction()) {
    log("    ⚠️ [RANDOM] Mordlustiger überspringt");
    return;
  }

  // Check if the skip button is visible (Mordlustiger can skip)
  const skipBtn = mordlustiger.page.locator('button:has-text("Überspringen")').first();
  if (await skipBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
    // Randomly decide to skip or act
    if (seededRandom() > 0.5) {
      await skipBtn.click();
      log("    Mordlustiger überspringt diese Nacht");
      return;
    }
  }

  const target = getRandomTarget(players, mordlustiger, !shouldTargetWrong());
  await selectTargetAndConfirm(mordlustiger.page, target.name, [
    "Ermorden",
    "Wählen",
  ]);
  log(`    Mordlustiger tötet ${target.name} (am Leben: ${target.isAlive})`);
}

// ============================================================================
// HEXE VARIANT HANDLERS
// ============================================================================

async function handleHexePhase(players: PlayerWindow[]): Promise<void> {
  log("  🧙 Hexe-Phase: Entscheide über Heilen/Töten... ()");

  const hexe = findPlayerByRole(players, ["Hexe"]);
  if (!hexe) {
    log("    Keine Hexe im Spiel");
    return;
  }

  // Random: Sometimes skip entirely
  if (shouldSkipAction()) {
    log("    ⚠️ [RANDOM] Hexe überspringt (Test: Keine Aktion)");
    return;
  }

  // Fully random decision: 0-1 random actions
  const actions = ["heal", "kill", "skip", "both"]; // "both" tests doing heal AND kill
  const action = randomChoice(actions);

  try {
    if (action === "heal" || action === "both") {
      const healBtn = hexe.page.locator('button:has-text("Heilen")').first();
      if (await healBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
        await healBtn.click();
        log(`    Hexe heilt das Opfer`);
        await sleep(500);
      }
    }

    if (action === "kill" || action === "both") {
      // Random target - including dead players for edge case
      const allPlayers = players.filter((p) => p.rolle !== "Hexe");
      if (allPlayers.length > 0) {
        const target = randomChoice(allPlayers);
        await selectTargetAndConfirm(hexe.page, target.name, [
          "Töten",
          "Vergiften",
        ]);
        log(`    Hexe vergiftet ${target.name} (am Leben: ${target.isAlive})`);
      }
    }

    if (action === "skip") {
      const skipBtn = hexe.page
        .locator(
          'button:has-text("Nicht heilen"), button:has-text("Überspringen"), button:has-text("Weiter"), button:has-text("Nichts tun")',
        )
        .first();
      if (await skipBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
        await skipBtn.click();
        log(`    Hexe überspringt`);
      }
    }

    // Random: Try double action
    if (shouldDoubleAction()) {
      log("    ⚠️ [RANDOM] Hexe versucht erneut zu handeln");
      const healBtn = hexe.page.locator('button:has-text("Heilen")').first();
      if (await healBtn.isVisible({ timeout: 500 }).catch(() => false)) {
        await healBtn.click();
      }
    }
  } catch (e) {
    log(`    Hexe konnte nicht handeln: ${e}`);
  }
}

async function handleHexenmeisterPhase(players: PlayerWindow[]): Promise<void> {
  log("  🧙‍♂️ Hexenmeister-Phase: Verzaubere... ()");

  const hexenmeister = findPlayerByRole(players, ["Hexenmeister"]);
  if (!hexenmeister) {
    log("    Kein Hexenmeister im Spiel");
    return;
  }

  if (shouldSkipAction()) {
    log("    ⚠️ [RANDOM] Hexenmeister überspringt");
    return;
  }

  const target = getRandomTarget(players, hexenmeister, !shouldTargetWrong());
  await selectTargetAndConfirm(hexenmeister.page, target.name, [
    "Verfluchen",
    "Wählen",
  ]);
  log(`    Hexenmeister verflucht ${target.name}`);
}

async function handleGiftmischerinPhase(
  players: PlayerWindow[],
): Promise<void> {
  log("  🧪 Giftmischerin-Phase: Vergebe Gift... ()");

  const giftmischerin = findPlayerByRole(players, ["Giftmischerin"]);
  if (!giftmischerin) {
    log("    Keine Giftmischerin im Spiel");
    return;
  }

  if (shouldSkipAction()) {
    log("    ⚠️ [RANDOM] Giftmischerin überspringt");
    return;
  }

  const target = getRandomTarget(players, giftmischerin, !shouldTargetWrong());
  await selectTargetAndConfirm(giftmischerin.page, target.name, [
    "Vergiften",
    "Wählen",
  ]);
  log(`    Giftmischerin vergiftet ${target.name}`);
}

async function handleKraeuterweibPhase(players: PlayerWindow[]): Promise<void> {
  log("  🌿 Kräuterweib-Phase: Verteile Kräuter... ()");

  const kraeuterweib = findPlayerByRole(players, ["Kräuterweib"]);
  if (!kraeuterweib) {
    log("    Kein Kräuterweib im Spiel");
    return;
  }

  if (shouldSkipAction()) {
    log("    ⚠️ [RANDOM] Kräuterweib überspringt");
    return;
  }

  const target = getRandomTarget(players, kraeuterweib, !shouldTargetWrong());
  await selectTargetAndConfirm(kraeuterweib.page, target.name, [
    "Stumm machen",
    "Wählen",
  ]);
  log(`    Kräuterweib macht ${target.name} stumm`);
}

async function handleZaubererPhase(players: PlayerWindow[]): Promise<void> {
  log("  ✨ Zauberer-Phase: Wirke Zauber... ()");

  const zauberer = findPlayerByRole(players, ["Zauberer"]);
  if (!zauberer) {
    log("    Kein Zauberer im Spiel");
    return;
  }

  if (shouldSkipAction()) {
    log("    ⚠️ [RANDOM] Zauberer überspringt");
    return;
  }

  const target = getRandomTarget(players, zauberer, !shouldTargetWrong());
  await selectTargetAndConfirm(zauberer.page, target.name, [
    "Schutz-Zauber",
    "Sicht-Zauber",
    "Schweigen-Zauber",
    "Wählen",
  ]);
  log(`    Zauberer zaubert auf ${target.name}`);
}

async function handleSandmannPhase(players: PlayerWindow[]): Promise<void> {
  log("  😴 Sandmann-Phase: Schläfere ein... ()");

  const sandmann = findPlayerByRole(players, ["Sandmann"]);
  if (!sandmann) {
    log("    Kein Sandmann im Spiel");
    return;
  }

  if (shouldSkipAction()) {
    log("    ⚠️ [RANDOM] Sandmann überspringt");
    return;
  }

  const target = getRandomTarget(players, sandmann, !shouldTargetWrong());
  await selectTargetAndConfirm(sandmann.page, target.name, [
    "Einschläfern",
    "Wählen",
  ]);
  log(`    Sandmann schläfert ${target.name} ein`);
}

// ============================================================================
// OTHER NIGHT ROLE HANDLERS
// ============================================================================

async function handleZahnarztPhase(players: PlayerWindow[]): Promise<void> {
  log("  🦷 Zahnarzt-Phase: Behandle Zähne... ()");

  const zahnarzt = findPlayerByRole(players, ["Zahnarzt"]);
  if (!zahnarzt) {
    log("    Kein Zahnarzt im Spiel");
    return;
  }

  if (shouldSkipAction()) {
    log("    ⚠️ [RANDOM] Zahnarzt überspringt");
    return;
  }

  const target = getRandomTarget(players, zahnarzt, !shouldTargetWrong());
  await selectTargetAndConfirm(zahnarzt.page, target.name, [
    "Behandeln",
    "Wählen",
  ]);
  log(`    Zahnarzt behandelt ${target.name}`);
}

async function handleRabePhase(players: PlayerWindow[]): Promise<void> {
  log("  🐦 Rabe-Phase: Markiere verdächtigen... ()");

  const rabe = findPlayerByRole(players, ["Rabe"]);
  if (!rabe) {
    log("    Kein Rabe im Spiel");
    return;
  }

  if (shouldSkipAction()) {
    log("    ⚠️ [RANDOM] Rabe überspringt");
    return;
  }

  const target = getRandomTarget(players, rabe, !shouldTargetWrong());
  await selectTargetAndConfirm(rabe.page, target.name, ["Markieren", "Wählen"]);
  log(`    Rabe markiert ${target.name}`);
}

async function handleFloetenspielerPhase(
  players: PlayerWindow[],
): Promise<void> {
  log("  🎵 Flötenspieler-Phase: Verzaubere... ()");

  const floetenspieler = findPlayerByRole(players, ["Flötenspieler"]);
  if (!floetenspieler) {
    log("    Kein Flötenspieler im Spiel");
    return;
  }

  if (shouldSkipAction()) {
    log("    ⚠️ [RANDOM] Flötenspieler überspringt");
    return;
  }

  const target = getRandomTarget(players, floetenspieler, !shouldTargetWrong());
  await selectTargetAndConfirm(floetenspieler.page, target.name, [
    "Verzaubern",
    "Wählen",
  ]);
  log(`    Flötenspieler verzaubert ${target.name}`);
}

async function handleVampirPhase(players: PlayerWindow[]): Promise<void> {
  log("  🧛 Vampir-Phase: Beiße... ()");

  const vampir = findPlayerByRole(players, ["Vampir"]);
  if (!vampir) {
    log("    Kein Vampir im Spiel");
    return;
  }

  if (shouldSkipAction()) {
    log("    ⚠️ [RANDOM] Vampir überspringt");
    return;
  }

  const target = getRandomTarget(players, vampir, !shouldTargetWrong());
  await selectTargetAndConfirm(vampir.page, target.name, ["Beißen", "Wählen"]);
  log(`    Vampir beißt ${target.name}`);
}

async function handleZombiePhase(players: PlayerWindow[]): Promise<void> {
  log("  🧟 Zombie-Phase: Erwecke Toten... ()");

  const zombie = findPlayerByRole(players, ["Zombie"]);
  if (!zombie) {
    log("    Kein Zombie im Spiel");
    return;
  }

  if (shouldSkipAction()) {
    log("    ⚠️ [RANDOM] Zombie überspringt");
    return;
  }

  // Zombie can revive dead players (or try alive for edge case)
  const deadPlayers = players.filter((p) => !p.isAlive);
  if (deadPlayers.length === 0 && !shouldTargetWrong()) {
    log("    Keine Toten zum Erwecken");
    return;
  }

  const target =
    deadPlayers.length > 0 && !shouldTargetWrong()
      ? randomChoice(deadPlayers)
      : getRandomTarget(players, zombie); // Edge case: target alive
  await selectTargetAndConfirm(zombie.page, target.name, [
    "Erwecken",
    "Wählen",
  ]);
  log(`    Zombie erweckt ${target.name} (am Leben: ${target.isAlive})`);
}

async function handlePyromanePhase(players: PlayerWindow[]): Promise<void> {
  log("  🔥 Pyromane-Phase: Markiere oder zünde... ()");

  const pyromane = findPlayerByRole(players, ["Pyromane"]);
  if (!pyromane) {
    log("    Kein Pyromane im Spiel");
    return;
  }

  if (shouldSkipAction()) {
    log("    ⚠️ [RANDOM] Pyromane überspringt");
    return;
  }

  // Pyromane can douse or ignite (random decision)
  const action = seededRandom() > 0.7 ? "ignite" : "douse";

  if (action === "ignite") {
    const igniteBtn = pyromane.page
      .locator('button:has-text("Anzünden"), button:has-text("Entzünden")')
      .first();
    if (await igniteBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
      await igniteBtn.click();
      log("    Pyromane zündet alle markierten an!");
      return;
    }
  }

  const target = getRandomTarget(players, pyromane, !shouldTargetWrong());
  await selectTargetAndConfirm(pyromane.page, target.name, [
    "Markieren",
    "Übergießen",
    "Wählen",
  ]);
  log(`    Pyromane markiert ${target.name}`);
}

async function handleTonksPhase(players: PlayerWindow[]): Promise<void> {
  log("  🎭 Tonks-Phase: Verwandle Aussehen... ()");

  const tonks = findPlayerByRole(players, ["Tonks"]);
  if (!tonks) {
    log("    Kein Tonks im Spiel");
    return;
  }

  if (shouldSkipAction()) {
    log("    ⚠️ [RANDOM] Tonks überspringt");
    return;
  }

  const target = getRandomTarget(players, tonks, !shouldTargetWrong());
  await selectTargetAndConfirm(tonks.page, target.name, [
    "Verwandeln",
    "Wählen",
  ]);
  log(`    Tonks nimmt die Gestalt von ${target.name} an`);
}

async function handleBuddlerPhase(players: PlayerWindow[]): Promise<void> {
  log("  ⛏️ Buddler-Phase: Grabe Grab aus... ()");

  const buddler = findPlayerByRole(players, ["Buddler"]);
  if (!buddler) {
    log("    Kein Buddler im Spiel");
    return;
  }

  if (shouldSkipAction()) {
    log("    ⚠️ [RANDOM] Buddler überspringt");
    return;
  }

  // Buddler can dig up dead player's role (or try alive for edge case)
  const deadPlayers = players.filter((p) => !p.isAlive);
  if (deadPlayers.length === 0 && !shouldTargetWrong()) {
    log("    Keine Toten zum Ausgraben");
    return;
  }

  const target =
    deadPlayers.length > 0 && !shouldTargetWrong()
      ? randomChoice(deadPlayers)
      : getRandomTarget(players, buddler); // Edge case: target alive
  await selectTargetAndConfirm(buddler.page, target.name, [
    "Ausgraben",
    "Wählen",
  ]);
  log(
    `    Buddler gräbt ${target.name}s Grab aus (am Leben: ${target.isAlive})`,
  );
}

async function handleHenkerPhase(players: PlayerWindow[]): Promise<void> {
  log("  🪓 Henker-Phase: Wähle Ziel zum Hängen... ()");

  const henker = findPlayerByRole(players, ["Henker"]);
  if (!henker) {
    log("    Kein Henker im Spiel");
    return;
  }

  log(`    DEBUG: Henker gefunden: ${henker.name} (Rolle: ${henker.rolle})`);

  if (shouldSkipAction()) {
    log("    ⚠️ [RANDOM] Henker überspringt");
    return;
  }

  const target = getRandomTarget(players, henker, !shouldTargetWrong());
  log(`    DEBUG: Ziel ausgewählt: ${target.name}`);
  
  // Wait for UI to be ready
  await sleep(1500);
  
  // Check if Henker's page is active for this phase
  const hasUI = await henker.page.evaluate(() => {
    const panel = document.querySelector('.action-panel, .aktions-panel');
    return panel !== null && panel.textContent?.includes('Henker');
  }).catch(() => false);
  
  log(`    DEBUG: Hat Henker UI? ${hasUI}`);
  
  if (!hasUI) {
    log("    ⚠️ Henker hat noch keine Aktions-UI, warte...");
    await sleep(2000);
  }

  await selectTargetAndConfirm(henker.page, target.name, [
    "Ziel wählen",
    "Wählen",
  ]);
  log(`    Henker wählt ${target.name} als Ziel`);
}

// ============================================================================
// DAY PHASE HANDLERS
// ============================================================================

async function handleDiskussionPhase(players: PlayerWindow[]): Promise<void> {
  log("  💬 Diskussion: Spieler chatten... ()");

  const chatMessages = [
    "Ich bin unschuldig!",
    "Der da ist verdächtig!",
    "Wer hat heute Nacht geschrien?",
    "Ich glaube, wir haben einen Wolf gefunden.",
    "Das ergibt keinen Sinn...",
    "Lasst uns nachdenken.",
    "Ich sage es ist ${target}!",
    "Warte, ich habe etwas beobachtet.",
    "Vertraut mir, ich bin Dorfbewohner!",
    "Wir müssen abstimmen!",
    "Die Wölfe haben wieder zugeschlagen...",
    // Edge case messages
    "",
    "   ",
    "a".repeat(500), // Very long message
    "<script>alert('xss')</script>", // XSS attempt
    "🐺🐺🐺🐺🐺🐺🐺🐺", // Lots of emojis
    "SELECT * FROM users;", // SQL injection attempt
    "null",
    "undefined",
    '{"test": true}',
  ];

  const alivePlayers = players.filter((p) => p.isAlive);
  const chatCount = Math.floor(seededRandom() * 6) + 1; // 1-6 messages

  for (let i = 0; i < chatCount; i++) {
    if (alivePlayers.length === 0) break;

    const chatter = randomChoice(alivePlayers);
    let message = randomChoice(chatMessages).replace(
      "${target}",
      randomChoice(players).name,
    );

    // Random: Sometimes send rapid-fire messages
    if (shouldDoubleAction()) {
      log(`    ⚠️ [RANDOM] ${chatter.name} spammt Chat`);
      for (let j = 0; j < 3; j++) {
        try {
          const chatInput = chatter.page.locator("#chat-input");
          if (await chatInput.isVisible({ timeout: 500 }).catch(() => false)) {
            await chatInput.fill(randomChoice(chatMessages));
            await chatInput.press("Enter");
          }
        } catch (e) { }
        await sleep(50);
      }
    }

    try {
      const chatInput = chatter.page.locator("#chat-input");
      if (await chatInput.isVisible({ timeout: 1000 }).catch(() => false)) {
        await chatInput.fill(message);
        await chatInput.press("Enter");
        log(
          `    ${chatter.name}: "${message.substring(0, 50)}${message.length > 50 ? "..." : ""}"`,
        );
      }
    } catch (e) {
      // Chat failed, continue
    }
    await sleep(200);
  }

  await sleep(1000);
}

async function handleAbstimmungPhase(
  players: PlayerWindow[],
  _werwolfe: PlayerWindow[],
): Promise<void> {
  log("  🗳️ Abstimmung: Spieler stimmen ab... ()");

  const alivePlayers = players.filter((p) => p.isAlive);
  const allPlayers = players; // For edge case testing (voting for dead)

  // Random: Sometimes some players don't vote at all
  for (const voter of alivePlayers) {
    // Random skip - DISABLED to ensure phase completion
    /*
    if (shouldSkipAction()) {
      log(
        `    ⚠️ [RANDOM] ${voter.name} enthält sich (Test: Unvollständige Abstimmung)`,
      );
      continue;
    }
    */

    let voteTarget: PlayerWindow;

    // Full randomness in voting
    if (shouldRandomVote()) {
      // Completely random target (including dead, self, etc.)
      if (shouldTargetSelf()) {
        voteTarget = voter;
        log(
          `    ⚠️ [RANDOM] ${voter.name} versucht für sich selbst zu stimmen`,
        );
      } else if (shouldTargetWrong()) {
        const deadPlayers = allPlayers.filter((p) => !p.isAlive);
        voteTarget =
          deadPlayers.length > 0
            ? randomChoice(deadPlayers)
            : randomChoice(alivePlayers);
        log(
          `    ⚠️ [RANDOM] ${voter.name} stimmt für toten Spieler: ${voteTarget.name}`,
        );
      } else {
        voteTarget = randomChoice(alivePlayers);
      }
    } else {
      // Slightly smarter but still random voting
      voteTarget = randomChoice(alivePlayers);
    }

    if (!voteTarget) continue;

    try {
      await selectTargetAndConfirm(voter.page, voteTarget.name, [
        "Wählen",
        "Abstimmen",
        "Hinrichten",
      ]);
      log(`    ${voter.name} → ${voteTarget.name}`);
    } catch (e) {
      log(`    ${voter.name} konnte nicht abstimmen`);
    }

    // Random: Try to vote again
    if (shouldDoubleAction()) {
      log(`    ⚠️ [RANDOM] ${voter.name} versucht erneut abzustimmen`);
      const newTarget = randomChoice(alivePlayers);
      await selectTargetAndConfirm(voter.page, newTarget.name, [
        "Wählen",
        "Abstimmen",
      ]);
    }

    await sleep(100);
  }
}

async function handleJaegerPhase(
  players: PlayerWindow[],
  _werwolfe: PlayerWindow[],
): Promise<void> {
  log("  🎯 Jäger-Phase: Wähle Ziel zum Erschießen... ()");

  // Find dying hunter
  const jaeger = players.find(
    (p) =>
      (p.rolle?.toLowerCase().includes("jäger") ||
        p.rolle?.toLowerCase().includes("jaeger")) &&
      !p.isAlive,
  );

  if (!jaeger) {
    const aliveJaeger = findPlayerByRole(players, ["Jäger", "Jaeger"]);
    if (!aliveJaeger || aliveJaeger.isAlive) {
      log("    Kein sterbender Jäger");
      return;
    }
  }

  const hunter = jaeger || findPlayerByRole(players, ["Jäger", "Jaeger"]);
  if (!hunter) return;

  // Random: Sometimes skip (test: what if hunter doesn't shoot?)
  if (shouldSkipAction()) {
    log("    ⚠️ [RANDOM] Jäger schießt nicht (Test: Kein Schuss)");
    return;
  }

  // Fully random target (including dead players, wolves, villagers)
  const target = getRandomTarget(players, hunter, !shouldTargetWrong());

  if (!target) return;

  await selectTargetAndConfirm(hunter.page, target.name, [
    "Erschießen",
    "Wählen",
  ]);
  log(`    Jäger erschießt ${target.name} (am Leben: ${target.isAlive})`);
  if (target.isAlive) target.isAlive = false;
}

async function handleKamikazePhase(
  players: PlayerWindow[],
  _werwolfe: PlayerWindow[],
): Promise<void> {
  log("  💣 Kamikaze-Phase: Selbstmordanschlag... ()");

  const kamikaze = findPlayerByRole(players, ["Kamikaze"]);
  if (!kamikaze) {
    log("    Kein Kamikaze im Spiel");
    return;
  }

  // Random: Sometimes skip
  if (shouldSkipAction()) {
    log("    ⚠️ [RANDOM] Kamikaze zündet nicht (Test: Kein Anschlag)");
    return;
  }

  // Fully random target
  const target = getRandomTarget(players, kamikaze, !shouldTargetWrong());

  if (!target) return;

  await selectTargetAndConfirm(kamikaze.page, target.name, [
    "Explodieren",
    "Mitnehmen",
    "Wählen",
  ]);
  log(
    `    Kamikaze reißt ${target.name} mit in den Tod! (am Leben: ${target.isAlive})`,
  );
  if (kamikaze.isAlive) kamikaze.isAlive = false;
  if (target.isAlive) target.isAlive = false;
}

// ============================================================================
// AMOR PHASE (kept separate as it's special)
// ============================================================================

async function handleAmorPhase(players: PlayerWindow[]): Promise<void> {
  log("  💕 Amor-Phase (amor_phase): Wähle Liebespaar... ()");

  const amor = findPlayerByRole(players, ["Amor"]);
  if (!amor) {
    log("    Kein Amor im Spiel");
    return;
  }

  // Random: Sometimes skip
  if (shouldSkipAction()) {
    log("    ⚠️ [RANDOM] Amor überspringt (Test: Kein Liebespaar)");
    return;
  }

  const targets = players.filter((p) => p !== amor && p.isAlive);
  if (targets.length < 2) {
    log("    Nicht genug Spieler für Liebespaar");
    return;
  }

  // Random selection (possibly including dead for edge case)
  let lover1: PlayerWindow, lover2: PlayerWindow;

  if (shouldTargetWrong()) {
    // Edge case: Try to include self or same person twice
    lover1 = shouldTargetSelf() ? amor : randomChoice(targets);
    lover2 = shouldDoubleAction() ? lover1 : randomChoice(targets); // Same person twice?
    log(`    ⚠️ [RANDOM] Amor versucht ungültige Kombination`);
  } else {
    const shuffled = [...targets].sort(() => seededRandom() - 0.5);
    lover1 = shuffled[0];
    lover2 = shuffled[1];
  }

  try {
    // Amor muss 2 Spieler auswählen (selectedSpielerIds Array)
    // Klicke auf ersten Spieler
    const card1 = amor.page.locator(
      `.spieler-card[data-name="${lover1.name}"]`,
    );
    if (await card1.isVisible({ timeout: 2000 }).catch(() => false)) {
      await card1.click();
      log(`    Erster Liebhaber ausgewählt: ${lover1.name}`);
      await sleep(500);
    } else {
      // Fallback: Suche nach Text
      const card1Alt = amor.page
        .locator(`.spieler-card:has-text("${lover1.name}")`)
        .first();
      if (await card1Alt.isVisible({ timeout: 1000 }).catch(() => false)) {
        await card1Alt.click();
        log(`    Erster Liebhaber ausgewählt: ${lover1.name}`);
        await sleep(500);
      }
    }

    // Klicke auf zweiten Spieler
    const card2 = amor.page.locator(
      `.spieler-card[data-name="${lover2.name}"]`,
    );
    if (await card2.isVisible({ timeout: 2000 }).catch(() => false)) {
      await card2.click();
      log(`    Zweiter Liebhaber ausgewählt: ${lover2.name}`);
      await sleep(500);
    } else {
      // Fallback: Suche nach Text
      const card2Alt = amor.page
        .locator(`.spieler-card:has-text("${lover2.name}")`)
        .first();
      if (await card2Alt.isVisible({ timeout: 1000 }).catch(() => false)) {
        await card2Alt.click();
        log(`    Zweiter Liebhaber ausgewählt: ${lover2.name}`);
        await sleep(500);
      }
    }

    // Warte kurz bis die UI aktualisiert ist (2/2 Spieler ausgewählt)
    await sleep(800);

    // Jetzt sollte der "Verlieben" Button erscheinen
    const actionBtn = amor.page.locator('button:has-text("Verlieben")').first();
    if (await actionBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await actionBtn.click();
      log(`    ❤️ Amor verliebt ${lover1.name} und ${lover2.name}`);
    } else {
      // Fallback: Hole IDs aus den Karten und sende direkt via Socket
      log("    Button nicht gefunden, versuche direkte Socket-Aktion...");

      const id1 = await amor.page
        .locator(`.spieler-card[data-name="${lover1.name}"]`)
        .getAttribute("data-id")
        .catch(() => null);
      const id2 = await amor.page
        .locator(`.spieler-card[data-name="${lover2.name}"]`)
        .getAttribute("data-id")
        .catch(() => null);

      if (id1 && id2) {
        await amor.page.evaluate(
          ([playerId1, playerId2]) => {
            if ((window as any).socket) {
              (window as any).socket.emit("aktion_ausfuehren", {
                aktion: "amor_verlieben",
                ziel_id: [parseInt(playerId1), parseInt(playerId2)],
              });
            }
          },
          [id1, id2],
        );
        log(
          `    ❤️ Amor verliebt ${lover1.name} (ID:${id1}) und ${lover2.name} (ID:${id2}) via Socket`,
        );
      } else {
        log(`    ❌ Konnte Spieler-IDs nicht finden`);
      }
    }
  } catch (e) {
    log(`    ❌ Amor konnte nicht verlieben: ${e}`);
  }
}

// ============================================================================
// VALIDATION FUNCTIONS
// ============================================================================

/**
 * Validate that werewolves can see each other (and themselves) during werewolf phase
 * This checks for the werwolf-team-sichtbar class on player cards
 */
async function validateWerwolfVisibility(
  allWerwolfe: PlayerWindow[],
  activeWolves: PlayerWindow[],
): Promise<void> {
  log("    🔍 VALIDATION: Checking werewolf visibility...");

  for (const wolf of activeWolves) {
    // Give UI time to update
    await sleep(500);

    // Check that this wolf can see all other werewolves
    for (const otherWolf of allWerwolfe) {
      const card = wolf.page.locator(`.spieler-card[data-name="${otherWolf.name}"]`);

      // Verify card exists
      if (!(await card.isVisible({ timeout: 2000 }).catch(() => false))) {
        throw new Error(`❌ HARD ERROR: ${wolf.name} cannot see player card for ${otherWolf.name}`);
      }

      // Check if card has werwolf visibility class OR is self (ist-ich class)
      const hasWolfClass = await card.evaluate((el) =>
        el.classList.contains('werwolf-team-sichtbar') || el.classList.contains('ist-ich')
      );

      // Get data-rolle attribute (should contain werewolf role)
      const dataRolle = await card.getAttribute('data-rolle');

      if (!hasWolfClass && wolf.name !== otherWolf.name) {
        throw new Error(`❌ HARD ERROR: ${wolf.name} cannot see ${otherWolf.name} as werewolf (missing werwolf-team-sichtbar class)`);
      }

      if (wolf.name === otherWolf.name && !hasWolfClass) {
        throw new Error(`❌ HARD ERROR: ${wolf.name} cannot see themselves as werewolf (missing ist-ich class)`);
      }

      if (otherWolf.isAlive && !dataRolle) {
        throw new Error(`❌ HARD ERROR: ${wolf.name} cannot see role data for ${otherWolf.name} (data-rolle attribute is empty)`);
      }
    }

    // Validate nametags are visible and don't disappear
    await validateNametags(wolf.page, allWerwolfe);
  }

  log("    ✅ Werewolf visibility validated!");
}

/**
 * Validate that lovers (Verliebte) can see each other's roles
 */
async function validateVerliebteVisibility(players: PlayerWindow[]): Promise<void> {
  log("    🔍 VALIDATION: Checking Verliebte visibility...");

  // Find players with verliebt-partner class on other cards
  for (const player of players.filter(p => p.isAlive)) {
    const partnerCards = await player.page.locator('.spieler-card.verliebt-partner').count();

    if (partnerCards > 0) {
      // This player is verliebt, check they can see their partner
      log(`    💕 ${player.name} is verliebt, checking partner visibility...`);

      // There should be exactly 1 partner card
      if (partnerCards !== 1) {
        throw new Error(`❌ HARD ERROR: ${player.name} has ${partnerCards} partner cards, expected 1`);
      }

      const partnerCard = player.page.locator('.spieler-card.verliebt-partner').first();

      // Partner card must be visible
      if (!(await partnerCard.isVisible({ timeout: 2000 }).catch(() => false))) {
        throw new Error(`❌ HARD ERROR: ${player.name} cannot see partner card`);
      }

      // Partner card must have data-rolle attribute (shows the role)
      const partnerRolle = await partnerCard.getAttribute('data-rolle');
      const partnerName = await partnerCard.getAttribute('data-name');

      if (!partnerRolle) {
        throw new Error(`❌ HARD ERROR: ${player.name} cannot see partner's role (data-rolle empty for ${partnerName})`);
      }

      log(`    ✅ ${player.name} can see partner ${partnerName} with role ${partnerRolle}`);

      // Validate nametags
      await validateNametags(player.page, [player]);
    }
  }

  log("    ✅ Verliebte visibility validated!");
}

/**
 * Validate that nametags stay visible and don't disappear after a second
 */
async function validateNametags(page: Page, players: PlayerWindow[]): Promise<void> {
  for (const player of players.filter(p => p.isAlive)) {
    const card = page.locator(`.spieler-card[data-name="${player.name}"]`);
    const nameElement = card.locator('.spieler-name');

    // Check visibility at t=0
    const visible1 = await nameElement.isVisible({ timeout: 1000 }).catch(() => false);
    if (!visible1) {
      throw new Error(`❌ HARD ERROR: Nametag for ${player.name} is not visible initially`);
    }

    // Wait 1.5 seconds and check again
    await sleep(1500);
    const visible2 = await nameElement.isVisible({ timeout: 500 }).catch(() => false);
    if (!visible2) {
      throw new Error(`❌ HARD ERROR: Nametag for ${player.name} disappeared after 1.5 seconds`);
    }
  }
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function findPlayerByRole(
  players: PlayerWindow[],
  roleNames: string[],
): PlayerWindow | undefined {
  return players.find(
    (p) =>
      p.isAlive &&
      roleNames.some((role) =>
        p.rolle?.toLowerCase().includes(role.toLowerCase()),
      ),
  );
}

async function selectTargetAndConfirm(
  page: Page,
  targetName: string,
  buttonTexts: string[],
): Promise<boolean> {
  // Wait for the current phase to finish loading on this specific page
  // This ensures SocketIO phase_update has been received and processed
  await page.waitForFunction(
    () => {
      const panel = document.getElementById('action-panel');
      if (!panel) return false;
      // Panel must be visible OR we're in a passive phase
      const style = window.getComputedStyle(panel);
      return style.display !== 'none' || !!(window as any).istErzaehler;
    },
    { timeout: 10000 }
  ).catch(() => {
    console.log('[selectTargetAndConfirm] Warning: Action panel did not become visible within timeout');
  });

  // Wait for action buttons container to be populated
  const actionButtonsContainer = page.locator('#action-buttons');
  await actionButtonsContainer.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {
    console.log('[selectTargetAndConfirm] Warning: Action buttons not visible');
  });

  // First, check if target card is visible
  let targetCard = page.locator(`.spieler-card[data-name="${targetName}"]`);

  if (!(await targetCard.isVisible({ timeout: 1000 }).catch(() => false))) {
    targetCard = page
      .locator(`.spieler-card:has-text("${targetName}")`)
      .first();
  }

  if (!(await targetCard.isVisible({ timeout: 2000 }).catch(() => false))) {
    throw new Error(`Target card not found: ${targetName}`);
  }

  // Hide any existing alert before action so we can detect new ones
  await page.evaluate(() => {
    const el = document.getElementById('status-nachricht');
    if (el) {
      el.style.display = 'none';
      el.className = '';
      el.textContent = '';
    }
  });

  // Now click on the target card
  await targetCard.click();
  // Wait for buttons to appear/update after selecting a target
  await page
    .locator('#action-buttons button.btn:not([disabled]), #village3d-action-buttons button:not([disabled])')
    .first()
    .waitFor({ state: 'visible', timeout: 3000 })
    .catch(() => {
      console.log('[selectTargetAndConfirm] Warning: No enabled action button appeared');
    });

  // Find and click action button
  let buttonClicked = false;
  for (const text of buttonTexts) {
    const btn = page
      .locator(
        `#action-buttons button:has-text("${text}"), #village3d-action-buttons button:has-text("${text}")`,
      )
      .first();
    // Wait for button to be visible AND enabled (not disabled)
    if (await btn.isVisible({ timeout: 1000 }).catch(() => false)) {
      // Wait for button to be enabled
      const isEnabled = await btn.isEnabled({ timeout: 2000 }).catch(() => false);
      if (isEnabled) {
        await btn.click();
        buttonClicked = true;
        break;
      }
    }
  }

  if (!buttonClicked) {
    // Prefer buttons in the action panel/HUD, not random buttons (e.g., chat send)
    const genericBtn = page
      .locator(
        [
          '#action-buttons button.btn:not([disabled])',
          '#village3d-action-buttons button:not([disabled])',
        ].join(', '),
      )
      .filter({ hasNotText: 'Überspringen' })
      .first();

    if (await genericBtn.isVisible({ timeout: 1500 }).catch(() => false)) {
      await genericBtn.click();
      buttonClicked = true;
    } else {
      const okBtn = page
        .locator(
          '#action-buttons button:has-text("Bestätigen"), #action-buttons button:has-text("OK"), #village3d-action-buttons button:has-text("Bestätigen"), #village3d-action-buttons button:has-text("OK")',
        )
        .first();
      if (await okBtn.isVisible({ timeout: 500 }).catch(() => false)) {
        await okBtn.click();
        buttonClicked = true;
      }
    }
  }

  // If still no button found, retry once after a delay (role UI might load asynchronously)
  if (!buttonClicked) {
    await sleep(2500);
    
    // Retry with generic button
    const retryBtn = page
      .locator(
        [
          '#action-buttons button.btn:not([disabled])',
          '#village3d-action-buttons button:not([disabled])',
        ].join(', '),
      )
      .filter({ hasNotText: 'Überspringen' })
      .first();

    if (await retryBtn.isVisible({ timeout: 1500 }).catch(() => false)) {
      await retryBtn.click();
      buttonClicked = true;
    }
  }

  if (!buttonClicked) {
    throw new Error(`No action button found for "${targetName}" (checked: ${buttonTexts.join(", ")})`);
  }

  // Wait for the status alert to become visible (no timeout - wait until it happens)
  // The UI shows alerts via #status-nachricht with class alert-success or alert-error
  const alertElement = page.locator('#status-nachricht');

  // Wait for the alert to be visible and have content
  await alertElement.waitFor({ state: 'visible', timeout: 5000 });

  // Check what type of alert it is
  const alertClass = await alertElement.getAttribute('class');
  const alertText = await alertElement.textContent();

  if (alertClass?.includes('alert-error')) {
    throw new Error(`Server rejected action: ${alertText}`);
  }

  // Success (alert-success, alert-info, etc.)
  return true;
}

async function checkGameEnd(hostPage: Page): Promise<boolean> {
  try {
    // Check for game end modal or phase
    const endModal = hostPage.locator(
      '[class*="spiel-ende"], .game-over, .winner-modal',
    );
    if (await endModal.isVisible({ timeout: 500 }).catch(() => false)) {
      return true;
    }

    // Check JavaScript state
    return await hostPage.evaluate(() => {
      const phase = (window as any).aktuellePhase;
      const phaseText =
        document.querySelector(".phase-name")?.textContent?.toLowerCase() || "";
      return (
        (window as any).spielEnde === true ||
        phase === "spiel_ende" ||
        // Only match "spiel ende" or "spielende" - not "nacht_ende" or "tag_ende"
        phaseText === "spiel ende" ||
        phaseText === "spielende"
      );
    });
  } catch (e) {
    return false;
  }
}
