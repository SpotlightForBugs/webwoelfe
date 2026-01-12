/**
 * Village3DThree - Main renderer class
 *
 * TypeScript version with modular architecture
 */

import "./pc_shim.js";

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
  PCVec3,
  UIButtonData,
  PCModel,
  HintEntity,
  AnimatedEntity,
  PulseEntity,
  ViewMode,
} from "./types.js";
import { PlayerAvatarBuilder } from "./PlayerAvatarBuilder.js";

export default class Village3DThree {
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

  // Sky and celestial bodies
  private skyDome: PCEntity | null = null;
  private stars: Array<{
    entity: PCEntity;
    material: PCMaterial;
    baseBrightness: number;
    twinkleSpeed: number;
    twinklePhase: number;
  }> = [];
  private moon: PCEntity | null = null;
  private sun: PCEntity | null = null;
  private sunGlow: PCEntity | null = null;

  // Particles and effects
  private fireParticles: Array<{
    entity: PCEntity;
    type: string;
    life: number;
    maxLife: number;
    velocity: PCVec3;
    startScale: number;
    endScale: number;
  }> = [];

  private particles: Array<{
    entity: PCEntity;
    type: string;
    life: number;
    maxLife: number;
    velocity: PCVec3;
    startScale: number;
    endScale: number;
    startColor: PCColor;
    endColor: PCColor;
  }> = [];

  private particleSpawner = {
    timer: 0,
  };

  // Lighting
  private camera: PCEntity | null = null;
  private light: PCEntity | null = null;
  private fillLight: PCEntity | null = null;
  private rimLight: PCEntity | null = null;
  private fireLight: PCEntity | null = null;
  private moonGlow: PCEntity | null = null;

  // Atmosphere
  private fireflies: Array<{
    entity: PCEntity;
    material: PCMaterial;
    velocity: PCVec3;
    pulseSpeed: number;
    pulsePhase: number;
  }> = [];

  private fogPlanes: PCEntity[] = [];

  // Layout mode
  private layoutMode: string = "circle";

  // Sleeping players tracking
  private sleepingPlayers: Set<number> = new Set();

  // Current orbit for camera
  private cameraAngle: number = 0;
  private cameraHeight: number = 15;
  private cameraRadius: number = 25;
  private targetPosition: PCVec3 | null = null;

  // First-person camera state
  private viewMode: ViewMode = "orbit";
  private firstPersonPlayerId: number | null = null;
  private firstPersonYaw: number = 0;
  private firstPersonPitch: number = 0;
  private firstPersonHeight: number = 1.7;

  // Buildings
  private buildings: PCEntity[] = [];

  // Material caches
  private deadMaterial: PCMaterial | null = null;
  private skyMaterial: PCMaterial | null = null;
  private moonMaterial: PCMaterial | null = null;

  // Victim highlight tracking
  private victimHighlight: { entity: PCEntity; material: PCMaterial } | null =
    null;

  // HUD state
  private hudVisible: boolean = false;
  private leftSidebarVisible: boolean = true;
  private rightSidebarVisible: boolean = true;

  // Selection highlight
  private selectedHighlight: { playerId: number; entity: PCEntity } | null =
    null;

  // Hover highlight (interaction cue)
  private hoverHighlight: { playerId: number; entity: PCEntity } | null = null;
  private lastHoverCheckAt: number = 0;

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
    this.viewMode = "first-person";
    this.firstPersonPlayerId = options.firstPersonPlayerId ?? null;
    this.firstPersonHeight =
      options.firstPersonHeight ?? this.firstPersonHeight;

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
        const pc = window.pc;

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
      const pc = window.pc;
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
    const pc = window.pc;

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

    // Setup input controls
    this.setupInput();

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

    const pc = window.pc;

    // Camera
    this.camera = new pc.Entity("Camera");
    if (!this.camera) throw new Error("Failed to create camera");
    this.camera.addComponent("camera", {
      // Lobby mode uses brighter sky color
      clearColor: this.isLobbyMode
        ? new pc.Color(0.35, 0.45, 0.55)
        : new pc.Color(0.1, 0.1, 0.15),
      farClip: 1000,
    });
    this.camera.setPosition(
      0,
      this.targetCameraHeight,
      this.targetCameraRadius,
    );
    this.camera.lookAt(0, 0, 0);
    this.app.root.addChild(this.camera);

    // Initialize camera tracking variables
    this.cameraAngle = this.defaultCameraAngle;
    this.cameraHeight = this.defaultCameraHeight;
    this.cameraRadius = this.defaultCameraRadius;
    this.targetCameraAngle = this.cameraAngle;
    this.targetCameraHeight = this.cameraHeight;
    this.targetCameraRadius = this.cameraRadius;

    const pc2 = window.pc;
    this.targetPosition = new pc2.Vec3(0, 0, 0);

    // Directional light (sun/moon)
    this.light = new pc.Entity("DirectionalLight");
    if (!this.light) throw new Error("Failed to create light");
    this.light.addComponent("light", {
      type: "directional",
      // Düsterwald: cold moonlight at night, pale overcast by day
      color: this.isNight
        ? new pc.Color(0.25, 0.3, 0.55)
        : new pc.Color(0.7, 0.7, 0.75),
      intensity: this.isNight ? 0.35 : 0.55,
      castShadows: true,
      shadowDistance: 50,
      shadowResolution: 2048,
    });
    this.light.setEulerAngles(this.isNight ? 45 : 60, 30, 0);
    this.app.root.addChild(this.light);

    // Fill light - subtle warm bounce from ground
    this.fillLight = new pc.Entity("FillLight");
    if (!this.fillLight) throw new Error("Failed to create fill light");
    this.fillLight.addComponent("light", {
      type: "directional",
      color: new pc.Color(0.25, 0.22, 0.35),
      intensity: 0.25,
      castShadows: false,
    });
    this.fillLight.setLocalEulerAngles(-35, 190, 0);
    this.app.root.addChild(this.fillLight);

    // Rim light - creates silhouette highlights
    this.rimLight = new pc.Entity("RimLight");
    if (!this.rimLight) throw new Error("Failed to create rim light");
    this.rimLight.addComponent("light", {
      type: "directional",
      color: new pc.Color(0.4, 0.5, 0.7),
      intensity: 0.15,
      castShadows: false,
    });
    this.rimLight.setLocalEulerAngles(10, -90, 0);
    this.app.root.addChild(this.rimLight);

    // Ambient light - Düsterwald: very dark, cold blue-green tint (brighter for lobby)
    if (this.isLobbyMode) {
      this.app.scene.ambientLight = new pc.Color(0.25, 0.25, 0.3);
    } else {
      this.app.scene.ambientLight = this.isNight
        ? new pc.Color(0.06, 0.07, 0.12)
        : new pc.Color(0.18, 0.18, 0.22);
    }

    // Sky dome with stars (also for lobby mode for proper background)
    this.createSkyDome();
    if (!this.isLobbyMode) {
      this.createCelestialBodies();
    }

    // Ground
    this.createDetailedGround();

    // Buildings (only in game mode)
    if (!this.isLobbyMode) {
      this.createVillageBuildings();
      this.createCampfire();
    }

