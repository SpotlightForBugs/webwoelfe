import { Page, BrowserContext, Browser, expect, BrowserContextOptions } from '@playwright/test';

// Track window positions for tiling
let windowPositionIndex = 0;
const WINDOW_WIDTH = 900;
const WINDOW_HEIGHT = 700;
const WINDOWS_PER_ROW = 2;

/**
 * Calculate window position for tiling
 */
function getContextOptions(): BrowserContextOptions {
  const row = Math.floor(windowPositionIndex / WINDOWS_PER_ROW);
  const col = windowPositionIndex % WINDOWS_PER_ROW;
  
  windowPositionIndex++;
  
  return {
    viewport: { width: WINDOW_WIDTH, height: WINDOW_HEIGHT },
  };
}

/**
 * Reset window position counter (call at start of test)
 */
export function resetWindowPositions(): void {
  windowPositionIndex = 0;
}

/**
 * Get action delay from environment
 */
export function getActionDelay(): number {
  const delay = process.env.TEST_ACTION_DELAY;
  return delay ? parseInt(delay, 10) : 0;
}

/**
 * Should keep browser open
 */
export function shouldKeepOpen(): boolean {
  return process.env.TEST_KEEP_OPEN === 'true';
}

/**
 * Delay between actions (respects --delay flag)
 */
export async function delayAction(): Promise<void> {
  const delay = getActionDelay();
  if (delay > 0) {
    await new Promise(resolve => setTimeout(resolve, delay));
  }
}

/**
 * Wait at end of test if --keep flag is set
 */
export async function waitIfKeepOpen(): Promise<void> {
  if (shouldKeepOpen()) {
    console.log('\n[KEEP-OPEN] Browser will stay open for 10 minutes for inspection...');
    logEvent('INFO', 'Test complete - keeping browser open for inspection');
    await new Promise(resolve => setTimeout(resolve, 10 * 60 * 1000));
  }
}

/**
 * Player interface representing a game participant
 */
export interface Player {
  context: BrowserContext;
  page: Page;
  name: string;
  role?: string;
  isNarrator?: boolean;
}

/**
 * Game state information
 */
export interface GameState {
  roomCode: string;
  players: Player[];
  narrator?: Player;
}

/**
 * Create a new game room
 */
