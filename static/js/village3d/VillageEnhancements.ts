/**
 * Village3DEnhancements - Erweiterte 3D-Dorf-Funktionen
 * 
 * Dieses Modul erweitert das bestehende Village3D mit:
 * - Spieler-Häuser-Zuordnung (dynamisch vom Backend)
 * - Charaktere die zwischen Dorfplatz und Haus wandern
 * - Verbesserte Tag/Nacht-Übergänge (Phaseninformationen vom Backend)
 * - Phasenabhängige visuelle Effekte (dynamisch konfiguriert)
 * 
 * KEINE HARDCODIERTEN TEXTE - Alles kommt vom Backend via API!
 */

import type { PCEntity, PCMaterial, PCModel, PlayerData, PlayerEntity } from './types.js';
import { PlayerHouseBuilder, PlayerHouseEntity } from './PlayerHouseBuilder.js';

// ============================================================================
// DYNAMISCHE API-TYPEN (vom Backend geliefert)
// ============================================================================

/**
 * Phase-Display-Informationen (vom Backend via /api/phase/<name>/info)
 */
export interface PhaseDisplayInfo {
  name: string;
  display_name: string;
  icon: string;
  color: string;
  description: string;
}

/**
 * Eliminierungs-Event (vom Backend via Socket)
 */
export interface EliminationEvent {
  player_id: number;
  player_name: string;
  reason: string;           // z.B. "vote", "werewolf", "witch", "hunter"
  display_text: string;     // Vollständiger Text vom Backend
  animation_type?: string;  // Optional: spezielle Animation
}

/**
 * Spielende-Event (vom Backend)
 */
export interface GameEndEvent {
  winner_team: string;
  display_title: string;
  display_message: string;
  player_results: Array<{
    player_id: number;
    player_name: string;
    role: string;
    is_winner: boolean;
    is_alive: boolean;
  }>;
}

/**
 * Haus-Konfiguration (kann vom Backend pro Spieler/Rolle kommen)
 */
export interface HouseConfig {
  style?: string;
  roof_style?: string;
  color_scheme?: {
    walls: string;
    roof: string;
    trim: string;
  };
}

// ============================================================================
// SPIELER-CHARAKTER-BEWEGUNG
// ============================================================================

export interface CharacterMovementState {
  playerId: number;
  currentPosition: { x: number; y: number; z: number };
  targetPosition: { x: number; y: number; z: number };
  isMoving: boolean;
  moveProgress: number;
  moveSpeed: number;
  isAtHome: boolean;
  walkCyclePhase: number;
}

// ============================================================================
// PHASEN-ÜBERGANGS-EFFEKTE
// ============================================================================

export interface PhaseTransition {
  fromPhase: string;
  toPhase: string;
  duration: number;
  effects: PhaseEffect[];
}

export interface PhaseEffect {
  type: 'fog_in' | 'fog_out' | 'light_change' | 'camera_pan' | 'overlay_text' | 'sound';
  startTime: number;
  duration: number;
  params: Record<string, unknown>;
}

// ============================================================================
// ABSTIMMUNGS-UI IM 3D-RAUM
// ============================================================================

export interface VotingMarker3D {
  playerId: number;
  targetHouse: PlayerHouseEntity;
  markerEntity: PCEntity;
  voterId: number;
}

// ============================================================================
// VILLAGE ENHANCEMENT MANAGER
// ============================================================================

export class VillageEnhancementManager {
  private playerHouses: Map<number, PlayerHouseEntity> = new Map();
  private playerCharacters: Map<number, PlayerEntity> = new Map();
  private characterMovement: Map<number, CharacterMovementState> = new Map();
  private votingMarkers: Map<number, VotingMarker3D[]> = new Map();
  
  private houseBuilder: PlayerHouseBuilder;
  private app: unknown; // PlayCanvas Application
  
  private currentPhase: string = 'day';
  private phaseTransitionTime: number = 0;
  private isTransitioning: boolean = false;
  
  // Kamera-Animation
  private targetCameraState = {
    angle: 0,
    height: 15,
    radius: 25,
    lookAtY: 0
  };

  constructor(materialCache: Map<string, PCMaterial>, app: unknown) {
    this.app = app;
    this.houseBuilder = new PlayerHouseBuilder(materialCache);
  }

  // ============================================================================
  // SPIELER-HÄUSER ERSTELLEN
  // ============================================================================

