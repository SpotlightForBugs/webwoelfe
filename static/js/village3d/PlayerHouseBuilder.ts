/**
 * PlayerHouseBuilder - Erstellt individuelle Spieler-Häuser im 3D-Dorf
 *
 * Jeder Spieler erhält ein einzigartiges Haus mit:
 * - Unterschiedlichen Dachformen
 * - Variablen Fensterformen
 * - Leichten Farbvariationen
 * - Beleuchtungszuständen (lebend/schlafend/ausgeschieden)
 */

import type { PCEntity, PCMaterial, PCColor, PCModel, PlayerData } from './types.js';

export interface PlayerHouseConfig {
  playerId: number;
  playerName: string;
  position: { x: number; z: number };
  rotation: number;
  houseStyle: 'cottage' | 'tudor' | 'farmhouse' | 'cabin';
  roofStyle: 'gabled' | 'hipped' | 'thatched' | 'flat';
  colorScheme: {
    walls: string;
    roof: string;
    trim: string;
  };
}

export interface PlayerHouseEntity extends PCEntity {
  houseData: {
    playerId: number;
    playerName: string;
    isAlive: boolean;
    isAsleep: boolean;
    isActive: boolean;
  };
  houseParts: {
    base: PCEntity;
    roof: PCEntity;
    door: PCEntity;
    windows: PCEntity[];
    chimney?: PCEntity;
    windowLights: PCEntity[];
    nameLabel?: PCEntity;
  };
  windowMaterials: PCMaterial[];
  baseMaterial: PCMaterial;
  roofMaterial: PCMaterial;
}

// Vordefinierte Hausstile für Variation
const HOUSE_STYLES = {
  cottage: {
    baseScale: { x: 3.5, y: 2.2, z: 3.0 },
    roofHeight: 1.8,
    roofOverhang: 0.4,
    windowSize: { w: 0.6, h: 0.7 },
    hasChimney: true
  },
  tudor: {
    baseScale: { x: 4.0, y: 2.5, z: 3.5 },
    roofHeight: 2.2,
    roofOverhang: 0.3,
    windowSize: { w: 0.5, h: 0.8 },
    hasChimney: true
  },
  farmhouse: {
    baseScale: { x: 5.0, y: 2.0, z: 3.2 },
    roofHeight: 1.6,
    roofOverhang: 0.6,
    windowSize: { w: 0.7, h: 0.6 },
    hasChimney: true
  },
  cabin: {
    baseScale: { x: 3.2, y: 2.0, z: 2.8 },
    roofHeight: 1.4,
    roofOverhang: 0.5,
    windowSize: { w: 0.5, h: 0.5 },
    hasChimney: false
  }
};

// Farbpalette für Häuser - Düsterwald-Stil
const COLOR_PALETTES = [
  { walls: '#2a2520', roof: '#1a1614', trim: '#3d3530' },
  { walls: '#2d2822', roof: '#1c1510', trim: '#403a34' },
  { walls: '#252320', roof: '#181614', trim: '#383430' },
  { walls: '#302a24', roof: '#1e1816', trim: '#443e38' },
  { walls: '#282622', roof: '#161412', trim: '#3c3834' },
  { walls: '#2c2824', roof: '#1a1614', trim: '#423c36' },
];

export class PlayerHouseBuilder {
  // Material-Cache für wiederverwendbare Materialien (für zukünftige Optimierung)
  private _materialCache: Map<string, PCMaterial>;
  private houseConfigs: Map<number, PlayerHouseConfig> = new Map();

  constructor(materialCache: Map<string, PCMaterial>) {
    this._materialCache = materialCache;
  }

  /**
   * Gibt den Material-Cache zurück (für externe Nutzung)
   */
  getMaterialCache(): Map<string, PCMaterial> {
    return this._materialCache;
  }

