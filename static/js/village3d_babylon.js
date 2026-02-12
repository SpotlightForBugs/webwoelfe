/**
 * Village3DBabylon - Babylon.js renderer for "Werwölfe von Düsterwald"
 *
 * Loads Babylon.js from CDN, renders a dark-forest village scene with
 * GLB models from Kenney Fantasy Town & Graveyard kits, and provides
 * the identical public API consumed by spiel.html / game.js.
 *
 * @module village3d_babylon
 */

// ---------------------------------------------------------------------------
// CDN loader – ensures BABYLON, BABYLON.GUI, and BABYLON loaders are present
// ---------------------------------------------------------------------------
const BABYLON_CDN = 'https://cdn.jsdelivr.net/npm/babylonjs@7.37.2/babylon.js';
const LOADERS_CDN = 'https://cdn.jsdelivr.net/npm/babylonjs-loaders@7.37.2/babylonjs.loaders.min.js';
const GUI_CDN     = 'https://cdn.jsdelivr.net/npm/babylonjs-gui@7.37.2/babylon.gui.min.js';

function loadScript(src) {
  return new Promise((resolve, reject) => {
    if (document.querySelector(`script[src="${src}"]`)) { resolve(); return; }
    const s = document.createElement('script');
    s.src = src;
    s.onload = resolve;
    s.onerror = reject;
    document.head.appendChild(s);
  });
}

async function ensureBabylon() {
  if (typeof BABYLON === 'undefined') await loadScript(BABYLON_CDN);
  if (typeof BABYLON.SceneLoader === 'undefined' || !BABYLON.SceneLoader._registeredPlugins?.['.glb']) {
    await loadScript(LOADERS_CDN);
  }
  if (typeof BABYLON.GUI === 'undefined') await loadScript(GUI_CDN);
}

// ---------------------------------------------------------------------------
// Utility helpers
// ---------------------------------------------------------------------------
function hexToColor3(hex) {
  if (!hex || !hex.startsWith('#')) return new BABYLON.Color3(0.5, 0.5, 0.5);
  const r = parseInt(hex.slice(1, 3), 16) / 255;
  const g = parseInt(hex.slice(3, 5), 16) / 255;
  const b = parseInt(hex.slice(5, 7), 16) / 255;
  return new BABYLON.Color3(r, g, b);
}

function hexToColor4(hex, a = 1) {
  const c = hexToColor3(hex);
  return new BABYLON.Color4(c.r, c.g, c.b, a);
}

function lerpColor3(a, b, t) {
  return new BABYLON.Color3(
    a.r + (b.r - a.r) * t,
    a.g + (b.g - a.g) * t,
    a.b + (b.b - a.b) * t
  );
}

function lerpNumber(a, b, t) { return a + (b - a) * t; }

function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

// Role → color map (fallback; real colors fetched from /api/roles)
const DEFAULT_ROLE_COLORS = {
  'werwolf': '#950706', 'seherin': '#4a90d9', 'hexe': '#8b5cf6',
  'jaeger': '#16a34a', 'amor': '#ec4899', 'dorfbewohner': '#6b7280',
  'erzaehler': '#d4a574',
};

// Character model pool (a–r = 18 models)
const CHAR_LETTERS = 'abcdefghijklmnopqr'.split('');

// House blueprint definitions (which wall/roof GLBs to combine)
const HOUSE_BLUEPRINTS = [
  { walls: ['wall.glb','wall-window-shutters.glb','wall-doorway-round.glb','wall-window-small.glb'],
    roof: 'roof-gable.glb', chimney: true },
  { walls: ['wall-wood.glb','wall-wood-window-round.glb','wall-wood-door.glb','wall-wood.glb'],
    roof: 'roof-high-gable.glb', chimney: false },
  { walls: ['wall.glb','wall-window-glass.glb','wall-doorway-square.glb','wall-window-stone.glb'],
    roof: 'roof.glb', chimney: true },
  { walls: ['wall-wood.glb','wall-wood.glb','wall-wood-door.glb','wall-wood-window-round.glb'],
    roof: 'roof-point.glb', chimney: false },
  { walls: ['wall.glb','wall-window-shutters.glb','wall-doorway-round.glb','wall.glb'],
    roof: 'roof-gable-detail.glb', chimney: true },
];

// ---------------------------------------------------------------------------
// Main class
// ---------------------------------------------------------------------------
export class Village3DBabylon {
  /**
   * @param {string} containerId - DOM element ID to render into
   * @param {string} raumCode - Room code (for potential API calls)
   * @param {object} [options]
   */
  constructor(containerId, raumCode, options = {}) {
    this._containerId = containerId;
    this._raumCode = raumCode;
    this._options = options;
    this._lobbyMode = !!options.lobbyMode;
    this.onPlayerClick = options.onPlayerClick || null;
    this._startView = options.startView || 'top-down';
    this._firstPersonPlayerId = options.firstPersonPlayerId || null;
    this._firstPersonHeight = options.firstPersonHeight || 2.0;

    // State
    this._players = [];
    this._playerNodes = new Map();   // id → { root, character, label, pedestal, ... }
    this._isNight = false;
    this._timeTransition = 0;        // 0 = day, 1 = night
    this._timeTarget = 0;            // 0 = day, 1 = night
    this._viewMode = 'top-down';     // 'top-down' | 'first-person'
    this._selectedPlayerId = null;
    this._victimPlayerId = null;
    this._sleepingPlayers = new Set();
    this._destroyed = false;

    // Babylon references (set during init)
    this._engine = null;
    this._scene = null;
    this._arcCamera = null;
    this._fpCamera = null;
    this._activeCamera = null;
    this._advancedTexture = null;     // GUI AdvancedDynamicTexture

    // Lighting refs
    this._dirLight = null;
    this._hemiLight = null;
    this._campfireLight = null;
    this._lanternLights = [];

    // Sky/environment
    this._skybox = null;
    this._moonBillboard = null;
    this._sunBillboard = null;

    // Particles
    this._fireflySystem = null;
    this._campfireFlame = null;
    this._campfireSmoke = null;
    this._campfireEmbers = null;
    this._starSystem = null;

    // Caches
    this._glbCache = new Map();       // path → Promise<result>
    this._houseBlueprintNodes = [];   // pre-assembled house meshes
    this._roleColors = { ...DEFAULT_ROLE_COLORS };

    // HUD state (delegates to HTML overlay in spiel.html)
    this._hudVisible = false;
    this._leftSidebarVisible = true;
    this._rightSidebarVisible = true;

    // Shadow generator
    this._shadowGen = null;

    // Effect cleanup timers
    this._effectTimers = [];

    // Kick off init
    this._ready = this._init();
  }

  // =========================================================================
  // Initialization
  // =========================================================================

  async _init() {
    await ensureBabylon();

    const container = document.getElementById(this._containerId);
    if (!container) { console.error('[Village3D] Container not found:', this._containerId); return; }

    // Create canvas
    const canvas = document.createElement('canvas');
    canvas.style.width = '100%';
    canvas.style.height = '100%';
    canvas.style.outline = 'none';
    canvas.style.display = 'block';
    canvas.id = this._containerId + '-canvas';
    container.appendChild(canvas);
    this._canvas = canvas;

    // Engine
    this._engine = new BABYLON.Engine(canvas, true, {
      preserveDrawingBuffer: true,
      stencil: true,
      antialias: true,
    });
    this._engine.setHardwareScalingLevel(1 / Math.min(window.devicePixelRatio, 2));

    // Scene
    const scene = new BABYLON.Scene(this._engine);
    this._scene = scene;
    scene.clearColor = new BABYLON.Color4(0.25, 0.25, 0.3, 1);
    scene.ambientColor = new BABYLON.Color3(0.3, 0.3, 0.35);
    scene.fogMode = BABYLON.Scene.FOGMODE_EXP2;
    scene.fogDensity = 0.015;
    scene.fogColor = new BABYLON.Color3(0.45, 0.45, 0.5);
    scene.collisionsEnabled = false;

    // Optimisations
    scene.skipPointerMovePicking = false; // need for hover
    scene.autoClear = true;
    scene.autoClearDepthAndStencil = true;

    // Cameras
    this._createCameras(canvas);

    // Lights
    this._createLights();

    // Environment
    this._createGround();
    this._createSkybox();
    this._createCelestialBodies();
    this._createCampfire();
    this._createVillageDecorations();
    this._createGraveyardArea();
    this._createForestRing();
    this._createLanterns();
    this._createFireflies();
    this._createStars();

    // GUI overlay texture
    this._advancedTexture = BABYLON.GUI.AdvancedDynamicTexture.CreateFullscreenUI('UI', true, scene);

    // Input
    this._setupPicking();

    // Render loop
    this._engine.runRenderLoop(() => {
      if (this._destroyed) return;
      this._updateTransitions();
      this._scene.render();
    });

    // Resize
    this._resizeHandler = () => this._engine.resize();
    window.addEventListener('resize', this._resizeHandler);

    // WebGL context loss
    canvas.addEventListener('webglcontextlost', (e) => {
      e.preventDefault();
      console.warn('[Village3D] WebGL context lost');
      this._engine.stopRenderLoop();
    });
    canvas.addEventListener('webglcontextrestored', () => {
      console.info('[Village3D] WebGL context restored');
      this._engine.runRenderLoop(() => {
        if (this._destroyed) return;
        this._updateTransitions();
        this._scene.render();
      });
    });

    // Load role colors from API
    this._loadRoleColors();

    // Set initial time
    this.setTimeOfDay(this._isNight);

    // Expose materialCache-like for VillageIntegration compatibility
    this.materialCache = new Map();
    this.app = null; // no PlayCanvas app

    console.info('[Village3D-Babylon] Initialized');
  }

  // =========================================================================
  // Cameras
  // =========================================================================

