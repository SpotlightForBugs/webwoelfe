/**
 * Minimal PlayCanvas-compatible shim implemented on top of Three.js.
 *
 * Goal: keep the existing Village3D implementation working while removing the
 * PlayCanvas runtime dependency. Templates load Three.js via CDN which exposes
 * a global `THREE`.
 */

import type * as THREE_NS from 'three';

type Listener = (...args: any[]) => void;

class Emitter {
  private listeners: Map<string, Set<Listener>> = new Map();

  on(event: string, cb: Listener, scope?: unknown): void {
    const bound = scope ? cb.bind(scope) : cb;
    const set = this.listeners.get(event) ?? new Set<Listener>();
    set.add(bound);
    this.listeners.set(event, set);
  }

  off(event: string, cb: Listener): void {
    this.listeners.get(event)?.delete(cb);
  }

  emit(event: string, ...args: any[]): void {
    this.listeners.get(event)?.forEach((cb) => cb(...args));
  }
}

export const FILLMODE_NONE = 0;
export const RESOLUTION_AUTO = 0;

export const BLEND_NORMAL = 0;
export const BLEND_ADDITIVE = 1;

export const CULLFACE_NONE = 0;
export const CULLFACE_BACK = 1;
export const CULLFACE_FRONT = 2;

export const FOG_NONE = 0;
export const FOG_LINEAR = 1;
export const FOG_EXP2 = 2;

export const KEY_R = 82;
export const KEY_F = 70;

function getTHREE(): typeof THREE_NS {
  const three = (window as any).THREE as typeof THREE_NS | undefined;
  if (!three) {
    throw new Error('[Village3D] Three.js is not loaded (window.THREE missing)');
  }
  return three;
}

export class Color {
  r: number;
  g: number;
  b: number;

  constructor(r = 0, g = 0, b = 0) {
    this.r = r;
    this.g = g;
    this.b = b;
  }

  toThree(): THREE_NS.Color {
    const THREE = getTHREE();
    return new THREE.Color(this.r, this.g, this.b);
  }
}

export class Vec3 {
  x: number;
  y: number;
  z: number;

  constructor(x = 0, y = 0, z = 0) {
    this.x = x;
    this.y = y;
    this.z = z;
  }

  copy(v: Vec3): Vec3 {
    this.x = v.x;
    this.y = v.y;
    this.z = v.z;
    return this;
  }

  set(x: number, y: number, z: number): Vec3 {
    this.x = x;
    this.y = y;
    this.z = z;
    return this;
  }

  add(v: Vec3): Vec3 {
    this.x += v.x;
    this.y += v.y;
    this.z += v.z;
    return this;
  }

  sub2(a: Vec3, b: Vec3): Vec3 {
    this.x = a.x - b.x;
    this.y = a.y - b.y;
    this.z = a.z - b.z;
    return this;
  }

  scale(s: number): Vec3 {
    this.x *= s;
    this.y *= s;
    this.z *= s;
    return this;
  }

  dot(v: Vec3): number {
    return this.x * v.x + this.y * v.y + this.z * v.z;
  }

  normalize(): Vec3 {
    const len = Math.sqrt(this.x * this.x + this.y * this.y + this.z * this.z);
    if (len > 1e-8) {
      this.x /= len;
      this.y /= len;
      this.z /= len;
    }
    return this;
  }

  clone(): Vec3 {
    return new Vec3(this.x, this.y, this.z);
  }
}

export class Texture {
  private texture: THREE_NS.Texture | null = null;

  // graphicsDevice is accepted for API compatibility; unused.
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  constructor(_graphicsDevice?: unknown) {}

  setSource(source: HTMLCanvasElement | HTMLImageElement): void {
    const THREE = getTHREE();
    if (source instanceof HTMLCanvasElement) {
      this.texture = new THREE.CanvasTexture(source);
    } else {
      this.texture = new THREE.Texture(source);
      this.texture.needsUpdate = true;
    }
  }

  get threeTexture(): THREE_NS.Texture | null {
    return this.texture;
  }
}

export class StandardMaterial {
  diffuse: Color = new Color(1, 1, 1);
  emissive: Color = new Color(0, 0, 0);
  specular: Color = new Color(0.1, 0.1, 0.1);
  emissiveIntensity: number = 1;

  diffuseMap: Texture | null = null;
  emissiveMap: Texture | null = null;

  opacity: number = 1;
  blendType: number = BLEND_NORMAL;
  useLighting: boolean = true;
  cull: number = CULLFACE_BACK;
  depthWrite: boolean = true;
  shininess: number = 30;

