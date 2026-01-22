/**
 * VillageIntegration - Verbindet VillageEnhancementManager mit dem Rest der App
 * 
 * Diese Klasse:
 * - Hört auf Socket.io Events (phase_update, spieler_gestorben, etc.)
 * - Ruft die entsprechenden Methoden im VillageEnhancementManager auf
 * - Hört auf CustomEvents und aktualisiert die UI
 * 
 * KEINE HARDCODIERTEN TEXTE - Alles wird vom Backend geliefert!
 */

import { VillageEnhancementManager, PhaseDisplayInfo, EliminationEvent, GameEndEvent } from './VillageEnhancements.js';
import type { PlayerData, PCMaterial } from './types.js';

// Socket.io Typen
interface SocketIO {
  on(event: string, callback: (...args: unknown[]) => void): void;
  emit(event: string, data?: unknown): void;
}

// Village3D Interface (für Methodenaufrufe)
interface Village3DInterface {
  setTimeOfDay(isNight: boolean): void;
  showHint(playerId: number, type: string): void;
  highlightPlayer(playerId: number, color: string): void;
  showVoteIndicator(playerId: number, voterName: string): void;
  updatePlayerStatus(playerId: number, isAlive: boolean): void;
  clearAllHighlights?(): void;
}

// Hint-Event-Daten
interface HintData {
  spielerId?: number;
  spieler_id?: number;
  hintTyp?: string;
  type?: string;
  typ?: string;
}

// Backend-Event-Daten
interface PhaseChangedData {
  phase: string;
  runde?: number;
  display_info?: PhaseDisplayInfo;
  erzaehler_text?: string;
  is_night?: boolean;
  active_role?: string;
}

interface PlayerDiedData {
  spieler_id: number;
  spieler_name: string;
  todesart: string;
  display_text?: string;
}

interface VoteSubmittedData {
  waehler_id: number;
  waehler_name: string;
  ziel_id: number;
  ziel_name: string;
}

interface VoteResultData {
  hingerichtet_id?: number;
  hingerichtet_name?: string;
  display_text?: string;
  stimmen: Array<{ spieler_id: number; stimmen: number }>;
}

interface GameEndData {
  gewinner: string;
  display_title?: string;
  display_message?: string;
  spieler?: Array<{
    id: number;
    name: string;
    rolle: string;
    ist_gewinner: boolean;
    ist_am_leben: boolean;
  }>;
}

interface NightResultData {
  tote?: Array<{
    id: number;
    name: string;
    todesart: string;
    display_text?: string;
  }>;
}

/**
 * Integrationsklasse für VillageEnhancementManager
 */
export class VillageIntegration {
  private enhancementManager: VillageEnhancementManager;
  private socket: SocketIO;
  private village3d: Village3DInterface | null = null;
  
  // UI-Elemente (werden vom Template gesetzt)
  private phaseOverlayElement: HTMLElement | null = null;
  private eliminationTextElement: HTMLElement | null = null;

  constructor(
    materialCache: Map<string, PCMaterial>,
    app: unknown,
    socket: SocketIO,
    _raumCode: string
  ) {
    this.socket = socket;
    this.enhancementManager = new VillageEnhancementManager(materialCache, app);
    
    this.setupSocketListeners();
    this.setupCustomEventListeners();
    this.setupCallbacks();
  }

  /**
   * Setzt die Village3D-Instanz für direkte Methodenaufrufe
   */
  setVillage3D(village3d: Village3DInterface): void {
    this.village3d = village3d;
  }

  /**
   * Gibt den Enhancement Manager zurück
   */
  getEnhancementManager(): VillageEnhancementManager {
    return this.enhancementManager;
  }

  /**
   * Initialisiert Spielerhäuser
   */
  initializePlayerHouses(players: PlayerData[]): void {
    this.enhancementManager.createPlayerHouses(players);
  }

  /**
   * Setzt die UI-Elemente für Overlays
   */
  setUIElements(phaseOverlay: HTMLElement | null, eliminationText: HTMLElement | null): void {
    this.phaseOverlayElement = phaseOverlay;
    this.eliminationTextElement = eliminationText;
  }

  // ============================================================================
  // SOCKET LISTENERS
  // ============================================================================