  _createCameras(canvas) {
    // ArcRotateCamera for top-down/orbit
    const arc = new BABYLON.ArcRotateCamera('arcCam',
      -Math.PI / 2, Math.PI / 3.5, 30,
      new BABYLON.Vector3(0, 1, 0), this._scene);
    arc.lowerRadiusLimit = 8;
    arc.upperRadiusLimit = 60;
    arc.lowerBetaLimit = 0.2;
    arc.upperBetaLimit = Math.PI / 2.2;
    arc.wheelDeltaPercentage = 0.02;
    arc.panningSensibility = 80;
    arc.pinchDeltaPercentage = 0.004;
    arc.angularSensibilityX = 500;
    arc.angularSensibilityY = 500;
    arc.inertia = 0.85;
    arc.attachControl(canvas, true);
    this._arcCamera = arc;

    // UniversalCamera for first-person
    const fp = new BABYLON.UniversalCamera('fpCam',
      new BABYLON.Vector3(0, this._firstPersonHeight, 0), this._scene);
    fp.speed = 0.3;
    fp.angularSensibility = 2000;
    fp.minZ = 0.1;
    this._fpCamera = fp;

    // Set default
    if (this._startView === 'first-person') {
      this._scene.activeCamera = fp;
      fp.attachControl(canvas, true);
      this._viewMode = 'first-person';
      this._activeCamera = fp;
    } else {
      this._scene.activeCamera = arc;
      this._viewMode = 'top-down';
      this._activeCamera = arc;
    }
  }

  // =========================================================================
  // Lights
  // =========================================================================

  _createLights() {
    const scene = this._scene;

    // Hemisphere ambient
    const hemi = new BABYLON.HemisphericLight('hemi',
      new BABYLON.Vector3(0, 1, 0), scene);
    hemi.intensity = 0.5;
    hemi.diffuse = new BABYLON.Color3(0.5, 0.5, 0.55);
    hemi.groundColor = new BABYLON.Color3(0.15, 0.15, 0.12);
    this._hemiLight = hemi;

    // Directional (sun/moon)
    const dir = new BABYLON.DirectionalLight('dir',
      new BABYLON.Vector3(-0.5, -1, 0.3).normalize(), scene);
    dir.position = new BABYLON.Vector3(10, 20, -10);
    dir.intensity = 0.8;
    dir.diffuse = new BABYLON.Color3(0.8, 0.75, 0.65);
    this._dirLight = dir;

    // Shadow generator (basic, can be toggled off)
    try {
      const sg = new BABYLON.ShadowGenerator(1024, dir);
      sg.useBlurExponentialShadowMap = true;
      sg.blurKernel = 16;
      sg.darkness = 0.4;
      this._shadowGen = sg;
    } catch (e) {
      console.warn('[Village3D] Shadows not supported:', e);
    }

    // Campfire point light (warm)
    const fire = new BABYLON.PointLight('fireLight',
      new BABYLON.Vector3(0, 1.2, 0), scene);
    fire.diffuse = new BABYLON.Color3(1.0, 0.65, 0.25);
    fire.intensity = 1.0;
    fire.range = 18;
    this._campfireLight = fire;
  }

  // =========================================================================
  // Ground
  // =========================================================================

