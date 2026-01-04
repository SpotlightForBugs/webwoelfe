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
const BASE_URL = process.env.BASE_URL || "http://localhost:5001";
const HEADLESS_OTHERS = process.env.HL === "1" || process.env.HL === "true";
// Server hat 30 Sekunden Delay für automatische Phasen (PHASE_WECHSEL_DELAY in app.py)
// Test wartet nur kurz für UI-Interaktionen
const PHASE_DELAY_MS = 2000; // 2 Sekunden für UI-Updates
const AUDIO_WAIT_MS = 5000; // 5 Sekunden extra Wartezeit nach Aktionen

// Player names
const PLAYER_NAMES = [
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

function calculateWindowLayout(index: number, total: number) {
  const screenWidth = 1920;
  const screenHeight = 1080;
  const cols = Math.ceil(Math.sqrt(total * (screenWidth / screenHeight)));
  const rows = Math.ceil(total / cols);
  const width = Math.floor(screenWidth / cols);
  const height = Math.floor(screenHeight / rows);
  const row = Math.floor(index / cols);
  const col = index % cols;

  return {
    x: col * width,
    y: row * height,
    width: Math.max(400, width - 10),
    height: Math.max(300, height - 30),
  };
}

/**
 * Positions and resizes a browser window for tiled display on Windows.
 * Uses CDP (Chrome DevTools Protocol) for reliable window management.
 */
async function tileWindow(
  page: Page,
  index: number,
  total: number,
): Promise<void> {
  const layout = calculateWindowLayout(index, total);

  try {
    // Get CDP session for direct window control
    const cdpSession = await page.context().newCDPSession(page);

    // Get the current window ID
    const { windowId } = await cdpSession.send("Browser.getWindowForTarget");

    // Set window bounds (position and size)
    await cdpSession.send("Browser.setWindowBounds", {
      windowId,
      bounds: {
        left: layout.x,
        top: layout.y,
        width: layout.width,
        height: layout.height,
        windowState: "normal",
      },
    });
  } catch (e) {
    // Fallback to JavaScript window methods if CDP fails
    await page.evaluate(
      ({ x, y, w, h }) => {
        window.moveTo(x, y);
        window.resizeTo(w, h);
      },
      { x: layout.x, y: layout.y, w: layout.width, h: layout.height },
    );
  }
}

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

    log(`🐺 Webwölfe - Full Game Simulation`);
    log(`==========================================`);
    log(`Spieleranzahl: ${PLAYER_COUNT}`);
    log(`Base URL: ${BASE_URL}`);
    log(`Headless Others: ${HEADLESS_OTHERS ? "Ja" : "Nein"}`);
    log(`==========================================\n`);

    // Launch browsers
    const browser = await chromium.launch({
      headless: false,
      args: ["--disable-web-security", "--no-sandbox"],
    });

    const headlessBrowser = HEADLESS_OTHERS
      ? await chromium.launch({
          headless: true,
          args: ["--disable-web-security", "--no-sandbox"],
        })
      : null;

    try {
      // ========================================================================
      // PHASE 1: Room Creation
      // ========================================================================
      log("📝 Erstelle Raum...");

      const hostContext = await browser.newContext({ viewport: null });
      const hostPage = await hostContext.newPage();

      // Tile the host window
      await tileWindow(hostPage, 0, PLAYER_COUNT);

      await hostPage.goto(BASE_URL);
      await hostPage.waitForLoadState("networkidle");

      // Close pre-alpha modal if present
      const closeModalBtn = hostPage.locator("[data-close-modal]").first();
      if (await closeModalBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
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

      for (let i = 1; i < PLAYER_COUNT; i++) {
        const playerName =
          PLAYER_NAMES[i % PLAYER_NAMES.length] +
          (i >= PLAYER_NAMES.length
            ? ` ${Math.floor(i / PLAYER_NAMES.length) + 1}`
            : "");
        const targetBrowser = headlessBrowser || browser;
        const context = await targetBrowser.newContext({ viewport: null });
        const page = await context.newPage();

        // Tile windows for non-headless mode
        if (!HEADLESS_OTHERS) {
          await tileWindow(page, i, PLAYER_COUNT);
        }

        await page.goto(BASE_URL);
        await page.waitForLoadState("networkidle");

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

        players.push({
          context,
          page,
          name: playerName,
          isAlive: true,
          isHost: false,
        });

        log(`  ✓ ${playerName} beigetreten (${i + 1}/${PLAYER_COUNT})`);
        await sleep(200);
      }

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
        await player.page.waitForURL(/\/spiel\//, { timeout: 10000 });
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
            .locator(".rolle-badge, [class*='rolle']")
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
      const MAX_SAME_PHASE = 10; // Max Iterationen in der gleichen Phase

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
          if (samePhaseCount > MAX_SAME_PHASE) {
            log(`  ⚠️ Phase ${currentPhase} hängt - überspringe...`);
            // Versuche manuell zur nächsten Phase zu wechseln (nur für Host)
            await hostPage.evaluate(() => {
              if ((window as any).socket) {
                (window as any).socket.emit("phase_weiter");
              }
            });
            await sleep(3000);
            samePhaseCount = 0;
            continue;
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
      await new Promise(() => {});
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
  if (
    normalizedPhase.includes("start") ||
    normalizedPhase.includes("ende") ||
    normalizedPhase.includes("ergebnis") ||
    normalizedPhase.includes("verliebteinfo") ||
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
  if (normalizedPhase.includes("armor") || normalizedPhase.includes("amor")) {
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
    await handleHurePhase(players);
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

  // ========================================================================
  // DAY PHASES
  // ========================================================================

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
  log("  🐺 Werwolf-Phase: Wähle Opfer...");

  // Find alive villager to attack
  const aliveVillagers = dorfbewohner.filter((p) => p.isAlive);
  if (aliveVillagers.length === 0) {
    log("    Keine lebenden Dorfbewohner mehr!");
    return;
  }

  const target =
    aliveVillagers[Math.floor(Math.random() * aliveVillagers.length)];
  log(`    Ziel: ${target.name}`);

  // Each werewolf votes for the target
  // Button-Text ist "Töten", Aktion ist "werwolf_wahl"
  for (const wolf of werwolfe.filter((w) => w.isAlive)) {
    const success = await selectTargetAndConfirm(wolf.page, target.name, [
      "Töten",
      "Wählen",
      "Angreifen",
    ]);
    if (success) {
      log(`    ${wolf.name} stimmt für ${target.name}`);
    } else {
      log(`    ${wolf.name} konnte nicht abstimmen`);
    }
    await sleep(500);
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

  // Dieb can choose from leftover roles or skip
  const skipBtn = dieb.page
    .locator(
      'button:has-text("Überspringen"), button:has-text("Behalten"), button:has-text("Weiter")',
    )
    .first();
  if (await skipBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
    await skipBtn.click();
    log("    Dieb behält seine Rolle");
  }
}

async function handleDoppelgaengerPhase(
  players: PlayerWindow[],
): Promise<void> {
  log("  👤 Doppelgänger-Phase: Wähle Spieler zum Kopieren...");

  const doppelgaenger = findPlayerByRole(players, ["Doppelgänger"]);
  if (!doppelgaenger) {
    log("    Kein Doppelgänger im Spiel");
    return;
  }

  const targets = players.filter((p) => p !== doppelgaenger && p.isAlive);
  if (targets.length === 0) return;

  const target = targets[Math.floor(Math.random() * targets.length)];
  await selectTargetAndConfirm(doppelgaenger.page, target.name, [
    "Kopieren",
    "Wählen",
  ]);
  log(`    Doppelgänger kopiert ${target.name}`);
}

async function handlePriesterPhase(players: PlayerWindow[]): Promise<void> {
  log("  ⛪ Dunkler Priester-Phase: Markiere einen Spieler...");

  const priester = findPlayerByRole(players, ["Dunkler Priester", "Priester"]);
  if (!priester) {
    log("    Kein Dunkler Priester im Spiel");
    return;
  }

  const targets = players.filter((p) => p !== priester && p.isAlive);
  if (targets.length === 0) return;

  const target = targets[Math.floor(Math.random() * targets.length)];
  await selectTargetAndConfirm(priester.page, target.name, [
    "Markieren",
    "Wählen",
  ]);
  log(`    Dunkler Priester markiert ${target.name}`);
}

async function handleWildesKindPhase(players: PlayerWindow[]): Promise<void> {
  log("  🐕 Wildes Kind-Phase: Wähle Vorbild...");

  const wildesKind = findPlayerByRole(players, ["Wildes Kind"]);
  if (!wildesKind) {
    log("    Kein Wildes Kind im Spiel");
    return;
  }

  const targets = players.filter((p) => p !== wildesKind && p.isAlive);
  if (targets.length === 0) return;

  const target = targets[Math.floor(Math.random() * targets.length)];
  await selectTargetAndConfirm(wildesKind.page, target.name, [
    "Wählen",
    "Vorbild",
  ]);
  log(`    Wildes Kind wählt ${target.name} als Vorbild`);
}

async function handleHundPhase(players: PlayerWindow[]): Promise<void> {
  log("  🐶 Hund-Phase: Wolf oder Dorfbewohner?...");

  const hund = findPlayerByRole(players, ["Hund"]);
  if (!hund) {
    log("    Kein Hund im Spiel");
    return;
  }

  // Randomly choose wolf or villager
  const choice = Math.random() > 0.5 ? "Werwolf" : "Dorfbewohner";
  const btn = hund.page.locator(`button:has-text("${choice}")`).first();
  if (await btn.isVisible({ timeout: 2000 }).catch(() => false)) {
    await btn.click();
    log(`    Hund wird ${choice}`);
  }
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

  log(`  👁️ ${roleNames[0]}-Phase: Wähle Spieler zum Sehen...`);

  const seher = findPlayerByRole(players, roleNames);
  if (!seher) {
    log(`    Keine ${roleNames[0]} im Spiel`);
    return;
  }

  const targets = players.filter((p) => p !== seher && p.isAlive);
  if (targets.length === 0) return;

  const target = targets[Math.floor(Math.random() * targets.length)];
  // Button-Text ist "Identität sehen", Aktion ist "seherin_sehen"
  const success = await selectTargetAndConfirm(seher.page, target.name, [
    "Identität sehen",
    "Sehen",
    "Wählen",
    "Prüfen",
  ]);
  if (success) {
    log(`    ${roleNames[0]} sieht ${target.name}`);
  } else {
    log(`    ${roleNames[0]} konnte niemanden sehen`);
  }
}

async function handleMediumPhase(players: PlayerWindow[]): Promise<void> {
  log("  👻 Medium-Phase: Kontaktiere Tote...");

  const medium = findPlayerByRole(players, ["Medium"]);
  if (!medium) {
    log("    Kein Medium im Spiel");
    return;
  }

  // Medium sees a dead player
  const deadPlayers = players.filter((p) => !p.isAlive);
  if (deadPlayers.length === 0) {
    log("    Keine Toten zum Kontaktieren");
    return;
  }

  const target = deadPlayers[Math.floor(Math.random() * deadPlayers.length)];
  await selectTargetAndConfirm(medium.page, target.name, [
    "Kontaktieren",
    "Sehen",
    "Wählen",
  ]);
  log(`    Medium kontaktiert ${target.name}`);
}

async function handleTratschweibPhase(players: PlayerWindow[]): Promise<void> {
  log("  🗣️ Tratschweib-Phase: Erfrage Information...");

  const tratschweib = findPlayerByRole(players, ["Tratschweib"]);
  if (!tratschweib) {
    log("    Kein Tratschweib im Spiel");
    return;
  }

  // Select two players to compare
  const targets = players.filter((p) => p !== tratschweib && p.isAlive);
  if (targets.length < 2) return;

  const shuffled = targets.sort(() => Math.random() - 0.5);
  await selectTargetAndConfirm(tratschweib.page, shuffled[0].name, ["Wählen"]);
  await sleep(300);
  await selectTargetAndConfirm(tratschweib.page, shuffled[1].name, [
    "Vergleichen",
    "Prüfen",
    "Wählen",
  ]);
  log(`    Tratschweib vergleicht ${shuffled[0].name} und ${shuffled[1].name}`);
}

async function handleWerwolfseherinPhase(
  players: PlayerWindow[],
  werwolfe: PlayerWindow[],
): Promise<void> {
  log("  👁️🐺 Werwolfseherin-Phase: Sieht mit den Wölfen...");

  const werwolfseherin = findPlayerByRole(players, ["Werwolfseherin"]);
  if (!werwolfseherin) {
    log("    Keine Werwolfseherin im Spiel");
    return;
  }

  // She sees another wolf
  const otherWolves = werwolfe.filter((w) => w !== werwolfseherin && w.isAlive);
  if (otherWolves.length === 0) return;

  const target = otherWolves[Math.floor(Math.random() * otherWolves.length)];
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

  log(`  💉 ${roleNames[0]}-Phase: Wähle Spieler zum Schützen...`);

  const heiler = findPlayerByRole(players, roleNames);
  if (!heiler) {
    log(`    Kein ${roleNames[0]} im Spiel`);
    return;
  }

  const targets = dorfbewohner.filter((p) => p.isAlive);
  if (targets.length === 0) return;

  const target = targets[Math.floor(Math.random() * targets.length)];
  await selectTargetAndConfirm(heiler.page, target.name, [
    "Schützen",
    "Heilen",
    "Wählen",
  ]);
  log(`    ${roleNames[0]} schützt ${target.name}`);
}

async function handleHurePhase(players: PlayerWindow[]): Promise<void> {
  log("  💋 Hure/Prostituierte-Phase: Besuche Spieler...");

  const hure = findPlayerByRole(players, ["Hure", "Prostituierte", "Nutte"]);
  if (!hure) {
    log("    Keine Hure im Spiel");
    return;
  }

  const targets = players.filter((p) => p !== hure && p.isAlive);
  if (targets.length === 0) return;

  const target = targets[Math.floor(Math.random() * targets.length)];
  await selectTargetAndConfirm(hure.page, target.name, ["Besuchen", "Wählen"]);
  log(`    Hure besucht ${target.name}`);
}

// ============================================================================
// WEREWOLF VARIANT HANDLERS
// ============================================================================

async function handleEinsamerWolfPhase(
  einsameWoelfe: PlayerWindow[],
  dorfbewohner: PlayerWindow[],
): Promise<void> {
  log(
    "  🐺💀 Einsamer Wolf-Phase: Eigene Tötung (kennt andere Wölfe NICHT!)...",
  );

  // Der Einsame Wolf jagt ALLEINE!
  const aliveEinsameWoelfe = einsameWoelfe.filter((w) => w.isAlive);
  if (aliveEinsameWoelfe.length === 0) {
    log("    Kein lebender Einsamer Wolf");
    return;
  }

  const targets = dorfbewohner.filter((p) => p.isAlive);
  if (targets.length === 0) {
    log("    Keine Ziele verfügbar");
    return;
  }

  for (const wolf of aliveEinsameWoelfe) {
    const target = targets[Math.floor(Math.random() * targets.length)];
    await selectTargetAndConfirm(wolf.page, target.name, [
      "Töten",
      "Angreifen",
      "Wählen",
    ]);
    log(`    ${wolf.name} (Einsamer Wolf) greift ${target.name} an`);
  }
}

async function handleUrwolfPhase(
  players: PlayerWindow[],
  dorfbewohner: PlayerWindow[],
): Promise<void> {
  log("  🐺⚡ Urwolf-Phase: Verwandle oder töte...");

  const urwolf = findPlayerByRole(players, ["Urwolf"]);
  if (!urwolf) {
    log("    Kein Urwolf im Spiel");
    return;
  }

  // Urwolf can convert a villager to wolf
  const targets = dorfbewohner.filter((p) => p.isAlive);
  if (targets.length === 0) return;

  const target = targets[Math.floor(Math.random() * targets.length)];
  await selectTargetAndConfirm(urwolf.page, target.name, [
    "Verwandeln",
    "Wählen",
  ]);
  log(`    Urwolf versucht ${target.name} zu verwandeln`);
}

async function handleWeisserWolfPhase(
  players: PlayerWindow[],
  werwolfe: PlayerWindow[],
): Promise<void> {
  log("  🐺⚪ Weißer Wolf-Phase: Töte Mitwolf...");

  const weisserWolf = findPlayerByRole(players, ["Weißer Wolf"]);
  if (!weisserWolf) {
    log("    Kein Weißer Wolf im Spiel");
    return;
  }

  // White wolf kills another wolf
  const otherWolves = werwolfe.filter((w) => w !== weisserWolf && w.isAlive);
  if (otherWolves.length === 0) {
    log("    Keine anderen Wölfe zum Töten");
    return;
  }

  // Only kills every other night (random for simulation)
  if (Math.random() > 0.5) {
    const target = otherWolves[Math.floor(Math.random() * otherWolves.length)];
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
  log("  🔪 Mordlustiger-Phase: Zusätzliche Tötung...");

  const mordlustiger = findPlayerByRole(players, ["Mordlustiger"]);
  if (!mordlustiger) {
    log("    Kein Mordlustiger im Spiel");
    return;
  }

  const targets = players.filter((p) => p !== mordlustiger && p.isAlive);
  if (targets.length === 0) return;

  const target = targets[Math.floor(Math.random() * targets.length)];
  await selectTargetAndConfirm(mordlustiger.page, target.name, [
    "Töten",
    "Ermorden",
    "Wählen",
  ]);
  log(`    Mordlustiger tötet ${target.name}`);
}

// ============================================================================
// HEXE VARIANT HANDLERS
// ============================================================================

async function handleHexePhase(players: PlayerWindow[]): Promise<void> {
  log("  🧙 Hexe-Phase: Entscheide über Heilen/Töten...");

  const hexe = findPlayerByRole(players, ["Hexe"]);
  if (!hexe) {
    log("    Keine Hexe im Spiel");
    return;
  }

  // Randomly decide to heal, kill, or pass
  const action = Math.random();

  try {
    if (action < 0.4) {
      const healBtn = hexe.page.locator('button:has-text("Heilen")').first();
      if (await healBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
        await healBtn.click();
        log(`    Hexe heilt das Opfer`);
        return;
      }
    } else if (action < 0.6) {
      // Try to kill someone
      const targets = players.filter((p) => p.rolle !== "Hexe" && p.isAlive);
      if (targets.length > 0) {
        const target = targets[Math.floor(Math.random() * targets.length)];
        await selectTargetAndConfirm(hexe.page, target.name, [
          "Töten",
          "Vergiften",
        ]);
        log(`    Hexe vergiftet ${target.name}`);
        return;
      }
    }

    // Pass
    const skipBtn = hexe.page
      .locator(
        'button:has-text("Nicht heilen"), button:has-text("Überspringen"), button:has-text("Weiter"), button:has-text("Nichts tun")',
      )
      .first();
    if (await skipBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
      await skipBtn.click();
      log(`    Hexe überspringt`);
    }
  } catch (e) {
    log(`    Hexe konnte nicht handeln`);
  }
}

async function handleHexenmeisterPhase(players: PlayerWindow[]): Promise<void> {
  log("  🧙‍♂️ Hexenmeister-Phase: Verzaubere...");

  const hexenmeister = findPlayerByRole(players, ["Hexenmeister"]);
  if (!hexenmeister) {
    log("    Kein Hexenmeister im Spiel");
    return;
  }

  const targets = players.filter((p) => p !== hexenmeister && p.isAlive);
  if (targets.length === 0) return;

  const target = targets[Math.floor(Math.random() * targets.length)];
  await selectTargetAndConfirm(hexenmeister.page, target.name, [
    "Verzaubern",
    "Wählen",
  ]);
  log(`    Hexenmeister verzaubert ${target.name}`);
}

async function handleGiftmischerinPhase(
  players: PlayerWindow[],
): Promise<void> {
  log("  🧪 Giftmischerin-Phase: Vergebe Gift...");

  const giftmischerin = findPlayerByRole(players, ["Giftmischerin"]);
  if (!giftmischerin) {
    log("    Keine Giftmischerin im Spiel");
    return;
  }

  const targets = players.filter((p) => p !== giftmischerin && p.isAlive);
  if (targets.length === 0) return;

  const target = targets[Math.floor(Math.random() * targets.length)];
  await selectTargetAndConfirm(giftmischerin.page, target.name, [
    "Vergiften",
    "Wählen",
  ]);
  log(`    Giftmischerin vergiftet ${target.name}`);
}

async function handleKraeuterweibPhase(players: PlayerWindow[]): Promise<void> {
  log("  🌿 Kräuterweib-Phase: Verteile Kräuter...");

  const kraeuterweib = findPlayerByRole(players, ["Kräuterweib"]);
  if (!kraeuterweib) {
    log("    Kein Kräuterweib im Spiel");
    return;
  }

  const targets = players.filter((p) => p !== kraeuterweib && p.isAlive);
  if (targets.length === 0) return;

  const target = targets[Math.floor(Math.random() * targets.length)];
  await selectTargetAndConfirm(kraeuterweib.page, target.name, [
    "Kräuter geben",
    "Wählen",
  ]);
  log(`    Kräuterweib gibt ${target.name} Kräuter`);
}

async function handleZaubererPhase(players: PlayerWindow[]): Promise<void> {
  log("  ✨ Zauberer-Phase: Wirke Zauber...");

  const zauberer = findPlayerByRole(players, ["Zauberer"]);
  if (!zauberer) {
    log("    Kein Zauberer im Spiel");
    return;
  }

  const targets = players.filter((p) => p !== zauberer && p.isAlive);
  if (targets.length === 0) return;

  const target = targets[Math.floor(Math.random() * targets.length)];
  await selectTargetAndConfirm(zauberer.page, target.name, [
    "Zaubern",
    "Wählen",
  ]);
  log(`    Zauberer zaubert auf ${target.name}`);
}

async function handleSandmannPhase(players: PlayerWindow[]): Promise<void> {
  log("  😴 Sandmann-Phase: Schläfere ein...");

  const sandmann = findPlayerByRole(players, ["Sandmann"]);
  if (!sandmann) {
    log("    Kein Sandmann im Spiel");
    return;
  }

  const targets = players.filter((p) => p !== sandmann && p.isAlive);
  if (targets.length === 0) return;

  const target = targets[Math.floor(Math.random() * targets.length)];
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
  log("  🦷 Zahnarzt-Phase: Behandle Zähne...");

  const zahnarzt = findPlayerByRole(players, ["Zahnarzt"]);
  if (!zahnarzt) {
    log("    Kein Zahnarzt im Spiel");
    return;
  }

  const targets = players.filter((p) => p !== zahnarzt && p.isAlive);
  if (targets.length === 0) return;

  const target = targets[Math.floor(Math.random() * targets.length)];
  await selectTargetAndConfirm(zahnarzt.page, target.name, [
    "Behandeln",
    "Wählen",
  ]);
  log(`    Zahnarzt behandelt ${target.name}`);
}

async function handleRabePhase(players: PlayerWindow[]): Promise<void> {
  log("  🐦 Rabe-Phase: Markiere verdächtigen...");

  const rabe = findPlayerByRole(players, ["Rabe"]);
  if (!rabe) {
    log("    Kein Rabe im Spiel");
    return;
  }

  const targets = players.filter((p) => p !== rabe && p.isAlive);
  if (targets.length === 0) return;

  const target = targets[Math.floor(Math.random() * targets.length)];
  await selectTargetAndConfirm(rabe.page, target.name, ["Markieren", "Wählen"]);
  log(`    Rabe markiert ${target.name}`);
}

async function handleFloetenspielerPhase(
  players: PlayerWindow[],
): Promise<void> {
  log("  🎵 Flötenspieler-Phase: Verzaubere...");

  const floetenspieler = findPlayerByRole(players, ["Flötenspieler"]);
  if (!floetenspieler) {
    log("    Kein Flötenspieler im Spiel");
    return;
  }

  // Enchant 1-2 players
  const targets = players.filter((p) => p !== floetenspieler && p.isAlive);
  if (targets.length === 0) return;

  const target = targets[Math.floor(Math.random() * targets.length)];
  await selectTargetAndConfirm(floetenspieler.page, target.name, [
    "Verzaubern",
    "Wählen",
  ]);
  log(`    Flötenspieler verzaubert ${target.name}`);
}

async function handleVampirPhase(players: PlayerWindow[]): Promise<void> {
  log("  🧛 Vampir-Phase: Beiße...");

  const vampir = findPlayerByRole(players, ["Vampir"]);
  if (!vampir) {
    log("    Kein Vampir im Spiel");
    return;
  }

  const targets = players.filter((p) => p !== vampir && p.isAlive);
  if (targets.length === 0) return;

  const target = targets[Math.floor(Math.random() * targets.length)];
  await selectTargetAndConfirm(vampir.page, target.name, ["Beißen", "Wählen"]);
  log(`    Vampir beißt ${target.name}`);
}

async function handleZombiePhase(players: PlayerWindow[]): Promise<void> {
  log("  🧟 Zombie-Phase: Erwecke Toten...");

  const zombie = findPlayerByRole(players, ["Zombie"]);
  if (!zombie) {
    log("    Kein Zombie im Spiel");
    return;
  }

  // Zombie can revive dead players
  const deadPlayers = players.filter((p) => !p.isAlive);
  if (deadPlayers.length === 0) {
    log("    Keine Toten zum Erwecken");
    return;
  }

  const target = deadPlayers[Math.floor(Math.random() * deadPlayers.length)];
  await selectTargetAndConfirm(zombie.page, target.name, [
    "Erwecken",
    "Wählen",
  ]);
  log(`    Zombie erweckt ${target.name}`);
}

async function handlePyromanePhase(players: PlayerWindow[]): Promise<void> {
  log("  🔥 Pyromane-Phase: Markiere oder zünde...");

  const pyromane = findPlayerByRole(players, ["Pyromane"]);
  if (!pyromane) {
    log("    Kein Pyromane im Spiel");
    return;
  }

  // Pyromane can douse or ignite
  const action = Math.random() > 0.7 ? "ignite" : "douse";

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

  const targets = players.filter((p) => p !== pyromane && p.isAlive);
  if (targets.length === 0) return;

  const target = targets[Math.floor(Math.random() * targets.length)];
  await selectTargetAndConfirm(pyromane.page, target.name, [
    "Markieren",
    "Übergießen",
    "Wählen",
  ]);
  log(`    Pyromane markiert ${target.name}`);
}

async function handleTonksPhase(players: PlayerWindow[]): Promise<void> {
  log("  🎭 Tonks-Phase: Verwandle Aussehen...");

  const tonks = findPlayerByRole(players, ["Tonks"]);
  if (!tonks) {
    log("    Kein Tonks im Spiel");
    return;
  }

  const targets = players.filter((p) => p !== tonks && p.isAlive);
  if (targets.length === 0) return;

  const target = targets[Math.floor(Math.random() * targets.length)];
  await selectTargetAndConfirm(tonks.page, target.name, [
    "Verwandeln",
    "Wählen",
  ]);
  log(`    Tonks nimmt die Gestalt von ${target.name} an`);
}

async function handleBuddlerPhase(players: PlayerWindow[]): Promise<void> {
  log("  ⛏️ Buddler-Phase: Grabe Grab aus...");

  const buddler = findPlayerByRole(players, ["Buddler"]);
  if (!buddler) {
    log("    Kein Buddler im Spiel");
    return;
  }

  // Buddler can dig up dead player's role
  const deadPlayers = players.filter((p) => !p.isAlive);
  if (deadPlayers.length === 0) {
    log("    Keine Toten zum Ausgraben");
    return;
  }

  const target = deadPlayers[Math.floor(Math.random() * deadPlayers.length)];
  await selectTargetAndConfirm(buddler.page, target.name, [
    "Ausgraben",
    "Wählen",
  ]);
  log(`    Buddler gräbt ${target.name}s Grab aus`);
}

// ============================================================================
// DAY PHASE HANDLERS
// ============================================================================

async function handleDiskussionPhase(players: PlayerWindow[]): Promise<void> {
  log("  💬 Diskussion: Spieler chatten...");

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
  ];

  const chatters = players.filter((p) => p.isAlive).slice(0, 3);

  for (const chatter of chatters) {
    const message = chatMessages[
      Math.floor(Math.random() * chatMessages.length)
    ].replace(
      "${target}",
      players[Math.floor(Math.random() * players.length)].name,
    );

    try {
      const chatInput = chatter.page.locator(
        "#chat-input, input[name='chat'], .chat-input",
      );
      if (await chatInput.isVisible({ timeout: 1000 }).catch(() => false)) {
        await chatInput.fill(message);
        await chatInput.press("Enter");
        log(`    ${chatter.name}: "${message}"`);
      }
    } catch (e) {
      // Chat failed, continue
    }
    await sleep(500);
  }

  await sleep(2000);
}

async function handleAbstimmungPhase(
  players: PlayerWindow[],
  werwolfe: PlayerWindow[],
): Promise<void> {
  log("  🗳️ Abstimmung: Spieler stimmen ab...");

  const alivePlayers = players.filter((p) => p.isAlive);
  const aliveWolves = werwolfe.filter((w) => w.isAlive);

  // WICHTIG: Einsame Wölfe sind NICHT in werwolfe enthalten!
  // Sie wissen nicht, wer die anderen Wölfe sind und stimmen daher zufällig ab.

  // Villagers vote for suspected wolf, wolves vote for villager
  const villagerTarget =
    aliveWolves.length > 0
      ? aliveWolves[Math.floor(Math.random() * aliveWolves.length)]
      : alivePlayers[Math.floor(Math.random() * alivePlayers.length)];

  log(`    Verdächtiger: ${villagerTarget?.name || "Keiner"}`);

  for (const voter of alivePlayers) {
    let voteTarget: PlayerWindow;

    if (werwolfe.includes(voter)) {
      // Rudel-Wölfe stimmen koordiniert für einen Dorfbewohner
      const villagers = alivePlayers.filter((p) => !werwolfe.includes(p));
      voteTarget =
        villagers.length > 0
          ? villagers[Math.floor(Math.random() * villagers.length)]
          : villagerTarget;
    } else {
      // Einsame Wölfe und Dorfbewohner stimmen für den Verdächtigen
      // (Einsame Wölfe wissen nicht, wer die anderen Wölfe sind!)
      voteTarget = villagerTarget;
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
      // Voting failed
    }
    await sleep(200);
  }
}

async function handleJaegerPhase(
  players: PlayerWindow[],
  werwolfe: PlayerWindow[],
): Promise<void> {
  log("  🎯 Jäger-Phase: Wähle Ziel zum Erschießen...");

  // Find dying hunter
  const jaeger = players.find(
    (p) =>
      (p.rolle?.toLowerCase().includes("jäger") ||
        p.rolle?.toLowerCase().includes("jaeger")) &&
      !p.isAlive,
  );

  if (!jaeger) {
    // Check for alive hunter in phase (shouldn't happen normally)
    const aliveJaeger = findPlayerByRole(players, ["Jäger", "Jaeger"]);
    if (!aliveJaeger || aliveJaeger.isAlive) {
      log("    Kein sterbender Jäger");
      return;
    }
  }

  const hunter = jaeger || findPlayerByRole(players, ["Jäger", "Jaeger"]);
  if (!hunter) return;

  // Shoot a werewolf if possible
  const aliveWolves = werwolfe.filter((w) => w.isAlive);
  const alivePlayers = players.filter((p) => p.isAlive);
  const target =
    aliveWolves.length > 0
      ? aliveWolves[Math.floor(Math.random() * aliveWolves.length)]
      : alivePlayers[Math.floor(Math.random() * alivePlayers.length)];

  if (!target) return;

  await selectTargetAndConfirm(hunter.page, target.name, [
    "Erschießen",
    "Wählen",
  ]);
  log(`    Jäger erschießt ${target.name}`);
  target.isAlive = false;
}

async function handleKamikazePhase(
  players: PlayerWindow[],
  werwolfe: PlayerWindow[],
): Promise<void> {
  log("  💣 Kamikaze-Phase: Selbstmordanschlag...");

  const kamikaze = findPlayerByRole(players, ["Kamikaze"]);
  if (!kamikaze) {
    log("    Kein Kamikaze im Spiel");
    return;
  }

  // Kamikaze takes someone with them
  const aliveWolves = werwolfe.filter((w) => w.isAlive);
  const target =
    aliveWolves.length > 0
      ? aliveWolves[Math.floor(Math.random() * aliveWolves.length)]
      : players.filter((p) => p.isAlive && p !== kamikaze)[0];

  if (!target) return;

  await selectTargetAndConfirm(kamikaze.page, target.name, [
    "Explodieren",
    "Mitnehmen",
    "Wählen",
  ]);
  log(`    Kamikaze reißt ${target.name} mit in den Tod!`);
  kamikaze.isAlive = false;
  target.isAlive = false;
}

// ============================================================================
// AMOR PHASE (kept separate as it's special)
// ============================================================================

async function handleAmorPhase(players: PlayerWindow[]): Promise<void> {
  log("  💕 Amor-Phase (amor_phase): Wähle Liebespaar...");

  const amor = findPlayerByRole(players, ["Amor"]);
  if (!amor) {
    log("    Kein Amor im Spiel");
    return;
  }

  const targets = players.filter((p) => p !== amor && p.isAlive);
  if (targets.length < 2) {
    log("    Nicht genug Spieler für Liebespaar");
    return;
  }

  const shuffled = targets.sort(() => Math.random() - 0.5);
  const lover1 = shuffled[0];
  const lover2 = shuffled[1];

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
    // Die Aktion heißt 'armor_verlieben' (nicht 'amor_verlieben'!)
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
                aktion: "armor_verlieben",
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
  try {
    // Versuche zuerst mit data-name Attribut (genauer)
    let targetCard = page.locator(`.spieler-card[data-name="${targetName}"]`);

    if (!(await targetCard.isVisible({ timeout: 1000 }).catch(() => false))) {
      // Fallback: Suche nach Text (weniger genau)
      targetCard = page
        .locator(`.spieler-card:has-text("${targetName}")`)
        .first();
    }

    if (await targetCard.isVisible({ timeout: 2000 }).catch(() => false)) {
      await targetCard.click();
      await sleep(500);

      // Finde und klicke Aktions-Button
      for (const text of buttonTexts) {
        const btn = page.locator(`button:has-text("${text}")`).first();
        if (await btn.isVisible({ timeout: 1000 }).catch(() => false)) {
          await btn.click();
          return true;
        }
      }

      // Kein Button gefunden - versuche generischen "Bestätigen" oder "OK" Button
      const genericBtn = page
        .locator(
          'button:has-text("Bestätigen"), button:has-text("OK"), button.btn-primary',
        )
        .first();
      if (await genericBtn.isVisible({ timeout: 500 }).catch(() => false)) {
        await genericBtn.click();
        return true;
      }
    }
    return false;
  } catch (e) {
    return false;
  }
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