  /**
   * Generiert eine Hauskonfiguration basierend auf Spieler-ID
   */
  private generateHouseConfig(
    playerId: number,
    playerName: string,
    position: { x: number; z: number },
    rotation: number
  ): PlayerHouseConfig {
    // Deterministisch basierend auf Spieler-ID
    const styleIndex = playerId % 4;
    const colorIndex = playerId % COLOR_PALETTES.length;
    const roofStyles: Array<'gabled' | 'hipped' | 'thatched' | 'flat'> = ['gabled', 'hipped', 'thatched', 'flat'];
    const houseStyles: Array<'cottage' | 'tudor' | 'farmhouse' | 'cabin'> = ['cottage', 'tudor', 'farmhouse', 'cabin'];

    return {
      playerId,
      playerName,
      position,
      rotation,
      houseStyle: houseStyles[styleIndex],
      roofStyle: roofStyles[(playerId + 1) % 4],
      colorScheme: COLOR_PALETTES[colorIndex]
    };
  }

  /**
   * Erstellt ein Spielerhaus
   */
  createPlayerHouse(
    player: PlayerData,
    posX: number,
    posZ: number,
    rotation: number
  ): PlayerHouseEntity {
    const pc = window.pc;

    const config = this.generateHouseConfig(player.id, player.name, { x: posX, z: posZ }, rotation);
    this.houseConfigs.set(player.id, config);

    const style = HOUSE_STYLES[config.houseStyle];
    const colors = config.colorScheme;

    // Hauptentität
    const house = new pc.Entity(`PlayerHouse-${player.id}`) as PlayerHouseEntity;
    
    house.houseData = {
      playerId: player.id,
      playerName: player.name,
      isAlive: player.ist_am_leben,
      isAsleep: false,
      isActive: false
    };

    house.houseParts = {
      base: null as unknown as PCEntity,
      roof: null as unknown as PCEntity,
      door: null as unknown as PCEntity,
      windows: [],
      windowLights: []
    };

    house.windowMaterials = [];

    // === HAUSBASIS ===
    const base = new pc.Entity('HouseBase');
    base.addComponent('model', { type: 'box' });
    base.setLocalScale(style.baseScale.x, style.baseScale.y, style.baseScale.z);
    base.setLocalPosition(0, style.baseScale.y / 2, 0);

    const baseMat = new pc.StandardMaterial();
    baseMat.diffuse = this.hexToColor(colors.walls);
    baseMat.specular = new pc.Color(0.02, 0.02, 0.02);
    baseMat.update();
    (base.model as PCModel).material = baseMat;
    house.addChild(base);
    house.houseParts.base = base;
    house.baseMaterial = baseMat;

    // === DACH ===
    const roof = this.createRoof(config, style, colors);
    house.addChild(roof);
    house.houseParts.roof = roof;

    // === TÜR ===
    const door = new pc.Entity('Door');
    door.addComponent('model', { type: 'box' });
    door.setLocalScale(0.8, 1.6, 0.1);
    door.setLocalPosition(0, 0.8, style.baseScale.z / 2 + 0.05);

    const doorMat = new pc.StandardMaterial();
    doorMat.diffuse = new pc.Color(0.15, 0.1, 0.07);
    doorMat.update();
    (door.model as PCModel).material = doorMat;
    house.addChild(door);
    house.houseParts.door = door;

    // === FENSTER MIT LICHT ===
    const windowPositions = this.getWindowPositions(config, style);
    windowPositions.forEach((pos) => {
      const { window, windowLight, windowMat } = this.createWindow(pos, style, player.ist_am_leben);
      house.addChild(window);
      house.addChild(windowLight);
      house.houseParts.windows.push(window);
      house.houseParts.windowLights.push(windowLight);
      house.windowMaterials.push(windowMat);
    });

    // === SCHORNSTEIN ===
    if (style.hasChimney) {
      const chimney = this.createChimney(style);
      house.addChild(chimney);
      house.houseParts.chimney = chimney;
    }

    // === NAMENSLABEL ===
    const nameLabel = this.createNameLabel(player.name, player.ist_am_leben);
    house.addChild(nameLabel);
    house.houseParts.nameLabel = nameLabel;

    // Position und Rotation
    house.setPosition(posX, 0, posZ);
    house.setEulerAngles(0, rotation, 0);

    // Dachfarbe Material speichern
    house.roofMaterial = (roof.model as PCModel).material as PCMaterial;

    return house;
  }

