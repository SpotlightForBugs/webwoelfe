/**
 * Webwölfe - Enhanced PlayCanvas Village Renderer
 *
 * Advanced 3D Village Renderer using PlayCanvas engine.
 * Features:
 * - PBR Materials with detailed textures
 * - Dynamic Lighting (Day/Night Cycle)
 * - Particle Systems (Fire, Fog, Fireflies)
 * - Detailed Player Avatars with role-based appearance
 * - 3D Name Labels
 * - Village Buildings (Houses, Church, Well, Fence)
 * - Smooth Camera Controls
 * - Enhanced atmospheric effects
 */

export default class Village3DPlayCanvas {
  constructor(containerId, raumCode, options = {}) {
    this.containerId = containerId;
    this.raumCode = raumCode;
    this.container = document.getElementById(containerId);
    this.players = [];
    this.playerEntities = new Map();
    this.playerLabels = new Map();
    this.buildings = [];
    this.isNight = true;
    this.onPlayerClick = null;
    this.deadMaterial = null; // Cache for dead player material
    this.materialCache = new Map();

    // Target camera values for smoothing
    this.targetCameraAngle = 0;
    this.targetCameraHeight = 15;
    this.targetCameraRadius = 25;

    // Default camera settings - adjust for lobby vs game mode
    if (options.lobbyMode) {
      this.defaultCameraAngle = 0;
      this.defaultCameraHeight = 20;
      this.defaultCameraRadius = 18;
    } else {
      this.defaultCameraAngle = 0;
      this.defaultCameraHeight = 15;
      this.defaultCameraRadius = 25;
    }

    this.targetCameraAngle = this.defaultCameraAngle;
    this.targetCameraHeight = this.defaultCameraHeight;
    this.targetCameraRadius = this.defaultCameraRadius;

    // Lobby mode - simplified view with no buildings/environment
    this.isLobbyMode = options.lobbyMode || false;

    // Player layout mode: 'circle', 'double_circle', 'clusters', 'grid'
    this.layoutMode = "circle";

    // Track sleeping/inactive players for day/night cycle
    this.sleepingPlayers = new Set();

    // Role colors for player appearance - Loaded dynamically from API
    this.roleColors = {
      default: new pc.Color(0.3, 0.5, 0.8), // Same as Dorfbewohner - default fallback
    };

    // Role model definitions - Loaded dynamically from API
    this.roleModels = {};

    // Load role colors and models from API
    this.loadRoleDataFromAPI();

    if (!this.container) {
      console.warn("Village3D container not found:", containerId);
      return;
    }

    this.init();
  }

  // Load role colors and model definitions dynamically from API
  async loadRoleDataFromAPI() {
    try {
      const response = await fetch("/api/roles");
      const data = await response.json();

      if (data.success && data.roles) {
        // Convert hex colors from API to PlayCanvas Color objects
        // Also store model definitions
        data.roles.forEach((role) => {
          const roleName = role.name;

          // Load color
          const hexColor = role.farbe;
          if (hexColor && hexColor.startsWith("#")) {
            // Convert hex to RGB (0-1 range)
            const r = parseInt(hexColor.slice(1, 3), 16) / 255;
            const g = parseInt(hexColor.slice(3, 5), 16) / 255;
            const b = parseInt(hexColor.slice(5, 7), 16) / 255;
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

        // Refresh players with new role data if they exist
        if (this.players && this.players.length > 0) {
          console.log("[Village3D] Refreshing players with loaded role data...");

          // Destroy existing entities so they get recreated with role features
          this.playerEntities.forEach((entity) => entity.destroy());
          this.playerEntities.clear();
          this.playerLabels.forEach((label) => label.destroy());
          this.playerLabels.clear();

          this.setPlayers(this.players);
        }
      }
    } catch (error) {
      console.warn(
        "[Village3D] Failed to load role data from API, using defaults:",
        error,
      );
      // Fallback to some basic colors if API fails
      this.roleColors = {
        Werwolf: new pc.Color(0.6, 0.1, 0.1),
        Dorfbewohner: new pc.Color(0.3, 0.5, 0.8),
        Seherin: new pc.Color(0.5, 0.3, 0.9),
        Hexe: new pc.Color(0.2, 0.7, 0.3),
        default: new pc.Color(0.3, 0.5, 0.8),
      };
    }
  }

  init() {
    // Create canvas
    this.canvas = document.createElement("canvas");
    this.canvas.style.width = "100%";
    this.canvas.style.height = "100%";
    this.canvas.style.display = "block";
    this.canvas.tabIndex = 0; // Make canvas focusable
    this.container.appendChild(this.canvas);

    // Initialize PlayCanvas with antialiasing for sharper rendering
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
      },
    });

    this.app.start();
    // Use NONE to respect container size, not FILL_WINDOW which ignores it
    this.app.setCanvasFillMode(pc.FILLMODE_NONE);
    this.app.setCanvasResolution(pc.RESOLUTION_AUTO);

    // Resize handler to match container size with device pixel ratio for sharpness
    const resizeCanvas = () => {
      if (this.container && this.canvas) {
        const dpr = window.devicePixelRatio || 1;
        const width = this.container.clientWidth;
        const height = this.container.clientHeight;
        // Set canvas buffer size to account for device pixel ratio for sharper rendering
        this.canvas.width = width * dpr;
        this.canvas.height = height * dpr;
        this.app.resizeCanvas();
      }
    };

    window.addEventListener("resize", resizeCanvas);
    // Initial resize to fit container
    resizeCanvas();

    // Create Scene
    this.createScene();

    // Input handling
    this.setupInput();

    // Register update for animation
    this.updateBound = (dt) => {
      try {
        this.update(dt);
      } catch (e) {
        console.error("[Village3D] Update error:", e);
      }
    };
    this.app.on("update", this.updateBound);

    // Initialize fullscreen UI overlay system
    this.initFullscreenUI();
  }

  createScene() {
    // Camera with enhanced settings
    this.camera = new pc.Entity("Camera");
    this.camera.addComponent("camera", {
      clearColor: new pc.Color(0.02, 0.02, 0.06), // Deeper night blue
      farClip: 300,
      fov: 50, // Slightly wider for more immersive view
      nearClip: 0.1,
    });

    // Enhanced Fog for atmospheric depth
    try {
      if (this.app.scene.rendering) {
        this.app.scene.rendering.fog = pc.FOG_EXP2;
        this.app.scene.rendering.fogColor = new pc.Color(0.02, 0.03, 0.08);
        this.app.scene.rendering.fogDensity = 0.008;
        // Enhanced exposure for better dynamic range
        this.app.scene.rendering.exposure = 1.2;
        this.app.scene.rendering.gammaCorrection = pc.GAMMA_SRGB;
        this.app.scene.rendering.toneMapping = pc.TONEMAP_ACES;
      } else if (this.app.scene.settings) {
        this.app.scene.settings.render.fog = pc.FOG_EXP2;
        this.app.scene.settings.render.fogColor = new pc.Color(0.02, 0.03, 0.08);
        this.app.scene.settings.render.fogDensity = 0.008;
      }
    } catch (e) {
      console.debug("Fog settings not fully available:", e.message);
    }

    // Enhanced Ambient Light with color
    try {
      if (this.app.scene.rendering) {
        this.app.scene.rendering.ambientLight = new pc.Color(0.08, 0.1, 0.18);
      } else {
        this.app.scene.ambientLight = new pc.Color(0.08, 0.1, 0.18);
      }
    } catch (e) {
      console.debug("Could not set ambientLight:", e.message);
    }

    this.camera.setPosition(0, this.defaultCameraHeight, this.defaultCameraRadius);
    this.camera.lookAt(0, 0, 0);
    this.app.root.addChild(this.camera);

    // Orbit Controls
    this.cameraAngle = this.defaultCameraAngle;
    this.cameraHeight = this.defaultCameraHeight;
    this.cameraRadius = this.defaultCameraRadius;
    this.targetCameraAngle = this.cameraAngle;
    this.targetCameraHeight = this.cameraHeight;
    this.targetCameraRadius = this.cameraRadius;
    this.targetPosition = new pc.Vec3(0, 0, 0);

    // === SKY DOME - Gradient night sky ===
    this.createSkyDome();

    // === CELESTIAL BODIES ===
    this.createCelestialBodies();

    // Directional Light (Moon/Sun) - Enhanced with warmer undertones
    this.light = new pc.Entity("DirectionalLight");
    this.light.addComponent("light", {
      type: "directional",
      color: new pc.Color(0.6, 0.7, 0.95), // Slightly bluer moonlight
      intensity: 0.8,
      castShadows: true,
      shadowBias: 0.15,
      normalOffsetBias: 0.04,
      shadowDistance: 100,
      shadowResolution: 2048,
    });
    this.light.setLocalEulerAngles(50, 25, 0);
    this.app.root.addChild(this.light);

    // Fill light - subtle warm bounce from ground
    this.fillLight = new pc.Entity("FillLight");
    this.fillLight.addComponent("light", {
      type: "directional",
      color: new pc.Color(0.25, 0.22, 0.35), // Subtle purple-blue fill
      intensity: 0.25,
      castShadows: false,
    });
    this.fillLight.setLocalEulerAngles(-35, 190, 0);
    this.app.root.addChild(this.fillLight);

    // Rim light - creates silhouette highlights
    this.rimLight = new pc.Entity("RimLight");
    this.rimLight.addComponent("light", {
      type: "directional",
      color: new pc.Color(0.4, 0.5, 0.7),
      intensity: 0.15,
      castShadows: false,
    });
    this.rimLight.setLocalEulerAngles(10, -90, 0);
    this.app.root.addChild(this.rimLight);

    // Ground with enhanced detail
    this.createDetailedGround();

    // Village Buildings
    this.createVillageBuildings();

    // Campfire (center) - enhanced version
    if (this.isLobbyMode) {
      this.createSimpleCampfire();
    } else {
      this.createEnhancedCampfire();
    }

    // Environment (Trees, Stones, Fence)
    this.createEnhancedEnvironment();

    // Atmospheric effects (fog, fireflies, etc.)
    this.createEnhancedAtmosphericEffects();

    // Ground fog particles
    this.createGroundFog();
  }

