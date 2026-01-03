/**
 * ============================================================================
 * WEBWÖLFE - GAME SETUP TEST
 * ============================================================================
 *
 * Dieses Script startet mehrere Browser-Fenster, erstellt automatisch ein Spiel
 * und lässt alle Fenster offen für manuelles Testen.
 *
 * Usage:
 *   PLAYERS=8 npx playwright test tests/game_setup.spec.ts --headed --timeout=0
 *   ./game_setup.sh 8
 *
 * Features:
 * - Automatisches Erstellen eines Raums
 * - Automatisches Beitreten aller Spieler
 * - Fenster bleiben offen für manuelles Testen
 * - Fenster werden nebeneinander angeordnet
 */

import {
  test,
  expect,
  Browser,
  BrowserContext,
  Page,
  chromium,
} from "@playwright/test";

// Konfiguration
const PLAYER_COUNT = parseInt(process.env.PLAYERS || "8", 10);
const BASE_URL = process.env.BASE_URL || "http://localhost:5001";
const IS_MACOS = process.platform === "darwin";
const HEADLESS_OTHERS = process.env.HL === "1" || process.env.HL === "true";

// Spielernamen
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

interface PlayerWindow {
  context: BrowserContext;
  page: Page;
  name: string;
  isErzaehler: boolean;
}

