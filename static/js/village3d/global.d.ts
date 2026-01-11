/**
 * Global type declarations for Three.js runtime
 * Three.js is loaded at runtime via <script> tag and exposes itself on window.THREE
 */

import type * as THREE from 'three';
import type { Application, Entity, Color, Vec3, Texture, StandardMaterial, ModelComponent, CameraComponent, LightComponent } from './pc_shim.js';

type PcShim = {
  Application: typeof Application;
  Entity: typeof Entity;
  Color: typeof Color;
  Vec3: typeof Vec3;
  Texture: typeof Texture;
  StandardMaterial: typeof StandardMaterial;
  ModelComponent: typeof ModelComponent;
  CameraComponent: typeof CameraComponent;
  LightComponent: typeof LightComponent;

  Mouse: new (...args: any[]) => unknown;
  TouchDevice: new (...args: any[]) => unknown;
  ElementInput: new (...args: any[]) => unknown;
  Keyboard: new (...args: any[]) => unknown;

  FILLMODE_NONE: number;
  RESOLUTION_AUTO: number;

  BLEND_NORMAL: number;
  BLEND_ADDITIVE: number;

  CULLFACE_NONE: number;
  CULLFACE_BACK: number;
  CULLFACE_FRONT: number;

  FOG_NONE: number;
  FOG_LINEAR: number;
  FOG_EXP2: number;

  KEY_R: number;
  KEY_F: number;
};

declare global {
  interface Window {
    THREE: typeof THREE;
    pc: PcShim;
  }
}

export {};
