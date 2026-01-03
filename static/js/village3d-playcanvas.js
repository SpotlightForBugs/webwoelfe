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

    // Lobby mode - simplified view with no buildings/environment
    this.isLobbyMode = options.lobbyMode || false;

    // Camera settings - adjust for lobby vs game mode
    if (this.isLobbyMode) {
      // Lobby: more top-down view, closer to see players
      this.defaultCameraAngle = 0;
      this.defaultCameraHeight = 20; // Higher for top-down
      this.defaultCameraRadius = 18; // Closer to players
    } else {
      // Game: standard perspective view
      this.defaultCameraAngle = 0;
      this.defaultCameraHeight = 15;
      this.defaultCameraRadius = 25;
    }

    // Role colors for player appearance
    this.roleColors = {
      Werwolf: new pc.Color(0.6, 0.1, 0.1), // Dark red
      Dorfbewohner: new pc.Color(0.3, 0.5, 0.8), // Blue
      Seherin: new pc.Color(0.5, 0.3, 0.9), // Purple
      Hexe: new pc.Color(0.2, 0.7, 0.3), // Green
      Jäger: new pc.Color(0.6, 0.5, 0.2), // Brown/Gold
      Amor: new pc.Color(1.0, 0.4, 0.7), // Pink
      Heiler: new pc.Color(0.9, 0.9, 0.2), // Yellow
      default: new pc.Color(0.7, 0.7, 0.7), // Gray
    };

    if (!this.container) {
      console.warn("Village3D container not found:", containerId);
      return;
    }

    this.init();
  }

  init() {
    // Create canvas
    this.canvas = document.createElement("canvas");
    this.canvas.style.width = "100%";
    this.canvas.style.height = "100%";
    this.canvas.style.display = "block";
    this.container.appendChild(this.canvas);

    // Initialize PlayCanvas
    this.app = new pc.Application(this.canvas, {
      mouse: new pc.Mouse(this.canvas),
      touch: new pc.TouchDevice(this.canvas),
      elementInput: new pc.ElementInput(this.canvas),
    });

    this.app.start();
    // Use NONE to respect container size, not FILL_WINDOW which ignores it
    this.app.setCanvasFillMode(pc.FILLMODE_NONE);
    this.app.setCanvasResolution(pc.RESOLUTION_AUTO);

    // Resize handler to match container size
    const resizeCanvas = () => {
      if (this.container && this.canvas) {
        this.canvas.width = this.container.clientWidth;
        this.canvas.height = this.container.clientHeight;
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
  }

  createScene() {
    // Ambient Light
    this.app.scene.ambientLight = new pc.Color(0.1, 0.1, 0.15);

    // Camera
    this.camera = new pc.Entity("Camera");
    this.camera.addComponent("camera", {
      clearColor: new pc.Color(0.05, 0.05, 0.08),
      farClip: 150,
      fov: 45,
    });
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
    this.targetPosition = new pc.Vec3(0, 0, 0);

    // Directional Light (Moon/Sun)
    this.light = new pc.Entity("DirectionalLight");
    this.light.addComponent("light", {
      type: "directional",
      color: new pc.Color(0.6, 0.7, 0.9),
      intensity: 0.8,
      castShadows: true,
      shadowBias: 0.05,
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

    // Only create full village in game mode, not in lobby
    if (!this.isLobbyMode) {
      // Village Buildings
      this.createVillageBuildings();

      // Campfire (center)
      this.createCampfire();

      // Environment (Trees, Stones, Fence)
      this.createEnvironment();

      // Atmospheric effects
      this.createAtmosphericEffects();
    } else {
      // Lobby mode: minimal scene - just a simple center marker
      this.createSimpleCampfire();
    }
  }

  createDetailedGround() {
    // Main ground
    const ground = new pc.Entity("Ground");
    ground.addComponent("model", {
      type: "plane",
    });

    // Smaller ground in lobby mode
    const groundSize = this.isLobbyMode ? 30 : 80;
    ground.setLocalScale(groundSize, 1, groundSize);

    const material = new pc.StandardMaterial();
    material.diffuse = new pc.Color(0.12, 0.18, 0.08); // Rich grass
    material.specular = new pc.Color(0.02, 0.02, 0.02);
    material.shininess = 5;
    material.update();

    ground.model.material = material;
    this.app.root.addChild(ground);

    // Village center circle (lighter area) - smaller in lobby
    const centerCircle = new pc.Entity("CenterCircle");
    centerCircle.addComponent("model", {
      type: "cylinder",
    });
    const circleSize = this.isLobbyMode ? 12 : 18;
    centerCircle.setLocalScale(circleSize, 0.05, circleSize);
    centerCircle.setPosition(0, 0.05, 0);

    const circleMat = new pc.StandardMaterial();
    circleMat.diffuse = new pc.Color(0.25, 0.22, 0.18); // Dirt/worn grass
    circleMat.update();
    centerCircle.model.material = circleMat;

    this.app.root.addChild(centerCircle);
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

    // House base
    const base = new pc.Entity("Base");
    base.addComponent("model", { type: "box" });
    base.setLocalScale(4, 3, 5);
    base.setLocalPosition(0, 1.5, 0);

    const baseMat = new pc.StandardMaterial();
    const hue = 0.05 + Math.random() * 0.1; // Slight variation
    baseMat.diffuse = new pc.Color(hue + 0.5, hue + 0.4, hue + 0.3); // Wooden/stone
    baseMat.update();
    base.model.material = baseMat;
    house.addChild(base);

    // Roof
    const roof = new pc.Entity("Roof");
    roof.addComponent("model", { type: "cone" });
    roof.setLocalScale(5, 2.5, 5.5);
    roof.setLocalPosition(0, 3.5, 0);
    roof.setLocalEulerAngles(0, 45, 0);

    const roofMat = new pc.StandardMaterial();
    roofMat.diffuse = new pc.Color(0.4, 0.2, 0.15); // Dark red/brown roof
    roofMat.update();
    roof.model.material = roofMat;
    house.addChild(roof);

    // Door
    const door = new pc.Entity("Door");
    door.addComponent("model", { type: "box" });
    door.setLocalScale(0.8, 1.5, 0.1);
    door.setLocalPosition(0, 0.75, 2.55);

    const doorMat = new pc.StandardMaterial();
    doorMat.diffuse = new pc.Color(0.3, 0.2, 0.1);
    doorMat.update();
    door.model.material = doorMat;
    house.addChild(door);

    // Window
    const window1 = new pc.Entity("Window");
    window1.addComponent("model", { type: "box" });
    window1.setLocalScale(0.6, 0.6, 0.1);
    window1.setLocalPosition(-1, 2, 2.55);

    const windowMat = new pc.StandardMaterial();
    windowMat.diffuse = new pc.Color(0.6, 0.7, 0.9);
    windowMat.emissive = new pc.Color(0.8, 0.7, 0.4); // Warm glow
    windowMat.update();
    window1.model.material = windowMat;
    house.addChild(window1);

    house.setPosition(x, 0, z);
    house.setEulerAngles(0, rotation, 0);
    this.app.root.addChild(house);
    this.buildings.push(house);
  }

  createChurch(x, z) {
    const church = new pc.Entity("Church");

    // Base
    const base = new pc.Entity("Base");
    base.addComponent("model", { type: "box" });
    base.setLocalScale(6, 5, 8);
    base.setLocalPosition(0, 2.5, 0);

    const baseMat = new pc.StandardMaterial();
    baseMat.diffuse = new pc.Color(0.6, 0.6, 0.65); // Stone
    baseMat.update();
    base.model.material = baseMat;
    church.addChild(base);

    // Roof
    const roof = new pc.Entity("Roof");
    roof.addComponent("model", { type: "cone" });
    roof.setLocalScale(7, 3, 9);
    roof.setLocalPosition(0, 5.5, 0);

    const roofMat = new pc.StandardMaterial();
    roofMat.diffuse = new pc.Color(0.3, 0.15, 0.1);
    roofMat.update();
    roof.model.material = roofMat;
    church.addChild(roof);

    // Tower
    const tower = new pc.Entity("Tower");
    tower.addComponent("model", { type: "cylinder" });
    tower.setLocalScale(1.2, 4, 1.2);
    tower.setLocalPosition(0, 6, -2);
    tower.model.material = baseMat;
    church.addChild(tower);

    // Spire
    const spire = new pc.Entity("Spire");
    spire.addComponent("model", { type: "cone" });
    spire.setLocalScale(1.5, 2.5, 1.5);
    spire.setLocalPosition(0, 8.5, -2);

    const spireMat = new pc.StandardMaterial();
    spireMat.diffuse = new pc.Color(0.7, 0.65, 0.5); // Gold/bronze
    spireMat.shininess = 30;
    spireMat.update();
    spire.model.material = spireMat;
    church.addChild(spire);

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

      const mat = new pc.StandardMaterial();
      mat.diffuse = new pc.Color(0.3, 0.3, 0.35);
      mat.update();
      stone.model.material = mat;

      this.app.root.addChild(stone);
    }

    // Logs
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

      const mat = new pc.StandardMaterial();
      mat.diffuse = new pc.Color(0.25, 0.15, 0.08);
      mat.update();
      log.model.material = mat;

      this.app.root.addChild(log);
    }

    // Enhanced Particle System for Fire
    this.fireParticles = [];
    for (let i = 0; i < 20; i++) {
      const p = new pc.Entity("FireParticle");
      p.addComponent("model", { type: "plane" });
      p.setLocalScale(0.4, 0.4, 0.4);

      const mat = new pc.StandardMaterial();
      mat.emissive = new pc.Color(1, 0.6 - i * 0.02, 0.1);
      mat.opacity = 0.9;
      mat.blendType = pc.BLEND_ADDITIVE;
      mat.update();
      p.model.material = mat;

      this.app.root.addChild(p);
      this.fireParticles.push({
        entity: p,
        speed: 0.4 + Math.random() * 0.6,
        offset: Math.random() * Math.PI * 2,
        life: Math.random(),
      });
    }

    // Register update for animation
    this.app.on("update", (dt) => this.update(dt));
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

    // Register update for animation
    this.app.on("update", (dt) => this.update(dt));
  }

  createEnvironment() {
    // Trees with more variety
    for (let i = 0; i < 30; i++) {
      const angle = (i / 30) * Math.PI * 2 + (Math.random() - 0.5);
      const radius = 25 + Math.random() * 10;
      const x = Math.cos(angle) * radius;
      const z = Math.sin(angle) * radius;

      const treeHeight = 3 + Math.random() * 2;
      this.createTree(x, z, treeHeight);
    }

    // Bushes
    for (let i = 0; i < 15; i++) {
      const angle = Math.random() * Math.PI * 2;
      const radius = 18 + Math.random() * 8;
      const x = Math.cos(angle) * radius;
      const z = Math.sin(angle) * radius;

      this.createBush(x, z);
    }

    // Rocks/Stones scattered around
    for (let i = 0; i < 20; i++) {
      const angle = Math.random() * Math.PI * 2;
      const radius = 10 + Math.random() * 25;
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
    trunk.setLocalScale(
      0.4 + Math.random() * 0.2,
      height,
      0.4 + Math.random() * 0.2,
    );
    trunk.setLocalPosition(0, height / 2, 0);
    const trunkMat = new pc.StandardMaterial();
    trunkMat.diffuse = new pc.Color(0.2, 0.15, 0.1);
    trunkMat.update();
    trunk.model.material = trunkMat;
    tree.addChild(trunk);

    // Leaves (multiple layers)
    for (let i = 0; i < 3; i++) {
      const leaves = new pc.Entity(`Leaves-${i}`);
      leaves.addComponent("model", { type: "cone" });
      const scale = 3 - i * 0.5 + Math.random() * 0.5;
      leaves.setLocalScale(scale, height * 0.8, scale);
      leaves.setLocalPosition(0, height + i * 0.8, 0);
      leaves.setLocalEulerAngles(0, Math.random() * 360, 0);

      const leavesMat = new pc.StandardMaterial();
      leavesMat.diffuse = new pc.Color(
        0.05 + Math.random() * 0.05,
        0.15 + Math.random() * 0.1,
        0.05,
      );
      leavesMat.update();
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

    const mat = new pc.StandardMaterial();
    mat.diffuse = new pc.Color(0.08, 0.2, 0.08);
    mat.update();
    bush.model.material = mat;

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

    const mat = new pc.StandardMaterial();
    mat.diffuse = new pc.Color(0.35, 0.35, 0.4);
    mat.shininess = 5;
    mat.update();
    rock.model.material = mat;

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
    this.players = players;

    // Clear existing
    this.playerEntities.forEach((entity) => entity.destroy());
    this.playerEntities.clear();
    this.playerLabels.forEach((entity) => entity.destroy());
    this.playerLabels.clear();

    const count = players.length;
    const radius = 8;

    players.forEach((player, index) => {
      const angle = (index / count) * Math.PI * 2;
      const x = Math.cos(angle) * radius;
      const z = Math.sin(angle) * radius;

      const entity = this.createDetailedPlayer(player, x, z, angle);

      this.app.root.addChild(entity);
      this.playerEntities.set(player.id, entity);
    });
  }

  createDetailedPlayer(player, x, z, angle) {
    const entity = new pc.Entity(`Player-${player.id}`);

    // Get role color - in lobby mode use a visible color scheme
    let roleColor;
    if (this.isLobbyMode || !player.rolle) {
      // Lobby mode: use blue for all players so they're visible
      roleColor = new pc.Color(0.3, 0.5, 0.8);
    } else {
      roleColor = this.roleColors[player.rolle] || this.roleColors["default"];
    }

    // Body (more detailed)
    const body = new pc.Entity("Body");
    body.addComponent("model", { type: "capsule" });
    body.setLocalPosition(0, 1, 0);
    body.setLocalScale(0.8, 1.8, 0.8);

    const bodyMat = new pc.StandardMaterial();
    if (player.ist_am_leben) {
      bodyMat.diffuse = roleColor;
      bodyMat.specular = new pc.Color(0.2, 0.2, 0.2);
      bodyMat.shininess = 20;
    } else {
      bodyMat.diffuse = new pc.Color(0.2, 0.2, 0.2); // Dead color
      bodyMat.opacity = 0.4;
      bodyMat.blendType = pc.BLEND_NORMAL;
    }
    bodyMat.update();
    body.model.material = bodyMat;
    entity.addChild(body);

    // Head
    const head = new pc.Entity("Head");
    head.addComponent("model", { type: "sphere" });
    head.setLocalPosition(0, 1.8, 0);
    head.setLocalScale(0.6, 0.6, 0.6);

    const headMat = new pc.StandardMaterial();
    if (player.ist_am_leben) {
      headMat.diffuse = new pc.Color(0.9, 0.8, 0.7); // Skin tone
      headMat.shininess = 15;
    } else {
      headMat.diffuse = new pc.Color(0.3, 0.3, 0.3);
      headMat.opacity = 0.4;
      headMat.blendType = pc.BLEND_NORMAL;
    }
    headMat.update();
    head.model.material = headMat;
    entity.addChild(head);

    // Eyes
    if (player.ist_am_leben) {
      for (let i = 0; i < 2; i++) {
        const eye = new pc.Entity(`Eye-${i}`);
        eye.addComponent("model", { type: "sphere" });
        eye.setLocalPosition(i === 0 ? -0.15 : 0.15, 1.9, 0.25);
        eye.setLocalScale(0.08, 0.08, 0.08);

        const eyeMat = new pc.StandardMaterial();
        eyeMat.diffuse = new pc.Color(0.1, 0.1, 0.1);
        eyeMat.emissive = new pc.Color(0.2, 0.2, 0.3);
        eyeMat.update();
        eye.model.material = eyeMat;
        entity.addChild(eye);
      }
    }

    // Role indicator (glowing sphere above head)
    if (player.rolle && player.ist_am_leben) {
      const indicator = new pc.Entity("RoleIndicator");
      indicator.addComponent("model", { type: "sphere" });
      indicator.setLocalPosition(0, 2.8, 0);
      indicator.setLocalScale(0.25, 0.25, 0.25);

      const indicatorMat = new pc.StandardMaterial();
      indicatorMat.emissive = roleColor;
      indicatorMat.opacity = 0.8;
      indicatorMat.blendType = pc.BLEND_ADDITIVE;
      indicatorMat.update();
      indicator.model.material = indicatorMat;
      entity.addChild(indicator);
    }

    // Name Label (3D text using plane with canvas texture)
    const nameLabel = this.createNameLabel(player.name, player.ist_am_leben);
    nameLabel.setLocalPosition(0, 3.2, 0);
    entity.addChild(nameLabel);
    this.playerLabels.set(player.id, nameLabel);

    // Add collision for picking
    entity.addComponent("collision", {
      type: "box",
      halfExtents: new pc.Vec3(0.6, 1.5, 0.6),
    });

    entity.setPosition(x, 0, z);
    entity.lookAt(0, 0, 0);

    // Store data
    entity.playerData = player;

    return entity;
  }

  createNameLabel(name, isAlive) {
    const label = new pc.Entity("NameLabel");
    label.addComponent("model", { type: "plane" });
    label.setLocalScale(2, 0.5, 1);

    // Create canvas for text
    const canvas = document.createElement("canvas");
    canvas.width = 256;
    canvas.height = 64;
    const ctx = canvas.getContext("2d");

    // Background
    ctx.fillStyle = isAlive ? "rgba(0, 0, 0, 0.7)" : "rgba(0, 0, 0, 0.4)";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Text
    ctx.fillStyle = isAlive ? "#FFFFFF" : "#888888";
    ctx.font = "bold 32px Arial";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(name, canvas.width / 2, canvas.height / 2);

    // Create texture from canvas
    const texture = new pc.Texture(this.app.graphicsDevice, {
      width: canvas.width,
      height: canvas.height,
      format: pc.PIXELFORMAT_R8_G8_B8_A8,
    });

    const pixels = ctx.getImageData(0, 0, canvas.width, canvas.height);
    texture.lock().set(new Uint8Array(pixels.data));
    texture.unlock();

    // Apply to material
    const mat = new pc.StandardMaterial();
    mat.diffuseMap = texture;
    mat.emissive = new pc.Color(0.3, 0.3, 0.3);
    mat.opacity = isAlive ? 1.0 : 0.5;
    mat.blendType = pc.BLEND_NORMAL;
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
      this.app.scene.ambientLight = new pc.Color(0.03, 0.03, 0.08);
      this.app.scene.fogColor = new pc.Color(0.02, 0.02, 0.05);
      this.app.scene.fogDensity = 0.03;
      this.fireLight.enabled = true;

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
    } else {
      // Day settings
      this.light.light.color = new pc.Color(1, 0.95, 0.85); // Warm sunlight
      this.light.light.intensity = 1.2;
      this.fillLight.light.intensity = 0.4;
      this.app.scene.ambientLight = new pc.Color(0.5, 0.5, 0.55);
      this.app.scene.fogColor = new pc.Color(0.7, 0.8, 0.9);
      this.app.scene.fogDensity = 0.005;
      this.fireLight.enabled = false; // Fire less visible during day

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
    }
  }

  resetCamera() {
    this.cameraAngle = this.defaultCameraAngle;
    this.cameraHeight = this.defaultCameraHeight;
    this.cameraRadius = this.defaultCameraRadius;
  }

  setupInput() {
    // Mouse/Touch input for camera and picking
    let isDragging = false;
    let lastMouseX = 0;
    let lastMouseY = 0;

    this.app.mouse.on(pc.EVENT_MOUSEDOWN, (event) => {
      if (event.button === pc.MOUSEBUTTON_LEFT) {
        isDragging = true;
        lastMouseX = event.x;
        lastMouseY = event.y;

        // Picking
        this.pick(event.x, event.y);
      }
    });

    this.app.mouse.on(pc.EVENT_MOUSEUP, () => {
      isDragging = false;
    });

    this.app.mouse.on(pc.EVENT_MOUSEMOVE, (event) => {
      if (isDragging) {
        const dx = event.x - lastMouseX;
        const dy = event.y - lastMouseY;

        this.cameraAngle -= dx * 0.01;
        this.cameraHeight += dy * 0.05;
        this.cameraHeight = pc.math.clamp(this.cameraHeight, 5, 35);

        lastMouseX = event.x;
        lastMouseY = event.y;
      }
    });

    // Mouse wheel for zoom
    this.app.mouse.on(pc.EVENT_MOUSEWHEEL, (event) => {
      // Prevent page scrolling
      event.event.preventDefault();
      this.cameraRadius += event.wheel * 0.5;
      this.cameraRadius = pc.math.clamp(this.cameraRadius, 15, 40);
    });

    // Touch support
    if (this.app.touch) {
      this.app.touch.on(pc.EVENT_TOUCHSTART, (event) => {
        const touch = event.touches[0];
        isDragging = true;
        lastMouseX = touch.x;
        lastMouseY = touch.y;
        this.pick(touch.x, touch.y);
      });

      this.app.touch.on(pc.EVENT_TOUCHEND, () => {
        isDragging = false;
      });

      this.app.touch.on(pc.EVENT_TOUCHMOVE, (event) => {
        if (isDragging && event.touches.length === 1) {
          const touch = event.touches[0];
          const dx = touch.x - lastMouseX;
          const dy = touch.y - lastMouseY;

          this.cameraAngle -= dx * 0.01;
          this.cameraHeight += dy * 0.05;
          this.cameraHeight = pc.math.clamp(this.cameraHeight, 5, 35);

          lastMouseX = touch.x;
          lastMouseY = touch.y;
        }
      });
    }
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

    this.playerEntities.forEach((entity, id) => {
      // Simple bounding sphere check
      const pos = entity.getPosition();
      const radius = 2.0; // Larger radius for easier clicking

      // Ray-Sphere intersection
      const v = new pc.Vec3().sub2(pos, from);
      const dir = new pc.Vec3().sub2(to, from).normalize();
      const t = v.dot(dir);

      if (t > 0) {
        const p = new pc.Vec3().copy(dir).scale(t).add(from);
        const distSq = p.sub(pos).lengthSq();

        if (distSq < radius * radius) {
          const dist = t; // Distance from camera
          if (dist < closestDist) {
            closestDist = dist;
            closestPlayerId = id;
          }
        }
      }
    });

    if (closestPlayerId !== null && this.onPlayerClick) {
      this.onPlayerClick(closestPlayerId);
    }
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

    // Create hint icon above player
    const hint = new pc.Entity("Hint");
    hint.addComponent("model", { type: "sphere" });
    hint.setLocalPosition(0, 4, 0);
    hint.setLocalScale(0.5, 0.5, 0.5);

    const mat = new pc.StandardMaterial();
    mat.emissive =
      type === "danger" ? new pc.Color(1, 0, 0) : new pc.Color(1, 1, 0);
    mat.opacity = 0.8;
    mat.blendType = pc.BLEND_ADDITIVE;
    mat.update();
    hint.model.material = mat;

    entity.addChild(hint);

    // Animate and remove
    let time = 0;
    const updateHint = (dt) => {
      time += dt;
      hint.setLocalPosition(0, 4 + Math.sin(time * 3) * 0.3, 0);
      hint.setLocalScale(
        0.5 + Math.sin(time * 5) * 0.1,
        0.5 + Math.sin(time * 5) * 0.1,
        0.5 + Math.sin(time * 5) * 0.1,
      );

      if (time > 3) {
        this.app.off("update", updateHint);
        hint.destroy();
      }
    };
    this.app.on("update", updateHint);
  }

  update(dt) {
    // Update Camera Position
    const x = Math.sin(this.cameraAngle) * this.cameraRadius;
    const z = Math.cos(this.cameraAngle) * this.cameraRadius;

    // Smooth camera movement
    const currentPos = this.camera.getPosition();
    const targetPos = new pc.Vec3(x, this.cameraHeight, z);
    const newPos = new pc.Vec3().lerp(currentPos, targetPos, dt * 5);

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

    // Animate fireflies (night only)
    if (this.isNight && this.fireflies) {
      this.fireflies.forEach((f) => {
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

    // Make name labels always face camera
    this.playerLabels.forEach((label) => {
      label.lookAt(this.camera.getPosition());
    });
  }
}