  /**
   * Erstellt Häuser für alle Spieler im Kreis um den Dorfplatz
   */
  createPlayerHouses(players: PlayerData[]): void {
    // Bestehende Häuser entfernen
    this.playerHouses.forEach(house => house.destroy());
    this.playerHouses.clear();

    const count = players.length;
    const innerRadius = 12;
    const outerRadius = 18;
    const angleStep = (Math.PI * 2) / count;

    players.forEach((player, index) => {
      // Abwechselnd innerer und äußerer Ring
      const radius = index % 2 === 0 ? innerRadius : outerRadius;
      const angle = index * angleStep + Math.PI / 2;
      
      const x = Math.cos(angle) * radius;
      const z = Math.sin(angle) * radius;
      
      // Haus zum Zentrum ausrichten
      const rotation = (-angle * 180 / Math.PI) + 90;

      const house = this.houseBuilder.createPlayerHouse(player, x, z, rotation);
      
      if (this.app && (this.app as any).root) {
        (this.app as any).root.addChild(house);
      }
      
      this.playerHouses.set(player.id, house);

      // Bewegungszustand initialisieren
      this.characterMovement.set(player.id, {
        playerId: player.id,
        currentPosition: { x: 0, y: 0, z: 0 }, // Startet im Zentrum
        targetPosition: { x: 0, y: 0, z: 0 },
        isMoving: false,
        moveProgress: 0,
        moveSpeed: 3,
        isAtHome: false,
        walkCyclePhase: 0
      });
    });
  }

  /**
   * Gibt die Hausposition für einen Spieler zurück
   */
  getHousePosition(playerId: number): { x: number; z: number } | null {
    const house = this.playerHouses.get(playerId);
    if (!house) return null;
    const pos = house.getPosition();
    return { x: pos.x, z: pos.z };
  }

  // ============================================================================
  // CHARAKTER-BEWEGUNG
  // ============================================================================

  /**
   * Bewegt einen Charakter zu seinem Haus (bei Nacht)
   */
  moveCharacterToHome(playerId: number): void {
    const movement = this.characterMovement.get(playerId);
    const house = this.playerHouses.get(playerId);
    
    if (!movement || !house) return;

    const housePos = house.getPosition();
    movement.targetPosition = {
      x: housePos.x * 0.7, // Etwas vor dem Haus
      y: 0,
      z: housePos.z * 0.7
    };
    movement.isMoving = true;
    movement.moveProgress = 0;
    movement.isAtHome = true;
  }

  /**
   * Bewegt einen Charakter zum Dorfplatz (bei Tag)
   */
  moveCharacterToCenter(playerId: number): void {
    const movement = this.characterMovement.get(playerId);
    if (!movement) return;

    // Zufällige Position im Zentrum
    const angle = Math.random() * Math.PI * 2;
    const radius = 2 + Math.random() * 4;
    
    movement.targetPosition = {
      x: Math.cos(angle) * radius,
      y: 0,
      z: Math.sin(angle) * radius
    };
    movement.isMoving = true;
    movement.moveProgress = 0;
    movement.isAtHome = false;
  }

  /**
   * Aktualisiert die Charakterbewegung
   */
  updateCharacterMovement(dt: number): void {
    this.characterMovement.forEach((movement, playerId) => {
      if (!movement.isMoving) return;

      movement.moveProgress += dt * movement.moveSpeed * 0.3;
      movement.walkCyclePhase += dt * 8;

      if (movement.moveProgress >= 1) {
        movement.moveProgress = 1;
        movement.isMoving = false;
        movement.currentPosition = { ...movement.targetPosition };
      } else {
        // Lineare Interpolation
        const t = this.easeInOutQuad(movement.moveProgress);
        movement.currentPosition = {
          x: this.lerp(movement.currentPosition.x, movement.targetPosition.x, t),
          y: 0,
          z: this.lerp(movement.currentPosition.z, movement.targetPosition.z, t)
        };
      }

      // Spielerentität aktualisieren (falls vorhanden)
      const playerEntity = this.playerCharacters.get(playerId);
      if (playerEntity) {
        playerEntity.setPosition(
          movement.currentPosition.x,
          movement.currentPosition.y,
          movement.currentPosition.z
        );

        // Lauf-Animation
        if (movement.isMoving) {
          const bobHeight = Math.abs(Math.sin(movement.walkCyclePhase)) * 0.1;
          playerEntity.setPosition(
            movement.currentPosition.x,
            bobHeight,
            movement.currentPosition.z
          );
        }
      }
    });
  }

  // ============================================================================
  // PHASENÜBERGÄNGE
  // ============================================================================

  /**
   * Startet den Übergang zur Nachtphase
   * @param sleepingPlayers - IDs der Spieler die schlafen gehen
   * @param phaseInfo - Optionale Phase-Informationen vom Backend
   */
  transitionToNight(sleepingPlayers: number[], phaseInfo?: PhaseDisplayInfo): void {
    this.currentPhase = 'night';
    this.isTransitioning = true;
    this.phaseTransitionTime = 0;

    // Alle Spieler zu ihren Häusern schicken (außer aktive)
    sleepingPlayers.forEach(playerId => {
      this.moveCharacterToHome(playerId);
      
      // Haus als schlafend markieren
      const house = this.playerHouses.get(playerId);
      if (house) {
        this.houseBuilder.updateHouseState(house, { isAsleep: true });
      }
    });

    // Overlay-Text einblenden (vom Backend)
    if (phaseInfo) {
      this.showPhaseOverlay(phaseInfo);
    }
  }

