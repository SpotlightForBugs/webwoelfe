/**
 * Webwölfe - Hinweis-System
 * Verwaltet visuelle Hinweise für den Online-Modus
 *
 * WICHTIG: Im Remote-Play können Spieler KEINE Audio von anderen Geräten hören!
 * Daher werden Hinweise als SYNCHRONISIERTE VISUELLE EVENTS an ALLE gesendet.
 */

class HintSystem {
  constructor() {
    this.hinweisHistory = [];
    this.usesRemaining = {};
    this.village3d = null;
    this.modus = 'online';
    this.audioErlaubt = false;

    // CSS-Klassen für visuelle Hinweise (2D Fallback)
    this.visualHints = {
      augen_flackern: 'hint-eyes-flicker',
      schatten: 'hint-shadow',
      mond_schein: 'hint-moonlight',
      nervoes: 'hint-nervous',
      blick_abwenden: 'hint-look-away',
      gluehen: 'hint-glow',
      selbst_verdaechtigung: 'hint-sus-self',
      stolpern: 'hint-stumble',
      herzschlag: 'hint-heartbeat',
    };

    // 3D-Effekt-Mapping für Village3D
    this.effekt3D = {
      augen_flackern: 'eyes_glow_red',
      schatten: 'shadow_pass',
      mond_schein: 'moonbeam',
      nervoes: 'character_shake',
      blick_abwenden: 'look_away',
      gluehen: 'aura_glow',
      selbst_verdaechtigung: 'suspicious_behavior',
      stolpern: 'character_stumble',
      herzschlag: 'heartbeat_pulse',
    };

    // Nachricht-Vorlagen für synchronisierte Hinweise (ALLE sehen diese!)
    this.hinweisNachrichten = {
      augen_flackern: 'Die Augen von {spieler} flackern kurz seltsam...',
      schatten: 'Ein Schatten huscht über {spieler}...',
      mond_schein: 'Mondlicht fällt auf {spieler}...',
      nervoes: '{spieler} wirkt nervös...',
      blick_abwenden: '{spieler} wendet den Blick ab...',
      gluehen: 'Ein mystisches Glühen umgibt {spieler}...',
      selbst_verdaechtigung: '{spieler} verhält sich verdächtig!',
      stolpern: '{spieler} stolpert kurz...',
      herzschlag: 'Das Herz von {spieler} schlägt schneller...',
    };

    this.init();
  }

  /** Initialisiert das Hinweis-System */
  init() {
    const modusElement = document.querySelector('[data-spiel-modus]');
    if (modusElement) {
      const modus = modusElement.dataset.spielModus;
      if (modus) {
        this.modus = modus;
        this.audioErlaubt = modus === 'gruppe';
      }
    }

    if (window.village3d) {
      this.village3d = window.village3d;
    }
  }

  /** Setzt den Spiel-Modus */
  setModus(modus) {
    this.modus = modus;
    this.audioErlaubt = modus === 'gruppe';
    console.log(`Hinweis-System: Modus=${modus}, Audio=${this.audioErlaubt ? 'an' : 'aus'}`);
  }

  /** Verbindet mit der 3D-Visualisierung */
  setVillage3D(village3d) {
    this.village3d = village3d;
  }

  /** Zeigt einen visuellen Hinweis auf einem Spieler-Element */
  showVisualHint(spielerId, hintTyp) {
    const element = document.getElementById(`spieler-${spielerId}`);
    if (!element) return;

    const cssClass = this.visualHints[hintTyp];
    if (!cssClass) return;

    element.classList.add(cssClass);

    const dauer = this.getHintDuration(hintTyp);
    setTimeout(() => {
      element.classList.remove(cssClass);
    }, dauer);

    this.hinweisHistory.push({
      spielerId,
      hintTyp,
      zeitpunkt: new Date(),
    });
  }

  /** Gibt die Dauer eines Hinweises in ms zurück */
  getHintDuration(hintTyp) {
    const durations = {
      augen_flackern: 150,
      schatten: 300,
      mond_schein: 500,
      nervoes: 800,
      blick_abwenden: 400,
      herzschlag: 1500,
      gluehen: 600,
      selbst_verdaechtigung: 1000,
      stolpern: 500,
    };
    return durations[hintTyp] || 500;
  }

  /**
   * Zeigt einen synchronisierten Hinweis (für ALLE Spieler sichtbar!)
   * Im Online-Modus: Nur visuell + Nachricht
   */
  showHint(spielerId, spielerName, hintTyp) {
    if (this.village3d && this.effekt3D[hintTyp]) {
      this.village3d.showHint(spielerId, this.effekt3D[hintTyp]);
    }

    if (this.visualHints[hintTyp]) {
      this.showVisualHint(spielerId, hintTyp);
    }

    if (this.modus === 'online' && this.hinweisNachrichten[hintTyp]) {
      const nachricht = this.hinweisNachrichten[hintTyp].replace('{spieler}', spielerName);
      this.showHintMessage(nachricht, hintTyp);
    }

    this.hinweisHistory.push({
      spielerId,
      spielerName,
      hintTyp,
      zeitpunkt: new Date(),
      modus: this.modus,
    });
  }