  private setupSocketListeners(): void {
    // Unified Phase Update - single source of truth
    this.socket.on('phase_update', async (data: unknown) => {
      const phaseData = data as PhaseChangedData;
      await this.handlePhaseChanged(phaseData);
    });

    // Spieler gestorben
    this.socket.on('spieler_gestorben', (data: unknown) => {
      const deathData = data as PlayerDiedData;
      this.handlePlayerDied(deathData);
    });

    // Stimme abgegeben
    this.socket.on('stimme_abgegeben', (data: unknown) => {
      const voteData = data as VoteSubmittedData;
      this.handleVoteSubmitted(voteData);
    });

    // Hinweis anzeigen (für Seherin, Werwölfe, etc.)
    this.socket.on('hinweis_zeigen', (data: unknown) => {
      const hintData = data as HintData;
      this.handleHint(hintData);
    });

    // Abstimmungsergebnis
    this.socket.on('abstimmung_ergebnis', (data: unknown) => {
      const resultData = data as VoteResultData;
      this.handleVoteResult(resultData);
    });

    // Spielende
    this.socket.on('spiel_ende', (data: unknown) => {
      const endData = data as GameEndData;
      this.handleGameEnd(endData);
    });

    // Nachtergebnis
    this.socket.on('nacht_ergebnis', (data: unknown) => {
      const nightData = data as NightResultData;
      this.handleNightResult(nightData);
    });
  }

  // ============================================================================
  // CUSTOM EVENT LISTENERS (für UI-Updates)
  // ============================================================================

  private setupCustomEventListeners(): void {
    // Phasen-Overlay anzeigen
    window.addEventListener('village3d:phaseOverlay', ((event: CustomEvent) => {
      this.showPhaseOverlay(event.detail);
    }) as EventListener);

    // Eliminierungstext anzeigen
    window.addEventListener('village3d:eliminationText', ((event: CustomEvent) => {
      this.showEliminationText(event.detail.text);
    }) as EventListener);
  }

  // ============================================================================
  // CALLBACKS
  // ============================================================================

  private setupCallbacks(): void {
    // Kamera-Fokus über Event-Listener statt Callback
    window.addEventListener('village3d:cameraFocus', ((event: CustomEvent) => {
      // Event wird bereits von VillageEnhancementManager dispatched
      console.log('[VillageIntegration] Camera focus requested:', event.detail);
    }) as EventListener);
  }

  // ============================================================================
  // EVENT HANDLER
  // ============================================================================

  private async handlePhaseChanged(data: PhaseChangedData): Promise<void> {
    const phaseName = data.phase;

    // Phase-Info holen (vom Backend geliefert oder API)
    let phaseInfo: PhaseDisplayInfo | undefined = data.display_info;
    
    if (!phaseInfo) {
      // Fallback: Von API laden
      const fetched = await this.fetchPhaseDisplayInfo(phaseName);
      if (fetched) {
        phaseInfo = fetched;
      }
    }

    // Bestimme ob Nacht oder Tag
    const isNight = data.is_night ?? (
                    phaseName.includes('nacht') ||
                    (phaseName.includes('phase') && 
                     !phaseName.includes('tag') && 
                     !phaseName.includes('abstimmung')));

    if (isNight) {
      // Bei Nacht: Alle Spieler schlafen (IDs werden vom Backend geliefert)
      // Für jetzt: Alle lebenden Spieler
      const sleepingPlayers = this.getAllLivingPlayerIds();
      this.enhancementManager.transitionToNight(sleepingPlayers, phaseInfo);
    } else {
      this.enhancementManager.transitionToDay(phaseInfo);
    }

    // Village3D Tag/Nacht-Modus setzen
    if (this.village3d) {
      this.village3d.setTimeOfDay(isNight);
    }

    // Aktive Rolle markieren
    if (data.active_role) {
      // Spieler mit dieser Rolle als aktiv markieren
      this.setActiveRole(data.active_role);
    }
  }

  private handlePlayerDied(data: PlayerDiedData): void {
    // Eliminierungs-Event erstellen
    const event: EliminationEvent = {
      player_id: data.spieler_id,
      player_name: data.spieler_name,
      reason: data.todesart,
      display_text: data.display_text || `${data.spieler_name} ist gestorben.`
    };

    // Animation abspielen
    this.enhancementManager.playEliminationAnimation(event);
    
    // Village3D Spielerstatus aktualisieren
    if (this.village3d) {
      this.village3d.updatePlayerStatus(data.spieler_id, false);
    }
    
    // HUD-Liste aktualisieren
    (window as unknown as { updateVillage3DPlayerList?: () => void }).updateVillage3DPlayerList?.();
  }

  private handleVoteSubmitted(data: VoteSubmittedData): void {
    // Abstimmungsmarker anzeigen (in PlayerHouseBuilder)
    this.enhancementManager.showVoteMarker(data.waehler_id, data.ziel_id);
    
    // Village3D Highlight und Vote-Indikator
    if (this.village3d) {
      this.village3d.highlightPlayer(data.ziel_id, 'red');
      this.village3d.showVoteIndicator(data.ziel_id, data.waehler_name);
    }
  }

  private handleHint(data: HintData): void {
    const playerId = data.spielerId || data.spieler_id;
    const hintType = data.hintTyp || data.type || data.typ;
    
    if (playerId && hintType && this.village3d) {
      this.village3d.showHint(playerId, hintType);
    }
  }

