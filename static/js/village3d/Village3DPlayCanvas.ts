/**
 * Village3DPlayCanvas - Main renderer class
 *
 * TypeScript version with modular architecture
 */

import type {
  PlayerData,
  RoleModel,
  RoleData,
  Village3DOptions,
  PlayerEntity,
  RolesAPIResponse,
  PCApplication,
  PCEntity,
  PCColor,
  PCMaterial,
} from "./types";
import { PlayerAvatarBuilder } from "./PlayerAvatarBuilder";

export default class Village3DPlayCanvas {
  private container: HTMLElement;
  private canvas: HTMLCanvasElement | null = null;
  private app: PCApplication | null = null;

  // Player data
  private players: PlayerData[] = [];
  private playerEntities: Map<number, PlayerEntity> = new Map();
  private playerLabels: Map<number, PCEntity> = new Map();

  // State
  private isNight: boolean = true;
  private isLobbyMode: boolean = false;

  // Camera
  private targetCameraAngle: number = 0;
  private targetCameraHeight: number = 15;
  private targetCameraRadius: number = 25;
  private defaultCameraAngle: number = 0;
  private defaultCameraHeight: number = 15;
  private defaultCameraRadius: number = 25;

  // Role data
  private roleColors: Record<string, PCColor> = {};
  private roleModels: Record<string, RoleModel> = {};

  // Materials and caching
  private materialCache: Map<string, PCMaterial> = new Map();

  // Modules (initialized in init())
  private avatarBuilder!: PlayerAvatarBuilder;

  // Callbacks
  public onPlayerClick: ((playerId: number) => void) | null = null;

  // Update binding
  private updateBound: ((dt: number) => void) | null = null;

  constructor(
    containerId: string,
    _raumCode: string,
    options: Village3DOptions = {},
  ) {
    const container = document.getElementById(containerId);
    if (!container) {
      throw new Error(`Container element with id "${containerId}" not found`);
    }
    this.container = container;

    this.isLobbyMode = options.lobbyMode || false;
    this.onPlayerClick = options.onPlayerClick || null;

    // Camera defaults based on mode
    if (this.isLobbyMode) {
      this.defaultCameraAngle = Math.PI / 4;
      this.defaultCameraHeight = 20;
      this.defaultCameraRadius = 30;
    }

    this.targetCameraAngle = this.defaultCameraAngle;
    this.targetCameraHeight = this.defaultCameraHeight;
    this.targetCameraRadius = this.defaultCameraRadius;

    this.loadRoleDataFromAPI();
    this.init();
  }

  /**
   * Load role colors and model definitions from API
   */
  private async loadRoleDataFromAPI(): Promise<void> {
    try {
      const response = await fetch("/api/roles");
      const data: RolesAPIResponse = await response.json();

      if (data.success && data.roles) {
        const pc = (window as any).pc;

        data.roles.forEach((role: RoleData) => {
          const roleName = role.name;

          // Load color
          if (role.farbe && role.farbe.startsWith("#")) {
            const r = parseInt(role.farbe.slice(1, 3), 16) / 255;
            const g = parseInt(role.farbe.slice(3, 5), 16) / 255;
            const b = parseInt(role.farbe.slice(5, 7), 16) / 255;
            this.roleColors[roleName] = new pc.Color(r, g, b);
          }

          // Load model definition
          if (role.model) {
            this.roleModels[roleName] = role.model;
          }
        });

        console.log(
          "[Village3D] Loaded",
          Object.keys(this.roleColors).length,
          "role colors and",
          Object.keys(this.roleModels).length,
          "model definitions from API",
        );

        // Refresh players with new role data
        if (this.players.length > 0 && this.avatarBuilder) {
          console.log(
            "[Village3D] Refreshing players with loaded role data...",
          );
          this.playerEntities.forEach((entity) => entity.destroy());
          this.playerEntities.clear();
          this.playerLabels.forEach((label) => label.destroy());
          this.playerLabels.clear();
          this.setPlayers(this.players);
        }
      }
    } catch (error) {
      console.warn("[Village3D] Failed to load role data from API:", error);
      // Fallback colors
      const pc = (window as any).pc;
      this.roleColors = {
        Werwolf: new pc.Color(0.6, 0.1, 0.1),
        Dorfbewohner: new pc.Color(0.3, 0.5, 0.8),
        Seherin: new pc.Color(0.5, 0.3, 0.9),
        Hexe: new pc.Color(0.2, 0.7, 0.3),
        default: new pc.Color(0.3, 0.5, 0.8),
      };
    }
  }