  /** Zeigt eine Hinweis-Nachricht an (für alle Spieler synchronisiert) */
  showHintMessage(nachricht, hintTyp) {
    let messageContainer = document.getElementById('hint-messages');

    if (!messageContainer) {
      messageContainer = document.createElement('div');
      messageContainer.id = 'hint-messages';
      messageContainer.className = 'hint-messages-container';
      document.body.appendChild(messageContainer);
    }

    const msgElement = document.createElement('div');
    msgElement.className = `hint-message hint-message-${hintTyp}`;
    msgElement.innerHTML = `
      <i class="fa-solid fa-eye"></i>
      <span>${nachricht}</span>
    `;

    messageContainer.appendChild(msgElement);
    setTimeout(() => msgElement.classList.add('show'), 10);

    setTimeout(() => {
      msgElement.classList.remove('show');
      setTimeout(() => msgElement.remove(), 500);
    }, 4000);
  }

  /**
   * Ermöglicht einem Spieler sich selbst verdächtig zu machen
   * (für Selbstmörder, Gerber, Dorfdepp, Engel)
   */
  initSelfSuspicionButton(spielerId, spielerName, rolle, socket) {
    const kannVerdaechtigen = ['Selbstmörder', 'Gerber', 'Dorfdepp', 'Engel'];
    if (!kannVerdaechtigen.includes(rolle)) return;

    const maxUses = { Selbstmörder: 3, Gerber: 2, Dorfdepp: 2, Engel: 2 };
    this.usesRemaining[spielerId] = maxUses[rolle] || 2;

    const buttonContainer =
      document.getElementById(`spieler-${spielerId}-actions`) ||
      document.getElementById('eigene-aktionen');
    if (!buttonContainer) return;

    const btn = document.createElement('button');
    btn.className = 'btn-verdaechtig btn btn-outline-warning';
    btn.id = `btn-verdaechtig-${spielerId}`;
    btn.innerHTML = `
      <i class="fa-solid fa-face-grimace"></i>
      Verdächtig wirken
      <span class="badge bg-secondary ms-2">${this.usesRemaining[spielerId]}</span>
    `;
    btn.title = 'Sende einen subtilen Hinweis an alle Spieler, um verdächtig zu wirken!';

    btn.addEventListener('click', () => {
      this.triggerSelfSuspicion(spielerId, spielerName, socket);
    });

    buttonContainer.appendChild(btn);
  }

  /**
   * Löst einen Selbst-Verdächtigungs-Hinweis aus.
   * Sendet den Hinweis an den SERVER, der ihn an ALLE synchronisiert!
   */
  triggerSelfSuspicion(spielerId, spielerName, socket) {
    if (!this.usesRemaining[spielerId] || this.usesRemaining[spielerId] <= 0) {
      return;
    }

    this.usesRemaining[spielerId]--;

    const btn = document.getElementById(`btn-verdaechtig-${spielerId}`);
    if (btn) {
      const usesSpan = btn.querySelector('.uses-left');
      if (usesSpan) {
        usesSpan.textContent = String(this.usesRemaining[spielerId]);
      }
      if (this.usesRemaining[spielerId] <= 0) {
        btn.disabled = true;
        btn.title = 'Keine Verdächtigungen mehr übrig';
      }
    }

    const hinweise = ['selbst_verdaechtigung', 'nervoes', 'stolpern', 'blick_abwenden'];
    const zufallsHinweis = hinweise[Math.floor(Math.random() * hinweise.length)];

    // WICHTIG: Sende an SERVER, nicht lokal anzeigen!
    socket.emit('hinweis_senden', {
      spielerId,
      spielerName,
      hintTyp: zufallsHinweis,
      selbst_ausgeloest: true,
    });
  }

  /**
   * Verarbeitet eingehende SYNCHRONISIERTE Hinweise vom Server.
   * Im Online-Modus werden Hinweise ZENTRAL auf dem Server berechnet
   * und an ALLE Spieler gleichzeitig gesendet!
   */
  handleServerHint(data) {
    const { spielerId, spielerName, hintTyp } = data;
    console.log(`Synchronisierter Hinweis: ${spielerName} - ${hintTyp}`);
    this.showHint(spielerId, spielerName, hintTyp);
  }

  /** Sendet einen Hinweis-Request an den Server */
  sendHintRequest(socket, spielerId, hintTyp) {
    if (!socket) {
      console.warn('Kein Socket für Hinweis-Request');
      return;
    }
    socket.emit('hinweis_senden', { spielerId, hintTyp });
  }

  /** Gibt die Hinweis-Historie zurück (für Debug/Stats) */
  getHistory() {
    return this.hinweisHistory;
  }

  /** Leert die Hinweis-Historie (z.B. bei neuem Spiel) */
  clearHistory() {
    this.hinweisHistory = [];
  }
}

// Globale Variable + auto-init
export default HintSystem;

if (typeof window !== 'undefined') {
  window.HintSystem = HintSystem;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      window.hintSystem = new HintSystem();
    });
  } else {
    window.hintSystem = new HintSystem();
  }
}