  /**
   * Creates a gradient sky dome for atmospheric background
   */
  createSkyDome() {
    // Large inverted sphere for sky
    this.skyDome = new pc.Entity("SkyDome");
    this.skyDome.addComponent("model", { type: "sphere" });
    this.skyDome.setLocalScale(-150, -150, -150); // Inverted (inside-out)
    this.skyDome.setPosition(0, 0, 0);

    // Night sky gradient material
    const skyMat = new pc.StandardMaterial();
    skyMat.diffuse = new pc.Color(0.02, 0.03, 0.08); // Deep night blue
    skyMat.emissive = new pc.Color(0.015, 0.025, 0.06); // Subtle glow
    skyMat.useLighting = false;
    skyMat.cull = pc.CULLFACE_FRONT; // Render inside
    skyMat.update();
    this.skyDome.model.material = skyMat;
    this.skyMaterial = skyMat;

    this.app.root.addChild(this.skyDome);

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
        starMat.emissive = new pc.Color(brightness, brightness * 0.9, brightness * 0.7); // Warm
      } else if (warmth < 0.6) {
        starMat.emissive = new pc.Color(brightness * 0.8, brightness * 0.85, brightness); // Blue
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
   * Creates moon and optional sun for day/night
   */
  createCelestialBodies() {
    // Moon
    this.moon = new pc.Entity("Moon");
    this.moon.addComponent("model", { type: "sphere" });
    this.moon.setLocalScale(8, 8, 8);
    this.moon.setPosition(60, 80, -50);

    const moonMat = new pc.StandardMaterial();
    moonMat.diffuse = new pc.Color(0.95, 0.95, 0.9);
    moonMat.emissive = new pc.Color(0.7, 0.75, 0.85);
    moonMat.useLighting = false;
    moonMat.update();
    this.moon.model.material = moonMat;
    this.moonMaterial = moonMat;

    this.app.root.addChild(this.moon);

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
    this.moonGlow = moonGlow;

    // Sun (hidden by default, shown during day)
    this.sun = new pc.Entity("Sun");
    this.sun.addComponent("model", { type: "sphere" });
    this.sun.setLocalScale(12, 12, 12);
    this.sun.setPosition(80, 100, 60);
    this.sun.enabled = false;

    const sunMat = new pc.StandardMaterial();
    sunMat.emissive = new pc.Color(1, 0.95, 0.7);
    sunMat.useLighting = false;
    sunMat.update();
    this.sun.model.material = sunMat;

    this.app.root.addChild(this.sun);

    // Sun rays/glow
    this.sunGlow = new pc.Entity("SunGlow");
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
    this.sunGlow.model.material = sunGlowMat;

    this.app.root.addChild(this.sunGlow);
  }

  createDetailedGround() {
    // Main ground - varied grass terrain with vertex coloring simulation
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

    // Random grass patches for variation (simple planes slightly above ground)
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
      shininess: 5,
    });
    centerSquare.model.material = squareMat;
    this.app.root.addChild(centerSquare);

