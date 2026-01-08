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
  }

  createScene() {
    // Camera
    this.camera = new pc.Entity("Camera");
    this.camera.addComponent("camera", {
      clearColor: new pc.Color(0.01, 0.01, 0.02),
      farClip: 200,
      fov: 45,
    });

    // Add Fog for better atmosphere
    // In newer PlayCanvas versions, fog is set via rendering settings
    try {
      // Try the newer API first (PlayCanvas 1.60+)
      if (this.app.scene.rendering) {
        this.app.scene.rendering.fog = pc.FOG_EXP2;
        this.app.scene.rendering.fogColor = new pc.Color(0.01, 0.01, 0.02);
        this.app.scene.rendering.fogDensity = 0.01;
      } else if (this.app.scene.settings) {
        // Alternative settings path
        this.app.scene.settings.render.fog = pc.FOG_EXP2;
        this.app.scene.settings.render.fogColor = new pc.Color(
          0.01,
          0.01,
          0.02,
        );
        this.app.scene.settings.render.fogDensity = 0.01;
      }
    } catch (e) {
      // Fog is not essential, just log quietly
      console.debug("Fog not available:", e.message);
    }

    // Set Ambient Light
    try {
      if (this.app.scene.rendering) {
        this.app.scene.rendering.ambientLight = new pc.Color(0.15, 0.15, 0.2);
      } else {
        this.app.scene.ambientLight = new pc.Color(0.15, 0.15, 0.2);
      }
    } catch (e) {
      console.debug("Could not set ambientLight:", e.message);
    }

    this.camera.setPosition(
      0,
      this.defaultCameraHeight,
      this.defaultCameraRadius,
    );
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

    // Directional Light (Moon/Sun)
    this.light = new pc.Entity("DirectionalLight");
    this.light.addComponent("light", {
      type: "directional",
      color: new pc.Color(0.7, 0.8, 1.0),
      intensity: 1.0,
      castShadows: true,
      shadowBias: 0.2,
      normalOffsetBias: 0.05,
      shadowDistance: 80,
    });
    this.light.setLocalEulerAngles(45, 30, 0);
    this.app.root.addChild(this.light);

    // Additional fill light for better player visibility
    this.fillLight = new pc.Entity("FillLight");
    this.fillLight.addComponent("light", {
      type: "directional",
      color: new pc.Color(0.3, 0.3, 0.4),
      intensity: 0.3,
      castShadows: false,
    });
    this.fillLight.setLocalEulerAngles(-30, 180, 0);
    this.app.root.addChild(this.fillLight);

    // Ground
    this.createDetailedGround();

    // Create full medieval village (in both lobby and game)
    // Village Buildings - show in both modes for a complete scene
    this.createVillageBuildings();

    // Campfire (center)
    if (this.isLobbyMode) {
      this.createSimpleCampfire();
    } else {
      this.createCampfire();
    }

    // Environment (Trees, Stones, Fence)
    this.createEnvironment();

    // Atmospheric effects
    this.createAtmosphericEffects();
  }

  createDetailedGround() {
    // Main ground - varied grass terrain
    const ground = new pc.Entity("Ground");
    ground.addComponent("model", {
      type: "plane",
    });

    // Smaller ground in lobby mode
    const groundSize = this.isLobbyMode ? 40 : 80;
    ground.setLocalScale(groundSize, 1, groundSize);

    const material = new pc.StandardMaterial();
    material.diffuse = new pc.Color(0.15, 0.22, 0.12); // Richer, more natural grass
    material.specular = new pc.Color(0.01, 0.01, 0.01);
    material.shininess = 3;
    material.update();

    ground.model.material = material;
    this.app.root.addChild(ground);

    // Create dirt paths/roads for village authenticity
    if (!this.isLobbyMode) {
      this.createVillagePaths();
    }

    // Center village square (cobblestone)
    const centerSquare = new pc.Entity("CenterSquare");
    centerSquare.addComponent("model", {
      type: "cylinder",
    });
    const squareSize = this.isLobbyMode ? 10 : 14;
    centerSquare.setLocalScale(squareSize, 0.05, squareSize);
    centerSquare.setPosition(0, 0.02, 0); // Offset to avoid Z-fighting

    const squareMat = this.getMaterial({
      name: "VillageSquare",
      diffuse: new pc.Color(0.35, 0.32, 0.28), // Cobblestone/stone color
      specular: new pc.Color(0.05, 0.05, 0.05),
      shininess: 8,
    });
    centerSquare.model.material = squareMat;

    this.app.root.addChild(centerSquare);

    // Add some decorative stones around the square
    if (!this.isLobbyMode) {
      this.createSquareDecorations();
    }
  }

  /**
   * Create dirt paths connecting the village
   */
  createVillagePaths() {
    // Main cross paths through center
    const pathPositions = [
      { x: 0, z: 0, scaleX: 1.5, scaleZ: 35, rotation: 0 }, // North-South path
      { x: 0, z: 0, scaleX: 35, scaleZ: 1.5, rotation: 0 }, // East-West path
      { x: -15, z: -12, scaleX: 12, scaleZ: 1.2, rotation: 25 }, // Path to houses
      { x: 15, z: 10, scaleX: 10, scaleZ: 1.2, rotation: -35 }, // Path to houses
      { x: -8, z: 15, scaleX: 8, scaleZ: 1.2, rotation: 15 }, // Path to houses
      { x: 12, z: -10, scaleX: 9, scaleZ: 1.2, rotation: -20 }, // Path to church
    ];

    pathPositions.forEach((pos, idx) => {
      const path = new pc.Entity(`Path-${idx}`);
      path.addComponent("model", { type: "box" });
      path.setLocalScale(pos.scaleX, 0.02, pos.scaleZ);
      path.setPosition(pos.x, 0.01, pos.z);
      path.setEulerAngles(0, pos.rotation, 0);

      const pathMat = this.getMaterial({
        name: `DirtPath-${idx % 3}`, // Use 3 variants
        diffuse: new pc.Color(
          0.28 + (idx % 3) * 0.02,
          0.22 + (idx % 3) * 0.02,
          0.16,
        ),
        specular: new pc.Color(0.01, 0.01, 0.01),
        shininess: 1,
      });
      path.model.material = pathMat;

      this.app.root.addChild(path);
    });
  }

  /**
   * Create decorative elements around the village square
   */
  createSquareDecorations() {
    // Market stalls/benches around the square
    const stallPositions = [
      { x: -8, z: 0, rotation: 90 },
      { x: 8, z: 0, rotation: -90 },
      { x: 0, z: -8, rotation: 0 },
      { x: 0, z: 8, rotation: 180 },
    ];

    stallPositions.forEach((pos, idx) => {
      // Simple bench/stall
      const stall = new pc.Entity(`Bench-${idx}`);
      stall.addComponent("model", { type: "box" });
      stall.setLocalScale(2, 0.4, 0.6);
      stall.setPosition(pos.x, 0.2, pos.z);
      stall.setEulerAngles(0, pos.rotation, 0);

      const stallMat = this.getMaterial({
        name: "Bench",
        diffuse: new pc.Color(0.3, 0.2, 0.1), // Wood
        shininess: 10,
      });
      stall.model.material = stallMat;

      this.app.root.addChild(stall);
    });

    // Add some barrels/crates near the square
    const cratePositions = [
      { x: -9, z: -2 },
      { x: 9, z: 2 },
      { x: 2, z: 9 },
      { x: -2, z: -9 },
    ];

    cratePositions.forEach((pos, idx) => {
      const crate = new pc.Entity(`Crate-${idx}`);
      crate.addComponent("model", { type: "box" });
      const size = 0.5 + Math.random() * 0.3;
      crate.setLocalScale(size, size, size);
      crate.setPosition(pos.x, size / 2, pos.z);
      crate.setEulerAngles(
        Math.random() * 10 - 5,
        Math.random() * 360,
        Math.random() * 10 - 5,
      );

      const crateMat = this.getMaterial({
        name: `Crate-${idx % 2}`,
        diffuse: new pc.Color(0.35, 0.25, 0.15),
        shininess: 5,
      });
      crate.model.material = crateMat;

      this.app.root.addChild(crate);
    });
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

  createSimpleCampfire() {
    // Simple center marker for lobby - just a small fire light
    this.fireLight = new pc.Entity("FireLight");
    this.fireLight.addComponent("light", {
      type: "point",
      color: new pc.Color(1, 0.6, 0.2),
      intensity: 1.5,
      range: 12,
      castShadows: false,
    });
    this.fireLight.setPosition(0, 1, 0);
    this.app.root.addChild(this.fireLight);

    // Small center marker sphere
    const marker = new pc.Entity("CenterMarker");
    marker.addComponent("model", { type: "sphere" });
    marker.setLocalScale(0.5, 0.5, 0.5);
    marker.setPosition(0, 0.5, 0);

    const mat = new pc.StandardMaterial();
    mat.emissive = new pc.Color(1, 0.6, 0.2);
    mat.opacity = 0.8;
    mat.blendType = pc.BLEND_ADDITIVE;
    mat.update();
    marker.model.material = mat;

    this.app.root.addChild(marker);
  }

  createEnvironment() {
    // Trees with more variety
    const treeCount = this.isLobbyMode ? 40 : 30;
    for (let i = 0; i < treeCount; i++) {
      const angle = (i / treeCount) * Math.PI * 2 + (Math.random() - 0.5);
      const radius = this.isLobbyMode
        ? 15 + Math.random() * 5
        : 25 + Math.random() * 10;
      const x = Math.cos(angle) * radius;
      const z = Math.sin(angle) * radius;

      const treeHeight = 3 + Math.random() * 2;
      this.createTree(x, z, treeHeight);
    }

    // Bushes
    const bushCount = this.isLobbyMode ? 20 : 15;
    for (let i = 0; i < bushCount; i++) {
      const angle = Math.random() * Math.PI * 2;
      const radius = this.isLobbyMode
        ? 12 + Math.random() * 6
        : 18 + Math.random() * 8;
      const x = Math.cos(angle) * radius;
      const z = Math.sin(angle) * radius;

      this.createBush(x, z);
    }

    // Rocks/Stones scattered around
    const rockCount = this.isLobbyMode ? 25 : 20;
    for (let i = 0; i < rockCount; i++) {
      const angle = Math.random() * Math.PI * 2;
      const radius = this.isLobbyMode
        ? 8 + Math.random() * 15
        : 10 + Math.random() * 25;
      const x = Math.cos(angle) * radius;
      const z = Math.sin(angle) * radius;

      this.createRock(x, z);
    }
  }

  createTree(x, z, height) {
    const tree = new pc.Entity("Tree");

    // Trunk
    const trunk = new pc.Entity("Trunk");
    trunk.addComponent("model", { type: "cylinder" });
    trunk.setLocalScale(0.4, height, 0.4);
    trunk.setLocalPosition(0, height / 2, 0);

    const trunkMat = this.getMaterial({
      name: "TrunkMaterial",
      diffuse: new pc.Color(0.2, 0.15, 0.1),
    });
    trunk.model.material = trunkMat;
    tree.addChild(trunk);

    // Leaves (multiple layers)
    const leavesMat = this.getMaterial({
      name: "LeavesMaterial",
      diffuse: new pc.Color(0.08, 0.2, 0.08),
    });

    for (let i = 0; i < 3; i++) {
      const leaves = new pc.Entity(`Leaves-${i}`);
      leaves.addComponent("model", { type: "cone" });
      const scale = 3 - i * 0.5;
      leaves.setLocalScale(scale, height * 0.8, scale);
      leaves.setLocalPosition(0, height + i * 0.8, 0);
      leaves.model.material = leavesMat;
      tree.addChild(leaves);
    }

    tree.setPosition(x, 0, z);
    tree.setEulerAngles(0, Math.random() * 360, 0);
    this.app.root.addChild(tree);
  }

  createBush(x, z) {
    const bush = new pc.Entity("Bush");
    bush.addComponent("model", { type: "sphere" });
    const scale = 0.8 + Math.random() * 0.6;
    bush.setLocalScale(scale, scale * 0.7, scale);
    bush.setPosition(x, scale * 0.35, z);

    const bushMat = this.getMaterial({
      name: "BushMaterial",
      diffuse: new pc.Color(0.08, 0.2, 0.08),
    });
    bush.model.material = bushMat;

    this.app.root.addChild(bush);
  }

  createRock(x, z) {
    const rock = new pc.Entity("Rock");
    rock.addComponent("model", { type: "box" });
    const scale = 0.3 + Math.random() * 0.5;
    rock.setLocalScale(scale, scale * 0.6, scale * 1.2);
    rock.setPosition(x, scale * 0.3, z);
    rock.setEulerAngles(
      Math.random() * 20 - 10,
      Math.random() * 360,
      Math.random() * 20 - 10,
    );

    const rockMat = this.getMaterial({
      name: "RockMaterial",
      diffuse: new pc.Color(0.35, 0.35, 0.4),
      shininess: 5,
    });
    rock.model.material = rockMat;

    this.app.root.addChild(rock);
  }

  createAtmosphericEffects() {
    // Fireflies for night atmosphere
    this.fireflies = [];
    for (let i = 0; i < 15; i++) {
      const firefly = new pc.Entity("Firefly");
      firefly.addComponent("light", {
        type: "point",
        color: new pc.Color(0.8, 1.0, 0.6),
        intensity: 0.5,
        range: 3,
        castShadows: false,
      });

      const angle = Math.random() * Math.PI * 2;
      const radius = 10 + Math.random() * 15;
      firefly.setPosition(
        Math.cos(angle) * radius,
        1 + Math.random() * 3,
        Math.sin(angle) * radius,
      );

      this.app.root.addChild(firefly);
      this.fireflies.push({
        entity: firefly,
        angle: angle,
        radius: radius,
        height: 1 + Math.random() * 3,
        speed: 0.3 + Math.random() * 0.5,
        phase: Math.random() * Math.PI * 2,
      });
    }
  }

  setPlayers(players) {
    if (!players) return;
    this.players = players;
    console.log(
      "[Village3D] setPlayers called with",
      players.length,
      "players",
    );

    const count = players.length;

    // Adaptive layout based on player count
    if (count <= 12) {
      this.layoutMode = "circle";
    } else if (count <= 30) {
      this.layoutMode = "double_circle";
    } else if (count <= 60) {
      this.layoutMode = "clusters";
    } else {
      this.layoutMode = "grid";
    }

    console.log(
      `[Village3D] Using ${this.layoutMode} layout for ${count} players`,
    );

    const currentIds = new Set(players.map((p) => p.id));

    // Remove players that are no longer in the list
    this.playerEntities.forEach((entity, id) => {
      if (!currentIds.has(id)) {
        entity.destroy();
        this.playerEntities.delete(id);
        const label = this.playerLabels.get(id);
        if (label) {
          label.destroy();
          this.playerLabels.delete(id);
        }
      }
    });

    players.forEach((player, index) => {
      const position = this.getPlayerPosition(index, count);
      const x = position.x;
      const z = position.z;

      let entity = this.playerEntities.get(player.id);
      if (entity) {
        // Update existing entity position
        entity.setPosition(x, 0, z);
        entity.lookAt(0, 0, 0);
        entity.playerData = player;

        // Update status if needed
        this.updatePlayerStatus(player.id, player.ist_am_leben);
      } else {
        // Create new
        console.log(
          `[Village3D] Creating player ${player.name} at position (${x.toFixed(2)}, 0, ${z.toFixed(2)})`,
        );
        const angle = Math.atan2(x, z);
        entity = this.createDetailedPlayer(player, x, z, angle);
        this.app.root.addChild(entity);
        this.playerEntities.set(player.id, entity);
      }
    });

    console.log(
      "[Village3D] All players processed. Total:",
      this.playerEntities.size,
    );
  }

  /**
   * Calculate player position based on layout mode
   * @param {number} index - Player index
   * @param {number} total - Total number of players
   * @returns {{x: number, z: number}} Position coordinates
   */
  getPlayerPosition(index, total) {
    switch (this.layoutMode) {
      case "circle":
        return this.getCirclePosition(index, total, 8);

      case "double_circle":
        // Split into two concentric circles
        const innerCount = Math.ceil(total / 2);
        if (index < innerCount) {
          return this.getCirclePosition(index, innerCount, 6);
        } else {
          return this.getCirclePosition(
            index - innerCount,
            total - innerCount,
            11,
          );
        }

      case "clusters":
        // Arrange in clusters of ~10 players
        const clusterSize = 10;
        const clusterIndex = Math.floor(index / clusterSize);
        const posInCluster = index % clusterSize;
        const totalClusters = Math.ceil(total / clusterSize);

        // Position clusters in a circle
        const clusterAngle = (clusterIndex / totalClusters) * Math.PI * 2;
        const clusterRadius = 12;
        const clusterCenterX = Math.cos(clusterAngle) * clusterRadius;
        const clusterCenterZ = Math.sin(clusterAngle) * clusterRadius;

        // Position within cluster (small circle)
        const inClusterAngle = (posInCluster / clusterSize) * Math.PI * 2;
        const inClusterRadius = 3;

        return {
          x: clusterCenterX + Math.cos(inClusterAngle) * inClusterRadius,
          z: clusterCenterZ + Math.sin(inClusterAngle) * inClusterRadius,
        };

      case "grid":
        // Arrange in a grid pattern
        const cols = Math.ceil(Math.sqrt(total * 1.5)); // Wider than tall
        const row = Math.floor(index / cols);
        const col = index % cols;

        const spacing = 2.5;
        const gridWidth = (cols - 1) * spacing;
        const gridHeight = (Math.ceil(total / cols) - 1) * spacing;

        return {
          x: col * spacing - gridWidth / 2,
          z: row * spacing - gridHeight / 2,
        };

      default:
        return this.getCirclePosition(index, total, 8);
    }
  }

  /**
   * Get position on a circle
   * @param {number} index
   * @param {number} total
   * @param {number} radius
   * @returns {{x: number, z: number}}
   */
  getCirclePosition(index, total, radius) {
    const angle = (index / total) * Math.PI * 2;
    return {
      x: Math.cos(angle) * radius,
      z: Math.sin(angle) * radius,
    };
  }

  createDetailedPlayer(player, x, z, angle) {
    try {
      const entity = new pc.Entity(`Player-${player.id}`);
      console.log(`[Village3D] Created entity for player ${player.name}`);

      // Get role color - in lobby mode use a visible color scheme
      let roleColor;
      if (this.isLobbyMode || !player.rolle) {
        // Lobby mode: use blue for all players so they're visible
        roleColor = new pc.Color(0.3, 0.5, 0.8);
      } else {
        roleColor = this.roleColors[player.rolle] || this.roleColors["default"];
      }
      console.log(
        `[Village3D] Role color for ${player.name} (${player.rolle}):`,
        roleColor,
      );

      // Create role-specific appearance
      this.addRoleSpecificAppearance(entity, player, roleColor);
      console.log(`[Village3D] Added appearance for ${player.name}`);

      // Name Label (3D text using plane with canvas texture)
      const nameLabel = this.createNameLabel(player.name, player.ist_am_leben);
      nameLabel.setLocalPosition(0, 2.8, 0);
      // Billboard orientation will be set in update() - no initial rotation needed
      entity.addChild(nameLabel);
      this.playerLabels.set(player.id, nameLabel);

      // Add collision for picking
      entity.addComponent("collision", {
        type: "box",
        halfExtents: new pc.Vec3(0.4, 1.2, 0.3),
      });

      entity.setPosition(x, 0, z);
      entity.lookAt(0, 0, 0);

      // Store data
      entity.playerData = player;

      console.log(
        `[Village3D] Player ${player.name} fully configured at (${x.toFixed(2)}, 0, ${z.toFixed(2)})`,
      );
      return entity;
    } catch (e) {
      console.error("[Village3D] Error creating player:", player.name, e);
      throw e;
    }
  }

  addRoleSpecificAppearance(entity, player, roleColor) {
    // Early exit if entity or player is missing
    if (!entity || !player) return;

    const rolle = player.rolle;
    const isAlive = player.ist_am_leben;

    // Animation state
    entity.animState = {
      time: Math.random() * 10,
      idleSpeed: 0.5 + Math.random() * 0.5,
      breathingPhase: Math.random() * Math.PI * 2,
      headTurnPhase: Math.random() * Math.PI * 2,
      isMoving: false,
    };

    entity.parts = {};

    try {
      console.log(
        `[Village3D] addRoleSpecificAppearance for ${player.name}, rolle=${rolle}, alive=${isAlive}`,
      );

      // Skin tone for living players
      const skinColor = isAlive
        ? new pc.Color(0.87, 0.72, 0.58)
        : new pc.Color(0.35, 0.35, 0.35);
      const skinMat = new pc.StandardMaterial();
      skinMat.diffuse = skinColor;
      skinMat.specular = new pc.Color(0.15, 0.12, 0.1);
      skinMat.shininess = 25;
      if (!isAlive) {
        skinMat.opacity = 0.5;
        skinMat.blendType = pc.BLEND_NORMAL;
      }
      skinMat.update();

      // === TORSO (main body) ===
      const torso = new pc.Entity("Torso");
      torso.addComponent("model", { type: "box" });
      torso.setLocalPosition(0, 1.0, 0);
      torso.setLocalScale(0.6, 0.8, 0.35);

      const torsoMat = new pc.StandardMaterial();
      if (isAlive) {
        torsoMat.diffuse = roleColor;
        torsoMat.specular = new pc.Color(0.15, 0.15, 0.15);
        torsoMat.shininess = 15;
      } else {
        torsoMat.diffuse = new pc.Color(0.25, 0.25, 0.25);
        torsoMat.opacity = 0.5;
        torsoMat.blendType = pc.BLEND_NORMAL;
      }
      torsoMat.update();
      torso.model.material = torsoMat;
      entity.addChild(torso);
      entity.parts.torso = torso;
      console.log("[Village3D] Torso created");

      // === LEGS ===
      entity.parts.legs = [];
      for (let i = 0; i < 2; i++) {
        const leg = new pc.Entity(`Leg-${i}`);
        leg.addComponent("model", { type: "box" });
        leg.setLocalPosition(i === 0 ? -0.15 : 0.15, 0.3, 0);
        leg.setLocalScale(0.2, 0.6, 0.25);

        const legMat = new pc.StandardMaterial();
        if (isAlive) {
          legMat.diffuse = roleColor;
          legMat.specular = new pc.Color(0.15, 0.15, 0.15);
          legMat.shininess = 15;
        } else {
          legMat.diffuse = new pc.Color(0.25, 0.25, 0.25);
          legMat.opacity = 0.5;
          legMat.blendType = pc.BLEND_NORMAL;
        }
        legMat.update();
        leg.model.material = legMat;
        entity.addChild(leg);
        entity.parts.legs.push(leg);
      }
      console.log("[Village3D] Legs created");

      // === ARMS ===
      entity.parts.arms = [];
      for (let i = 0; i < 2; i++) {
        const armPivot = new pc.Entity(`ArmPivot-${i}`);
        armPivot.setLocalPosition(i === 0 ? -0.3 : 0.3, 1.3, 0);
        entity.addChild(armPivot);
        entity.parts.arms.push(armPivot);

        const arm = new pc.Entity(`Arm-${i}`);
        arm.addComponent("model", { type: "box" });
        arm.setLocalPosition(i === 0 ? -0.1 : 0.1, -0.25, 0);
        arm.setLocalScale(0.15, 0.55, 0.2);
        arm.setLocalEulerAngles(0, 0, i === 0 ? 8 : -8);

        const armMat = new pc.StandardMaterial();
        armMat.diffuse = skinColor;
        armMat.specular = new pc.Color(0.15, 0.12, 0.1);
        armMat.shininess = 25;
        if (!isAlive) {
          armMat.opacity = 0.5;
          armMat.blendType = pc.BLEND_NORMAL;
        }
        armMat.update();
        arm.model.material = armMat;
        armPivot.addChild(arm);

        // Hands
        const hand = new pc.Entity(`Hand-${i}`);
        hand.addComponent("model", { type: "sphere" });
        hand.setLocalPosition(0, -0.3, 0);
        hand.setLocalScale(0.12, 0.12, 0.1);

        const handMat = new pc.StandardMaterial();
        handMat.diffuse = skinColor;
        handMat.specular = new pc.Color(0.15, 0.12, 0.1);
        handMat.shininess = 25;
        if (!isAlive) {
          handMat.opacity = 0.5;
          handMat.blendType = pc.BLEND_NORMAL;
        }
        handMat.update();
        hand.model.material = handMat;
        arm.addChild(hand);
      }
      console.log("[Village3D] Arms created");

      // === NECK ===
      const neck = new pc.Entity("Neck");
      neck.addComponent("model", { type: "cylinder" });
      neck.setLocalPosition(0, 1.5, 0);
      neck.setLocalScale(0.15, 0.12, 0.15);

      const neckMat = new pc.StandardMaterial();
      neckMat.diffuse = skinColor;
      neckMat.specular = new pc.Color(0.15, 0.12, 0.1);
      neckMat.shininess = 25;
      if (!isAlive) {
        neckMat.opacity = 0.5;
        neckMat.blendType = pc.BLEND_NORMAL;
      }
      neckMat.update();
      neck.model.material = neckMat;
      entity.addChild(neck);
      entity.parts.neck = neck;

      // === HEAD PIVOT (for animation) ===
      const headPivot = new pc.Entity("HeadPivot");
      headPivot.setLocalPosition(0, 1.85, 0);
      entity.addChild(headPivot);
      entity.parts.head = headPivot; // Store pivot for animation

      // === HEAD (slightly oval) ===
      const head = new pc.Entity("Head");
      head.addComponent("model", { type: "sphere" });
      head.setLocalPosition(0, 0, 0); // Position relative to pivot
      head.setLocalScale(0.5, 0.55, 0.45);

      const headMat = new pc.StandardMaterial();
      headMat.diffuse = skinColor;
      headMat.specular = new pc.Color(0.15, 0.12, 0.1);
      headMat.shininess = 25;
      if (!isAlive) {
        headMat.opacity = 0.5;
        headMat.blendType = pc.BLEND_NORMAL;
      }
      headMat.update();
      head.model.material = headMat;
      headPivot.addChild(head);

      // === HAIR ===
      const hair = new pc.Entity("Hair");
      hair.addComponent("model", { type: "sphere" });
      hair.setLocalPosition(0, 0.15, -0.05); // Position relative to head pivot
      hair.setLocalScale(0.52, 0.35, 0.48);

      const hairMat = new pc.StandardMaterial();
      // Random hair color based on player id hash
      const hairColors = [
        new pc.Color(0.15, 0.1, 0.05), // Dark brown
        new pc.Color(0.35, 0.2, 0.1), // Brown
        new pc.Color(0.8, 0.6, 0.3), // Blonde
        new pc.Color(0.1, 0.08, 0.05), // Black
        new pc.Color(0.5, 0.25, 0.15), // Auburn
      ];
      const playerIdStr = String(player.id);
      const hairIndex =
        Math.abs(
          playerIdStr.split("").reduce((a, c) => a + c.charCodeAt(0), 0),
        ) % hairColors.length;
      hairMat.diffuse = isAlive
        ? hairColors[hairIndex]
        : new pc.Color(0.3, 0.3, 0.3);
      hairMat.shininess = 40;
      if (!isAlive) {
        hairMat.opacity = 0.5;
        hairMat.blendType = pc.BLEND_NORMAL;
      }
      hairMat.update();
      hair.model.material = hairMat;
      headPivot.addChild(hair);

      // === FACIAL FEATURES (only for living players) ===
      if (isAlive) {
        // --- EYES with white, iris, and pupil ---
        for (let i = 0; i < 2; i++) {
          const eyeX = i === 0 ? -0.12 : 0.12;

          // Eye white (sclera)
          const eyeWhite = new pc.Entity(`EyeWhite-${i}`);
          eyeWhite.addComponent("model", { type: "sphere" });
          eyeWhite.setLocalPosition(eyeX, 0.05, 0.2);
          eyeWhite.setLocalScale(0.1, 0.08, 0.06);

          const eyeWhiteMat = new pc.StandardMaterial();
          eyeWhiteMat.diffuse = new pc.Color(0.95, 0.95, 0.95);
          eyeWhiteMat.shininess = 60;
          eyeWhiteMat.update();
          eyeWhite.model.material = eyeWhiteMat;
          head.addChild(eyeWhite);

          // Iris (colored part)
          const iris = new pc.Entity(`Iris-${i}`);
          iris.addComponent("model", { type: "sphere" });
          iris.setLocalPosition(eyeX, 0.05, 0.24);
          iris.setLocalScale(0.055, 0.055, 0.03);

          const irisMat = new pc.StandardMaterial();
          // Random eye color
          const eyeColors = [
            new pc.Color(0.25, 0.45, 0.7), // Blue
            new pc.Color(0.35, 0.55, 0.3), // Green
            new pc.Color(0.45, 0.3, 0.2), // Brown
            new pc.Color(0.3, 0.35, 0.35), // Gray
          ];
          const eyeIdStr = String(player.id);
          const eyeIndex =
            Math.abs(
              eyeIdStr.split("").reduce((a, c) => a + c.charCodeAt(0) * 2, 0),
            ) % eyeColors.length;
          irisMat.diffuse = eyeColors[eyeIndex];
          irisMat.shininess = 80;
          irisMat.update();
          iris.model.material = irisMat;
          head.addChild(iris);

          // Pupil (black center)
          const pupil = new pc.Entity(`Pupil-${i}`);
          pupil.addComponent("model", { type: "sphere" });
          pupil.setLocalPosition(eyeX, 0.05, 0.26);
          pupil.setLocalScale(0.03, 0.03, 0.02);

          const pupilMat = new pc.StandardMaterial();
          pupilMat.diffuse = new pc.Color(0.05, 0.05, 0.05);
          pupilMat.update();
          pupil.model.material = pupilMat;
          head.addChild(pupil);

          // Eye highlight/reflection
          const eyeHighlight = new pc.Entity(`EyeHighlight-${i}`);
          eyeHighlight.addComponent("model", { type: "sphere" });
          eyeHighlight.setLocalPosition(eyeX + 0.015, 0.06, 0.265);
          eyeHighlight.setLocalScale(0.012, 0.012, 0.008);

          const highlightMat = new pc.StandardMaterial();
          highlightMat.diffuse = new pc.Color(1, 1, 1);
          highlightMat.emissive = new pc.Color(0.5, 0.5, 0.5);
          highlightMat.update();
          eyeHighlight.model.material = highlightMat;
          head.addChild(eyeHighlight);
        }

        // --- EYEBROWS ---
        for (let i = 0; i < 2; i++) {
          const eyebrow = new pc.Entity(`Eyebrow-${i}`);
          eyebrow.addComponent("model", { type: "box" });
          eyebrow.setLocalPosition(i === 0 ? -0.12 : 0.12, 0.13, 0.2);
          eyebrow.setLocalScale(0.1, 0.02, 0.04);
          eyebrow.setLocalEulerAngles(0, 0, i === 0 ? 5 : -5);

          const eyebrowMat = new pc.StandardMaterial();
          eyebrowMat.diffuse = hairMat.diffuse;
          eyebrowMat.shininess = 40;
          eyebrowMat.update();
          eyebrow.model.material = eyebrowMat;
          head.addChild(eyebrow);
        }

        // --- NOSE ---
        const nose = new pc.Entity("Nose");
        nose.addComponent("model", { type: "box" });
        nose.setLocalPosition(0, -0.03, 0.23);
        nose.setLocalScale(0.05, 0.08, 0.06);
        nose.setLocalEulerAngles(15, 0, 0);

        const noseMat = new pc.StandardMaterial();
        noseMat.diffuse = skinColor;
        noseMat.specular = new pc.Color(0.15, 0.12, 0.1);
        noseMat.shininess = 25;
        noseMat.update();
        nose.model.material = noseMat;
        head.addChild(nose);

        // --- MOUTH ---
        const mouth = new pc.Entity("Mouth");
        mouth.addComponent("model", { type: "box" });
        mouth.setLocalPosition(0, -0.13, 0.2);
        mouth.setLocalScale(0.12, 0.025, 0.03);

        const mouthMat = new pc.StandardMaterial();
        mouthMat.diffuse = new pc.Color(0.65, 0.35, 0.35);
        mouthMat.shininess = 50;
        mouthMat.update();
        mouth.model.material = mouthMat;
        head.addChild(mouth);

        // --- EARS ---
        for (let i = 0; i < 2; i++) {
          const ear = new pc.Entity(`Ear-Human-${i}`);
          ear.addComponent("model", { type: "sphere" });
          ear.setLocalPosition(i === 0 ? -0.26 : 0.26, 0, 0);
          ear.setLocalScale(0.06, 0.1, 0.04);

          const earMat = new pc.StandardMaterial();
          earMat.diffuse = skinColor;
          earMat.specular = new pc.Color(0.15, 0.12, 0.1);
          earMat.shininess = 25;
          earMat.update();
          ear.model.material = earMat;
          head.addChild(ear);
        }
      } else {
        // Dead players get X eyes
        for (let i = 0; i < 2; i++) {
          const eyeX = i === 0 ? -0.12 : 0.12;

          // X mark for dead eyes
          const xLine1 = new pc.Entity(`DeadEyeX1-${i}`);
          xLine1.addComponent("model", { type: "box" });
          xLine1.setLocalPosition(eyeX, 0.05, 0.23);
          xLine1.setLocalScale(0.08, 0.015, 0.015);
          xLine1.setLocalEulerAngles(0, 0, 45);

          const deadEyeMat = new pc.StandardMaterial();
          deadEyeMat.diffuse = new pc.Color(0.1, 0.1, 0.1);
          deadEyeMat.opacity = 0.6;
          deadEyeMat.blendType = pc.BLEND_NORMAL;
          deadEyeMat.update();
          xLine1.model.material = deadEyeMat;
          head.addChild(xLine1);

          const xLine2 = new pc.Entity(`DeadEyeX2-${i}`);
          xLine2.addComponent("model", { type: "box" });
          xLine2.setLocalPosition(eyeX, 0.05, 0.23);
          xLine2.setLocalScale(0.08, 0.015, 0.015);
          xLine2.setLocalEulerAngles(0, 0, -45);
          xLine2.model.material = deadEyeMat;
          head.addChild(xLine2);
        }
      }
    } catch (e) {
      console.error("[Village3D] Error in addRoleSpecificAppearance:", e);
      throw e;
    }

    // Add role-specific accessories and features
    if (isAlive && rolle) {
      // Get model definition from API data
      const modelDef = this.roleModels[rolle];

      if (modelDef) {
        // Use the appearance features defined in the role's Python file
        const appearanceFeatures = modelDef.appearance_others_alive || [];

        if (appearanceFeatures.length > 0) {
          console.log(
            `[Village3D] Rendering ${appearanceFeatures.length} features for ${rolle} from role definition`,
          );
          this.renderAppearanceFeatures(entity, appearanceFeatures, roleColor);
        } else {
          // No features defined, try legacy method or use default
          const modelId = modelDef.modell_id;
          const featureMethodName = `add${modelId
            .split("_")
            .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
            .join("")}Features`;

          if (typeof this[featureMethodName] === "function") {
            // Call the legacy feature method
            this[featureMethodName](entity, roleColor);
          } else {
            // Fallback to default role indicator
            console.log(
              `[Village3D] No features defined for ${rolle}, using default`,
            );
            this.addDefaultRoleIndicator(entity, roleColor);
          }
        }
      } else {
        // No model definition at all - use default
        console.warn(
          `[Village3D] No model definition found for ${rolle}, using default`,
        );
        this.addDefaultRoleIndicator(entity, roleColor);
      }
    }
  }

  /**
   * Renders appearance features from role definition data.
   * This replaces the hardcoded feature methods with dynamic rendering.
   *
   * Supports all properties from the enhanced AppearanceFeature dataclass:
   * - position, scale, rotation
   * - color_source, custom_color, secondary_color, opacity
   * - emissive, emissive_intensity, metallic, roughness
   * - animation, animation_speed, animation_amplitude
   * - particle_effect, particle_color, particle_rate
   * - light_source, light_color, light_intensity, light_range
   * - mirror_x, count, count_arrangement, count_spacing
   */
  renderAppearanceFeatures(entity, features, roleColor) {
    features.forEach((feature, idx) => {
      try {
        const {
          feature_type,
          geometry,
          position = {},
          scale = {},
          rotation = {},
          mirror_x = false,
          mirror_offset = 0,
          color_source = "role",
          custom_color,
          secondary_color,
          opacity = 1.0,
          emissive = false,
          emissive_intensity = 0.5,
          metallic = false,
          roughness = 0.5,
          animation,
          animation_speed = 1.0,
          animation_amplitude = 1.0,
          particle_effect,
          particle_color,
          particle_rate = 10.0,
          light_source = false,
          light_color,
          light_intensity = 0.5,
          light_range = 2.0,
          count = 1,
          count_arrangement = "linear",
          count_spacing = 0.1,
          visible_to_self = true,
          visible_to_others = true,
          visible_when_dead = false,
        } = feature;

        // Determine the color to use
        let featureColor = roleColor.clone ? roleColor.clone() : new pc.Color(roleColor.r, roleColor.g, roleColor.b);
        if (color_source === "custom" && custom_color) {
          featureColor = this.hexToColor(custom_color);
        } else if (color_source === "skin") {
          featureColor = new pc.Color(0.87, 0.72, 0.58);
        } else if (color_source === "emissive" && custom_color) {
          featureColor = this.hexToColor(custom_color);
        }

        // Map geometry types (handle new types)
        const geometryMap = {
          'cone': 'cone',
          'box': 'box',
          'sphere': 'sphere',
          'cylinder': 'cylinder',
          'torus': 'torus',
          'capsule': 'capsule',
          'plane': 'plane',
        };
        const pcGeometry = geometryMap[geometry] || 'sphere';

        // Create instances
        const instances = this.calculateInstances(count, count_arrangement, count_spacing, position);

        instances.forEach((instancePos, i) => {
          // Create main feature
          this.createFeatureInstance(
            entity, feature_type, idx, i, pcGeometry,
            instancePos, scale, rotation,
            featureColor, opacity, emissive, emissive_intensity,
            metallic, roughness, animation, animation_speed, animation_amplitude,
            light_source, light_color, light_intensity, light_range,
            particle_effect, particle_color, particle_rate
          );

          // Create mirrored version if needed
          if (mirror_x) {
            const mirroredPos = {
              x: -(instancePos.x || 0) + mirror_offset,
              y: instancePos.y || 0,
              z: instancePos.z || 0
            };
            const mirroredRotation = {
              x: rotation.x || 0,
              y: rotation.y || 0,
              z: -(rotation.z || 0)  // Mirror Z rotation
            };
            this.createFeatureInstance(
              entity, `${feature_type}_mirror`, idx, i, pcGeometry,
              mirroredPos, scale, mirroredRotation,
              featureColor, opacity, emissive, emissive_intensity,
              metallic, roughness, animation, animation_speed, animation_amplitude,
              light_source, light_color, light_intensity, light_range,
              particle_effect, particle_color, particle_rate
            );
          }
        });
      } catch (e) {
        console.error(
          `[Village3D] Error rendering feature ${feature.feature_type}:`,
          e,
        );
      }
    });
  }

  /**
   * Create a single feature instance with all material and effect properties.
   */
  createFeatureInstance(
    parent, featureType, featureIdx, instanceIdx, geometry,
    position, scale, rotation,
    color, opacity, emissive, emissiveIntensity,
    metallic, roughness, animation, animSpeed, animAmplitude,
    lightSource, lightColor, lightIntensity, lightRange,
    particleEffect, particleColor, particleRate
  ) {
    const featureEntity = new pc.Entity(`${featureType}-${featureIdx}-${instanceIdx}`);

    // Add model component (handle special geometry types)
    if (geometry === 'torus' || geometry === 'capsule' || geometry === 'plane') {
      // Approximate with available primitives
      if (geometry === 'torus') {
        // Approximate torus with a thin cylinder ring
        featureEntity.addComponent("model", { type: "cylinder" });
      } else if (geometry === 'capsule') {
        featureEntity.addComponent("model", { type: "cylinder" });
      } else if (geometry === 'plane') {
        featureEntity.addComponent("model", { type: "box" });
      }
    } else {
      featureEntity.addComponent("model", { type: geometry });
    }

    // Apply position
    featureEntity.setLocalPosition(
      position.x || 0,
      position.y || 0,
      position.z || 0
    );

    // Apply scale
    featureEntity.setLocalScale(
      scale.x || 1,
      scale.y || 1,
      scale.z || 1
    );

    // Apply rotation
    featureEntity.setLocalEulerAngles(
      rotation.x || 0,
      rotation.y || 0,
      rotation.z || 0
    );

    // Create and apply material
    const material = new pc.StandardMaterial();
    material.diffuse = color;

    // Handle opacity
    if (opacity < 1.0) {
      material.opacity = opacity;
      material.blendType = pc.BLEND_NORMAL;
    }

    // Handle emissive
    if (emissive) {
      material.emissive = color;
      material.emissiveIntensity = emissiveIntensity;
    }

    // Handle metallic/roughness
    if (metallic) {
      material.metalness = 0.8;
      material.shininess = 80;
    }
    material.shininess = (1 - roughness) * 100;

    material.update();

    if (featureEntity.model) {
      featureEntity.model.material = material;
    }

    // Add to parent
    parent.addChild(featureEntity);

    // Add light source if specified
    if (lightSource) {
      const light = new pc.Entity(`${featureType}-light-${instanceIdx}`);
      const lColor = lightColor ? this.hexToColor(lightColor) : color;
      light.addComponent("light", {
        type: "point",
        color: lColor,
        intensity: lightIntensity,
        range: lightRange,
        castShadows: false,
      });
      light.setLocalPosition(0, 0, 0);
      featureEntity.addChild(light);
    }

    // Add animation if specified
    if (animation) {
      this.addFeatureAnimation(featureEntity, animation, animSpeed, animAmplitude);
    }

    // Add particle effect if specified
    if (particleEffect) {
      this.addParticleEffect(featureEntity, particleEffect, particleColor, particleRate);
    }

    return featureEntity;
  }

  /**
   * Calculate instance positions based on arrangement type.
   */
  calculateInstances(count, arrangement, spacing, basePosition) {
    const instances = [];
    const baseX = basePosition.x || 0;
    const baseY = basePosition.y || 0;
    const baseZ = basePosition.z || 0;

    for (let i = 0; i < count; i++) {
      let pos = { x: baseX, y: baseY, z: baseZ };

      if (count > 1) {
        switch (arrangement) {
          case "linear":
            pos.x = baseX + (i - (count - 1) / 2) * spacing;
            break;
          case "radial":
            const angle = (i / count) * Math.PI * 2;
            pos.x = baseX + Math.cos(angle) * spacing;
            pos.z = baseZ + Math.sin(angle) * spacing;
            break;
          case "random":
            pos.x = baseX + (Math.random() - 0.5) * spacing * 2;
            pos.y = baseY + (Math.random() - 0.5) * spacing;
            pos.z = baseZ + (Math.random() - 0.5) * spacing * 2;
            break;
        }
      }
      instances.push(pos);
    }
    return instances;
  }

  /**
   * Add animation to a feature entity.
   */
  addFeatureAnimation(entity, animationType, speed, amplitude) {
    // Store animation data for update loop
    if (!this.animatedFeatures) {
      this.animatedFeatures = [];
    }

    this.animatedFeatures.push({
      entity: entity,
      type: animationType,
      speed: speed,
      amplitude: amplitude,
      phase: Math.random() * Math.PI * 2,
      originalPos: entity.getLocalPosition().clone(),
      originalRot: entity.getLocalEulerAngles().clone(),
      originalScale: entity.getLocalScale().clone(),
    });
  }

  /**
   * Add particle effect to a feature entity.
   */
  addParticleEffect(entity, effectType, color, rate) {
    // Create particle system entity
    const particles = new pc.Entity(`particles-${effectType}`);

    const particleColor = color ? this.hexToColor(color) : new pc.Color(1, 1, 1);

    // Configure based on effect type
    const configs = {
      "sparks": {
        numParticles: 20,
        lifetime: 0.5,
        rate: rate,
        emitterShape: pc.EMITTERSHAPE_SPHERE,
        emitterRadius: 0.1,
        startAngle: 0,
        endAngle: 360,
        velocityX: [-0.5, 0.5],
        velocityY: [0.5, 1.5],
        velocityZ: [-0.5, 0.5],
        scaleGraph: new pc.Curve([0, 0.02, 1, 0]),
        colorGraph: new pc.CurveSet([[0, particleColor.r], [1, particleColor.r]], [[0, particleColor.g], [1, particleColor.g]], [[0, particleColor.b], [1, particleColor.b]]),
      },
      "magic": {
        numParticles: 15,
        lifetime: 1.0,
        rate: rate * 0.5,
        emitterShape: pc.EMITTERSHAPE_SPHERE,
        emitterRadius: 0.2,
        velocityY: [0.1, 0.3],
        scaleGraph: new pc.Curve([0, 0.03, 0.5, 0.05, 1, 0]),
      },
      "fire": {
        numParticles: 30,
        lifetime: 0.4,
        rate: rate * 2,
        emitterShape: pc.EMITTERSHAPE_SPHERE,
        emitterRadius: 0.05,
        velocityY: [0.5, 1.0],
        scaleGraph: new pc.Curve([0, 0.04, 0.5, 0.06, 1, 0]),
      },
      "hearts": {
        numParticles: 5,
        lifetime: 2.0,
        rate: rate * 0.3,
        velocityY: [0.1, 0.3],
        scaleGraph: new pc.Curve([0, 0.05, 0.5, 0.08, 1, 0.05]),
      },
      "smoke": {
        numParticles: 10,
        lifetime: 1.5,
        rate: rate * 0.5,
        velocityY: [0.1, 0.2],
        scaleGraph: new pc.Curve([0, 0.05, 1, 0.15]),
      },
      "shadow": {
        numParticles: 10,
        lifetime: 0.5,
        rate: rate,
        velocityY: [-0.1, 0.1],
        scaleGraph: new pc.Curve([0, 0.1, 1, 0]),
      },
    };

    // Note: Full particle system requires texture asset
    // For now, add a simple visual indicator
    const indicator = new pc.Entity("particle-indicator");
    indicator.addComponent("model", { type: "sphere" });
    indicator.setLocalScale(0.05, 0.05, 0.05);
    const mat = new pc.StandardMaterial();
    mat.diffuse = particleColor;
    mat.emissive = particleColor;
    mat.emissiveIntensity = 0.5;
    mat.opacity = 0.5;
    mat.blendType = pc.BLEND_ADDITIVE;
    mat.update();
    indicator.model.material = mat;

    entity.addChild(indicator);
  }

  /**
   * Convert hex color string to PlayCanvas Color.
   */
  hexToColor(hex) {
    if (!hex) return new pc.Color(1, 1, 1);
    const cleanHex = hex.replace("#", "");
    const r = parseInt(cleanHex.slice(0, 2), 16) / 255;
    const g = parseInt(cleanHex.slice(2, 4), 16) / 255;
    const b = parseInt(cleanHex.slice(4, 6), 16) / 255;
    return new pc.Color(r, g, b);
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

  addWerwolfFeatures(entity, roleColor) {
    // Wolf ears (pointy, on top of head)
    for (let i = 0; i < 2; i++) {
      const ear = new pc.Entity(`WolfEar-${i}`);
      ear.addComponent("model", { type: "cone" });
      ear.setLocalPosition(i === 0 ? -0.18 : 0.18, 2.25, -0.05);
      ear.setLocalScale(0.12, 0.2, 0.1);
      ear.setLocalEulerAngles(0, 0, i === 0 ? -15 : 15);

      const earMat = new pc.StandardMaterial();
      earMat.diffuse = roleColor;
      earMat.update();
      ear.model.material = earMat;
      entity.addChild(ear);
    }

    // Claws on hands
    for (let i = 0; i < 2; i++) {
      for (let c = 0; c < 3; c++) {
        const claw = new pc.Entity(`Claw-${i}-${c}`);
        claw.addComponent("model", { type: "cone" });
        const baseX = i === 0 ? -0.4 : 0.4;
        const offsetX = (c - 1) * 0.03;
        claw.setLocalPosition(baseX + offsetX, 0.52, 0.08);
        claw.setLocalScale(0.025, 0.08, 0.025);
        claw.setLocalEulerAngles(60, 0, 0);

        const clawMat = new pc.StandardMaterial();
        clawMat.diffuse = new pc.Color(0.2, 0.2, 0.2);
        clawMat.shininess = 70;
        clawMat.update();
        claw.model.material = clawMat;
        entity.addChild(claw);
      }
    }

    // Fangs
    for (let i = 0; i < 2; i++) {
      const fang = new pc.Entity(`Fang-${i}`);
      fang.addComponent("model", { type: "cone" });
      fang.setLocalPosition(i === 0 ? -0.04 : 0.04, 1.68, 0.2);
      fang.setLocalScale(0.02, 0.06, 0.02);
      fang.setLocalEulerAngles(180, 0, 0);

      const fangMat = new pc.StandardMaterial();
      fangMat.diffuse = new pc.Color(0.95, 0.95, 0.9);
      fangMat.shininess = 80;
      fangMat.update();
      fang.model.material = fangMat;
      entity.addChild(fang);
    }

    // Glowing red eyes effect
    const eyeGlow = new pc.Entity("EyeGlow");
    eyeGlow.addComponent("light", {
      type: "point",
      color: new pc.Color(1, 0.2, 0.1),
      intensity: 0.6,
      range: 1.5,
    });
    eyeGlow.setLocalPosition(0, 1.9, 0.35);
    entity.addChild(eyeGlow);
  }

  addSeherinFeatures(entity, roleColor) {
    // Crystal ball (held in hand)
    const crystal = new pc.Entity("CrystalBall");
    crystal.addComponent("model", { type: "sphere" });
    crystal.setLocalPosition(0.42, 0.7, 0.15);
    crystal.setLocalScale(0.18, 0.18, 0.18);

    const crystalMat = new pc.StandardMaterial();
    crystalMat.diffuse = new pc.Color(0.5, 0.3, 0.9);
    crystalMat.emissive = new pc.Color(0.6, 0.4, 1.0);
    crystalMat.opacity = 0.7;
    crystalMat.blendType = pc.BLEND_ADDITIVE;
    crystalMat.shininess = 100;
    crystalMat.update();
    crystal.model.material = crystalMat;
    entity.addChild(crystal);

    // Mystical aura
    const aura = new pc.Entity("Aura");
    aura.addComponent("light", {
      type: "point",
      color: new pc.Color(0.6, 0.4, 1.0),
      intensity: 0.8,
      range: 2.5,
    });
    aura.setLocalPosition(0, 1.5, 0);
    entity.addChild(aura);

    // Pointed hat (on head)
    const hat = new pc.Entity("Hat");
    hat.addComponent("model", { type: "cone" });
    hat.setLocalPosition(0, 2.35, -0.02);
    hat.setLocalScale(0.35, 0.55, 0.35);

    const hatMat = new pc.StandardMaterial();
    hatMat.diffuse = roleColor;
    hatMat.update();
    hat.model.material = hatMat;
    entity.addChild(hat);
  }

  addHexeFeatures(entity, roleColor) {
    // Witch hat (wider brim)
    const hat = new pc.Entity("WitchHat");
    hat.addComponent("model", { type: "cone" });
    hat.setLocalPosition(0, 2.5, -0.02);
    hat.setLocalScale(0.3, 0.7, 0.3);

    const hatMat = new pc.StandardMaterial();
    hatMat.diffuse = new pc.Color(0.1, 0.1, 0.1);
    hatMat.update();
    hat.model.material = hatMat;
    entity.addChild(hat);

    // Hat brim
    const brim = new pc.Entity("HatBrim");
    brim.addComponent("model", { type: "cylinder" });
    brim.setLocalPosition(0, 2.15, 0);
    brim.setLocalScale(0.55, 0.04, 0.55);
    brim.model.material = hatMat;
    entity.addChild(brim);

    // Potion bottles (on belt)
    for (let i = 0; i < 2; i++) {
      const potion = new pc.Entity(`Potion-${i}`);
      potion.addComponent("model", { type: "cylinder" });
      potion.setLocalPosition(i === 0 ? -0.35 : 0.35, 0.7, 0.2);
      potion.setLocalScale(0.06, 0.15, 0.06);

      const potionMat = new pc.StandardMaterial();
      potionMat.diffuse =
        i === 0 ? new pc.Color(0, 1, 0) : new pc.Color(0.8, 0, 0.8);
      potionMat.emissive =
        i === 0 ? new pc.Color(0, 0.5, 0) : new pc.Color(0.4, 0, 0.4);
      potionMat.opacity = 0.8;
      potionMat.blendType = pc.BLEND_ADDITIVE;
      potionMat.update();
      potion.model.material = potionMat;
      entity.addChild(potion);
    }
  }

  addJaegerFeatures(entity, roleColor) {
    // Crossbow (carried in hand)
    const crossbow = new pc.Entity("Crossbow");
    crossbow.addComponent("model", { type: "box" });
    crossbow.setLocalPosition(0.5, 0.8, 0.2);
    crossbow.setLocalScale(0.5, 0.1, 0.1);
    crossbow.setLocalEulerAngles(0, 0, -30);

    const crossbowMat = new pc.StandardMaterial();
    crossbowMat.diffuse = new pc.Color(0.3, 0.2, 0.1);
    crossbowMat.update();
    crossbow.model.material = crossbowMat;
    entity.addChild(crossbow);

    // Quiver (on back)
    const quiver = new pc.Entity("Quiver");
    quiver.addComponent("model", { type: "cylinder" });
    quiver.setLocalPosition(0.2, 1.2, -0.25);
    quiver.setLocalScale(0.12, 0.35, 0.12);
    quiver.setLocalEulerAngles(15, 0, 0);

    const quiverMat = new pc.StandardMaterial();
    quiverMat.diffuse = new pc.Color(0.4, 0.3, 0.2);
    quiverMat.update();
    quiver.model.material = quiverMat;
    entity.addChild(quiver);

    // Arrows in quiver
    for (let i = 0; i < 3; i++) {
      const arrow = new pc.Entity(`Arrow-${i}`);
      arrow.addComponent("model", { type: "cylinder" });
      arrow.setLocalPosition(0.15 + i * 0.05, 1.55, -0.25);
      arrow.setLocalScale(0.025, 0.25, 0.025);

      const arrowMat = new pc.StandardMaterial();
      arrowMat.diffuse = new pc.Color(0.6, 0.5, 0.3);
      arrowMat.update();
      arrow.model.material = arrowMat;
      entity.addChild(arrow);
    }
  }

  addAmorFeatures(entity, roleColor) {
    // Cupid wings (on back)
    entity.parts.wings = [];
    for (let i = 0; i < 2; i++) {
      const wing = new pc.Entity(`Wing-${i}`);
      wing.addComponent("model", { type: "box" });
      wing.setLocalPosition(i === 0 ? -0.35 : 0.35, 1.15, -0.25);
      wing.setLocalScale(0.5, 0.35, 0.06);
      wing.setLocalEulerAngles(0, i === 0 ? 35 : -35, i === 0 ? -25 : 25);

      const wingMat = new pc.StandardMaterial();
      wingMat.diffuse = new pc.Color(1, 0.8, 0.9);
      wingMat.opacity = 0.7;
      wingMat.blendType = pc.BLEND_NORMAL;
      wingMat.update();
      wing.model.material = wingMat;
      entity.addChild(wing);
      entity.parts.wings.push(wing);
    }

    // Bow (weapon held in hand)
    const bow = new pc.Entity("Bow");
    bow.addComponent("model", { type: "torus" });
    bow.setLocalPosition(-0.45, 0.75, 0.1);
    bow.setLocalScale(0.3, 0.3, 0.08);
    bow.setLocalEulerAngles(0, 90, 0);

    const bowMat = new pc.StandardMaterial();
    bowMat.diffuse = roleColor;
    bowMat.update();
    bow.model.material = bowMat;
    entity.addChild(bow);

    // Hearts floating around
    const heart = new pc.Entity("HeartGlow");
    heart.addComponent("light", {
      type: "point",
      color: new pc.Color(1, 0.4, 0.7),
      intensity: 0.7,
      range: 2.5,
    });
    heart.setLocalPosition(0, 2.2, 0);
    entity.addChild(heart);
  }

  addHeilerFeatures(entity, roleColor) {
    // Medical cross (on chest)
    const cross1 = new pc.Entity("Cross1");
    cross1.addComponent("model", { type: "box" });
    cross1.setLocalPosition(0, 1.05, 0.19);
    cross1.setLocalScale(0.06, 0.22, 0.03);

    const crossMat = new pc.StandardMaterial();
    crossMat.diffuse = new pc.Color(1, 1, 1);
    crossMat.emissive = new pc.Color(0.8, 0.2, 0.2);
    crossMat.update();
    cross1.model.material = crossMat;
    entity.addChild(cross1);

    const cross2 = new pc.Entity("Cross2");
    cross2.addComponent("model", { type: "box" });
    cross2.setLocalPosition(0, 1.05, 0.19);
    cross2.setLocalScale(0.18, 0.06, 0.03);
    cross2.model.material = crossMat;
    entity.addChild(cross2);

    // Healing aura
    const healingAura = new pc.Entity("HealingAura");
    healingAura.addComponent("light", {
      type: "point",
      color: new pc.Color(0.9, 0.9, 0.2),
      intensity: 0.8,
      range: 2.5,
    });
    healingAura.setLocalPosition(0, 1.2, 0);
    entity.addChild(healingAura);

    // Staff (held in hand)
    const staff = new pc.Entity("Staff");
    staff.addComponent("model", { type: "cylinder" });
    staff.setLocalPosition(-0.5, 1.0, 0.1);
    staff.setLocalScale(0.05, 1.2, 0.05);
    staff.setLocalEulerAngles(0, 0, -10);

    const staffMat = new pc.StandardMaterial();
    staffMat.diffuse = new pc.Color(0.5, 0.4, 0.2);
    staffMat.update();
    staff.model.material = staffMat;
    entity.addChild(staff);
  }

  addDefaultRoleIndicator(entity, roleColor) {
    // Default glowing sphere above head
    const indicator = new pc.Entity("RoleIndicator");
    indicator.addComponent("model", { type: "sphere" });
    indicator.setLocalPosition(0, 2.4, 0);
    indicator.setLocalScale(0.15, 0.15, 0.15);

    const indicatorMat = new pc.StandardMaterial();
    indicatorMat.emissive = roleColor;
    indicatorMat.opacity = 0.8;
    indicatorMat.blendType = pc.BLEND_ADDITIVE;
    indicatorMat.update();
    indicator.model.material = indicatorMat;
    entity.addChild(indicator);
  }

  // === DORFBEWOHNER ===
  addDorfbewohnerFeatures(entity, roleColor) {
    // Simple hat
    const hat = new pc.Entity("Hat");
    hat.addComponent("model", { type: "cone" });
    hat.setLocalPosition(0, 2.35, 0);
    hat.setLocalScale(0.3, 0.25, 0.3);
    const hatMat = new pc.StandardMaterial();
    hatMat.diffuse = roleColor;
    hatMat.update();
    hat.model.material = hatMat;
    entity.addChild(hat);
  }

  // === WERWOLF VARIANTEN ===
  addEinsamerWolfFeatures(entity, roleColor) {
    // Lone wolf ears + scars
    for (let i = 0; i < 2; i++) {
      const ear = new pc.Entity(`LoneWolfEar-${i}`);
      ear.addComponent("model", { type: "cone" });
      ear.setLocalPosition(i === 0 ? -0.18 : 0.18, 2.25, -0.05);
      ear.setLocalScale(0.14, 0.22, 0.11);
      ear.model.material = new pc.StandardMaterial();
      ear.model.material.diffuse = roleColor;
      ear.model.material.update();
      entity.addChild(ear);
    }
    // Scars on face
    const scar = new pc.Entity("Scar");
    scar.addComponent("model", { type: "box" });
    scar.setLocalPosition(0.15, 1.85, 0.2);
    scar.setLocalScale(0.08, 0.15, 0.02);
    const scarMat = new pc.StandardMaterial();
    scarMat.diffuse = new pc.Color(0.3, 0.1, 0.1);
    scarMat.update();
    scar.model.material = scarMat;
    entity.addChild(scar);
  }

  addLupinFeatures(entity, roleColor) {
    // Distinguished wolf ears + monocle glow
    for (let i = 0; i < 2; i++) {
      const ear = new pc.Entity(`LupinEar-${i}`);
      ear.addComponent("model", { type: "cone" });
      ear.setLocalPosition(i === 0 ? -0.16 : 0.16, 2.27, -0.03);
      ear.setLocalScale(0.12, 0.21, 0.1);
      ear.model.material = new pc.StandardMaterial();
      ear.model.material.diffuse = roleColor;
      ear.model.material.update();
      entity.addChild(ear);
    }
    // Monocle
    const monocle = new pc.Entity("Monocle");
    monocle.addComponent("model", { type: "torus" });
    monocle.setLocalPosition(0.12, 1.9, 0.22);
    monocle.setLocalScale(0.08, 0.08, 0.02);
    const monocMat = new pc.StandardMaterial();
    monocMat.diffuse = new pc.Color(0.8, 0.7, 0.3);
    monocMat.shininess = 80;
    monocMat.update();
    monocle.model.material = monocMat;
    entity.addChild(monocle);
  }

  addPolarwolfFeatures(entity, roleColor) {
    // Ice crystal ears + frosted aura
    for (let i = 0; i < 2; i++) {
      const ear = new pc.Entity(`PolarEar-${i}`);
      ear.addComponent("model", { type: "cone" });
      ear.setLocalPosition(i === 0 ? -0.18 : 0.18, 2.25, -0.05);
      ear.setLocalScale(0.13, 0.21, 0.1);
      ear.model.material = new pc.StandardMaterial();
      ear.model.material.diffuse = new pc.Color(0.95, 0.98, 1.0);
      ear.model.material.shininess = 90;
      ear.model.material.update();
      entity.addChild(ear);
    }
    // Ice aura
    const iceAura = new pc.Entity("IceAura");
    iceAura.addComponent("light", {
      type: "point",
      color: new pc.Color(0.7, 0.9, 1.0),
      intensity: 0.5,
      range: 2.0,
    });
    iceAura.setLocalPosition(0, 1.5, 0);
    entity.addChild(iceAura);
  }

  addTeenagerWerwolfFeatures(entity, roleColor) {
    // Smaller ears + hoodie
    for (let i = 0; i < 2; i++) {
      const ear = new pc.Entity(`TeenEar-${i}`);
      ear.addComponent("model", { type: "cone" });
      ear.setLocalPosition(i === 0 ? -0.15 : 0.15, 2.22, 0);
      ear.setLocalScale(0.1, 0.18, 0.08);
      ear.model.material = new pc.StandardMaterial();
      ear.model.material.diffuse = roleColor;
      ear.model.material.update();
      entity.addChild(ear);
    }
  }

  addUrwolfFeatures(entity, roleColor) {
    // Large ancient ears + scars
    for (let i = 0; i < 2; i++) {
      const ear = new pc.Entity(`AncientEar-${i}`);
      ear.addComponent("model", { type: "cone" });
      ear.setLocalPosition(i === 0 ? -0.2 : 0.2, 2.28, -0.06);
      ear.setLocalScale(0.15, 0.24, 0.12);
      ear.model.material = new pc.StandardMaterial();
      ear.model.material.diffuse = roleColor;
      ear.model.material.update();
      entity.addChild(ear);
    }
  }

  addWeisserWolfFeatures(entity, roleColor) {
    // Pure white ears + ethereal glow
    for (let i = 0; i < 2; i++) {
      const ear = new pc.Entity(`WhiteEar-${i}`);
      ear.addComponent("model", { type: "cone" });
      ear.setLocalPosition(i === 0 ? -0.18 : 0.18, 2.25, -0.05);
      ear.setLocalScale(0.12, 0.21, 0.1);
      ear.model.material = new pc.StandardMaterial();
      ear.model.material.diffuse = new pc.Color(1.0, 1.0, 0.98);
      ear.model.material.emissive = new pc.Color(0.3, 0.3, 0.2);
      ear.model.material.update();
      entity.addChild(ear);
    }
  }

  addWerwolfseherinFeatures(entity, roleColor) {
    // Wolf ears + crystal ball
    for (let i = 0; i < 2; i++) {
      const ear = new pc.Entity(`SeherWolfEar-${i}`);
      ear.addComponent("model", { type: "cone" });
      ear.setLocalPosition(i === 0 ? -0.18 : 0.18, 2.25, -0.05);
      ear.setLocalScale(0.12, 0.21, 0.1);
      ear.model.material = new pc.StandardMaterial();
      ear.model.material.diffuse = roleColor;
      ear.model.material.update();
      entity.addChild(ear);
    }
    // Crystal ball
    const crystal = new pc.Entity("WolfCrystal");
    crystal.addComponent("model", { type: "sphere" });
    crystal.setLocalPosition(0.4, 0.7, 0.1);
    crystal.setLocalScale(0.15, 0.15, 0.15);
    const crystalMat = new pc.StandardMaterial();
    crystalMat.diffuse = new pc.Color(0.5, 0.3, 0.9);
    crystalMat.emissive = new pc.Color(0.6, 0.4, 1.0);
    crystalMat.opacity = 0.7;
    crystalMat.blendType = pc.BLEND_ADDITIVE;
    crystalMat.update();
    crystal.model.material = crystalMat;
    entity.addChild(crystal);
  }

  addWildesKindFeatures(entity, roleColor) {
    // Wild ragged appearance - torn clothes effect
    const tear = new pc.Entity("Tear");
    tear.addComponent("model", { type: "box" });
    tear.setLocalPosition(0.25, 1.0, 0.18);
    tear.setLocalScale(0.15, 0.25, 0.02);
    const tearMat = new pc.StandardMaterial();
    tearMat.diffuse = new pc.Color(0.1, 0.1, 0.1);
    tearMat.update();
    tear.model.material = tearMat;
    entity.addChild(tear);
  }

  addWolfImSchafspelzFeatures(entity, roleColor) {
    // Sheep wool appearance on shoulders
    for (let i = 0; i < 2; i++) {
      const wool = new pc.Entity(`Wool-${i}`);
      wool.addComponent("model", { type: "sphere" });
      wool.setLocalPosition(i === 0 ? -0.4 : 0.4, 1.35, -0.1);
      wool.setLocalScale(0.25, 0.2, 0.15);
      const woolMat = new pc.StandardMaterial();
      woolMat.diffuse = new pc.Color(0.95, 0.93, 0.9);
      woolMat.shininess = 20;
      woolMat.update();
      wool.model.material = woolMat;
      entity.addChild(wool);
    }
  }

  addWolfsjungeFeatures(entity, roleColor) {
    // Young small ears
    for (let i = 0; i < 2; i++) {
      const ear = new pc.Entity(`YoungEar-${i}`);
      ear.addComponent("model", { type: "cone" });
      ear.setLocalPosition(i === 0 ? -0.15 : 0.15, 2.2, 0);
      ear.setLocalScale(0.08, 0.15, 0.07);
      ear.model.material = new pc.StandardMaterial();
      ear.model.material.diffuse = roleColor;
      ear.model.material.update();
      entity.addChild(ear);
    }
  }

  // === BÖSE ROLLEN ===
  addFlötenspielerFeatures(entity, roleColor) {
    // Flute in hand
    const flute = new pc.Entity("Flute");
    flute.addComponent("model", { type: "cylinder" });
    flute.setLocalPosition(0.35, 1.0, 0.1);
    flute.setLocalScale(0.08, 0.35, 0.08);
    flute.setLocalEulerAngles(0, 0, 45);
    const fluteMat = new pc.StandardMaterial();
    fluteMat.diffuse = new pc.Color(0.7, 0.6, 0.3);
    fluteMat.shininess = 60;
    fluteMat.update();
    flute.model.material = fluteMat;
    entity.addChild(flute);
  }

  addHexenmeisterFeatures(entity, roleColor) {
    // Dark staff + pointed hat
    const hat = new pc.Entity("HexenmeisterHat");
    hat.addComponent("model", { type: "cone" });
    hat.setLocalPosition(0, 2.35, -0.02);
    hat.setLocalScale(0.32, 0.5, 0.32);
    const hatMat = new pc.StandardMaterial();
    hatMat.diffuse = new pc.Color(0.05, 0.02, 0.08);
    hatMat.update();
    hat.model.material = hatMat;
    entity.addChild(hat);

    const staff = new pc.Entity("MasterStaff");
    staff.addComponent("model", { type: "cylinder" });
    staff.setLocalPosition(-0.45, 1.0, 0.1);
    staff.setLocalScale(0.06, 1.3, 0.06);
    const staffMat = new pc.StandardMaterial();
    staffMat.diffuse = new pc.Color(0.1, 0.05, 0.02);
    staffMat.update();
    staff.model.material = staffMat;
    entity.addChild(staff);
  }

  addVampirFeatures(entity, roleColor) {
    // Fangs + cape suggestion
    for (let i = 0; i < 2; i++) {
      const fang = new pc.Entity(`VampireFang-${i}`);
      fang.addComponent("model", { type: "cone" });
      fang.setLocalPosition(i === 0 ? -0.04 : 0.04, 1.68, 0.2);
      fang.setLocalScale(0.025, 0.08, 0.025);
      fang.setLocalEulerAngles(180, 0, 0);
      const fangMat = new pc.StandardMaterial();
      fangMat.diffuse = new pc.Color(0.95, 0.95, 0.9);
      fangMat.update();
      fang.model.material = fangMat;
      entity.addChild(fang);
    }
    // Glowing red eyes
    const eyeGlow = new pc.Entity("VampireGlow");
    eyeGlow.addComponent("light", {
      type: "point",
      color: new pc.Color(0.8, 0.1, 0.1),
      intensity: 0.5,
      range: 1.5,
    });
    eyeGlow.setLocalPosition(0, 1.9, 0.35);
    entity.addChild(eyeGlow);
  }

  addZombieFeatures(entity, roleColor) {
    // Rotting flesh effects + missing parts
    const rotMark = new pc.Entity("RotMark");
    rotMark.addComponent("model", { type: "sphere" });
    rotMark.setLocalPosition(-0.15, 1.15, 0.18);
    rotMark.setLocalScale(0.12, 0.12, 0.05);
    const rotMat = new pc.StandardMaterial();
    rotMat.diffuse = new pc.Color(0.2, 0.25, 0.15);
    rotMat.update();
    rotMark.model.material = rotMat;
    entity.addChild(rotMark);
  }

  // === DORFBEWOHNER VARIANTEN ===
  addAlterMannFeatures(entity, roleColor) {
    // Cane + old man hair
    const cane = new pc.Entity("Cane");
    cane.addComponent("model", { type: "cylinder" });
    cane.setLocalPosition(-0.4, 0.7, 0.1);
    cane.setLocalScale(0.04, 0.9, 0.04);
    const caneMat = new pc.StandardMaterial();
    caneMat.diffuse = new pc.Color(0.3, 0.2, 0.1);
    caneMat.update();
    cane.model.material = caneMat;
    entity.addChild(cane);
  }

  addDorfdeppFeatures(entity, roleColor) {
    // Silly expression marker
    const jesterHat = new pc.Entity("JesterHat");
    jesterHat.addComponent("model", { type: "cone" });
    jesterHat.setLocalPosition(0, 2.35, 0);
    jesterHat.setLocalScale(0.28, 0.3, 0.28);
    const hatMat = new pc.StandardMaterial();
    hatMat.diffuse = new pc.Color(0.7, 0.3, 0.3);
    hatMat.update();
    jesterHat.model.material = hatMat;
    entity.addChild(jesterHat);
  }

  addDreiBruederFeatures(entity, roleColor) {
    // Band of three - unity mark
    const band = new pc.Entity("UnityBand");
    band.addComponent("model", { type: "torus" });
    band.setLocalPosition(0, 0.5, 0);
    band.setLocalScale(0.4, 0.08, 0.4);
    const bandMat = new pc.StandardMaterial();
    bandMat.diffuse = roleColor;
    bandMat.update();
    band.model.material = bandMat;
    entity.addChild(band);
  }

  addFreimaurerFeatures(entity, roleColor) {
    // Square and compass symbol on chest
    const symbol = new pc.Entity("MasonSymbol");
    symbol.addComponent("model", { type: "box" });
    symbol.setLocalPosition(0, 1.05, 0.19);
    symbol.setLocalScale(0.12, 0.12, 0.02);
    const symMat = new pc.StandardMaterial();
    symMat.diffuse = new pc.Color(0.6, 0.55, 0.3);
    symMat.emissive = new pc.Color(0.3, 0.25, 0.1);
    symMat.update();
    symbol.model.material = symMat;
    entity.addChild(symbol);
  }

  addGriesgramFeatures(entity, roleColor) {
    // Grumpy frown mark
    const grumpMarker = new pc.Entity("GrumpMark");
    grumpMarker.addComponent("model", { type: "box" });
    grumpMarker.setLocalPosition(0, 1.75, 0.22);
    grumpMarker.setLocalScale(0.16, 0.03, 0.02);
    const grumpMat = new pc.StandardMaterial();
    grumpMat.diffuse = new pc.Color(0.2, 0.2, 0.2);
    grumpMat.update();
    grumpMarker.model.material = grumpMat;
    entity.addChild(grumpMarker);
  }

  addHundFeatures(entity, roleColor) {
    // Dog ears + snout
    for (let i = 0; i < 2; i++) {
      const ear = new pc.Entity(`DogEar-${i}`);
      ear.addComponent("model", { type: "sphere" });
      ear.setLocalPosition(i === 0 ? -0.2 : 0.2, 2.15, 0.05);
      ear.setLocalScale(0.12, 0.18, 0.1);
      ear.model.material = new pc.StandardMaterial();
      ear.model.material.diffuse = roleColor;
      ear.model.material.update();
      entity.addChild(ear);
    }
  }

  addJesusFeatures(entity, roleColor) {
    // Holy halo + cross
    const halo = new pc.Entity("Halo");
    halo.addComponent("model", { type: "torus" });
    halo.setLocalPosition(0, 2.4, 0);
    halo.setLocalScale(0.4, 0.35, 0.4);
    halo.setLocalEulerAngles(90, 0, 0);
    const haloMat = new pc.StandardMaterial();
    haloMat.emissive = new pc.Color(1, 1, 0.7);
    haloMat.opacity = 0.7;
    haloMat.blendType = pc.BLEND_ADDITIVE;
    haloMat.update();
    halo.model.material = haloMat;
    entity.addChild(halo);
  }

  addTonksFeatures(entity, roleColor) {
    // Color-shifting appearance indicator
    const colorShift = new pc.Entity("ColorShift");
    colorShift.addComponent("model", { type: "sphere" });
    colorShift.setLocalPosition(0.3, 1.5, 0);
    colorShift.setLocalScale(0.2, 0.2, 0.2);
    const shiftMat = new pc.StandardMaterial();
    shiftMat.diffuse = new pc.Color(0.9, 0.4, 0.9);
    shiftMat.emissive = new pc.Color(0.5, 0.2, 0.5);
    shiftMat.opacity = 0.6;
    shiftMat.blendType = pc.BLEND_ADDITIVE;
    shiftMat.update();
    colorShift.model.material = shiftMat;
    entity.addChild(colorShift);
  }

  addZweiSchwesternFeatures(entity, roleColor) {
    // Sister bond mark
    const sisterhood = new pc.Entity("SisterhoodMark");
    sisterhood.addComponent("model", { type: "box" });
    sisterhood.setLocalPosition(0, 0.8, 0.18);
    sisterhood.setLocalScale(0.18, 0.08, 0.03);
    const sMat = new pc.StandardMaterial();
    sMat.diffuse = new pc.Color(0.8, 0.6, 0.8);
    sMat.update();
    sisterhood.model.material = sMat;
    entity.addChild(sisterhood);
  }

  // === HEILER VARIANTEN ===
  addErgebeneMagdFeatures(entity, roleColor) {
    // Servant outfit indicator
    const ribbon = new pc.Entity("Ribbon");
    ribbon.addComponent("model", { type: "box" });
    ribbon.setLocalPosition(0.3, 1.2, -0.18);
    ribbon.setLocalScale(0.08, 0.3, 0.03);
    const ribbonMat = new pc.StandardMaterial();
    ribbonMat.diffuse = new pc.Color(1, 0.8, 0.9);
    ribbonMat.update();
    ribbon.model.material = ribbonMat;
    entity.addChild(ribbon);
  }

  addLeibwaechterFeatures(entity, roleColor) {
    // Armor plating on shoulders
    for (let i = 0; i < 2; i++) {
      const armor = new pc.Entity(`Armor-${i}`);
      armor.addComponent("model", { type: "box" });
      armor.setLocalPosition(i === 0 ? -0.38 : 0.38, 1.3, -0.05);
      armor.setLocalScale(0.15, 0.18, 0.08);
      const armorMat = new pc.StandardMaterial();
      armorMat.diffuse = new pc.Color(0.5, 0.55, 0.6);
      armorMat.shininess = 70;
      armorMat.update();
      armor.model.material = armorMat;
      entity.addChild(armor);
    }
  }

  addOmaFeatures(entity, roleColor) {
    // Grandma shawl
    const shawl = new pc.Entity("Shawl");
    shawl.addComponent("model", { type: "box" });
    shawl.setLocalPosition(0, 1.15, -0.15);
    shawl.setLocalScale(0.65, 0.4, 0.08);
    const shawlMat = new pc.StandardMaterial();
    shawlMat.diffuse = new pc.Color(0.6, 0.4, 0.5);
    shawlMat.update();
    shawl.model.material = shawlMat;
    entity.addChild(shawl);
  }

  addProstituierteFeatures(entity, roleColor) {
    // Red dress accent
    const dress = new pc.Entity("DressAccent");
    dress.addComponent("model", { type: "box" });
    dress.setLocalPosition(0, 0.95, 0.18);
    dress.setLocalScale(0.5, 0.35, 0.05);
    const dressMat = new pc.StandardMaterial();
    dressMat.diffuse = new pc.Color(0.9, 0.3, 0.4);
    dressMat.shininess = 40;
    dressMat.update();
    dress.model.material = dressMat;
    entity.addChild(dress);
  }

  // === HEXE VARIANTEN ===
  addGiftmischerinFeatures(entity, roleColor) {
    // Poison bottles
    for (let i = 0; i < 2; i++) {
      const poison = new pc.Entity(`PoisonBottle-${i}`);
      poison.addComponent("model", { type: "cylinder" });
      poison.setLocalPosition(i === 0 ? -0.3 : 0.3, 0.75, 0.2);
      poison.setLocalScale(0.05, 0.12, 0.05);
      const poisonMat = new pc.StandardMaterial();
      poisonMat.diffuse = new pc.Color(0.4, 0.8, 0.2);
      poisonMat.emissive = new pc.Color(0.2, 0.4, 0.1);
      poisonMat.opacity = 0.8;
      poisonMat.blendType = pc.BLEND_ADDITIVE;
      poisonMat.update();
      poison.model.material = poisonMat;
      entity.addChild(poison);
    }
  }

  addHahnFeatures(entity, roleColor) {
    // Rooster comb
    const comb = new pc.Entity("RoosterComb");
    comb.addComponent("model", { type: "sphere" });
    comb.setLocalPosition(0, 2.35, 0.1);
    comb.setLocalScale(0.15, 0.2, 0.12);
    const combMat = new pc.StandardMaterial();
    combMat.diffuse = new pc.Color(1.0, 0.3, 0.2);
    combMat.shininess = 30;
    combMat.update();
    comb.model.material = combMat;
    entity.addChild(comb);
  }

  addKraeuterweibFeatures(entity, roleColor) {
    // Herb pouch
    const pouch = new pc.Entity("HerbPouch");
    pouch.addComponent("model", { type: "sphere" });
    pouch.setLocalPosition(-0.3, 0.8, 0.15);
    pouch.setLocalScale(0.15, 0.15, 0.1);
    const pouchMat = new pc.StandardMaterial();
    pouchMat.diffuse = new pc.Color(0.4, 0.5, 0.3);
    pouchMat.update();
    pouch.model.material = pouchMat;
    entity.addChild(pouch);
  }

  addSandmannFeatures(entity, roleColor) {
    // Sleepy aura
    const sleepAura = new pc.Entity("SleepAura");
    sleepAura.addComponent("light", {
      type: "point",
      color: new pc.Color(0.8, 0.8, 0.9),
      intensity: 0.4,
      range: 2.0,
    });
    sleepAura.setLocalPosition(0, 1.5, 0);
    entity.addChild(sleepAura);
  }

  addZaubererFeatures(entity, roleColor) {
    // Wizard hat + staff
    const hat = new pc.Entity("WizardHat");
    hat.addComponent("model", { type: "cone" });
    hat.setLocalPosition(0, 2.35, -0.02);
    hat.setLocalScale(0.32, 0.55, 0.32);
    const hatMat = new pc.StandardMaterial();
    hatMat.diffuse = new pc.Color(0.15, 0.15, 0.4);
    hatMat.emissive = new pc.Color(0.08, 0.08, 0.2);
    hatMat.update();
    hat.model.material = hatMat;
    entity.addChild(hat);
  }

  // === JÄGER VARIANTEN ===
  addBuddlerFeatures(entity, roleColor) {
    // Pickaxe
    const pick = new pc.Entity("Pickaxe");
    pick.addComponent("model", { type: "box" });
    pick.setLocalPosition(0.48, 0.9, 0.15);
    pick.setLocalScale(0.2, 0.08, 0.08);
    pick.setLocalEulerAngles(0, 0, 30);
    const pickMat = new pc.StandardMaterial();
    pickMat.diffuse = new pc.Color(0.4, 0.3, 0.2);
    pickMat.update();
    pick.model.material = pickMat;
    entity.addChild(pick);
  }

  addDrachenbaendigerFeatures(entity, roleColor) {
    // Dragon scale decoration
    const scale = new pc.Entity("DragonScale");
    scale.addComponent("model", { type: "sphere" });
    scale.setLocalPosition(0.35, 1.2, 0.15);
    scale.setLocalScale(0.12, 0.12, 0.08);
    const scaleMat = new pc.StandardMaterial();
    scaleMat.diffuse = new pc.Color(0.8, 0.4, 0.1);
    scaleMat.emissive = new pc.Color(0.4, 0.2, 0.05);
    scaleMat.shininess = 85;
    scaleMat.update();
    scale.model.material = scaleMat;
    entity.addChild(scale);
  }

  addFlammenmannFeatures(entity, roleColor) {
    // Fire aura
    const fireAura = new pc.Entity("PersonalFireAura");
    fireAura.addComponent("light", {
      type: "point",
      color: new pc.Color(1, 0.6, 0.2),
      intensity: 0.7,
      range: 2.5,
    });
    fireAura.setLocalPosition(0, 1.5, 0);
    entity.addChild(fireAura);
  }

  addGauklerFeatures(entity, roleColor) {
    // Juggling balls
    for (let i = 0; i < 2; i++) {
      const ball = new pc.Entity(`JugglingBall-${i}`);
      ball.addComponent("model", { type: "sphere" });
      ball.setLocalPosition(i === 0 ? -0.25 : 0.25, 1.35, 0.1);
      ball.setLocalScale(0.08, 0.08, 0.08);
      const ballMat = new pc.StandardMaterial();
      ballMat.diffuse = new pc.Color(0.9, 0.7, 0.2);
      ballMat.emissive = new pc.Color(0.45, 0.35, 0.1);
      ballMat.shininess = 60;
      ballMat.update();
      ball.model.material = ballMat;
      entity.addChild(ball);
    }
  }

  addInquisitorFeatures(entity, roleColor) {
    // Burning symbol
    const symbol = new pc.Entity("InquisitorSymbol");
    symbol.addComponent("model", { type: "box" });
    symbol.setLocalPosition(0, 1.05, 0.19);
    symbol.setLocalScale(0.1, 0.1, 0.02);
    const symMat = new pc.StandardMaterial();
    symMat.diffuse = new pc.Color(0.9, 0.4, 0.1);
    symMat.emissive = new pc.Color(0.5, 0.2, 0.05);
    symMat.update();
    symbol.model.material = symMat;
    entity.addChild(symbol);
  }

  addKamikazeFeatures(entity, roleColor) {
    // Explosive aura - red glow
    const boom = new pc.Entity("BoomAura");
    boom.addComponent("light", {
      type: "point",
      color: new pc.Color(1, 0.1, 0.1),
      intensity: 0.6,
      range: 2.0,
    });
    boom.setLocalPosition(0, 1.5, 0);
    entity.addChild(boom);
  }

  addKoenigFeatures(entity, roleColor) {
    // Crown
    const crown = new pc.Entity("Crown");
    crown.addComponent("model", { type: "torus" });
    crown.setLocalPosition(0, 2.35, 0);
    crown.setLocalScale(0.32, 0.15, 0.32);
    const crownMat = new pc.StandardMaterial();
    crownMat.diffuse = new pc.Color(1, 0.84, 0.0);
    crownMat.emissive = new pc.Color(0.5, 0.42, 0.0);
    crownMat.shininess = 90;
    crownMat.update();
    crown.model.material = crownMat;
    entity.addChild(crown);
  }

  addPrinzFeatures(entity, roleColor) {
    // Prince circlet (smaller crown)
    const circlet = new pc.Entity("Circlet");
    circlet.addComponent("model", { type: "torus" });
    circlet.setLocalPosition(0, 2.3, 0);
    circlet.setLocalScale(0.28, 0.1, 0.28);
    const circletMat = new pc.StandardMaterial();
    circletMat.diffuse = new pc.Color(0.8, 0.7, 0.2);
    circletMat.shininess = 80;
    circletMat.update();
    circlet.model.material = circletMat;
    entity.addChild(circlet);
  }

  addPyromaneFeatures(entity, roleColor) {
    // Flame aura - intense
    const flame = new pc.Entity("PyroFlameAura");
    flame.addComponent("light", {
      type: "point",
      color: new pc.Color(1, 0.5, 0.0),
      intensity: 0.8,
      range: 2.5,
    });
    flame.setLocalPosition(0, 1.5, 0);
    entity.addChild(flame);
  }

  addTanklastwagenfahrerFeatures(entity, roleColor) {
    // Truck driver badge
    const badge = new pc.Entity("TruckBadge");
    badge.addComponent("model", { type: "box" });
    badge.setLocalPosition(0.2, 1.05, 0.19);
    badge.setLocalScale(0.08, 0.1, 0.02);
    const badgeMat = new pc.StandardMaterial();
    badgeMat.diffuse = new pc.Color(0.3, 0.6, 0.3);
    badgeMat.update();
    badge.model.material = badgeMat;
    entity.addChild(badge);
  }

  // === SEHER VARIANTEN ===
  addAurenseherinFeatures(entity, roleColor) {
    // Aura glow
    const auraGlow = new pc.Entity("AuraGlow");
    auraGlow.addComponent("light", {
      type: "point",
      color: new pc.Color(0.9, 0.5, 0.9),
      intensity: 0.6,
      range: 2.5,
    });
    auraGlow.setLocalPosition(0, 1.5, 0);
    entity.addChild(auraGlow);
  }

  addBaerenbaendigerFeatures(entity, roleColor) {
    // Bear strength mark
    const strength = new pc.Entity("StrengthMark");
    strength.addComponent("model", { type: "box" });
    strength.setLocalPosition(0.25, 0.95, 0.18);
    strength.setLocalScale(0.15, 0.2, 0.03);
    const strengthMat = new pc.StandardMaterial();
    strengthMat.diffuse = new pc.Color(0.5, 0.35, 0.2);
    strengthMat.update();
    strength.model.material = strengthMat;
    entity.addChild(strength);
  }

  addDemoskopinFeatures(entity, roleColor) {
    // Poll clipboard
    const clipboard = new pc.Entity("Clipboard");
    clipboard.addComponent("model", { type: "box" });
    clipboard.setLocalPosition(0.35, 1.1, 0.08);
    clipboard.setLocalScale(0.15, 0.25, 0.05);
    clipboard.setLocalEulerAngles(0, 0, 20);
    const clipMat = new pc.StandardMaterial();
    clipMat.diffuse = new pc.Color(0.8, 0.7, 0.5);
    clipMat.update();
    clipboard.model.material = clipMat;
    entity.addChild(clipboard);
  }

  addMediumFeatures(entity, roleColor) {
    // Spirit aura
    const spiritAura = new pc.Entity("SpiritAura");
    spiritAura.addComponent("light", {
      type: "point",
      color: new pc.Color(0.8, 0.6, 1.0),
      intensity: 0.5,
      range: 2.2,
    });
    spiritAura.setLocalPosition(0, 1.5, 0);
    entity.addChild(spiritAura);
  }

  addParanormalerErmittlerFeatures(entity, roleColor) {
    // Investigation tool - magnifier
    const magnifier = new pc.Entity("Magnifier");
    magnifier.addComponent("model", { type: "torus" });
    magnifier.setLocalPosition(0.4, 1.15, 0.05);
    magnifier.setLocalScale(0.1, 0.1, 0.05);
    const magMat = new pc.StandardMaterial();
    magMat.diffuse = new pc.Color(0.7, 0.65, 0.5);
    magMat.shininess = 60;
    magMat.update();
    magnifier.model.material = magMat;
    entity.addChild(magnifier);
  }

  addSeherlehrlingFeatures(entity, roleColor) {
    // Apprentice scroll
    const scroll = new pc.Entity("Scroll");
    scroll.addComponent("model", { type: "cylinder" });
    scroll.setLocalPosition(0.35, 1.0, 0.1);
    scroll.setLocalScale(0.06, 0.25, 0.06);
    const scrollMat = new pc.StandardMaterial();
    scrollMat.diffuse = new pc.Color(0.9, 0.88, 0.8);
    scrollMat.update();
    scroll.model.material = scrollMat;
    entity.addChild(scroll);
  }

  addTratschweibFeatures(entity, roleColor) {
    // Gossip tongue mark
    const gossip = new pc.Entity("GossipMark");
    gossip.addComponent("model", { type: "box" });
    gossip.setLocalPosition(0, 1.72, 0.22);
    gossip.setLocalScale(0.14, 0.04, 0.02);
    const gossipMat = new pc.StandardMaterial();
    gossipMat.diffuse = new pc.Color(0.8, 0.4, 0.4);
    gossipMat.update();
    gossip.model.material = gossipMat;
    entity.addChild(gossip);
  }

  // === SOLO ROLLEN ===
  addHenkerFeatures(entity, roleColor) {
    // Executioner hood
    const hood = new pc.Entity("ExecutionerHood");
    hood.addComponent("model", { type: "sphere" });
    hood.setLocalPosition(0, 1.95, 0.05);
    hood.setLocalScale(0.55, 0.6, 0.5);
    const hoodMat = new pc.StandardMaterial();
    hoodMat.diffuse = new pc.Color(0.05, 0.05, 0.05);
    hoodMat.update();
    hood.model.material = hoodMat;
    entity.addChild(hood);
  }

  addSelbstmoerderFeatures(entity, roleColor) {
    // Sad aura
    const sadAura = new pc.Entity("SadAura");
    sadAura.addComponent("light", {
      type: "point",
      color: new pc.Color(0.4, 0.4, 0.5),
      intensity: 0.3,
      range: 1.5,
    });
    sadAura.setLocalPosition(0, 1.5, 0);
    entity.addChild(sadAura);
  }

  // === SONSTIGE ===
  addBuergermeisterFeatures(entity, roleColor) {
    // Mayor sash
    const sash = new pc.Entity("MayorSash");
    sash.addComponent("model", { type: "box" });
    sash.setLocalPosition(0, 1.0, 0.18);
    sash.setLocalScale(0.55, 0.15, 0.03);
    const sashMat = new pc.StandardMaterial();
    sashMat.diffuse = new pc.Color(0.8, 0.2, 0.2);
    sashMat.emissive = new pc.Color(0.4, 0.1, 0.1);
    sashMat.shininess = 50;
    sashMat.update();
    sash.model.material = sashMat;
    entity.addChild(sash);
  }

  addDiebFeatures(entity, roleColor) {
    // Mask
    const mask = new pc.Entity("Mask");
    mask.addComponent("model", { type: "box" });
    mask.setLocalPosition(0, 1.9, 0.2);
    mask.setLocalScale(0.3, 0.15, 0.04);
    const maskMat = new pc.StandardMaterial();
    maskMat.diffuse = new pc.Color(0.1, 0.1, 0.1);
    maskMat.update();
    mask.model.material = maskMat;
    entity.addChild(mask);
  }

  addDoppelgaengerFeatures(entity, roleColor) {
    // Mirror shimmer
    const shimmer = new pc.Entity("Shimmer");
    shimmer.addComponent("light", {
      type: "point",
      color: new pc.Color(0.7, 0.7, 0.8),
      intensity: 0.4,
      range: 2.0,
    });
    shimmer.setLocalPosition(0, 1.5, 0);
    entity.addChild(shimmer);
  }

  addEngelFeatures(entity, roleColor) {
    // Angel halo
    const halo = new pc.Entity("AngelHalo");
    halo.addComponent("model", { type: "torus" });
    halo.setLocalPosition(0, 2.4, 0);
    halo.setLocalScale(0.35, 0.3, 0.35);
    halo.setLocalEulerAngles(90, 0, 0);
    const haloMat = new pc.StandardMaterial();
    haloMat.emissive = new pc.Color(1, 0.95, 0.7);
    haloMat.opacity = 0.8;
    haloMat.blendType = pc.BLEND_ADDITIVE;
    haloMat.update();
    halo.model.material = haloMat;
    entity.addChild(halo);
  }

  addGerberFeatures(entity, roleColor) {
    // Leather working tools
    const tool = new pc.Entity("LeatherTool");
    tool.addComponent("model", { type: "box" });
    tool.setLocalPosition(0.35, 0.85, 0.15);
    tool.setLocalScale(0.1, 0.08, 0.06);
    const toolMat = new pc.StandardMaterial();
    toolMat.diffuse = new pc.Color(0.6, 0.45, 0.3);
    toolMat.update();
    tool.model.material = toolMat;
    entity.addChild(tool);
  }

  addKleinesMaedchenFeatures(entity, roleColor) {
    // Innocence ribbon
    const ribbon = new pc.Entity("InnocenceRibbon");
    ribbon.addComponent("model", { type: "box" });
    ribbon.setLocalPosition(0.2, 2.0, -0.1);
    ribbon.setLocalScale(0.1, 0.15, 0.03);
    const ribbonMat = new pc.StandardMaterial();
    ribbonMat.diffuse = new pc.Color(1, 0.7, 0.85);
    ribbonMat.update();
    ribbon.model.material = ribbonMat;
    entity.addChild(ribbon);
  }

  addPutzfrauFeatures(entity, roleColor) {
    // Cleaning bucket
    const bucket = new pc.Entity("Bucket");
    bucket.addComponent("model", { type: "cylinder" });
    bucket.setLocalPosition(-0.4, 0.5, 0.1);
    bucket.setLocalScale(0.1, 0.12, 0.1);
    const bucketMat = new pc.StandardMaterial();
    bucketMat.diffuse = new pc.Color(0.6, 0.5, 0.4);
    bucketMat.update();
    bucket.model.material = bucketMat;
    entity.addChild(bucket);
  }

  addSuendenbockFeatures(entity, roleColor) {
    // Scapegoat mark
    const mark = new pc.Entity("ScapegoatMark");
    mark.addComponent("model", { type: "sphere" });
    mark.setLocalPosition(-0.2, 1.5, 0.15);
    mark.setLocalScale(0.15, 0.15, 0.08);
    const markMat = new pc.StandardMaterial();
    markMat.diffuse = new pc.Color(0.6, 0.4, 0.3);
    markMat.update();
    mark.model.material = markMat;
    entity.addChild(mark);
  }

  // === SPEZIAL ===
  addChemielaborantFeatures(entity, roleColor) {
    // Chemical vials
    for (let i = 0; i < 2; i++) {
      const vial = new pc.Entity(`ChemicalVial-${i}`);
      vial.addComponent("model", { type: "cylinder" });
      vial.setLocalPosition(i === 0 ? -0.35 : 0.35, 0.8, 0.2);
      vial.setLocalScale(0.05, 0.15, 0.05);
      const vialMat = new pc.StandardMaterial();
      vialMat.diffuse = new pc.Color(0.3, 0.8, 0.5);
      vialMat.emissive = new pc.Color(0.15, 0.4, 0.25);
      vialMat.opacity = 0.9;
      vialMat.blendType = pc.BLEND_ADDITIVE;
      vialMat.update();
      vial.model.material = vialMat;
      entity.addChild(vial);
    }
  }

  addDunklerPriesterFeatures(entity, roleColor) {
    // Priest robes + dark aura
    const robes = new pc.Entity("PriestRobes");
    robes.addComponent("model", { type: "box" });
    robes.setLocalPosition(0, 0.95, -0.15);
    robes.setLocalScale(0.6, 0.5, 0.12);
    const robesMat = new pc.StandardMaterial();
    robesMat.diffuse = new pc.Color(0.1, 0.05, 0.1);
    robesMat.update();
    robes.model.material = robesMat;
    entity.addChild(robes);
  }

  addFluechtlingeFeatures(entity, roleColor) {
    // Refugee pack
    const pack = new pc.Entity("RefugeePack");
    pack.addComponent("model", { type: "box" });
    pack.setLocalPosition(-0.35, 1.2, -0.2);
    pack.setLocalScale(0.15, 0.25, 0.1);
    const packMat = new pc.StandardMaterial();
    packMat.diffuse = new pc.Color(0.5, 0.4, 0.3);
    packMat.update();
    pack.model.material = packMat;
    entity.addChild(pack);
  }

  addHureFeatures(entity, roleColor) {
    // Red dress accent
    const dress = new pc.Entity("HureDress");
    dress.addComponent("model", { type: "box" });
    dress.setLocalPosition(0, 0.95, 0.18);
    dress.setLocalScale(0.55, 0.4, 0.05);
    const dressMat = new pc.StandardMaterial();
    dressMat.diffuse = new pc.Color(0.95, 0.2, 0.3);
    dressMat.shininess = 50;
    dressMat.update();
    dress.model.material = dressMat;
    entity.addChild(dress);
  }

  addMordlustigerFeatures(entity, roleColor) {
    // Blood lust aura
    const lust = new pc.Entity("BloodLustAura");
    lust.addComponent("light", {
      type: "point",
      color: new pc.Color(1, 0.2, 0.2),
      intensity: 0.7,
      range: 2.3,
    });
    lust.setLocalPosition(0, 1.5, 0);
    entity.addChild(lust);
  }

  addNutteFeatures(entity, roleColor) {
    // Pink dress accent
    const dress = new pc.Entity("NutteDress");
    dress.addComponent("model", { type: "box" });
    dress.setLocalPosition(0, 0.95, 0.18);
    dress.setLocalScale(0.5, 0.35, 0.05);
    const dressMat = new pc.StandardMaterial();
    dressMat.diffuse = new pc.Color(0.9, 0.4, 0.6);
    dressMat.shininess = 40;
    dressMat.update();
    dress.model.material = dressMat;
    entity.addChild(dress);
  }

  addRabeFeatures(entity, roleColor) {
    // Raven feathers
    const feather = new pc.Entity("RavenFeather");
    feather.addComponent("model", { type: "box" });
    feather.setLocalPosition(-0.25, 2.1, -0.15);
    feather.setLocalScale(0.12, 0.35, 0.04);
    feather.setLocalEulerAngles(0, 0, -30);
    const featherMat = new pc.StandardMaterial();
    featherMat.diffuse = new pc.Color(0.05, 0.05, 0.08);
    featherMat.update();
    feather.model.material = featherMat;
    entity.addChild(feather);
  }

  addZahnarztFeatures(entity, roleColor) {
    // Dentist mirror
    const mirror = new pc.Entity("DentistMirror");
    mirror.addComponent("model", { type: "sphere" });
    mirror.setLocalPosition(0.35, 1.1, 0.15);
    mirror.setLocalScale(0.08, 0.08, 0.04);
    const mirrorMat = new pc.StandardMaterial();
    mirrorMat.diffuse = new pc.Color(0.8, 0.8, 0.9);
    mirrorMat.shininess = 95;
    mirrorMat.update();
    mirror.model.material = mirrorMat;
    entity.addChild(mirror);
  }

  createNameLabel(name, isAlive) {
    const label = new pc.Entity("NameLabel");
    label.addComponent("model", { type: "plane" });
    // Negative X scale flips the texture horizontally to un-mirror it
    label.setLocalScale(-2, 0.5, 1);

    // Create canvas for text - higher resolution for sharper text
    const canvas = document.createElement("canvas");
    canvas.width = 512;
    canvas.height = 128;
    const ctx = canvas.getContext("2d");

    // Background with rounded corners effect
    ctx.fillStyle = isAlive ? "rgba(0, 0, 0, 0.8)" : "rgba(0, 0, 0, 0.5)";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Text - larger font for higher res canvas
    ctx.fillStyle = isAlive ? "#FFFFFF" : "#999999";
    ctx.font = "bold 64px Arial, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";

    // Add subtle text shadow for better readability
    ctx.shadowColor = "rgba(0, 0, 0, 0.5)";
    ctx.shadowBlur = 4;
    ctx.shadowOffsetX = 2;
    ctx.shadowOffsetY = 2;
    ctx.fillText(name, canvas.width / 2, canvas.height / 2);

    // Create texture from canvas
    const texture = new pc.Texture(this.app.graphicsDevice, {
      width: canvas.width,
      height: canvas.height,
      format: pc.PIXELFORMAT_R8_G8_B8_A8,
      mipmaps: true,
      minFilter: pc.FILTER_LINEAR_MIPMAP_LINEAR,
      magFilter: pc.FILTER_LINEAR,
    });

    const pixels = ctx.getImageData(0, 0, canvas.width, canvas.height);
    texture.lock().set(new Uint8Array(pixels.data));
    texture.unlock();

    // Apply to material
    const mat = new pc.StandardMaterial();
    mat.diffuseMap = texture;
    mat.emissive = new pc.Color(1, 1, 1);
    mat.emissiveMap = texture;
    mat.opacity = isAlive ? 1.0 : 0.6;
    mat.blendType = pc.BLEND_NORMAL;
    mat.cull = pc.CULLFACE_NONE; // Double-sided so visible from both directions
    mat.depthWrite = false; // Helps with transparency sorting
    mat.update();

    label.model.material = mat;

    return label;
  }

  setTimeOfDay(isNight) {
    this.isNight = isNight;

    if (isNight) {
      // Night settings
      this.light.light.color = new pc.Color(0.15, 0.2, 0.4); // Deep moonlight
      this.light.light.intensity = 0.3;
      this.fillLight.light.intensity = 0.1;

      // Update scene properties using the correct API
      this.setSceneSettings({
        ambientLight: new pc.Color(0.03, 0.03, 0.08),
        fogColor: new pc.Color(0.02, 0.02, 0.05),
        fogDensity: 0.03,
      });

      if (this.fireLight) this.fireLight.enabled = true;

      // Show fireflies
      this.fireflies?.forEach((f) => (f.entity.enabled = true));

      // Dim building windows
      this.buildings.forEach((building) => {
        building.children.forEach((child) => {
          if (child.name === "Window" && child.model) {
            child.model.material.emissive = new pc.Color(0.8, 0.7, 0.4);
            child.model.material.update();
          }
        });
      });

      // Make sleeping/inactive players appear to sleep at night
      this.playerEntities.forEach((entity, playerId) => {
        if (this.sleepingPlayers.has(playerId)) {
          this.applySleepingState(entity, true);
        }
      });
    } else {
      // Day settings
      this.light.light.color = new pc.Color(1, 0.95, 0.85); // Warm sunlight
      this.light.light.intensity = 1.2;
      this.fillLight.light.intensity = 0.4;

      // Update scene properties using the correct API
      this.setSceneSettings({
        ambientLight: new pc.Color(0.5, 0.5, 0.55),
        fogColor: new pc.Color(0.7, 0.8, 0.9),
        fogDensity: 0.005,
      });

      if (this.fireLight) this.fireLight.enabled = false; // Fire less visible during day

      // Hide fireflies
      this.fireflies?.forEach((f) => (f.entity.enabled = false));

      // No window glow during day
      this.buildings.forEach((building) => {
        building.children.forEach((child) => {
          if (child.name === "Window" && child.model) {
            child.model.material.emissive = new pc.Color(0, 0, 0);
            child.model.material.update();
          }
        });
      });

      // Wake up all players during day
      this.playerEntities.forEach((entity) => {
        this.applySleepingState(entity, false);
      });
    }
  }

  /**
   * Apply or remove sleeping visual state to a player
   * @param {pc.Entity} entity - Player entity
   * @param {boolean} isSleeping - Whether player is sleeping
   */
  applySleepingState(entity, isSleeping) {
    if (!entity || !entity.parts) return;

    if (isSleeping) {
      // Tilt head down as if sleeping
      if (entity.parts.head) {
        entity.parts.head.setLocalEulerAngles(20, 0, 0); // Head tilted down
      }

      // Lower arms
      if (entity.parts.arms && entity.parts.arms.length > 0) {
        entity.parts.arms.forEach((armPivot) => {
          armPivot.setLocalEulerAngles(0, 0, 0); // Arms at rest
        });
      }

      // Add Z's floating above head
      if (!entity.findByName("SleepingZ")) {
        const zMarker = new pc.Entity("SleepingZ");
        zMarker.addComponent("model", { type: "plane" });
        zMarker.setLocalPosition(0, 3.2, 0);
        zMarker.setLocalScale(0.5, 0.5, 0.5);

        // Use cached Z texture if available - prevents creating many textures
        if (!this.sleepZTexture) {
          // Create canvas with "Z" text
          const canvas = document.createElement("canvas");
          canvas.width = 128;
          canvas.height = 128;
          const ctx = canvas.getContext("2d");
          ctx.fillStyle = "rgba(255, 255, 255, 0.8)";
          ctx.font = "bold 80px Arial";
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.fillText("Z", 64, 64);

          this.sleepZTexture = new pc.Texture(this.app.graphicsDevice, {
            width: canvas.width,
            height: canvas.height,
            format: pc.PIXELFORMAT_R8_G8_B8_A8,
          });
          const pixels = ctx.getImageData(0, 0, canvas.width, canvas.height);
          this.sleepZTexture.lock().set(new Uint8Array(pixels.data));
          this.sleepZTexture.unlock();
        }

        const mat = new pc.StandardMaterial();
        mat.diffuseMap = this.sleepZTexture;
        mat.emissive = new pc.Color(1, 1, 1);
        mat.opacity = 0.8;
        mat.blendType = pc.BLEND_NORMAL;
        mat.cull = pc.CULLFACE_NONE;
        mat.update();
        zMarker.model.material = mat;

        entity.addChild(zMarker);
      }
    } else {
      // Reset to normal posture
      if (entity.parts.head) {
        entity.parts.head.setLocalEulerAngles(0, 0, 0);
      }

      // Remove Z marker
      const zMarker = entity.findByName("SleepingZ");
      if (zMarker) {
        zMarker.destroy();
      }
    }
  }

  /**
   * Mark a player as sleeping/inactive
   * @param {string} playerId
   */
  setPlayerSleeping(playerId, isSleeping) {
    if (isSleeping) {
      this.sleepingPlayers.add(playerId);
    } else {
      this.sleepingPlayers.delete(playerId);
    }

    const entity = this.playerEntities.get(playerId);
    if (entity && this.isNight) {
      this.applySleepingState(entity, isSleeping);
    }
  }

  // Helper to set scene rendering settings with proper API support
  setSceneSettings(settings) {
    try {
      // Try newer API first (PlayCanvas 1.60+)
      if (this.app.scene.rendering) {
        if (settings.ambientLight)
          this.app.scene.rendering.ambientLight = settings.ambientLight;
        if (settings.fogColor)
          this.app.scene.rendering.fogColor = settings.fogColor;
        if (settings.fogDensity !== undefined)
          this.app.scene.rendering.fogDensity = settings.fogDensity;
      } else {
        // Fallback for older API - direct property access with assignments
        const scene = this.app.scene;
        if (settings.ambientLight && scene.ambientLight) {
          scene.ambientLight.copy(settings.ambientLight);
        }
      }
    } catch (e) {
      console.debug("Scene settings update skipped:", e.message);
    }
  }

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

  showHint(playerId, type) {
    const entity = this.playerEntities.get(playerId);
    if (!entity) return;

    // Hint color mapping for different effects
    const hintColors = {
      eyes_glow_red: new pc.Color(1, 0.2, 0.1), // Red eyes
      shadow_pass: new pc.Color(0.2, 0.2, 0.3), // Dark shadow
      moonbeam: new pc.Color(0.8, 0.9, 1.0), // Moonlight white
      character_shake: new pc.Color(0.8, 0.6, 0.2), // Nervous yellow
      look_away: new pc.Color(0.6, 0.6, 0.6), // Gray
      aura_glow: new pc.Color(0.5, 0.3, 0.9), // Purple glow
      suspicious_behavior: new pc.Color(1.0, 0.5, 0), // Orange suspicious
      character_stumble: new pc.Color(0.6, 0.4, 0.2), // Brown stumble
      danger: new pc.Color(1, 0, 0),
      default: new pc.Color(1, 1, 0),
    };

    const hintColor = hintColors[type] || hintColors["default"];

    // Create hint icon above player
    const hint = new pc.Entity("Hint");
    hint.addComponent("model", { type: "sphere" });
    hint.setLocalPosition(0, 3.5, 0);
    hint.setLocalScale(0.4, 0.4, 0.4);

    const mat = new pc.StandardMaterial();
    mat.emissive = hintColor;
    mat.opacity = 0.8;
    mat.blendType = pc.BLEND_ADDITIVE;
    mat.update();
    hint.model.material = mat;

    entity.addChild(hint);

    // Special effect: shake the character for 'character_shake' or 'character_stumble'
    if (type === "character_shake" || type === "character_stumble") {
      const originalPos = entity.getLocalPosition().clone();
      let shakeTime = 0;
      const shakeUpdate = (dt) => {
        shakeTime += dt;
        const intensity = type === "character_shake" ? 0.05 : 0.1;
        entity.setLocalPosition(
          originalPos.x + Math.sin(shakeTime * 30) * intensity,
          originalPos.y,
          originalPos.z + Math.cos(shakeTime * 25) * intensity,
        );
        if (shakeTime > 0.8) {
          this.app.off("update", shakeUpdate);
          entity.setLocalPosition(originalPos.x, originalPos.y, originalPos.z);
        }
      };
      this.app.on("update", shakeUpdate);
    }

    // Special effect: eye glow for 'eyes_glow_red'
    if (type === "eyes_glow_red" && entity.parts && entity.parts.head) {
      const eyes = entity.parts.head.findByName
        ? [
            entity.parts.head.findByName("EyeWhite-0"),
            entity.parts.head.findByName("EyeWhite-1"),
          ]
        : [];
      const originalMats = [];
      eyes.forEach((eye, i) => {
        if (eye && eye.model) {
          originalMats[i] = eye.model.material;
          const glowMat = new pc.StandardMaterial();
          glowMat.emissive = new pc.Color(1, 0.1, 0);
          glowMat.diffuse = new pc.Color(1, 0.2, 0.1);
          glowMat.update();
          eye.model.material = glowMat;
        }
      });
      // Restore after delay
      setTimeout(() => {
        eyes.forEach((eye, i) => {
          if (eye && eye.model && originalMats[i]) {
            eye.model.material = originalMats[i];
          }
        });
      }, 1500);
    }

    // Animate and remove hint orb
    let time = 0;
    const updateHint = (dt) => {
      time += dt;
      hint.setLocalPosition(0, 3.5 + Math.sin(time * 3) * 0.3, 0);
      hint.setLocalScale(
        0.4 + Math.sin(time * 5) * 0.1,
        0.4 + Math.sin(time * 5) * 0.1,
        0.4 + Math.sin(time * 5) * 0.1,
      );
      // Fade out
      if (time > 2) {
        mat.opacity = 0.8 * (1 - (time - 2));
        mat.update();
      }

      if (time > 3) {
        this.app.off("update", updateHint);
        hint.destroy();
      }
    };
    this.app.on("update", updateHint);
  }

  update(dt) {
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

    // Animate Fire
    if (this.fireLight.enabled) {
      // Flicker light
      this.fireLight.light.intensity = 3 + Math.random() * 0.8;

      // Animate particles
      this.fireParticles.forEach((p) => {
        p.life += dt * p.speed;
        if (p.life > 1) p.life = 0;

        const y = p.life * 3.5;
        const scale = (1 - p.life) * 0.5;

        p.entity.setLocalPosition(
          Math.sin(p.life * 12 + p.offset) * 0.3,
          y,
          Math.cos(p.life * 12 + p.offset) * 0.3,
        );
        p.entity.setLocalScale(scale, scale, scale);
        p.entity.lookAt(this.camera.getPosition());
        p.entity.rotateLocal(90, 0, 0);
      });
    }

    // Update animated features from role definitions
    this.updateAnimatedFeatures(dt);

    // Animate fireflies (night only)
    if (this.isNight && this.fireflies && this.fireflies.length > 0) {
      this.fireflies.forEach((f) => {
        if (!f.entity || !f.entity.light) return;
        f.phase += dt * f.speed;
        const newAngle = f.angle + Math.sin(f.phase) * 0.5;
        const newRadius = f.radius + Math.cos(f.phase * 0.7) * 2;
        const newHeight = f.height + Math.sin(f.phase * 1.3) * 1;

        f.entity.setPosition(
          Math.cos(newAngle) * newRadius,
          newHeight,
          Math.sin(newAngle) * newRadius,
        );

        // Flicker intensity
        f.entity.light.intensity = 0.3 + Math.sin(f.phase * 5) * 0.2;
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

  // 3D Vote Visualization - Show vote indicator above player
  showVoteIndicator(playerId, voterName) {
    const entity = this.playerEntities.get(playerId);
    if (!entity) return;

    // Create vote badge
    const voteBadge = new pc.Entity(`VoteBadge-${Date.now()}`);
    voteBadge.addComponent("model", { type: "sphere" });
    voteBadge.setLocalPosition(
      Math.random() * 0.6 - 0.3,
      3.8 + Math.random() * 0.4,
      0,
    );
    voteBadge.setLocalScale(0.2, 0.2, 0.2);

    const mat = new pc.StandardMaterial();
    mat.diffuse = new pc.Color(1, 0, 0);
    mat.emissive = new pc.Color(1, 0.2, 0.2);
    mat.opacity = 0.9;
    mat.blendType = pc.BLEND_ADDITIVE;
    mat.update();
    voteBadge.model.material = mat;

    entity.addChild(voteBadge);

    // Animate vote badge
    let time = 0;
    const animateVote = (dt) => {
      time += dt;
      voteBadge.setLocalPosition(
        voteBadge.getLocalPosition().x,
        3.8 + Math.sin(time * 3) * 0.2,
        voteBadge.getLocalPosition().z,
      );

      if (time > 5) {
        this.app.off("update", animateVote);
        voteBadge.destroy();
      }
    };
    this.app.on("update", animateVote);
  }

  // 3D Chat Bubble - Display chat message above player
  showChatBubble(playerId, message, duration = 5000) {
    const entity = this.playerEntities.get(playerId);
    if (!entity) return;

    // Create chat bubble
    const bubble = new pc.Entity("ChatBubble");
    bubble.addComponent("model", { type: "plane" });
    bubble.setLocalPosition(0, 4.0, 0);

    // Calculate size based on message length
    const width = Math.min(Math.max(message.length * 0.15, 2), 5);
    bubble.setLocalScale(width, 0.8, 1);

    // Create canvas for text
    const canvas = document.createElement("canvas");
    canvas.width = 512;
    canvas.height = 128;
    const ctx = canvas.getContext("2d");

    // Background
    ctx.fillStyle = "rgba(40, 40, 50, 0.9)";
    ctx.beginPath();
    ctx.moveTo(10 + 15, 10);
    ctx.lineTo(canvas.width - 10 - 15, 10);
    ctx.arcTo(canvas.width - 10, 10, canvas.width - 10, 10 + 15, 15);
    ctx.lineTo(canvas.width - 10, canvas.height - 10 - 15);
    ctx.arcTo(
      canvas.width - 10,
      canvas.height - 10,
      canvas.width - 10 - 15,
      canvas.height - 10,
      15,
    );
    ctx.lineTo(10 + 15, canvas.height - 10);
    ctx.arcTo(10, canvas.height - 10, 10, canvas.height - 10 - 15, 15);
    ctx.lineTo(10, 10 + 15);
    ctx.arcTo(10, 10, 10 + 15, 10, 15);
    ctx.closePath();
    ctx.fill();

    // Border
    ctx.strokeStyle = "rgba(212, 175, 55, 0.8)";
    ctx.lineWidth = 3;
    ctx.stroke();

    // Text
    ctx.fillStyle = "#FFFFFF";
    ctx.font = "bold 32px Arial";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";

    // Word wrap
    const maxWidth = canvas.width - 40;
    const words = message.split(" ");
    let line = "";
    let y = canvas.height / 2;

    words.forEach((word) => {
      const testLine = line + word + " ";
      const metrics = ctx.measureText(testLine);
      if (metrics.width > maxWidth && line !== "") {
        ctx.fillText(line, canvas.width / 2, y - 10);
        line = word + " ";
        y += 20;
      } else {
        line = testLine;
      }
    });
    ctx.fillText(line, canvas.width / 2, y);

    // Create texture
    const texture = new pc.Texture(this.app.graphicsDevice, {
      width: canvas.width,
      height: canvas.height,
      format: pc.PIXELFORMAT_R8_G8_B8_A8,
    });
    const pixels = ctx.getImageData(0, 0, canvas.width, canvas.height);
    texture.lock().set(new Uint8Array(pixels.data));
    texture.unlock();

    // Apply material
    const mat = new pc.StandardMaterial();
    mat.diffuseMap = texture;
    mat.emissive = new pc.Color(0.2, 0.2, 0.2);
    mat.opacity = 1.0;
    mat.blendType = pc.BLEND_NORMAL;
    mat.update();
    bubble.model.material = mat;

    entity.addChild(bubble);

    // Animate bubble
    let time = 0;
    const animateBubble = (dt) => {
      time += dt;
      bubble.setLocalPosition(0, 4.0 + Math.sin(time * 2) * 0.1, 0);
      bubble.lookAt(this.camera.getPosition());

      if (time > duration / 1000) {
        this.app.off("update", animateBubble);
        bubble.destroy();
      }
    };
    this.app.on("update", animateBubble);
  }

  // Show action effect (healing, attack, etc.)
  showActionEffect(playerId, effectType) {
    const entity = this.playerEntities.get(playerId);
    if (!entity) return;

    let color, particleCount, particleSpeed;

    switch (effectType) {
      case "heal":
        color = new pc.Color(0, 1, 0);
        particleCount = 20;
        particleSpeed = 2;
        break;
      case "attack":
        color = new pc.Color(1, 0, 0);
        particleCount = 30;
        particleSpeed = 3;
        break;
      case "protect":
        color = new pc.Color(0, 0.5, 1);
        particleCount = 25;
        particleSpeed = 1.5;
        break;
      case "poison":
        color = new pc.Color(0.5, 0, 0.8);
        particleCount = 25;
        particleSpeed = 2.5;
        break;
      case "love":
        color = new pc.Color(1, 0.4, 0.7);
        particleCount = 30;
        particleSpeed = 1.8;
        break;
      default:
        color = new pc.Color(1, 1, 0);
        particleCount = 20;
        particleSpeed = 2;
    }

    // Create particle system
    const particles = [];
    for (let i = 0; i < particleCount; i++) {
      const particle = new pc.Entity(`Particle-${i}`);
      particle.addComponent("model", { type: "sphere" });
      particle.setLocalScale(0.15, 0.15, 0.15);

      const mat = new pc.StandardMaterial();
      mat.emissive = color;
      mat.opacity = 0.8;
      mat.blendType = pc.BLEND_ADDITIVE;
      mat.update();
      particle.model.material = mat;

      entity.addChild(particle);
      particles.push({
        entity: particle,
        velocity: new pc.Vec3(
          (Math.random() - 0.5) * 2,
          Math.random() * 3 + 1,
          (Math.random() - 0.5) * 2,
        ),
        life: 0,
        maxLife: 1 + Math.random() * 0.5,
      });
    }

    // Animate particles
    const animateEffect = (dt) => {
      let allDead = true;
      particles.forEach((p) => {
        p.life += dt * particleSpeed;
        if (p.life < p.maxLife) {
          allDead = false;
          const pos = p.entity.getLocalPosition();
          pos.add(p.velocity.clone().scale(dt));
          p.velocity.y -= dt * 5; // Gravity
          p.entity.setLocalPosition(pos);

          // Fade out
          const alpha = 1 - p.life / p.maxLife;
          p.entity.setLocalScale(0.15 * alpha, 0.15 * alpha, 0.15 * alpha);
        } else {
          p.entity.enabled = false;
        }
      });

      if (allDead) {
        this.app.off("update", animateEffect);
        particles.forEach((p) => p.entity.destroy());
      }
    };
    this.app.on("update", animateEffect);
  }

  // Update player status (e.g., when killed)
  updatePlayerStatus(playerId, isAlive) {
    const entity = this.playerEntities.get(playerId);
    if (!entity) return;

    if (!isAlive) {
      // Create cached dead material if not exists
      if (!this.deadMaterial) {
        this.deadMaterial = new pc.StandardMaterial();
        this.deadMaterial.diffuse = new pc.Color(0.3, 0.3, 0.3);
        this.deadMaterial.opacity = 0.4;
        this.deadMaterial.blendType = pc.BLEND_NORMAL;
        this.deadMaterial.update();
      }

      // Make player gray and semi-transparent
      entity.children.forEach((child) => {
        if (child.model && child.model.material) {
          // Use cached material
          child.model.material = this.deadMaterial;
        }
        if (child.light) {
          child.enabled = false;
        }
      });

      // Show death effect
      this.showActionEffect(playerId, "attack");

      // Add tombstone
      const tombstone = new pc.Entity("Tombstone");
      tombstone.addComponent("model", { type: "box" });
      tombstone.setLocalScale(0.6, 1.2, 0.2);
      tombstone.setLocalPosition(0, 0.6, 1);
      tombstone.setLocalEulerAngles(-10, 0, 0);

      const mat = new pc.StandardMaterial();
      mat.diffuse = new pc.Color(0.3, 0.3, 0.35);
      mat.update();
      tombstone.model.material = mat;
      entity.addChild(tombstone);
    }
  }
}
