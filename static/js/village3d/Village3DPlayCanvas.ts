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
} from "./types.js";
import { PlayerAvatarBuilder } from "./PlayerAvatarBuilder.js";

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
    velocity: any;
    startScale: number;
    endScale: number;
  }> = [];

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

    // Sky dome with stars
    if (!this.isLobbyMode) {
      this.createSkyDome();
      this.createCelestialBodies();
    }

    // Ground
    this.createDetailedGround();

    // Buildings (only in game mode)
    if (!this.isLobbyMode) {
      this.createVillageBuildings();
    }
  }

  /**
   * Create sky dome with stars
   */
  private createSkyDome(): void {
    if (!this.app) return;
    const pc = (window as any).pc;

    // Large inverted sphere for sky
    this.skyDome = new pc.Entity("SkyDome");
    if (this.skyDome) {
      this.skyDome.addComponent("model", { type: "sphere" });
      this.skyDome.setLocalScale(-150, -150, -150); // Inverted (inside-out)
      this.skyDome.setPosition(0, 0, 0);
    }

    // Night sky gradient material
    const skyMat = new pc.StandardMaterial();
    skyMat.diffuse = new pc.Color(0.02, 0.03, 0.08); // Deep night blue
    skyMat.emissive = new pc.Color(0.015, 0.025, 0.06); // Subtle glow
    skyMat.useLighting = false;
    skyMat.cull = pc.CULLFACE_FRONT; // Render inside
    skyMat.update();

    if (this.skyDome) {
      const skyModel = this.skyDome.model as any;
      if (skyModel) {
        skyModel.material = skyMat;
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
      const radius = 140;
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
      star.model.material = starMat;

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
    const pc = (window as any).pc;

    // Moon
    this.moon = new pc.Entity("Moon");
    if (this.moon) {
      this.moon.addComponent("model", { type: "sphere" });
      this.moon.setLocalScale(8, 8, 8);
      this.moon.setPosition(60, 80, -50);

      const moonMat = new pc.StandardMaterial();
      moonMat.diffuse = new pc.Color(0.95, 0.95, 0.9);
      moonMat.emissive = new pc.Color(0.7, 0.75, 0.85);
      moonMat.useLighting = false;
      moonMat.update();

      const moonModel = this.moon.model as any;
      if (moonModel) {
        moonModel.material = moonMat;
      }

      this.app.root.addChild(this.moon);
    }

    // Moon glow (larger, softer sphere behind)
    const moonGlow = new pc.Entity("MoonGlow");
    moonGlow.addComponent("model", { type: "sphere" });
    moonGlow.setLocalScale(14, 14, 14);
    moonGlow.setPosition(60, 80, -50);

    const glowMat = new pc.StandardMaterial();
    glowMat.emissive = new pc.Color(0.3, 0.35, 0.5);
    glowMat.opacity = 0.25;
    glowMat.blendType = pc.BLEND_ADDITIVE;
    glowMat.useLighting = false;
    glowMat.update();
    moonGlow.model.material = glowMat;

    this.app.root.addChild(moonGlow);

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

      const sunModel = this.sun.model as any;
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

      const sunGlowModel = this.sunGlow.model as any;
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
    const pc = (window as any).pc;

    // Main ground - varied grass terrain
    const ground = new pc.Entity("Ground");
    ground.addComponent("model", { type: "plane" });

    // Larger ground for better horizon
    const groundSize = this.isLobbyMode ? 120 : 180;
    ground.setLocalScale(groundSize, 1, groundSize);

    const material = new pc.StandardMaterial();
    material.diffuse = new pc.Color(0.1, 0.15, 0.08); // Darker, richer base
    material.specular = new pc.Color(0.02, 0.02, 0.02);
    material.shininess = 2;
    material.update();

    ground.model.material = material;
    this.app.root.addChild(ground);

    // Random grass patches for variation
    const patchCount = this.isLobbyMode ? 20 : 50;
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
      const colorVar = Math.random() * 0.05;
      patchMat.diffuse = new pc.Color(
        0.12 + colorVar,
        0.18 + colorVar,
        0.1 + colorVar,
      );
      patchMat.opacity = 0.8;
      patchMat.blendType = pc.BLEND_NORMAL;
      patchMat.update();
      patch.model.material = patchMat;
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
      diffuse: new pc.Color(0.25, 0.22, 0.2), // Darker stone
      specular: new pc.Color(0.05, 0.05, 0.05),
    });
    centerSquare.model.material = squareMat;
    this.app.root.addChild(centerSquare);

    // Add decorative stones around the square
    if (!this.isLobbyMode) {
      this.createSquareDecorations();
    }
  }

  /**
   * Create village paths connecting buildings
   */
  private createVillagePaths(): void {
    if (!this.app) return;
    const pc = (window as any).pc;

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
      path.setLocalScale(pathData.scaleX, 0.02, pathData.scaleZ);
      path.setPosition(pathData.x, 0.02, pathData.z);
      path.setLocalEulerAngles(0, pathData.rotation, 0);

      const pathMat = new pc.StandardMaterial();
      pathMat.diffuse = new pc.Color(0.2, 0.15, 0.1);
      pathMat.specular = new pc.Color(0.02, 0.02, 0.02);
      pathMat.update();
      const pathModel = path.model as any;
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
    const pc = (window as any).pc;

    const decorationCount = 20;
    for (let i = 0; i < decorationCount; i++) {
      const angle = (i / decorationCount) * Math.PI * 2;
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
      deco.model.material = decoMat;

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
    // Village houses around the perimeter
    const housePositions = [
      { x: -20, z: -8, rot: 45 },
      { x: -18, z: 10, rot: -30 },
      { x: -5, z: 18, rot: -90 },
      { x: 10, z: 16, rot: -120 },
      { x: 18, z: 5, rot: 180 },
      { x: 16, z: -12, rot: 150 },
    ];

    housePositions.forEach((pos, idx) => {
      const offsetX = (Math.random() - 0.5) * 2;
      const offsetZ = (Math.random() - 0.5) * 2;
      const offsetRot = (Math.random() - 0.5) * 10;
      this.createHouse(
        pos.x + offsetX,
        pos.z + offsetZ,
        pos.rot + offsetRot,
        idx,
      );
    });

    // Church (special building)
    this.createChurch(-12, -20);

    // Well (near center)
    this.createWell(12, 12);

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
    const pc = (window as any).pc;

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
    trunkMat.diffuse = new pc.Color(0.25, 0.2, 0.15);
    trunkMat.specular = new pc.Color(0.05, 0.05, 0.05);
    trunkMat.update();
    trunk.model.material = trunkMat;
    tree.addChild(trunk);

    // Foliage clumps
    const foliageMat = new pc.StandardMaterial();
    foliageMat.diffuse = new pc.Color(0.05, 0.15 + Math.random() * 0.1, 0.05);
    foliageMat.specular = new pc.Color(0.01, 0.05, 0.01);
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
        clump.model.material = foliageMat;
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
    const pc = (window as any).pc;

    const bush = new pc.Entity("Bush");

    const bushMat = new pc.StandardMaterial();
    bushMat.diffuse = new pc.Color(0.1, 0.2 + Math.random() * 0.1, 0.08);
    bushMat.specular = new pc.Color(0.02, 0.05, 0.02);
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
      clump.model.material = bushMat;
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
    const pc = (window as any).pc;

    const rock = new pc.Entity("Rock");
    rock.addComponent("model", { type: "sphere" });

    const size = 0.5 + Math.random() * 1.5;
    rock.setLocalScale(size, size * 0.6, size);

    const rockMat = new pc.StandardMaterial();
    rockMat.diffuse = new pc.Color(0.35, 0.35, 0.38);
    rockMat.specular = new pc.Color(0.05, 0.05, 0.05);
    rockMat.update();
    rock.model.material = rockMat;

    rock.setPosition(x, size * 0.3, z);
    rock.setLocalEulerAngles(
      Math.random() * 360,
      Math.random() * 360,
      Math.random() * 360,
    );

    this.app.root.addChild(rock);
  }

  /**
   * Create a house
   */
  private createHouse(
    x: number,
    z: number,
    rotation: number,
    index: number,
  ): void {
    if (!this.app) return;
    const pc = (window as any).pc;

    const house = new pc.Entity(`House-${index}`);

    // Stone base
    const stoneBase = new pc.Entity("StoneBase");
    stoneBase.addComponent("model", { type: "box" });
    stoneBase.setLocalScale(4.2, 1.5, 5.2);
    stoneBase.setLocalPosition(0, 0.75, 0);

    const stoneMat = new pc.StandardMaterial();
    stoneMat.diffuse = new pc.Color(0.45, 0.45, 0.48);
    stoneMat.specular = new pc.Color(0.1, 0.1, 0.1);
    stoneMat.shininess = 5;
    stoneMat.update();
    stoneBase.model.material = stoneMat;
    house.addChild(stoneBase);

    // Upper floor
    const upperFloor = new pc.Entity("UpperFloor");
    upperFloor.addComponent("model", { type: "box" });
    upperFloor.setLocalScale(4, 2, 5);
    upperFloor.setLocalPosition(0, 2.5, 0);

    const plasterMat = new pc.StandardMaterial();
    const hue = 0.05 + Math.random() * 0.1;
    plasterMat.diffuse = new pc.Color(0.85 + hue, 0.8 + hue, 0.7 + hue);
    plasterMat.update();
    upperFloor.model.material = plasterMat;
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
      beam.model.material = beamMat;
      house.addChild(beam);
    }

    // Roof
    const roofAngle = 35;
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
    roofMat.diffuse = new pc.Color(0.4, 0.22, 0.15);
    roofMat.update();

    const roofLeft = new pc.Entity("RoofLeft");
    roofLeft.addComponent("model", { type: "box" });
    roofLeft.setLocalScale(roofPanelWidth, 0.12, roofLength);
    const panelCenterX = -halfWidth / 2;
    const panelCenterY = roofBaseY + roofPeakHeight / 2;
    roofLeft.setLocalPosition(panelCenterX, panelCenterY, 0);
    roofLeft.setLocalEulerAngles(0, 0, roofAngle);
    roofLeft.model.material = roofMat;
    house.addChild(roofLeft);

    const roofRight = new pc.Entity("RoofRight");
    roofRight.addComponent("model", { type: "box" });
    roofRight.setLocalScale(roofPanelWidth, 0.12, roofLength);
    roofRight.setLocalPosition(halfWidth / 2, panelCenterY, 0);
    roofRight.setLocalEulerAngles(0, 0, -roofAngle);
    roofRight.model.material = roofMat;
    house.addChild(roofRight);

    // Door
    const door = new pc.Entity("Door");
    door.addComponent("model", { type: "box" });
    door.setLocalScale(1, 1.8, 0.1);
    door.setLocalPosition(0, 0.9, 2.65);

    const doorMat = new pc.StandardMaterial();
    doorMat.diffuse = new pc.Color(0.2, 0.15, 0.08);
    doorMat.update();
    door.model.material = doorMat;
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
      windowMat.diffuse = new pc.Color(0.5, 0.6, 0.7);
      windowMat.emissive = new pc.Color(0.8, 0.7, 0.4);
      windowMat.opacity = 0.8;
      windowMat.blendType = pc.BLEND_NORMAL;
      windowMat.update();
      window.model.material = windowMat;
      house.addChild(window);
    });

    // Add fence and garden
    this.createHouseFence(house);
    this.createGardenPatch(house);

    house.setPosition(x, 0, z);
    house.setEulerAngles(0, rotation, 0);
    this.app.root.addChild(house);
  }

  /**
   * Create wooden fence around house
   */
  private createHouseFence(house: PCEntity): void {
    if (!this.app) return;

    const fenceMat = this.getMaterial({
      name: "WoodenFence",
      diffuse: new (window as any).pc.Color(0.3, 0.22, 0.15),
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

    const pc = (window as any).pc;
    postPositions.forEach((pos, idx) => {
      const post = new pc.Entity(`FencePost-${idx}`);
      post.addComponent("model", { type: "box" });
      post.setLocalScale(0.12, 0.8, 0.12);
      post.setLocalPosition(pos.x, 0.4, pos.z);
      post.model.material = fenceMat;
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
      railL.model.material = fenceMat;
      house.addChild(railL);

      // Right side
      const railR = new pc.Entity(`FenceRail-R-${idx}`);
      railR.addComponent("model", { type: "box" });
      railR.setLocalScale(0.08, 0.08, 6.5);
      railR.setLocalPosition(fenceDistance, height, 0);
      railR.model.material = fenceMat;
      house.addChild(railR);

      // Back side
      const railB = new pc.Entity(`FenceRail-B-${idx}`);
      railB.addComponent("model", { type: "box" });
      railB.setLocalScale(6.5, 0.08, 0.08);
      railB.setLocalPosition(0, height, -fenceDistance);
      railB.model.material = fenceMat;
      house.addChild(railB);

      // Front side (with gate opening)
      const railFL = new pc.Entity(`FenceRail-FL-${idx}`);
      railFL.addComponent("model", { type: "box" });
      railFL.setLocalScale(2, 0.08, 0.08);
      railFL.setLocalPosition(-2.5, height, fenceDistance);
      railFL.model.material = fenceMat;
      house.addChild(railFL);

      const railFR = new pc.Entity(`FenceRail-FR-${idx}`);
      railFR.addComponent("model", { type: "box" });
      railFR.setLocalScale(2, 0.08, 0.08);
      railFR.setLocalPosition(2.5, height, fenceDistance);
      railFR.model.material = fenceMat;
      house.addChild(railFR);
    });
  }

  /**
   * Create a small garden patch next to house
   */
  private createGardenPatch(house: PCEntity): void {
    if (!this.app) return;
    const pc = (window as any).pc;

    const gardenMat = this.getMaterial({
      name: "GardenSoil",
      diffuse: new pc.Color(0.2, 0.15, 0.1),
      shininess: 1,
    });

    const garden = new pc.Entity("Garden");
    garden.addComponent("model", { type: "box" });
    garden.setLocalScale(2, 0.05, 2);
    garden.setLocalPosition(-3, 0.025, -3);
    garden.model.material = gardenMat;
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
      plant.model.material = plantMat;
      house.addChild(plant);
    }
  }

  /**
   * Create church
   */
  private createChurch(x: number, z: number): void {
    if (!this.app) return;
    const pc = (window as any).pc;

    const church = new pc.Entity("Church");

    // Main base
    const base = new pc.Entity("Base");
    base.addComponent("model", { type: "box" });
    base.setLocalScale(8, 6, 10);
    base.setLocalPosition(0, 3, 0);

    const stoneMat = new pc.StandardMaterial();
    stoneMat.diffuse = new pc.Color(0.55, 0.55, 0.58);
    stoneMat.specular = new pc.Color(0.1, 0.1, 0.1);
    stoneMat.shininess = 5;
    stoneMat.update();
    base.model.material = stoneMat;
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
    roofLeft.model.material = roofMat;
    church.addChild(roofLeft);

    const roofRight = new pc.Entity("RoofRight");
    roofRight.addComponent("model", { type: "box" });
    roofRight.setLocalScale(churchRoofPanelWidth, 0.2, churchRoofLength);
    roofRight.setLocalPosition(churchHalfWidth / 2, churchPanelCenterY, 0);
    roofRight.setLocalEulerAngles(0, 0, -churchRoofAngle);
    roofRight.model.material = roofMat;
    church.addChild(roofRight);

    // Bell tower
    const tower = new pc.Entity("Tower");
    tower.addComponent("model", { type: "box" });
    tower.setLocalScale(2.5, 8, 2.5);
    tower.setLocalPosition(0, 7, -3.5);
    tower.model.material = stoneMat;
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
      window.model.material = towerWindowMat;
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
    spire.model.material = spireMat;
    church.addChild(spire);

    // Cross on top
    const crossV = new pc.Entity("CrossVertical");
    crossV.addComponent("model", { type: "box" });
    crossV.setLocalScale(0.15, 1.2, 0.15);
    crossV.setLocalPosition(0, 14.6, -3.5);

    const crossMat = new pc.StandardMaterial();
    crossMat.diffuse = new pc.Color(0.8, 0.7, 0.3);
    crossMat.emissive = new pc.Color(0.4, 0.35, 0.15);
    crossMat.shininess = 80;
    crossMat.update();
    crossV.model.material = crossMat;
    church.addChild(crossV);

    const crossH = new pc.Entity("CrossHorizontal");
    crossH.addComponent("model", { type: "box" });
    crossH.setLocalScale(0.6, 0.15, 0.15);
    crossH.setLocalPosition(0, 14.3, -3.5);
    crossH.model.material = crossMat;
    church.addChild(crossH);

    // Main entrance
    const entrance = new pc.Entity("Entrance");
    entrance.addComponent("model", { type: "box" });
    entrance.setLocalScale(2.5, 3.5, 0.2);
    entrance.setLocalPosition(0, 1.75, 5.1);

    const doorMat = new pc.StandardMaterial();
    doorMat.diffuse = new pc.Color(0.15, 0.1, 0.05);
    doorMat.update();
    entrance.model.material = doorMat;
    church.addChild(entrance);

    church.setPosition(x, 0, z);
    this.app.root.addChild(church);
  }

  /**
   * Create well
   */
  private createWell(x: number, z: number): void {
    if (!this.app) return;
    const pc = (window as any).pc;

    const well = new pc.Entity("Well");

    // Base
    const base = new pc.Entity("Base");
    base.addComponent("model", { type: "cylinder" });
    base.setLocalScale(1.5, 1, 1.5);
    base.setLocalPosition(0, 0.5, 0);

    const baseMat = new pc.StandardMaterial();
    baseMat.diffuse = new pc.Color(0.4, 0.4, 0.45);
    baseMat.update();
    base.model.material = baseMat;
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
      post.model.material = postMat;
      well.addChild(post);
    }

    // Roof
    const roof = new pc.Entity("Roof");
    roof.addComponent("model", { type: "cone" });
    roof.setLocalScale(2, 1.2, 2);
    roof.setLocalPosition(0, 3.5, 0);

    const roofMat = new pc.StandardMaterial();
    roofMat.diffuse = new pc.Color(0.4, 0.2, 0.15);
    roofMat.update();
    roof.model.material = roofMat;
    well.addChild(roof);

    well.setPosition(x, 0, z);
    this.app.root.addChild(well);
  }

  /**
   * Create campfire with animated flames
   */
  /**
   * Create enhanced campfire with animated flames and particle effects
   */
  private createCampfire(): void {
    if (!this.app) return;
    const pc = (window as any).pc;

    // Main fire light with warmer, flickering color
    const fireLight = new pc.Entity("FireLight");
    fireLight.addComponent("light", {
      type: "point",
      color: new pc.Color(1, 0.4, 0.1),
      intensity: 4,
      range: 25,
      castShadows: true,
    });
    fireLight.setPosition(0, 1.2, 0);
    this.app.root.addChild(fireLight);

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
      stone.model.material = stoneMat;
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

      log.model.material = logMat;
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
    velocity: any;
    startScale: number;
    endScale: number;
  } {
    const pc = (window as any).pc;
    const entity = new pc.Entity("Particle");
    entity.addComponent("model", { type: "plane" });

    const particle = {
      entity,
      type,
      life: 0,
      maxLife: 0,
      velocity: new pc.Vec3(),
      startScale: 1,
      endScale: 0,
    };

    if (type === "flame") {
      particle.maxLife = 0.8 + Math.random() * 0.6;
      particle.startScale = 0.5 + Math.random() * 0.3;
      particle.endScale = 0.1;
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
      const flameModel = entity.model as any;
      if (flameModel) {
        flameModel.material = mat;
      }
    } else if (type === "smoke") {
      particle.maxLife = 2.0 + Math.random();
      particle.startScale = 0.3;
      particle.endScale = 1.5;
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
      const smokeModel = entity.model as any;
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
      const emberModel = entity.model as any;
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
      pos.add(p.velocity.clone().mulScalar(dt));
      p.entity.setPosition(pos);

      // Update scale
      const t = p.life / p.maxLife;
      const scale = p.startScale + (p.endScale - p.startScale) * t;
      p.entity.setLocalScale(scale, scale, scale);

      // Update opacity
      const opacity = 1 - t;
      const particleModel = p.entity.model as any;
      if (particleModel && particleModel.material) {
        particleModel.material.opacity = opacity;
        particleModel.material.update();
      }

      // Face camera
      if (this.app.root.findByName("Camera")) {
        const cam = this.app.root.findByName("Camera");
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
    const pc = (window as any).pc;
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

    // Update particle effects
    this.updateParticles(dt);

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
   * Update action buttons in the action panel
   */
  updateActionButtons(buttons: any[]): void {
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
      button.textContent = btn.label || btn.text;
      button.addEventListener("click", () => {
        if (btn.action && typeof btn.action === "function") {
          btn.action();
        }
      });
      (container as HTMLElement).appendChild(button);
    });
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