    // Enhanced environment and effects
    this.createEnhancedEnvironment();
    this.createEnhancedAtmosphericEffects();
    this.createGroundFog();
  }

  /**
   * Create sky dome with stars
   */
  private createSkyDome(): void {
    if (!this.app) return;
    const pc = window.pc;

    // Large inverted sphere for sky
    this.skyDome = new pc.Entity("SkyDome");
    if (this.skyDome) {
      this.skyDome.addComponent("model", { type: "sphere" });
      this.skyDome.setLocalScale(400, 400, 400);
      this.skyDome.setPosition(0, 0, 0);
    }

    // Night sky gradient material - Düsterwald: pitch black with hint of deep purple
    this.skyMaterial = new pc.StandardMaterial();
    if (!this.skyMaterial) throw new Error("Failed to create sky material");

    if (this.isLobbyMode) {
      this.skyMaterial.diffuse = new pc.Color(0.05, 0.08, 0.15);
      this.skyMaterial.emissive = new pc.Color(0.02, 0.03, 0.06);
    } else {
      this.skyMaterial.diffuse = new pc.Color(0.008, 0.01, 0.025);
      this.skyMaterial.emissive = new pc.Color(0.01, 0.008, 0.03);
    }

    this.skyMaterial.useLighting = false;
    this.skyMaterial.cull = pc.CULLFACE_FRONT; // Render inside
    this.skyMaterial.update();

    if (this.skyDome) {
      const skyModel = this.skyDome.model as PCModel;
      if (skyModel) {
        skyModel.material = this.skyMaterial;
      }
      this.app.root.addChild(this.skyDome);
    }

    // Stars (small glowing spheres scattered on sky dome)
    this.stars = [];
    const starCount = this.isLobbyMode ? 100 : 180;
    for (let i = 0; i < starCount; i++) {
      const star = new pc.Entity(`Star-${i}`);
      star.addComponent("model", { type: "sphere" });

      // Random position on sphere surface
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      const radius = 380;
      const x = radius * Math.sin(phi) * Math.cos(theta);
      const y = Math.abs(radius * Math.cos(phi)) + 10; // Only upper hemisphere
      const z = radius * Math.sin(phi) * Math.sin(theta);

      // Variable star sizes for depth
      const size = 0.15 + Math.random() * 0.35;
      star.setLocalScale(size, size, size);
      star.setPosition(x, y, z);

      // Star material with twinkle potential
      const starMat = new pc.StandardMaterial();
      const brightness = 0.6 + Math.random() * 0.4;
      const warmth = Math.random();
      // Mix between white, blue, and yellow stars
      if (warmth < 0.3) {
        starMat.emissive = new pc.Color(
          brightness,
          brightness * 0.9,
          brightness * 0.7,
        ); // Warm
      } else if (warmth < 0.6) {
        starMat.emissive = new pc.Color(
          brightness * 0.8,
          brightness * 0.85,
          brightness,
        ); // Blue
      } else {
        starMat.emissive = new pc.Color(brightness, brightness, brightness); // White
      }
      starMat.opacity = 0.9;
      starMat.blendType = pc.BLEND_ADDITIVE;
      starMat.useLighting = false;
      starMat.update();
      (star.model as PCModel).material = starMat;

      this.app.root.addChild(star);
      this.stars.push({
        entity: star,
        material: starMat,
        baseBrightness: brightness,
        twinkleSpeed: 2 + Math.random() * 4,
        twinklePhase: Math.random() * Math.PI * 2,
      });
    }
  }

  /**
   * Create moon and sun for day/night cycle
   */
  private createCelestialBodies(): void {
    if (!this.app) return;
    const pc = window.pc;

    // Moon
    this.moon = new pc.Entity("Moon");
    if (this.moon) {
      this.moon.addComponent("model", { type: "sphere" });
      this.moon.setLocalScale(8, 8, 8);
      this.moon.setPosition(60, 80, -50);

      this.moonMaterial = new pc.StandardMaterial();
      if (!this.moonMaterial) throw new Error("Failed to create moon material");
      this.moonMaterial.diffuse = new pc.Color(0.95, 0.95, 0.9);
      this.moonMaterial.emissive = new pc.Color(0.7, 0.75, 0.85);
      this.moonMaterial.useLighting = false;
      this.moonMaterial.update();

      const moonModel = this.moon.model as PCModel;
      if (moonModel && this.moonMaterial) {
        moonModel.material = this.moonMaterial;
      }

      this.app.root.addChild(this.moon);
    }

    // Moon glow (larger, softer sphere behind)
    this.moonGlow = new pc.Entity("MoonGlow");
    this.moonGlow.addComponent("model", { type: "sphere" });
    this.moonGlow.setLocalScale(14, 14, 14);
    this.moonGlow.setPosition(60, 80, -50);

    const glowMat = new pc.StandardMaterial();
    glowMat.emissive = new pc.Color(0.3, 0.35, 0.5);
    glowMat.opacity = 0.25;
    glowMat.blendType = pc.BLEND_ADDITIVE;
    glowMat.useLighting = false;
    glowMat.update();
    (this.moonGlow.model as PCModel).material = glowMat;

    this.app.root.addChild(this.moonGlow);

    // Sun (hidden by default, shown during day)
    this.sun = new pc.Entity("Sun");
    if (this.sun) {
      this.sun.addComponent("model", { type: "sphere" });
      this.sun.setLocalScale(12, 12, 12);
      this.sun.setPosition(80, 100, 60);
      this.sun.enabled = false;

      const sunMat = new pc.StandardMaterial();
      sunMat.emissive = new pc.Color(1, 0.95, 0.7);
      sunMat.useLighting = false;
      sunMat.update();

      const sunModel = this.sun.model as PCModel;
      if (sunModel) {
        sunModel.material = sunMat;
      }

      this.app.root.addChild(this.sun);
    }

    // Sun rays/glow
    this.sunGlow = new pc.Entity("SunGlow");
    if (this.sunGlow) {
      this.sunGlow.addComponent("model", { type: "sphere" });
      this.sunGlow.setLocalScale(25, 25, 25);
      this.sunGlow.setPosition(80, 100, 60);
      this.sunGlow.enabled = false;

      const sunGlowMat = new pc.StandardMaterial();
      sunGlowMat.emissive = new pc.Color(1, 0.8, 0.4);
      sunGlowMat.opacity = 0.2;
      sunGlowMat.blendType = pc.BLEND_ADDITIVE;
      sunGlowMat.useLighting = false;
      sunGlowMat.update();

      const sunGlowModel = this.sunGlow.model as PCModel;
      if (sunGlowModel) {
        sunGlowModel.material = sunGlowMat;
      }

      this.app.root.addChild(this.sunGlow);
    }
  }

  /**
   * Create detailed ground with terrain textures and village square
   */
  private createDetailedGround(): void {
    if (!this.app) return;
    const pc = window.pc;

    // Main ground - varied grass terrain
    const ground = new pc.Entity("Ground");
    ground.addComponent("model", { type: "plane" });

    // Larger ground for better horizon
    const groundSize = this.isLobbyMode ? 600 : 900;
    ground.setLocalScale(groundSize, 1, groundSize);

    const material = new pc.StandardMaterial();
    // Düsterwald: dark forest floor, but visible
    if (this.isLobbyMode) {
      material.diffuse = new pc.Color(0.12, 0.18, 0.12);
    } else {
      material.diffuse = new pc.Color(0.08, 0.1, 0.06);
    }
    material.specular = new pc.Color(0.01, 0.01, 0.01);
    material.shininess = 1;
    material.update();

    (ground.model as PCModel).material = material;
    this.app.root.addChild(ground);

    this.createTerrainUndulations(groundSize);

    // Random grass patches for variation
    const patchCount = this.isLobbyMode ? 40 : 90;
    for (let i = 0; i < patchCount; i++) {
      const patch = new pc.Entity("GrassPatch");
      patch.addComponent("model", { type: "plane" });
      const scale = 5 + Math.random() * 10;
      patch.setLocalScale(scale, 1, scale);

      const angle = Math.random() * Math.PI * 2;
      const dist = Math.random() * (groundSize * 0.4);
      patch.setPosition(
        Math.cos(angle) * dist,
        0.01 + Math.random() * 0.01,
        Math.sin(angle) * dist,
      );
      patch.setEulerAngles(0, Math.random() * 360, 0);

      const patchMat = new pc.StandardMaterial();
      // Düsterwald: very dark, almost invisible patches
      const colorVar = Math.random() * 0.02;
      patchMat.diffuse = new pc.Color(
        0.03 + colorVar,
        0.05 + colorVar,
        0.02 + colorVar,
      );
      patchMat.opacity = 0.7;
      patchMat.blendType = pc.BLEND_NORMAL;
      patchMat.update();
      (patch.model as PCModel).material = patchMat;
      this.app.root.addChild(patch);
    }

    // Create dirt paths/roads for village authenticity
    if (!this.isLobbyMode) {
      this.createVillagePaths();
    }

    // Center village square (cobblestone)
    const centerSquare = new pc.Entity("CenterSquare");
    centerSquare.addComponent("model", { type: "cylinder" });
    const squareSize = this.isLobbyMode ? 10 : 15;
    centerSquare.setLocalScale(squareSize, 0.05, squareSize);
    centerSquare.setPosition(0, 0.03, 0);

    const squareMat = this.getMaterial({
      name: "VillageSquare",
      // Düsterwald: dark, worn cobblestone
      diffuse: new pc.Color(0.12, 0.1, 0.09),
      specular: new pc.Color(0.02, 0.02, 0.02),
    });
    (centerSquare.model as PCModel).material = squareMat;
    this.app.root.addChild(centerSquare);

    // Add decorative stones around the square
    if (!this.isLobbyMode) {
      this.createSquareDecorations();
    }
  }

  private createTerrainUndulations(groundSize: number): void {
    if (!this.app) return;
    const pc = window.pc;

    const hillColors = [
      new pc.Color(0.07, 0.09, 0.05),
      new pc.Color(0.06, 0.08, 0.05),
      new pc.Color(0.08, 0.11, 0.06),
    ];
    const hillMats = hillColors.map((color) => {
      const mat = new pc.StandardMaterial();
      mat.diffuse = color;
      mat.specular = new pc.Color(0.01, 0.01, 0.01);
      mat.shininess = 1;
      mat.update();
      return mat;
    });

    const ridgeMat = new pc.StandardMaterial();
    ridgeMat.diffuse = new pc.Color(0.07, 0.09, 0.05);
    ridgeMat.specular = new pc.Color(0.01, 0.01, 0.01);
    ridgeMat.shininess = 1;
    ridgeMat.update();

    const innerBumpCount = this.isLobbyMode ? 6 : 10;
    for (let i = 0; i < innerBumpCount; i++) {
      const angle = Math.random() * Math.PI * 2;
      const radius = 10 + Math.random() * 12;
      const size = 6 + Math.random() * 8;
      const height = 0.3 + Math.random() * 0.7;

      const bump = new pc.Entity(`Bump-${i}`);
      bump.addComponent("model", { type: "sphere" });
      bump.setLocalScale(size, height, size);
      bump.setPosition(
        Math.cos(angle) * radius,
        height * 0.35,
        Math.sin(angle) * radius,
      );
      (bump.model as PCModel).material =
        hillMats[Math.floor(Math.random() * hillMats.length)];
      this.app.root.addChild(bump);
    }

    const hillCount = this.isLobbyMode ? 10 : 18;
    const hillMinRadius = this.isLobbyMode ? 24 : 32;
    const hillMaxRadius = groundSize * 0.45;
    for (let i = 0; i < hillCount; i++) {
      const angle = Math.random() * Math.PI * 2;
      const radius =
        hillMinRadius + Math.random() * (hillMaxRadius - hillMinRadius);
      const size = this.isLobbyMode
        ? 12 + Math.random() * 18
        : 18 + Math.random() * 28;
      const height = this.isLobbyMode
        ? 1.6 + Math.random() * 3
        : 2.2 + Math.random() * 4.5;

      const hill = new pc.Entity(`Hill-${i}`);
      hill.addComponent("model", { type: "sphere" });
      hill.setLocalScale(size, height, size);
      hill.setPosition(
        Math.cos(angle) * radius,
        height * 0.35,
        Math.sin(angle) * radius,
      );
      hill.setLocalEulerAngles(
        (Math.random() - 0.5) * 6,
        Math.random() * 360,
        (Math.random() - 0.5) * 6,
      );
      (hill.model as PCModel).material =
        hillMats[Math.floor(Math.random() * hillMats.length)];
      this.app.root.addChild(hill);
    }

    const ridgeCount = this.isLobbyMode ? 5 : 8;
    const ridgeMinRadius = this.isLobbyMode ? 18 : 26;
    const ridgeMaxRadius = groundSize * 0.4;
    for (let i = 0; i < ridgeCount; i++) {
      const angle = Math.random() * Math.PI * 2;
      const radius =
        ridgeMinRadius + Math.random() * (ridgeMaxRadius - ridgeMinRadius);
      const length = this.isLobbyMode
        ? 25 + Math.random() * 35
        : 35 + Math.random() * 55;
      const width = 6 + Math.random() * 10;
      const height = 0.6 + Math.random() * 1.6;

      const ridge = new pc.Entity(`Ridge-${i}`);
      ridge.addComponent("model", { type: "box" });
      ridge.setLocalScale(length, height, width);
      ridge.setPosition(
        Math.cos(angle) * radius,
        height * 0.5,
        Math.sin(angle) * radius,
      );
      ridge.setLocalEulerAngles(
        (Math.random() - 0.5) * 4,
        Math.random() * 360,
        (Math.random() - 0.5) * 4,
      );
      (ridge.model as PCModel).material = ridgeMat;
      this.app.root.addChild(ridge);
    }
  }

  /**
   * Create village paths connecting buildings
   */
  private createVillagePaths(): void {
    if (!this.app) return;
    const pc = window.pc;

    const pathPositions = [
      { x: 0, z: 0, scaleX: 2.5, scaleZ: 40, rotation: 0 },
      { x: 0, z: 0, scaleX: 40, scaleZ: 2.5, rotation: 0 },
      { x: -15, z: -12, scaleX: 12, scaleZ: 2, rotation: 25 },
      { x: 15, z: 10, scaleX: 10, scaleZ: 2, rotation: -35 },
      { x: -8, z: 15, scaleX: 8, scaleZ: 2, rotation: 15 },
      { x: 12, z: -10, scaleX: 9, scaleZ: 2, rotation: -20 },
    ];

    pathPositions.forEach((pathData, idx) => {
      const path = new pc.Entity(`Path-${idx}`);
      path.addComponent("model", { type: "box" });
      const scaleX = Math.max(1, pathData.scaleX + (Math.random() - 0.5) * 3);
      const scaleZ = Math.max(1, pathData.scaleZ + (Math.random() - 0.5) * 3);
      const offsetX = (Math.random() - 0.5) * 3;
      const offsetZ = (Math.random() - 0.5) * 3;
      const rotation = pathData.rotation + (Math.random() - 0.5) * 12;
      path.setLocalScale(scaleX, 0.02, scaleZ);
      path.setPosition(pathData.x + offsetX, 0.02, pathData.z + offsetZ);
      path.setLocalEulerAngles(0, rotation, 0);

      const pathMat = new pc.StandardMaterial();
      // Düsterwald: muddy, dark paths
      pathMat.diffuse = new pc.Color(0.08, 0.06, 0.04);
      pathMat.specular = new pc.Color(0.01, 0.01, 0.01);
      pathMat.update();
      const pathModel = path.model as PCModel;
      if (pathModel) {
        pathModel.material = pathMat;
      }

      if (this.app && this.app.root) {
        this.app.root.addChild(path);
      }
    });
  }

  /**
   * Create decorative elements around the village square
   */
  private createSquareDecorations(): void {
    if (!this.app) return;
    const pc = window.pc;

    const decorationCount = 16 + Math.floor(Math.random() * 10);
    for (let i = 0; i < decorationCount; i++) {
      const angle = Math.random() * Math.PI * 2;
      const radius = 8 + Math.random() * 4;

      const deco = new pc.Entity(`Decoration-${i}`);
      deco.addComponent("model", { type: "box" });
      const size = 0.15 + Math.random() * 0.25;
      deco.setLocalScale(size, size * 0.5, size);
      deco.setPosition(
        Math.cos(angle) * radius,
        0.05,
        Math.sin(angle) * radius,
      );
      deco.setLocalEulerAngles(
        Math.random() * 10 - 5,
        Math.random() * 360,
        Math.random() * 10 - 5,
      );

      const decoMat = new pc.StandardMaterial();
      decoMat.diffuse = new pc.Color(0.3, 0.28, 0.25);
      decoMat.update();
      (deco.model as PCModel).material = decoMat;

      this.app.root.addChild(deco);
    }
  }

  /**
   * Create ground plane (legacy method, replaced by createDetailedGround)
   * @deprecated Use createDetailedGround instead
   */
  // @ts-expect-error - Legacy method kept for reference
  private createGround(): void {
    if (!this.app) {
      throw new Error("PlayCanvas application not initialized");
    }

    const pc = window.pc;

    const ground = new pc.Entity("Ground");
    ground.addComponent("model", { type: "plane" });
    ground.setLocalScale(100, 1, 100);
    ground.setLocalPosition(0, 0, 0);

    const groundMat = new pc.StandardMaterial();
    groundMat.diffuse = new pc.Color(0.2, 0.4, 0.25);
    groundMat.specular = new pc.Color(0.05, 0.05, 0.05);
    groundMat.update();
    (ground.model as PCModel).material = groundMat;

    this.app.root.addChild(ground);
  }

  /**
   * Create village buildings
   */
  private createVillageBuildings(): void {
    const innerCount = this.isLobbyMode
      ? 7 + Math.floor(Math.random() * 4)
      : 12 + Math.floor(Math.random() * 6);
    const outerCount = this.isLobbyMode
      ? 4 + Math.floor(Math.random() * 3)
      : 8 + Math.floor(Math.random() * 5);
    const innerOffset = Math.random() * Math.PI * 2;
    const outerOffset = Math.random() * Math.PI * 2;
    const innerStep = (Math.PI * 2) / innerCount;
    const outerStep = (Math.PI * 2) / outerCount;
    let buildingIndex = 0;

    for (let i = 0; i < innerCount; i++) {
      const angle =
        innerOffset + i * innerStep + (Math.random() - 0.5) * innerStep * 0.6;
      const radius =
        (this.isLobbyMode ? 14 : 18) +
        Math.random() * (this.isLobbyMode ? 8 : 12);
      const x = Math.cos(angle) * radius;
      const z = Math.sin(angle) * radius;
      const rot = (-angle * 180) / Math.PI + 90 + (Math.random() - 0.5) * 18;
      const scale = 0.85 + Math.random() * 0.4;
      const typeRoll = Math.random();

      if (typeRoll < 0.5) {
        this.createHouse(x, z, rot, buildingIndex, scale);
      } else if (typeRoll < 0.75) {
        this.createHut(x, z, rot, buildingIndex, scale);
      } else {
        this.createLonghouse(x, z, rot, buildingIndex, scale);
      }
      buildingIndex += 1;
    }

    for (let i = 0; i < outerCount; i++) {
      const angle =
        outerOffset + i * outerStep + (Math.random() - 0.5) * outerStep * 0.7;
      const radius =
        (this.isLobbyMode ? 24 : 32) +
        Math.random() * (this.isLobbyMode ? 10 : 18);
      const x = Math.cos(angle) * radius;
      const z = Math.sin(angle) * radius;
      const rot = (-angle * 180) / Math.PI + 90 + (Math.random() - 0.5) * 25;
      const scale = 0.9 + Math.random() * 0.5;
      const typeRoll = Math.random();

      if (typeRoll < 0.35) {
        this.createBarn(x, z, rot, buildingIndex, scale);
      } else if (typeRoll < 0.6) {
        this.createWatchTower(x, z, rot, buildingIndex, scale);
      } else if (typeRoll < 0.8) {
        this.createHut(x, z, rot, buildingIndex, scale);
      } else {
        this.createLonghouse(x, z, rot, buildingIndex, scale);
      }
      buildingIndex += 1;
    }

    // Church (special building)
    const churchBase = this.isLobbyMode
      ? { x: -10, z: -18 }
      : { x: -14, z: -24 };
    const churchFlipX = Math.random() < 0.5 ? -1 : 1;
    const churchFlipZ = Math.random() < 0.5 ? -1 : 1;
    const churchOffsetX = (Math.random() - 0.5) * 8;
    const churchOffsetZ = (Math.random() - 0.5) * 8;
    this.createChurch(
      churchBase.x * churchFlipX + churchOffsetX,
      churchBase.z * churchFlipZ + churchOffsetZ,
    );

    // Well (near center)
    const wellBase = this.isLobbyMode ? { x: 8, z: 9 } : { x: 12, z: 14 };
    const wellFlipX = Math.random() < 0.5 ? -1 : 1;
    const wellFlipZ = Math.random() < 0.5 ? -1 : 1;
    const wellOffsetX = (Math.random() - 0.5) * 6;
    const wellOffsetZ = (Math.random() - 0.5) * 6;
    this.createWell(
      wellBase.x * wellFlipX + wellOffsetX,
      wellBase.z * wellFlipZ + wellOffsetZ,
    );

    // Create enhanced environment (trees, bushes, rocks)
    this.createEnhancedEnvironment();

    // Campfire in center
    this.createCampfire();
  }

  /**
   * Create enhanced environment with trees, bushes, rocks
   */
  private createEnhancedEnvironment(): void {
    // Trees with more variety and foliage
    const treeCount = this.isLobbyMode ? 30 : 60;
    for (let i = 0; i < treeCount; i++) {
      const angle = Math.random() * Math.PI * 2;
      const radius = this.isLobbyMode
        ? 20 + Math.random() * 20
        : 35 + Math.random() * 45;

      const x = Math.cos(angle) * radius;
      const z = Math.sin(angle) * radius;
      const treeHeight = 4 + Math.random() * 4;

      this.createDetailedTree(x, z, treeHeight);
    }

    // Dense bushes around the perimeter
    const bushCount = 40;
    for (let i = 0; i < bushCount; i++) {
      const angle = Math.random() * Math.PI * 2;
      const radius = 30 + Math.random() * 50;
      this.createBush(Math.cos(angle) * radius, Math.sin(angle) * radius);
    }

    // Rocks
    const rockCount = 30;
    for (let i = 0; i < rockCount; i++) {
      const radius = 10 + Math.random() * 60;
      const angle = Math.random() * Math.PI * 2;
      const rx = Math.cos(angle) * radius;
      const rz = Math.sin(angle) * radius;
      this.createRock(rx, rz);
    }
  }

  /**
   * Create a detailed tree with trunk and foliage
   */
  private createDetailedTree(x: number, z: number, height: number): void {
    if (!this.app) return;
    const pc = window.pc;

    const tree = new pc.Entity("Tree");

    // Trunk
    const trunk = new pc.Entity("Trunk");
    trunk.addComponent("model", { type: "cylinder" });
    trunk.setLocalScale(
      0.5 + Math.random() * 0.3,
      height,
      0.5 + Math.random() * 0.3,
    );
    trunk.setLocalPosition(0, height / 2, 0);
    trunk.setLocalEulerAngles(
      Math.random() * 10 - 5,
      0,
      Math.random() * 10 - 5,
    );

    const trunkMat = new pc.StandardMaterial();
    // Düsterwald: gnarled, almost black bark
    trunkMat.diffuse = new pc.Color(0.1, 0.08, 0.06);
    trunkMat.specular = new pc.Color(0.02, 0.02, 0.02);
    trunkMat.update();
    (trunk.model as PCModel).material = trunkMat;
    tree.addChild(trunk);

    // Foliage clumps - Düsterwald: dark, nearly black-green
    const foliageMat = new pc.StandardMaterial();
    foliageMat.diffuse = new pc.Color(0.02, 0.06 + Math.random() * 0.04, 0.02);
    foliageMat.specular = new pc.Color(0.005, 0.02, 0.005);
    foliageMat.update();

    const layers = 3;
    for (let i = 0; i < layers; i++) {
      const layerY = height * (0.6 + i * 0.2);
      const layerW = (3 - i) * 1.2;
      const clumps = 2 + i + Math.floor(Math.random() * 2);

      for (let j = 0; j < clumps; j++) {
        const clump = new pc.Entity("FoliageClump");
        clump.addComponent("model", { type: "sphere" });
        const size = 1 + Math.random() * 1.5;
        clump.setLocalScale(size, size * 0.7, size);

        const angle = (j / clumps) * Math.PI * 2 + Math.random();
        const dist = layerW * 0.5 + Math.random() * 0.5;

        clump.setLocalPosition(
          Math.cos(angle) * dist,
          layerY + Math.random(),
          Math.sin(angle) * dist,
        );
        (clump.model as PCModel).material = foliageMat;
        tree.addChild(clump);
      }
    }

    tree.setPosition(x, 0, z);
    tree.setLocalEulerAngles(0, Math.random() * 360, 0);
    this.app.root.addChild(tree);
  }

  /**
   * Create a bush
   */
  private createBush(x: number, z: number): void {
    if (!this.app) return;
    const pc = window.pc;

    const bush = new pc.Entity("Bush");

    const bushMat = new pc.StandardMaterial();
    // Düsterwald: dark, thorny-looking bushes
    bushMat.diffuse = new pc.Color(0.04, 0.08 + Math.random() * 0.04, 0.03);
    bushMat.specular = new pc.Color(0.01, 0.02, 0.01);
    bushMat.update();

    const clusterCount = 3 + Math.floor(Math.random() * 3);
    for (let i = 0; i < clusterCount; i++) {
      const clump = new pc.Entity("BushClump");
      clump.addComponent("model", { type: "sphere" });
      const size = 0.5 + Math.random() * 0.8;
      clump.setLocalScale(size, size * 0.8, size);

      const angle = (i / clusterCount) * Math.PI * 2 + Math.random();
      const dist = Math.random() * 0.5;

      clump.setLocalPosition(
        Math.cos(angle) * dist,
        0.4 + Math.random() * 0.2,
        Math.sin(angle) * dist,
      );
      (clump.model as PCModel).material = bushMat;
      bush.addChild(clump);
    }

    bush.setPosition(x, 0, z);
    this.app.root.addChild(bush);
  }

  /**
   * Create a rock
   */
  private createRock(x: number, z: number): void {
    if (!this.app) return;
    const pc = window.pc;

    const rock = new pc.Entity("Rock");
    rock.addComponent("model", { type: "sphere" });

    const size = 0.5 + Math.random() * 1.5;
    rock.setLocalScale(size, size * 0.6, size);

    const rockMat = new pc.StandardMaterial();
    rockMat.diffuse = new pc.Color(0.35, 0.35, 0.38);
    rockMat.specular = new pc.Color(0.05, 0.05, 0.05);
    rockMat.update();
    (rock.model as PCModel).material = rockMat;

    rock.setPosition(x, size * 0.3, z);
    rock.setLocalEulerAngles(
      Math.random() * 360,
      Math.random() * 360,
      Math.random() * 360,
    );

    this.app.root.addChild(rock);
  }

  private createHut(
    x: number,
    z: number,
    rotation: number,
    index: number,
    scale: number = 1,
  ): void {
    if (!this.app) return;
    const pc = window.pc;

    const hut = new pc.Entity(`Hut-${index}`);

    const base = new pc.Entity("HutBase");
    base.addComponent("model", { type: "cylinder" });
    base.setLocalScale(3.2, 1.4, 3.2);
    base.setLocalPosition(0, 0.7, 0);

    const wallMat = new pc.StandardMaterial();
    const wallTint = 0.02 + Math.random() * 0.04;
    wallMat.diffuse = new pc.Color(
      0.22 + wallTint,
      0.18 + wallTint,
      0.14 + wallTint,
    );
    wallMat.specular = new pc.Color(0.03, 0.03, 0.03);
    wallMat.update();
    (base.model as PCModel).material = wallMat;
    hut.addChild(base);

    const roof = new pc.Entity("HutRoof");
    roof.addComponent("model", { type: "cone" });
    roof.setLocalScale(4.1, 2.4, 4.1);
    roof.setLocalPosition(0, 2.4, 0);

    const roofMat = new pc.StandardMaterial();
    const roofTint = (Math.random() - 0.5) * 0.06;
    roofMat.diffuse = new pc.Color(
      0.18 + roofTint,
      0.1 + roofTint * 0.6,
      0.06 + roofTint * 0.4,
    );
    roofMat.update();
    (roof.model as PCModel).material = roofMat;
    hut.addChild(roof);

    const door = new pc.Entity("HutDoor");
    door.addComponent("model", { type: "box" });
    door.setLocalScale(0.9, 1.5, 0.12);
    door.setLocalPosition(0, 0.75, 1.6);
    const doorMat = new pc.StandardMaterial();
    doorMat.diffuse = new pc.Color(0.2, 0.14, 0.08);
    doorMat.update();
    (door.model as PCModel).material = doorMat;
    hut.addChild(door);

    const windowMat = new pc.StandardMaterial();
    windowMat.diffuse = new pc.Color(0.12, 0.1, 0.08);
    windowMat.emissive = new pc.Color(0.35, 0.22, 0.1);
    windowMat.opacity = 0.75;
    windowMat.blendType = pc.BLEND_NORMAL;
    windowMat.update();

    const windowLeft = new pc.Entity("HutWindowL");
    windowLeft.addComponent("model", { type: "box" });
    windowLeft.setLocalScale(0.5, 0.5, 0.08);
    windowLeft.setLocalPosition(-0.9, 1.0, 1.45);
    (windowLeft.model as PCModel).material = windowMat;
    hut.addChild(windowLeft);

    const windowRight = new pc.Entity("HutWindowR");
    windowRight.addComponent("model", { type: "box" });
    windowRight.setLocalScale(0.5, 0.5, 0.08);
    windowRight.setLocalPosition(0.9, 1.0, 1.45);
    (windowRight.model as PCModel).material = windowMat;
    hut.addChild(windowRight);

    const chimney = new pc.Entity("HutChimney");
    chimney.addComponent("model", { type: "box" });
    chimney.setLocalScale(0.35, 1.1, 0.35);
    chimney.setLocalPosition(1.1, 2.6, -0.4);
    const chimneyMat = new pc.StandardMaterial();
    chimneyMat.diffuse = new pc.Color(0.14, 0.14, 0.16);
    chimneyMat.update();
    (chimney.model as PCModel).material = chimneyMat;
    hut.addChild(chimney);

    hut.setLocalScale(scale, scale, scale);
    hut.setPosition(x, 0, z);
    hut.setEulerAngles(0, rotation, 0);
    this.app.root.addChild(hut);
    this.buildings.push(hut);
  }

  private createLonghouse(
    x: number,
    z: number,
    rotation: number,
    index: number,
    scale: number = 1,
  ): void {
    if (!this.app) return;
    const pc = window.pc;

    const longhouse = new pc.Entity(`Longhouse-${index}`);

    const base = new pc.Entity("LonghouseBase");
    base.addComponent("model", { type: "box" });
    base.setLocalScale(7, 2.0, 3.6);
    base.setLocalPosition(0, 1.0, 0);

    const baseMat = new pc.StandardMaterial();
    const baseTint = 0.02 + Math.random() * 0.04;
    baseMat.diffuse = new pc.Color(
      0.2 + baseTint,
      0.17 + baseTint,
      0.13 + baseTint,
    );
    baseMat.specular = new pc.Color(0.03, 0.03, 0.03);
    baseMat.update();
    (base.model as PCModel).material = baseMat;
    longhouse.addChild(base);

    const roofAngle = 22 + Math.random() * 12;
    const houseWidth = 7.2;
    const houseDepth = 3.8;
    const roofOverhang = 0.6;
    const roofBaseY = 2.2;

    const roofRad = (roofAngle * Math.PI) / 180;
    const halfWidth = houseWidth / 2 + roofOverhang;
    const roofPanelWidth = halfWidth / Math.cos(roofRad);
    const roofPeakHeight = halfWidth * Math.tan(roofRad);
    const roofLength = houseDepth + roofOverhang * 2;

    const roofMat = new pc.StandardMaterial();
    const roofTint = (Math.random() - 0.5) * 0.06;
    roofMat.diffuse = new pc.Color(
      0.17 + roofTint,
      0.09 + roofTint * 0.6,
      0.06 + roofTint * 0.4,
    );
    roofMat.update();

    const roofLeft = new pc.Entity("LonghouseRoofLeft");
    roofLeft.addComponent("model", { type: "box" });
    roofLeft.setLocalScale(roofPanelWidth, 0.14, roofLength);
    const panelCenterX = -halfWidth / 2;
    const panelCenterY = roofBaseY + roofPeakHeight / 2;
    roofLeft.setLocalPosition(panelCenterX, panelCenterY, 0);
    roofLeft.setLocalEulerAngles(0, 0, roofAngle);
    (roofLeft.model as PCModel).material = roofMat;
    longhouse.addChild(roofLeft);

    const roofRight = new pc.Entity("LonghouseRoofRight");
    roofRight.addComponent("model", { type: "box" });
    roofRight.setLocalScale(roofPanelWidth, 0.14, roofLength);
    roofRight.setLocalPosition(halfWidth / 2, panelCenterY, 0);
    roofRight.setLocalEulerAngles(0, 0, -roofAngle);
    (roofRight.model as PCModel).material = roofMat;
    longhouse.addChild(roofRight);

    const door = new pc.Entity("LonghouseDoor");
    door.addComponent("model", { type: "box" });
    door.setLocalScale(1.2, 1.8, 0.12);
    door.setLocalPosition(0, 0.9, 1.9);
    const doorMat = new pc.StandardMaterial();
    doorMat.diffuse = new pc.Color(0.2, 0.14, 0.08);
    doorMat.update();
    (door.model as PCModel).material = doorMat;
    longhouse.addChild(door);

    const windowMat = new pc.StandardMaterial();
    windowMat.diffuse = new pc.Color(0.12, 0.1, 0.08);
    windowMat.emissive = new pc.Color(0.35, 0.22, 0.1);
    windowMat.opacity = 0.7;
    windowMat.blendType = pc.BLEND_NORMAL;
    windowMat.update();

    for (let i = 0; i < 3; i++) {
      const window = new pc.Entity(`LonghouseWindow-${i}`);
      window.addComponent("model", { type: "box" });
      window.setLocalScale(0.7, 0.6, 0.08);
      window.setLocalPosition(-2.4 + i * 2.4, 1.0, 1.9);
      (window.model as PCModel).material = windowMat;
      longhouse.addChild(window);
    }

    longhouse.setLocalScale(scale, scale, scale);
    longhouse.setPosition(x, 0, z);
    longhouse.setEulerAngles(0, rotation, 0);
    this.app.root.addChild(longhouse);
    this.buildings.push(longhouse);
  }

  private createBarn(
    x: number,
    z: number,
    rotation: number,
    index: number,
    scale: number = 1,
  ): void {
    if (!this.app) return;
    const pc = window.pc;

    const barn = new pc.Entity(`Barn-${index}`);

    const base = new pc.Entity("BarnBase");
    base.addComponent("model", { type: "box" });
    base.setLocalScale(6.6, 3.0, 4.4);
    base.setLocalPosition(0, 1.5, 0);

    const baseMat = new pc.StandardMaterial();
    const baseTint = 0.02 + Math.random() * 0.05;
    baseMat.diffuse = new pc.Color(
      0.23 + baseTint,
      0.18 + baseTint,
      0.13 + baseTint,
    );
    baseMat.specular = new pc.Color(0.03, 0.03, 0.03);
    baseMat.update();
    (base.model as PCModel).material = baseMat;
    barn.addChild(base);

    const roofAngle = 28 + Math.random() * 10;
    const barnWidth = 6.9;
    const barnDepth = 4.6;
    const roofOverhang = 0.7;
    const roofBaseY = 3.2;

    const roofRad = (roofAngle * Math.PI) / 180;
    const halfWidth = barnWidth / 2 + roofOverhang;
    const roofPanelWidth = halfWidth / Math.cos(roofRad);
    const roofPeakHeight = halfWidth * Math.tan(roofRad);
    const roofLength = barnDepth + roofOverhang * 2;

    const roofMat = new pc.StandardMaterial();
    const roofTint = (Math.random() - 0.5) * 0.06;
    roofMat.diffuse = new pc.Color(
      0.16 + roofTint,
      0.09 + roofTint * 0.6,
      0.05 + roofTint * 0.4,
    );
    roofMat.update();

    const roofLeft = new pc.Entity("BarnRoofLeft");
    roofLeft.addComponent("model", { type: "box" });
    roofLeft.setLocalScale(roofPanelWidth, 0.16, roofLength);
    const panelCenterX = -halfWidth / 2;
    const panelCenterY = roofBaseY + roofPeakHeight / 2;
    roofLeft.setLocalPosition(panelCenterX, panelCenterY, 0);
    roofLeft.setLocalEulerAngles(0, 0, roofAngle);
    (roofLeft.model as PCModel).material = roofMat;
    barn.addChild(roofLeft);

    const roofRight = new pc.Entity("BarnRoofRight");
    roofRight.addComponent("model", { type: "box" });
    roofRight.setLocalScale(roofPanelWidth, 0.16, roofLength);
    roofRight.setLocalPosition(halfWidth / 2, panelCenterY, 0);
    roofRight.setLocalEulerAngles(0, 0, -roofAngle);
    (roofRight.model as PCModel).material = roofMat;
    barn.addChild(roofRight);

    const barnDoor = new pc.Entity("BarnDoor");
    barnDoor.addComponent("model", { type: "box" });
    barnDoor.setLocalScale(2.4, 2.2, 0.14);
    barnDoor.setLocalPosition(0, 1.1, 2.25);
    const doorMat = new pc.StandardMaterial();
    doorMat.diffuse = new pc.Color(0.2, 0.14, 0.08);
    doorMat.update();
    (barnDoor.model as PCModel).material = doorMat;
    barn.addChild(barnDoor);

    const loft = new pc.Entity("BarnLoftWindow");
    loft.addComponent("model", { type: "box" });
    loft.setLocalScale(1.2, 0.8, 0.1);
    loft.setLocalPosition(0, 2.4, 2.26);
    const loftMat = new pc.StandardMaterial();
    loftMat.diffuse = new pc.Color(0.12, 0.1, 0.08);
    loftMat.emissive = new pc.Color(0.3, 0.2, 0.1);
    loftMat.opacity = 0.6;
    loftMat.blendType = pc.BLEND_NORMAL;
    loftMat.update();
    (loft.model as PCModel).material = loftMat;
    barn.addChild(loft);

    barn.setLocalScale(scale, scale, scale);
    barn.setPosition(x, 0, z);
    barn.setEulerAngles(0, rotation, 0);
    this.app.root.addChild(barn);
    this.buildings.push(barn);
  }

  private createWatchTower(
    x: number,
    z: number,
    rotation: number,
    index: number,
    scale: number = 1,
  ): void {
    if (!this.app) return;
    const pc = window.pc;

    const tower = new pc.Entity(`WatchTower-${index}`);

    const base = new pc.Entity("TowerBase");
    base.addComponent("model", { type: "box" });
    base.setLocalScale(2.6, 3.6, 2.6);
    base.setLocalPosition(0, 1.8, 0);

    const baseMat = new pc.StandardMaterial();
    baseMat.diffuse = new pc.Color(0.18, 0.14, 0.1);
    baseMat.specular = new pc.Color(0.03, 0.03, 0.03);
    baseMat.update();
    (base.model as PCModel).material = baseMat;
    tower.addChild(base);

    const mid = new pc.Entity("TowerMid");
    mid.addComponent("model", { type: "box" });
    mid.setLocalScale(2.1, 3.0, 2.1);
    mid.setLocalPosition(0, 4.8, 0);
    const midMat = new pc.StandardMaterial();
    midMat.diffuse = new pc.Color(0.16, 0.12, 0.08);
    midMat.specular = new pc.Color(0.03, 0.03, 0.03);
    midMat.update();
    (mid.model as PCModel).material = midMat;
    tower.addChild(mid);

    const platform = new pc.Entity("TowerPlatform");
    platform.addComponent("model", { type: "box" });
    platform.setLocalScale(3.4, 0.6, 3.4);
    platform.setLocalPosition(0, 6.6, 0);
    const platformMat = new pc.StandardMaterial();
    platformMat.diffuse = new pc.Color(0.2, 0.15, 0.1);
    platformMat.update();
    (platform.model as PCModel).material = platformMat;
    tower.addChild(platform);

    const roof = new pc.Entity("TowerRoof");
    roof.addComponent("model", { type: "cone" });
    roof.setLocalScale(3.2, 2.4, 3.2);
    roof.setLocalPosition(0, 8.0, 0);
    const roofMat = new pc.StandardMaterial();
    roofMat.diffuse = new pc.Color(0.15, 0.08, 0.05);
    roofMat.update();
    (roof.model as PCModel).material = roofMat;
    tower.addChild(roof);

    const windowMat = new pc.StandardMaterial();
    windowMat.diffuse = new pc.Color(0.12, 0.1, 0.08);
    windowMat.emissive = new pc.Color(0.28, 0.2, 0.1);
    windowMat.opacity = 0.6;
    windowMat.blendType = pc.BLEND_NORMAL;
    windowMat.update();

    const towerWindow = new pc.Entity("TowerWindow");
    towerWindow.addComponent("model", { type: "box" });
    towerWindow.setLocalScale(0.5, 0.5, 0.08);
    towerWindow.setLocalPosition(0, 5.2, 1.08);
    (towerWindow.model as PCModel).material = windowMat;
    tower.addChild(towerWindow);

    tower.setLocalScale(scale, scale, scale);
    tower.setPosition(x, 0, z);
    tower.setEulerAngles(0, rotation, 0);
    this.app.root.addChild(tower);
    this.buildings.push(tower);
  }

  /**
   * Create a house
   */
  private createHouse(
    x: number,
    z: number,
    rotation: number,
    index: number,
    scale: number = 1,
  ): void {
    if (!this.app) return;
    const pc = window.pc;

    const house = new pc.Entity(`House-${index}`);

    // Stone base
    const stoneBase = new pc.Entity("StoneBase");
    stoneBase.addComponent("model", { type: "box" });
    stoneBase.setLocalScale(4.2, 1.5, 5.2);
    stoneBase.setLocalPosition(0, 0.75, 0);

    const stoneMat = new pc.StandardMaterial();
    // Düsterwald: dark, mossy stone
    stoneMat.diffuse = new pc.Color(0.18, 0.18, 0.2);
    stoneMat.specular = new pc.Color(0.04, 0.04, 0.04);
    stoneMat.shininess = 3;
    stoneMat.update();
    (stoneBase.model as PCModel).material = stoneMat;
    house.addChild(stoneBase);

    // Upper floor - Düsterwald: weathered, dark timber houses
    const upperFloor = new pc.Entity("UpperFloor");
    upperFloor.addComponent("model", { type: "box" });
    upperFloor.setLocalScale(4, 2, 5);
    upperFloor.setLocalPosition(0, 2.5, 0);

    const plasterMat = new pc.StandardMaterial();
    const hue = 0.02 + Math.random() * 0.04;
    plasterMat.diffuse = new pc.Color(0.25 + hue, 0.22 + hue, 0.18 + hue);
    plasterMat.update();
    (upperFloor.model as PCModel).material = plasterMat;
    house.addChild(upperFloor);

    // Timber beams (vertical)
    for (let i = 0; i < 5; i++) {
      const beam = new pc.Entity(`Beam-V-${i}`);
      beam.addComponent("model", { type: "box" });
      beam.setLocalScale(0.15, 2, 0.15);
      beam.setLocalPosition(-1.8 + i * 0.9, 2.5, 2.55);

      const beamMat = new pc.StandardMaterial();
      beamMat.diffuse = new pc.Color(0.25, 0.15, 0.08);
      beamMat.update();
      (beam.model as PCModel).material = beamMat;
      house.addChild(beam);
    }

    // Roof
    const roofAngle = 28 + Math.random() * 18;
    const houseWidth = 4.2;
    const houseDepth = 5.2;
    const roofOverhang = 0.5;
    const roofBaseY = 3.5;

    const roofRad = (roofAngle * Math.PI) / 180;
    const halfWidth = houseWidth / 2 + roofOverhang;
    const roofPanelWidth = halfWidth / Math.cos(roofRad);
    const roofPeakHeight = halfWidth * Math.tan(roofRad);
    const roofLength = houseDepth + roofOverhang * 2;

    const roofMat = new pc.StandardMaterial();
    // Düsterwald: dark, weathered thatch/wood
    const roofShift = (Math.random() - 0.5) * 0.06;
    roofMat.diffuse = new pc.Color(
      0.18 + roofShift,
      0.1 + roofShift * 0.6,
      0.06 + roofShift * 0.4,
    );
    roofMat.update();

    const roofLeft = new pc.Entity("RoofLeft");
    roofLeft.addComponent("model", { type: "box" });
    roofLeft.setLocalScale(roofPanelWidth, 0.12, roofLength);
    const panelCenterX = -halfWidth / 2;
    const panelCenterY = roofBaseY + roofPeakHeight / 2;
    roofLeft.setLocalPosition(panelCenterX, panelCenterY, 0);
    roofLeft.setLocalEulerAngles(0, 0, roofAngle);
    (roofLeft.model as PCModel).material = roofMat;
    house.addChild(roofLeft);

    const roofRight = new pc.Entity("RoofRight");
    roofRight.addComponent("model", { type: "box" });
    roofRight.setLocalScale(roofPanelWidth, 0.12, roofLength);
    roofRight.setLocalPosition(halfWidth / 2, panelCenterY, 0);
    roofRight.setLocalEulerAngles(0, 0, -roofAngle);
    (roofRight.model as PCModel).material = roofMat;
    house.addChild(roofRight);

    // Door
    const door = new pc.Entity("Door");
    door.addComponent("model", { type: "box" });
    door.setLocalScale(1, 1.8, 0.1);
    door.setLocalPosition(0, 0.9, 2.65);

    const doorMat = new pc.StandardMaterial();
    doorMat.diffuse = new pc.Color(0.2, 0.15, 0.08);
    doorMat.update();
    (door.model as PCModel).material = doorMat;
    house.addChild(door);

    // Windows
    const windowPositions = [
      { x: -1.2, y: 2.5, z: 2.6 },
      { x: 1.2, y: 2.5, z: 2.6 },
      { x: -1.2, y: 0.9, z: 2.6 },
    ];

    windowPositions.forEach((pos, idx) => {
      const window = new pc.Entity(`Window-${idx}`);
      window.addComponent("model", { type: "box" });
      window.setLocalScale(0.7, 0.7, 0.08);
      window.setLocalPosition(pos.x, pos.y, pos.z);

      const windowMat = new pc.StandardMaterial();
      // Düsterwald: dim candlelight glow through grimy glass
      windowMat.diffuse = new pc.Color(0.15, 0.12, 0.1);
      windowMat.emissive = new pc.Color(0.4, 0.25, 0.1);
      windowMat.opacity = 0.7;
      windowMat.blendType = pc.BLEND_NORMAL;
      windowMat.update();
      (window.model as PCModel).material = windowMat;
      house.addChild(window);
    });

    // Add fence and garden
    this.createHouseFence(house);
    this.createGardenPatch(house);

    house.setLocalScale(scale, scale, scale);
    house.setPosition(x, 0, z);
    house.setEulerAngles(0, rotation, 0);
    this.app.root.addChild(house);
    this.buildings.push(house);

    // Add fence and garden patch
    this.createHouseFence(house);
    this.createGardenPatch(house);
  }

  /**
   * Create wooden fence around house
   */
  private createHouseFence(house: PCEntity): void {
    if (!this.app) return;

    const fenceMat = this.getMaterial({
      name: "WoodenFence",
      diffuse: new window.pc.Color(0.3, 0.22, 0.15),
      shininess: 3,
    });

    // Fence posts around house perimeter
    const fenceDistance = 4;
    const postPositions = [
      { x: -fenceDistance, z: -3 },
      { x: -fenceDistance, z: 0 },
      { x: -fenceDistance, z: 3 },
      { x: fenceDistance, z: -3 },
      { x: fenceDistance, z: 0 },
      { x: fenceDistance, z: 3 },
      { x: -3, z: -fenceDistance },
      { x: 0, z: -fenceDistance },
      { x: 3, z: -fenceDistance },
      { x: -3, z: fenceDistance },
      { x: 3, z: fenceDistance },
    ];

    const pc = window.pc;
    postPositions.forEach((pos, idx) => {
      const post = new pc.Entity(`FencePost-${idx}`);
      post.addComponent("model", { type: "box" });
      post.setLocalScale(0.12, 0.8, 0.12);
      post.setLocalPosition(pos.x, 0.4, pos.z);
      (post.model as PCModel).material = fenceMat;
      house.addChild(post);
    });

    // Horizontal fence rails
    const railHeight = [0.3, 0.6];
    railHeight.forEach((height, idx) => {
      // Left side
      const railL = new pc.Entity(`FenceRail-L-${idx}`);
      railL.addComponent("model", { type: "box" });
      railL.setLocalScale(0.08, 0.08, 6.5);
      railL.setLocalPosition(-fenceDistance, height, 0);
      (railL.model as PCModel).material = fenceMat;
      house.addChild(railL);

      // Right side
      const railR = new pc.Entity(`FenceRail-R-${idx}`);
      railR.addComponent("model", { type: "box" });
      railR.setLocalScale(0.08, 0.08, 6.5);
      railR.setLocalPosition(fenceDistance, height, 0);
      (railR.model as PCModel).material = fenceMat;
      house.addChild(railR);

      // Back side
      const railB = new pc.Entity(`FenceRail-B-${idx}`);
      railB.addComponent("model", { type: "box" });
      railB.setLocalScale(6.5, 0.08, 0.08);
      railB.setLocalPosition(0, height, -fenceDistance);
      (railB.model as PCModel).material = fenceMat;
      house.addChild(railB);

      // Front side (with gate opening)
      const railFL = new pc.Entity(`FenceRail-FL-${idx}`);
      railFL.addComponent("model", { type: "box" });
      railFL.setLocalScale(2, 0.08, 0.08);
      railFL.setLocalPosition(-2.5, height, fenceDistance);
      (railFL.model as PCModel).material = fenceMat;
      house.addChild(railFL);

      const railFR = new pc.Entity(`FenceRail-FR-${idx}`);
      railFR.addComponent("model", { type: "box" });
      railFR.setLocalScale(2, 0.08, 0.08);
      railFR.setLocalPosition(2.5, height, fenceDistance);
      (railFR.model as PCModel).material = fenceMat;
      house.addChild(railFR);
    });
  }

  /**
   * Create a small garden patch next to house
   */
  private createGardenPatch(house: PCEntity): void {
    if (!this.app) return;
    const pc = window.pc;

    const gardenMat = this.getMaterial({
      name: "GardenSoil",
      diffuse: new pc.Color(0.2, 0.15, 0.1),
      shininess: 1,
    });

    const garden = new pc.Entity("Garden");
    garden.addComponent("model", { type: "box" });
    garden.setLocalScale(2, 0.05, 2);
    garden.setLocalPosition(-3, 0.025, -3);
    (garden.model as PCModel).material = gardenMat;
    house.addChild(garden);

    // Add some small plants/crops
    for (let i = 0; i < 4; i++) {
      const plant = new pc.Entity(`Plant-${i}`);
      plant.addComponent("model", { type: "box" });
      plant.setLocalScale(0.15, 0.3, 0.15);
      plant.setLocalPosition(
        -3.5 + (i % 2) * 0.8,
        0.15,
        -3.5 + Math.floor(i / 2) * 0.8,
      );

      const plantMat = this.getMaterial({
        name: `Plant-${i % 2}`,
        diffuse: new pc.Color(0.1, 0.3 + (i % 2) * 0.1, 0.1),
        shininess: 5,
      });
      (plant.model as PCModel).material = plantMat;
      house.addChild(plant);
    }
  }

  /**
   * Create church
   */
  private createChurch(x: number, z: number): void {
    if (!this.app) return;
    const pc = window.pc;

    const church = new pc.Entity("Church");

    // Main base
    const base = new pc.Entity("Base");
    base.addComponent("model", { type: "box" });
    base.setLocalScale(8, 6, 10);
    base.setLocalPosition(0, 3, 0);

    const stoneMat = new pc.StandardMaterial();
    stoneMat.diffuse = new pc.Color(0.22, 0.22, 0.25);
    stoneMat.specular = new pc.Color(0.1, 0.1, 0.1);
    stoneMat.shininess = 5;
    stoneMat.update();
    (base.model as PCModel).material = stoneMat;
    church.addChild(base);

    // Roof
    const churchRoofAngle = 35;
    const churchWidth = 8;
    const churchDepth = 10;
    const churchRoofOverhang = 0.5;
    const churchRoofBaseY = 6;

    const churchRoofRad = (churchRoofAngle * Math.PI) / 180;
    const churchHalfWidth = churchWidth / 2 + churchRoofOverhang;
    const churchRoofPanelWidth = churchHalfWidth / Math.cos(churchRoofRad);
    const churchRoofPeakHeight = churchHalfWidth * Math.tan(churchRoofRad);
    const churchRoofLength = churchDepth + churchRoofOverhang * 2;

    const roofMat = new pc.StandardMaterial();
    roofMat.diffuse = new pc.Color(0.28, 0.12, 0.08);
    roofMat.update();

    const roofLeft = new pc.Entity("RoofLeft");
    roofLeft.addComponent("model", { type: "box" });
    roofLeft.setLocalScale(churchRoofPanelWidth, 0.2, churchRoofLength);
    const churchPanelCenterX = -churchHalfWidth / 2;
    const churchPanelCenterY = churchRoofBaseY + churchRoofPeakHeight / 2;
    roofLeft.setLocalPosition(churchPanelCenterX, churchPanelCenterY, 0);
    roofLeft.setLocalEulerAngles(0, 0, churchRoofAngle);
    (roofLeft.model as PCModel).material = roofMat;
    church.addChild(roofLeft);

    const roofRight = new pc.Entity("RoofRight");
    roofRight.addComponent("model", { type: "box" });
    roofRight.setLocalScale(churchRoofPanelWidth, 0.2, churchRoofLength);
    roofRight.setLocalPosition(churchHalfWidth / 2, churchPanelCenterY, 0);
    roofRight.setLocalEulerAngles(0, 0, -churchRoofAngle);
    (roofRight.model as PCModel).material = roofMat;
    church.addChild(roofRight);

    // Bell tower
    const tower = new pc.Entity("Tower");
    tower.addComponent("model", { type: "box" });
    tower.setLocalScale(2.5, 8, 2.5);
    tower.setLocalPosition(0, 7, -3.5);
    (tower.model as PCModel).material = stoneMat;
    church.addChild(tower);

    // Tower windows
    const towerWindowMat = new pc.StandardMaterial();
    towerWindowMat.diffuse = new pc.Color(0.2, 0.2, 0.3);
    towerWindowMat.opacity = 0.6;
    towerWindowMat.blendType = pc.BLEND_NORMAL;
    towerWindowMat.update();

    for (let i = 0; i < 4; i++) {
      const window = new pc.Entity(`TowerWindow-${i}`);
      window.addComponent("model", { type: "box" });
      window.setLocalScale(0.6, 1.2, 0.1);
      const angle = (i / 4) * Math.PI * 2;
      const windowX = Math.sin(angle) * 1.3;
      const windowZ = -3.5 + Math.cos(angle) * 1.3;
      window.setLocalPosition(windowX, 9, windowZ);
      window.setLocalEulerAngles(0, i * 90, 0);
      (window.model as PCModel).material = towerWindowMat;
      church.addChild(window);
    }

    // Spire (tower roof)
    const spire = new pc.Entity("Spire");
    spire.addComponent("model", { type: "cone" });
    spire.setLocalScale(2, 4, 2);
    spire.setLocalPosition(0, 12.5, -3.5);

    const spireMat = new pc.StandardMaterial();
    spireMat.diffuse = new pc.Color(0.25, 0.35, 0.25);
    spireMat.shininess = 40;
    spireMat.update();
    (spire.model as PCModel).material = spireMat;
    church.addChild(spire);

    // Cross on top
    const crossV = new pc.Entity("CrossVertical");
    crossV.addComponent("model", { type: "box" });
    crossV.setLocalScale(0.15, 1.2, 0.15);
    crossV.setLocalPosition(0, 14.6, -3.5);

    const crossMat = new pc.StandardMaterial();
    // Düsterwald: tarnished, weathered
    crossMat.diffuse = new pc.Color(0.35, 0.3, 0.15);
    crossMat.emissive = new pc.Color(0.12, 0.1, 0.05);
    crossMat.shininess = 20;
    crossMat.update();
    (crossV.model as PCModel).material = crossMat;
    church.addChild(crossV);

    const crossH = new pc.Entity("CrossHorizontal");
    crossH.addComponent("model", { type: "box" });
    crossH.setLocalScale(0.6, 0.15, 0.15);
    crossH.setLocalPosition(0, 14.3, -3.5);
    (crossH.model as PCModel).material = crossMat;
    church.addChild(crossH);

    // Main entrance
    const entrance = new pc.Entity("Entrance");
    entrance.addComponent("model", { type: "box" });
    entrance.setLocalScale(2.5, 3.5, 0.2);
    entrance.setLocalPosition(0, 1.75, 5.1);

    const doorMat = new pc.StandardMaterial();
    doorMat.diffuse = new pc.Color(0.15, 0.1, 0.05);
    doorMat.update();
    (entrance.model as PCModel).material = doorMat;
    church.addChild(entrance);

    church.setPosition(x, 0, z);
    this.app.root.addChild(church);
    this.buildings.push(church);
  }

  /**
   * Create well
   */
  private createWell(x: number, z: number): void {
    if (!this.app) return;
    const pc = window.pc;

    const well = new pc.Entity("Well");

    // Base
    const base = new pc.Entity("Base");
    base.addComponent("model", { type: "cylinder" });
    base.setLocalScale(1.5, 1, 1.5);
    base.setLocalPosition(0, 0.5, 0);

    const baseMat = new pc.StandardMaterial();
    // Düsterwald: mossy, dark stone
    baseMat.diffuse = new pc.Color(0.15, 0.16, 0.14);
    baseMat.update();
    (base.model as PCModel).material = baseMat;
    well.addChild(base);

    // Posts
    for (let i = 0; i < 2; i++) {
      const post = new pc.Entity("Post");
      post.addComponent("model", { type: "cylinder" });
      post.setLocalScale(0.1, 2, 0.1);
      post.setLocalPosition(i === 0 ? -1 : 1, 2, 0);

      const postMat = new pc.StandardMaterial();
      postMat.diffuse = new pc.Color(0.3, 0.2, 0.1);
      postMat.update();
      (post.model as PCModel).material = postMat;
      well.addChild(post);
    }

    // Roof
    const roof = new pc.Entity("Roof");
    roof.addComponent("model", { type: "cone" });
    roof.setLocalScale(2, 1.2, 2);
    roof.setLocalPosition(0, 3.5, 0);

    const roofMat = new pc.StandardMaterial();
    // Düsterwald: rotting wood
    roofMat.diffuse = new pc.Color(0.12, 0.08, 0.05);
    roofMat.update();
    (roof.model as PCModel).material = roofMat;
    well.addChild(roof);

    well.setPosition(x, 0, z);
    this.app.root.addChild(well);
    this.buildings.push(well);
  }

  /**
   * Create campfire with animated flames
   */
  /**
   * Create enhanced campfire with animated flames and particle effects
   */
  private createCampfire(): void {
    if (!this.app) return;
    const pc = window.pc;

    // Main fire light with warmer, flickering color
    this.fireLight = new pc.Entity("FireLight");
    if (!this.fireLight) throw new Error("Failed to create fire light");
    this.fireLight.addComponent("light", {
      type: "point",
      color: new pc.Color(1, 0.4, 0.1),
      intensity: 4,
      range: 25,
      castShadows: true,
    });
    this.fireLight.setPosition(0, 1.2, 0);
    this.app.root.addChild(this.fireLight);

    // Core heat light (intense yellow)
    const coreLight = new pc.Entity("FireCoreLight");
    coreLight.addComponent("light", {
      type: "point",
      color: new pc.Color(1, 0.8, 0.2),
      intensity: 1.5,
      range: 5,
      castShadows: false,
    });
    coreLight.setPosition(0, 0.5, 0);
    this.app.root.addChild(coreLight);

    // Stone ring - more irregular
    for (let i = 0; i < 12; i++) {
      const angle = (i / 12) * Math.PI * 2 + Math.random() * 0.2;
      const stone = new pc.Entity("Stone");
      stone.addComponent("model", { type: "sphere" });
      stone.setLocalScale(
        0.3 + Math.random() * 0.2,
        0.25 + Math.random() * 0.15,
        0.3 + Math.random() * 0.2,
      );
      const dist = 1.4 + Math.random() * 0.2;
      stone.setLocalPosition(
        Math.cos(angle) * dist,
        0.1,
        Math.sin(angle) * dist,
      );

      const stoneMat = this.getMaterial({
        name: "CampfireStone",
        diffuse: new pc.Color(0.25, 0.25, 0.3),
      });
      (stone.model as PCModel).material = stoneMat;
      this.app.root.addChild(stone);
    }

    // Crossed logs (teepee style)
    const logMat = this.getMaterial({
      name: "BurntLog",
      diffuse: new pc.Color(0.15, 0.1, 0.05),
      emissive: new pc.Color(0.2, 0.05, 0), // Glowing embers
    });

    for (let i = 0; i < 4; i++) {
      const log = new pc.Entity("Log");
      log.addComponent("model", { type: "cylinder" });
      log.setLocalScale(0.25, 1.6, 0.25);

      const angle = (i / 4) * Math.PI * 2;
      log.setLocalPosition(Math.sin(angle) * 0.6, 0.6, Math.cos(angle) * 0.6);
      log.lookAt(0, 1.2, 0);
      log.rotateLocal(90, 0, 0);

      (log.model as PCModel).material = logMat;
      this.app.root.addChild(log);
    }

    // Initialize particle system
    this.fireParticles = [];
  }

  /**
   * Spawn fire particles (flames, smoke, embers)
   */
  private spawnFireParticles(dt: number): void {
    if (!this.app) return;

    const maxParticles = 60;
    if (this.fireParticles.length >= maxParticles) return;

    // Spawn rate based on deltaTime
    const spawnRate = 0.05;
    const spawnCount = Math.floor(dt / spawnRate);

    for (let i = 0; i < spawnCount; i++) {
      if (this.fireParticles.length >= maxParticles) break;

      const type = Math.random();
      let particle;

      if (type < 0.6) {
        particle = this.createParticle("flame");
      } else if (type < 0.9) {
        particle = this.createParticle("smoke");
      } else {
        particle = this.createParticle("ember");
      }

      this.fireParticles.push(particle);
      this.app.root.addChild(particle.entity);
    }
  }

  /**
   * Create a single particle entity
   */
  private createParticle(type: "flame" | "smoke" | "ember"): {
    entity: PCEntity;
    type: string;
    life: number;
    maxLife: number;
    velocity: PCVec3;
    startScale: number;
    endScale: number;
    startColor: PCColor;
    endColor: PCColor;
  } {
    const pc = window.pc;
    const entity = new pc.Entity("Particle");
    entity.addComponent("model", { type: "plane" });

    const particle: {
      entity: PCEntity;
      type: string;
      life: number;
      maxLife: number;
      velocity: PCVec3;
      startScale: number;
      endScale: number;
      startColor: PCColor;
      endColor: PCColor;
    } = {
      entity,
      type,
      life: 0,
      maxLife: 0,
      velocity: new pc.Vec3(),
      startScale: 1,
      endScale: 0,
      startColor: new pc.Color(1, 1, 1),
      endColor: new pc.Color(0.5, 0.5, 0.5),
    };

    if (type === "flame") {
      particle.maxLife = 0.8 + Math.random() * 0.6;
      particle.startScale = 0.5 + Math.random() * 0.3;
      particle.endScale = 0.1;
      particle.startColor = new pc.Color(1, 0.8, 0.2);
      particle.endColor = new pc.Color(1, 0.2, 0);
      particle.velocity.set(
        (Math.random() - 0.5) * 0.5,
        1.5 + Math.random(),
        (Math.random() - 0.5) * 0.5,
      );
      entity.setPosition(
        (Math.random() - 0.5) * 0.5,
        0.2,
        (Math.random() - 0.5) * 0.5,
      );

      const mat = this.getMaterial({
        name: "FlameMat",
        emissive: new pc.Color(1, 0.8, 0.2),
        opacity: 0.8,
      });
      const flameModel = entity.model as PCModel;
      if (flameModel) {
        flameModel.material = mat;
      }
    } else if (type === "smoke") {
      particle.maxLife = 2.0 + Math.random();
      particle.startScale = 0.3;
      particle.endScale = 1.5;
      particle.startColor = new pc.Color(0.3, 0.3, 0.3);
      particle.endColor = new pc.Color(0.05, 0.05, 0.05);
      particle.velocity.set(
        (Math.random() - 0.5) * 0.8,
        1.0 + Math.random() * 0.5,
        (Math.random() - 0.5) * 0.8,
      );
      entity.setPosition(
        (Math.random() - 0.5) * 0.5,
        1.5,
        (Math.random() - 0.5) * 0.5,
      );

      const mat = this.getMaterial({
        name: "SmokeMat",
        diffuse: new pc.Color(0.2, 0.2, 0.2),
        opacity: 0.3,
      });
      const smokeModel = entity.model as PCModel;
      if (smokeModel) {
        smokeModel.material = mat;
      }
    } else {
      // ember
      particle.maxLife = 1.5 + Math.random();
      particle.startScale = 0.05;
      particle.endScale = 0.0;
      particle.velocity.set(
        (Math.random() - 0.5) * 2,
        2 + Math.random() * 2,
        (Math.random() - 0.5) * 2,
      );
      entity.setPosition(0, 0.5, 0);

      const mat = this.getMaterial({
        name: "EmberMat",
        emissive: new pc.Color(1, 0.6, 0.1),
        opacity: 1,
      });
      const emberModel = entity.model as PCModel;
      if (emberModel) {
        emberModel.material = mat;
      }
    }

    return particle;
  }

  /**
   * Update particle system
   */
  private updateParticles(dt: number): void {
    if (!this.app) return;

    // Update existing particles
    for (let i = this.fireParticles.length - 1; i >= 0; i--) {
      const p = this.fireParticles[i];
      p.life += dt;

      if (p.life >= p.maxLife) {
        // Remove particle
        p.entity.destroy();
        this.fireParticles.splice(i, 1);
        continue;
      }

      // Update position
      const pos = p.entity.getPosition();
      pos.add(p.velocity.clone().scale(dt));
      p.entity.setPosition(pos);

      // Update scale
      const t = p.life / p.maxLife;
      const scale = p.startScale + (p.endScale - p.startScale) * t;
      p.entity.setLocalScale(scale, scale, scale);

      // Update opacity
      const opacity = 1 - t;
      const particleModel = p.entity.model as PCModel;
      if (particleModel && particleModel.material) {
        particleModel.material.opacity = opacity;
        particleModel.material.update();
      }

      // Face camera
      const cam = this.app.root.findByName("Camera");
      if (cam) {
        p.entity.lookAt(cam.getPosition());
      }
    }

    // Spawn new particles
    this.spawnFireParticles(dt);
  }

  /**
   * Get or create cached material
   */
  private getMaterial(options: {
    name?: string;
    diffuse?: PCColor;
    specular?: PCColor;
    emissive?: PCColor;
    shininess?: number;
    opacity?: number;
    blendType?: number;
  }): PCMaterial {
    const pc = window.pc;
    const key = options.name || JSON.stringify(options);

    const cached = this.materialCache.get(key);
    if (cached) {
      return cached;
    }

    const mat = new pc.StandardMaterial();
    if (options.diffuse) mat.diffuse = options.diffuse;
    if (options.specular) mat.specular = options.specular;
    if (options.emissive) mat.emissive = options.emissive;
    if (options.shininess !== undefined) mat.shininess = options.shininess;
    if (options.opacity !== undefined) {
      mat.opacity = options.opacity;
      mat.blendType = options.blendType || pc.BLEND_NORMAL;
    }
    mat.update();
    this.materialCache.set(key, mat);
    return mat;
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

    // Calculate layout using getPlayerPosition
    players.forEach((player, index) => {
      const pos = this.getPlayerPosition(index, players.length);
      const angle = Math.atan2(pos.z, pos.x);

      const playerEntity = this.avatarBuilder.createPlayerAvatar(
        player,
        pos.x,
        pos.z,
        angle,
      );

      // UI-style pedestal to make positions clearer
      this.addPlayerPedestal(playerEntity);

      // Add name label
      const nameLabel = this.createNameLabel(player.name, player.ist_am_leben);
      playerEntity.addChild(nameLabel);
      this.playerLabels.set(player.id, nameLabel);

      if (this.app) {
        this.app.root.addChild(playerEntity);
      }

      this.playerEntities.set(player.id, playerEntity);

      // Update visual effects
      this.updatePlayerEffects(playerEntity, player);
    });

    if (this.viewMode === "first-person") {
      const target = this.getFirstPersonTarget();
      if (target) {
        this.syncFirstPersonOrientation(target);
        this.snapCameraToFirstPerson(target);
      }
    }

    console.log(`[Village3D] Created ${players.length} player avatars`);
  }

  private addPlayerPedestal(playerEntity: PlayerEntity): void {
    const pc = window.pc;

    const base = new pc.Entity("Pedestal");
    base.addComponent("model", { type: "cylinder" });
    base.setLocalScale(2.4, 0.12, 2.4);
    base.setLocalPosition(0, 0.02, 0);

    const baseMat = this.getMaterial({
      name: "PlayerPedestal",
      diffuse: new pc.Color(0.18, 0.16, 0.15),
      specular: new pc.Color(0.06, 0.06, 0.06),
    });
    (base.model as PCModel).material = baseMat;
    playerEntity.addChild(base);

    // Subtle ring
    const ring = new pc.Entity("PedestalRing");
    ring.addComponent("model", { type: "torus" });
    ring.setLocalScale(2.8, 2.8, 0.25);
    ring.setLocalPosition(0, 0.06, 0);

    const ringMat = new pc.StandardMaterial();
    ringMat.emissive = new pc.Color(0.25, 0.2, 0.15);
    ringMat.emissiveIntensity = 1.2;
    ringMat.opacity = 0.35;
    ringMat.blendType = pc.BLEND_ADDITIVE;
    ringMat.update();
    (ring.model as PCModel).material = ringMat;
    playerEntity.addChild(ring);
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

    // Update lighting - Düsterwald: always ominous
    if (this.light) {
      const lightComp = this.light.light!;
      if (lightComp) {
        lightComp.color = isNight
          ? new window.pc.Color(0.25, 0.3, 0.55)
          : new window.pc.Color(0.6, 0.6, 0.7);
        lightComp.intensity = isNight ? 0.35 : 0.5;
      }
    }

    // Update ambient light - Düsterwald: always dark
    if (this.app) {
      this.app.scene.ambientLight = isNight
        ? new window.pc.Color(0.06, 0.07, 0.12)
        : new window.pc.Color(0.15, 0.15, 0.18);
    }

    // Update celestial bodies
    if (this.sun) this.sun.enabled = !isNight;
    if (this.sunGlow) this.sunGlow.enabled = !isNight;
    if (this.moon) this.moon.enabled = isNight;
    if (this.moonGlow) this.moonGlow.enabled = isNight;

    // Update fog - Düsterwald: thick, oppressive mist
    this.setSceneSettings({
      fog: isNight ? "linear" : "linear",
      fogStart: isNight ? 12 : 20,
      fogEnd: isNight ? 55 : 80,
      fogColor: isNight
        ? new window.pc.Color(0.015, 0.02, 0.04)
        : new window.pc.Color(0.25, 0.28, 0.32),
    });
  }

  /**
   * Main update loop
   */
  private update(dt: number): void {
    if (!this.app) return;

    // Spawn fire particles if campfire exists
    if (this.fireLight && this.particles.length < 60) {
      this.particleSpawner.timer += dt;
      if (this.particleSpawner.timer > 0.05) {
        this.particleSpawner.timer = 0;
        const particle = this.createParticle(
          Math.random() < 0.6
            ? "flame"
            : Math.random() < 0.8
              ? "smoke"
              : "ember",
        );
        this.particles.push(particle);
        this.app.root.addChild(particle.entity);
      }
    }

    // Update particle effects
    this.updateParticles(dt);

    // Update fireflies
    this.fireflies.forEach((firefly) => {
      firefly.pulsePhase += dt * firefly.pulseSpeed;
      const intensity = 1.5 + Math.sin(firefly.pulsePhase) * 0.5;
      firefly.material.emissiveIntensity = intensity;
      firefly.material.update();

      // Move firefly
      const pos = firefly.entity.getPosition();
      pos.add(firefly.velocity.clone().scale(dt));

      // Boundary check - keep within area
      if (pos.x < -30 || pos.x > 30) firefly.velocity.x *= -1;
      if (pos.z < -30 || pos.z > 30) firefly.velocity.z *= -1;
      if (pos.y < 1 || pos.y > 6) firefly.velocity.y *= -1;

      firefly.entity.setPosition(pos);
    });

    // Update stars twinkling
    this.stars.forEach((star) => {
      star.twinklePhase += dt * star.twinkleSpeed;
      const brightness =
        star.baseBrightness + Math.sin(star.twinklePhase) * 0.3;
      star.material.emissiveIntensity = Math.max(0.5, brightness);
      star.material.update();
    });

    // Update victim highlight pulse
    if (this.victimHighlight) {
      const ring = this.victimHighlight.entity as PulseEntity;
      ring.pulseTime = (ring.pulseTime || 0) + dt;
      const pulse = 0.8 + Math.sin(ring.pulseTime * 3) * 0.2;
      this.victimHighlight.material.opacity = pulse;
      this.victimHighlight.material.update();
    }

    // Update fog planes if enabled
    if (this.fogPlanes.length > 0) {
      // Fog planes animation could go here
      // Currently just checking length to avoid unused variable warning
    }

    if (this.viewMode === "first-person") {
      this.updateFirstPersonCamera();
    } else {
      this.updateOrbitCamera(dt);
    }

    // Billboard effect: keep name labels facing the camera
    if (this.camera) {
      const camPos = this.camera.getPosition();
      this.playerLabels.forEach((label) => {
        if (!label || !label.parent) return;
        const labelPos = label.getPosition();
        const dx = camPos.x - labelPos.x;
        const dz = camPos.z - labelPos.z;
        const worldAngleDeg = Math.atan2(dx, dz) * (180 / Math.PI);
        const parentRot = label.parent.getEulerAngles();
        const localYAngle = worldAngleDeg - parentRot.y + 180;
        label.setLocalEulerAngles(90, localYAngle, 0);
      });
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

      // Update any action effects
      entity.children.forEach((child) => {
        const animChild = child as AnimatedEntity;
        if (
          animChild.animateCallback &&
          typeof animChild.animateCallback === "function"
        ) {
          animChild.animateCallback(dt);
        }
      });

      // Update hints
      entity.children.forEach((child) => {
        const hintChild = child as HintEntity;
        if (hintChild.name === "Hint" && hintChild.hintTime !== undefined) {
          hintChild.hintTime += dt;
          // Bob up and down
          const bobOffset = Math.sin(hintChild.hintTime * 3) * 0.3;
          hintChild.setLocalPosition(0, 4 + bobOffset, 0);
        }
      });
    });
  }

  private updateOrbitCamera(dt: number): void {
    if (!this.camera) return;
    const pc = window.pc;
    const targetX = Math.cos(this.targetCameraAngle) * this.targetCameraRadius;
    const targetZ = Math.sin(this.targetCameraAngle) * this.targetCameraRadius;

    if (!this.targetPosition) {
      this.targetPosition = new pc.Vec3(
        targetX,
        this.targetCameraHeight,
        targetZ,
      );
    } else {
      this.targetPosition.set(targetX, this.targetCameraHeight, targetZ);
    }

    const currentPos = this.camera.getPosition();
    const lerpFactor = Math.min(dt * 3, 1);

    this.camera.setPosition(
      currentPos.x + (this.targetPosition.x - currentPos.x) * lerpFactor,
      currentPos.y + (this.targetPosition.y - currentPos.y) * lerpFactor,
      currentPos.z + (this.targetPosition.z - currentPos.z) * lerpFactor,
    );

    this.camera.lookAt(0, 0, 0);
  }

  private updateFirstPersonCamera(): void {
    if (!this.camera) return;

    const target = this.getFirstPersonTarget();
    if (!target) {
      if (this.players.length === 0) return;
      return;
    }

    const pc = window.pc;
    const basePos = target.getPosition();
    const desiredEye = new pc.Vec3(
      basePos.x,
      basePos.y + this.firstPersonHeight,
      basePos.z,
    );

    this.camera.setPosition(desiredEye);

    const dir = new pc.Vec3(
      Math.sin(this.firstPersonYaw) * Math.cos(this.firstPersonPitch),
      Math.sin(this.firstPersonPitch),
      -Math.cos(this.firstPersonYaw) * Math.cos(this.firstPersonPitch),
    );
    dir.normalize();

    const lookTarget = desiredEye.clone().add(dir);
    this.camera.lookAt(lookTarget);
  }

  private getFirstPersonTarget(): PlayerEntity | null {
    const candidateId =
      this.firstPersonPlayerId ?? this.findFirstAlivePlayerId();
    if (candidateId === null) return null;

    const target = this.playerEntities.get(candidateId) || null;
    if (target) {
      this.firstPersonPlayerId = candidateId;
    }
    return target;
  }

  private findFirstAlivePlayerId(): number | null {
    const alive = this.players.find((p) => p.ist_am_leben);
    if (alive) return alive.id;
    return this.players.length > 0 ? this.players[0].id : null;
  }

  private syncFirstPersonOrientation(target: PlayerEntity): void {
    const yawDeg = target.getEulerAngles().y;
    this.firstPersonYaw = (yawDeg * Math.PI) / 180;
    this.firstPersonPitch = 0;
  }

  private snapCameraToFirstPerson(target: PlayerEntity): void {
    if (!this.camera) return;
    const pc = window.pc;
    const pos = target.getPosition();
    const eye = new pc.Vec3(pos.x, pos.y + this.firstPersonHeight, pos.z);

    const dir = new pc.Vec3(
      Math.sin(this.firstPersonYaw) * Math.cos(this.firstPersonPitch),
      Math.sin(this.firstPersonPitch),
      -Math.cos(this.firstPersonYaw) * Math.cos(this.firstPersonPitch),
    ).normalize();

    this.camera.setPosition(eye);
    this.camera.lookAt(eye.clone().add(dir));
  }

  toggleFirstPerson(playerId?: number): ViewMode {
    if (playerId !== undefined) {
      this.firstPersonPlayerId = playerId;
    }

    return this.enterFirstPerson();
  }

  enterFirstPerson(playerId?: number): ViewMode {
    if (playerId !== undefined) {
      this.firstPersonPlayerId = playerId;
    }

    this.viewMode = "first-person";
    const target = this.getFirstPersonTarget();
    if (target) {
      this.syncFirstPersonOrientation(target);
      this.snapCameraToFirstPerson(target);
    }

    if (this.canvas) {
      this.canvas.style.cursor = "crosshair";
    }

    return this.viewMode;
  }

  exitFirstPerson(): ViewMode {
    this.viewMode = "first-person";
    if (this.canvas) {
      this.canvas.style.cursor = "crosshair";
    }
    return this.viewMode;
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
   * Update top bar with phase and round information
   */
  updateTopBar(phase: string, round: number): void {
    const phaseEl = document.querySelector("#village3d-phase-name");
    const roundEl = document.querySelector("#village3d-round-info");

    if (phaseEl) {
      phaseEl.textContent = phase.replace(/_/g, " ").toUpperCase();
    }
    if (roundEl) {
      roundEl.textContent = `Runde ${round}`;
    }
  }

  /**
   * Update role badge in top bar
   */
  updateRoleBadge(role: string, color: string | null = null): void {
    const badge = document.querySelector("#village3d-role-badge");
    if (badge) {
      badge.textContent = role || "Warte...";
      if (color) {
        (badge as HTMLElement).style.background =
          `linear-gradient(135deg, ${color}80 0%, ${color}40 100%)`;
      }
    }
  }

  /**
   * Show/hide the HTML HUD overlay for fullscreen play.
   * This does not use the browser fullscreen API; it just toggles the HUD.
   */
  showFullscreenUI(show: boolean): void {
    if (this.hudVisible === show) return;
    this.hudVisible = show;
    const hud = document.querySelector("#village3d-hud") as HTMLElement | null;
    if (hud) {
      hud.classList.toggle("is-visible", show);
    }

    // Mobile-first: when entering fullscreen HUD, start with panels collapsed.
    // Users can open them via the topbar buttons.
    if (show) {
      const isMobile =
        (typeof window !== "undefined" &&
          (window.matchMedia?.("(max-width: 768px)")?.matches ||
            window.matchMedia?.("(pointer: coarse)")?.matches)) ||
        false;

      if (isMobile) {
        this.leftSidebarVisible = false;
        this.rightSidebarVisible = false;

        const left = document.querySelector(
          "#village3d-left-panel",
        ) as HTMLElement | null;
        const right = document.querySelector(
          "#village3d-right-panel",
        ) as HTMLElement | null;
        left?.classList.add("is-collapsed");
        right?.classList.add("is-collapsed");
      }
    }
  }

  /** Toggle the left HUD panel (player list / role info). */
  toggleLeftSidebar(): void {
    this.leftSidebarVisible = !this.leftSidebarVisible;
    const el = document.querySelector(
      "#village3d-left-panel",
    ) as HTMLElement | null;
    if (el) {
      el.classList.toggle("is-collapsed", !this.leftSidebarVisible);
    }
  }

  /** Toggle the right HUD panel (chat/log). */
  toggleRightSidebar(): void {
    this.rightSidebarVisible = !this.rightSidebarVisible;
    const el = document.querySelector(
      "#village3d-right-panel",
    ) as HTMLElement | null;
    if (el) {
      el.classList.toggle("is-collapsed", !this.rightSidebarVisible);
    }
  }

  /**
   * Append a message to the 3D HUD chat feed and show a small bubble above the sender if we can resolve them.
   */
  addChatMessage(from: string, text: string, _isDead: boolean = false): void {
    const list = document.querySelector(
      "#village3d-chat-messages",
    ) as HTMLElement | null;
    if (list) {
      const row = document.createElement("div");
      row.className = "village3d-chat-row";
      row.textContent = `${from}: ${text}`;
      list.appendChild(row);
      list.scrollTop = list.scrollHeight;
    }

    // Best-effort: show a bubble above the matching player
    const player = this.players.find((p) => p.name === from);
    if (player) {
      this.showChatBubble(player.id, text);
    }
  }

  /**
   * Update action buttons in the action panel
   */
  updateActionButtons(buttons: UIButtonData[]): void {
    const container = document.querySelector("#village3d-action-buttons");
    if (!container) return;

    (container as HTMLElement).innerHTML = "";

    if (!buttons || buttons.length === 0) {
      (container as HTMLElement).innerHTML =
        '<p style="color: #999; pointer-events: auto;">Warte auf deine Aktion...</p>';
      return;
    }

    buttons.forEach((btn) => {
      const button = document.createElement("button");
      button.style.cssText = `
        padding: 0.75rem 1.5rem;
        background: linear-gradient(135deg, #d4a574 0%, #b8885a 100%);
        border: none;
        border-radius: 8px;
        color: #000;
        cursor: pointer;
        font-weight: 600;
        font-size: 0.9rem;
        transition: all 0.3s ease;
        pointer-events: auto;
      `;
      button.textContent = btn.label || btn.text || "Action";
      if (btn.title) button.title = btn.title;
      if (btn.disabled) {
        button.disabled = true;
        button.style.opacity = "0.5";
        button.style.cursor = "not-allowed";
      }
      button.addEventListener("click", () => {
        if (button.disabled) return;
        if (btn.onClick) {
          btn.onClick();
          return;
        }
        if (btn.action && typeof btn.action === "function") {
          btn.action();
        }
      });
      (container as HTMLElement).appendChild(button);
    });
  }

  /**
   * Persistent selection highlight ring (separate from temporary highlightPlayer pulses).
   */
  setSelectedPlayer(playerId: number | null, color: string = "#ffd54a"): void {
    if (this.selectedHighlight) {
      const prevEntity = this.playerEntities.get(
        this.selectedHighlight.playerId,
      );
      if (prevEntity && this.selectedHighlight.entity.parent) {
        this.selectedHighlight.entity.destroy();
      }
      this.selectedHighlight = null;
    }

    if (playerId === null) return;
    const playerEntity = this.playerEntities.get(playerId);
    if (!playerEntity) return;

    const pc = window.pc;
    const ring = new pc.Entity("SelectedHighlight");
    ring.addComponent("model", { type: "torus" });
    ring.setLocalScale(2.2, 2.2, 0.35);
    ring.setLocalPosition(0, 0.11, 0);

    const mat = new pc.StandardMaterial();
    mat.emissive = this.hexToColor(color);
    mat.emissiveIntensity = 2.5;
    mat.opacity = 0.9;
    mat.blendType = pc.BLEND_ADDITIVE;
    mat.update();
    (ring.model as PCModel).material = mat;

    playerEntity.addChild(ring);
    this.selectedHighlight = { playerId, entity: ring };
  }

  /**
   * Setup input handling for camera controls and player interaction
   */
  private setupInput(): void {
    if (!this.app || !this.canvas) return;

    const pc = window.pc;
    let isDragging = false;
    let hasMoved = false;
    let lastX = 0;
    let lastY = 0;
    const stopDrag = () => {
      if (!isDragging) return;
      isDragging = false;
      this.canvas!.style.cursor =
        this.viewMode === "first-person" ? "crosshair" : "grab";
    };

    // Mouse down
    this.canvas.addEventListener("mousedown", (e: MouseEvent) => {
      if (e.button === 0) {
        // Left click
        isDragging = true;
        hasMoved = false;
        lastX = e.clientX;
        lastY = e.clientY;
        this.canvas!.style.cursor = "grabbing";
      }
    });

    // Mouse up
    this.canvas.addEventListener("mouseup", (e: MouseEvent) => {
      if (e.button === 0) {
        // Treat as click if there was no drag movement
        if (isDragging && !hasMoved) {
          const rect = this.canvas!.getBoundingClientRect();
          const x = e.clientX - rect.left;
          const y = e.clientY - rect.top;
          this.pick(x, y);
        }
        stopDrag();
      }
    });

    // Mouse move
    this.canvas.addEventListener("mousemove", (e: MouseEvent) => {
      if (isDragging) {
        const deltaX = e.clientX - lastX;
        const deltaY = e.clientY - lastY;
        if (Math.abs(deltaX) > 2 || Math.abs(deltaY) > 2) {
          hasMoved = true;
        }

        if (this.viewMode === "first-person") {
          this.firstPersonYaw -= deltaX * 0.01;
          const clampedPitch = this.firstPersonPitch - deltaY * 0.01;
          this.firstPersonPitch = Math.max(
            -Math.PI / 2 + 0.2,
            Math.min(Math.PI / 2 - 0.2, clampedPitch),
          );
        } else {
          this.targetCameraAngle -= deltaX * 0.01;
          this.targetCameraHeight = Math.max(
            5,
            Math.min(50, this.targetCameraHeight - deltaY * 0.1),
          );
        }

        lastX = e.clientX;
        lastY = e.clientY;
      } else {
        // Hover feedback (throttled)
        const now = performance.now();
        if (now - this.lastHoverCheckAt > 80) {
          this.lastHoverCheckAt = now;
          const rect = this.canvas!.getBoundingClientRect();
          const x = e.clientX - rect.left;
          const y = e.clientY - rect.top;
          const hoveredId = this.getPlayerIdAtScreen(x, y);
          this.setHoveredPlayer(hoveredId);
          const baseCursor =
            this.viewMode === "first-person" ? "crosshair" : "grab";
          this.canvas!.style.cursor =
            hoveredId !== null ? "pointer" : baseCursor;
        }
      }
    });

    // Click fallback
    this.canvas.addEventListener("click", (e: MouseEvent) => {
      if (hasMoved) return;
      const rect = this.canvas!.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      this.pick(x, y);
    });

    this.canvas.addEventListener("mouseleave", stopDrag);
    window.addEventListener("mouseup", stopDrag);
    window.addEventListener("blur", stopDrag);

    // Mouse wheel
    this.canvas.addEventListener("wheel", (e: WheelEvent) => {
      e.preventDefault();
      if (this.viewMode === "first-person") return;
      this.targetCameraRadius = Math.max(
        10,
        Math.min(60, this.targetCameraRadius + e.deltaY * 0.05),
      );
    });

    // Keyboard
    const keyboard = this.app.keyboard;
    if (keyboard) {
      keyboard.on(
        "keydown",
        (e: KeyboardEvent) => {
          const keyCode = (e as unknown as { key: number }).key;
          if (keyCode === pc.KEY_R) {
            if (this.viewMode === "first-person") {
              const target = this.getFirstPersonTarget();
              if (target) {
                this.syncFirstPersonOrientation(target);
                this.snapCameraToFirstPerson(target);
              }
            } else {
              this.resetCamera();
            }
          }

          if (keyCode === pc.KEY_F) {
            this.toggleFirstPerson();
          }
        },
        this,
      );
    }

    this.canvas.style.cursor =
      this.viewMode === "first-person" ? "crosshair" : "grab";
  }

  /**
   * Pick player from screen coordinates
   */
  private pick(x: number, y: number): void {
    const id = this.getPlayerIdAtScreen(x, y);
    if (id !== null) {
      if (this.onPlayerClick) this.onPlayerClick(id);
      console.log(`[Village3D] Clicked player ${id}`);
    }
  }

  private getPlayerIdAtScreen(x: number, y: number): number | null {
    if (!this.app || !this.camera) return null;
    const pc = window.pc;
    const camera = this.camera.camera!;
    if (!camera) return null;

    const from = camera.screenToWorld(x, y, camera.nearClip);
    const to = camera.screenToWorld(x, y, camera.farClip);

    let closestPlayerId: number | null = null;
    let closestDistance = Infinity;

    const rayDir = new pc.Vec3();
    rayDir.sub2(to, from).normalize();

    this.playerEntities.forEach((entity, playerId) => {
      const playerPos = entity.getPosition();
      const toPlayer = new pc.Vec3();
      toPlayer.sub2(playerPos, from);

      const dot = toPlayer.dot(rayDir);
      if (dot > 0) {
        const closest = new pc.Vec3();
        closest.copy(rayDir);
        closest.scale(dot);
        closest.add(from);

        const dx = closest.x - playerPos.x;
        const dy = closest.y - playerPos.y;
        const dz = closest.z - playerPos.z;
        const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);

        if (dist < 2 && dot < closestDistance) {
          closestDistance = dot;
          closestPlayerId = playerId;
        }
      }
    });

    return closestPlayerId;
  }

  private setHoveredPlayer(playerId: number | null): void {
    if (playerId === null) {
      if (this.hoverHighlight) {
        this.hoverHighlight.entity.destroy();
        this.hoverHighlight = null;
      }
      return;
    }

    if (this.hoverHighlight && this.hoverHighlight.playerId === playerId)
      return;
    if (this.hoverHighlight) {
      this.hoverHighlight.entity.destroy();
      this.hoverHighlight = null;
    }

    const playerEntity = this.playerEntities.get(playerId);
    if (!playerEntity) return;

    const pc = window.pc;
    const ring = new pc.Entity("HoverHighlight");
    ring.addComponent("model", { type: "torus" });
    ring.setLocalScale(2.35, 2.35, 0.3);
    ring.setLocalPosition(0, 0.12, 0);

    const mat = new pc.StandardMaterial();
    mat.emissive = new pc.Color(1, 0.85, 0.4);
    mat.emissiveIntensity = 2.2;
    mat.opacity = 0.45;
    mat.blendType = pc.BLEND_ADDITIVE;
    mat.update();
    (ring.model as PCModel).material = mat;

    playerEntity.addChild(ring);
    this.hoverHighlight = { playerId, entity: ring };
  }

  /**
   * Zoom camera to focus on specific player
   */
  zoomToPlayer(playerId: number): void {
    const playerEntity = this.playerEntities.get(playerId);
    if (!playerEntity) return;

    const pos = playerEntity.getPosition();
    const angle = Math.atan2(pos.z, pos.x);

    this.targetCameraAngle = angle;
    this.targetCameraRadius = 15;
    this.targetCameraHeight = 10;
  }

  /**
   * Focus camera on player (public method)
   */
  focusOnPlayer(playerId: number): void {
    this.zoomToPlayer(playerId);
  }

  /**
   * Highlight a specific player with a color
   */
  highlightPlayer(playerId: number, color?: string): void {
    const playerEntity = this.playerEntities.get(playerId);
    if (!playerEntity) return;

    const pc = window.pc;

    // Create highlight ring
    const highlight = new pc.Entity("Highlight");
    highlight.addComponent("model", { type: "torus" });
    highlight.setLocalScale(2, 2, 0.3);
    highlight.setLocalPosition(0, 0.1, 0);

    const mat = new pc.StandardMaterial();
    mat.emissive = color ? this.hexToColor(color) : new pc.Color(1, 1, 0);
    mat.emissiveIntensity = 2;
    mat.opacity = 0.8;
    mat.blendType = pc.BLEND_ADDITIVE;
    mat.update();
    (highlight.model as PCModel).material = mat;

    playerEntity.addChild(highlight);

    // Auto-remove after 3 seconds
    setTimeout(() => {
      if (highlight.parent) {
        highlight.destroy();
      }
    }, 3000);
  }

  /**
   * Show hint indicator above player
   */
  showHint(playerId: number, type: string): void {
    const playerEntity = this.playerEntities.get(playerId);
    if (!playerEntity) return;

    const pc = window.pc;

    // Create hint entity
    const hint = new pc.Entity("Hint");
    hint.addComponent("model", { type: "cone" });
    hint.setLocalScale(0.5, 1, 0.5);
    hint.setLocalPosition(0, 4, 0);
    hint.setLocalEulerAngles(180, 0, 0);

    const mat = new pc.StandardMaterial();

    // Color based on type
    switch (type) {
      case "target":
        mat.emissive = new pc.Color(1, 0, 0);
        break;
      case "heal":
        mat.emissive = new pc.Color(0, 1, 0);
        break;
      case "protect":
        mat.emissive = new pc.Color(0, 0.5, 1);
        break;
      case "investigate":
        mat.emissive = new pc.Color(1, 1, 0);
        break;
      default:
        mat.emissive = new pc.Color(1, 1, 1);
    }

    mat.emissiveIntensity = 2;
    mat.update();
    (hint.model as PCModel).material = mat;

    playerEntity.addChild(hint);

    // Store animation data
    (hint as HintEntity).hintTime = 0;
    (hint as HintEntity).hintType = type;
  }

  /**
   * Show vote indicator above player
   */
  showVoteIndicator(playerId: number, voterName: string): void {
    const playerEntity = this.playerEntities.get(playerId);
    if (!playerEntity) return;

    const pc = window.pc;

    // Create vote arrow
    const arrow = new pc.Entity("VoteArrow");
    arrow.addComponent("model", { type: "cone" });
    arrow.setLocalScale(0.3, 0.8, 0.3);
    arrow.setLocalPosition(0, 3.5, 0);
    arrow.setLocalEulerAngles(180, 0, 0);

    const mat = new pc.StandardMaterial();
    mat.emissive = new pc.Color(1, 0.8, 0);
    mat.emissiveIntensity = 2;
    mat.update();
    (arrow.model as PCModel).material = mat;

    playerEntity.addChild(arrow);

    console.log(`[Village3D] Vote from ${voterName} on player ${playerId}`);

    // Auto-remove after 5 seconds
    setTimeout(() => {
      if (arrow.parent) {
        arrow.destroy();
      }
    }, 5000);
  }

  /**
   * Show chat bubble above player
   */
  showChatBubble(
    playerId: number,
    message: string,
    duration: number = 5000,
  ): void {
    const playerEntity = this.playerEntities.get(playerId);
    if (!playerEntity) return;

    const pc = window.pc;

    // Create bubble background
    const bubble = new pc.Entity("ChatBubble");
    bubble.addComponent("model", { type: "sphere" });
    bubble.setLocalScale(2, 1.5, 0.5);
    bubble.setLocalPosition(0, 3.5, 0);

    const mat = new pc.StandardMaterial();
    mat.diffuse = new pc.Color(1, 1, 1);
    mat.opacity = 0.9;
    mat.update();
    (bubble.model as PCModel).material = mat;

    playerEntity.addChild(bubble);

    console.log(`[Village3D] Chat from player ${playerId}: ${message}`);

    // Auto-remove
    setTimeout(() => {
      if (bubble.parent) {
        bubble.destroy();
      }
    }, duration);
  }

  /**
   * Show action effect (healing, attack, etc.)
   */
  showActionEffect(playerId: number, effectType: string): void {
    const playerEntity = this.playerEntities.get(playerId);
    if (!playerEntity) return;

    const pc = window.pc;

    // Create effect particles
    const effect = new pc.Entity("ActionEffect");
    effect.addComponent("model", { type: "sphere" });
    effect.setLocalScale(0.3, 0.3, 0.3);
    effect.setLocalPosition(0, 2, 0);

    const mat = new pc.StandardMaterial();

    switch (effectType) {
      case "heal":
        mat.emissive = new pc.Color(0, 1, 0);
        break;
      case "attack":
        mat.emissive = new pc.Color(1, 0, 0);
        break;
      case "protect":
        mat.emissive = new pc.Color(0, 0.5, 1);
        break;
      case "poison":
        mat.emissive = new pc.Color(0.5, 0, 1);
        break;
      default:
        mat.emissive = new pc.Color(1, 1, 1);
    }

    mat.emissiveIntensity = 3;
    mat.opacity = 0.7;
    mat.blendType = pc.BLEND_ADDITIVE;
    mat.update();
    (effect.model as PCModel).material = mat;

    playerEntity.addChild(effect);

    // Animate and remove
    let time = 0;
    const animate = (dt: number) => {
      time += dt;
      if (time > 2) {
        effect.destroy();
        return;
      }

      effect.setLocalPosition(0, 2 + time * 2, 0);
      const scale = 0.3 + time * 0.5;
      effect.setLocalScale(scale, scale, scale);
      mat.opacity = 0.7 * (1 - time / 2);
      mat.update();
    };

    // Store animation callback
    (effect as AnimatedEntity).animateCallback = animate;
  }

  /**
   * Update player status (alive/dead)
   */
  updatePlayerStatus(playerId: number, isAlive: boolean): void {
    const playerEntity = this.playerEntities.get(playerId);
    if (!playerEntity) return;

    console.log(
      `[Village3D] Player ${playerId} status: ${isAlive ? "alive" : "dead"}`,
    );

    // Update visual appearance
    if (!isAlive) {
      // Make player semi-transparent and desaturated
      if (!this.deadMaterial) {
        const pc = window.pc;
        this.deadMaterial = new pc.StandardMaterial();
        if (this.deadMaterial) {
          this.deadMaterial.diffuse = new pc.Color(0.3, 0.3, 0.3);
          this.deadMaterial.opacity = 0.5;
          this.deadMaterial.blendType = pc.BLEND_NORMAL;
          this.deadMaterial.update();
        }
      }

      // Apply to all child meshes
      playerEntity.children.forEach((child: any) => {
        if (child.model && this.deadMaterial) {
          (child.model as PCModel).material = this.deadMaterial;
        }
      });
    }
  }

  /**
   * Highlight werewolf victim (for Hexe phase)
   */
  highlightVictim(playerId: number): void {
    const playerEntity = this.playerEntities.get(playerId);
    if (!playerEntity) return;

    const pc = window.pc;

    // Create pulsing red ring
    const ring = new pc.Entity("VictimHighlight");
    ring.addComponent("model", { type: "torus" });
    ring.setLocalScale(2.5, 2.5, 0.4);
    ring.setLocalPosition(0, 0.1, 0);

    const mat = new pc.StandardMaterial();
    mat.emissive = new pc.Color(1, 0, 0);
    mat.emissiveIntensity = 3;
    mat.opacity = 0.8;
    mat.blendType = pc.BLEND_ADDITIVE;
    mat.update();
    (ring.model as PCModel).material = mat;

    playerEntity.addChild(ring);

    // Store for later removal
    this.victimHighlight = { entity: ring, material: mat };

    // Animate pulsing
    (ring as PulseEntity).pulseTime = 0;
  }

  /**
   * Clear victim highlight
   */
  clearVictimHighlight(): void {
    if (this.victimHighlight) {
      this.victimHighlight.entity.destroy();
      this.victimHighlight = null;
    }
  }

  /**
   * Apply sleeping visual state to player
   */
  private applySleepingState(entity: PCEntity, isSleeping: boolean): void {
    if (isSleeping) {
      // Dim and add "Z" indicator
      entity.children.forEach((child: any) => {
        if (child.model) {
          const mat = (child.model as PCModel).material;
          if (mat) {
            mat.emissiveIntensity = (mat.emissiveIntensity || 1) * 0.5;
            mat.update();
          }
        }
      });
    } else {
      // Restore normal brightness
      entity.children.forEach((child: any) => {
        if (child.model) {
          const mat = (child.model as PCModel).material;
          if (mat) {
            mat.emissiveIntensity = (mat.emissiveIntensity || 0.5) * 2;
            mat.update();
          }
        }
      });
    }
  }

  /**
   * Mark player as sleeping/inactive
   */
  setPlayerSleeping(playerId: number, isSleeping: boolean): void {
    const playerEntity = this.playerEntities.get(playerId);
    if (!playerEntity) return;

    if (isSleeping) {
      this.sleepingPlayers.add(playerId);
    } else {
      this.sleepingPlayers.delete(playerId);
    }

    this.applySleepingState(playerEntity, isSleeping);
  }

  /**
   * Calculate player position based on layout
   */
  private getPlayerPosition(
    index: number,
    total: number,
  ): { x: number; z: number } {
    if (this.layoutMode === "circle") {
      return this.getCirclePosition(index, total, 10);
    }

    // Default to circle
    return this.getCirclePosition(index, total, 10);
  }

  /**
   * Get position on circle
   */
  private getCirclePosition(
    index: number,
    total: number,
    radius: number,
  ): { x: number; z: number } {
    const angle = (index / total) * Math.PI * 2;
    return {
      x: Math.cos(angle) * radius,
      z: Math.sin(angle) * radius,
    };
  }

  /**
   * Create name label for player
   */
  private createNameLabel(name: string, isAlive: boolean): PCEntity {
    const pc = window.pc;
    const label = new pc.Entity("NameLabel");
    label.addComponent("model", { type: "plane" });
    label.setLocalScale(-2, 0.5, 1); // Flip so text is not mirrored

    // High-res canvas for crisp text
    const canvas = document.createElement("canvas");
    canvas.width = 512;
    canvas.height = 128;
    const ctx = canvas.getContext("2d")!;

    // Background
    ctx.fillStyle = isAlive ? "rgba(0,0,0,0.8)" : "rgba(0,0,0,0.5)";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Text styling
    ctx.fillStyle = isAlive ? "#FFFFFF" : "#999999";
    ctx.font = "bold 64px Arial, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.shadowColor = "rgba(0,0,0,0.5)";
    ctx.shadowBlur = 4;
    ctx.shadowOffsetX = 2;
    ctx.shadowOffsetY = 2;
    ctx.fillText(name, canvas.width / 2, canvas.height / 2);

    // Texture from canvas
    const texture = new pc.Texture(this.app!.graphicsDevice);
    texture.setSource(canvas);

    // Material setup
    const mat = new pc.StandardMaterial();
    mat.diffuseMap = texture;
    mat.emissive = new pc.Color(1, 1, 1);
    mat.emissiveMap = texture;
    mat.opacity = isAlive ? 1.0 : 0.6;
    mat.blendType = pc.BLEND_NORMAL;
    mat.cull = pc.CULLFACE_NONE; // Double-sided
    mat.depthWrite = false; // helps transparency sorting
    mat.update();
    (label.model as PCModel).material = mat;

    label.setLocalPosition(0, 3, 0);
    return label;
  }

  /**
   * Helper to set scene rendering settings
   */
  private setSceneSettings(settings: Record<string, unknown>): void {
    if (!this.app) return;
    const pc = window.pc;
    const scene = this.app.scene;

    if (scene && settings) {
      // Handle fog type specially - it's a getter-only in PlayCanvas
      if ("fog" in settings) {
        const fogType = settings.fog;
        const sceneWithFog = scene as unknown as { fog: unknown };
        if (fogType === "linear") {
          sceneWithFog.fog = pc.FOG_LINEAR;
        } else if (fogType === "exp" || fogType === "exp2") {
          sceneWithFog.fog = pc.FOG_EXP2;
        } else if (fogType === "none") {
          sceneWithFog.fog = pc.FOG_NONE;
        }
        delete settings.fog;
      }

      // Set remaining properties
      const sceneAny = scene as unknown as Record<string, unknown>;
      Object.keys(settings).forEach((key) => {
        if (key in sceneAny) {
          sceneAny[key] = settings[key];
        }
      });
    }
  }

  /**
   * Create enhanced atmospheric effects
   */
  private createEnhancedAtmosphericEffects(): void {
    if (!this.app) return;
    const pc = window.pc;

    // Fireflies
    const count = 40;
    for (let i = 0; i < count; i++) {
      const firefly = new pc.Entity("Firefly");
      firefly.addComponent("model", { type: "sphere" });
      firefly.setLocalScale(0.15, 0.15, 0.15);

      const angle = Math.random() * Math.PI * 2;
      const dist = 15 + Math.random() * 20;
      const height = 2 + Math.random() * 4;

      firefly.setPosition(
        Math.cos(angle) * dist,
        height,
        Math.sin(angle) * dist,
      );

      const mat = new pc.StandardMaterial();
      mat.emissive = new pc.Color(0.8, 1, 0.6);
      mat.emissiveIntensity = 2 + Math.random();
      mat.useLighting = false;
      mat.update();
      (firefly.model as PCModel).material = mat;

      this.app.root.addChild(firefly);

      this.fireflies.push({
        entity: firefly,
        material: mat,
        velocity: new pc.Vec3(
          (Math.random() - 0.5) * 2,
          (Math.random() - 0.5) * 0.5,
          (Math.random() - 0.5) * 2,
        ),
        pulseSpeed: 2 + Math.random() * 2,
        pulsePhase: Math.random() * Math.PI * 2,
      });
    }
  }

  /**
   * Create ground fog effect
   */
  private createGroundFog(): void {
    // Create subtle ground fog effect using semi-transparent planes
    // Note: Disabled by default due to potential visual artifacts
    // Can be enabled by uncommenting the code below

    /* Uncomment to enable ground fog planes:
    if (!this.app) return;
    const pc = window.pc;
    
    for (let i = 0; i < 3; i++) {
      const fogPlane = new pc.Entity('FogPlane');
      fogPlane.addComponent('model', { type: 'plane' });
      fogPlane.setLocalScale(80, 1, 80);
      fogPlane.setPosition(0, 0.5 + i * 0.3, 0);
      
      const mat = new pc.StandardMaterial();
      mat.diffuse = new pc.Color(0.05, 0.05, 0.08);
      mat.opacity = 0.1 - i * 0.03;
      mat.blendType = pc.BLEND_NORMAL;
      mat.update();
      (fogPlane.model as PCModel).material = mat;
      
      this.app.root.addChild(fogPlane);
      this.fogPlanes.push({ entity: fogPlane, material: mat });
    }
    */

    // Initialize empty array for future use
    this.fogPlanes = [];
  }

  /**
   * Convert hex color to PlayCanvas Color
   */
  private hexToColor(hex: string): PCColor {
    const pc = window.pc;

    hex = hex.replace("#", "");
    const r = parseInt(hex.substring(0, 2), 16) / 255;
    const g = parseInt(hex.substring(2, 4), 16) / 255;
    const b = parseInt(hex.substring(4, 6), 16) / 255;

    return new pc.Color(r, g, b);
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
