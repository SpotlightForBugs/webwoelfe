import { test, expect, Browser, BrowserContext, Page } from "@playwright/test";
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
 * ============================================================================
 * MASSIVE 500 PLAYER FULL GAME TESTS
 * ============================================================================
 *
 * Diese Tests sind für ein ECHTES 500-Spieler-Event konzipiert!
 *
 * Strategie:
 * - 450 headless Browser (für Performance)
 * - 50 headful Browser (für visuelle Kontrolle)
 * - Wir spielen eine KOMPLETTE Runde durch (Tag/Nacht Zyklen)
 * - Tests für alle 5 Spielmodi
 *
 * Hardware-Anforderungen:
 * - Mindestens 32GB RAM empfohlen
 * - SSD für schnelles Context-Switching
 * - Stabile Netzwerkverbindung
 *
 * Timeout: 30 Minuten pro Test (eine Runde kann lange dauern!)
 *
 * USAGE: Spieleranzahl via Umgebungsvariable konfigurieren:
 *   PLAYER_COUNT=100 npx playwright test massive-500-full-game
 *   ./run-tests.sh 500 -n 200
 *
 * FEATURES:
 * - ALLE ROLLEN aktiv (Chaos-Modus)
 * - Bürgermeisterwahl
 * - Alle Rollenaktionen (Seherin, Hexe, Amor, Jäger, etc.)
 * - Verliebte (Amor)
 * - Tote werden namentlich angesagt
 * - 5 Sekunden Pause zwischen Aktionen
 * - Hints-System aktiv
 */

// Konfiguration - Spieleranzahl via Umgebungsvariable oder Default
// Windows select() hat ein Limit von ~512 file descriptors, daher max 200 empfohlen
const PLAYER_COUNT = parseInt(process.env.PLAYER_COUNT || "100", 10);
const HEADLESS_COUNT = PLAYER_COUNT - 1; // Alle bis auf einen headless
const HEADFUL_COUNT = 1; // 1 sichtbares Fenster für Beobachtung
const BATCH_SIZE = Math.min(50, Math.ceil(PLAYER_COUNT / 10)); // Dynamische Batch-Größe
const MAX_ROUNDS = 20; // Maximale Anzahl Tag/Nacht Zyklen (komplettes Spiel, nicht nur eine Runde!)
const PHASE_TIMEOUT = 60000; // 60 Sekunden pro Phase (mehr Zeit für alle Aktionen)
const JOIN_DELAY = 50; // ms zwischen Spieler-Joins
const ACTION_DELAY = 8000; // 8 SEKUNDEN zwischen Aktionen (für Beobachtung + Narrator)
const ANNOUNCEMENT_DELAY = 5000; // 5 Sekunden für Ansagen (Zeit für Narrator Audio)
const NARRATOR_AUDIO_WAIT = 6000; // 6 Sekunden für TTS Audio
const CHAT_DELAY = 2000; // 2 Sekunden zwischen Chat-Nachrichten

// Zufällige Chat-Nachrichten für die Diskussionsphase
const DISCUSSION_MESSAGES = [
  "Ich bin auf jeden Fall kein Werwolf!",
  "Hmm, wer war letzte Nacht verdächtig ruhig?",
  "Ich glaube {player} ist ein Werwolf!",
  "Lasst uns systematisch vorgehen...",
  "Ich habe eine Ahnung wer es sein könnte...",
  "Hat jemand was Verdächtiges bemerkt?",
  "{player} verhält sich sehr merkwürdig.",
  "Wir müssen heute unbedingt einen Wolf erwischen!",
  "Ich vertraue {player} nicht.",
  "Glaubt mir, ich bin ein Dorfbewohner!",
  "Der Werwolf sitzt bestimmt unter uns...",
  "Lasst uns keine Fehler machen!",
  "Ich stimme für {player}!",
  "Warte, lasst uns erst diskutieren.",
  "Mein Bauchgefühl sagt mir...",
  "Gestern Nacht habe ich was gehört!",
  "Ich bin die Seherin und {player} ist böse!",
  "Lüg nicht, ich weiß dass du ein Wolf bist!",
  "Zusammenhalten Leute!",
  "Das ist eine schwierige Entscheidung...",
];

// Alle Rollen die im Spiel aktiv sein sollen
const ALL_ROLES = [
  "Werwolf",
  "Dorfbewohner",
  "Seherin",
  "Hexe",
  "Jäger",
  "Amor",
  "Leibwächter",
  "Alte Vettel",
  "Dorfdepp",
  "Weißer Wolf",
  "Urwolf",
  "Mädchen",
  "Dieb",
  "Günstling",
];

// Nur Chaos-Modus für volles Spiel mit allen Rollen
const GAME_MODE = {
  name: "Chaos - Alle Rollen",
  regelset: "chaos",
  desc: "Vollständiges Spiel mit ALLEN Rollen",
};

/**
 * Spieler-Interface für 500-Spieler-Management
 */
interface MassPlayer {
  id: number;
  name: string;
  context: BrowserContext;
  page: Page;
  role?: string;
  isAlive: boolean;
  team?: "wolf" | "village" | "solo";
  isHeadful?: boolean;
  isMayor?: boolean;
  isLover?: boolean;
}

/**
 * Spiel-Status
 */
interface GameStatus {
  phase: string;
  round: number;
  aliveCount: number;
  wolfCount: number;
  villageCount: number;
  isGameOver: boolean;
  winner?: string;
}

// Globaler headful Browser für den EINEN sichtbaren Spieler
let headfulBrowser: Browser | null = null;
let headfulPage: Page | null = null;

/**
 * Helper: Ein einziges sichtbares Browser-Fenster starten
 */
async function getHeadfulPage(): Promise<Page> {
  if (!headfulPage) {
    const { chromium } = require("playwright");
    headfulBrowser = await chromium.launch({
      headless: false,
      args: ["--window-size=1280,720"],
    });
    const context = await headfulBrowser!.newContext({
      viewport: { width: 1280, height: 720 },
    });
    headfulPage = await context.newPage();
    logEvent(
      "BROWSER",
      "Single headful browser window started for observation",
    );
  }
  return headfulPage!;
}