  /**
   * Startet den Übergang zur Tagphase
   * @param phaseInfo - Optionale Phase-Informationen vom Backend
   */
  transitionToDay(phaseInfo?: PhaseDisplayInfo): void {
    this.currentPhase = 'day';
    this.isTransitioning = true;
    this.phaseTransitionTime = 0;

    // Alle lebenden Spieler zum Zentrum
    this.characterMovement.forEach((_movement, playerId) => {
      const house = this.playerHouses.get(playerId);
      if (house && house.houseData.isAlive) {
        this.moveCharacterToCenter(playerId);
        this.houseBuilder.updateHouseState(house, { isAsleep: false });
      }
    });

    if (phaseInfo) {
      this.showPhaseOverlay(phaseInfo);
    }
  }

  /**
   * Markiert einen Spieler als aktiv (z.B. Werwolf in der Nacht)
   */
  setPlayerActive(playerId: number, isActive: boolean): void {
    const house = this.playerHouses.get(playerId);
    if (house) {
      this.houseBuilder.updateHouseState(house, { isActive });
    }
  }

  // ============================================================================
  // ABSTIMMUNGS-UI
  // ============================================================================

  /**
   * Zeigt einen Abstimmungsmarker über einem Haus
   */
  showVoteMarker(voterId: number, targetPlayerId: number): void {
    const pc = window.pc;
    const targetHouse = this.playerHouses.get(targetPlayerId);
    
    if (!targetHouse || !this.app) return;

    // Bestehenden Marker des Voters entfernen
    this.removeVoteMarker(voterId);

    // Neuen Marker erstellen (Stein/Zeichen über dem Haus)
    const marker = new pc.Entity(`VoteMarker-${voterId}-${targetPlayerId}`);
    marker.addComponent('model', { type: 'sphere' });
    marker.setLocalScale(0.4, 0.4, 0.4);

    // Position über dem Zielhaus
    const housePos = targetHouse.getPosition();
    const existingMarkers = this.votingMarkers.get(targetPlayerId) || [];
    const offsetX = (existingMarkers.length % 5 - 2) * 0.5;
    const offsetZ = Math.floor(existingMarkers.length / 5) * 0.4;
    
    marker.setPosition(
      housePos.x + offsetX,
      5 + existingMarkers.length * 0.1,
      housePos.z + offsetZ
    );

    // Material (roter Abstimmungsstein)
    const markerMat = new pc.StandardMaterial();
    markerMat.diffuse = new pc.Color(0.7, 0.2, 0.1);
    markerMat.emissive = new pc.Color(0.4, 0.1, 0.05);
    markerMat.emissiveIntensity = 1.5;
    markerMat.update();
    (marker.model as PCModel).material = markerMat;

    (this.app as any).root.addChild(marker);

    // Speichern
    if (!this.votingMarkers.has(targetPlayerId)) {
      this.votingMarkers.set(targetPlayerId, []);
    }
    this.votingMarkers.get(targetPlayerId)!.push({
      playerId: targetPlayerId,
      targetHouse,
      markerEntity: marker,
      voterId
    });
  }

  /**
   * Entfernt einen Abstimmungsmarker
   */
  removeVoteMarker(voterId: number): void {
    this.votingMarkers.forEach((markers) => {
      const markerIndex = markers.findIndex(m => m.voterId === voterId);
      if (markerIndex !== -1) {
        markers[markerIndex].markerEntity.destroy();
        markers.splice(markerIndex, 1);
      }
    });
  }

  /**
   * Entfernt alle Abstimmungsmarker
   */
  clearAllVoteMarkers(): void {
    this.votingMarkers.forEach(markers => {
      markers.forEach(m => m.markerEntity.destroy());
    });
    this.votingMarkers.clear();
  }

  // ============================================================================
  // ELIMINIERUNG
  // ============================================================================

  /**
   * Spielt die Eliminierungsanimation ab
   * @param event - Eliminierungs-Event vom Backend mit allen Texten
   */
  async playEliminationAnimation(event: EliminationEvent): Promise<void> {
    const house = this.playerHouses.get(event.player_id);
    if (!house) return;

    // Kamera auf Haus fokussieren
    const housePos = house.getPosition();
    this.focusCameraOn(housePos.x, housePos.z);

    // Warte auf Kamerabewegung
    await this.delay(800);

    // Haus-Zerstörungseffekt
    this.houseBuilder.updateHouseState(house, { isAlive: false, isAsleep: false, isActive: false });

    // Partikeleffekt (Rauch/Staub)
    this.spawnDestructionParticles(housePos.x, housePos.z);

    // Charakter entfernen
    const character = this.playerCharacters.get(event.player_id);
    if (character) {
      character.enabled = false;
    }

    // Eliminierungstext vom Backend (nicht hardcodiert!)
    this.showEliminationText(event.display_text);

    await this.delay(2000);
    
    // Kamera zurücksetzen
    this.resetCamera();
  }