  private threeMaterial: THREE_NS.Material | null = null;
  private boundMeshes: Set<THREE_NS.Mesh> = new Set();

  bind(mesh: THREE_NS.Mesh): void {
    this.boundMeshes.add(mesh);
    if (this.threeMaterial) {
      mesh.material = this.threeMaterial;
    }
  }

  update(): void {
    const THREE = getTHREE();

    const prev = this.threeMaterial;
    const wantsBasic = !this.useLighting;

    let next: THREE_NS.Material;
    if (wantsBasic) {
      const mat = new THREE.MeshBasicMaterial();
      mat.color = this.diffuse.toThree();
      mat.opacity = this.opacity;
      mat.transparent = this.opacity < 1;
      mat.depthWrite = this.depthWrite;
      if (this.diffuseMap?.threeTexture) {
        mat.map = this.diffuseMap.threeTexture;
        mat.map.needsUpdate = true;
      }
      next = mat;
    } else {
      const mat = new THREE.MeshStandardMaterial();
      mat.color = this.diffuse.toThree();
      mat.emissive = this.emissive.toThree();
      mat.emissiveIntensity = this.emissiveIntensity;
      mat.opacity = this.opacity;
      mat.transparent = this.opacity < 1;
      mat.depthWrite = this.depthWrite;
      // Rough shininess mapping (best-effort)
      const rough = Math.max(0.05, Math.min(1, 1 - this.shininess / 100));
      mat.roughness = rough;
      mat.metalness = 0;
      if (this.diffuseMap?.threeTexture) {
        mat.map = this.diffuseMap.threeTexture;
        mat.map.needsUpdate = true;
      }
      if (this.emissiveMap?.threeTexture) {
        mat.emissiveMap = this.emissiveMap.threeTexture;
        mat.emissiveMap.needsUpdate = true;
      }
      next = mat;
    }

    if (this.blendType === BLEND_ADDITIVE) {
      (next as any).blending = THREE.AdditiveBlending;
      (next as any).transparent = true;
    } else {
      (next as any).blending = THREE.NormalBlending;
    }

    if (this.cull === CULLFACE_NONE) {
      (next as any).side = THREE.DoubleSide;
    } else if (this.cull === CULLFACE_FRONT) {
      // PlayCanvas FRONT culling means render inside of geometry.
      (next as any).side = THREE.BackSide;
    } else {
      (next as any).side = THREE.FrontSide;
    }

    (next as any).needsUpdate = true;
    this.threeMaterial = next;

    this.boundMeshes.forEach((m) => {
      m.material = next;
    });

    if (prev && prev !== next) {
      prev.dispose();
    }
  }

  get _three(): THREE_NS.Material | null {
    return this.threeMaterial;
  }
}

export class ModelComponent {
  readonly mesh: THREE_NS.Mesh;
  private currentMaterial: StandardMaterial | null = null;

  constructor(mesh: THREE_NS.Mesh) {
    this.mesh = mesh;
  }

  set material(mat: StandardMaterial) {
    this.currentMaterial = mat;
    mat.bind(this.mesh);
    mat.update();
  }

  get material(): StandardMaterial {
    if (!this.currentMaterial) {
      // Provide a usable material wrapper if something tries to read it before assignment.
      this.currentMaterial = new StandardMaterial();
      this.currentMaterial.bind(this.mesh);
      this.currentMaterial.update();
    }
    return this.currentMaterial;
  }
}

export class CameraComponent {
  readonly camera: THREE_NS.PerspectiveCamera;
  nearClip: number;
  farClip: number;

  constructor(canvas: HTMLCanvasElement, opts: { farClip?: number } = {}) {
    const THREE = getTHREE();
    const aspect = canvas.clientWidth > 0 && canvas.clientHeight > 0
      ? canvas.clientWidth / canvas.clientHeight
      : 1;
    this.nearClip = 0.1;
    this.farClip = opts.farClip ?? 1000;
    this.camera = new THREE.PerspectiveCamera(60, aspect, this.nearClip, this.farClip);
  }

  screenToWorld(x: number, y: number, distance: number, canvas?: HTMLCanvasElement): Vec3 {
    const THREE = getTHREE();
    const c = canvas ?? ((window as any).__village3d_canvas as HTMLCanvasElement | undefined);
    if (!c) {
      return new Vec3(0, 0, 0);
    }

    const rect = c.getBoundingClientRect();
    const w = rect.width || 1;
    const h = rect.height || 1;
    const ndcX = (x / w) * 2 - 1;
    const ndcY = -(y / h) * 2 + 1;

    const origin = new THREE.Vector3();
    this.camera.getWorldPosition(origin);

    const target = new THREE.Vector3(ndcX, ndcY, 0.5).unproject(this.camera);
    const dir = target.sub(origin).normalize();
    const p = origin.add(dir.multiplyScalar(distance));

    return new Vec3(p.x, p.y, p.z);
  }
}

