/**
 * Webwölfe - Hinweis-System TypeScript
 * Verwaltet visuelle Hinweise für den Online-Modus
 * 
 * WICHTIG: Im Remote-Play können Spieler KEINE Audio von anderen Geräten hören!
 * Daher werden Hinweise als SYNCHRONISIERTE VISUELLE EVENTS an ALLE gesendet.
 */

// SocketIO client interface (matches runtime socket.io-client loaded via CDN)
interface SocketIOSocket {
  emit(event: 'hinweis_senden', data: {
    spielerId: string;
    spielerName?: string;
    hintTyp: string;
    selbst_ausgeloest?: boolean;
  }): void;
  on(event: string, callback: (data: ServerHintData) => void): void;
  off(event: string, callback?: (data: ServerHintData) => void): void;
}

interface HintHistoryEntry {
  spielerId: string;
  spielerName?: string;
  hintTyp: string;
  zeitpunkt: Date;
  modus?: string;
}

interface ServerHintData {
  spielerId: string;
  spielerName: string;
  hintTyp: string;
  timestamp: number;
  selbst_ausgeloest?: boolean;
}

interface Village3DInterface {
  showHint(spielerId: string, effectType: string): void;
}

type SpielModus = 'gruppe' | 'online';

type HintType =
  | 'augen_flackern'
  | 'schatten'
  | 'mond_schein'
  | 'nervoes'
  | 'blick_abwenden'
  | 'gluehen'
  | 'selbst_verdaechtigung'
  | 'stolpern'
  | 'herzschlag';

type SelfSuspicionRole = 'Selbstmörder' | 'Gerber' | 'Dorfdepp' | 'Engel';

class HintSystem {
  private hinweisHistory: HintHistoryEntry[] = [];
  private usesRemaining: Record<string, number> = {};
  private village3d: Village3DInterface | null = null;
  private modus: SpielModus = 'online';
  private audioErlaubt = false;