  _createGround() {
    const scene = this._scene;

    // Main ground disc
    const ground = BABYLON.MeshBuilder.CreateDisc('ground', { radius: 40, tessellation: 64 }, scene);
    ground.rotation.x = Math.PI / 2;
    ground.receiveShadows = true;

    const gMat = new BABYLON.StandardMaterial('groundMat', scene);
    const gSize = 1024;
    const gTex = new BABYLON.DynamicTexture('groundTex', gSize, scene, true);
    const ctx = gTex.getContext();
    const half = gSize / 2;

    // Paint ground with smooth radial zones using gradients
    // 1) Base: dark earthy green everywhere
    ctx.fillStyle = '#2a3520';
    ctx.fillRect(0, 0, gSize, gSize);

    // 2) Radial gradient: cobblestone center fading into grass
    const centerGrad = ctx.createRadialGradient(half, half, 0, half, half, half * 0.45);
    centerGrad.addColorStop(0, 'rgba(120, 110, 95, 0.9)');   // warm stone center
    centerGrad.addColorStop(0.5, 'rgba(95, 85, 70, 0.7)');   // packed earth
    centerGrad.addColorStop(0.8, 'rgba(60, 55, 40, 0.4)');   // transition
    centerGrad.addColorStop(1, 'rgba(42, 53, 32, 0)');        // grass (transparent)
    ctx.fillStyle = centerGrad;
    ctx.fillRect(0, 0, gSize, gSize);

    // 3) Dirt path ring where houses sit
    ctx.lineWidth = 28;
    ctx.strokeStyle = 'rgba(85, 75, 60, 0.5)';
    ctx.beginPath();
    ctx.arc(half, half, half * 0.48, 0, Math.PI * 2);
    ctx.stroke();

    // 4) Subtle grass variation - soft noise, not rectangles
    for (let i = 0; i < 3000; i++) {
      const x = Math.random() * gSize;
      const y = Math.random() * gSize;
      const dx = x - half, dy = y - half;
      const dist = Math.sqrt(dx * dx + dy * dy) / half;
      if (dist > 0.35) {
        // Grass tufts in outer area only - small circles, not rectangles
        const brightness = 35 + Math.random() * 25;
        const radius = 2 + Math.random() * 4;
        ctx.fillStyle = `rgba(${brightness - 5}, ${brightness + 15}, ${brightness - 10}, 0.3)`;
        ctx.beginPath();
        ctx.arc(x, y, radius, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    // 5) Cobblestone detail in center - subtle circles not hard rectangles
    for (let i = 0; i < 800; i++) {
      const angle = Math.random() * Math.PI * 2;
      const r = Math.random() * half * 0.3;
      const x = half + Math.cos(angle) * r;
      const y = half + Math.sin(angle) * r;
      const v = 90 + Math.random() * 40;
      const size = 2 + Math.random() * 3;
      ctx.fillStyle = `rgba(${v}, ${v - 8}, ${v - 18}, 0.25)`;
      ctx.beginPath();
      ctx.arc(x, y, size, 0, Math.PI * 2);
      ctx.fill();
    }
    gTex.update();
    gMat.diffuseTexture = gTex;
    gMat.specularColor = BABYLON.Color3.Black();
    ground.material = gMat;
    this._ground = ground;

    // Village square (flat disc, slightly raised)
    const square = BABYLON.MeshBuilder.CreateDisc('square', { radius: 5, tessellation: 32 }, scene);
    square.rotation.x = Math.PI / 2;
    square.position.y = 0.01;
    const sqMat = new BABYLON.StandardMaterial('squareMat', scene);
    sqMat.diffuseColor = new BABYLON.Color3(0.35, 0.32, 0.28);
    sqMat.specularColor = BABYLON.Color3.Black();
    square.material = sqMat;
    square.receiveShadows = true;
  }

  // =========================================================================
  // Skybox
  // =========================================================================

  _createSkybox() {
    const scene = this._scene;
    const skybox = BABYLON.MeshBuilder.CreateBox('skybox', { size: 200 }, scene);
    const skyMat = new BABYLON.StandardMaterial('skyMat', scene);
    skyMat.backFaceCulling = false;
    skyMat.disableLighting = true;
    skyMat.diffuseColor = BABYLON.Color3.Black();
    skyMat.specularColor = BABYLON.Color3.Black();
    skyMat.emissiveColor = new BABYLON.Color3(0.25, 0.25, 0.3);
    skybox.material = skyMat;
    skybox.infiniteDistance = true;
    skybox.renderingGroupId = 0;
    this._skybox = skybox;
    this._skyMat = skyMat;
  }

  // =========================================================================
  // Celestial bodies
  // =========================================================================

  _createCelestialBodies() {
    const scene = this._scene;

    // Moon billboard
    const moon = BABYLON.MeshBuilder.CreatePlane('moon', { size: 5 }, scene);
    moon.position = new BABYLON.Vector3(-20, 30, -25);
    moon.billboardMode = BABYLON.Mesh.BILLBOARDMODE_ALL;
    const moonMat = new BABYLON.StandardMaterial('moonMat', scene);
    moonMat.disableLighting = true;
    moonMat.emissiveColor = new BABYLON.Color3(0.85, 0.88, 0.95);
    moonMat.alpha = 0.9;
    moonMat.backFaceCulling = false;

    // Procedural moon texture
    const moonTex = new BABYLON.DynamicTexture('moonTex', 128, scene, false);
    const mctx = moonTex.getContext();
    mctx.clearRect(0, 0, 128, 128);
    const grad = mctx.createRadialGradient(64, 64, 0, 64, 64, 60);
    grad.addColorStop(0, 'rgba(220,225,235,1)');
    grad.addColorStop(0.6, 'rgba(180,185,200,0.9)');
    grad.addColorStop(0.85, 'rgba(120,125,145,0.4)');
    grad.addColorStop(1, 'rgba(0,0,0,0)');
    mctx.fillStyle = grad;
    mctx.fillRect(0, 0, 128, 128);
    // Craters
    for (let i = 0; i < 5; i++) {
      const cx = 40 + Math.random() * 48;
      const cy = 40 + Math.random() * 48;
      const cr = 3 + Math.random() * 8;
      mctx.beginPath();
      mctx.arc(cx, cy, cr, 0, Math.PI * 2);
      mctx.fillStyle = 'rgba(150,155,170,0.3)';
      mctx.fill();
    }
    moonTex.update();
    moonMat.diffuseTexture = moonTex;
    moonMat.opacityTexture = moonTex;
    moon.material = moonMat;
    this._moonBillboard = moon;

    // Sun billboard (pale, overcast)
    const sun = BABYLON.MeshBuilder.CreatePlane('sun', { size: 6 }, scene);
    sun.position = new BABYLON.Vector3(20, 25, 20);
    sun.billboardMode = BABYLON.Mesh.BILLBOARDMODE_ALL;
    const sunMat = new BABYLON.StandardMaterial('sunMat', scene);
    sunMat.disableLighting = true;
    sunMat.emissiveColor = new BABYLON.Color3(0.9, 0.85, 0.7);
    sunMat.alpha = 0;
    sunMat.backFaceCulling = false;

    const sunTex = new BABYLON.DynamicTexture('sunTex', 128, scene, false);
    const sctx = sunTex.getContext();
    sctx.clearRect(0, 0, 128, 128);
    const sgrad = sctx.createRadialGradient(64, 64, 0, 64, 64, 60);
    sgrad.addColorStop(0, 'rgba(255,245,220,1)');
    sgrad.addColorStop(0.3, 'rgba(255,235,190,0.7)');
    sgrad.addColorStop(0.7, 'rgba(200,190,160,0.2)');
    sgrad.addColorStop(1, 'rgba(0,0,0,0)');
    sctx.fillStyle = sgrad;
    sctx.fillRect(0, 0, 128, 128);
    sunTex.update();
    sunMat.diffuseTexture = sunTex;
    sunMat.opacityTexture = sunTex;
    sun.material = sunMat;
    this._sunBillboard = sun;
    this._sunMat = sunMat;
  }

  // =========================================================================
  // Campfire
  // =========================================================================

  _createCampfire() {
    const scene = this._scene;

    // Stone ring
    for (let i = 0; i < 10; i++) {
      const ang = (i / 10) * Math.PI * 2;
      const stone = BABYLON.MeshBuilder.CreateBox('fStone' + i, { width: 0.4, height: 0.3, depth: 0.35 }, scene);
      stone.position = new BABYLON.Vector3(Math.cos(ang) * 0.8, 0.15, Math.sin(ang) * 0.8);
      stone.rotation.y = ang + Math.random() * 0.5;
      const sMat = new BABYLON.StandardMaterial('fStoneMat' + i, scene);
      sMat.diffuseColor = new BABYLON.Color3(0.25 + Math.random() * 0.1, 0.22 + Math.random() * 0.08, 0.18);
      sMat.specularColor = BABYLON.Color3.Black();
      stone.material = sMat;
      if (this._shadowGen) this._shadowGen.addShadowCaster(stone);
    }

    // Logs
    for (let i = 0; i < 4; i++) {
      const ang = (i / 4) * Math.PI * 2 + 0.3;
      const log = BABYLON.MeshBuilder.CreateCylinder('fLog' + i, { diameter: 0.18, height: 1.0 }, scene);
      log.position = new BABYLON.Vector3(Math.cos(ang) * 0.3, 0.2, Math.sin(ang) * 0.3);
      log.rotation.z = Math.PI / 2 - 0.2;
      log.rotation.y = ang;
      const lMat = new BABYLON.StandardMaterial('fLogMat' + i, scene);
      lMat.diffuseColor = new BABYLON.Color3(0.3, 0.18, 0.08);
      lMat.specularColor = BABYLON.Color3.Black();
      log.material = lMat;
    }

    // Fire particle system
    const fireEmitter = new BABYLON.Vector3(0, 0.4, 0);
    const flame = new BABYLON.ParticleSystem('flame', 120, scene);
    flame.emitter = fireEmitter;
    flame.minEmitBox = new BABYLON.Vector3(-0.2, 0, -0.2);
    flame.maxEmitBox = new BABYLON.Vector3(0.2, 0, 0.2);
    flame.color1 = new BABYLON.Color4(1, 0.6, 0.1, 1);
    flame.color2 = new BABYLON.Color4(1, 0.3, 0.05, 1);
    flame.colorDead = new BABYLON.Color4(0.3, 0.05, 0, 0);
    flame.minSize = 0.15;
    flame.maxSize = 0.5;
    flame.minLifeTime = 0.3;
    flame.maxLifeTime = 0.8;
    flame.emitRate = 80;
    flame.direction1 = new BABYLON.Vector3(-0.2, 1.5, -0.2);
    flame.direction2 = new BABYLON.Vector3(0.2, 2.5, 0.2);
    flame.gravity = new BABYLON.Vector3(0, 0, 0);
    flame.minEmitPower = 0.5;
    flame.maxEmitPower = 1.5;
    flame.updateSpeed = 0.02;
    flame.blendMode = BABYLON.ParticleSystem.BLENDMODE_ADD;
    flame.start();
    this._campfireFlame = flame;

    // Smoke
    const smoke = new BABYLON.ParticleSystem('smoke', 40, scene);
    smoke.emitter = new BABYLON.Vector3(0, 1.0, 0);
    smoke.minEmitBox = new BABYLON.Vector3(-0.15, 0, -0.15);
    smoke.maxEmitBox = new BABYLON.Vector3(0.15, 0, 0.15);
    smoke.color1 = new BABYLON.Color4(0.3, 0.3, 0.35, 0.15);
    smoke.color2 = new BABYLON.Color4(0.2, 0.2, 0.22, 0.08);
    smoke.colorDead = new BABYLON.Color4(0.1, 0.1, 0.1, 0);
    smoke.minSize = 0.5;
    smoke.maxSize = 1.5;
    smoke.minLifeTime = 1.5;
    smoke.maxLifeTime = 3.0;
    smoke.emitRate = 12;
    smoke.direction1 = new BABYLON.Vector3(-0.3, 2, -0.3);
    smoke.direction2 = new BABYLON.Vector3(0.3, 4, 0.3);
    smoke.gravity = new BABYLON.Vector3(0, 0.2, 0);
    smoke.minEmitPower = 0.3;
    smoke.maxEmitPower = 0.8;
    smoke.updateSpeed = 0.015;
    smoke.blendMode = BABYLON.ParticleSystem.BLENDMODE_STANDARD;
    smoke.start();
    this._campfireSmoke = smoke;

    // Embers
    const embers = new BABYLON.ParticleSystem('embers', 30, scene);
    embers.emitter = fireEmitter;
    embers.minEmitBox = new BABYLON.Vector3(-0.3, 0, -0.3);
    embers.maxEmitBox = new BABYLON.Vector3(0.3, 0, 0.3);
    embers.color1 = new BABYLON.Color4(1, 0.5, 0.1, 1);
    embers.color2 = new BABYLON.Color4(1, 0.3, 0, 0.8);
    embers.colorDead = new BABYLON.Color4(0.2, 0.05, 0, 0);
    embers.minSize = 0.02;
    embers.maxSize = 0.06;
    embers.minLifeTime = 1.0;
    embers.maxLifeTime = 3.0;
    embers.emitRate = 15;
    embers.direction1 = new BABYLON.Vector3(-0.8, 2, -0.8);
    embers.direction2 = new BABYLON.Vector3(0.8, 5, 0.8);
    embers.gravity = new BABYLON.Vector3(0, -0.1, 0);
    embers.minEmitPower = 0.8;
    embers.maxEmitPower = 2.0;
    embers.updateSpeed = 0.01;
    embers.blendMode = BABYLON.ParticleSystem.BLENDMODE_ADD;
    embers.start();
    this._campfireEmbers = embers;
  }

  // =========================================================================
  // Village decorations (well, benches, barrels)
  // =========================================================================

  _createVillageDecorations() {
    const scene = this._scene;

    // Well at center offset
    this._loadGLB('/static/models/village/fountain-center.glb').then(result => {
      if (result && result.meshes) {
        const root = result.meshes[0];
        root.position = new BABYLON.Vector3(2.5, 0, -1.5);
        root.scaling = new BABYLON.Vector3(1.2, 1.2, 1.2);
      }
    }).catch(() => {
      // Fallback: procedural well
      const well = BABYLON.MeshBuilder.CreateCylinder('well', { diameter: 1.2, height: 0.8, tessellation: 12 }, scene);
      well.position = new BABYLON.Vector3(2.5, 0.4, -1.5);
      const wMat = new BABYLON.StandardMaterial('wellMat', scene);
      wMat.diffuseColor = new BABYLON.Color3(0.35, 0.3, 0.25);
      wMat.specularColor = BABYLON.Color3.Black();
      well.material = wMat;
    });

    // Benches
    for (let i = 0; i < 3; i++) {
      const ang = (i / 3) * Math.PI * 2 + 0.5;
      const bench = BABYLON.MeshBuilder.CreateBox('bench' + i, { width: 1.2, height: 0.35, depth: 0.4 }, scene);
      bench.position = new BABYLON.Vector3(Math.cos(ang) * 3.5, 0.17, Math.sin(ang) * 3.5);
      bench.rotation.y = ang + Math.PI / 2;
      const bMat = new BABYLON.StandardMaterial('benchMat' + i, scene);
      bMat.diffuseColor = new BABYLON.Color3(0.35, 0.22, 0.1);
      bMat.specularColor = BABYLON.Color3.Black();
      bench.material = bMat;
    }
  }

  // =========================================================================
  // Graveyard area
  // =========================================================================

  _createGraveyardArea() {
    const scene = this._scene;
    const gx = -18, gz = 15;

    // Iron fence around graveyard
    const fencePositions = [
      { x: gx - 5, z: gz - 5, ry: 0 },
      { x: gx - 5, z: gz, ry: 0 },
      { x: gx - 5, z: gz + 5, ry: 0 },
      { x: gx + 5, z: gz - 5, ry: 0 },
      { x: gx + 5, z: gz, ry: 0 },
      { x: gx + 5, z: gz + 5, ry: 0 },
      { x: gx - 3, z: gz - 5, ry: Math.PI / 2 },
      { x: gx, z: gz - 5, ry: Math.PI / 2 },
      { x: gx + 3, z: gz - 5, ry: Math.PI / 2 },
      { x: gx - 3, z: gz + 5, ry: Math.PI / 2 },
      { x: gx + 3, z: gz + 5, ry: Math.PI / 2 },
    ];
    for (const fp of fencePositions) {
      this._loadGLB('/static/models/graveyard/iron-fence.glb').then(r => {
        if (!r) return;
        const root = r.meshes[0];
        root.position = new BABYLON.Vector3(fp.x, 0, fp.z);
        root.rotation.y = fp.ry;
      }).catch(() => {});
    }

    // Gravestones
    const stoneModels = ['gravestone-cross.glb', 'gravestone-round.glb', 'gravestone-wide.glb',
                          'gravestone-broken.glb', 'gravestone-decorative.glb'];
    for (let i = 0; i < 8; i++) {
      const sx = gx - 3 + (i % 4) * 2 + (Math.random() - 0.5) * 0.5;
      const sz = gz - 2 + Math.floor(i / 4) * 3 + (Math.random() - 0.5) * 0.5;
      const model = stoneModels[i % stoneModels.length];
      this._loadGLB(`/static/models/graveyard/${model}`).then(r => {
        if (!r) return;
        r.meshes[0].position = new BABYLON.Vector3(sx, 0, sz);
        r.meshes[0].rotation.y = Math.random() * 0.3 - 0.15;
      }).catch(() => {
        // Fallback procedural gravestone
        const gs = BABYLON.MeshBuilder.CreateBox('grave' + i, { width: 0.4, height: 0.8, depth: 0.15 }, scene);
        gs.position = new BABYLON.Vector3(sx, 0.4, sz);
        gs.rotation.y = Math.random() * 0.3;
        const gm = new BABYLON.StandardMaterial('graveMat' + i, scene);
        gm.diffuseColor = new BABYLON.Color3(0.35, 0.35, 0.38);
        gm.specularColor = BABYLON.Color3.Black();
        gs.material = gm;
      });
    }

    // Crypt
    this._loadGLB('/static/models/graveyard/crypt.glb').then(r => {
      if (!r) return;
      r.meshes[0].position = new BABYLON.Vector3(gx + 1, 0, gz + 3);
      r.meshes[0].scaling = new BABYLON.Vector3(1.3, 1.3, 1.3);
    }).catch(() => {
      const crypt = BABYLON.MeshBuilder.CreateBox('crypt', { width: 3, height: 2.5, depth: 2 }, scene);
      crypt.position = new BABYLON.Vector3(gx + 1, 1.25, gz + 3);
      const cm = new BABYLON.StandardMaterial('cryptMat', scene);
      cm.diffuseColor = new BABYLON.Color3(0.3, 0.28, 0.3);
      cm.specularColor = BABYLON.Color3.Black();
      crypt.material = cm;
    });
  }

  // =========================================================================
  // Forest ring (outer trees & rocks)
  // =========================================================================

  _createForestRing() {
    const scene = this._scene;
    const treeModels = ['tree.glb', 'tree-crooked.glb', 'tree-high-crooked.glb'];
    const pineModels = ['pine.glb', 'pine-crooked.glb', 'pine-fall.glb'];

    // Dense ring of trees
    for (let i = 0; i < 50; i++) {
      const ang = (i / 50) * Math.PI * 2 + Math.random() * 0.1;
      const rad = 22 + Math.random() * 14;
      const tx = Math.cos(ang) * rad;
      const tz = Math.sin(ang) * rad;

      const isPine = Math.random() > 0.5;
      const models = isPine ? pineModels : treeModels;
      const modelPath = isPine
        ? `/static/models/graveyard/${models[Math.floor(Math.random() * models.length)]}`
        : `/static/models/village/${models[Math.floor(Math.random() * models.length)]}`;

      this._loadGLB(modelPath).then(r => {
        if (!r) return;
        const root = r.meshes[0];
        root.position = new BABYLON.Vector3(tx, 0, tz);
        const s = 0.8 + Math.random() * 0.6;
        root.scaling = new BABYLON.Vector3(s, s, s);
        root.rotation.y = Math.random() * Math.PI * 2;
        if (this._shadowGen) this._shadowGen.addShadowCaster(root);
      }).catch(() => {
        // Fallback procedural tree
        this._createProceduralTree(tx, tz, 1.0 + Math.random() * 1.5);
      });
    }

    // Scattered rocks
    const rockModels = ['rock-large.glb', 'rock-small.glb', 'rock-wide.glb'];
    for (let i = 0; i < 15; i++) {
      const ang = Math.random() * Math.PI * 2;
      const rad = 16 + Math.random() * 18;
      const rx = Math.cos(ang) * rad;
      const rz = Math.sin(ang) * rad;
      const model = rockModels[i % rockModels.length];
      this._loadGLB(`/static/models/village/${model}`).then(r => {
        if (!r) return;
        r.meshes[0].position = new BABYLON.Vector3(rx, 0, rz);
        r.meshes[0].rotation.y = Math.random() * Math.PI * 2;
        const s = 0.6 + Math.random() * 0.8;
        r.meshes[0].scaling = new BABYLON.Vector3(s, s, s);
      }).catch(() => {});
    }

    // Fences along paths
    for (let i = 0; i < 6; i++) {
      const ang = (i / 6) * Math.PI * 2 + 0.2;
      const fx = Math.cos(ang) * 16;
      const fz = Math.sin(ang) * 16;
      this._loadGLB('/static/models/village/fence-broken.glb').then(r => {
        if (!r) return;
        r.meshes[0].position = new BABYLON.Vector3(fx, 0, fz);
        r.meshes[0].rotation.y = ang + Math.PI / 2;
      }).catch(() => {});
    }
  }

  _createProceduralTree(x, z, scale) {
    const scene = this._scene;
    // Trunk
    const trunk = BABYLON.MeshBuilder.CreateCylinder('trunk', {
      diameterTop: 0.15 * scale, diameterBottom: 0.3 * scale,
      height: 2.5 * scale, tessellation: 6
    }, scene);
    trunk.position = new BABYLON.Vector3(x, 1.25 * scale, z);
    const tMat = new BABYLON.StandardMaterial('trunkMat', scene);
    tMat.diffuseColor = new BABYLON.Color3(0.25, 0.15, 0.08);
    tMat.specularColor = BABYLON.Color3.Black();
    trunk.material = tMat;

    // Foliage
    const foliage = BABYLON.MeshBuilder.CreateSphere('foliage', {
      diameter: 2.0 * scale, segments: 6
    }, scene);
    foliage.position = new BABYLON.Vector3(x, 3.0 * scale, z);
    const fMat = new BABYLON.StandardMaterial('foliageMat', scene);
    fMat.diffuseColor = new BABYLON.Color3(0.08 + Math.random() * 0.06, 0.2 + Math.random() * 0.1, 0.05);
    fMat.specularColor = BABYLON.Color3.Black();
    foliage.material = fMat;

    if (this._shadowGen) {
      this._shadowGen.addShadowCaster(trunk);
      this._shadowGen.addShadowCaster(foliage);
    }
  }

  // =========================================================================
  // Lanterns
  // =========================================================================

  _createLanterns() {
    const scene = this._scene;
    for (let i = 0; i < 8; i++) {
      const ang = (i / 8) * Math.PI * 2 + Math.PI / 8;
      const lx = Math.cos(ang) * 8;
      const lz = Math.sin(ang) * 8;

      this._loadGLB('/static/models/graveyard/lightpost-single.glb').then(r => {
        if (!r) return;
        r.meshes[0].position = new BABYLON.Vector3(lx, 0, lz);
      }).catch(() => {
        // Fallback: simple pole + sphere
        const pole = BABYLON.MeshBuilder.CreateCylinder('lpole' + i, { diameter: 0.1, height: 2.5 }, scene);
        pole.position = new BABYLON.Vector3(lx, 1.25, lz);
        const pMat = new BABYLON.StandardMaterial('lpoleMat' + i, scene);
        pMat.diffuseColor = new BABYLON.Color3(0.15, 0.12, 0.1);
        pMat.specularColor = BABYLON.Color3.Black();
        pole.material = pMat;

        const lamp = BABYLON.MeshBuilder.CreateSphere('llamp' + i, { diameter: 0.25 }, scene);
        lamp.position = new BABYLON.Vector3(lx, 2.6, lz);
        const lMat = new BABYLON.StandardMaterial('llampMat' + i, scene);
        lMat.emissiveColor = new BABYLON.Color3(1.0, 0.75, 0.3);
        lMat.disableLighting = true;
        lamp.material = lMat;
      });

      // Warm point light for each lantern
      const ll = new BABYLON.PointLight('lantern' + i, new BABYLON.Vector3(lx, 2.8, lz), scene);
      ll.diffuse = new BABYLON.Color3(1.0, 0.75, 0.35);
      ll.intensity = 0.8;
      ll.range = 6;
      this._lanternLights.push(ll);
    }
  }

  // =========================================================================
  // Fireflies (night particle system)
  // =========================================================================

  _createFireflies() {
    const scene = this._scene;
    const ff = new BABYLON.ParticleSystem('fireflies', 60, scene);
    ff.emitter = new BABYLON.Vector3(0, 1.5, 0);
    ff.minEmitBox = new BABYLON.Vector3(-20, 0.5, -20);
    ff.maxEmitBox = new BABYLON.Vector3(20, 3, 20);
    ff.color1 = new BABYLON.Color4(0.6, 0.9, 0.3, 0.8);
    ff.color2 = new BABYLON.Color4(0.4, 0.8, 0.2, 0.6);
    ff.colorDead = new BABYLON.Color4(0.2, 0.5, 0.1, 0);
    ff.minSize = 0.04;
    ff.maxSize = 0.1;
    ff.minLifeTime = 2;
    ff.maxLifeTime = 5;
    ff.emitRate = 12;
    ff.direction1 = new BABYLON.Vector3(-0.3, 0.2, -0.3);
    ff.direction2 = new BABYLON.Vector3(0.3, 0.5, 0.3);
    ff.gravity = new BABYLON.Vector3(0, 0, 0);
    ff.minEmitPower = 0.1;
    ff.maxEmitPower = 0.4;
    ff.updateSpeed = 0.008;
    ff.blendMode = BABYLON.ParticleSystem.BLENDMODE_ADD;
    ff.start();
    this._fireflySystem = ff;
  }

  // =========================================================================
  // Stars
  // =========================================================================

  _createStars() {
    const scene = this._scene;
    const stars = new BABYLON.ParticleSystem('stars', 200, scene);
    stars.emitter = new BABYLON.Vector3(0, 80, 0);
    stars.minEmitBox = new BABYLON.Vector3(-80, -5, -80);
    stars.maxEmitBox = new BABYLON.Vector3(80, 5, 80);
    stars.color1 = new BABYLON.Color4(0.9, 0.9, 1.0, 0.8);
    stars.color2 = new BABYLON.Color4(0.7, 0.8, 1.0, 0.5);
    stars.colorDead = new BABYLON.Color4(0.5, 0.5, 0.7, 0);
    stars.minSize = 0.05;
    stars.maxSize = 0.15;
    stars.minLifeTime = 8;
    stars.maxLifeTime = 15;
    stars.emitRate = 20;
    stars.direction1 = new BABYLON.Vector3(0, 0, 0);
    stars.direction2 = new BABYLON.Vector3(0, 0.01, 0);
    stars.gravity = BABYLON.Vector3.Zero();
    stars.minEmitPower = 0;
    stars.maxEmitPower = 0.01;
    stars.updateSpeed = 0.005;
    stars.blendMode = BABYLON.ParticleSystem.BLENDMODE_ADD;
    stars.start();
    this._starSystem = stars;
  }

  // =========================================================================
  // GLB Loader with caching and cloning
  // =========================================================================

  _loadGLB(path) {
    if (this._glbCache.has(path)) {
      // Instantiate from cached container
      return this._glbCache.get(path).then(container => {
        if (!container) return null;
        const instances = container.instantiateModelsToScene(name => name + '_i' + Date.now());
        if (!instances || instances.rootNodes.length === 0) return null;
        const root = instances.rootNodes[0];
        // Collect all descendant meshes for callers that iterate r.meshes
        const allMeshes = [root];
        root.getChildMeshes(false).forEach(m => allMeshes.push(m));
        return { meshes: allMeshes };
      });
    }

    const dir = path.substring(0, path.lastIndexOf('/') + 1);
    const file = path.substring(path.lastIndexOf('/') + 1);

    const promise = BABYLON.SceneLoader.LoadAssetContainerAsync(dir, file, this._scene).then(container => {
      return container;
    }).catch(err => {
      console.warn(`[Village3D] Failed to load ${path}:`, err.message || err);
      return null;
    });

    this._glbCache.set(path, promise);

    // For first load, also instantiate
    return promise.then(container => {
      if (!container) return null;
      const instances = container.instantiateModelsToScene(name => name + '_i0');
      if (!instances || instances.rootNodes.length === 0) return null;
      const root = instances.rootNodes[0];
      const allMeshes = [root];
      root.getChildMeshes(false).forEach(m => allMeshes.push(m));
      return { meshes: allMeshes };
    });
  }

  // =========================================================================
  // Role colors from API
  // =========================================================================

  async _loadRoleColors() {
    try {
      const resp = await fetch('/api/roles');
      if (resp.ok) {
        const data = await resp.json();
        if (data.roles) {
          for (const [key, info] of Object.entries(data.roles)) {
            if (info.farbe) {
              this._roleColors[key.toLowerCase()] = info.farbe;
            }
          }
        }
      }
    } catch (e) {
      // Use defaults
    }
  }

  _getRoleColor(rolle) {
    if (!rolle) return '#6b7280';
    const key = rolle.toLowerCase().replace(/\s+/g, '_').replace(/ä/g, 'ae').replace(/ö/g, 'oe').replace(/ü/g, 'ue').replace(/ß/g, 'ss');
    return this._roleColors[key] || this._roleColors[rolle.toLowerCase()] || '#6b7280';
  }

  // =========================================================================
  // PLAYER MANAGEMENT
  // =========================================================================

  /**
   * Set all players and create their 3D representations
   * @param {Array<{id,name,rolle,ist_am_leben,ist_erzaehler}>} players
   */
  async setPlayers(players) {
    // Wait for engine/scene initialization before creating any 3D objects
    await this._ready;
    if (!this._scene || this._destroyed) return;

    this._players = players;

    // Remove old player nodes
    for (const [, info] of this._playerNodes) {
      if (info.root) info.root.dispose();
      if (info.label) info.label.dispose();
    }
    this._playerNodes.clear();

    const count = players.length;
    const radius = Math.max(12, count * 1.2);

    players.forEach((p, idx) => {
      const angle = (idx / count) * Math.PI * 2 - Math.PI / 2;
      const x = Math.cos(angle) * radius;
      const z = Math.sin(angle) * radius;

      // Root transform node
      const root = new BABYLON.TransformNode('player_' + p.id, this._scene);
      root.position = new BABYLON.Vector3(x, 0, z);
      root.metadata = { playerId: p.id };

      // Build house at this position
      this._buildPlayerHouse(p, root, angle, idx);

      // Build character
      this._buildPlayerCharacter(p, root, angle, idx);

      // Pedestal / selection ring
      const pedestal = BABYLON.MeshBuilder.CreateTorus('pedestal_' + p.id, {
        diameter: 1.6, thickness: 0.1, tessellation: 32
      }, this._scene);
      pedestal.position = new BABYLON.Vector3(0, 0.05, 1.5);
      pedestal.parent = root;
      const pedMat = new BABYLON.StandardMaterial('pedMat_' + p.id, this._scene);
      const roleColor = hexToColor3(this._getRoleColor(p.rolle));
      pedMat.emissiveColor = roleColor;
      pedMat.diffuseColor = roleColor;
      pedMat.alpha = 0.6;
      pedestal.material = pedMat;

      // Name label (Babylon GUI)
      const label = this._createPlayerLabel(p, root);

      // Store
      this._playerNodes.set(p.id, {
        root,
        character: null, // set in _buildPlayerCharacter callback
        label,
        pedestal,
        pedestalMat: pedMat,
        isAlive: p.ist_am_leben,
        rolle: p.rolle,
        angle,
        houseRoot: null,
      });

      // If dead, apply dead effect
      if (!p.ist_am_leben) {
        this._applyDeathEffect(p.id);
      }
    });

    // Auto-fit camera to show the full player ring plus houses behind them
    this._playerRadius = radius;
    if (this._arcCamera) {
      // Camera needs to see the ring at `radius` + houses behind (~3 units)
      // With an ArcRotateCamera, radius ~= viewing distance from target
      this._arcCamera.radius = radius + 12;
      this._arcCamera.beta = Math.PI / 3.5;  // ~51 degrees from vertical
      this._arcCamera.target = new BABYLON.Vector3(0, 1, 0); // slightly above ground
    }
  }

  _buildPlayerHouse(player, rootNode, angle, idx) {
    const bp = HOUSE_BLUEPRINTS[idx % HOUSE_BLUEPRINTS.length];
    const houseRoot = new BABYLON.TransformNode('house_' + player.id, this._scene);
    houseRoot.parent = rootNode;
    houseRoot.position = new BABYLON.Vector3(0, 0, -1.5);
    // Rotate house to face center
    houseRoot.rotation.y = angle + Math.PI;

    const wallPositions = [
      { x: 0, z: -0.5, ry: 0 },    // back
      { x: 0.5, z: 0, ry: Math.PI / 2 },  // right
      { x: 0, z: 0.5, ry: Math.PI },  // front (door)
      { x: -0.5, z: 0, ry: -Math.PI / 2 }, // left
    ];

    bp.walls.forEach((wallFile, wi) => {
      this._loadGLB(`/static/models/village/${wallFile}`).then(r => {
        if (!r || this._destroyed) return;
        const m = r.meshes[0];
        m.parent = houseRoot;
        m.position = new BABYLON.Vector3(wallPositions[wi].x, 0, wallPositions[wi].z);
        m.rotation.y = wallPositions[wi].ry;
        if (this._shadowGen) this._shadowGen.addShadowCaster(m);
      }).catch(() => {});
    });

    // Roof
    this._loadGLB(`/static/models/village/${bp.roof}`).then(r => {
      if (!r || this._destroyed) return;
      const m = r.meshes[0];
      m.parent = houseRoot;
      m.position.y = 1.0;
      if (this._shadowGen) this._shadowGen.addShadowCaster(m);
    }).catch(() => {});

    // Chimney
    if (bp.chimney) {
      this._loadGLB('/static/models/village/chimney-base.glb').then(r => {
        if (!r || this._destroyed) return;
        const m = r.meshes[0];
        m.parent = houseRoot;
        m.position = new BABYLON.Vector3(0.2, 1.3, -0.2);
        m.scaling = new BABYLON.Vector3(0.5, 0.5, 0.5);
      }).catch(() => {});
    }

    const nodeInfo = this._playerNodes.get(player.id);
    if (nodeInfo) nodeInfo.houseRoot = houseRoot;
  }

  _buildPlayerCharacter(player, rootNode, angle, idx) {
    const charLetter = CHAR_LETTERS[idx % CHAR_LETTERS.length];
    const charPath = `/static/models/characters/character-${charLetter}.glb`;

    // Position character in front of house (toward center)
    const charPos = new BABYLON.Vector3(0, 0, 1.5);

    this._loadGLB(charPath).then(r => {
      if (!r || this._destroyed) return;
      const m = r.meshes[0];
      m.parent = rootNode;
      m.position = charPos.clone();
      // Face center
      m.rotation.y = angle + Math.PI;
      m.scaling = new BABYLON.Vector3(1.2, 1.2, 1.2);

      // Tint based on role
      if (player.rolle) {
        const color = hexToColor3(this._getRoleColor(player.rolle));
        r.meshes.forEach(mesh => {
          if (mesh.material) {
            const tinted = mesh.material.clone('tint_' + mesh.name);
            tinted.diffuseColor = BABYLON.Color3.Lerp(
              tinted.diffuseColor || BABYLON.Color3.White(), color, 0.35);
            mesh.material = tinted;
          }
        });
      }

      if (this._shadowGen) this._shadowGen.addShadowCaster(m);

      // Picking: make clickable
      r.meshes.forEach(mesh => {
        if (mesh.isPickable !== undefined) {
          mesh.isPickable = true;
        }
        mesh.metadata = { playerId: player.id };
      });

      // Store character ref
      const nodeInfo = this._playerNodes.get(player.id);
      if (nodeInfo) nodeInfo.character = m;
    }).catch(() => {
      // Fallback: procedural character
      const body = BABYLON.MeshBuilder.CreateCapsule('char_' + player.id, {
        radius: 0.35, height: 1.6
      }, this._scene);
      body.parent = rootNode;
      body.position = new BABYLON.Vector3(charPos.x, 0.8, charPos.z);
      body.rotation.y = angle + Math.PI;
      const mat = new BABYLON.StandardMaterial('charMat_' + player.id, this._scene);
      mat.diffuseColor = hexToColor3(this._getRoleColor(player.rolle));
      mat.specularColor = BABYLON.Color3.Black();
      body.material = mat;
      body.isPickable = true;
      body.metadata = { playerId: player.id };
      if (this._shadowGen) this._shadowGen.addShadowCaster(body);

      const nodeInfo = this._playerNodes.get(player.id);
      if (nodeInfo) nodeInfo.character = body;
    });
  }

  _createPlayerLabel(player, rootNode) {
    if (!this._advancedTexture) return null;

    const rect = new BABYLON.GUI.Rectangle('labelRect_' + player.id);
    rect.width = '140px';
    rect.height = '32px';
    rect.cornerRadius = 8;
    rect.color = 'rgba(255,255,255,0.6)';
    rect.thickness = 1;
    rect.background = 'rgba(0,0,0,0.7)';
    this._advancedTexture.addControl(rect);

    const text = new BABYLON.GUI.TextBlock('labelText_' + player.id);
    text.text = player.name;
    text.color = 'white';
    text.fontSize = 14;
    text.fontWeight = 'bold';
    rect.addControl(text);

    // Link to 3D position
    rect.linkWithMesh(rootNode);
    rect.linkOffsetY = -100;

    // Narrator gets gold label
    if (player.ist_erzaehler) {
      rect.background = 'rgba(212,165,116,0.7)';
      text.color = '#000';
    }

    return rect;
  }

  // =========================================================================
  // Death effect
  // =========================================================================

  _applyDeathEffect(playerId) {
    const info = this._playerNodes.get(playerId);
    if (!info) return;

    // Grey out character
    if (info.character) {
      const greyOut = (node) => {
        if (node.material) {
          const gMat = node.material.clone('dead_' + node.name);
          gMat.diffuseColor = new BABYLON.Color3(0.3, 0.3, 0.35);
          gMat.alpha = 0.5;
          node.material = gMat;
        }
        if (node.getChildren) {
          node.getChildren().forEach(greyOut);
        }
      };
      greyOut(info.character);
    }

    // Dim house (tilt slightly)
    if (info.houseRoot) {
      info.houseRoot.rotation.z = 0.05;
      const darken = (node) => {
        if (node.material) {
          const dMat = node.material.clone('deadHouse_' + node.name);
          dMat.diffuseColor = BABYLON.Color3.Lerp(
            dMat.diffuseColor || BABYLON.Color3.White(),
            new BABYLON.Color3(0.1, 0.1, 0.12), 0.6);
          node.material = dMat;
        }
        if (node.getChildren) {
          node.getChildren().forEach(darken);
        }
      };
      darken(info.houseRoot);
    }

    // Dim pedestal
    if (info.pedestalMat) {
      info.pedestalMat.emissiveColor = new BABYLON.Color3(0.2, 0.2, 0.25);
      info.pedestalMat.alpha = 0.3;
    }

    // Dim label
    if (info.label) {
      info.label.background = 'rgba(50,50,50,0.7)';
      info.label.alpha = 0.5;
    }

    // Ghost particle rising
    const rootPos = info.root.position;
    const ghost = new BABYLON.ParticleSystem('ghost_' + playerId, 20, this._scene);
    ghost.emitter = new BABYLON.Vector3(rootPos.x, 1.5, rootPos.z + 1.5);
    ghost.minEmitBox = new BABYLON.Vector3(-0.2, 0, -0.2);
    ghost.maxEmitBox = new BABYLON.Vector3(0.2, 0, 0.2);
    ghost.color1 = new BABYLON.Color4(0.7, 0.7, 0.8, 0.5);
    ghost.color2 = new BABYLON.Color4(0.5, 0.5, 0.6, 0.3);
    ghost.colorDead = new BABYLON.Color4(0.3, 0.3, 0.4, 0);
    ghost.minSize = 0.1;
    ghost.maxSize = 0.3;
    ghost.minLifeTime = 1;
    ghost.maxLifeTime = 2.5;
    ghost.emitRate = 8;
    ghost.direction1 = new BABYLON.Vector3(-0.1, 1, -0.1);
    ghost.direction2 = new BABYLON.Vector3(0.1, 2, 0.1);
    ghost.gravity = new BABYLON.Vector3(0, 0.5, 0);
    ghost.minEmitPower = 0.3;
    ghost.maxEmitPower = 0.8;
    ghost.blendMode = BABYLON.ParticleSystem.BLENDMODE_ADD;
    ghost.targetStopDuration = 3;
    ghost.start();

    // Auto-dispose
    setTimeout(() => { ghost.dispose(); }, 5000);
  }

  // =========================================================================
  // DAY / NIGHT
  // =========================================================================

  /**
   * @param {boolean} isNight
   */
  setTimeOfDay(isNight) {
    this._timeTarget = isNight ? 1 : 0;
    this._isNight = isNight;
    // Kick off transition (runs in render loop)
  }

  _updateTransitions() {
    const dt = this._engine.getDeltaTime() / 1000;
    const speed = 0.5; // full transition in ~2s

    const current = this._timeTransition;
    const target = this._timeTarget;
    if (Math.abs(current - target) < 0.001) {
      this._timeTransition = target;
    } else {
      this._timeTransition += (target - current) * speed * dt * 4;
    }
    const t = this._timeTransition; // 0 = day, 1 = night

    // Fog
    this._scene.fogDensity = lerpNumber(0.015, 0.035, t);
    this._scene.fogColor = lerpColor3(
      new BABYLON.Color3(0.45, 0.45, 0.5),  // day fog (light grey-blue)
      new BABYLON.Color3(0.05, 0.05, 0.12), // night fog
      t
    );

    // Sky
    if (this._skyMat) {
      this._skyMat.emissiveColor = lerpColor3(
        new BABYLON.Color3(0.30, 0.32, 0.38),
        new BABYLON.Color3(0.02, 0.02, 0.06),
        t
      );
    }

    // Clear color
    this._scene.clearColor = new BABYLON.Color4(
      lerpNumber(0.30, 0.02, t),
      lerpNumber(0.30, 0.02, t),
      lerpNumber(0.36, 0.06, t),
      1
    );

    // Directional light
    if (this._dirLight) {
      this._dirLight.intensity = lerpNumber(0.9, 0.15, t);
      this._dirLight.diffuse = lerpColor3(
        new BABYLON.Color3(0.85, 0.8, 0.7), // day (warm sunlight)
        new BABYLON.Color3(0.3, 0.35, 0.55), // night (moonlight)
        t
      );
    }

    // Hemisphere
    if (this._hemiLight) {
      this._hemiLight.intensity = lerpNumber(0.55, 0.15, t);
      this._hemiLight.diffuse = lerpColor3(
        new BABYLON.Color3(0.55, 0.55, 0.6),
        new BABYLON.Color3(0.12, 0.12, 0.2),
        t
      );
    }

    // Campfire glow (stronger at night)
    if (this._campfireLight) {
      this._campfireLight.intensity = lerpNumber(1.0, 3.0, t);
      // Flicker
      const flicker = Math.sin(Date.now() * 0.008) * 0.3 + Math.sin(Date.now() * 0.013) * 0.15;
      this._campfireLight.intensity += flicker * t;
    }

    // Lanterns (bright at night, dim at day)
    for (const ll of this._lanternLights) {
      ll.intensity = lerpNumber(0.15, 0.9, t);
    }

    // Moon/Sun alpha
    if (this._moonBillboard && this._moonBillboard.material) {
      this._moonBillboard.material.alpha = lerpNumber(0, 0.9, t);
    }
    if (this._sunBillboard && this._sunMat) {
      this._sunMat.alpha = lerpNumber(0.7, 0, t);
    }

    // Fireflies only at night
    if (this._fireflySystem) {
      this._fireflySystem.emitRate = t > 0.5 ? 15 : 0;
    }

    // Stars only at night
    if (this._starSystem) {
      this._starSystem.emitRate = t > 0.3 ? 20 : 0;
    }
  }

  // =========================================================================
  // Input / Picking
  // =========================================================================

  _setupPicking() {
    const scene = this._scene;

    scene.onPointerDown = (evt, pickResult) => {
      if (evt.button !== 0) return; // left click only

      if (pickResult.hit && pickResult.pickedMesh) {
        const playerId = this._findPlayerIdFromMesh(pickResult.pickedMesh);
        if (playerId !== null && this.onPlayerClick) {
          this.onPlayerClick(playerId);
        }
      }
    };

    // Hover effect
    scene.onPointerMove = (_evt, pickResult) => {
      if (pickResult.hit && pickResult.pickedMesh) {
        const pid = this._findPlayerIdFromMesh(pickResult.pickedMesh);
        this._setHoverPlayer(pid);
      } else {
        this._setHoverPlayer(null);
      }
    };

    this._hoveredPlayerId = null;
  }

  _findPlayerIdFromMesh(mesh) {
    // Walk up parent chain to find metadata.playerId
    let current = mesh;
    while (current) {
      if (current.metadata && current.metadata.playerId !== undefined) {
        return current.metadata.playerId;
      }
      current = current.parent;
    }
    return null;
  }

  _setHoverPlayer(playerId) {
    if (this._hoveredPlayerId === playerId) return;

    // Un-hover old
    if (this._hoveredPlayerId !== null) {
      const info = this._playerNodes.get(this._hoveredPlayerId);
      if (info && info.pedestal && info.pedestalMat) {
        if (this._hoveredPlayerId !== this._selectedPlayerId) {
          info.pedestalMat.alpha = 0.6;
        }
      }
      this._canvas.style.cursor = 'default';
    }

    this._hoveredPlayerId = playerId;

    // Hover new
    if (playerId !== null) {
      const info = this._playerNodes.get(playerId);
      if (info && info.pedestal && info.pedestalMat && info.isAlive) {
        info.pedestalMat.alpha = 1.0;
        this._canvas.style.cursor = 'pointer';
      }
    }
  }

  // =========================================================================
  // CAMERA METHODS
  // =========================================================================

  resetCamera() {
    if (this._viewMode === 'first-person') {
      this.exitFirstPerson();
    }
    const r = this._playerRadius || 12;
    this._arcCamera.alpha = -Math.PI / 2;
    this._arcCamera.beta = Math.PI / 3.5;
    this._arcCamera.radius = r + 12;
    this._arcCamera.target = new BABYLON.Vector3(0, 1, 0);
  }

  zoomToPlayer(playerId) {
    const info = this._playerNodes.get(playerId);
    if (!info) return;
    const pos = info.root.position;
    if (this._viewMode === 'top-down') {
      this._arcCamera.target = new BABYLON.Vector3(pos.x, 1, pos.z);
      this._arcCamera.radius = 10;
    } else {
      this._fpCamera.position = new BABYLON.Vector3(
        pos.x, this._firstPersonHeight, pos.z + 3);
      this._fpCamera.setTarget(new BABYLON.Vector3(pos.x, 1.2, pos.z));
    }
  }

  focusOnPlayer(playerId) {
    this.zoomToPlayer(playerId);
  }

  toggleViewMode(playerId) {
    if (this._viewMode === 'top-down') {
      return this.enterFirstPerson(playerId);
    } else {
      return this.exitFirstPerson();
    }
  }

  toggleFirstPerson(playerId) {
    return this.toggleViewMode(playerId);
  }

  enterFirstPerson(playerId) {
    const pid = playerId || this._firstPersonPlayerId || this._findFirstAlivePlayer();
    if (pid === null) return this._viewMode;

    const info = this._playerNodes.get(pid);
    if (!info) return this._viewMode;

    this._viewMode = 'first-person';
    this._scene.activeCamera = this._fpCamera;
    this._arcCamera.detachControl();
    this._fpCamera.attachControl(this._canvas, true);

    const pos = info.root.position;
    this._fpCamera.position = new BABYLON.Vector3(pos.x, this._firstPersonHeight, pos.z + 1.5);
    this._fpCamera.setTarget(BABYLON.Vector3.Zero());
    this._activeCamera = this._fpCamera;

    return this._viewMode;
  }

  exitFirstPerson() {
    this._viewMode = 'top-down';
    this._scene.activeCamera = this._arcCamera;
    this._fpCamera.detachControl();
    this._arcCamera.attachControl(this._canvas, true);
    this._activeCamera = this._arcCamera;
    return this._viewMode;
  }

  getViewMode() {
    return this._viewMode;
  }

  _findFirstAlivePlayer() {
    for (const p of this._players) {
      if (p.ist_am_leben && !p.ist_erzaehler) return p.id;
    }
    return this._players.length > 0 ? this._players[0].id : null;
  }

  // =========================================================================
  // PLAYER STATUS
  // =========================================================================

  updatePlayerStatus(playerId, isAlive) {
    const info = this._playerNodes.get(playerId);
    if (!info) return;
    info.isAlive = isAlive;

    if (!isAlive) {
      this._applyDeathEffect(playerId);
    }
  }

  // =========================================================================
  // HIGHLIGHT / SELECTION
  // =========================================================================

  highlightPlayer(playerId, color = '#ffd54a') {
    const info = this._playerNodes.get(playerId);
    if (!info || !info.pedestal) return;

    const c = hexToColor3(color);
    info.pedestalMat.emissiveColor = c;
    info.pedestalMat.alpha = 1.0;

    // Pulse animation then fade
    const start = Date.now();
    const timer = setInterval(() => {
      const elapsed = (Date.now() - start) / 1000;
      if (elapsed > 2 || this._destroyed) {
        clearInterval(timer);
        if (playerId !== this._selectedPlayerId) {
          info.pedestalMat.alpha = 0.6;
        }
        return;
      }
      info.pedestalMat.alpha = 0.6 + Math.sin(elapsed * 8) * 0.4;
    }, 30);
    this._effectTimers.push(timer);
  }

  setSelectedPlayer(playerId, color = '#ffd54a') {
    // Clear old selection
    if (this._selectedPlayerId !== null) {
      const oldInfo = this._playerNodes.get(this._selectedPlayerId);
      if (oldInfo && oldInfo.pedestalMat) {
        const roleC = hexToColor3(this._getRoleColor(oldInfo.rolle));
        oldInfo.pedestalMat.emissiveColor = roleC;
        oldInfo.pedestalMat.alpha = 0.6;
      }
    }

    this._selectedPlayerId = playerId;

    if (playerId !== null) {
      const info = this._playerNodes.get(playerId);
      if (info && info.pedestalMat) {
        const c = hexToColor3(color);
        info.pedestalMat.emissiveColor = c;
        info.pedestalMat.alpha = 1.0;
      }
    }
  }

  highlightVictim(playerId) {
    this._victimPlayerId = playerId;
    const info = this._playerNodes.get(playerId);
    if (!info) return;

    // Red pulsing ring
    info.pedestalMat.emissiveColor = new BABYLON.Color3(0.9, 0.1, 0.1);

    // Pulsing
    const timer = setInterval(() => {
      if (this._victimPlayerId !== playerId || this._destroyed) {
        clearInterval(timer);
        return;
      }
      const pulse = Math.sin(Date.now() * 0.006) * 0.4 + 0.6;
      info.pedestalMat.alpha = pulse;
    }, 30);
    this._effectTimers.push(timer);
  }

  clearVictimHighlight() {
    if (this._victimPlayerId !== null) {
      const info = this._playerNodes.get(this._victimPlayerId);
      if (info && info.pedestalMat) {
        const roleC = hexToColor3(this._getRoleColor(info.rolle));
        info.pedestalMat.emissiveColor = roleC;
        info.pedestalMat.alpha = 0.6;
      }
    }
    this._victimPlayerId = null;
  }

  // =========================================================================
  // HINTS / INDICATORS
  // =========================================================================

  showHint(playerId, type) {
    const info = this._playerNodes.get(playerId);
    if (!info) return;

    const colors = {
      'target': '#ff4444', 'heal': '#44ff44', 'protect': '#4488ff',
      'investigate': '#aa44ff',
    };
    const color = colors[type] || '#ffffff';
    this.highlightPlayer(playerId, color);
  }

  showVoteIndicator(playerId, voterName) {
    const info = this._playerNodes.get(playerId);
    if (!info) return;

    // Create a floating text above the player
    if (!this._advancedTexture) return;
    const voteLabel = new BABYLON.GUI.Rectangle('vote_' + playerId + '_' + Date.now());
    voteLabel.width = '90px';
    voteLabel.height = '22px';
    voteLabel.cornerRadius = 6;
    voteLabel.background = 'rgba(218,165,32,0.85)';
    voteLabel.color = 'rgba(255,255,255,0.6)';
    voteLabel.thickness = 1;
    this._advancedTexture.addControl(voteLabel);

    const vt = new BABYLON.GUI.TextBlock();
    vt.text = voterName;
    vt.color = '#1a1a1a';
    vt.fontSize = 11;
    vt.fontWeight = 'bold';
    voteLabel.addControl(vt);

    voteLabel.linkWithMesh(info.root);
    voteLabel.linkOffsetY = -130;

    // Fade and remove
    setTimeout(() => {
      if (!this._destroyed) voteLabel.dispose();
    }, 4000);
  }

  showChatBubble(playerId, message, duration = 4000) {
    const info = this._playerNodes.get(playerId);
    if (!info || !this._advancedTexture) return;

    const truncated = message.length > 40 ? message.slice(0, 37) + '...' : message;

    const bubble = new BABYLON.GUI.Rectangle('chat_' + playerId + '_' + Date.now());
    bubble.width = '160px';
    bubble.adaptHeightToChildren = true;
    bubble.cornerRadius = 10;
    bubble.background = 'rgba(0,0,0,0.75)';
    bubble.color = 'rgba(255,255,255,0.3)';
    bubble.thickness = 1;
    bubble.paddingTop = '4px';
    bubble.paddingBottom = '4px';
    bubble.paddingLeft = '6px';
    bubble.paddingRight = '6px';
    this._advancedTexture.addControl(bubble);

    const bt = new BABYLON.GUI.TextBlock();
    bt.text = truncated;
    bt.color = 'white';
    bt.fontSize = 11;
    bt.textWrapping = BABYLON.GUI.TextWrapping.WordWrap;
    bt.resizeToFit = true;
    bt.paddingTop = '4px';
    bt.paddingBottom = '4px';
    bubble.addControl(bt);

    bubble.linkWithMesh(info.root);
    bubble.linkOffsetY = -150;

    setTimeout(() => {
      if (!this._destroyed) bubble.dispose();
    }, duration);
  }

  // =========================================================================
  // ACTION EFFECTS
  // =========================================================================

  showActionEffect(playerId, effectType) {
    const info = this._playerNodes.get(playerId);
    if (!info) return;

    const pos = info.root.position;
    const charPos = new BABYLON.Vector3(pos.x, 1.2, pos.z + 1.5);

    const effectConfigs = {
      'heal': { color1: [0.2, 0.9, 0.3, 1], color2: [0.1, 0.7, 0.2, 0.7], dir: [0, 2, 0], size: [0.1, 0.3] },
      'attack': { color1: [1, 0.2, 0.1, 1], color2: [0.8, 0.1, 0, 0.8], dir: [1, 1, 1], size: [0.15, 0.4] },
      'protect': { color1: [0.3, 0.5, 1, 0.8], color2: [0.2, 0.3, 0.9, 0.5], dir: [0, 1.5, 0], size: [0.2, 0.5] },
      'poison': { color1: [0.6, 0.1, 0.8, 1], color2: [0.4, 0, 0.6, 0.7], dir: [0, 1, 0], size: [0.1, 0.3] },
    };

    const cfg = effectConfigs[effectType] || effectConfigs['heal'];

    const ps = new BABYLON.ParticleSystem('effect_' + effectType, 50, this._scene);
    ps.emitter = charPos;
    ps.minEmitBox = new BABYLON.Vector3(-0.3, 0, -0.3);
    ps.maxEmitBox = new BABYLON.Vector3(0.3, 0, 0.3);
    ps.color1 = new BABYLON.Color4(...cfg.color1);
    ps.color2 = new BABYLON.Color4(...cfg.color2);
    ps.colorDead = new BABYLON.Color4(0, 0, 0, 0);
    ps.minSize = cfg.size[0];
    ps.maxSize = cfg.size[1];
    ps.minLifeTime = 0.5;
    ps.maxLifeTime = 1.5;
    ps.emitRate = 40;
    ps.direction1 = new BABYLON.Vector3(-cfg.dir[0], cfg.dir[1], -cfg.dir[2]);
    ps.direction2 = new BABYLON.Vector3(cfg.dir[0], cfg.dir[1] * 1.5, cfg.dir[2]);
    ps.gravity = new BABYLON.Vector3(0, -0.5, 0);
    ps.minEmitPower = 0.5;
    ps.maxEmitPower = 1.5;
    ps.blendMode = BABYLON.ParticleSystem.BLENDMODE_ADD;
    ps.targetStopDuration = 1.5;
    ps.start();

    setTimeout(() => { ps.dispose(); }, 3000);

    // Protect: also show a translucent sphere shield
    if (effectType === 'protect') {
      const shield = BABYLON.MeshBuilder.CreateSphere('shield_' + playerId, { diameter: 2.0, segments: 16 }, this._scene);
      shield.position = charPos.clone();
      const sMat = new BABYLON.StandardMaterial('shieldMat', this._scene);
      sMat.diffuseColor = new BABYLON.Color3(0.3, 0.5, 1.0);
      sMat.emissiveColor = new BABYLON.Color3(0.2, 0.3, 0.8);
      sMat.alpha = 0.2;
      sMat.backFaceCulling = false;
      shield.material = sMat;

      let elapsed = 0;
      const timer = setInterval(() => {
        elapsed += 0.03;
        sMat.alpha = 0.2 + Math.sin(elapsed * 5) * 0.1;
        if (elapsed > 2 || this._destroyed) {
          clearInterval(timer);
          shield.dispose();
        }
      }, 30);
      this._effectTimers.push(timer);
    }
  }

  // =========================================================================
  // SLEEPING
  // =========================================================================

  setPlayerSleeping(playerId, isSleeping) {
    if (isSleeping) {
      this._sleepingPlayers.add(playerId);
    } else {
      this._sleepingPlayers.delete(playerId);
    }

    const info = this._playerNodes.get(playerId);
    if (!info || !info.character) return;

    if (isSleeping) {
      // Tilt character to suggest sleeping
      info.character.rotation.z = 0.3;
      // Zzz particles
      if (!info.sleepParticles) {
        const zps = new BABYLON.ParticleSystem('zzz_' + playerId, 5, this._scene);
        zps.emitter = new BABYLON.Vector3(
          info.root.position.x, 2.2, info.root.position.z + 1.5);
        zps.minEmitBox = BABYLON.Vector3.Zero();
        zps.maxEmitBox = BABYLON.Vector3.Zero();
        zps.color1 = new BABYLON.Color4(0.7, 0.7, 0.9, 0.6);
        zps.color2 = new BABYLON.Color4(0.5, 0.5, 0.8, 0.4);
        zps.colorDead = new BABYLON.Color4(0.3, 0.3, 0.5, 0);
        zps.minSize = 0.1;
        zps.maxSize = 0.2;
        zps.minLifeTime = 1.5;
        zps.maxLifeTime = 3;
        zps.emitRate = 2;
        zps.direction1 = new BABYLON.Vector3(-0.1, 0.5, 0);
        zps.direction2 = new BABYLON.Vector3(0.1, 1, 0);
        zps.gravity = new BABYLON.Vector3(0, 0.2, 0);
        zps.minEmitPower = 0.1;
        zps.maxEmitPower = 0.3;
        zps.blendMode = BABYLON.ParticleSystem.BLENDMODE_ADD;
        zps.start();
        info.sleepParticles = zps;
      }
    } else {
      info.character.rotation.z = 0;
      if (info.sleepParticles) {
        info.sleepParticles.stop();
        info.sleepParticles.dispose();
        info.sleepParticles = null;
      }
    }
  }

  // =========================================================================
  // HUD (delegates to HTML overlay elements in spiel.html)
  // =========================================================================

  showFullscreenUI(show) {
    this._hudVisible = !!show;
    const hud = document.getElementById('village3d-hud');
    if (hud) {
      hud.classList.toggle('is-visible', this._hudVisible);
    }
  }

  toggleLeftSidebar() {
    this._leftSidebarVisible = !this._leftSidebarVisible;
    const panel = document.getElementById('village3d-left-panel');
    if (panel) panel.classList.toggle('is-collapsed', !this._leftSidebarVisible);
  }

  toggleRightSidebar() {
    this._rightSidebarVisible = !this._rightSidebarVisible;
    const panel = document.getElementById('village3d-right-panel');
    if (panel) panel.classList.toggle('is-collapsed', !this._rightSidebarVisible);
  }

  updateTopBar(phase, round) {
    const phaseEl = document.getElementById('village3d-phase-name');
    const roundEl = document.getElementById('village3d-round-info');
    if (phaseEl) {
      const isNight = phase && (phase.includes('nacht') || (phase.includes('phase') && !phase.includes('tag')));
      const icon = isNight ? 'fa-moon' : 'fa-sun';
      const displayName = phase ? phase.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) : '...';
      phaseEl.innerHTML = `<i class="fa-solid ${icon}"></i> ${displayName}`;
    }
    if (roundEl && round !== undefined) {
      roundEl.textContent = `Runde ${round}`;
    }
  }

  updateRoleBadge(role, color = null) {
    const badge = document.getElementById('village3d-role-badge');
    if (!badge) return;
    badge.textContent = role || 'Warte...';
    if (color) {
      badge.style.borderColor = color;
      badge.style.background = `${color}33`;
    }
  }

  addChatMessage(from, text, isDead = false) {
    const container = document.getElementById('village3d-chat-messages');
    if (!container) return;
    const row = document.createElement('div');
    row.className = 'village3d-chat-row';
    if (isDead) row.style.opacity = '0.5';
    row.innerHTML = `<strong>${from}:</strong> ${text}`;
    container.appendChild(row);
    container.scrollTop = container.scrollHeight;
  }

  updateActionButtons(buttons) {
    const container = document.getElementById('village3d-action-buttons');
    if (!container) return;
    container.innerHTML = '';
    if (!buttons || buttons.length === 0) return;

    buttons.forEach(btn => {
      const el = document.createElement('button');
      el.className = 'v3d-icon-btn';
      el.style.marginRight = '8px';
      el.style.padding = '8px 14px';
      el.textContent = btn.label;
      if (btn.title) el.title = btn.title;
      if (btn.disabled) el.disabled = true;
      el.addEventListener('click', () => { if (btn.action) btn.action(); });
      container.appendChild(el);
    });
  }

  // =========================================================================
  // DESTROY
  // =========================================================================

  destroy() {
    this._destroyed = true;

    // Clear timers
    for (const t of this._effectTimers) clearInterval(t);
    this._effectTimers = [];

    // Dispose particles
    [this._campfireFlame, this._campfireSmoke, this._campfireEmbers,
     this._fireflySystem, this._starSystem].forEach(ps => {
      if (ps) ps.dispose();
    });

    // Dispose player stuff
    for (const [, info] of this._playerNodes) {
      if (info.label) info.label.dispose();
      if (info.sleepParticles) info.sleepParticles.dispose();
    }
    this._playerNodes.clear();

    // Dispose GUI
    if (this._advancedTexture) this._advancedTexture.dispose();

    // Dispose scene and engine
    if (this._scene) this._scene.dispose();
    if (this._engine) {
      this._engine.stopRenderLoop();
      this._engine.dispose();
    }

    // Remove canvas
    if (this._canvas && this._canvas.parentNode) {
      this._canvas.parentNode.removeChild(this._canvas);
    }

    // Remove resize handler
    if (this._resizeHandler) {
      window.removeEventListener('resize', this._resizeHandler);
    }

    console.info('[Village3D-Babylon] Destroyed');
  }
}

export default Village3DBabylon;
