/**
 * Webwölfe - PlayCanvas Village Renderer
 *
 * Advanced 3D Village Renderer using PlayCanvas engine.
 * Features:
 * - PBR Materials
 * - Dynamic Lighting (Day/Night Cycle)
 * - Particle Systems (Fire, Fog)
 * - Interactive Player Avatars
 * - Smooth Camera Controls
 */

export default class Village3DPlayCanvas {
  constructor(containerId, raumCode) {
    this.containerId = containerId;
    this.raumCode = raumCode;
    this.container = document.getElementById(containerId);
    this.players = [];
    this.playerEntities = new Map();
    this.isNight = true;
    this.onPlayerClick = null;

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
    this.app.setCanvasFillMode(pc.FILLMODE_FILL_WINDOW);
    this.app.setCanvasResolution(pc.RESOLUTION_AUTO);

    // Resize handler
    window.addEventListener("resize", () => this.app.resizeCanvas());

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
      farClip: 100,
      fov: 45,
    });
    this.camera.setPosition(0, 15, 25);
    this.camera.lookAt(0, 0, 0);
    this.app.root.addChild(this.camera);

    // Orbit Controls (Custom implementation for simplicity)
    this.cameraAngle = 0;
    this.cameraHeight = 15;
    this.cameraRadius = 25;
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
      shadowDistance: 50,
    });
    this.light.setLocalEulerAngles(45, 30, 0);
    this.app.root.addChild(this.light);

    // Ground
    this.createGround();

    // Campfire
    this.createCampfire();

    // Environment (Trees, Stones)
    this.createEnvironment();
  }

  createGround() {
    const ground = new pc.Entity("Ground");
    ground.addComponent("model", {
      type: "plane",
    });
    ground.setLocalScale(50, 1, 50);

    const material = new pc.StandardMaterial();
    material.diffuse = new pc.Color(0.1, 0.15, 0.1); // Dark grass
    material.specular = new pc.Color(0.05, 0.05, 0.05);
    material.update();

    ground.model.material = material;
    this.app.root.addChild(ground);
  }

  createCampfire() {
    // Fire Light
    this.fireLight = new pc.Entity("FireLight");
    this.fireLight.addComponent("light", {
      type: "point",
      color: new pc.Color(1, 0.5, 0.1),
      intensity: 2,
      range: 15,
      castShadows: true,
    });
    this.fireLight.setPosition(0, 1, 0);
    this.app.root.addChild(this.fireLight);

    // Logs
    for (let i = 0; i < 5; i++) {
      const log = new pc.Entity("Log");
      log.addComponent("model", {
        type: "cylinder",
      });
      log.setLocalScale(0.2, 1, 0.2);
      log.setLocalPosition(
        Math.sin(i * 1.25) * 0.5,
        0.1,
        Math.cos(i * 1.25) * 0.5,
      );
      log.setLocalEulerAngles(90, i * 72, 0);

      const mat = new pc.StandardMaterial();
      mat.diffuse = new pc.Color(0.3, 0.2, 0.1);
      mat.update();
      log.model.material = mat;

      this.app.root.addChild(log);
    }

    // Simple Particle System for Fire (using planes)
    this.fireParticles = [];
    for (let i = 0; i < 10; i++) {
      const p = new pc.Entity("FireParticle");
      p.addComponent("model", { type: "plane" });
      p.setLocalScale(0.5, 0.5, 0.5);
      p.setLocalEulerAngles(90, 0, 0); // Face up? No, billboard later

      const mat = new pc.StandardMaterial();
      mat.emissive = new pc.Color(1, 0.6, 0.2);
      mat.opacity = 0.8;
      mat.blendType = pc.BLEND_ADDITIVE;
      mat.update();
      p.model.material = mat;

      this.app.root.addChild(p);
      this.fireParticles.push({
        entity: p,
        speed: 0.5 + Math.random(),
        offset: Math.random() * Math.PI * 2,
        life: Math.random(),
      });
    }

    // Register update for animation
    this.app.on("update", (dt) => this.update(dt));
  }

  createEnvironment() {
    // Trees
    for (let i = 0; i < 20; i++) {
      const angle = (i / 20) * Math.PI * 2 + (Math.random() - 0.5);
      const radius = 15 + Math.random() * 5;
      const x = Math.cos(angle) * radius;
      const z = Math.sin(angle) * radius;

      const tree = new pc.Entity("Tree");

      // Trunk
      const trunk = new pc.Entity("Trunk");
      trunk.addComponent("model", { type: "cylinder" });
      trunk.setLocalScale(0.5, 4, 0.5);
      trunk.setLocalPosition(0, 2, 0);
      const trunkMat = new pc.StandardMaterial();
      trunkMat.diffuse = new pc.Color(0.2, 0.15, 0.1);
      trunkMat.update();
      trunk.model.material = trunkMat;
      tree.addChild(trunk);

      // Leaves
      const leaves = new pc.Entity("Leaves");
      leaves.addComponent("model", { type: "cone" });
      leaves.setLocalScale(3, 4, 3);
      leaves.setLocalPosition(0, 4, 0);
      const leavesMat = new pc.StandardMaterial();
      leavesMat.diffuse = new pc.Color(0.05, 0.15, 0.05);
      leavesMat.update();
      leaves.model.material = leavesMat;
      tree.addChild(leaves);

      tree.setPosition(x, 0, z);
      this.app.root.addChild(tree);
    }
  }

  setPlayers(players) {
    this.players = players;

    // Clear existing
    this.playerEntities.forEach((entity) => entity.destroy());
    this.playerEntities.clear();

    const count = players.length;
    const radius = 8;

    players.forEach((player, index) => {
      const angle = (index / count) * Math.PI * 2;
      const x = Math.cos(angle) * radius;
      const z = Math.sin(angle) * radius;

      const entity = new pc.Entity(`Player-${player.id}`);

      // Body
      const body = new pc.Entity("Body");
      body.addComponent("model", { type: "capsule" });
      body.setLocalPosition(0, 1, 0);
      body.setLocalScale(0.8, 1.8, 0.8);

      const mat = new pc.StandardMaterial();
      if (player.ist_am_leben) {
        mat.diffuse = new pc.Color(0.8, 0.8, 0.8);
      } else {
        mat.diffuse = new pc.Color(0.3, 0.3, 0.3); // Dead color
        mat.opacity = 0.5;
        mat.blendType = pc.BLEND_NORMAL;
      }
      mat.update();
      body.model.material = mat;
      entity.addChild(body);

      // Name Tag (using Canvas texture or just 3D text if available, but simple plane for now)
      // For simplicity, we'll just use color coding or rely on HTML overlay for names
      // But let's add a "Head"
      const head = new pc.Entity("Head");
      head.addComponent("model", { type: "sphere" });
      head.setLocalPosition(0, 1.6, 0);
      head.setLocalScale(0.6, 0.6, 0.6);
      head.model.material = mat;
      entity.addChild(head);

      // Add collision for picking
      entity.addComponent("collision", {
        type: "box",
        halfExtents: new pc.Vec3(0.5, 1, 0.5),
      });
      // Note: collision needs rigid body usually, or we use bounding box raycast manually
      // We'll use manual bounding box check for simplicity in setupInput

      entity.setPosition(x, 0, z);
      entity.lookAt(0, 0, 0);

      // Store data
      entity.playerData = player;

      this.app.root.addChild(entity);
      this.playerEntities.set(player.id, entity);
    });
  }

  setTimeOfDay(isNight) {
    this.isNight = isNight;

    if (isNight) {
      // Night settings
      this.light.light.color = new pc.Color(0.2, 0.3, 0.5); // Moonlight
      this.light.light.intensity = 0.4;
      this.app.scene.ambientLight = new pc.Color(0.05, 0.05, 0.1);
      this.app.scene.fogColor = new pc.Color(0.05, 0.05, 0.1);
      this.app.scene.fogDensity = 0.05;
      this.fireLight.enabled = true;
    } else {
      // Day settings
      this.light.light.color = new pc.Color(1, 0.95, 0.8); // Sunlight
      this.light.light.intensity = 1.0;
      this.app.scene.ambientLight = new pc.Color(0.4, 0.4, 0.4);
      this.app.scene.fogColor = new pc.Color(0.6, 0.7, 0.8);
      this.app.scene.fogDensity = 0.01;
      this.fireLight.enabled = false; // Fire less visible during day
    }
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
        this.cameraHeight = pc.math.clamp(this.cameraHeight, 5, 30);

        lastMouseX = event.x;
        lastMouseY = event.y;
      }
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
        if (isDragging) {
          const touch = event.touches[0];
          const dx = touch.x - lastMouseX;
          const dy = touch.y - lastMouseY;

          this.cameraAngle -= dx * 0.01;
          this.cameraHeight += dy * 0.05;
          this.cameraHeight = pc.math.clamp(this.cameraHeight, 5, 30);

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
      const radius = 1.5; // Approximate radius

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
      this.fireLight.light.intensity = 2 + Math.random() * 0.5;

      // Animate particles
      this.fireParticles.forEach((p) => {
        p.life += dt * p.speed;
        if (p.life > 1) p.life = 0;

        const y = p.life * 3;
        const scale = (1 - p.life) * 0.5;

        p.entity.setLocalPosition(
          Math.sin(p.life * 10 + p.offset) * 0.2,
          y,
          Math.cos(p.life * 10 + p.offset) * 0.2,
        );
        p.entity.setLocalScale(scale, scale, scale);
        p.entity.lookAt(this.camera.getPosition());
        p.entity.rotateLocal(90, 0, 0); // Adjust for plane orientation
      });
    }
  }
}