  // CSS-Klassen für visuelle Hinweise (2D Fallback)
  private readonly visualHints: Record<HintType, string> = {
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
  private readonly effekt3D: Record<HintType, string> = {
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
  private readonly hinweisNachrichten: Record<HintType, string> = {
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

  constructor() {
    this.init();
  }

  /**
   * Initialisiert das Hinweis-System
   */
  private init(): void {
    // Modus aus Seiten-Daten lesen
    const modusElement = document.querySelector<HTMLElement>('[data-spiel-modus]');
    if (modusElement) {
      const modus = modusElement.dataset.spielModus as SpielModus | undefined;
      if (modus) {
        this.modus = modus;
        this.audioErlaubt = modus === 'gruppe';
      }
    }

    // 3D-Visualisierung finden
    const windowWithVillage = window as typeof window & { village3d?: Village3DInterface };
    if (windowWithVillage.village3d) {
      this.village3d = windowWithVillage.village3d;
    }
  }

  /**
   * Setzt den Spiel-Modus
   */
  setModus(modus: SpielModus): void {
    this.modus = modus;
    this.audioErlaubt = modus === 'gruppe';
    console.log(`Hinweis-System: Modus=${modus}, Audio=${this.audioErlaubt ? 'an' : 'aus'}`);
  }

  /**
   * Verbindet mit der 3D-Visualisierung
   */
  setVillage3D(village3d: Village3DInterface): void {
    this.village3d = village3d;
  }

  /**
   * Zeigt einen visuellen Hinweis auf einem Spieler-Element
   */
  showVisualHint(spielerId: string, hintTyp: HintType): void {
    const element = document.getElementById(`spieler-${spielerId}`);
    if (!element) return;

    const cssClass = this.visualHints[hintTyp];
    if (!cssClass) return;

    // Füge CSS-Klasse hinzu
    element.classList.add(cssClass);

    // Entferne nach Animation
    const dauer = this.getHintDuration(hintTyp);
    setTimeout(() => {
      element.classList.remove(cssClass);
    }, dauer);

    // Protokolliere Hinweis
    this.hinweisHistory.push({
      spielerId,
      hintTyp,
      zeitpunkt: new Date(),
    });
  }

  /**
   * Gibt die Dauer eines Hinweises in ms zurück
   */
  private getHintDuration(hintTyp: HintType): number {
    const durations: Record<HintType, number> = {
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
  showHint(spielerId: string, spielerName: string, hintTyp: HintType): void {
    // 1. 3D-Effekt wenn verfügbar
    if (this.village3d && this.effekt3D[hintTyp]) {
      this.village3d.showHint(spielerId, this.effekt3D[hintTyp]);
    }

    // 2. 2D CSS-Effekt als Fallback
    if (this.visualHints[hintTyp]) {
      this.showVisualHint(spielerId, hintTyp);
    }

    // 3. Synchronisierte Nachricht für ALLE Spieler
    if (this.modus === 'online' && this.hinweisNachrichten[hintTyp]) {
      const nachricht = this.hinweisNachrichten[hintTyp].replace('{spieler}', spielerName);
      this.showHintMessage(nachricht, hintTyp);
    }

    // Protokolliere Hinweis
    this.hinweisHistory.push({
      spielerId,
      spielerName,
      hintTyp,
      zeitpunkt: new Date(),
      modus: this.modus,
    });
  }

  /**
   * Zeigt eine Hinweis-Nachricht an (für alle Spieler synchronisiert)
   */
  private showHintMessage(nachricht: string, hintTyp: HintType): void {
    let messageContainer = document.getElementById('hint-messages');

    if (!messageContainer) {
      messageContainer = document.createElement('div');
      messageContainer.id = 'hint-messages';
      messageContainer.className = 'hint-messages-container';
      document.body.appendChild(messageContainer);
    }

    // Erstelle Nachricht-Element
    const msgElement = document.createElement('div');
    msgElement.className = `hint-message hint-message-${hintTyp}`;
    msgElement.innerHTML = `
            <i class="fa-solid fa-eye"></i>
            <span>${nachricht}</span>
        `;

    messageContainer.appendChild(msgElement);

    // Animation rein
    setTimeout(() => msgElement.classList.add('show'), 10);

    // Nach 4 Sekunden ausblenden
    setTimeout(() => {
      msgElement.classList.remove('show');
      setTimeout(() => msgElement.remove(), 500);
    }, 4000);
  }

  /**
   * Ermöglicht einem Spieler sich selbst verdächtig zu machen
   * (für Selbstmörder, Gerber, Dorfdepp, Engel)
   */
  initSelfSuspicionButton(
    spielerId: string,
    spielerName: string,
    rolle: string,
    socket: SocketIOSocket
  ): void {
    // Prüfe ob Rolle selbst-verdächtigend sein kann
    const kannVerdaechtigen: SelfSuspicionRole[] = [
      'Selbstmörder',
      'Gerber',
      'Dorfdepp',
      'Engel',
    ];
    if (!kannVerdaechtigen.includes(rolle as SelfSuspicionRole)) return;

    // Setze verfügbare Nutzungen
    const maxUses: Record<SelfSuspicionRole, number> = {
      Selbstmörder: 3,
      Gerber: 2,
      Dorfdepp: 2,
      Engel: 2,
    };
    this.usesRemaining[spielerId] = maxUses[rolle as SelfSuspicionRole] || 2;

    // Erstelle Button
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
   * Löst einen Selbst-Verdächtigungs-Hinweis aus
   * Sendet den Hinweis an den SERVER, der ihn an ALLE synchronisiert!
   */
  private triggerSelfSuspicion(spielerId: string, spielerName: string, socket: SocketIOSocket): void {
    if (!this.usesRemaining[spielerId] || this.usesRemaining[spielerId] <= 0) {
      return;
    }

    // Reduziere verfügbare Nutzungen
    this.usesRemaining[spielerId]--;

    // Update Button
    const btn = document.getElementById(`btn-verdaechtig-${spielerId}`);
    if (btn) {
      const usesSpan = btn.querySelector('.uses-left');
      if (usesSpan) {
        usesSpan.textContent = String(this.usesRemaining[spielerId]);
      }

      if (this.usesRemaining[spielerId] <= 0) {
        (btn as HTMLButtonElement).disabled = true;
        btn.title = 'Keine Verdächtigungen mehr übrig';
      }
    }

    // Wähle zufälligen verdächtigen Hinweis
    const hinweise: HintType[] = [
      'selbst_verdaechtigung',
      'nervoes',
      'stolpern',
      'blick_abwenden',
    ];
    const zufallsHinweis = hinweise[Math.floor(Math.random() * hinweise.length)];

    // WICHTIG: Sende an SERVER, nicht lokal anzeigen!
    // Der Server broadcastet dann an ALLE Spieler synchronisiert
    socket.emit('hinweis_senden', {
      spielerId,
      spielerName,
      hintTyp: zufallsHinweis,
      selbst_ausgeloest: true, // Markiert, dass Spieler selbst auslöste
    });

    // NICHT lokal anzeigen - warten auf Server-Broadcast!
    // Der Server sendet den Hinweis dann an ALLE (inkl. uns selbst)
  }

  /**
   * Verarbeitet eingehende SYNCHRONISIERTE Hinweise vom Server
   * Im Online-Modus werden Hinweise ZENTRAL auf dem Server berechnet
   * und an ALLE Spieler gleichzeitig gesendet!
   */
  handleServerHint(data: ServerHintData): void {
    const { spielerId, spielerName, hintTyp } = data;

    // WICHTIG: Im Online-Modus wird NICHT mehr lokal gewürfelt!
    // Der Server hat bereits entschieden, dass dieser Hinweis gezeigt wird.
    // Alle Spieler sehen DENSELBEN Hinweis zur SELBEN Zeit.

    console.log(`Synchronisierter Hinweis: ${spielerName} - ${hintTyp}`);

    // Zeige Hinweis sofort (keine lokale Chance mehr!)
    this.showHint(spielerId, spielerName, hintTyp as HintType);
  }

  /**
   * Sendet einen Hinweis-Request an den Server
   * (für Rollen wie Selbstmörder, die sich selbst verdächtig machen können)
   */
  sendHintRequest(socket: SocketIOSocket, spielerId: string, hintTyp: HintType): void {
    if (!socket) {
      console.warn('Kein Socket für Hinweis-Request');
      return;
    }

    socket.emit('hinweis_senden', {
      spielerId,
      hintTyp,
    });
  }

  /**
   * HINWEIS-GENERIERUNG ERFOLGT NUR AUF DEM SERVER!
   * 
   * Im Online-Modus werden Hinweise zentral auf dem Server berechnet
   * und synchronisiert an ALLE Spieler gesendet. Dies stellt sicher, dass:
   * 
   * 1. Alle Spieler denselben Hinweis sehen
   * 2. Der Hinweis zur selben Zeit erscheint
   * 3. Keine Manipulation durch Client möglich ist
   * 
   * Server-Logik (Python):
   * - Pro Nachtphase werden Hinweise basierend auf Rollen-Teams gewürfelt
   * - Werwölfe: 15% Chance, verdächtige Hinweise
   * - Dorfbewohner: 5% Chance (False Positives)
   * - Der Server broadcastet dann an ALLE via SocketIO
   */

  /**
   * Gibt die Hinweis-Historie zurück (für Debug/Stats)
   */
  getHistory(): HintHistoryEntry[] {
    return this.hinweisHistory;
  }

  /**
   * Leert die Hinweis-Historie (z.B. bei neuem Spiel)
   */
  clearHistory(): void {
    this.hinweisHistory = [];
  }
}

// Exportiere für globale Nutzung und als ES6 module
export default HintSystem;

// Auch als globale Variable verfügbar machen
declare global {
  interface Window {
    HintSystem: typeof HintSystem;
    hintSystem: HintSystem;
  }
}

if (typeof window !== 'undefined') {
  window.HintSystem = HintSystem;

  // Instanziere wenn DOM bereit
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      window.hintSystem = new HintSystem();
    });
  } else {
    window.hintSystem = new HintSystem();
  }
}