  /**
   * Erzeugt Zerstörungs-Partikel
   */
  private spawnDestructionParticles(x: number, z: number): void {
    const pc = window.pc;
    if (!this.app) return;

    for (let i = 0; i < 20; i++) {
      const particle = new pc.Entity(`DestructionParticle-${i}`);
      particle.addComponent('model', { type: 'sphere' });
      
      const size = 0.1 + Math.random() * 0.3;
      particle.setLocalScale(size, size, size);
      particle.setPosition(
        x + (Math.random() - 0.5) * 4,
        1 + Math.random() * 3,
        z + (Math.random() - 0.5) * 4
      );

      const mat = new pc.StandardMaterial();
      mat.diffuse = new pc.Color(0.3, 0.25, 0.2);
      mat.opacity = 0.7;
      mat.blendType = pc.BLEND_NORMAL;
      mat.update();
      (particle.model as PCModel).material = mat;

      (this.app as any).root.addChild(particle);

      // Partikel nach Verzögerung entfernen
      setTimeout(() => particle.destroy(), 2000 + Math.random() * 1000);
    }
  }

  // ============================================================================
  // UI-OVERLAY
  // ============================================================================

  /**
   * Zeigt das Phasenübergangs-Overlay
   * @param info - Phase-Informationen vom Backend
   */
  private showPhaseOverlay(info: PhaseDisplayInfo): void {
    // Dies wird im HTML/CSS implementiert
    const event = new CustomEvent('village3d:phaseOverlay', {
      detail: { 
        text: info.display_name,
        description: info.description,
        icon: info.icon,
        color: info.color,
        phase: this.currentPhase 
      }
    });
    window.dispatchEvent(event);
  }

  /**
   * Zeigt den Eliminierungstext
   */
  private showEliminationText(text: string): void {
    const event = new CustomEvent('village3d:eliminationText', {
      detail: { text }
    });
    window.dispatchEvent(event);
  }

  // ============================================================================
  // KAMERA-STEUERUNG
  // ============================================================================

  /**
   * Fokussiert die Kamera auf eine Position
   */
  focusCameraOn(x: number, z: number): void {
    this.targetCameraState = {
      angle: Math.atan2(z, x) + Math.PI,
      height: 10,
      radius: 15,
      lookAtY: 2
    };
    
    // Event für externe Kamera-Steuerung (z.B. Village3DThree)
    window.dispatchEvent(new CustomEvent('village3d:cameraFocus', {
      detail: { x, z, cameraState: this.targetCameraState }
    }));
  }

  /**
   * Setzt die Kamera auf Standardposition zurück
   */
  resetCamera(): void {
    this.targetCameraState = {
      angle: 0,
      height: 15,
      radius: 25,
      lookAtY: 0
    };
  }

  /**
   * Gibt den Ziel-Kamera-Zustand zurück (für externe Kamera-Steuerung)
   */
  getTargetCameraState(): { angle: number; height: number; radius: number; lookAtY: number } {
    return { ...this.targetCameraState };
  }

  // ============================================================================
  // UPDATE-LOOP
  // ============================================================================

  /**
   * Haupt-Update-Methode (wird jeden Frame aufgerufen)
   */
  update(dt: number): void {
    // Charakterbewegung
    this.updateCharacterMovement(dt);

    // Phasenübergang
    if (this.isTransitioning) {
      this.phaseTransitionTime += dt;
      if (this.phaseTransitionTime > 2.0) {
        this.isTransitioning = false;
      }
    }

    // Aktive Häuser animieren
    const time = Date.now() / 1000;
    this.playerHouses.forEach(house => {
      if (house.houseData.isActive) {
        this.houseBuilder.animateActiveHouse(house, time);
      }
    });
  }

  // ============================================================================
  // HILFSMETHODEN
  // ============================================================================

  private lerp(a: number, b: number, t: number): number {
    return a + (b - a) * t;
  }

  private easeInOutQuad(t: number): number {
    return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
  }

  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // ============================================================================
  // CLEANUP
  // ============================================================================

  destroy(): void {
    this.playerHouses.forEach(house => house.destroy());
    this.playerHouses.clear();
    
    this.playerCharacters.forEach(char => char.destroy());
    this.playerCharacters.clear();
    
    this.characterMovement.clear();
    this.clearAllVoteMarkers();
  }
}