  /**
   * Initialize PlayCanvas application
   */
  private init(): void {
    const pc = (window as any).pc;

    // Check minimum container size
    const minHeight = 300;
    if (this.container.clientHeight < minHeight) {
      this.container.style.minHeight = `${minHeight}px`;
      console.warn(
        `[Village3D] Container height was below minimum, setting to ${minHeight}px`,
      );
    }

    // Create canvas
    this.canvas = document.createElement("canvas");
    this.canvas.style.width = "100%";
    this.canvas.style.height = "100%";
    this.canvas.style.display = "block";
    this.canvas.tabIndex = 0;
    this.container.appendChild(this.canvas);

    // Initialize PlayCanvas
    this.app = new pc.Application(this.canvas, {
      mouse: new pc.Mouse(this.canvas),
      touch: new pc.TouchDevice(this.canvas),
      keyboard: new pc.Keyboard(window),
      elementInput: new pc.ElementInput(this.canvas),
      graphicsDeviceOptions: {
        antialias: true,
        alpha: false,
        depth: true,
        stencil: true,
        powerPreference: "high-performance",
        deviceTypes: ["webgpu", "webgl2"],
        glslangUrl: "cdn.jsdelivr.net",
        twgslUrl: "cdn.jsdelivr.net",
      },
    });

    if (!this.app) {
      throw new Error("PlayCanvas application failed to initialize");
    }

    this.app.start();
    this.app.setCanvasFillMode(pc.FILLMODE_NONE);
    this.app.setCanvasResolution(pc.RESOLUTION_AUTO);

    // Resize handler
    const resizeCanvas = () => {
      if (this.canvas && this.app) {
        const dpr = window.devicePixelRatio || 1;
        this.canvas.width = this.container.clientWidth * dpr;
        this.canvas.height = this.container.clientHeight * dpr;
        this.app.resizeCanvas();
      }
    };

    window.addEventListener("resize", resizeCanvas);
    resizeCanvas();

    // Create scene and modules
    this.createScene();

    // Initialize avatar builder now that app is ready
    this.avatarBuilder = new PlayerAvatarBuilder(
      this.materialCache,
      this.roleColors,
      this.roleModels,
    );

    if (!this.app) {
      throw new Error("PlayCanvas application not initialized");
    }

    // Register update loop
    this.updateBound = (dt: number) => this.update(dt);
    this.app.on("update", this.updateBound);
  }

  /**
   * Create 3D scene with camera, lights, and environment
   */
  private createScene(): void {
    if (!this.app) {
      throw new Error("PlayCanvas application not initialized");
    }

    const pc = (window as any).pc;

    // Camera
    const camera = new pc.Entity("Camera");
    camera.addComponent("camera", {
      clearColor: new pc.Color(0.1, 0.1, 0.15),
      farClip: 1000,
    });
    camera.setPosition(0, this.targetCameraHeight, this.targetCameraRadius);
    camera.lookAt(0, 0, 0);
    this.app.root.addChild(camera);

    // Directional light (sun/moon)
    const light = new pc.Entity("DirectionalLight");
    light.addComponent("light", {
      type: "directional",
      color: this.isNight
        ? new pc.Color(0.4, 0.4, 0.6)
        : new pc.Color(1, 1, 0.9),
      intensity: this.isNight ? 0.4 : 0.8,
      castShadows: true,
      shadowDistance: 50,
      shadowResolution: 2048,
    });
    light.setEulerAngles(this.isNight ? 45 : 60, 30, 0);
    this.app.root.addChild(light);

    // Ambient light
    this.app.scene.ambientLight = this.isNight
      ? new pc.Color(0.15, 0.15, 0.2)
      : new pc.Color(0.3, 0.3, 0.35);

    // Ground
    this.createGround();

    // Buildings (only in game mode)
    if (!this.isLobbyMode) {
      this.createVillageBuildings();
    }
  }