  /**
   * Erstellt das Dach basierend auf Stil
   */
  private createRoof(
    config: PlayerHouseConfig,
    style: typeof HOUSE_STYLES.cottage,
    colors: { walls: string; roof: string; trim: string }
  ): PCEntity {
    const pc = window.pc;
    const roof = new pc.Entity('Roof');

    const roofMat = new pc.StandardMaterial();
    roofMat.diffuse = this.hexToColor(colors.roof);
    roofMat.specular = new pc.Color(0.01, 0.01, 0.01);
    roofMat.update();

    const baseY = style.baseScale.y;

    switch (config.roofStyle) {
      case 'gabled': {
        // Zwei schräge Dachplatten
        const roofAngle = 35;
        const roofWidth = style.baseScale.x / 2 + style.roofOverhang;
        const roofDepth = style.baseScale.z + style.roofOverhang * 2;
        const panelWidth = roofWidth / Math.cos(roofAngle * Math.PI / 180);

        const leftPanel = new pc.Entity('RoofLeft');
        leftPanel.addComponent('model', { type: 'box' });
        leftPanel.setLocalScale(panelWidth, 0.1, roofDepth);
        leftPanel.setLocalPosition(-roofWidth / 2, baseY + style.roofHeight / 2, 0);
        leftPanel.setLocalEulerAngles(0, 0, roofAngle);
        (leftPanel.model as PCModel).material = roofMat;
        roof.addChild(leftPanel);

        const rightPanel = new pc.Entity('RoofRight');
        rightPanel.addComponent('model', { type: 'box' });
        rightPanel.setLocalScale(panelWidth, 0.1, roofDepth);
        rightPanel.setLocalPosition(roofWidth / 2, baseY + style.roofHeight / 2, 0);
        rightPanel.setLocalEulerAngles(0, 0, -roofAngle);
        (rightPanel.model as PCModel).material = roofMat;
        roof.addChild(rightPanel);
        break;
      }

      case 'hipped': {
        // Pyramidendach
        roof.addComponent('model', { type: 'cone' });
        const size = Math.max(style.baseScale.x, style.baseScale.z) + style.roofOverhang;
        roof.setLocalScale(size, style.roofHeight, size);
        roof.setLocalPosition(0, baseY + style.roofHeight / 2, 0);
        (roof.model as PCModel).material = roofMat;
        break;
      }

      case 'thatched': {
        // Abgerundetes Strohdach
        roof.addComponent('model', { type: 'sphere' });
        const sizeX = style.baseScale.x + style.roofOverhang;
        const sizeZ = style.baseScale.z + style.roofOverhang;
        roof.setLocalScale(sizeX, style.roofHeight * 0.8, sizeZ);
        roof.setLocalPosition(0, baseY + style.roofHeight * 0.3, 0);
        
        // Strohdach-Texturfarbe
        roofMat.diffuse = new pc.Color(0.18, 0.14, 0.08);
        roofMat.update();
        (roof.model as PCModel).material = roofMat;
        break;
      }

      case 'flat': {
        // Flaches Dach mit Rand
        roof.addComponent('model', { type: 'box' });
        roof.setLocalScale(
          style.baseScale.x + style.roofOverhang,
          0.15,
          style.baseScale.z + style.roofOverhang
        );
        roof.setLocalPosition(0, baseY + 0.075, 0);
        (roof.model as PCModel).material = roofMat;
        break;
      }
    }

    return roof;
  }

  /**
   * Berechnet Fensterpositionen
   */
  private getWindowPositions(
    _config: PlayerHouseConfig,
    style: typeof HOUSE_STYLES.cottage
  ): Array<{ x: number; y: number; z: number; side: 'front' | 'left' | 'right' }> {
    const positions: Array<{ x: number; y: number; z: number; side: 'front' | 'left' | 'right' }> = [];
    const windowY = style.baseScale.y * 0.5;

    // Vorderfenster (links und rechts der Tür)
    positions.push({
      x: -style.baseScale.x / 3,
      y: windowY,
      z: style.baseScale.z / 2 + 0.05,
      side: 'front'
    });
    positions.push({
      x: style.baseScale.x / 3,
      y: windowY,
      z: style.baseScale.z / 2 + 0.05,
      side: 'front'
    });

    // Seitenfenster
    positions.push({
      x: -style.baseScale.x / 2 - 0.05,
      y: windowY,
      z: 0,
      side: 'left'
    });
    positions.push({
      x: style.baseScale.x / 2 + 0.05,
      y: windowY,
      z: 0,
      side: 'right'
    });

    return positions;
  }

