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

    // Create full medieval village (in both lobby and game)
    // Village Buildings
    this.createVillageBuildings();

    // Campfire (center)
    this.createCampfire();

    // Environment (Trees, Stones, Fence)
    this.createEnvironment();

    // Atmospheric effects
    this.createAtmosphericEffects();
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
    const roofLeft = new pc.Entity("RoofLeft");
    roofLeft.addComponent("model", { type: "box" });
    roofLeft.setLocalScale(3, 0.2, 6);
    roofLeft.setLocalPosition(-1.2, 4.3, 0);
    roofLeft.setLocalEulerAngles(0, 0, -30);

    const roofMat = new pc.StandardMaterial();
    roofMat.diffuse = new pc.Color(0.35, 0.18, 0.12); // Dark terracotta
    roofMat.update();
    roofLeft.model.material = roofMat;
    house.addChild(roofLeft);

    const roofRight = new pc.Entity("RoofRight");
    roofRight.addComponent("model", { type: "box" });
    roofRight.setLocalScale(3, 0.2, 6);
    roofRight.setLocalPosition(1.2, 4.3, 0);
    roofRight.setLocalEulerAngles(0, 0, 30);
    roofRight.model.material = roofMat;
    house.addChild(roofRight);

    // Roof peak
    const roofPeak = new pc.Entity("RoofPeak");
    roofPeak.addComponent("model", { type: "box" });
    roofPeak.setLocalScale(0.3, 0.3, 6);
    roofPeak.setLocalPosition(0, 4.8, 0);
    roofPeak.model.material = roofMat;
    house.addChild(roofPeak);

    // Chimney
    const chimney = new pc.Entity("Chimney");
    chimney.addComponent("model", { type: "box" });
    chimney.setLocalScale(0.6, 1.5, 0.6);
    chimney.setLocalPosition(1.5, 5.3, 1);
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

    house.setPosition(x, 0, z);
    house.setEulerAngles(0, rotation, 0);
    this.app.root.addChild(house);
    this.buildings.push(house);
  }

  createChurch(x, z) {
    const church = new pc.Entity("Church");

    // Main stone base (Romanesque style)
    const base = new pc.Entity("Base");
    base.addComponent("model", { type: "box" });
    base.setLocalScale(8, 6, 10);
    base.setLocalPosition(0, 3, 0);

    const stoneMat = new pc.StandardMaterial();
    stoneMat.diffuse = new pc.Color(0.55, 0.55, 0.58); // Light stone
    stoneMat.specular = new pc.Color(0.1, 0.1, 0.1);
    stoneMat.shininess = 5;
    stoneMat.update();
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

    // Gabled roof
    const roofLeft = new pc.Entity("RoofLeft");
    roofLeft.addComponent("model", { type: "box" });
    roofLeft.setLocalScale(6, 0.3, 11);
    roofLeft.setLocalPosition(-2.5, 7, 0);
    roofLeft.setLocalEulerAngles(0, 0, -25);

    const roofMat = new pc.StandardMaterial();
    roofMat.diffuse = new pc.Color(0.28, 0.12, 0.08); // Dark tile
    roofMat.update();
    roofLeft.model.material = roofMat;
    church.addChild(roofLeft);

    const roofRight = new pc.Entity("RoofRight");
    roofRight.addComponent("model", { type: "box" });
    roofRight.setLocalScale(6, 0.3, 11);
    roofRight.setLocalPosition(2.5, 7, 0);
    roofRight.setLocalEulerAngles(0, 0, 25);
    roofRight.model.material = roofMat;
    church.addChild(roofRight);

    // Roof ridge
    const ridge = new pc.Entity("Ridge");
    ridge.addComponent("model", { type: "box" });
    ridge.setLocalScale(0.4, 0.4, 11);
    ridge.setLocalPosition(0, 7.8, 0);
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
    for (let i = 0; i < 4; i++) {
      const window = new pc.Entity(`TowerWindow-${i}`);
      window.addComponent("model", { type: "box" });
      window.setLocalScale(0.6, 1.2, 0.1);
      const angle = (i / 4) * Math.PI * 2;
      const windowX = Math.sin(angle) * 1.3;
      const windowZ = -3.5 + Math.cos(angle) * 1.3;
      window.setLocalPosition(windowX, 9, windowZ);
      window.setLocalEulerAngles(0, i * 90, 0);

      const windowMat = new pc.StandardMaterial();
      windowMat.diffuse = new pc.Color(0.2, 0.2, 0.3);
      windowMat.opacity = 0.6;
      windowMat.blendType = pc.BLEND_NORMAL;
      windowMat.update();
      window.model.material = windowMat;
      church.addChild(window);
    }

    // Tower roof (spire)
    const spire = new pc.Entity("Spire");
    spire.addComponent("model", { type: "cone" });
    spire.setLocalScale(2, 4, 2);
    spire.setLocalPosition(0, 12.5, -3.5);

    const spireMat = new pc.StandardMaterial();
    spireMat.diffuse = new pc.Color(0.25, 0.35, 0.25); // Copper patina
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

    // Create role-specific appearance
    this.addRoleSpecificAppearance(entity, player, roleColor);

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

  addRoleSpecificAppearance(entity, player, roleColor) {
    const rolle = player.rolle;
    const isAlive = player.ist_am_leben;

    // Base body
    const body = new pc.Entity("Body");
    body.addComponent("model", { type: "capsule" });
    body.setLocalPosition(0, 1, 0);
    body.setLocalScale(0.8, 1.8, 0.8);

    const bodyMat = new pc.StandardMaterial();
    if (isAlive) {
      bodyMat.diffuse = roleColor;
      bodyMat.specular = new pc.Color(0.2, 0.2, 0.2);
      bodyMat.shininess = 20;
    } else {
      bodyMat.diffuse = new pc.Color(0.2, 0.2, 0.2);
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
    if (isAlive) {
      headMat.diffuse = new pc.Color(0.9, 0.8, 0.7);
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
    if (isAlive) {
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

    // Add role-specific accessories and features
    if (isAlive && rolle) {
      switch (rolle) {
        case "Werwolf":
          this.addWerwolfFeatures(entity, roleColor);
          break;
        case "Seherin":
          this.addSeherinFeatures(entity, roleColor);
          break;
        case "Hexe":
          this.addHexeFeatures(entity, roleColor);
          break;
        case "Jäger":
          this.addJaegerFeatures(entity, roleColor);
          break;
        case "Amor":
          this.addAmorFeatures(entity, roleColor);
          break;
        case "Heiler":
          this.addHeilerFeatures(entity, roleColor);
          break;
        default:
          // Default role indicator
          this.addDefaultRoleIndicator(entity, roleColor);
          break;
      }
    }
  }

  addWerwolfFeatures(entity, roleColor) {
    // Wolf ears
    for (let i = 0; i < 2; i++) {
      const ear = new pc.Entity(`Ear-${i}`);
      ear.addComponent("model", { type: "cone" });
      ear.setLocalPosition(i === 0 ? -0.35 : 0.35, 2.3, 0);
      ear.setLocalScale(0.15, 0.3, 0.15);
      ear.setLocalEulerAngles(0, 0, i === 0 ? -20 : 20);

      const earMat = new pc.StandardMaterial();
      earMat.diffuse = roleColor;
      earMat.update();
      ear.model.material = earMat;
      entity.addChild(ear);
    }

    // Claws (hands)
    for (let i = 0; i < 2; i++) {
      const claw = new pc.Entity(`Claw-${i}`);
      claw.addComponent("model", { type: "cone" });
      claw.setLocalPosition(i === 0 ? -0.6 : 0.6, 0.5, 0.3);
      claw.setLocalScale(0.15, 0.3, 0.15);
      claw.setLocalEulerAngles(90, 0, i === 0 ? -45 : 45);

      const clawMat = new pc.StandardMaterial();
      clawMat.diffuse = new pc.Color(0.3, 0.3, 0.3);
      clawMat.shininess = 50;
      clawMat.update();
      claw.model.material = clawMat;
      entity.addChild(claw);
    }

    // Glowing red eyes effect
    const eyeGlow = new pc.Entity("EyeGlow");
    eyeGlow.addComponent("light", {
      type: "point",
      color: new pc.Color(1, 0, 0),
      intensity: 0.5,
      range: 2,
    });
    eyeGlow.setLocalPosition(0, 1.9, 0.5);
    entity.addChild(eyeGlow);
  }

  addSeherinFeatures(entity, roleColor) {
    // Crystal ball
    const crystal = new pc.Entity("CrystalBall");
    crystal.addComponent("model", { type: "sphere" });
    crystal.setLocalPosition(0, 0.8, 0.5);
    crystal.setLocalScale(0.3, 0.3, 0.3);

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
      intensity: 1.0,
      range: 3,
    });
    aura.setLocalPosition(0, 1.5, 0);
    entity.addChild(aura);

    // Pointed hat
    const hat = new pc.Entity("Hat");
    hat.addComponent("model", { type: "cone" });
    hat.setLocalPosition(0, 2.6, 0);
    hat.setLocalScale(0.5, 0.8, 0.5);

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
    hat.setLocalPosition(0, 2.7, 0);
    hat.setLocalScale(0.4, 1.0, 0.4);

    const hatMat = new pc.StandardMaterial();
    hatMat.diffuse = new pc.Color(0.1, 0.1, 0.1);
    hatMat.update();
    hat.model.material = hatMat;
    entity.addChild(hat);

    // Hat brim
    const brim = new pc.Entity("HatBrim");
    brim.addComponent("model", { type: "cylinder" });
    brim.setLocalPosition(0, 2.3, 0);
    brim.setLocalScale(0.8, 0.05, 0.8);
    brim.model.material = hatMat;
    entity.addChild(brim);

    // Potion bottles
    for (let i = 0; i < 2; i++) {
      const potion = new pc.Entity(`Potion-${i}`);
      potion.addComponent("model", { type: "cylinder" });
      potion.setLocalPosition(i === 0 ? -0.5 : 0.5, 0.6, 0.3);
      potion.setLocalScale(0.1, 0.3, 0.1);

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
    // Crossbow
    const crossbow = new pc.Entity("Crossbow");
    crossbow.addComponent("model", { type: "box" });
    crossbow.setLocalPosition(0.6, 1.2, 0.3);
    crossbow.setLocalScale(0.8, 0.15, 0.15);
    crossbow.setLocalEulerAngles(0, 0, -45);

    const crossbowMat = new pc.StandardMaterial();
    crossbowMat.diffuse = new pc.Color(0.3, 0.2, 0.1);
    crossbowMat.update();
    crossbow.model.material = crossbowMat;
    entity.addChild(crossbow);

    // Quiver
    const quiver = new pc.Entity("Quiver");
    quiver.addComponent("model", { type: "cylinder" });
    quiver.setLocalPosition(-0.4, 1.5, -0.3);
    quiver.setLocalScale(0.2, 0.5, 0.2);
    quiver.setLocalEulerAngles(30, 0, 0);

    const quiverMat = new pc.StandardMaterial();
    quiverMat.diffuse = new pc.Color(0.4, 0.3, 0.2);
    quiverMat.update();
    quiver.model.material = quiverMat;
    entity.addChild(quiver);

    // Arrows in quiver
    for (let i = 0; i < 3; i++) {
      const arrow = new pc.Entity(`Arrow-${i}`);
      arrow.addComponent("model", { type: "cylinder" });
      arrow.setLocalPosition(-0.4 + i * 0.1, 2.0, -0.3);
      arrow.setLocalScale(0.05, 0.4, 0.05);

      const arrowMat = new pc.StandardMaterial();
      arrowMat.diffuse = new pc.Color(0.6, 0.5, 0.3);
      arrowMat.update();
      arrow.model.material = arrowMat;
      entity.addChild(arrow);
    }
  }

  addAmorFeatures(entity, roleColor) {
    // Cupid wings
    for (let i = 0; i < 2; i++) {
      const wing = new pc.Entity(`Wing-${i}`);
      wing.addComponent("model", { type: "box" });
      wing.setLocalPosition(i === 0 ? -0.5 : 0.5, 1.5, -0.3);
      wing.setLocalScale(0.8, 0.4, 0.1);
      wing.setLocalEulerAngles(0, i === 0 ? 30 : -30, i === 0 ? -20 : 20);

      const wingMat = new pc.StandardMaterial();
      wingMat.diffuse = new pc.Color(1, 0.8, 0.9);
      wingMat.opacity = 0.7;
      wingMat.blendType = pc.BLEND_NORMAL;
      wingMat.update();
      wing.model.material = wingMat;
      entity.addChild(wing);
    }

    // Bow (weapon)
    const bow = new pc.Entity("Bow");
    bow.addComponent("model", { type: "torus" });
    bow.setLocalPosition(0.6, 1.0, 0);
    bow.setLocalScale(0.5, 0.5, 0.1);
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
      intensity: 0.8,
      range: 3,
    });
    heart.setLocalPosition(0, 2.0, 0);
    entity.addChild(heart);
  }

  addHeilerFeatures(entity, roleColor) {
    // Medical cross
    const cross1 = new pc.Entity("Cross1");
    cross1.addComponent("model", { type: "box" });
    cross1.setLocalPosition(0, 2.5, 0.4);
    cross1.setLocalScale(0.1, 0.4, 0.1);

    const crossMat = new pc.StandardMaterial();
    crossMat.diffuse = new pc.Color(1, 1, 1);
    crossMat.emissive = new pc.Color(0.5, 0.5, 0);
    crossMat.update();
    cross1.model.material = crossMat;
    entity.addChild(cross1);

    const cross2 = new pc.Entity("Cross2");
    cross2.addComponent("model", { type: "box" });
    cross2.setLocalPosition(0, 2.5, 0.4);
    cross2.setLocalScale(0.3, 0.1, 0.1);
    cross2.model.material = crossMat;
    entity.addChild(cross2);

    // Healing aura
    const healingAura = new pc.Entity("HealingAura");
    healingAura.addComponent("light", {
      type: "point",
      color: new pc.Color(0.9, 0.9, 0.2),
      intensity: 1.0,
      range: 3,
    });
    healingAura.setLocalPosition(0, 1.5, 0);
    entity.addChild(healingAura);

    // Staff
    const staff = new pc.Entity("Staff");
    staff.addComponent("model", { type: "cylinder" });
    staff.setLocalPosition(-0.6, 1.5, 0);
    staff.setLocalScale(0.08, 2.0, 0.08);
    staff.setLocalEulerAngles(0, 0, -15);

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