  private async handleVoteResult(data: VoteResultData): Promise<void> {
    // Alle Marker entfernen
    this.enhancementManager.clearAllVoteMarkers();

    // Wenn jemand hingerichtet wurde
    if (data.hingerichtet_id) {
      const event: EliminationEvent = {
        player_id: data.hingerichtet_id,
        player_name: data.hingerichtet_name || '',
        reason: 'vote',
        display_text: data.display_text || `${data.hingerichtet_name} wurde hingerichtet.`
      };

      await this.enhancementManager.playEliminationAnimation(event);
    }
  }

  private handleGameEnd(data: GameEndData): void {
    // Spielende-Event erstellen
    const event: GameEndEvent = {
      winner_team: data.gewinner,
      display_title: data.display_title || 'Spiel beendet',
      display_message: data.display_message || `${data.gewinner} haben gewonnen!`,
      player_results: (data.spieler || []).map(s => ({
        player_id: s.id,
        player_name: s.name,
        role: s.rolle,
        is_winner: s.ist_gewinner,
        is_alive: s.ist_am_leben
      }))
    };

    // Event dispatchen für UI
    window.dispatchEvent(new CustomEvent('village3d:gameEnd', {
      detail: event
    }));
  }

  private async handleNightResult(data: NightResultData): Promise<void> {
    if (!data.tote || data.tote.length === 0) return;

    // Für jeden Toten eine Animation abspielen
    for (const death of data.tote) {
      const event: EliminationEvent = {
        player_id: death.id,
        player_name: death.name,
        reason: death.todesart,
        display_text: death.display_text || `${death.name} wurde getötet.`
      };

      await this.enhancementManager.playEliminationAnimation(event);
      
      // Kurze Pause zwischen Animationen
      await this.delay(1000);
    }
  }

  // ============================================================================
  // UI METHODEN
  // ============================================================================

  private showPhaseOverlay(detail: {
    text: string;
    description?: string;
    icon?: string;
    color?: string;
    phase: string;
  }): void {
    if (!this.phaseOverlayElement) return;

    // HTML erstellen
    const iconHtml = detail.icon ? `<i class="${detail.icon}"></i> ` : '';
    const descHtml = detail.description ? `<p class="phase-description">${detail.description}</p>` : '';
    
    this.phaseOverlayElement.innerHTML = `
      <div class="phase-overlay-content" style="--phase-color: ${detail.color || '#d4a574'}">
        <h2 class="phase-title">${iconHtml}${detail.text}</h2>
        ${descHtml}
      </div>
    `;

    // Anzeigen
    this.phaseOverlayElement.classList.add('is-visible');

    // Nach Timeout ausblenden
    setTimeout(() => {
      this.phaseOverlayElement?.classList.remove('is-visible');
    }, 3000);
  }

  private showEliminationText(text: string): void {
    if (!this.eliminationTextElement) return;

    this.eliminationTextElement.textContent = text;
    this.eliminationTextElement.classList.add('is-visible');

    setTimeout(() => {
      this.eliminationTextElement?.classList.remove('is-visible');
    }, 4000);
  }

  // ============================================================================
  // HILFSMETHODEN
  // ============================================================================

  private async fetchPhaseDisplayInfo(phaseName: string): Promise<PhaseDisplayInfo | null> {
    try {
      const response = await fetch(`/api/phase/${encodeURIComponent(phaseName)}/info`);
      const data = await response.json();
      if (data.success && data.info) {
        return data.info as PhaseDisplayInfo;
      }
    } catch (error) {
      console.warn('[VillageIntegration] Failed to fetch phase info:', error);
    }
    return null;
  }

  private getAllLivingPlayerIds(): number[] {
    // Von window.alleSpieler holen (vom Template gesetzt)
    const alleSpieler = (window as unknown as { alleSpieler?: Array<{ id: number; istAmLeben?: boolean }> }).alleSpieler;
    if (!alleSpieler) return [];
    
    return alleSpieler
      .filter(s => s.istAmLeben !== false)
      .map(s => s.id);
  }

  private setActiveRole(roleName: string): void {
    // Von window.alleSpieler die Spieler mit dieser Rolle finden und aktivieren
    const alleSpieler = (window as unknown as { alleSpieler?: Array<{ id: number; rolle?: string; istAmLeben?: boolean }> }).alleSpieler;
    if (!alleSpieler) return;

    // Alle deaktivieren, dann die richtigen aktivieren
    alleSpieler.forEach(s => {
      this.enhancementManager.setPlayerActive(s.id, false);
    });

    alleSpieler
      .filter(s => s.rolle === roleName && s.istAmLeben !== false)
      .forEach(s => {
        this.enhancementManager.setPlayerActive(s.id, true);
      });
  }

  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // ============================================================================
  // UPDATE LOOP
  // ============================================================================

  update(dt: number): void {
    this.enhancementManager.update(dt);
  }

  // ============================================================================
  // CLEANUP
  // ============================================================================

  destroy(): void {
    this.enhancementManager.destroy();
  }
}

// Export für globale Nutzung
export default VillageIntegration;