// Fenster-Layout berechnen
function calculateWindowLayout(
  index: number,
  total: number,
): { x: number; y: number; width: number; height: number } {
  const screenWidth = 1920;
  const screenHeight = 1080;

  // Berechne optimales Grid
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

test.describe("Game Setup - Auto-Create and Stay Open", () => {
  test(`Setup game with ${PLAYER_COUNT} players`, async () => {
    const players: PlayerWindow[] = [];
    let roomCode = "";

    console.log(`\n🐺 Webwölfe Game Setup`);
    console.log(`==========================================`);
    console.log(`Spieleranzahl: ${PLAYER_COUNT}`);
    console.log(`Base URL: ${BASE_URL}`);
    console.log(`Headless Others: ${HEADLESS_OTHERS ? "Ja" : "Nein"}`);
    console.log(`==========================================\n`);

    // Browser starten (headed für Erzähler)
    const browser = await chromium.launch({
      headless: false,
      args: ["--disable-web-security", "--no-sandbox"],
    });

    // Headless Browser für andere Spieler (wenn HL Flag gesetzt)
    const headlessBrowser = HEADLESS_OTHERS
      ? await chromium.launch({
          headless: true,
          args: ["--disable-web-security", "--no-sandbox"],
        })
      : null;

    try {
      // ============================================
      // 1. Ersteller (Erzähler) - Erstellt den Raum
      // ============================================
      console.log("📝 Erstelle Raum...");

      const layout0 = calculateWindowLayout(0, PLAYER_COUNT);
      const erzaehlerContext = await browser.newContext({ viewport: null });
      const erzaehlerPage = await erzaehlerContext.newPage();

      // Fenster positionieren
      await erzaehlerPage.evaluate(
        ({ x, y }) => {
          window.moveTo(x, y);
        },
        { x: layout0.x, y: layout0.y },
      );

      // Zur Startseite navigieren
      await erzaehlerPage.goto(BASE_URL);
      await erzaehlerPage.waitForLoadState("networkidle");

      // Pre-Alpha Modal schließen falls vorhanden
      const closeModalBtn = erzaehlerPage.locator("[data-close-modal]").first();
      if (await closeModalBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
        await closeModalBtn.click();
        await erzaehlerPage.waitForTimeout(300);
      }

      // Name eingeben
      const erzaehlerName = PLAYER_NAMES[0];
      await erzaehlerPage.fill('input[name="spieler_name"]', erzaehlerName);

      // Online-Modus auswählen (automatischer Erzähler)
      // Dies ist der Standard, aber wir stellen sicher, dass er ausgewählt ist
      const modusSelect = erzaehlerPage.locator("#modus-select");
      await modusSelect.selectOption("online");
      console.log("✓ Online-Modus mit automatischem Erzähler ausgewählt");

      // Raum erstellen
      const createBtn = erzaehlerPage.locator(
        'button:has-text("Spiel erstellen")',
      );
      await createBtn.click();

      // Warte auf Lobby und hole Raumcode
      await erzaehlerPage.waitForURL(/\/lobby\//);

      // Raumcode aus URL oder Seite extrahieren
      const url = erzaehlerPage.url();
      const urlMatch = url.match(/\/lobby\/([A-Z0-9]+)/i);
      if (urlMatch) {
        roomCode = urlMatch[1];
      } else {
        // Fallback: Aus Seite extrahieren
        const codeElement = await erzaehlerPage
          .locator('.room-code, [class*="code"], h2')
          .first();
        roomCode = (await codeElement.textContent())?.trim() || "";
      }

      console.log(`✓ Raum erstellt: ${roomCode}`);
      console.log(`✓ Erzähler: ${erzaehlerName}\n`);

      players.push({
        context: erzaehlerContext,
        page: erzaehlerPage,
        name: erzaehlerName,
        isErzaehler: true,
      });

      // ============================================
      // 2. Weitere Spieler beitreten lassen
      // ============================================
      console.log("👥 Spieler treten bei...");

      for (let i = 1; i < PLAYER_COUNT; i++) {
        const playerName =
          PLAYER_NAMES[i % PLAYER_NAMES.length] +
          (i >= PLAYER_NAMES.length
            ? ` ${Math.floor(i / PLAYER_NAMES.length) + 1}`
            : "");
        const layout = calculateWindowLayout(i, PLAYER_COUNT);

        // Verwende headless Browser wenn HL Flag gesetzt
        const targetBrowser = headlessBrowser || browser;
        const context = await targetBrowser.newContext({ viewport: null });
        const page = await context.newPage();

        // Fenster positionieren (nur wenn nicht headless)
        if (!HEADLESS_OTHERS) {
          await page.evaluate(
            ({ x, y }) => {
              window.moveTo(x, y);
            },
            { x: layout.x, y: layout.y },
          );
        }

        // Zur Startseite
        await page.goto(BASE_URL);
        await page.waitForLoadState("networkidle");

        // Pre-Alpha Modal schließen falls vorhanden
        const closeModal = page.locator("[data-close-modal]").first();
        if (await closeModal.isVisible({ timeout: 1000 }).catch(() => false)) {
          await closeModal.click();
          await page.waitForTimeout(200);
        }

        // "Beitreten" Formular ist die zweite Card auf der Seite
        // Name eingeben (zweites spieler_name Feld)
        const beitretenCard = page.locator(".card").nth(1);
        await beitretenCard
          .locator('input[name="spieler_name"]')
          .fill(playerName);

        // Raumcode eingeben
        await beitretenCard.locator('input[name="code"]').fill(roomCode);

        // "Beitreten" Button klicken
        await beitretenCard.locator('button:has-text("Beitreten")').click();

        // Warte auf Lobby
        await page.waitForURL(/\/lobby\//);

        players.push({
          context,
          page,
          name: playerName,
          isErzaehler: false,
        });

        console.log(`  ✓ ${playerName} beigetreten (${i + 1}/${PLAYER_COUNT})`);

        // Kleine Verzögerung zwischen Joins
        await new Promise((r) => setTimeout(r, 200));
      }

      console.log(`\n✅ Alle ${PLAYER_COUNT} Spieler sind beigetreten!`);
      console.log(`\n==========================================`);
      console.log(`🎮 RAUMCODE: ${roomCode}`);
      console.log(`==========================================`);
      console.log(`\nDie Fenster bleiben offen für manuelles Testen.`);
      console.log(`Drücke Strg+C um alle Fenster zu schließen.\n`);

      // ============================================
      // 3. Fenster offen lassen für manuelles Testen
      // ============================================
      // Wir warten unendlich lange, damit die Fenster offen bleiben
      await new Promise(() => {
        // Diese Promise resolved nie - die Fenster bleiben offen
        // bis der Nutzer Strg+C drückt
      });
    } catch (error) {
      console.error("❌ Fehler:", error);
      throw error;
    }
  });
});
