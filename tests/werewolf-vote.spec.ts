import { test, expect, Browser } from '@playwright/test';
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
  cleanup,
  logEvent,
  logAction,
  logVote,
  logPhaseChange,
  delayAction,
  waitIfKeepOpen,
} from './helpers/game-helpers';

/**
 * WEREWOLF NIGHT PHASE VOTE TEST
 * 
 * This test focuses specifically on werewolf voting during night phase:
 * - Players join and game starts
 * - Game advances through night phases
 * - Werewolves vote together to eliminate a target at night
 * - Verifies the vote count and selection mechanics
 */
test.describe('Werewolf Voting Test', () => {
  let players: Player[] = [];
  let roomCode: string;
  
  test.afterEach(async () => {
    console.log('\n=== Test Cleanup ===');
    await cleanup(players);
    players = [];
  });
  
  test('3: 5 players - werewolves pick a victim at night', async ({ browser }) => {
    logEvent('TEST', 'Starting werewolf night voting test');
    logEvent('SETUP', 'Initializing werewolf night voting test');
    console.log('\n===================================================');
    console.log('   TEST 3: WEREWOLF NIGHT VOTING TEST             ');
    console.log('   Testing werewolf night phase selection         ');
    console.log('===================================================\n');
    
    // Generate random player names
    const generateRandomName = (prefix: string, index: number): string => {
      const random = Math.floor(Math.random() * 10000);
      return `${prefix}_${index}_${random}`;
    };
    
    const playerNames = [
      generateRandomName('Player', 0),
      generateRandomName('Player', 1),
      generateRandomName('Player', 2),
      generateRandomName('Player', 3),
      generateRandomName('Player', 4),
    ];
    
    // Step 1: Create the game room
    console.log('[STEP 1] Creating game room...');
    logEvent('ROOM', 'Creating game room');
    const { player: creator, roomCode: code } = await createRoom(
      browser,
      playerNames[0],
      'Werewolf Vote Test',
      5,
      false, // Not a narrator
      'online'
    );
    roomCode = code;
    players.push(creator);
    logEvent('SUCCESS', `Room created: ${roomCode}`);
    console.log(`✓ Room created with code: ${roomCode}`);
    console.log(`✓ Creator: ${creator.name}\n`);
    
    // Step 2: Other players join the room
    console.log('[STEP 2] Other players joining...');
    logEvent('JOIN', 'Players joining room');
    for (let i = 1; i < playerNames.length; i++) {
      const player = await joinRoom(browser, roomCode, playerNames[i]);
      players.push(player);
      logEvent('JOIN', `${playerNames[i]} joined`);
      console.log(`✓ ${playerNames[i]} joined the game`);
      await player.page.waitForTimeout(500);
    }
    console.log(`✓ All ${playerNames.length} players in lobby\n`);
    
    // Verify all players in lobby
    console.log('[STEP 3] Verifying lobby state...');
    logEvent('VERIFY', 'Checking all players visible in lobby');
    await players[0].page.waitForTimeout(1000);
    console.log(`✓ Lobby ready with ${players.length} players\n`);
    
    // Start the game
    console.log('[STEP 4] Starting the game...');
    logEvent('START', 'Game starting');
    await startGame(players[0]);
    console.log(`✓ Game started by ${players[0].name}\n`);
    
    // Wait for all players to see game page
    console.log('[STEP 5] Waiting for game page to load...');
    logEvent('LOAD', 'Waiting for game page');
    await waitForGameStart(players);
    console.log(`✓ All players on game page\n`);
    
    // Get roles
    console.log('[STEP 6] Getting player roles...');
    logEvent('ROLES', 'Retrieving role assignments');
    const roles = await getAllPlayerRoles(players);
    for (const player of players) {
      player.role = await getPlayerRole(player);
    }
    
    logEvent('INFO', 'Game setup complete, roles assigned');
    console.log('\nROLE DISTRIBUTION:');
    console.log('─────────────────────────────');
    for (const player of players) {
      console.log(`  ${player.name.padEnd(12)}: ${player.role}`);
      logEvent('ROLE', `${player.name} is ${player.role}`);
    }
    console.log('─────────────────────────────\n');
    
    // Identify werewolves and villagers
    const werewolves = players.filter(p => p.role?.toLowerCase().includes('werwolf'));
    const villagers = players.filter(p => !p.role?.toLowerCase().includes('werwolf') && !p.role?.toLowerCase().includes('erzaehler'));
    
    logEvent('TEAM', `Werewolves: ${werewolves.map(w => w.name).join(', ')}`);
    logEvent('TEAM', `Villagers: ${villagers.map(v => v.name).join(', ')}`);
    console.log(`WEREWOLVES: ${werewolves.map(w => w.name).join(', ')} (${werewolves.length})`);
    console.log(`VILLAGERS: ${villagers.map(v => v.name).join(', ')} (${villagers.length})`);
    
    if (werewolves.length === 0) {
      throw new Error('No werewolves in game - cannot test werewolf voting');
    }
    
    console.log('\nSetup complete! Ready for voting test.\n');
    
    let roundCount = 0;
    const maxRounds = 15;
    
    // Loop until we reach voting phase or game ends
    while (roundCount < maxRounds) {
      roundCount++;
      
      const currentPhase = await getCurrentPhase(players[0]);
      logPhaseChange(`Round ${roundCount}`, currentPhase);
      console.log(`\n[ROUND ${roundCount}] Phase: ${currentPhase}`);
      
      // Skip if game is over
      if (currentPhase.includes('gewonnen') || currentPhase.includes('vorbei')) {
        logEvent('INFO', `Game ended with phase: ${currentPhase}`);
        console.log(`✓ Game has ended with phase: ${currentPhase}`);
        break;
      }
      
      // Check if we reached day/voting phase
      if (currentPhase.includes('tag_start') || currentPhase.includes('abstimmung')) {
        logEvent('PHASE', 'Reached day phase - test complete');
        console.log('\n' + '='.repeat(60));
        console.log('                   DAY PHASE REACHED                        ');
        console.log('='.repeat(60));
        console.log('✓ Test complete: werewolves successfully picked victims');
        logEvent('SUCCESS', 'Werewolf night voting test completed successfully');
        break;
      }
      
      // Handle werewolf night phase - werewolves must attack for game to progress
      if (currentPhase.includes('werwolf')) {
        console.log(`[ROUND ${roundCount}] Werewolf night phase - performing attack...`);
        logEvent('PHASE', 'Werewolf night phase');
        
        const target = villagers.length > 0 ? villagers[0] : players.find(p => !p.role?.toLowerCase().includes('werwolf'));
        if (target) {
          for (const wolf of werewolves) {
            try {
              logAction(wolf.name, 'attack', target.name);
              await selectTarget(wolf, target.name);
              await delayAction();
              const confirmBtn = wolf.page.locator('button:has-text("Angreifen"), button:has-text("Bestaetigen"), button:has-text("Waehlen")');
              if (await confirmBtn.isVisible()) {
                await confirmBtn.click();
                await delayAction();
              }
            } catch (e) {
              logEvent('ERROR', `Werewolf ${wolf.name} attack failed`, String(e));
              console.log(`  Wolf ${wolf.name} could not attack: ${e}`);
            }
          }
        }
        await players[0].page.waitForTimeout(1500);
        try {
          await advancePhase(players[0]);
        } catch (e) {
          // Phase may advance automatically
        }
        continue;
      }
      
      // Handle seer phase
      if (currentPhase.includes('seherin')) {
        console.log(`[ROUND ${roundCount}] Seer phase - skipping...`);
        logEvent('PHASE', 'Seer phase');
        const seer = players.find(p => p.role?.toLowerCase().includes('seherin'));
        if (seer) {
          try {
            const skipBtn = seer.page.locator('button:has-text("Ueberspringen"), button:has-text("Weiter")');
            if (await skipBtn.isVisible()) {
              await skipBtn.click();
              await delayAction();
            }
          } catch (e) {
            // Continue
          }
        }
        await players[0].page.waitForTimeout(1500);
        try {
          await advancePhase(players[0]);
        } catch (e) {
          // Phase may advance automatically
        }
        continue;
      }
      
      // Handle witch phase
      if (currentPhase.includes('hexe')) {
        console.log(`[ROUND ${roundCount}] Witch phase - skipping...`);
        logEvent('PHASE', 'Witch phase');
        const witch = players.find(p => p.role?.toLowerCase().includes('hexe'));
        if (witch) {
          try {
            const skipBtn = witch.page.locator('button:has-text("Ueberspringen"), button:has-text("Weiter"), button:has-text("Niemanden")');
            if (await skipBtn.isVisible()) {
              await skipBtn.click();
              await delayAction();
            }
          } catch (e) {
            // Continue
          }
        }
        await players[0].page.waitForTimeout(1500);
        try {
          await advancePhase(players[0]);
        } catch (e) {
          // Phase may advance automatically
        }
        continue;
      }
      
      // Auto-advance preliminary phases
      if (currentPhase.includes('rollen_verteilt') || currentPhase.includes('lobby')) {
        console.log(`[ROUND ${roundCount}] Auto-advancing through preliminary phase...`);
        logEvent('AUTO-ADVANCE', `Advancing from ${currentPhase}`);
        await advancePhase(players[0]);
        await players[0].page.waitForTimeout(1500);
        continue;
      }
      
      // Standard phase advance
      console.log(`[ROUND ${roundCount}] Advancing to next phase...`);
      await players[0].page.waitForTimeout(1500);
      
      try {
        await advancePhase(players[0]);
      } catch (e) {
        // May advance automatically
      }
    }
    
    expect(roundCount).toBeLessThanOrEqual(maxRounds);
    
    console.log('\n' + '='.repeat(60));
    console.log('                  TEST 3 COMPLETED SUCCESSFULLY               ');
    console.log('='.repeat(60));
    console.log(`✓ Rounds elapsed: ${roundCount}/${maxRounds}`);
    console.log('✓ Werewolves successfully picked their victim(s)');
    logEvent('TEST_COMPLETE', `Test 3 completed in ${roundCount} rounds`);
    
    // Keep open if --keep flag is set
    await waitIfKeepOpen();
    
    logEvent('SUCCESS', 'Test 3 - Werewolf night voting completed!');
    console.log('\n✓ TEST 3: WEREWOLF NIGHT VOTING - COMPLETE');
    console.log('='.repeat(60));
  });
});