export class LightComponent {
  readonly light: THREE_NS.Light;

  constructor(type: string, color: Color, intensity: number) {
    const THREE = getTHREE();
    if (type === 'directional') {
      this.light = new THREE.DirectionalLight(color.toThree(), intensity);
      (this.light as THREE_NS.DirectionalLight).castShadow = true;
    } else if (type === 'point') {
      this.light = new THREE.PointLight(color.toThree(), intensity, 100);
    } else {
      this.light = new THREE.AmbientLight(color.toThree(), intensity);
    }
  }

  get color(): Color {
    const c: any = (this.light as any).color;
    if (!c) return new Color(1, 1, 1);
    return new Color(c.r, c.g, c.b);
  }

  set color(v: Color) {
    const c: any = (this.light as any).color;
    if (!c) return;
    const t = v.toThree();
    c.set(t);
  }

  get intensity(): number {
    return (this.light as any).intensity ?? 1;
  }

  set intensity(v: number) {
    (this.light as any).intensity = v;
  }
}

function degToRad(deg: number): number {
  return (deg * Math.PI) / 180;
}

export class Entity {
  readonly name: string;
  readonly object: THREE_NS.Object3D;

  model?: ModelComponent;
  camera?: CameraComponent;
  light?: LightComponent;

  parent: Entity | null = null;

  get children(): Entity[] {
    const kids: Entity[] = [];
    (this.object.children || []).forEach((child: any) => {
      const e = child?.userData?.__pc_entity as Entity | undefined;
      if (e) kids.push(e);
    });
    return kids;
  }

  get enabled(): boolean {
    return this.object.visible;
  }

  set enabled(v: boolean) {
    this.object.visible = v;
  }

  constructor(name: string, object?: THREE_NS.Object3D) {
    this.name = name;
    const THREE = getTHREE();
    this.object = object ?? new THREE.Object3D();
    this.object.name = name;
    (this.object as any).userData.__pc_entity = this;
  }