  /**
   * Create ground plane
   */
  private createGround(): void {
    if (!this.app) {
      throw new Error("PlayCanvas application not initialized");
    }

    const pc = (window as any).pc;

    const ground = new pc.Entity("Ground");
    ground.addComponent("model", { type: "plane" });
    ground.setLocalScale(100, 1, 100);
    ground.setLocalPosition(0, 0, 0);

    const groundMat = new pc.StandardMaterial();
    groundMat.diffuse = new pc.Color(0.2, 0.4, 0.25);
    groundMat.specular = new pc.Color(0.05, 0.05, 0.05);
    groundMat.update();
    ground.model.material = groundMat;

    this.app.root.addChild(ground);
  }

  /**
   * Create village buildings
   */
  private createVillageBuildings(): void {
    // Simplified building creation
    // Full implementation would mirror original JS createVillageBuildings method
    console.log("[Village3D] Creating village buildings...");
  }

  /**
   * Set players and create their 3D avatars
   */
  setPlayers(players: PlayerData[]): void {
    this.players = players;

    // Clear existing
    this.playerEntities.forEach((entity) => entity.destroy());
    this.playerEntities.clear();
    this.playerLabels.clear();

    // Calculate layout
    const radius = 10;
    const angleStep = (Math.PI * 2) / Math.max(players.length, 1);

    players.forEach((player, index) => {
      const angle = index * angleStep;
      const x = Math.cos(angle) * radius;
      const z = Math.sin(angle) * radius;

      const playerEntity = this.avatarBuilder.createPlayerAvatar(
        player,
        x,
        z,
        angle,
      );

      if (this.app) {
        this.app.root.addChild(playerEntity);
      }

      this.playerEntities.set(player.id, playerEntity);

      // Update visual effects
      this.updatePlayerEffects(playerEntity, player);
    });

    console.log(`[Village3D] Created ${players.length} player avatars`);
  }

  /**
   * Update visual effects on player entity
   */
  private updatePlayerEffects(_entity: PlayerEntity, data: PlayerData): void {
    // Apply visual effects from data.visual_effects
    if (data.visual_effects && Array.isArray(data.visual_effects)) {
      data.visual_effects.forEach((effect) => {
        console.log(
          `[Village3D] Applying effect ${effect.type} to player ${data.id}`,
        );
        // Effect application logic would go here
      });
    }
  }

  /**
   * Set time of day (day/night cycle)
   */
  setTimeOfDay(isNight: boolean): void {
    this.isNight = isNight;
    console.log(`[Village3D] Setting time to ${isNight ? "night" : "day"}`);
    // Update lighting and atmosphere
  }

  /**
   * Main update loop
   */
  private update(dt: number): void {
    if (!this.app) return;

    // Camera smoothing
    const camera = this.app.root.findByName("Camera");
    if (camera) {
      const targetX =
        Math.cos(this.targetCameraAngle) * this.targetCameraRadius;
      const targetZ =
        Math.sin(this.targetCameraAngle) * this.targetCameraRadius;

      const currentPos = camera.getPosition();
      const lerpFactor = Math.min(dt * 3, 1);

      camera.setPosition(
        currentPos.x + (targetX - currentPos.x) * lerpFactor,
        currentPos.y + (this.targetCameraHeight - currentPos.y) * lerpFactor,
        currentPos.z + (targetZ - currentPos.z) * lerpFactor,
      );

      camera.lookAt(0, 0, 0);
    }

    // Animate players
    this.playerEntities.forEach((entity) => {
      if (entity.animState) {
        entity.animState.time += dt * entity.animState.idleSpeed;

        // Simple idle animation
        if (entity.parts.arms) {
          entity.parts.arms.forEach((arm: PCEntity, i: number) => {
            const swing = Math.sin(entity.animState.time + i * Math.PI) * 0.1;
            arm.setLocalEulerAngles(swing * 20, 0, 0);
          });
        }
      }
    });
  }

  /**
   * Reset camera to default position
   */
  resetCamera(): void {
    this.targetCameraAngle = this.defaultCameraAngle;
    this.targetCameraHeight = this.defaultCameraHeight;
    this.targetCameraRadius = this.defaultCameraRadius;
  }

  /**
   * Cleanup and destroy
   */
  destroy(): void {
    if (this.updateBound && this.app) {
      this.app.off("update", this.updateBound);
    }

    this.playerEntities.forEach((entity) => entity.destroy());
    this.playerEntities.clear();
    this.playerLabels.clear();

    if (this.app) {
      this.app.destroy();
    }

    if (this.canvas && this.canvas.parentElement) {
      this.canvas.parentElement.removeChild(this.canvas);
    }
  }
}