  /**
   * Erstellt ein Fenster mit Lichteffekt
   */
  private createWindow(
    pos: { x: number; y: number; z: number; side: 'front' | 'left' | 'right' },
    style: typeof HOUSE_STYLES.cottage,
    isAlive: boolean
  ): { window: PCEntity; windowLight: PCEntity; windowMat: PCMaterial } {
    const pc = globalThis.window.pc;

    // Fensterrahmen
    const windowFrame = new pc.Entity('Window');
    windowFrame.addComponent('model', { type: 'box' });

    let scaleX = style.windowSize.w;
    let scaleZ = 0.08;
    
    if (pos.side === 'left' || pos.side === 'right') {
      scaleX = 0.08;
      scaleZ = style.windowSize.w;
    }

    windowFrame.setLocalScale(scaleX, style.windowSize.h, scaleZ);
    windowFrame.setLocalPosition(pos.x, pos.y, pos.z);

    const windowMat = new pc.StandardMaterial();
    windowMat.diffuse = new pc.Color(0.1, 0.08, 0.06);
    
    // Warmes Fensterlicht wenn lebend
    if (isAlive) {
      windowMat.emissive = new pc.Color(0.6, 0.4, 0.15);
      windowMat.emissiveIntensity = 1.5;
    } else {
      windowMat.emissive = new pc.Color(0.05, 0.05, 0.05);
      windowMat.emissiveIntensity = 0.3;
    }
    windowMat.opacity = 0.85;
    windowMat.blendType = pc.BLEND_NORMAL;
    windowMat.update();
    (windowFrame.model as PCModel).material = windowMat;

    // Lichtschein vor dem Fenster
    const windowLight = new pc.Entity('WindowLight');
    windowLight.addComponent('model', { type: 'sphere' });
    windowLight.setLocalScale(1.2, 0.8, 0.6);
    
    let lightPos = { x: pos.x, y: pos.y, z: pos.z + 0.5 };
    if (pos.side === 'left') {
      lightPos = { x: pos.x - 0.5, y: pos.y, z: pos.z };
    } else if (pos.side === 'right') {
      lightPos = { x: pos.x + 0.5, y: pos.y, z: pos.z };
    }
    windowLight.setLocalPosition(lightPos.x, lightPos.y, lightPos.z);

    const lightMat = new pc.StandardMaterial();
    if (isAlive) {
      lightMat.emissive = new pc.Color(0.8, 0.5, 0.2);
      lightMat.opacity = 0.15;
    } else {
      lightMat.emissive = new pc.Color(0.1, 0.1, 0.1);
      lightMat.opacity = 0.02;
    }
    lightMat.blendType = pc.BLEND_ADDITIVE;
    lightMat.useLighting = false;
    lightMat.update();
    (windowLight.model as PCModel).material = lightMat;

    return { window: windowFrame, windowLight, windowMat };
  }

  /**
   * Erstellt einen Schornstein
   */
  private createChimney(style: typeof HOUSE_STYLES.cottage): PCEntity {
    const pc = window.pc;

    const chimney = new pc.Entity('Chimney');
    chimney.addComponent('model', { type: 'box' });
    chimney.setLocalScale(0.4, 1.2, 0.4);
    chimney.setLocalPosition(
      style.baseScale.x / 3,
      style.baseScale.y + style.roofHeight * 0.6,
      -style.baseScale.z / 4
    );

    const chimneyMat = new pc.StandardMaterial();
    chimneyMat.diffuse = new pc.Color(0.12, 0.1, 0.1);
    chimneyMat.update();
    (chimney.model as PCModel).material = chimneyMat;

    return chimney;
  }