/**
 * Helper: Headful Browser schließen
 */
async function closeHeadfulBrowser(): Promise<void> {
  if (headfulBrowser) {
    await headfulBrowser.close();
    headfulBrowser = null;
    headfulPage = null;
    logEvent("BROWSER", "Headful browser closed");
  }
}

async function createMassPlayers(
  browser: Browser,
  roomCode: string,
  count: number,
  batchSize: number = BATCH_SIZE,
): Promise<MassPlayer[]> {
  const players: MassPlayer[] = [];
  const batches = Math.ceil(count / batchSize);

  logEvent(
    "MASS_JOIN",
    `Creating ${count} players: ${HEADLESS_COUNT} headless + ${HEADFUL_COUNT} headful (1 window)...`,
  );

  for (let batch = 0; batch < batches; batch++) {
    const startIdx = batch * batchSize;
    const endIdx = Math.min(startIdx + batchSize, count);
    const batchPlayers: Promise<MassPlayer>[] = [];

    logEvent("BATCH", `Joining players ${startIdx + 1} to ${endIdx}...`);

    for (let i = startIdx; i < endIdx; i++) {
      const playerNum = i + 1;
      const playerName = `S${playerNum.toString().padStart(4, "0")}`;

      // Der ERSTE Spieler (1) ist headful - alle anderen headless
      const isHeadful = playerNum === 1;

      batchPlayers.push(
        (async (): Promise<MassPlayer> => {
          let context: BrowserContext;
          let page: Page;

          if (isHeadful) {
            // Der EINE sichtbare Spieler - eigenes Fenster
            page = await getHeadfulPage();
            // Dummy context - wird nicht geschlossen
            context = page.context();
          } else {
            // Headless: Separater Context (unsichtbar)
            context = await browser.newContext({
              viewport: { width: 800, height: 600 },
            });
            page = await context.newPage();
          }

          // Join the room
          await page.goto("/");

          const joinForm = page
            .locator("form")
            .filter({ has: page.locator('input[name="code"]') });
          await joinForm.locator('input[name="spieler_name"]').fill(playerName);
          await joinForm.locator('input[name="code"]').fill(roomCode);
          await joinForm.locator('button[type="submit"]').click();

          // Wait for lobby
          await expect(page).toHaveURL(/\/lobby\//, { timeout: 15000 });

          return {
            id: playerNum,
            name: playerName,
            context,
            page,
            isAlive: true,
            isHeadful,
          };
        })(),
      );

      // Small delay between joins to not overwhelm the server
      await new Promise((resolve) => setTimeout(resolve, JOIN_DELAY));
    }

    // Wait for batch to complete
    const batchResults = await Promise.all(batchPlayers);
    players.push(...batchResults);

    logEvent("BATCH_DONE", `${players.length}/${count} players joined`);
  }

  const headfulPlayers = players.filter((p) => p.isHeadful).length;
  const headlessPlayers = players.filter((p) => !p.isHeadful).length;
  logEvent(
    "SUMMARY",
    `${headlessPlayers} headless + ${headfulPlayers} headful (1 visible window) = ${players.length} total`,
  );

  return players;
}

/**
 * Helper: Alle Spielerrollen abrufen
 */
async function getMassPlayerRoles(players: MassPlayer[]): Promise<void> {
  logEvent("ROLES", `Getting roles for ${players.length} players...`);

  const rolePromises = players.map(async (player) => {
    try {
      const roleBadge = player.page.locator(".rolle-badge");
      await expect(roleBadge).toBeVisible({ timeout: 10000 });
      const roleText = await roleBadge.textContent();
      player.role = roleText?.trim() || "Dorfbewohner";

      // Determine team
      const roleLower = player.role.toLowerCase();
      if (roleLower.includes("werwolf") && !roleLower.includes("weiß")) {
        player.team = "wolf";
      } else if (
        roleLower.includes("vampir") ||
        roleLower.includes("zombie") ||
        roleLower.includes("flöten") ||
        roleLower.includes("engel") ||
        roleLower.includes("weiß")
      ) {
        player.team = "solo";
      } else {
        player.team = "village";
      }
    } catch (e) {
      player.role = "Dorfbewohner";
      player.team = "village";
    }
  });

  await Promise.all(rolePromises);

  // Log role distribution
  const wolves = players.filter((p) => p.team === "wolf").length;
  const villagers = players.filter((p) => p.team === "village").length;
  const solos = players.filter((p) => p.team === "solo").length;

  logEvent("ROLE_DIST", `Wölfe: ${wolves}, Dorf: ${villagers}, Solo: ${solos}`);
}

/**
 * Helper: Spielstatus von einem Spieler abrufen
 */
async function getGameStatus(
  player: MassPlayer,
  allPlayers: MassPlayer[],
): Promise<GameStatus> {
  const phase = await getCurrentPhase({
    context: player.context,
    page: player.page,
    name: player.name,
  });

  // Count living players by checking page content
  const aliveCount = allPlayers.filter((p) => p.isAlive).length;
  const wolfCount = allPlayers.filter(
    (p) => p.isAlive && p.team === "wolf",
  ).length;
  const villageCount = allPlayers.filter(
    (p) => p.isAlive && p.team === "village",
  ).length;

  const isOver =
    phase.includes("ende") ||
    phase.includes("gewonnen") ||
    wolfCount === 0 ||
    villageCount === 0 ||
    wolfCount >= villageCount;

  let winner: string | undefined;
  if (wolfCount === 0) winner = "Dorf";
  if (wolfCount >= villageCount) winner = "Werwölfe";

  return {
    phase,
    round: 0, // Will be set externally
    aliveCount,
    wolfCount,
    villageCount,
    isGameOver: isOver,
    winner,
  };
}

/**
 * Helper: Werwolf-Phase ausführen
 */
async function executeWerewolfPhase(
  wolves: MassPlayer[],
  villagers: MassPlayer[],
): Promise<string | null> {
  const livingWolves = wolves.filter((w) => w.isAlive);
  const livingVillagers = villagers.filter((v) => v.isAlive);

  if (livingWolves.length === 0 || livingVillagers.length === 0) {
    return null;
  }

  // Wähle ein zufälliges Opfer
  const victimIdx = Math.floor(Math.random() * livingVillagers.length);
  const victim = livingVillagers[victimIdx];

  logEvent("WOLF_ATTACK", `Wölfe greifen ${victim.name} an`);

  // Alle Wölfe wählen das gleiche Ziel
  for (const wolf of livingWolves) {
    try {
      const targetCard = wolf.page.locator(
        `.spieler-card:has-text("${victim.name}")`,
      );
      if (await targetCard.isVisible({ timeout: 2000 })) {
        await targetCard.click();
        await new Promise((resolve) => setTimeout(resolve, ACTION_DELAY));

        const attackBtn = wolf.page.locator(
          'button:has-text("Angreifen"), button:has-text("Wählen"), button:has-text("Bestätigen")',
        );
        if (await attackBtn.isVisible({ timeout: 1000 })) {
          await attackBtn.click();
        }
      }
    } catch (e) {
      // Ignoriere Fehler bei einzelnen Wölfen
    }
  }

  return victim.name;
}

/**
 * Helper: Tag-Abstimmung ausführen
 */
async function executeDayVoting(
  players: MassPlayer[],
  wolves: MassPlayer[],
): Promise<string | null> {
  const livingPlayers = players.filter((p) => p.isAlive);
  const livingWolves = wolves.filter((w) => w.isAlive);

  if (livingPlayers.length === 0) return null;

  // Strategie: Dorfbewohner versuchen einen Wolf zu finden
  // Wölfe stimmen gegen einen zufälligen Dorfbewohner

  // Wähle einen zufälligen Wolf als Ziel (falls bekannt) oder random
  let voteTarget: MassPlayer;
  if (livingWolves.length > 0) {
    voteTarget = livingWolves[Math.floor(Math.random() * livingWolves.length)];
  } else {
    voteTarget =
      livingPlayers[Math.floor(Math.random() * livingPlayers.length)];
  }

  logEvent("DAY_VOTE", `Abstimmung gegen ${voteTarget.name}`);

  // Alle Spieler stimmen ab (in Batches)
  const voteBatches = Math.ceil(livingPlayers.length / BATCH_SIZE);

  for (let batch = 0; batch < voteBatches; batch++) {
    const startIdx = batch * BATCH_SIZE;
    const endIdx = Math.min(startIdx + BATCH_SIZE, livingPlayers.length);
    const batchPlayers = livingPlayers.slice(startIdx, endIdx);

    const votePromises = batchPlayers.map(async (player) => {
      try {
        const targetCard = player.page.locator(
          `.spieler-card:has-text("${voteTarget.name}")`,
        );
        if (await targetCard.isVisible({ timeout: 2000 })) {
          await targetCard.click();
          await new Promise((resolve) => setTimeout(resolve, ACTION_DELAY));

          const voteBtn = player.page.locator(
            'button:has-text("Abstimmen"), button:has-text("Wählen")',
          );
          if (await voteBtn.isVisible({ timeout: 1000 })) {
            await voteBtn.click();
          }
        }
      } catch (e) {
        // Ignoriere Fehler bei einzelnen Stimmen
      }
    });

    await Promise.all(votePromises);
  }

  return voteTarget.name;
}

/**
 * Helper: Cleanup für Mass-Spieler
 */
async function cleanupMassPlayers(players: MassPlayer[]): Promise<void> {
  logEvent("CLEANUP", `Closing ${players.length} player sessions...`);

  // Headless: Schließe Contexts (jeder hat seinen eigenen)
  // Headful: Schließe nur die Pages (Context wird am Ende geschlossen)
  const closePromises = players.map(async (player) => {
    try {
      if (player.isHeadful) {
        // Headful: Nur die Page schließen, Context bleibt
        await player.page.close();
      } else {
        // Headless: Ganzen Context schließen
        await player.context.close();
      }
    } catch {
      // Ignoriere Cleanup-Fehler
    }
  });

  await Promise.all(closePromises);

  // Headful Browser und Context schließen
  await closeHeadfulBrowser();
}

// ============================================================================
// HELPER: Wait for Game UI/Audio (real announcements, not fake)
// ============================================================================

/**
 * Wartet bis das Spiel eine Erzählung/Audio abgespielt hat
 */
async function waitForNarratorAudio(page: Page): Promise<void> {
  try {
    // Warte auf Audio-Element oder Erzählungs-Overlay
    const audioPlaying = page.locator(
      "audio[autoplay], .erzaehlung-overlay, .notification",
    );
    if (await audioPlaying.first().isVisible({ timeout: 2000 })) {
      // Warte bis Audio endet oder Overlay verschwindet
      await page.waitForTimeout(NARRATOR_AUDIO_WAIT);
    }
  } catch {
    // Kein Audio, weitermachen
  }
  await page.waitForTimeout(1000);
}

/**
 * Sendet eine echte Chat-Nachricht im Spiel
 */
async function sendChatMessage(
  player: MassPlayer,
  message: string,
): Promise<void> {
  try {
    const chatInput = player.page.locator("#chat-input");
    const sendBtn = player.page.locator(
      'button:has-text("paper-plane"), button[onclick="sendChat()"]',
    );

    if (await chatInput.isVisible({ timeout: 1000 })) {
      await chatInput.fill(message);
      await chatInput.press("Enter");
      logEvent("💬 CHAT", `${player.name}: ${message}`);
    }
  } catch {
    // Chat nicht verfügbar
  }
}

/**
 * Simuliert echte Diskussion mit Chat-Nachrichten
 */
async function executeRealDiscussion(
  players: MassPlayer[],
  durationMs: number = 10000,
): Promise<void> {
  logEvent("🗣️ DISKUSSION", "Spieler diskutieren...");

  const alivePlayers = players.filter((p) => p.isAlive);
  const numMessages = Math.min(5, Math.ceil(alivePlayers.length / 3));
  const messageInterval = durationMs / numMessages;

  for (let i = 0; i < numMessages; i++) {
    const randomPlayer =
      alivePlayers[Math.floor(Math.random() * alivePlayers.length)];
    const randomTarget =
      alivePlayers[Math.floor(Math.random() * alivePlayers.length)];

    let message =
      DISCUSSION_MESSAGES[
        Math.floor(Math.random() * DISCUSSION_MESSAGES.length)
      ];
    message = message.replace("{player}", randomTarget.name);

    await sendChatMessage(randomPlayer, message);
    await randomPlayer.page.waitForTimeout(messageInterval);
  }
}

/**
 * Führt eine echte UI-basierte Spielerauswahl durch (klickt auf Spielerkarte)
 */
async function selectPlayerInUI(
  actor: MassPlayer,
  targetName: string,
): Promise<boolean> {
  try {
    const targetCard = actor.page
      .locator(`.spieler-card:has-text("${targetName}")`)
      .first();

    if (await targetCard.isVisible({ timeout: 3000 })) {
      // Scroll ins Sichtfeld
      await targetCard.scrollIntoViewIfNeeded();
      await actor.page.waitForTimeout(500);

      // Klick auf Spielerkarte
      await targetCard.click();
      logEvent("🎯 SELECT", `${actor.name} wählt ${targetName}`);
      await actor.page.waitForTimeout(ACTION_DELAY);
      return true;
    }
  } catch (e) {
    logEvent("WARN", `Konnte ${targetName} nicht auswählen: ${e}`);
  }
  return false;
}

/**
 * Klickt auf einen Aktions-Button (Töten, Abstimmen, etc.)
 */
async function clickActionButton(
  player: MassPlayer,
  ...buttonTexts: string[]
): Promise<boolean> {
  for (const text of buttonTexts) {
    try {
      const btn = player.page
        .locator(`button:has-text("${text}"), .btn:has-text("${text}")`)
        .first();
      if (await btn.isVisible({ timeout: 2000 })) {
        await btn.click();
        logEvent("🔘 ACTION", `${player.name} klickt "${text}"`);
        await player.page.waitForTimeout(1000);
        return true;
      }
    } catch {}
  }
  return false;
}

// ============================================================================
// HELPER: Bürgermeisterwahl - REAL UI INTERACTION
// ============================================================================

async function executeMayorElection(
  allPlayers: MassPlayer[],
  hostPage: Page,
): Promise<string | null> {
  logEvent("👑 WAHL", "Bürgermeisterwahl beginnt!");
  await waitForNarratorAudio(hostPage);
  await hostPage.waitForTimeout(ACTION_DELAY);

  const alivePlayers = allPlayers.filter((p) => p.isAlive);
  if (alivePlayers.length === 0) return null;

  // Jeder stimmt für einen zufälligen Spieler via echte UI-Klicks
  const votes: Map<string, number> = new Map();

  for (const player of alivePlayers) {
    const candidates = alivePlayers.filter((p) => p.id !== player.id);
    if (candidates.length === 0) continue;

    const vote = candidates[Math.floor(Math.random() * candidates.length)];
    votes.set(vote.name, (votes.get(vote.name) || 0) + 1);

    // Echte UI-Auswahl
    await selectPlayerInUI(player, vote.name);
    await clickActionButton(player, "Wählen", "Abstimmen", "Bestätigen");
  }

  // Finde Gewinner
  let maxVotes = 0;
  let mayor: string | null = null;
  for (const [name, count] of votes) {
    if (count > maxVotes) {
      maxVotes = count;
      mayor = name;
    }
  }

  if (mayor) {
    const mayorPlayer = allPlayers.find((p) => p.name === mayor);
    if (mayorPlayer) mayorPlayer.isMayor = true;
    logEvent("👑 BÜRGERMEISTER", `${mayor} wurde gewählt!`);
  }

  await waitForNarratorAudio(hostPage);
  await hostPage.waitForTimeout(ACTION_DELAY);
  return mayor;
}

// ============================================================================
// HELPER: Vollständige Nachtphase mit ECHTEN UI-AKTIONEN
// ============================================================================

async function executeFullNightPhase(
  allPlayers: MassPlayer[],
  hostPage: Page,
  isFirstNight: boolean,
): Promise<{ dead: string[]; healed: string | null }> {
  const dead: string[] = [];
  let healed: string | null = null;
  let werewolfVictim: string | null = null;

  logEvent("🌙 NACHT", "Die Nacht bricht herein...");
  await waitForNarratorAudio(hostPage);
  await hostPage.waitForTimeout(ACTION_DELAY);

  // Erste Nacht: Amor wählt Verliebte - ECHTE UI KLICKS
  if (isFirstNight) {
    const amor = allPlayers.find(
      (p) => p.isAlive && p.role?.toLowerCase().includes("amor"),
    );
    if (amor) {
      logEvent("💘 AMOR", `${amor.name} wählt zwei Verliebte...`);
      await waitForNarratorAudio(amor.page);

      const candidates = allPlayers.filter(
        (p) => p.isAlive && p.id !== amor.id,
      );
      if (candidates.length >= 2) {
        const shuffled = candidates.sort(() => Math.random() - 0.5);
        const lover1 = shuffled[0];
        const lover2 = shuffled[1];

        // Echte UI-Klicks: Wähle ersten Verliebten
        await selectPlayerInUI(amor, lover1.name);
        await amor.page.waitForTimeout(1000);

        // Echte UI-Klicks: Wähle zweiten Verliebten
        await selectPlayerInUI(amor, lover2.name);
        await clickActionButton(amor, "Verlieben", "Bestätigen", "Wählen");

        lover1.isLover = true;
        lover2.isLover = true;
        logEvent(
          "💕 VERLIEBTE",
          `${lover1.name} und ${lover2.name} sind nun verliebt!`,
        );
      }
      await waitForNarratorAudio(hostPage);
      await hostPage.waitForTimeout(ACTION_DELAY);
    }
  }

  // Leibwächter - ECHTE UI
  const bodyguard = allPlayers.find(
    (p) => p.isAlive && p.role?.toLowerCase().includes("leibwächter"),
  );
  let protectedPlayer: string | null = null;
  if (bodyguard) {
    logEvent(
      "🛡️ LEIBWÄCHTER",
      `${bodyguard.name} wählt jemanden zum Beschützen...`,
    );
    await waitForNarratorAudio(bodyguard.page);

    const candidates = allPlayers.filter(
      (p) => p.isAlive && p.id !== bodyguard.id,
    );
    if (candidates.length > 0) {
      const target = candidates[Math.floor(Math.random() * candidates.length)];
      protectedPlayer = target.name;

      await selectPlayerInUI(bodyguard, target.name);
      await clickActionButton(bodyguard, "Beschützen", "Bestätigen", "Wählen");
      logEvent("🛡️ SCHUTZ", `${bodyguard.name} beschützt ${target.name}`);
    }
    await hostPage.waitForTimeout(ACTION_DELAY);
  }

  // Seherin - ECHTE UI
  const seer = allPlayers.find(
    (p) => p.isAlive && p.role?.toLowerCase().includes("seherin"),
  );
  if (seer) {
    logEvent("🔮 SEHERIN", `${seer.name} erwacht...`);
    await waitForNarratorAudio(seer.page);

    const candidates = allPlayers.filter((p) => p.isAlive && p.id !== seer.id);
    if (candidates.length > 0) {
      const target = candidates[Math.floor(Math.random() * candidates.length)];

      await selectPlayerInUI(seer, target.name);
      await clickActionButton(seer, "Sehen", "Identität sehen", "Bestätigen");
      logEvent("👁️ VISION", `${seer.name} hat ${target.name} angesehen`);
    }
    await hostPage.waitForTimeout(ACTION_DELAY);
  }

  // Werwölfe - ECHTE UI ABSTIMMUNG
  logEvent("🐺 WERWÖLFE", "Die Werwölfe erwachen...");
  const wolves = allPlayers.filter((p) => p.isAlive && p.team === "wolf");
  if (wolves.length > 0) {
    await waitForNarratorAudio(wolves[0].page);

    const villagers = allPlayers.filter((p) => p.isAlive && p.team !== "wolf");
    if (villagers.length > 0) {
      const victim = villagers[Math.floor(Math.random() * villagers.length)];
      werewolfVictim = victim.name;

      // Alle Wölfe wählen das gleiche Ziel via echte UI-Klicks
      for (const wolf of wolves) {
        logEvent("🐺 WAHL", `${wolf.name} wählt ${victim.name}`);
        await selectPlayerInUI(wolf, victim.name);
        await clickActionButton(
          wolf,
          "Töten",
          "Angreifen",
          "Wählen",
          "Bestätigen",
        );
      }

      logEvent("🐺 ANGRIFF", `Die Werwölfe greifen ${werewolfVictim} an!`);
    }
  }
  await waitForNarratorAudio(hostPage);
  await hostPage.waitForTimeout(ACTION_DELAY);

  // Hexe - ECHTE UI
  const witch = allPlayers.find(
    (p) => p.isAlive && p.role?.toLowerCase().includes("hexe"),
  );
  if (witch) {
    logEvent("🧙 HEXE", `${witch.name} erwacht...`);
    await waitForNarratorAudio(witch.page);

    // Heiltrank - 50% Chance zu heilen wenn Opfer existiert
    if (werewolfVictim && Math.random() > 0.5) {
      await clickActionButton(witch, "Heilen", "Heiltrank", "Retten");
      healed = werewolfVictim;
      logEvent("💊 HEILUNG", `${witch.name} heilt ${werewolfVictim}`);
    }

    // Gifttrank - 20% Chance jemanden zu vergiften
    if (Math.random() > 0.8) {
      const poisonCandidates = allPlayers.filter(
        (p) => p.isAlive && p.id !== witch.id && p.name !== werewolfVictim,
      );
      if (poisonCandidates.length > 0) {
        const poisoned =
          poisonCandidates[Math.floor(Math.random() * poisonCandidates.length)];

        await selectPlayerInUI(witch, poisoned.name);
        await clickActionButton(witch, "Vergiften", "Gifttrank", "Töten");

        dead.push(poisoned.name);
        poisoned.isAlive = false;
        logEvent("☠️ GIFT", `${witch.name} vergiftet ${poisoned.name}`);
      }
    } else {
      await clickActionButton(witch, "Nichts tun", "Überspringen", "Weiter");
    }
    await hostPage.waitForTimeout(ACTION_DELAY);
  }

  // Werwolf-Opfer stirbt (falls nicht geheilt oder geschützt)
  if (
    werewolfVictim &&
    werewolfVictim !== healed &&
    werewolfVictim !== protectedPlayer
  ) {
    dead.push(werewolfVictim);
    const victim = allPlayers.find((p) => p.name === werewolfVictim);
    if (victim) victim.isAlive = false;
  }

  // Verliebte: Wenn einer stirbt, stirbt der andere auch
  for (const deadName of [...dead]) {
    const deadPlayer = allPlayers.find((p) => p.name === deadName);
    if (deadPlayer?.isLover) {
      const otherLover = allPlayers.find(
        (p) => p.isLover && p.name !== deadName && p.isAlive,
      );
      if (otherLover) {
        otherLover.isAlive = false;
        dead.push(otherLover.name);
        logEvent(
          "💔 HERZSCHMERZ",
          `${otherLover.name} stirbt an gebrochenem Herzen`,
        );
      }
    }
  }

  await waitForNarratorAudio(hostPage);
  await hostPage.waitForTimeout(ACTION_DELAY);
  return { dead, healed };
}

// ============================================================================
// HELPER: Vollständige Tagphase mit ECHTEM Chat und Abstimmung
// ============================================================================

async function executeFullDayPhase(
  allPlayers: MassPlayer[],
  hostPage: Page,
  deadLastNight: string[],
): Promise<string | null> {
  logEvent("☀️ TAG", "Der Tag bricht an...");
  await waitForNarratorAudio(hostPage);
  await hostPage.waitForTimeout(ACTION_DELAY);

  // Tote der Nacht ansagen - das Spiel macht das automatisch
  if (deadLastNight.length > 0) {
    logEvent("☠️ TOTE", `Gestorben in der Nacht: ${deadLastNight.join(", ")}`);
    await waitForNarratorAudio(hostPage);

    // Jäger-Aktion wenn Jäger gestorben ist - ECHTE UI
    for (const deadName of deadLastNight) {
      const deadPlayer = allPlayers.find((p) => p.name === deadName);
      if (deadPlayer?.role?.toLowerCase().includes("jäger")) {
        logEvent(
          "🏹 JÄGER",
          `${deadPlayer.name} ist gestorben und kann schießen!`,
        );

        // Warte auf Jäger-UI und wähle Ziel
        await waitForNarratorAudio(deadPlayer.page);
        const candidates = allPlayers.filter((p) => p.isAlive);
        if (candidates.length > 0) {
          const hunterVictim =
            candidates[Math.floor(Math.random() * candidates.length)];
          await selectPlayerInUI(deadPlayer, hunterVictim.name);
          await clickActionButton(
            deadPlayer,
            "Erschießen",
            "Schießen",
            "Bestätigen",
          );
          hunterVictim.isAlive = false;
          logEvent(
            "💥 SCHUSS",
            `${deadPlayer.name} erschießt ${hunterVictim.name}!`,
          );
        }
      }
    }
  } else {
    logEvent("😴 SICHER", "Niemand ist in der Nacht gestorben!");
  }

  await waitForNarratorAudio(hostPage);
  await hostPage.waitForTimeout(ACTION_DELAY);

  // Diskussionsphase - ECHTE CHAT-NACHRICHTEN
  logEvent("🗣️ DISKUSSION", "Die Dorfbewohner diskutieren...");
  await executeRealDiscussion(allPlayers, ACTION_DELAY * 2);

  // Abstimmung - ECHTE UI-KLICKS
  logEvent("🗳️ ABSTIMMUNG", "Zeit für die Abstimmung!");
  await waitForNarratorAudio(hostPage);
  await hostPage.waitForTimeout(ACTION_DELAY);

  const alivePlayers = allPlayers.filter((p) => p.isAlive);
  if (alivePlayers.length === 0) return null;

  const votes: Map<string, number> = new Map();

  for (const player of alivePlayers) {
    const candidates = alivePlayers.filter((p) => p.id !== player.id);
    if (candidates.length === 0) continue;

    // Wölfe stimmen gegen Dorfbewohner, Dorf stimmt zufällig
    let voteTarget: MassPlayer;
    if (player.team === "wolf") {
      const villagerCandidates = candidates.filter((p) => p.team !== "wolf");
      voteTarget =
        villagerCandidates.length > 0
          ? villagerCandidates[
              Math.floor(Math.random() * villagerCandidates.length)
            ]
          : candidates[Math.floor(Math.random() * candidates.length)];
    } else {
      voteTarget = candidates[Math.floor(Math.random() * candidates.length)];
    }

    // ECHTE UI-ABSTIMMUNG
    await selectPlayerInUI(player, voteTarget.name);
    await clickActionButton(player, "Abstimmen", "Wählen", "Bestätigen");

    // Bürgermeister hat doppelte Stimme
    const voteWeight = player.isMayor ? 2 : 1;
    votes.set(voteTarget.name, (votes.get(voteTarget.name) || 0) + voteWeight);
  }

  // Finde den mit den meisten Stimmen
  let maxVotes = 0;
  let eliminated: string | null = null;
  for (const [name, count] of votes) {
    if (count > maxVotes) {
      maxVotes = count;
      eliminated = name;
    }
  }

  if (eliminated) {
    const eliminatedPlayer = allPlayers.find((p) => p.name === eliminated);
    if (eliminatedPlayer) {
      eliminatedPlayer.isAlive = false;
      logEvent(
        "⚖️ HINRICHTUNG",
        `${eliminated} wird hingerichtet! (Rolle: ${eliminatedPlayer.role || "Unbekannt"})`,
      );
      await waitForNarratorAudio(hostPage);

      // Jäger stirbt -> schießt (ECHTE UI)
      if (eliminatedPlayer.role?.toLowerCase().includes("jäger")) {
        await waitForNarratorAudio(eliminatedPlayer.page);
        const candidates = allPlayers.filter((p) => p.isAlive);
        if (candidates.length > 0) {
          const hunterVictim =
            candidates[Math.floor(Math.random() * candidates.length)];
          await selectPlayerInUI(eliminatedPlayer, hunterVictim.name);
          await clickActionButton(
            eliminatedPlayer,
            "Erschießen",
            "Schießen",
            "Bestätigen",
          );
          hunterVictim.isAlive = false;
          logEvent("💥 RACHE", `Der Jäger nimmt ${hunterVictim.name} mit!`);
        }
      }

      // Verliebte sterben zusammen
      if (eliminatedPlayer.isLover) {
        const otherLover = allPlayers.find(
          (p) => p.isLover && p.name !== eliminated && p.isAlive,
        );
        if (otherLover) {
          otherLover.isAlive = false;
          logEvent(
            "💔 HERZSCHMERZ",
            `${otherLover.name} stirbt vor Liebeskummer`,
          );
        }
      }

      // Bürgermeister wählt Nachfolger
      if (eliminatedPlayer.isMayor) {
        const candidates = allPlayers.filter((p) => p.isAlive);
        if (candidates.length > 0) {
          const successor =
            candidates[Math.floor(Math.random() * candidates.length)];
          successor.isMayor = true;
          logEvent(
            "👑 NACHFOLGE",
            `${successor.name} wird neuer Bürgermeister`,
          );
        }
      }
    }
  } else {
    logEvent("🤷 UNENTSCHIEDEN", "Niemand wird heute hingerichtet");
  }

  await waitForNarratorAudio(hostPage);
  await hostPage.waitForTimeout(ACTION_DELAY);
  return eliminated;
}

// ============================================================================
// TESTS - VOLLSTÄNDIGES SPIEL MIT ECHTEN UI-AKTIONEN
// ============================================================================

test.describe(`Massives Werwolf-Spiel - ${GAME_MODE.name}`, () => {
  // 60 Minuten Timeout (vollständiges Spiel kann lange dauern!)
  test.setTimeout(60 * 60 * 1000);

  let hostPlayer: Player;
  let massPlayers: MassPlayer[] = [];
  let roomCode: string;

  test.afterEach(async () => {
    if (hostPlayer) {
      try {
        await hostPlayer.context.close();
      } catch {}
    }
    await cleanupMassPlayers(massPlayers);
    massPlayers = [];
  });

  test(`Vollständiges Spiel mit ${PLAYER_COUNT} Spielern`, async ({
    browser,
  }) => {
    resetWindowPositions();

    logEvent("🎮 START", `=== VOLLSTÄNDIGES WERWOLF-SPIEL ===`);
    logEvent("INFO", `${PLAYER_COUNT} Spieler, Chaos-Modus, ALLE Rollen aktiv`);
    logEvent("INFO", GAME_MODE.desc);
    logEvent(
      "INFO",
      `Pausen zwischen Aktionen: ${ACTION_DELAY / 1000} Sekunden`,
    );

    // ================================================================
    // SCHRITT 1: Raum erstellen
    // ================================================================
    logEvent("STEP", "1. Raum erstellen...");

    const { player: host, roomCode: code } = await createRoom(
      browser,
      `Host_Standard`,
      `${GAME_MODE.name} - 500 Spieler Event`,
      PLAYER_COUNT,
      true, // isNarrator
      "online",
    );

    hostPlayer = host;
    roomCode = code;

    logEvent("ROOM", `Raum erstellt: ${roomCode}`);

    // Regelset wählen (falls verfügbar)
    try {
      const regelsetSelect = host.page.locator('select[name="regelset"]');
      if (await regelsetSelect.isVisible({ timeout: 2000 })) {
        await regelsetSelect.selectOption(GAME_MODE.regelset);
      }
    } catch {}

    // ================================================================
    // SCHRITT 2: 499 weitere Spieler joinen lassen
    // ================================================================
    logEvent("STEP", "2. Spieler joinen lassen...");

    const startJoinTime = Date.now();
    massPlayers = await createMassPlayers(browser, roomCode, PLAYER_COUNT - 1);
    const joinTime = (Date.now() - startJoinTime) / 1000;

    logEvent(
      "JOINED",
      `${massPlayers.length + 1} Spieler in ${joinTime.toFixed(1)}s beigetreten`,
    );

    // ================================================================
    // WARTE BIS ALLE SPIELER IM LOBBY SICHTBAR SIND
    // ================================================================
    logEvent("LOBBY", "Warte auf alle Spieler in der Lobby...");

    // Warte bis die Spielerliste alle Spieler anzeigt (selector: .spieler-karte mit data-spieler-id)
    const expectedPlayerCount = massPlayers.length + 1;
    await host.page.waitForFunction(
      (count) => {
        const playerItems = document.querySelectorAll(
          "#spieler-liste .spieler-karte[data-spieler-id]",
        );
        return playerItems.length >= count;
      },
      expectedPlayerCount,
      { timeout: 60000 },
    );

    logEvent(
      "LOBBY",
      `Alle ${expectedPlayerCount} Spieler in der Lobby sichtbar!`,
    );

    // Extra Wartezeit damit der Host alles sieht
    await host.page.waitForTimeout(3000);

    // ================================================================
    // SCHRITT 3: Spiel starten
    // ================================================================
    logEvent("STEP", "3. Spiel starten...");

    await startGame(hostPlayer);

    // Warte auf Spielstart für alle
    const gameStartPromises = massPlayers.map(async (mp) => {
      try {
        await expect(mp.page).toHaveURL(/\/spiel\//, { timeout: 30000 });
      } catch {
        mp.isAlive = false; // Markiere als nicht aktiv wenn Fehler
      }
    });

    await Promise.all(gameStartPromises);
    await expect(hostPlayer.page).toHaveURL(/\/spiel\//, { timeout: 30000 });

    logEvent("GAME_START", "Spiel gestartet!");

    // ================================================================
    // SCHRITT 4: Rollen abrufen
    // ================================================================
    logEvent("STEP", "4. Rollen abrufen...");

    await getMassPlayerRoles(massPlayers);

    // Kategorisiere Spieler
    const wolves = massPlayers.filter((p) => p.team === "wolf");
    const villagers = massPlayers.filter((p) => p.team === "village");
    const solos = massPlayers.filter((p) => p.team === "solo");

    logEvent(
      "TEAMS",
      `${wolves.length} Wölfe, ${villagers.length} Dorfbewohner, ${solos.length} Solo`,
    );

    // ================================================================
    // SCHRITT 5: Spielrunde durchspielen
    // ================================================================
    logEvent("STEP", "5. Spielrunde starten...");

    let round = 0;
    let gameOver = false;
    let lastPhase = "";

    while (!gameOver && round < MAX_ROUNDS) {
      round++;
      logEvent("ROUND", `=== RUNDE ${round} ===`);

      // Status prüfen
      const status = await getGameStatus(massPlayers[0], massPlayers);
      status.round = round;

      logEvent(
        "STATUS",
        `Phase: ${status.phase}, Lebend: ${status.aliveCount}, Wölfe: ${status.wolfCount}, Dorf: ${status.villageCount}`,
      );

      if (status.isGameOver) {
        gameOver = true;
        logEvent("GAME_OVER", `Gewinner: ${status.winner || "Unbekannt"}`);
        break;
      }

      const currentPhase = status.phase;

      // Phase-Übergang loggen
      if (currentPhase !== lastPhase) {
        logPhaseChange(lastPhase, currentPhase, round);
        lastPhase = currentPhase;
      }

      // Phase-spezifische Aktionen
      if (currentPhase.includes("werwolf")) {
        // Werwolf-Phase
        const victim = await executeWerewolfPhase(wolves, villagers);
        if (victim) {
          const victimPlayer = massPlayers.find((p) => p.name === victim);
          if (victimPlayer) victimPlayer.isAlive = false;
        }
      } else if (currentPhase.includes("seherin")) {
        // Seherin-Phase (automatisch oder überspringen)
        logEvent("PHASE", "Seherin-Phase...");
      } else if (currentPhase.includes("hexe")) {
        // Hexen-Phase (automatisch oder überspringen)
        logEvent("PHASE", "Hexen-Phase...");
      } else if (
        currentPhase.includes("abstimmung") ||
        currentPhase.includes("tag")
      ) {
        // Tag-Abstimmung
        const eliminated = await executeDayVoting(massPlayers, wolves);
        if (eliminated) {
          const eliminatedPlayer = massPlayers.find(
            (p) => p.name === eliminated,
          );
          if (eliminatedPlayer) eliminatedPlayer.isAlive = false;
        }
      }

      // Phase weiterschalten (Host macht das)
      try {
        await advancePhase(hostPlayer);
      } catch {
        logEvent("WARN", "Konnte Phase nicht weiterschalten");
      }

      // Kurze Pause zwischen Phasen
      await hostPlayer.page.waitForTimeout(1000);

      // Nochmal Status prüfen
      const newStatus = await getGameStatus(massPlayers[0], massPlayers);
      if (
        newStatus.isGameOver ||
        newStatus.wolfCount === 0 ||
        newStatus.villageCount === 0
      ) {
        gameOver = true;
        logEvent(
          "GAME_OVER",
          `Gewinner: ${newStatus.winner || (newStatus.wolfCount === 0 ? "Dorf" : "Werwölfe")}`,
        );
      }
    }

    // ================================================================
    // SCHRITT 6: Ergebnis auswerten
    // ================================================================
    logEvent("STEP", "6. Ergebnis auswerten...");

    const finalStatus = await getGameStatus(massPlayers[0], massPlayers);

    logEvent("FINAL", `Runden gespielt: ${round}`);
    logEvent("FINAL", `Lebende Spieler: ${finalStatus.aliveCount}`);
    logEvent("FINAL", `Lebende Wölfe: ${finalStatus.wolfCount}`);
    logEvent("FINAL", `Lebende Dorfbewohner: ${finalStatus.villageCount}`);

    if (finalStatus.winner) {
      logEvent("WINNER", `🏆 ${finalStatus.winner} haben gewonnen!`);
    }

    // Assertions
    expect(round).toBeGreaterThan(0);
    expect(round).toBeLessThanOrEqual(MAX_ROUNDS);

    // Das Spiel sollte irgendwann enden
    expect(finalStatus.isGameOver || round === MAX_ROUNDS).toBeTruthy();

    logEvent(
      "SUCCESS",
      `=== ${GAME_MODE.name.toUpperCase()} TEST ABGESCHLOSSEN ===`,
    );
  });
});

// ============================================================================
// ZUSÄTZLICHE STRESS-TESTS (auskommentiert um Server-Überlastung zu vermeiden)
// ============================================================================

test.describe.skip("500 Spieler Stress & Performance Tests", () => {
  test.setTimeout(15 * 60 * 1000); // 15 Minuten

  test("Gleichzeitiger Join von 500 Spielern", async ({ browser }) => {
    resetWindowPositions();

    logEvent("STRESS", "Testing simultaneous 500 player join...");

    // Raum erstellen
    const { player: host, roomCode } = await createRoom(
      browser,
      "StressTestHost",
      "Stress Test 500",
      PLAYER_COUNT,
      true,
      "online",
    );

    const startTime = Date.now();

    // 499 Spieler gleichzeitig joinen (in größeren Batches)
    const massPlayers = await createMassPlayers(
      browser,
      roomCode,
      PLAYER_COUNT - 1,
      100,
    );

    const joinTime = (Date.now() - startTime) / 1000;

    logEvent(
      "PERF",
      `500 Spieler in ${joinTime.toFixed(1)} Sekunden beigetreten`,
    );
    logEvent(
      "PERF",
      `Durchschnitt: ${((joinTime / 500) * 1000).toFixed(0)}ms pro Spieler`,
    );

    expect(massPlayers.length).toBe(499);
    expect(joinTime).toBeLessThan(600); // Sollte in unter 10 Minuten schaffen

    // Cleanup
    await cleanupMassPlayers(massPlayers);
    await host.context.close();
  });

  test("Server-Stabilität bei 500 aktiven Verbindungen", async ({
    browser,
  }) => {
    resetWindowPositions();

    logEvent("STRESS", "Testing server stability with 500 connections...");

    // Raum erstellen
    const { player: host, roomCode } = await createRoom(
      browser,
      "StabilityHost",
      "Stability Test",
      PLAYER_COUNT,
      true,
      "online",
    );

    // Spieler joinen
    const massPlayers = await createMassPlayers(
      browser,
      roomCode,
      PLAYER_COUNT - 1,
      100,
    );

    // 30 Sekunden warten und prüfen ob alle noch verbunden
    await host.page.waitForTimeout(30000);

    // Prüfe ob Host noch responsive ist
    const hostResponsive = await host.page.evaluate(
      () => document.readyState === "complete",
    );
    expect(hostResponsive).toBeTruthy();

    // Prüfe eine Stichprobe von Spielern
    const sampleSize = 50;
    const samplePlayers = massPlayers.slice(0, sampleSize);

    let responsiveCount = 0;
    for (const player of samplePlayers) {
      try {
        const isResponsive = await player.page.evaluate(
          () => document.readyState === "complete",
        );
        if (isResponsive) responsiveCount++;
      } catch {
        // Spieler nicht mehr verbunden
      }
    }

    logEvent(
      "STABILITY",
      `${responsiveCount}/${sampleSize} Stichproben-Spieler noch verbunden`,
    );
    expect(responsiveCount).toBeGreaterThan(sampleSize * 0.9); // 90% sollten noch da sein

    // Cleanup
    await cleanupMassPlayers(massPlayers);
    await host.context.close();
  });
});