  addComponent(type: 'model' | 'camera' | 'light' | 'element', opts: any): void {
    const THREE = getTHREE();

    if (type === 'model') {
      const modelType = opts?.type as string;
      let geom: THREE_NS.BufferGeometry;

      switch (modelType) {
        case 'box':
          geom = new THREE.BoxGeometry(1, 1, 1);
          break;
        case 'sphere':
          geom = new THREE.SphereGeometry(0.5, 16, 16);
          break;
        case 'cylinder':
          geom = new THREE.CylinderGeometry(0.5, 0.5, 1, 16);
          break;
        case 'cone':
          geom = new THREE.ConeGeometry(0.5, 1, 16);
          break;
        case 'plane':
          geom = new THREE.PlaneGeometry(1, 1);
          break;
        case 'torus':
          geom = new THREE.TorusGeometry(0.5, 0.15, 12, 32);
          break;
        case 'capsule':
          // CapsuleGeometry exists in newer Three; fall back if missing.
          geom = (THREE as any).CapsuleGeometry
            ? new (THREE as any).CapsuleGeometry(0.35, 0.7, 8, 16)
            : new THREE.CylinderGeometry(0.35, 0.35, 1.4, 16);
          break;
        default:
          geom = new THREE.BoxGeometry(1, 1, 1);
      }

      const mat = new THREE.MeshStandardMaterial({ color: 0xffffff });
      const mesh = new THREE.Mesh(geom, mat);
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      this.object.add(mesh);
      this.model = new ModelComponent(mesh);
      return;
    }

    if (type === 'camera') {
      const canvas = (window as any).__village3d_canvas as HTMLCanvasElement | undefined;
      if (!canvas) {
        throw new Error('[Village3D] pc_shim: canvas not registered');
      }
      this.camera = new CameraComponent(canvas, { farClip: opts?.farClip });
      this.object.add(this.camera.camera);
      return;
    }

    if (type === 'light') {
      const lightType = opts?.type as string;
      const color = opts?.color as Color;
      const intensity = typeof opts?.intensity === 'number' ? opts.intensity : 1;
      const comp = new LightComponent(lightType, color ?? new Color(1, 1, 1), intensity);
      if (lightType === 'directional') {
        const dir = comp.light as THREE_NS.DirectionalLight;
        dir.castShadow = !!opts?.castShadows;
        if (opts?.shadowResolution) {
          dir.shadow.mapSize.set(opts.shadowResolution, opts.shadowResolution);
        }
      }
      this.light = comp;
      this.object.add(comp.light);
    }

    if (type === 'element') {
      // Minimal support for text labels.
      // We render text to a canvas and map it onto a plane.
      if (opts?.type !== 'text') return;

      const text: string = String(opts?.text ?? '');
      const fontSize = typeof opts?.fontSize === 'number' ? opts.fontSize : 0.5;
      const color: Color = opts?.color instanceof Color ? opts.color : new Color(1, 1, 1);

      const canvas = document.createElement('canvas');
      canvas.width = 512;
      canvas.height = 128;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = 'rgba(0,0,0,0.65)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      ctx.font = 'bold 64px Arial, sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      const css = `rgb(${Math.round(color.r * 255)}, ${Math.round(color.g * 255)}, ${Math.round(color.b * 255)})`;
      ctx.fillStyle = css;
      ctx.shadowColor = 'rgba(0,0,0,0.5)';
      ctx.shadowBlur = 4;
      ctx.shadowOffsetX = 2;
      ctx.shadowOffsetY = 2;
      ctx.fillText(text, canvas.width / 2, canvas.height / 2);

      const tex = new THREE.CanvasTexture(canvas);
      tex.needsUpdate = true;

      const geom = new THREE.PlaneGeometry(2 * fontSize * 3, fontSize * 3);
      const mat = new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false });
      const mesh = new THREE.Mesh(geom, mat);
      mesh.renderOrder = 999;
      this.object.add(mesh);
      return;
    }
  }

  addChild(child: Entity): void {
    child.parent = this;
    this.object.add(child.object);
  }

  findByName(name: string): Entity | null {
    let found: Entity | null = null;
    this.object.traverse((o: any) => {
      if (found) return;
      if (o?.name === name) {
        const e = o?.userData?.__pc_entity as Entity | undefined;
        found = e ?? null;
      }
    });
    return found;
  }

  destroy(): void {
    if (this.object.parent) {
      this.object.parent.remove(this.object);
    }

    this.object.traverse((o: any) => {
      if (o.isMesh) {
        if (o.geometry?.dispose) o.geometry.dispose();
        const material = o.material;
        if (Array.isArray(material)) {
          material.forEach((m) => m?.dispose?.());
        } else {
          material?.dispose?.();
        }
      }
    });
  }

  setLocalScale(x: number, y: number, z: number): void {
    this.object.scale.set(x, y, z);
  }

  setLocalPosition(x: number, y: number, z: number): void {
    this.object.position.set(x, y, z);
  }

  setLocalEulerAngles(x: number, y: number, z: number): void {
    this.object.rotation.set(degToRad(x), degToRad(y), degToRad(z));
  }

  rotateLocal(x: number, y: number, z: number): void {
    this.object.rotateX(degToRad(x));
    this.object.rotateY(degToRad(y));
    this.object.rotateZ(degToRad(z));
  }

  setPosition(x: number | Vec3, y?: number, z?: number): void {
    if (x instanceof Vec3) {
      this.object.position.set(x.x, x.y, x.z);
      return;
    }
    this.object.position.set(x, y ?? 0, z ?? 0);
  }

  setEulerAngles(x: number, y: number, z: number): void {
    this.object.rotation.set(degToRad(x), degToRad(y), degToRad(z));
  }

  lookAt(x: number | Vec3, y?: number, z?: number): void {
    const THREE = getTHREE();
    if (x instanceof Vec3) {
      this.object.lookAt(new THREE.Vector3(x.x, x.y, x.z));
      return;
    }
    this.object.lookAt(x, y ?? 0, z ?? 0);
  }

  getPosition(): Vec3 {
    const THREE = getTHREE();
    const v = new THREE.Vector3();
    this.object.getWorldPosition(v);
    return new Vec3(v.x, v.y, v.z);
  }

  getEulerAngles(): { x: number; y: number; z: number } {
    const r = this.object.rotation;
    return {
      x: (r.x * 180) / Math.PI,
      y: (r.y * 180) / Math.PI,
      z: (r.z * 180) / Math.PI,
    };
  }
}

class SceneFacade {
  private ambient: THREE_NS.AmbientLight;
  private fogType: number = FOG_NONE;

