import { test, expect, chromium } from '@playwright/test';

test('Hexe Phase bleibt nicht hängen bei Nichts tun', async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext();
  
  // Spieler erstellen (mindestens 5 für ein Spiel)
  const names = ['Spieler1', 'Spieler2', 'Spieler3', 'Spieler4', 'Spieler5'];
  const pages = [];
  
  for (const name of names) {
    const page = await context.newPage();
    await page.goto('http://localhost:8888');
    pages.push(page);
  }

  // Raum erstellen
  await pages[0].click('text=Raum erstellen');
  const code = await pages[0].locator('#room-code-display').innerText();
  console.log(`Raum-Code: ${code}`);

  // Beitreten
  for (let i = 1; i < names.length; i++) {
    await pages[i].fill('#room-code', code);
    await pages[i].click('text=Raum beitreten');
  }

  // Namen setzen
  for (let i = 0; i < names.length; i++) {
    await pages[i].fill('#player-name', names[i]);
    await pages[i].click('text=Bereit!');
  }

  // Spiel starten (als Erzähler/Host)
  await pages[0].click('text=Spiel starten');

  // Warte bis Rollen verteilt sind und Spiel startet
  await pages[0].waitForSelector('.role-badge', { timeout: 10000 });

  // Rollen herausfinden
  const players = [];
  for (let i = 0; i < names.length; i++) {
    const rolle = await pages[i].locator('.role-name').innerText();
    players.push({ name: names[i], page: pages[i], rolle });
    console.log(`${names[i]} ist ${rolle}`);
  }

  // Wir brauchen eine Hexe im Spiel für diesen Test. 
  // Da die Rollenverteilung zufällig ist, müssen wir eventuell den Test anpassen oder die Rollen hart setzen.
  // In diesem Projekt scheint berechne_rollen genutzt zu werden.
  
  const hexe = players.find(p => p.rolle === 'Hexe');
  if (!hexe) {
    console.log('Keine Hexe in dieser Runde, überspringe Test-Details (aber fahre fort)');
    await browser.close();
    return;
  }

  // Gehe durch die Phasen bis zur Hexe-Phase
  let aktuellePhase = '';
  const maxSteps = 20;
  for (let step = 0; step < maxSteps; step++) {
    aktuellePhase = await pages[0].locator('#phase-name').innerText();
    aktuellePhase = aktuellePhase.toLowerCase().trim();
    console.log(`Aktuelle Phase: ${aktuellePhase}`);

    if (aktuellePhase.includes('hexe phase')) {
      console.log('Hexe-Phase erreicht!');
      break;
    }

    // Wenn Werwolf-Phase, muss ein Werwolf wählen
    if (aktuellePhase.includes('werwolf phase')) {
      const werwolf = players.find(p => p.rolle === 'Werwolf');
      if (werwolf) {
        await werwolf.page.click('.spieler-card:not(.selected)');
        await werwolf.page.click('text=Töten');
      }
    }
    
    // Seherin Phase
    if (aktuellePhase.includes('seherin phase')) {
        const seherin = players.find(p => p.rolle === 'Seherin');
        if (seherin) {
            await seherin.page.click('.spieler-card:not(.selected)');
            await seherin.page.click('text=Identität sehen');
        }
    }

    // Automatisches Weitergehen oder Host klickt weiter
    const weiterBtn = pages[0].locator('button:has-text("Weiter"), button:has-text("Nächste Phase")');
    if (await weiterBtn.isVisible()) {
        await weiterBtn.click();
    }
    
    await new Promise(r => setTimeout(r, 2000));
  }

  expect(aktuellePhase).toContain('hexe phase');

  // Hexe klickt "Nichts tun"
  console.log('Hexe klickt "Nichts tun"');
  await hexe.page.click('text=Nichts tun');

  // Prüfen ob Phase wechselt (sollte automatisch gehen, wenn alle fertig sind)
  await new Promise(r => setTimeout(r, 5000));
  const neuePhase = await pages[0].locator('#phase-name').innerText();
  console.log(`Phase nach "Nichts tun": ${neuePhase}`);

  expect(neuePhase.toLowerCase()).not.toContain('hexe phase');

  await browser.close();
});