  /**
   * Erstellt ein Namenslabel über dem Haus
   */
  private createNameLabel(name: string, isAlive: boolean): PCEntity {
    const pc = window.pc;

    const label = new pc.Entity('NameLabel');
    label.addComponent('model', { type: 'plane' });
    label.setLocalScale(3, 0.6, 1);
    label.setLocalPosition(0, 4.5, 0);
    label.setLocalEulerAngles(0, 0, 0);

    // Canvas für Text
    const canvas = document.createElement('canvas');
    canvas.width = 256;
    canvas.height = 64;
    const ctx = canvas.getContext('2d')!;

    // Hintergrund
    ctx.fillStyle = isAlive ? 'rgba(0,0,0,0.75)' : 'rgba(0,0,0,0.4)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Rand
    ctx.strokeStyle = isAlive ? '#d4a574' : '#666666';
    ctx.lineWidth = 2;
    ctx.strokeRect(2, 2, canvas.width - 4, canvas.height - 4);

    // Text
    ctx.fillStyle = isAlive ? '#ffffff' : '#888888';
    ctx.font = 'bold 32px "Crimson Pro", Georgia, serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(name, canvas.width / 2, canvas.height / 2);

    const texture = new pc.Texture();
    texture.setSource(canvas);

    const labelMat = new pc.StandardMaterial();
    labelMat.diffuseMap = texture;
    labelMat.emissive = new pc.Color(1, 1, 1);
    labelMat.emissiveMap = texture;
    labelMat.opacity = isAlive ? 1.0 : 0.5;
    labelMat.blendType = pc.BLEND_NORMAL;
    labelMat.cull = pc.CULLFACE_NONE;
    labelMat.depthWrite = false;
    labelMat.update();
    (label.model as PCModel).material = labelMat;

    return label;
  }

  /**
   * Aktualisiert den Hauszustand (lebend/schlafend/ausgeschieden)
   */
  updateHouseState(
    house: PlayerHouseEntity,
    state: {
      isAlive?: boolean;
      isAsleep?: boolean;
      isActive?: boolean;
    }
  ): void {
    const pc = window.pc;

    if (state.isAlive !== undefined) {
      house.houseData.isAlive = state.isAlive;
    }
    if (state.isAsleep !== undefined) {
      house.houseData.isAsleep = state.isAsleep;
    }
    if (state.isActive !== undefined) {
      house.houseData.isActive = state.isActive;
    }

    const { isAlive, isAsleep, isActive } = house.houseData;

    // Fenster-Beleuchtung aktualisieren
    house.windowMaterials.forEach(mat => {
      if (!isAlive) {
        // Ausgeschieden - dunkle, beschädigte Fenster
        mat.emissive = new pc.Color(0.02, 0.02, 0.02);
        mat.emissiveIntensity = 0.1;
      } else if (isAsleep) {
        // Schlafend - Fenster dunkel
        mat.emissive = new pc.Color(0.05, 0.04, 0.03);
        mat.emissiveIntensity = 0.3;
      } else if (isActive) {
        // Aktiv - pulsierendes Licht
        mat.emissive = new pc.Color(0.8, 0.6, 0.25);
        mat.emissiveIntensity = 2.0;
      } else {
        // Normal lebend - warmes Licht
        mat.emissive = new pc.Color(0.6, 0.4, 0.15);
        mat.emissiveIntensity = 1.5;
      }
      mat.update();
    });

    // Hausmaterial bei Tod verändern
    if (!isAlive && house.baseMaterial) {
      house.baseMaterial.diffuse = new pc.Color(0.12, 0.1, 0.1);
      house.baseMaterial.update();
    }
    if (!isAlive && house.roofMaterial) {
      house.roofMaterial.diffuse = new pc.Color(0.08, 0.06, 0.06);
      house.roofMaterial.update();
    }
  }

  /**
   * Animiert Fensterlicht-Pulsieren für aktive Spieler
   */
  animateActiveHouse(house: PlayerHouseEntity, time: number): void {
    if (!house.houseData.isActive || !house.houseData.isAlive) return;

    const pulseIntensity = 1.5 + Math.sin(time * 3) * 0.5;
    
    house.windowMaterials.forEach(mat => {
      mat.emissiveIntensity = pulseIntensity;
      mat.update();
    });
  }

  /**
   * Konvertiert Hex-Farbe zu PlayCanvas-Color
   */
  private hexToColor(hex: string): PCColor {
    const pc = window.pc;
    hex = hex.replace('#', '');
    const r = parseInt(hex.substring(0, 2), 16) / 255;
    const g = parseInt(hex.substring(2, 4), 16) / 255;
    const b = parseInt(hex.substring(4, 6), 16) / 255;
    return new pc.Color(r, g, b);
  }
}