  constructor(private readonly scene: THREE_NS.Scene) {
    const THREE = getTHREE();
    this.ambient = new THREE.AmbientLight(new THREE.Color(0.15, 0.15, 0.2), 1);
    scene.add(this.ambient);
  }

  set ambientLight(c: Color) {
    this.ambient.color = c.toThree();
  }

  get ambientLight(): Color {
    const col = this.ambient.color;
    return new Color(col.r, col.g, col.b);
  }

  get fog(): unknown {
    return this.fogType;
  }

  set fog(value: unknown) {
    const THREE = getTHREE();
    const v = value as number;
    this.fogType = v;
    if (v === FOG_NONE) {
      this.scene.fog = null;
    } else if (v === FOG_EXP2) {
      this.scene.fog = new THREE.FogExp2(new THREE.Color(0.02, 0.03, 0.08), 0.02);
    } else if (v === FOG_LINEAR) {
      this.scene.fog = new THREE.Fog(new THREE.Color(0.02, 0.03, 0.08), 10, 80);
    }
  }
}

export class Keyboard extends Emitter {
  constructor(target: Window) {
    super();
    target.addEventListener('keydown', (e) => {
      this.emit('keydown', { key: e.keyCode });
    });
  }
}

export class Mouse {}
export class TouchDevice {}
export class ElementInput {}

export class Application extends Emitter {
  readonly renderer: THREE_NS.WebGLRenderer;
  readonly threeScene: THREE_NS.Scene;
  readonly root: Entity;
  readonly scene: SceneFacade;
  readonly keyboard: Keyboard;

  readonly graphicsDevice: unknown;

  private running: boolean = false;
  private lastFrameAt: number = 0;

  constructor(canvas: HTMLCanvasElement, _opts: any) {
    super();

    (window as any).__village3d_canvas = canvas;

    const THREE = getTHREE();
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false });
    this.renderer.setPixelRatio(window.devicePixelRatio || 1);
    this.renderer.setSize(canvas.clientWidth || 1, canvas.clientHeight || 1, false);
    this.renderer.shadowMap.enabled = true;

    this.threeScene = new THREE.Scene();
    this.root = new Entity('Root', this.threeScene as any);
    this.scene = new SceneFacade(this.threeScene);

    this.keyboard = new Keyboard(window);

    // API compatibility placeholder
    this.graphicsDevice = {};
  }

  start(): void {
    if (this.running) return;
    this.running = true;
    this.lastFrameAt = performance.now();

    const tick = (now: number) => {
      if (!this.running) return;
      const dt = Math.max(0, (now - this.lastFrameAt) / 1000);
      this.lastFrameAt = now;

      this.emit('update', dt);

      const camera = this.findActiveCamera();
      if (camera) {
        this.renderer.render(this.threeScene, camera);
      }

      requestAnimationFrame(tick);
    };

    requestAnimationFrame(tick);
  }

  private findActiveCamera(): THREE_NS.PerspectiveCamera | null {
    let found: THREE_NS.PerspectiveCamera | null = null;
    this.threeScene.traverse((o: any) => {
      if (found) return;
      if (o.isPerspectiveCamera) {
        found = o as THREE_NS.PerspectiveCamera;
      }
    });
    return found;
  }

  setCanvasFillMode(_mode: number): void {}
  setCanvasResolution(_mode: number): void {}

  resizeCanvas(): void {
    const canvas = this.renderer.domElement;
    const rect = canvas.getBoundingClientRect();
    this.renderer.setSize(rect.width || 1, rect.height || 1, false);

    const camera = this.findActiveCamera();
    if (camera) {
      camera.aspect = (rect.width || 1) / (rect.height || 1);
      camera.updateProjectionMatrix();
    }
  }

  destroy(): void {
    this.running = false;
    this.renderer.dispose();
  }
}

// Install shim as window.pc if not already present.
export function ensurePcShim(): void {
  const w = window as any;
  if (w.pc) return;

  w.pc = {
    Application,
    Entity,
    Color,
    Vec3,
    Texture,
    StandardMaterial,
    ModelComponent,
    CameraComponent,
    LightComponent,

    Mouse,
    TouchDevice,
    ElementInput,
    Keyboard,

    // constants
    FILLMODE_NONE,
    RESOLUTION_AUTO,

    BLEND_NORMAL,
    BLEND_ADDITIVE,

    CULLFACE_NONE,
    CULLFACE_BACK,
    CULLFACE_FRONT,

    FOG_NONE,
    FOG_LINEAR,
    FOG_EXP2,

    KEY_R,
    KEY_F,
  };
}

ensurePcShim();