    // Add some decorative stones around the square
    if (!this.isLobbyMode) {
      this.createSquareDecorations();
    }
  }

  createVillagePaths() {
    // Main cross paths - made more irregular
    const pathPositions = [
      { x: 0, z: 0, scaleX: 2.5, scaleZ: 40, rotation: 0 },
      { x: 0, z: 0, scaleX: 40, scaleZ: 2.5, rotation: 0 },
      { x: -15, z: -12, scaleX: 12, scaleZ: 2, rotation: 25 },
      { x: 15, z: 10, scaleX: 10, scaleZ: 2, rotation: -35 },
      { x: -8, z: 15, scaleX: 8, scaleZ: 2, rotation: 15 },
      { x: 12, z: -10, scaleX: 9, scaleZ: 2, rotation: -20 },
      // Ring path
      { x: 18, z: 18, scaleX: 15, scaleZ: 2, rotation: 45 },
      { x: -18, z: 18, scaleX: 15, scaleZ: 2, rotation: -45 },
      { x: 18, z: -18, scaleX: 15, scaleZ: 2, rotation: -45 },
    ];

    pathPositions.forEach((pos, idx) => {
      const path = new pc.Entity(`Path-${idx}`);
      path.addComponent("model", { type: "box" });
      path.setLocalScale(pos.scaleX, 0.02, pos.scaleZ);
      path.setPosition(pos.x, 0.02, pos.z);
      path.setEulerAngles(0, pos.rotation, 0);

      const pathMat = this.getMaterial({
        name: `DirtPath-${idx % 3}`,
        diffuse: new pc.Color(0.24, 0.18, 0.12),
        specular: new pc.Color(0.02, 0.02, 0.02),
        shininess: 2,
      });
      path.model.material = pathMat;
      this.app.root.addChild(path);
    });
  }

  createSquareDecorations() {
    // Market stalls/benches - enhanced with details
    const stallPositions = [
      { x: -9, z: 0, rotation: 90 },
      { x: 9, z: 0, rotation: -90 },
      { x: 0, z: -9, rotation: 0 },
      { x: 0, z: 9, rotation: 180 },
    ];

    stallPositions.forEach((pos, idx) => {
      const group = new pc.Entity(`StallGroup-${idx}`);
      group.setPosition(pos.x, 0, pos.z);
      group.setEulerAngles(0, pos.rotation, 0);
      this.app.root.addChild(group);

      // Bench
      const bench = new pc.Entity("Bench");
      bench.addComponent("model", { type: "box" });
      bench.setLocalScale(2.5, 0.4, 0.8);
      bench.setLocalPosition(0, 0.2, 0);
      const woodMat = this.getMaterial({
        name: "OldWood",
        diffuse: new pc.Color(0.2, 0.15, 0.1),
      });
      bench.model.material = woodMat;
      group.addChild(bench);

      // Random props on/around bench
      if (Math.random() > 0.3) {
        const prop = new pc.Entity("Prop");
        const type = Math.random();
        if (type < 0.33) {
          // Crate
          prop.addComponent("model", { type: "box" });
          prop.setLocalScale(0.6, 0.6, 0.6);
          prop.setLocalPosition(1.5, 0.3, 0);
        } else if (type < 0.66) {
          // Barrel
          prop.addComponent("model", { type: "cylinder" });
          prop.setLocalScale(0.5, 0.7, 0.5);
          prop.setLocalPosition(-1.5, 0.35, 0.2);
        } else {
          // Sack
          prop.addComponent("model", { type: "sphere" });
          prop.setLocalScale(0.5, 0.4, 0.5);
          prop.setLocalPosition(1.2, 0.2, -0.2);
        }
        prop.model.material = woodMat;
        group.addChild(prop);
      }
    });

    // Scattered debris/rocks
    for (let i = 0; i < 15; i++) {
      const rock = new pc.Entity("Pebble");
      rock.addComponent("model", { type: "sphere" });
      const scale = 0.1 + Math.random() * 0.15;
      rock.setLocalScale(scale, scale * 0.6, scale);
      const radius = 8 + Math.random() * 6;
      const angle = Math.random() * Math.PI * 2;
      rock.setPosition(Math.cos(angle) * radius, 0.05, Math.sin(angle) * radius);

      const rockMat = this.getMaterial({
        name: "Pebble",
        diffuse: new pc.Color(0.3, 0.3, 0.35),
      });
      rock.model.material = rockMat;
      this.app.root.addChild(rock);
    }
  }

  createEnhancedCampfire() {
    // Main fire light with warmer, flickering color
    this.fireLight = new pc.Entity("FireLight");
    this.fireLight.addComponent("light", {
      type: "point",
      color: new pc.Color(1, 0.4, 0.1),
      intensity: 4,
      range: 25,
      castShadows: true,
      shadowNormalOffset: 0.02,
      shadowBias: 0.1,
    });
    this.fireLight.setPosition(0, 1.2, 0);
    this.app.root.addChild(this.fireLight);

    // Add a second, smaller light for the core heat (intense yellow)
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
      stone.addComponent("model", { type: "sphere" }); // Use spheres for rounder stones
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

    // Crossed Logs
    const logMat = this.getMaterial({
      name: "BurntLog",
      diffuse: new pc.Color(0.15, 0.1, 0.05),
      emissive: new pc.Color(0.2, 0.05, 0), // Glowing embers
    });

    for (let i = 0; i < 4; i++) {
      const log = new pc.Entity("Log");
      log.addComponent("model", { type: "cylinder" });
      log.setLocalScale(0.25, 1.6, 0.25);

      // Stacked teepee style
      const angle = (i / 4) * Math.PI * 2;
      log.setLocalPosition(Math.sin(angle) * 0.6, 0.6, Math.cos(angle) * 0.6);
      // Tilt inward
      log.lookAt(0, 1.2, 0);
      log.rotateLocal(90, 0, 0);

      log.model.material = logMat;
      this.app.root.addChild(log);
    }

    // Particle System for Fire (Manual plane particles)
    this.fireParticles = [];
    // 1. Core flames (yellow/white)
    // 2. Mid flames (orange/red)
    // 3. Smoke (dark gray)
    // 4. Embers (tiny bright sparks)

    // Initialize particles array
    this.particles = [];

    // Create a particle spawner
    this.particleSpawner = {
      timer: 0,
      spawn: (dt) => {
        this.spawnFireParticles(dt);
      },
    };
    // We'll hook this up in update()
  }

  spawnFireParticles(dt) {
    // Spawn limits
    const maxParticles = 60;
    if (this.particles.length >= maxParticles) return;

    // Spawn Rate
    const spawnRate = 0.05; // Seconds per particle
    this.particleSpawner.timer += dt;

    while (this.particleSpawner.timer > spawnRate) {
      this.particleSpawner.timer -= spawnRate;

      const type = Math.random();
      let p;

      if (type < 0.6) {
        // Flame
        p = this.createParticle("flame");
      } else if (type < 0.9) {
        // Smoke
        p = this.createParticle("smoke");
      } else {
        // Ember
        p = this.createParticle("ember");
      }

      this.particles.push(p);
      this.app.root.addChild(p.entity);
    }
  }

  createParticle(type) {
    const entity = new pc.Entity("Particle");
    entity.addComponent("model", { type: "plane" });

    const p = {
      entity: entity,
      type: type,
      life: 0,
      maxLife: 0,
      velocity: new pc.Vec3(),
      startScale: 1,
      endScale: 0,
      startColor: new pc.Color(),
      endColor: new pc.Color(),
    };

    if (type === "flame") {
      p.maxLife = 0.8 + Math.random() * 0.6;
      p.startScale = 0.5 + Math.random() * 0.3;
      p.endScale = 0.1;
      p.velocity.set(
        (Math.random() - 0.5) * 0.5,
        1.5 + Math.random(),
        (Math.random() - 0.5) * 0.5,
      );
      entity.setPosition(
        (Math.random() - 0.5) * 0.5,
        0.2,
        (Math.random() - 0.5) * 0.5,
      );

      // Flame material (additive)
      const mat = this.getMaterial({
        name: "FlameMat",
        emissive: new pc.Color(1, 0.8, 0.2),
        opacity: 0.8,
        blendType: pc.BLEND_ADDITIVE,
      });
      entity.model.material = mat;
    } else if (type === "smoke") {
      p.maxLife = 2.0 + Math.random();
      p.startScale = 0.3;
      p.endScale = 1.5;
      p.velocity.set(
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
        blendType: pc.BLEND_NORMAL,
      });
      entity.model.material = mat;
    } else if (type === "ember") {
      p.maxLife = 1.5 + Math.random();
      p.startScale = 0.05;
      p.endScale = 0.0;
      p.velocity.set(
        (Math.random() - 0.5) * 2,
        2 + Math.random() * 2,
        (Math.random() - 0.5) * 2,
      );
      entity.setPosition(0, 0.5, 0);

      const mat = this.getMaterial({
        name: "EmberMat",
        emissive: new pc.Color(1, 0.6, 0.1),
        opacity: 1,
        blendType: pc.BLEND_ADDITIVE,
      });
      entity.model.material = mat;
    }

    entity.setLocalEulerAngles(
      Math.random() * 360,
      Math.random() * 360,
      Math.random() * 360,
    );
    return p;
  }

  createEnhancedEnvironment() {
    // Trees with more variety and foliage
    const treeCount = this.isLobbyMode ? 30 : 60;
    for (let i = 0; i < treeCount; i++) {
      // Leave clearing in center
      const angle = Math.random() * Math.PI * 2;
      const radius = this.isLobbyMode
        ? 20 + Math.random() * 20
        : 35 + Math.random() * 45;

      const x = Math.cos(angle) * radius;
      const z = Math.sin(angle) * radius;

      const treeHeight = 4 + Math.random() * 4;
      this.createDetailedTree(x, z, treeHeight);
    }

    // Create dense bushes around the perimeter
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
      this.createRock(Math.cos(angle) * radius, Math.sin(angle) * radius);
    }
  }

  createDetailedTree(x, z, height) {
    const tree = new pc.Entity("Tree");

    // Twisted Trunk
    const trunk = new pc.Entity("Trunk");
    trunk.addComponent("model", { type: "cylinder" });
    trunk.setLocalScale(
      0.5 + Math.random() * 0.3,
      height,
      0.5 + Math.random() * 0.3,
    );
    trunk.setLocalPosition(0, height / 2, 0);
    // Slight lean
    trunk.setLocalEulerAngles(
      Math.random() * 10 - 5,
      0,
      Math.random() * 10 - 5,
    );

    const trunkMat = this.getMaterial({
      name: "Bark",
      diffuse: new pc.Color(0.25, 0.2, 0.15),
      specular: new pc.Color(0.05, 0.05, 0.05),
    });
    trunk.model.material = trunkMat;
    tree.addChild(trunk);

    // Irregular Foliage Clumps
    const foliageMat = this.getMaterial({
      name: "DeepFoliage",
      diffuse: new pc.Color(0.05, 0.15 + Math.random() * 0.1, 0.05),
      specular: new pc.Color(0.01, 0.05, 0.01),
    });

    const layers = 3;
    for (let i = 0; i < layers; i++) {
      const layerY = height * (0.6 + i * 0.2);
      const layerW = (3 - i) * 1.2;

      const clumps = 2 + i + Math.floor(Math.random() * 2);
      for (let j = 0; j < clumps; j++) {
        const clump = new pc.Entity("FoliageClump");
        clump.addComponent("model", { type: "sphere" }); // Sphere is smoother
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

  createEnhancedAtmosphericEffects() {
    // Fireflies - smaller, more numerous, pulsing
    this.fireflies = [];
    const count = 40;
    for (let i = 0; i < count; i++) {
      const firefly = new pc.Entity("Firefly");
      firefly.addComponent("light", {
        type: "point",
        color: new pc.Color(0.6, 1.0, 0.4),
        intensity: 0.8,
        range: 2,
        castShadows: false,
      });
      // Add visible speck
      const speck = new pc.Entity("Speck");
      speck.addComponent("model", { type: "sphere" });
      speck.setLocalScale(0.05, 0.05, 0.05);
      const mat = new pc.StandardMaterial();
      mat.emissive = new pc.Color(0.8, 1, 0.5);
      mat.useLighting = false;
      mat.update();
      speck.model.material = mat;
      firefly.addChild(speck);

      const angle = Math.random() * Math.PI * 2;
      const radius = 5 + Math.random() * 30;
      firefly.setPosition(
        Math.cos(angle) * radius,
        0.5 + Math.random() * 2.5,
        Math.sin(angle) * radius,
      );

      this.app.root.addChild(firefly);
      this.fireflies.push({
        entity: firefly,
        angle: angle,
        radius: radius,
        height: firefly.getPosition().y,
        speed: 0.2 + Math.random() * 0.4,
        phase: Math.random() * Math.PI * 2,
      });
    }
  }

  createGroundFog() {
    // Disabled manual fog planes due to visual artifacts (Z-fighting/geometry clipping).
    // Relying on global scene fog instead found in setTimeOfDay().
    this.fogPlanes = [];
  }

  // Material caching helper
  getMaterial(options) {
    const key = options.name || JSON.stringify(options);
    if (this.materialCache.has(key)) {
      return this.materialCache.get(key);
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

  createVillageBuildings() {
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
      this.createHouse(pos.x, pos.z, pos.rot, idx);
    });

    // Church (special building)
    this.createChurch(-12, -20);

    // Well (near center)
    this.createWell(12, 12);
  }

  createHouse(x, z, rotation, index) {
    const house = new pc.Entity(`House-${index}`);

    // Medieval timber-framed house base (stone lower floor)
    const stoneBase = new pc.Entity("StoneBase");
    stoneBase.addComponent("model", { type: "box" });
    stoneBase.setLocalScale(4.2, 1.5, 5.2);
    stoneBase.setLocalPosition(0, 0.75, 0);

    const stoneMat = new pc.StandardMaterial();
    stoneMat.diffuse = new pc.Color(0.45, 0.45, 0.48); // Stone gray
    stoneMat.specular = new pc.Color(0.1, 0.1, 0.1);
    stoneMat.shininess = 5;
    stoneMat.update();
    stoneBase.model.material = stoneMat;
    house.addChild(stoneBase);

    // Upper floor (timber and plaster)
    const upperFloor = new pc.Entity("UpperFloor");
    upperFloor.addComponent("model", { type: "box" });
    upperFloor.setLocalScale(4, 2, 5);
    upperFloor.setLocalPosition(0, 2.5, 0);

    const plasterMat = new pc.StandardMaterial();
    const hue = 0.05 + Math.random() * 0.1;
    plasterMat.diffuse = new pc.Color(0.85 + hue, 0.8 + hue, 0.7 + hue); // Off-white plaster
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
      beamMat.diffuse = new pc.Color(0.25, 0.15, 0.08); // Dark wood
      beamMat.update();
      beam.model.material = beamMat;
      house.addChild(beam);
    }

    // Timber beams (horizontal)
    for (let i = 0; i < 3; i++) {
      const beam = new pc.Entity(`Beam-H-${i}`);
      beam.addComponent("model", { type: "box" });
      beam.setLocalScale(4, 0.15, 0.15);
      beam.setLocalPosition(0, 1.8 + i * 0.7, 2.55);

      const beamMat = new pc.StandardMaterial();
      beamMat.diffuse = new pc.Color(0.25, 0.15, 0.08);
      beamMat.update();
      beam.model.material = beamMat;
      house.addChild(beam);
    }

    // Roof (proper gabled roof with two slopes)
    // House dimensions: 4 wide (X), 5 deep (Z), upper floor top at Y=3.5
    const roofAngle = 35; // degrees - slightly less steep for better look
    const houseWidth = 4.2; // Width of house
    const houseDepth = 5.2; // Depth of house
    const roofOverhang = 0.5; // How much roof extends past walls
    const roofBaseY = 3.5; // Top of upper floor

    // Calculate roof panel dimensions
    const roofRad = (roofAngle * Math.PI) / 180;
    const halfWidth = houseWidth / 2 + roofOverhang;
    const roofPanelWidth = halfWidth / Math.cos(roofRad); // Width of angled panel
    const roofPeakHeight = halfWidth * Math.tan(roofRad); // Height at peak
    const roofLength = houseDepth + roofOverhang * 2; // Length extends past house

    const roofMat = new pc.StandardMaterial();
    roofMat.diffuse = new pc.Color(0.4, 0.22, 0.15); // Dark terracotta/brown
    roofMat.update();

    // Left roof panel - rotates around its local center, so we need to offset
    // After rotation, the panel's edge should be at x=0, y=roofBaseY+roofPeakHeight
    const roofLeft = new pc.Entity("RoofLeft");
    roofLeft.addComponent("model", { type: "box" });
    roofLeft.setLocalScale(roofPanelWidth, 0.12, roofLength);
    // Position the center of the rotated panel
    // Panel center in local space before rotation: (roofPanelWidth/2, 0, 0)
    // After rotating by roofAngle around Z:
    // x' = (roofPanelWidth/2) * cos(angle) = halfWidth/2
    // y' = (roofPanelWidth/2) * sin(angle) = roofPeakHeight/2
    const panelCenterX = -halfWidth / 2;
    const panelCenterY = roofBaseY + roofPeakHeight / 2;
    roofLeft.setLocalPosition(panelCenterX, panelCenterY, 0);
    roofLeft.setLocalEulerAngles(0, 0, roofAngle);
    roofLeft.model.material = roofMat;
    house.addChild(roofLeft);

    // Right roof panel (mirror of left)
    const roofRight = new pc.Entity("RoofRight");
    roofRight.addComponent("model", { type: "box" });
    roofRight.setLocalScale(roofPanelWidth, 0.12, roofLength);
    roofRight.setLocalPosition(halfWidth / 2, panelCenterY, 0);
    roofRight.setLocalEulerAngles(0, 0, -roofAngle);
    roofRight.model.material = roofMat;
    house.addChild(roofRight);

    // Roof ridge beam at the peak
    const roofPeak = new pc.Entity("RoofPeak");
    roofPeak.addComponent("model", { type: "box" });
    roofPeak.setLocalScale(0.2, 0.15, roofLength + 0.1);
    roofPeak.setLocalPosition(0, roofBaseY + roofPeakHeight + 0.05, 0);
    roofPeak.model.material = roofMat;
    house.addChild(roofPeak);

    // Gable walls (fill triangular area at front and back)
    const gableMat = plasterMat; // Same as upper floor
    [-1, 1].forEach((side, idx) => {
      const gable = new pc.Entity(`Gable-${idx}`);
      gable.addComponent("model", { type: "box" });
      // Approximate triangle with a box - make it smaller to look like a triangle
      gable.setLocalScale(houseWidth * 0.85, roofPeakHeight * 0.65, 0.12);
      gable.setLocalPosition(
        0,
        roofBaseY + roofPeakHeight * 0.32,
        side * (houseDepth / 2 + 0.06),
      );
      gable.model.material = gableMat;
      house.addChild(gable);
    });

    // Chimney
    const chimney = new pc.Entity("Chimney");
    chimney.addComponent("model", { type: "box" });
    chimney.setLocalScale(0.6, 1.8, 0.6);
    chimney.setLocalPosition(1.2, roofBaseY + roofPeakHeight + 0.5, 1);
    chimney.model.material = stoneMat;
    house.addChild(chimney);

    // Door (arched medieval style)
    const door = new pc.Entity("Door");
    door.addComponent("model", { type: "box" });
    door.setLocalScale(1, 1.8, 0.1);
    door.setLocalPosition(0, 0.9, 2.65);

    const doorMat = new pc.StandardMaterial();
    doorMat.diffuse = new pc.Color(0.2, 0.15, 0.08); // Dark oak
    doorMat.specular = new pc.Color(0.1, 0.08, 0.05);
    doorMat.update();
    door.model.material = doorMat;
    house.addChild(door);

    // Door arch
    const doorArch = new pc.Entity("DoorArch");
    doorArch.addComponent("model", { type: "box" });
    doorArch.setLocalScale(1.2, 0.3, 0.12);
    doorArch.setLocalPosition(0, 1.8, 2.65);
    doorArch.model.material = stoneMat;
    house.addChild(doorArch);

    // Windows (multiple)
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
      windowMat.diffuse = new pc.Color(0.5, 0.6, 0.7); // Glass blue
      windowMat.emissive = new pc.Color(0.8, 0.7, 0.4); // Warm candlelight glow
      windowMat.opacity = 0.8;
      windowMat.blendType = pc.BLEND_NORMAL;
      windowMat.update();
      window.model.material = windowMat;
      house.addChild(window);

      // Window cross divider
      const divider1 = new pc.Entity(`WindowDiv1-${idx}`);
      divider1.addComponent("model", { type: "box" });
      divider1.setLocalScale(0.05, 0.7, 0.05);
      divider1.setLocalPosition(pos.x, pos.y, pos.z + 0.05);
      const divMat = new pc.StandardMaterial();
      divMat.diffuse = new pc.Color(0.15, 0.1, 0.05);
      divMat.update();
      divider1.model.material = divMat;
      house.addChild(divider1);

      const divider2 = new pc.Entity(`WindowDiv2-${idx}`);
      divider2.addComponent("model", { type: "box" });
      divider2.setLocalScale(0.7, 0.05, 0.05);
      divider2.setLocalPosition(pos.x, pos.y, pos.z + 0.05);
      divider2.model.material = divMat;
      house.addChild(divider2);
    });

    // Shutters
    for (let i = 0; i < 2; i++) {
      const shutter = new pc.Entity(`Shutter-${i}`);
      shutter.addComponent("model", { type: "box" });
      shutter.setLocalScale(0.3, 0.7, 0.05);
      shutter.setLocalPosition(i === 0 ? -1.6 : -0.8, 2.5, 2.63);

      const shutterMat = new pc.StandardMaterial();
      shutterMat.diffuse = new pc.Color(0.25, 0.15, 0.08);
      shutterMat.update();
      shutter.model.material = shutterMat;
      house.addChild(shutter);
    }

    // Add wooden fence around house
    this.createHouseFence(house);

    // Add small garden patch
    if (Math.random() > 0.5) {
      this.createGardenPatch(house);
    }

    house.setPosition(x, 0, z);
    house.setEulerAngles(0, rotation, 0);
    this.app.root.addChild(house);
    this.buildings.push(house);
  }

  /**
   * Create a wooden fence around a house
   */
  createHouseFence(house) {
    const fenceMat = this.getMaterial({
      name: "WoodenFence",
      diffuse: new pc.Color(0.3, 0.22, 0.15),
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
  createGardenPatch(house) {
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

  createChurch(x, z) {
    const church = new pc.Entity("Church");

    // Main stone base (Romanesque style)
    const base = new pc.Entity("Base");
    base.addComponent("model", { type: "box" });
    base.setLocalScale(8, 6, 10);
    base.setLocalPosition(0, 3, 0);

    const stoneMat = this.getMaterial({
      name: "ChurchStone",
      diffuse: new pc.Color(0.55, 0.55, 0.58),
      specular: new pc.Color(0.1, 0.1, 0.1),
      shininess: 5,
    });
    base.model.material = stoneMat;
    church.addChild(base);

    // Buttresses (support columns)
    for (let i = 0; i < 4; i++) {
      const buttress = new pc.Entity(`Buttress-${i}`);
      buttress.addComponent("model", { type: "box" });
      buttress.setLocalScale(0.6, 6.5, 0.8);
      const xPos = i < 2 ? -4.3 : 4.3;
      const zPos = i % 2 === 0 ? -4.5 : 4.5;
      buttress.setLocalPosition(xPos, 3.25, zPos);
      buttress.model.material = stoneMat;
      church.addChild(buttress);
    }

    // Gabled roof - properly calculated to meet at peak
    // Church base is 8 wide (X), 10 deep (Z), top at Y=6
    const churchRoofAngle = 35; // degrees
    const churchWidth = 8;
    const churchDepth = 10;
    const churchRoofOverhang = 0.5;
    const churchRoofBaseY = 6;

    const churchRoofRad = (churchRoofAngle * Math.PI) / 180;
    const churchHalfWidth = churchWidth / 2 + churchRoofOverhang;
    const churchRoofPanelWidth = churchHalfWidth / Math.cos(churchRoofRad);
    const churchRoofPeakHeight = churchHalfWidth * Math.tan(churchRoofRad);
    const churchRoofLength = churchDepth + churchRoofOverhang * 2;

    const roofMat = this.getMaterial({
      name: "ChurchRoof",
      diffuse: new pc.Color(0.28, 0.12, 0.08),
    });

    // Left roof panel
    const roofLeft = new pc.Entity("RoofLeft");
    roofLeft.addComponent("model", { type: "box" });
    roofLeft.setLocalScale(churchRoofPanelWidth, 0.2, churchRoofLength);
    const churchPanelCenterX = -churchHalfWidth / 2;
    const churchPanelCenterY = churchRoofBaseY + churchRoofPeakHeight / 2;
    roofLeft.setLocalPosition(churchPanelCenterX, churchPanelCenterY, 0);
    roofLeft.setLocalEulerAngles(0, 0, churchRoofAngle);
    roofLeft.model.material = roofMat;
    church.addChild(roofLeft);

    // Right roof panel
    const roofRight = new pc.Entity("RoofRight");
    roofRight.addComponent("model", { type: "box" });
    roofRight.setLocalScale(churchRoofPanelWidth, 0.2, churchRoofLength);
    roofRight.setLocalPosition(churchHalfWidth / 2, churchPanelCenterY, 0);
    roofRight.setLocalEulerAngles(0, 0, -churchRoofAngle);
    roofRight.model.material = roofMat;
    church.addChild(roofRight);

    // Roof ridge
    const ridge = new pc.Entity("Ridge");
    ridge.addComponent("model", { type: "box" });
    ridge.setLocalScale(0.3, 0.25, churchRoofLength + 0.2);
    ridge.setLocalPosition(0, churchRoofBaseY + churchRoofPeakHeight, 0);
    ridge.model.material = stoneMat;
    church.addChild(ridge);

    // Bell tower
    const tower = new pc.Entity("Tower");
    tower.addComponent("model", { type: "box" });
    tower.setLocalScale(2.5, 8, 2.5);
    tower.setLocalPosition(0, 7, -3.5);
    tower.model.material = stoneMat;
    church.addChild(tower);

    // Tower windows (arched)
    const towerWindowMat = this.getMaterial({
      name: "TowerWindow",
      diffuse: new pc.Color(0.2, 0.2, 0.3),
      opacity: 0.6,
      blendType: pc.BLEND_NORMAL,
    });

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

    // Tower roof (spire)
    const spire = new pc.Entity("Spire");
    spire.addComponent("model", { type: "cone" });
    spire.setLocalScale(2, 4, 2);
    spire.setLocalPosition(0, 12.5, -3.5);

    const spireMat = this.getMaterial({
      name: "SpireCopper",
      diffuse: new pc.Color(0.25, 0.35, 0.25),
      shininess: 40,
    });
    spire.model.material = spireMat;
    church.addChild(spire);

    // Cross on top
    const crossV = new pc.Entity("CrossVertical");
    crossV.addComponent("model", { type: "box" });
    crossV.setLocalScale(0.15, 1.2, 0.15);
    crossV.setLocalPosition(0, 14.6, -3.5);

    const crossMat = new pc.StandardMaterial();
    crossMat.diffuse = new pc.Color(0.8, 0.7, 0.3); // Gold
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

    // Main entrance (large arched door)
    const entrance = new pc.Entity("Entrance");
    entrance.addComponent("model", { type: "box" });
    entrance.setLocalScale(2.5, 3.5, 0.2);
    entrance.setLocalPosition(0, 1.75, 5.1);

    const doorMat = new pc.StandardMaterial();
    doorMat.diffuse = new pc.Color(0.15, 0.1, 0.05); // Dark wood
    doorMat.specular = new pc.Color(0.1, 0.08, 0.05);
    doorMat.update();
    entrance.model.material = doorMat;
    church.addChild(entrance);

    // Door arch
    const arch = new pc.Entity("DoorArch");
    arch.addComponent("model", { type: "torus" });
    arch.setLocalScale(1.3, 1.3, 0.2);
    arch.setLocalPosition(0, 3.4, 5.15);
    arch.setLocalEulerAngles(90, 0, 0);
    arch.model.material = stoneMat;
    church.addChild(arch);

    // Rose window above entrance
    const roseWindow = new pc.Entity("RoseWindow");
    roseWindow.addComponent("model", { type: "torus" });
    roseWindow.setLocalScale(1, 1, 0.1);
    roseWindow.setLocalPosition(0, 5, 5.1);
    roseWindow.setLocalEulerAngles(90, 0, 0);

    const roseWindowMat = new pc.StandardMaterial();
    roseWindowMat.diffuse = new pc.Color(0.7, 0.3, 0.3); // Stained glass red
    roseWindowMat.emissive = new pc.Color(0.8, 0.4, 0.2);
    roseWindowMat.opacity = 0.7;
    roseWindowMat.blendType = pc.BLEND_NORMAL;
    roseWindowMat.update();
    roseWindow.model.material = roseWindowMat;
    church.addChild(roseWindow);

    // Side windows (stained glass)
    for (let i = 0; i < 3; i++) {
      const sideWindow = new pc.Entity(`SideWindow-${i}`);
      sideWindow.addComponent("model", { type: "box" });
      sideWindow.setLocalScale(0.8, 2, 0.1);
      sideWindow.setLocalPosition(-4.05, 3 + i * 0.2, -3 + i * 3);

      const stainedMat = new pc.StandardMaterial();
      const colors = [
        new pc.Color(0.3, 0.3, 0.8), // Blue
        new pc.Color(0.8, 0.3, 0.3), // Red
        new pc.Color(0.3, 0.8, 0.3), // Green
      ];
      stainedMat.diffuse = colors[i];
      stainedMat.emissive = colors[i];
      stainedMat.opacity = 0.7;
      stainedMat.blendType = pc.BLEND_NORMAL;
      stainedMat.update();
      sideWindow.model.material = stainedMat;
      church.addChild(sideWindow);

      // Same on other side
      const sideWindow2 = sideWindow.clone();
      sideWindow2.setLocalPosition(4.05, 3 + i * 0.2, -3 + i * 3);
      church.addChild(sideWindow2);
    }

    church.setPosition(x, 0, z);
    this.app.root.addChild(church);
    this.buildings.push(church);
  }

  createWell(x, z) {
    const well = new pc.Entity("Well");

    // Base
    const base = new pc.Entity("Base");
    base.addComponent("model", { type: "cylinder" });
    base.setLocalScale(1.5, 1, 1.5);
    base.setLocalPosition(0, 0.5, 0);

    const baseMat = new pc.StandardMaterial();
    baseMat.diffuse = new pc.Color(0.4, 0.4, 0.45); // Stone
    baseMat.update();
    base.model.material = baseMat;
    well.addChild(base);

    // Roof support posts
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
    this.buildings.push(well);
  }

  createCampfire() {
    // Fire Light
    this.fireLight = new pc.Entity("FireLight");
    this.fireLight.addComponent("light", {
      type: "point",
      color: new pc.Color(1, 0.5, 0.1),
      intensity: 3,
      range: 20,
      castShadows: true,
    });
    this.fireLight.setPosition(0, 1, 0);
    this.app.root.addChild(this.fireLight);

    // Stone ring around fire
    for (let i = 0; i < 8; i++) {
      const angle = (i / 8) * Math.PI * 2;
      const stone = new pc.Entity("Stone");
      stone.addComponent("model", { type: "box" });
      stone.setLocalScale(
        0.4 + Math.random() * 0.2,
        0.3,
        0.4 + Math.random() * 0.2,
      );
      stone.setLocalPosition(
        Math.cos(angle) * 1.5,
        0.15,
        Math.sin(angle) * 1.5,
      );
      stone.setLocalEulerAngles(
        Math.random() * 10 - 5,
        Math.random() * 360,
        Math.random() * 10 - 5,
      );

      const stoneMat = this.getMaterial({
        name: "CampfireStone",
        diffuse: new pc.Color(0.3, 0.3, 0.35),
      });
      stone.model.material = stoneMat;

      this.app.root.addChild(stone);
    }

    // Logs
    const logMat = this.getMaterial({
      name: "CampfireLog",
      diffuse: new pc.Color(0.25, 0.15, 0.08),
    });

    for (let i = 0; i < 5; i++) {
      const log = new pc.Entity("Log");
      log.addComponent("model", { type: "cylinder" });
      log.setLocalScale(0.2, 1.2, 0.2);
      log.setLocalPosition(
        Math.sin(i * 1.25) * 0.5,
        0.2,
        Math.cos(i * 1.25) * 0.5,
      );
      log.setLocalEulerAngles(
        90 + Math.random() * 10,
        i * 72,
        Math.random() * 20,
      );
      log.model.material = logMat;

      this.app.root.addChild(log);
    }

    // Enhanced Particle System for Fire
    this.fireParticles = [];
    for (let i = 0; i < 20; i++) {
      const p = new pc.Entity("FireParticle");
      p.addComponent("model", { type: "plane" });
      p.setLocalScale(0.4, 0.4, 0.4);

      const fireParticleMat = this.getMaterial({
        name: `FireParticle-${i % 5}`, // Use 5 variants
        emissive: new pc.Color(1, 0.6 - (i % 5) * 0.1, 0.1),
        opacity: 0.9,
        blendType: pc.BLEND_ADDITIVE,
      });
      p.model.material = fireParticleMat;

      this.app.root.addChild(p);
      this.fireParticles.push({
        entity: p,
        speed: 0.4 + Math.random() * 0.6,
        offset: Math.random() * Math.PI * 2,
        life: Math.random(),
      });
    }
  }

  /**
   * ============================================================
   * FULLSCREEN UI OVERLAY SYSTEM
   * Renders all game UI elements as overlays within the 3D scene
   * ============================================================
   */

  /**
   * Initialize fullscreen UI overlay system
   */
  initFullscreenUI() {
    // Create container for UI overlays
    this.uiOverlayContainer = document.createElement('div');
    this.uiOverlayContainer.id = 'village3d-ui-overlay';
    this.uiOverlayContainer.style.cssText = `
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      pointer-events: none;
      z-index: 100;
      font-family: inherit;
    `;
    this.container.appendChild(this.uiOverlayContainer);

    // Create top bar for phase info and role
    this.createTopBar();

    // Create bottom action panel
    this.createActionPanel();

    // Create left sidebar for player info/effects
    this.createLeftSidebar();

    // Create right sidebar for chat/log (collapsed by default in fullscreen)
    this.createRightSidebar();

    // Create player selection overlay
    this.createPlayerSelectionOverlay();

    console.log('[Village3D] Fullscreen UI overlay system initialized');
  }

  /**
   * Create top information bar
   */
  createTopBar() {
    const topBar = document.createElement('div');
    topBar.id = 'village3d-top-bar';
    topBar.style.cssText = `
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      background: linear-gradient(180deg, rgba(0, 0, 0, 0.8) 0%, rgba(0, 0, 0, 0) 100%);
      padding: 1.5rem;
      color: white;
      z-index: 101;
      pointer-events: none;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 1rem;
    `;

    topBar.innerHTML = `
      <div style="flex: 1;">
        <div id="village3d-phase-name" style="font-size: 1.8rem; font-weight: bold; color: #d4a574; margin-bottom: 0.25rem;">
          Loading...
        </div>
        <div id="village3d-round-info" style="font-size: 0.9rem; color: rgba(255,255,255,0.7);">
          Runde 1
        </div>
      </div>
      <div style="text-align: right;">
        <div id="village3d-role-badge" style="display: inline-block; background: rgba(100,100,100,0.8); padding: 0.5rem 1rem; border-radius: 20px; font-weight: 600; pointer-events: auto;">
          Loading...
        </div>
      </div>
    `;

    this.uiOverlayContainer.appendChild(topBar);
    this.topBar = topBar;
  }

  /**
   * Create bottom action panel for role actions
   */
  createActionPanel() {
    const actionPanel = document.createElement('div');
    actionPanel.id = 'village3d-action-panel';
    actionPanel.style.cssText = `
      position: absolute;
      bottom: 0;
      left: 0;
      right: 0;
      background: linear-gradient(180deg, rgba(0, 0, 0, 0) 0%, rgba(0, 0, 0, 0.9) 100%);
      padding: 2rem 1.5rem 1.5rem;
      z-index: 101;
      pointer-events: none;
      max-height: 30vh;
      overflow-y: auto;
    `;

    actionPanel.innerHTML = `
      <div style="display: flex; gap: 0.75rem; flex-wrap: wrap; justify-content: center;">
        <div id="village3d-action-buttons" style="display: flex; gap: 0.5rem; flex-wrap: wrap; justify-content: center; width: 100%; pointer-events: auto;">
          <!-- Actions will be injected here -->
        </div>
      </div>
    `;

    this.uiOverlayContainer.appendChild(actionPanel);
    this.actionPanel = actionPanel;
  }

  /**
   * Create left sidebar for player status info
   */
  createLeftSidebar() {
    const leftSidebar = document.createElement('div');
    leftSidebar.id = 'village3d-left-sidebar';
    leftSidebar.style.cssText = `
      position: absolute;
      top: 2rem;
      left: 1rem;
      width: 280px;
      max-height: 70vh;
      background: rgba(0, 0, 0, 0.85);
      border: 1px solid rgba(212, 165, 116, 0.3);
      border-radius: 12px;
      padding: 1.5rem;
      color: white;
      z-index: 102;
      pointer-events: auto;
      overflow-y: auto;
      display: none;
      font-size: 0.9rem;
    `;

    leftSidebar.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
        <h4 style="margin: 0; color: #d4a574; font-size: 1rem;">
          <i class="fa-solid fa-user"></i> Dein Status
        </h4>
        <button onclick="window.toggleLeftSidebar?.()" style="background: none; border: none; color: white; cursor: pointer; font-size: 1.2rem; pointer-events: auto; padding: 0;">×</button>
      </div>
      <div id="village3d-player-status" style="padding: 1rem 0; border-bottom: 1px solid rgba(255,255,255,0.1); margin-bottom: 1rem;">
        <!-- Player status will be injected here -->
      </div>
      <div id="village3d-role-effects" style="font-size: 0.85rem;">
        <!-- Role-specific effects will be injected here -->
      </div>
    `;

    this.uiOverlayContainer.appendChild(leftSidebar);
    this.leftSidebar = leftSidebar;
  }

  /**
   * Create right sidebar for chat and log
   */
  createRightSidebar() {
    const rightSidebar = document.createElement('div');
    rightSidebar.id = 'village3d-right-sidebar';
    rightSidebar.style.cssText = `
      position: absolute;
      top: 2rem;
      right: 1rem;
      width: 300px;
      max-height: 70vh;
      background: rgba(0, 0, 0, 0.85);
      border: 1px solid rgba(212, 165, 116, 0.3);
      border-radius: 12px;
      padding: 1.5rem;
      color: white;
      z-index: 102;
      pointer-events: auto;
      overflow: hidden;
      display: none;
      font-size: 0.9rem;
      flex-direction: column;
    `;

    rightSidebar.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
        <h4 style="margin: 0; color: #d4a574; font-size: 1rem;">
          <i class="fa-solid fa-comments"></i> Chat
        </h4>
        <button onclick="window.toggleRightSidebar?.()" style="background: none; border: none; color: white; cursor: pointer; font-size: 1.2rem; pointer-events: auto; padding: 0;">×</button>
      </div>
      <div id="village3d-chat-messages" style="flex: 1; overflow-y: auto; margin-bottom: 1rem; max-height: 40vh; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 1rem;">
        <!-- Chat messages will be injected here -->
      </div>
      <div style="display: flex; gap: 0.5rem; pointer-events: auto;">
        <input type="text" id="village3d-chat-input" placeholder="Nachricht..." style="flex: 1; padding: 0.5rem; border-radius: 6px; border: none; background: rgba(255,255,255,0.1); color: white; font-size: 0.9rem;" />
        <button onclick="window.sendChatMessage?.()" style="padding: 0.5rem 1rem; background: #d4a574; border: none; border-radius: 6px; color: #000; cursor: pointer; font-weight: 600;">Send</button>
      </div>
    `;

    this.uiOverlayContainer.appendChild(rightSidebar);
    this.rightSidebar = rightSidebar;
  }

  /**
   * Create player selection overlay showing all players for selection
   */
  createPlayerSelectionOverlay() {
    const overlay = document.createElement('div');
    overlay.id = 'village3d-player-selection';
    overlay.style.cssText = `
      position: absolute;
      bottom: 0;
      left: 50%;
      transform: translateX(-50%);
      background: rgba(0, 0, 0, 0.95);
      border: 2px solid #d4a574;
      border-bottom: none;
      border-radius: 12px 12px 0 0;
      padding: 1.5rem;
      color: white;
      z-index: 103;
      pointer-events: auto;
      max-width: 90vw;
      max-height: 35vh;
      display: none;
    `;

    overlay.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
        <h3 style="margin: 0; color: #d4a574;">Spieler auswählen</h3>
        <button onclick="window.closePlayerSelection?.()" style="background: none; border: none; color: white; cursor: pointer; font-size: 1.5rem; padding: 0;">×</button>
      </div>
      <div id="village3d-player-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); gap: 1rem; max-height: 25vh; overflow-y: auto;">
        <!-- Players will be injected here -->
      </div>
    `;

    this.uiOverlayContainer.appendChild(overlay);
    this.playerSelectionOverlay = overlay;
  }

  /**
   * Update top bar with phase and round information
   */
  updateTopBar(phase, round) {
    const phaseEl = this.topBar?.querySelector('#village3d-phase-name');
    const roundEl = this.topBar?.querySelector('#village3d-round-info');

    if (phaseEl) {
      phaseEl.textContent = phase.replace(/_/g, ' ').toUpperCase();
    }
    if (roundEl) {
      roundEl.textContent = `Runde ${round}`;
    }
  }

  /**
   * Update role badge in top bar
   */
  updateRoleBadge(role, color) {
    const badge = this.topBar?.querySelector('#village3d-role-badge');
    if (badge) {
      badge.textContent = role || 'Warte...';
      if (color) {
        badge.style.background = `linear-gradient(135deg, ${color}80 0%, ${color}40 100%)`;
      }
    }
  }

  /**
   * Update action buttons in the action panel
   */
  updateActionButtons(buttons) {
    const container = this.actionPanel?.querySelector('#village3d-action-buttons');
    if (!container) return;

    container.innerHTML = '';

    if (!buttons || buttons.length === 0) {
      container.innerHTML = '<p style="color: #999; pointer-events: auto;">Warte auf deine Aktion...</p>';
      return;
    }

    buttons.forEach((btn) => {
      const button = document.createElement('button');
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
      button.onmouseover = () => {
        button.style.transform = 'translateY(-2px)';
        button.style.boxShadow = '0 4px 12px rgba(212,165,116,0.4)';
      };
      button.onmouseout = () => {
        button.style.transform = '';
        button.style.boxShadow = '';
      };
      button.onclick = () => {
        if (btn.onclick) {
          btn.onclick();
        }
      };
      container.appendChild(button);
    });
  }

  /**
   * Show player selection overlay
   */
  showPlayerSelection(onSelect, allowMultiple = false) {
    if (!this.playerSelectionOverlay) return;

    this.playerSelectionOverlay.style.display = 'block';
    const grid = this.playerSelectionOverlay.querySelector('#village3d-player-grid');
    grid.innerHTML = '';

    this.players.forEach((player) => {
      if (!player.ist_am_leben && !allowMultiple) return;

      const card = document.createElement('div');
      card.style.cssText = `
        padding: 1rem;
        background: rgba(100, 100, 100, 0.5);
        border: 2px solid rgba(212, 165, 116, 0.3);
        border-radius: 8px;
        text-align: center;
        cursor: pointer;
        transition: all 0.3s ease;
        pointer-events: auto;
      `;
      card.innerHTML = `
        <div style="font-size: 2rem; margin-bottom: 0.5rem;">👤</div>
        <div style="font-weight: 600; font-size: 0.9rem;">${player.name}</div>
        ${!player.ist_am_leben ? '<div style="font-size: 0.75rem; color: #ff6b6b;">💀 Tot</div>' : ''}
      `;

      card.onmouseover = () => {
        card.style.borderColor = '#d4a574';
        card.style.background = 'rgba(212, 165, 116, 0.2)';
      };
      card.onmouseout = () => {
        card.style.borderColor = 'rgba(212, 165, 116, 0.3)';
        card.style.background = 'rgba(100, 100, 100, 0.5)';
      };
      card.onclick = () => {
        onSelect(player.id);
        this.closePlayerSelection();
      };

      grid.appendChild(card);
    });

    window.closePlayerSelection = () => {
      this.playerSelectionOverlay.style.display = 'none';
    };
  }

  /**
   * Close player selection overlay
   */
  closePlayerSelection() {
    if (this.playerSelectionOverlay) {
      this.playerSelectionOverlay.style.display = 'none';
    }
  }

  /**
   * Toggle left sidebar visibility
   */
  toggleLeftSidebar() {
    if (this.leftSidebar) {
      const isVisible = this.leftSidebar.style.display !== 'none';
      this.leftSidebar.style.display = isVisible ? 'none' : 'block';
    }
  }

  /**
   * Toggle right sidebar visibility
   */
  toggleRightSidebar() {
    if (this.rightSidebar) {
      const isVisible = this.rightSidebar.style.display !== 'none';
      this.rightSidebar.style.display = isVisible ? 'none' : 'block';
    }
  }

  /**
   * Add message to chat overlay
   */
  addChatMessage(name, message, isDead = false) {
    const container = this.rightSidebar?.querySelector('#village3d-chat-messages');
    if (!container) return;

    const msg = document.createElement('div');
    msg.style.cssText = `
      padding: 0.5rem;
      margin-bottom: 0.5rem;
      background: rgba(255, 255, 255, 0.05);
      border-radius: 6px;
      ${isDead ? 'opacity: 0.6; font-style: italic;' : ''}
    `;
    msg.innerHTML = `<strong style="color: #d4a574;">${name}:</strong> ${message}`;
    container.appendChild(msg);
    container.scrollTop = container.scrollHeight;
  }

  /**
   * Update player status in left sidebar
   */
  updatePlayerStatus(playerName, role, isAlive, effects = []) {
    const statusDiv = this.leftSidebar?.querySelector('#village3d-player-status');
    if (!statusDiv) return;

    let html = `
      <div style="font-weight: 600; margin-bottom: 0.5rem;">${playerName}</div>
      <div style="color: ${isAlive ? '#2d8659' : '#ff6b6b'}; margin-bottom: 0.5rem;">
        ${isAlive ? '✓ Lebendig' : '✗ Tot'}
      </div>
      <div style="color: #d4a574; font-size: 0.95rem; margin-bottom: 0.5rem;">${role}</div>
    `;

    if (effects.length > 0) {
      html += '<div style="border-top: 1px solid rgba(255,255,255,0.1); padding-top: 0.5rem;">';
      effects.forEach((effect) => {
        html += `<div style="margin-bottom: 0.25rem;">🔧 ${effect}</div>`;
      });
      html += '</div>';
    }

    statusDiv.innerHTML = html;
  }

  /**
   * Show/hide fullscreen UI overlays
   */
  showFullscreenUI(show = true) {
    if (this.uiOverlayContainer) {
      this.uiOverlayContainer.style.display = show ? 'block' : 'none';
    }
  }

  /**
   * Reset the camera to default values
   */
  resetCamera() {
    this.targetCameraAngle = this.defaultCameraAngle;
    this.targetCameraHeight = this.defaultCameraHeight;
    this.targetCameraRadius = this.defaultCameraRadius;
  }

  setupInput() {
    // Mouse/Touch input for camera and picking
    let mouseButtonDown = false;
    let isDragging = false;
    let isClick = false;
    let lastMouseX = 0;
    let lastMouseY = 0;
    let mouseDownX = 0;
    let mouseDownY = 0;
    const CLICK_THRESHOLD = 5; // Pixels - if mouse moves less than this, it's a click

    this.app.mouse.on(pc.EVENT_MOUSEDOWN, (event) => {
      if (event.button === pc.MOUSEBUTTON_LEFT) {
        mouseButtonDown = true;
        isDragging = false;
        isClick = true;
        lastMouseX = event.x;
        lastMouseY = event.y;
        mouseDownX = event.x;
        mouseDownY = event.y;
      }
    });

    this.app.mouse.on(pc.EVENT_MOUSEUP, (event) => {
      if (event.button === pc.MOUSEBUTTON_LEFT) {
        // Only pick if it was a click, not a drag
        if (isClick) {
          this.pick(event.x, event.y);
        }
        mouseButtonDown = false;
        isDragging = false;
        isClick = false;
      }
    });

    this.app.mouse.on(pc.EVENT_MOUSEMOVE, (event) => {
      // Only process movement when mouse button is pressed
      if (!mouseButtonDown) return;

      const dx = event.x - mouseDownX;
      const dy = event.y - mouseDownY;

      // Check if we've moved enough to be considered a drag
      if (Math.abs(dx) > CLICK_THRESHOLD || Math.abs(dy) > CLICK_THRESHOLD) {
        isClick = false;
        isDragging = true;
      }

      if (isDragging) {
        const moveDx = event.x - lastMouseX;
        const moveDy = event.y - lastMouseY;

        this.targetCameraAngle -= moveDx * 0.01;
        this.targetCameraHeight += moveDy * 0.05;
        this.targetCameraHeight = pc.math.clamp(this.targetCameraHeight, 5, 35);

        lastMouseX = event.x;
        lastMouseY = event.y;
      }
    });

    // Mouse wheel for zoom
    this.app.mouse.on(pc.EVENT_MOUSEWHEEL, (event) => {
      // Prevent page scrolling
      event.event.preventDefault();
      this.targetCameraRadius += event.wheel * 0.5;
      this.targetCameraRadius = pc.math.clamp(this.targetCameraRadius, 10, 50);
    });

    // Touch support
    if (this.app.touch) {
      let touchStartX = 0;
      let touchStartY = 0;
      let isTouchClick = false;
      let lastPinchDistance = 0;

      this.app.touch.on(pc.EVENT_TOUCHSTART, (event) => {
        if (event.touches.length === 1) {
          const touch = event.touches[0];
          isDragging = false;
          isTouchClick = true;
          lastMouseX = touch.x;
          lastMouseY = touch.y;
          touchStartX = touch.x;
          touchStartY = touch.y;
        } else if (event.touches.length === 2) {
          // Start pinch zoom
          isTouchClick = false;
          const dx = event.touches[0].x - event.touches[1].x;
          const dy = event.touches[0].y - event.touches[1].y;
          lastPinchDistance = Math.sqrt(dx * dx + dy * dy);
        }
      });

      this.app.touch.on(pc.EVENT_TOUCHEND, (event) => {
        if (isTouchClick && event.touches.length === 0) {
          this.pick(touchStartX, touchStartY);
        }
        isDragging = false;
        isTouchClick = false;
        lastPinchDistance = 0;
      });

      this.app.touch.on(pc.EVENT_TOUCHMOVE, (event) => {
        if (event.touches.length === 1) {
          const touch = event.touches[0];
          const dx = touch.x - touchStartX;
          const dy = touch.y - touchStartY;

          // Check if it's a drag
          if (
            Math.abs(dx) > CLICK_THRESHOLD ||
            Math.abs(dy) > CLICK_THRESHOLD
          ) {
            isTouchClick = false;
            isDragging = true;
          }

          if (isDragging) {
            const moveDx = touch.x - lastMouseX;
            const moveDy = touch.y - lastMouseY;

            this.targetCameraAngle -= moveDx * 0.01;
            this.targetCameraHeight += moveDy * 0.05;
            this.targetCameraHeight = pc.math.clamp(
              this.targetCameraHeight,
              5,
              35,
            );

            lastMouseX = touch.x;
            lastMouseY = touch.y;
          }
        } else if (event.touches.length === 2) {
          // Pinch zoom
          isTouchClick = false;
          const dx = event.touches[0].x - event.touches[1].x;
          const dy = event.touches[0].y - event.touches[1].y;
          const pinchDistance = Math.sqrt(dx * dx + dy * dy);

          if (lastPinchDistance > 0) {
            const pinchDelta = lastPinchDistance - pinchDistance;
            this.targetCameraRadius += pinchDelta * 0.05;
            this.targetCameraRadius = pc.math.clamp(
              this.targetCameraRadius,
              10,
              50,
            );
          }
          lastPinchDistance = pinchDistance;
        }
      });
    }

    this.app.keyboard.on(pc.EVENT_KEYDOWN, (event) => {
      if (event.key === pc.KEY_R) {
        const activeElement = document.activeElement;
        if (
          activeElement &&
          (activeElement.tagName === "INPUT" ||
            activeElement.tagName === "TEXTAREA" ||
            activeElement.isContentEditable)
        ) {
          return;
        }
        this.resetCamera();
      }
    });
  }

  /**
   * Update animated features (call from main update loop).
   */
  updateAnimatedFeatures(dt) {
    if (!this.animatedFeatures) return;

    const time = Date.now() / 1000;

    this.animatedFeatures.forEach((anim) => {
      if (!anim.entity || !anim.entity.parent) return;

      const t = time * anim.speed + anim.phase;
      const amp = anim.amplitude;

      switch (anim.type) {
        case "rotate":
          anim.entity.setLocalEulerAngles(
            anim.originalRot.x,
            anim.originalRot.y + t * 60,
            anim.originalRot.z
          );
          break;
        case "pulse":
          const pulseScale = 1 + Math.sin(t * 2) * 0.1 * amp;
          anim.entity.setLocalScale(
            anim.originalScale.x * pulseScale,
            anim.originalScale.y * pulseScale,
            anim.originalScale.z * pulseScale
          );
          break;
        case "float":
          anim.entity.setLocalPosition(
            anim.originalPos.x,
            anim.originalPos.y + Math.sin(t) * 0.1 * amp,
            anim.originalPos.z
          );
          break;
        case "sway":
          anim.entity.setLocalEulerAngles(
            anim.originalRot.x,
            anim.originalRot.y,
            anim.originalRot.z + Math.sin(t) * 10 * amp
          );
          break;
        case "flutter":
          const flutterAngle = Math.sin(t * 4) * 15 * amp;
          anim.entity.setLocalEulerAngles(
            anim.originalRot.x,
            anim.originalRot.y + flutterAngle,
            anim.originalRot.z
          );
          break;
        case "flicker":
          // Random intensity flicker for fire/lights
          if (anim.entity.light) {
            anim.entity.light.intensity = 0.8 + Math.random() * 0.4;
          }
          break;
      }
    });
  }

  // Keyboard Controls
  // Only move if we are not in an input field
  const activeElement = document.activeElement;
  if (
    activeElement &&
    (activeElement.tagName === "INPUT" ||
      activeElement.tagName === "TEXTAREA" ||
      (activeElement.isContentEditable && activeElement.tagName !== "CANVAS"))
  ) {
    return;
  }

  if (
    this.app.keyboard.isPressed(pc.KEY_LEFT) ||
    this.app.keyboard.isPressed(pc.KEY_A)
  ) {
    this.targetCameraAngle += 2 * dt;
  }
  if (
    this.app.keyboard.isPressed(pc.KEY_RIGHT) ||
    this.app.keyboard.isPressed(pc.KEY_D)
  ) {
    this.targetCameraAngle -= 2 * dt;
  }
  if (
    this.app.keyboard.isPressed(pc.KEY_UP) ||
    this.app.keyboard.isPressed(pc.KEY_W)
  ) {
    this.targetCameraRadius -= 10 * dt;
  }
  if (
    this.app.keyboard.isPressed(pc.KEY_DOWN) ||
    this.app.keyboard.isPressed(pc.KEY_S)
  ) {
    this.targetCameraRadius += 10 * dt;
  }

  this.targetCameraRadius = pc.math.clamp(this.targetCameraRadius, 5, 50);

  // Smooth camera rotation and zoom
  this.cameraAngle = pc.math.lerp(
    this.cameraAngle,
    this.targetCameraAngle,
    dt * 8,
  );
  this.cameraHeight = pc.math.lerp(
    this.cameraHeight,
    this.targetCameraHeight,
    dt * 8,
  );
  this.cameraRadius = pc.math.lerp(
    this.cameraRadius,
    this.targetCameraRadius,
    dt * 8,
  );

  // Update Camera Position
  const x = Math.sin(this.cameraAngle) * this.cameraRadius;
  const z = Math.cos(this.cameraAngle) * this.cameraRadius;

  // Smooth camera movement (positional lerp)
  const currentPos = this.camera.getPosition();
  const targetPos = new pc.Vec3(x, this.cameraHeight, z);
  const newPos = new pc.Vec3().lerp(currentPos, targetPos, dt * 10);

  this.camera.setPosition(newPos);
  this.camera.lookAt(0, 2, 0);

  // Animate Enhanced Fire and Particles
  if (this.fireLight && this.fireLight.enabled) {
    // Flicker main light
    this.fireLight.light.intensity = 3.5 + Math.random() * 1.5;

    // Spawn new particles
    if (this.particleSpawner) {
      this.particleSpawner.spawn(dt);
    }
  }

  // Update all active particles (Fire, Smoke, Embers)
  if (this.particles) {
    for (let i = this.particles.length - 1; i >= 0; i--) {
      const p = this.particles[i];
      p.life += dt;

      if (p.life >= p.maxLife) {
        p.entity.destroy();
        this.particles.splice(i, 1);
        continue;
      }

      // Move
      const pos = p.entity.getPosition();
      pos.add(p.velocity.clone().scale(dt));
      p.entity.setPosition(pos);

      // Scale
      const t = p.life / p.maxLife; // 0 to 1
      const currentScale = pc.math.lerp(p.startScale, p.endScale, t);
      p.entity.setLocalScale(currentScale, currentScale, currentScale);

      // Rotate
      p.entity.rotateLocal(100 * dt, 50 * dt, 0);

      // Fade / Color
      if (p.type === "smoke") {
        p.entity.model.material.opacity = 0.3 * (1 - t);
        p.entity.model.material.update();
      } else if (p.type === "flame") {
        p.entity.model.material.opacity = 0.8 * (1 - t);
        p.entity.model.material.update();
      }
    }
  }

  // Update Stars Twinkle
  if (this.stars && this.isNight) {
    this.stars.forEach(star => {
      star.twinklePhase += dt * star.twinkleSpeed;
      const brightness = star.baseBrightness + Math.sin(star.twinklePhase) * 0.3;
      const c = star.material.emissive;
      // mod brightness without changing color hue too much
      star.material.emissive = new pc.Color(
        c.r * (1 + Math.sin(star.twinklePhase) * 0.1),
        c.g * (1 + Math.sin(star.twinklePhase) * 0.1),
        c.b * (1 + Math.sin(star.twinklePhase) * 0.1)
      );
      star.material.update();
    });
  }

  // Update Ground Fog Drift
  if (this.fogPlanes) {
    this.fogPlanes.forEach(fp => {
      fp.entity.rotateLocal(0, fp.rotSpeed * dt, 0);
      const pos = fp.entity.getPosition();
      // Gentle drift
      pos.x += fp.driftSpeed.x * dt;
      pos.z += fp.driftSpeed.y * dt;

      // Loop around if too far
      if (Math.abs(pos.x) > 60) pos.x *= -0.9;
      if (Math.abs(pos.z) > 60) pos.z *= -0.9;

      fp.entity.setPosition(pos);
    });
  }

  // Update animated features from role definitions
  this.updateAnimatedFeatures(dt);

  // Animate fireflies (enhanced)
  if (this.isNight && this.fireflies && this.fireflies.length > 0) {
    this.fireflies.forEach((f) => {
      if (!f.entity) return;
      f.phase += dt * f.speed;

      // Complex flight path
      const newAngle = f.angle + Math.sin(f.phase) * 0.5;
      const newRadius = f.radius + Math.cos(f.phase * 0.7) * 2;
      const newHeight = f.height + Math.sin(f.phase * 1.3) * 1.5;

      f.entity.setPosition(
        Math.cos(newAngle) * newRadius,
        Math.max(0.5, newHeight), // Don't go below ground
        Math.sin(newAngle) * newRadius,
      );

      // Pulse intensity
      if (f.entity.light) {
        f.entity.light.intensity = 0.8 + Math.sin(f.phase * 5) * 0.4;
      }
    });
  }

  // Make name labels always face camera (billboard effect)
  this.playerLabels.forEach((label) => {
    if (!label || !label.parent) return;

    // Get world position of label
    const labelPos = label.getPosition();
    const cameraPos = this.camera.getPosition();

    // Calculate world angle from label to camera
    const dx = cameraPos.x - labelPos.x;
    const dz = cameraPos.z - labelPos.z;
    const worldAngle = Math.atan2(dx, dz) * (180 / Math.PI);

    // Get parent's world rotation Y component
    const parentRotation = label.parent.getEulerAngles();
    const parentYRotation = parentRotation.y;

    // Calculate local Y rotation needed (world angle minus parent's world Y rotation)
    // Add 180 to flip the plane so the texture shows correctly (not mirrored)
    const localYAngle = worldAngle - parentYRotation + 180;

    // Set rotation: 90 on X to make plane vertical (facing forward), then local Y rotation to face camera
    label.setLocalEulerAngles(90, localYAngle, 0);
  });

  // Animate Players
  this.playerEntities.forEach((entity) => {
    if (!entity.animState) return;

    const anim = entity.animState;
    anim.time += dt * anim.idleSpeed;

    const isAlive = entity.playerData ? entity.playerData.ist_am_leben : true;

    if (isAlive && entity.parts) {
      // 1. Breathing (subtle scaling of torso)
      if (entity.parts.torso) {
        const breathing = Math.sin(anim.time * 2) * 0.03 + 1;
        entity.parts.torso.setLocalScale(
          0.6 * breathing,
          0.8,
          0.35 * breathing,
        );
      }

      // 2. Head Movement (idle looking around) - more noticeable
      if (entity.parts.head) {
        const headYaw = Math.sin(anim.time * 0.5) * 25; // Increased from 15
        const headPitch = Math.cos(anim.time * 0.8) * 8; // Increased from 5
        entity.parts.head.setLocalEulerAngles(headPitch, headYaw, 0);
      }

      // 3. Arm Swaying - more noticeable
      if (entity.parts.arms && entity.parts.arms.length > 0) {
        entity.parts.arms.forEach((armPivot, i) => {
          const side = i === 0 ? 1 : -1;
          const sway = Math.sin(anim.time * 1.5 + i * Math.PI) * 12; // Increased from 5
          armPivot.setLocalEulerAngles(sway, 0, side * 8);
        });
      }

      // 4. Subtle body swaying - more noticeable
      const bodyLean = Math.cos(anim.time * 0.4) * 2; // Increased from 1
      const currentY = entity.getLocalEulerAngles().y;
      entity.setLocalEulerAngles(0, currentY, bodyLean);

      // 5. Special Accessory Animations
      if (entity.parts.wings) {
        entity.parts.wings.forEach((wing, i) => {
          const side = i === 0 ? 1 : -1;
          const flap = Math.sin(anim.time * 3) * 10;
          wing.setLocalEulerAngles(0, side * (35 + flap), side * -25);
        });
      }
    } else if (!isAlive && entity.parts) {
      // Dead players have subtle "ghostly" floating if alive is false
      const float = Math.sin(anim.time * 0.5) * 0.1;
      entity.setLocalPosition(
        entity.getLocalPosition().x,
        float,
        entity.getLocalPosition().z,
      );
    }
  });
  }

  pick(x, y) {
    const from = this.camera.camera.screenToWorld(
      x,
      y,
      this.camera.camera.nearClip,
    );
    const to = this.camera.camera.screenToWorld(
      x,
      y,
      this.camera.camera.farClip,
    );

    let closestDist = Infinity;
    let closestPlayerId = null;

    // Use a slightly more accurate picking with ray-box or ray-cylinder if possible
    // For now, let's improve the manual check to use a bounding box approach
    this.playerEntities.forEach((entity, id) => {
      const pos = entity.getPosition();
      const dir = new pc.Vec3().sub2(to, from).normalize();

      // Simple ray-cylinder approximation (since players are standing)
      // Project ray onto XZ plane
      const rayStart2D = new pc.Vec2(from.x, from.z);
      const rayDir2D = new pc.Vec2(dir.x, dir.z);
      const dir2DLength = rayDir2D.length();

      if (dir2DLength < 0.001) return; // Vertical ray, handled by direct distance if needed

      rayDir2D.normalize();
      const circleCenter2D = new pc.Vec2(pos.x, pos.z);
      const radius = 1.5; // Increased radius for easier clicking

      const v = new pc.Vec2().sub2(circleCenter2D, rayStart2D);
      const t = v.dot(rayDir2D);

      if (t > 0) {
        const p = new pc.Vec2().copy(rayDir2D).scale(t).add(rayStart2D);
        const distSq = new pc.Vec2().sub2(p, circleCenter2D).lengthSq();

        if (distSq < radius * radius) {
          // Now check Y height
          const hitY = from.y + dir.y * (t / dir2DLength);
          if (hitY >= pos.y && hitY <= pos.y + 3.0) {
            const dist = t;
            if (dist < closestDist) {
              closestDist = dist;
              closestPlayerId = id;
            }
          }
        }
      }
    });

    if (closestPlayerId !== null && this.onPlayerClick) {
      console.log(`[Village3D] Picked player: ${closestPlayerId}`);
      this.onPlayerClick(closestPlayerId);
      this.zoomToPlayer(closestPlayerId);
    }
  }

  zoomToPlayer(playerId) {
    const entity = this.playerEntities.get(playerId);
    if (!entity) return;

    const pos = entity.getPosition();
    const angle = Math.atan2(pos.x, pos.z);

    // Rotate camera to face the player but zoom OUT for better overview
    this.targetCameraAngle = angle;
    this.targetCameraRadius = 20; // Zoom out for better view
    this.targetCameraHeight = 12; // Higher vantage point
  }

  // Public method for external calls (e.g., from updateActionButtons)
  focusOnPlayer(playerId) {
    this.zoomToPlayer(playerId);
  }

  highlightPlayer(playerId, color) {
    const entity = this.playerEntities.get(playerId);
    if (!entity) return;

    // Add/update highlight effect
    let highlight = entity.findByName("Highlight");
    if (!highlight) {
      highlight = new pc.Entity("Highlight");
      highlight.addComponent("model", { type: "cylinder" });
      highlight.setLocalScale(1.2, 0.1, 1.2);
      highlight.setLocalPosition(0, 0.05, 0);
      entity.addChild(highlight);
    }

    const mat = new pc.StandardMaterial();
    mat.emissive =
      color === "red" ? new pc.Color(1, 0, 0) : new pc.Color(0, 1, 0);
    mat.opacity = 0.6;
    mat.blendType = pc.BLEND_ADDITIVE;
    mat.update();
    highlight.model.material = mat;

    // Remove after a delay
    setTimeout(() => {
      if (highlight) highlight.destroy();
    }, 2000);
  }

  /**
   * Highlight a player as the werewolf victim (for Hexe phase)
   * Shows a red pulsing effect around the player
   */
  highlightVictim(playerId) {
    // Clear any existing highlight first
    this.clearVictimHighlight();

    const entity = this.playerEntities.get(playerId);
    if (!entity) {
      console.warn('[Village3D] Cannot highlight victim, player not found:', playerId);
      return;
    }

    console.log('[Village3D] Highlighting victim:', playerId);

    // Create a pulsing red glow effect
    const victimMarker = new pc.Entity('VictimMarker');

    // Create a glowing ring around the player
    const ring = new pc.Entity('VictimRing');
    ring.addComponent('model', { type: 'cylinder' });
    ring.setLocalScale(1.5, 0.05, 1.5);
    ring.setLocalPosition(0, 0.1, 0);

    const ringMat = new pc.StandardMaterial();
    ringMat.diffuse = new pc.Color(1.0, 0.1, 0.1);
    ringMat.emissive = new pc.Color(1.0, 0.0, 0.0);
    ringMat.emissiveIntensity = 2.0;
    ringMat.opacity = 0.7;
    ringMat.blendType = pc.BLEND_NORMAL;
    ringMat.update();
    ring.model.material = ringMat;
    victimMarker.addChild(ring);

    // Add a red light
    const victimLight = new pc.Entity('VictimLight');
    victimLight.addComponent('light', {
      type: 'point',
      color: new pc.Color(1.0, 0.0, 0.0),
      intensity: 1.5,
      range: 3,
      castShadows: false,
    });
    victimLight.setLocalPosition(0, 2, 0);
    victimMarker.addChild(victimLight);

    // Add skull icon above head
    const skullMarker = new pc.Entity('SkullMarker');
    skullMarker.addComponent('model', { type: 'sphere' });
    skullMarker.setLocalScale(0.4, 0.4, 0.4);
    skullMarker.setLocalPosition(0, 3.2, 0);

    const skullMat = new pc.StandardMaterial();
    skullMat.diffuse = new pc.Color(0.8, 0.0, 0.0);
    skullMat.emissive = new pc.Color(1.0, 0.0, 0.0);
    skullMat.emissiveIntensity = 1.5;
    skullMat.update();
    skullMarker.model.material = skullMat;
    victimMarker.addChild(skullMarker);

    entity.addChild(victimMarker);

    // Store reference for cleanup
    this.currentVictimMarker = victimMarker;
    this.currentVictimPlayerId = playerId;

    // Animate the ring pulsing
    this.victimAnimStartTime = Date.now();
  }

  /**
   * Clear the werewolf victim highlight
   */
  clearVictimHighlight() {
    if (this.currentVictimMarker) {
      console.log('[Village3D] Clearing victim highlight');
      this.currentVictimMarker.destroy();
      this.currentVictimMarker = null;
      this.currentVictimPlayerId = null;
    }
  }
}