export async function createRoom(
  browser: Browser,
  playerName: string,
  roomName: string = 'Test Game',
  playerCount: number = 5,
  isNarrator: boolean = true,
  mode: 'online' | 'gruppe' = 'online'
): Promise<{ player: Player; roomCode: string }> {
  const context = await browser.newContext(getContextOptions());
  const page = await context.newPage();
  
  // Go to home page
  await page.goto('/');
  await expect(page.locator('h1')).toBeVisible({ timeout: 10000 });
  
  // The create form is the first form (without the code input)
  const createForm = page.locator('form').filter({ hasNot: page.locator('input[name="code"]') });
  
  // Fill in the form to create a new game
  await createForm.locator('input[name="spieler_name"]').fill(playerName);
  await createForm.locator('input[name="raum_name"]').fill(roomName);
  await createForm.locator('input[name="spieler_anzahl"]').fill(String(playerCount));
  
  // Select mode
  await createForm.locator('select[name="modus"]').selectOption(mode);
  
  // For online mode, always make the creator a narrator so phases can advance
  // For gruppe mode, only if explicitly requested
  const shouldBeNarrator = mode === 'online' || isNarrator;
  if (shouldBeNarrator) {
    await createForm.locator('input[name="ist_erzaehler"]').check();
  }
  
  // Submit the form
  await createForm.locator('button[type="submit"]').click();
  
  // Wait for lobby page
  await expect(page).toHaveURL(/\/lobby\//, { timeout: 10000 });
  
  // Extract room code from the page
  const roomCodeElement = page.locator('.room-code');
  await expect(roomCodeElement).toBeVisible({ timeout: 5000 });
  const roomCode = (await roomCodeElement.textContent())?.trim() || '';
  
  return {
    player: {
      context,
      page,
      name: playerName,
      isNarrator
    },
    roomCode
  };
}

/**
 * Join an existing game room
 */
export async function joinRoom(
  browser: Browser,
  roomCode: string,
  playerName: string
): Promise<Player> {
  const context = await browser.newContext(getContextOptions());
  const page = await context.newPage();
  
  // Go to home page
  await page.goto('/');
  
  // The join form is the second form on the page (after the create form)
  // It has an input with name="code"
  const joinForm = page.locator('form').filter({ has: page.locator('input[name="code"]') });
  
  // Fill the player name first
  await joinForm.locator('input[name="spieler_name"]').fill(playerName);
  
  // Fill the room code
  await joinForm.locator('input[name="code"]').fill(roomCode);
  
  // Submit the join form
  await joinForm.locator('button[type="submit"]').click();
  
  // Wait for lobby page
  await expect(page).toHaveURL(/\/lobby\//, { timeout: 10000 });
  
  return {
    context,
    page,
    name: playerName,
    isNarrator: false
  };
}

/**
 * Start the game from the lobby (any player can start if enough players)
 */
export async function startGame(player: Player): Promise<void> {
  const startButton = player.page.locator('#start-btn, button:has-text("Spiel starten")');
  await expect(startButton).toBeVisible({ timeout: 10000 });
  await startButton.click();
  
  // Wait for navigation to game page
  await expect(player.page).toHaveURL(/\/spiel\//, { timeout: 15000 });
}

/**
 * Wait for all players to be on the game page
 */
export async function waitForGameStart(players: Player[]): Promise<void> {
  for (const player of players) {
    await expect(player.page).toHaveURL(/\/spiel\//, { timeout: 30000 });
  }
}

/**
 * Get the current player's role from the game page
 */
export async function getPlayerRole(player: Player): Promise<string> {
  // Wait for role badge to be visible
  const roleBadge = player.page.locator('.rolle-badge');
  await expect(roleBadge).toBeVisible({ timeout: 10000 });
  
  const roleText = await roleBadge.textContent();
  player.role = roleText?.trim() || 'Unknown';
  return player.role;
}

/**
 * Get all players' roles
 */
export async function getAllPlayerRoles(players: Player[]): Promise<Map<string, string>> {
  const roleMap = new Map<string, string>();
  
  for (const player of players) {
    const role = await getPlayerRole(player);
    roleMap.set(player.name, role);
  }
  
  return roleMap;
}

/**
 * Advance to next phase (for narrator or automatic games)
 */
export async function advancePhase(player: Player): Promise<void> {
  // Try to emit socket event directly (for online mode with narrator)
  try {
    await player.page.evaluate(() => {
      // Directly call the naechstePhase function if it exists
      if (typeof (window as any).naechstePhase === 'function') {
        (window as any).naechstePhase();
      } else if (typeof (window as any).socket !== 'undefined') {
        // Or emit the socket event
        (window as any).socket.emit('phase_weiter');
      }
    });
  } catch (e) {
    // Fallback: Try to find and click a button
    const buttons = [
      'button:has-text("Weiter")',
      'button:has-text("Phase")',
      '#phase-weiter-btn',
      'button:has-text("Naechste Phase")',
      'button:has-text("Naechste Runde")',
      'button[type="button"]:visible'
    ];
    
    for (const selector of buttons) {
      try {
        const btn = player.page.locator(selector);
        if (await btn.isVisible({ timeout: 500 }).catch(() => false)) {
          await btn.first().click();
          break;
        }
      } catch (e) {
        // Continue trying next selector
      }
    }
  }
  
  // Wait for phase transition
  await player.page.waitForTimeout(1000);
}

/**
 * Get current phase from the game page
 */
export async function getCurrentPhase(player: Player): Promise<string> {
  const phaseElement = player.page.locator('#phase-name, .phase-name');
  const phaseText = await phaseElement.textContent();
  return phaseText?.trim().toLowerCase() || '';
}

/**
 * Select a player target (for voting, attacking, etc.)
 */
export async function selectTarget(player: Player, targetName: string): Promise<void> {
  const targetCard = player.page.locator(`.spieler-card[data-name="${targetName}"], .spieler-card:has-text("${targetName}")`);
  await expect(targetCard).toBeVisible();
  await targetCard.click();
  // Wait for action buttons to update after selection
  await player.page.waitForTimeout(300);
}

/**
 * Confirm an action (after selecting a target)
 */
export async function confirmAction(player: Player, actionText: string = 'Bestaetigen'): Promise<void> {
  const confirmButton = player.page.locator(`button:has-text("${actionText}"), .btn-primary:has-text("${actionText}")`);
  // Wait for button to become visible
  await expect(confirmButton).toBeVisible({ timeout: 5000 });
  if (await confirmButton.isVisible()) {
    await confirmButton.click();
    await player.page.waitForTimeout(500);
  }
}

/**
 * Perform a vote during daytime voting phase
 */
export async function vote(player: Player, targetName: string): Promise<void> {
  await selectTarget(player, targetName);
  await confirmAction(player, 'Abstimmen');
}

/**
 * Werewolf attack action
 */
export async function werewolfAttack(player: Player, targetName: string): Promise<void> {
  await selectTarget(player, targetName);
  await confirmAction(player, 'Angreifen');
}

/**
 * Seer see action
 */
export async function seerSee(player: Player, targetName: string): Promise<void> {
  await selectTarget(player, targetName);
  await confirmAction(player, 'Sehen');
}

/**
 * Witch heal action
 */
export async function witchHeal(player: Player): Promise<void> {
  const healButton = player.page.locator('button:has-text("Heilen"), button:has-text("Heiltrank")');
  if (await healButton.isVisible()) {
    await healButton.click();
    await player.page.waitForTimeout(500);
  }
}

/**
 * Witch poison action
 */
export async function witchPoison(player: Player, targetName: string): Promise<void> {
  await selectTarget(player, targetName);
  const poisonButton = player.page.locator('button:has-text("Vergiften"), button:has-text("Gifttrank")');
  if (await poisonButton.isVisible()) {
    await poisonButton.click();
    await player.page.waitForTimeout(500);
  }
}

/**
 * Skip/pass an action
 */
export async function skipAction(player: Player): Promise<void> {
  const skipButton = player.page.locator('button:has-text("Ueberspringen"), button:has-text("Nichts tun"), button:has-text("Weiter")');
  if (await skipButton.isVisible()) {
    await skipButton.click();
    await player.page.waitForTimeout(500);
  }
}

/**
 * Check if a player is dead on the game page
 */
export async function isPlayerDead(observer: Player, targetName: string): Promise<boolean> {
  const targetCard = observer.page.locator(`.spieler-card:has-text("${targetName}")`);
  const classes = await targetCard.getAttribute('class');
  return classes?.includes('tot') || false;
}

/**
 * Check if game has ended
 */
export async function isGameOver(player: Player): Promise<boolean> {
  const phase = await getCurrentPhase(player);
  return phase.includes('ende') || phase.includes('gewonnen');
}

/**
 * Get the winner of the game
 */
export async function getWinner(player: Player): Promise<string> {
  const winnerElement = player.page.locator('.winner, .gewinner, [data-winner]');
  if (await winnerElement.isVisible()) {
    return (await winnerElement.textContent())?.trim() || '';
  }
  return '';
}

/**
 * Clean up all player contexts
 */
export async function cleanup(players: Player[]): Promise<void> {
  for (const player of players) {
    try {
      await player.context.close();
    } catch {
      // Ignore cleanup errors
    }
  }
}

/**
 * Wait for a specific element to appear
 */
export async function waitForElement(player: Player, selector: string, timeout: number = 10000): Promise<boolean> {
  try {
    await player.page.waitForSelector(selector, { timeout });
    return true;
  } catch {
    return false;
  }
}

/**
 * Take a screenshot of a player's view
 */
export async function takeScreenshot(player: Player, name: string): Promise<void> {
  await player.page.screenshot({ path: `tests/screenshots/${name}-${player.name}.png` });
}

/**
 * Log game state for debugging
 */
export async function logGameState(players: Player[]): Promise<void> {
  console.log('--- Game State ---');
  for (const player of players) {
    const phase = await getCurrentPhase(player);
    console.log(`Player: ${player.name}, Role: ${player.role || 'Unknown'}, Phase: ${phase}`);
  }
  console.log('-------------------');
}

/**
 * Verbose logging for voting
 */
export function logVote(voter: string, votedFor: string, reason: string = ''): void {
  const reasonStr = reason ? ` (${reason})` : '';
  console.log(`[VOTE] ${voter} votes for ${votedFor}${reasonStr}`);
}

/**
 * Verbose logging for actions
 */
export function logAction(actor: string, action: string, target: string = '', details: string = ''): void {
  const targetStr = target ? ` on ${target}` : '';
  const detailsStr = details ? ` - ${details}` : '';
  console.log(`[ACTION] ${actor} performs ${action}${targetStr}${detailsStr}`);
}

/**
 * Verbose logging for phase changes
 */
export function logPhaseChange(oldPhase: string, newPhase: string, round: number = 0): void {
  const roundStr = round > 0 ? ` (Round ${round})` : '';
  console.log(`[PHASE] ${oldPhase} --> ${newPhase}${roundStr}`);
}

/**
 * Verbose logging for game events
 */
export function logEvent(eventType: string, message: string, details: string = ''): void {
  const detailsStr = details ? ` [${details}]` : '';
  console.log(`[${eventType.toUpperCase()}] ${message}${detailsStr}`);
}
