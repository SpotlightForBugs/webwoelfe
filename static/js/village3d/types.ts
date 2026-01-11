/**
 * Type definitions for Village3D PlayCanvas renderer
 */

import * as pc from "playcanvas";

// Re-export PlayCanvas types for convenience
export type PCApplication = pc.Application;
export type PCEntity = pc.Entity;
export type PCColor = pc.Color;
export type PCVec3 = pc.Vec3;
export type PCMaterial = pc.StandardMaterial;
export type PCCamera = pc.CameraComponent;
export type PCLight = pc.LightComponent;
export type PCElement = pc.ElementComponent;
export type PCScene = pc.Scene;
export type PCMeshInstance = pc.MeshInstance;

// Extended ModelComponent interface to include material property
// which exists at runtime for convenience (sets material on all mesh instances)
export interface PCModel extends pc.ModelComponent {
  material: PCMaterial;
}

// ============================================================================
// Player and Game Data Types
// ============================================================================

export interface PlayerData {
  id: number;
  name: string;
  rolle: string;
  ist_am_leben: boolean;
  ist_erzaehler: boolean;
  verliebt_mit?: number;
  visual_effects?: VisualEffect[];
  [key: string]: string | number | boolean | VisualEffect[] | undefined;
}

export interface VisualEffect {
  type: string;
  icon?: string;
  color?: string;
  animation?: string;
  tooltip?: string;
}

// ============================================================================
// Role Model Types
// ============================================================================

export interface AppearanceFeature {
  feature_type: string;
  geometry:
    | "box"
    | "sphere"
    | "cylinder"
    | "cone"
    | "capsule"
    | "torus"
    | "plane";
  position?: { x: number; y: number; z: number };
  scale?: { x: number; y: number; z: number };
  rotation?: { x: number; y: number; z: number };
  mirror_x?: boolean;
  mirror_offset?: number;
  color_source?: "role" | "custom" | "skin" | "dark" | "emissive" | "gradient";
  custom_color?: string;
  secondary_color?: string;
  opacity?: number;
  emissive?: boolean;
  emissive_intensity?: number;
  metallic?: boolean;
  roughness?: number;
  animation?: string;
  animation_speed?: number;
  animation_amplitude?: number;
  particle_effect?: string;
  particle_color?: string;
  particle_rate?: number;
  light_source?: boolean;
  light_color?: string;
  light_intensity?: number;
  light_range?: number;
  count?: number;
  count_arrangement?: string;
  count_spacing?: number;
  visible_to_self?: boolean;
  visible_to_others?: boolean;
  visible_to_seher?: boolean;
  visible_when_dead?: boolean;
  description?: string;
}

export interface BodyModification {
  type: string;
  modifications: Record<string, unknown>;
}

export interface AnimationState {
  name: string;
  duration: number;
  loop: boolean;
}

export interface RoleModel {
  modell_id: string;
  anzeige_name: string;
  beschreibung: string;
  appearance_self_alive: AppearanceFeature[];
  appearance_others_alive: AppearanceFeature[];
  appearance_dead: AppearanceFeature[];
  appearance_seher_view?: AppearanceFeature[];
  animations?: Record<string, AnimationState>;
  hint_effects?: string[];
  seher_sicht: "good" | "bad" | "neutral" | string;
  body?: BodyModification;
  sound_on_action?: string;
  sound_on_death?: string;
  sound_ambient?: string;
}

export interface RoleData {
  name: string;
  farbe: string;
  model?: RoleModel;
}

// ============================================================================
// PlayCanvas Entity Extensions
// ============================================================================

export interface PlayerEntityData {
  id: number;
  name: string;
  rolle: string;
  ist_am_leben: boolean;
}

export interface PlayerEntity extends PCEntity {
  playerData: PlayerData;
  parts: {
    torso?: PCEntity;
    head?: PCEntity;
    arms?: PCEntity[];
    legs?: PCEntity[];
  };
  animState: {
    time: number;
    idleSpeed: number;
  };
}

// Entity with hint animation data
export interface HintEntity extends PCEntity {
  hintTime?: number;
  hintType?: string;
}

// Entity with animation callback
export interface AnimatedEntity extends PCEntity {
  animateCallback?: (dt: number) => void;
}

// Entity with pulse animation data
export interface PulseEntity extends PCEntity {
  pulseTime?: number;
}

// ============================================================================
// Building and Scene Types
// ============================================================================

export interface BuildingData {
  entity: PCEntity;
  type: "house" | "church" | "well" | "campfire";
  position: PCVec3;
  bounds?: {
    minX: number;
    maxX: number;
    minZ: number;
    maxZ: number;
  };
}

export interface ParticleData {
  entity: PCEntity;
  velocity: PCVec3;
  lifetime: number;
  type: "fire" | "fog" | "sparks";
}

// ============================================================================
// Camera and Control Types
// ============================================================================

export interface CameraState {
  angle: number;
  height: number;
  radius: number;
  target: PCVec3;
}

export interface InputState {
  isMouseDown: boolean;
  lastMouseX: number;
  lastMouseY: number;
  mouseDownX: number;
  mouseDownY: number;
  isDragging: boolean;
}

// ============================================================================
// Material Cache Types
// ============================================================================

export interface MaterialOptions {
  name: string;
  diffuse: PCColor;
  specular?: PCColor;
  emissive?: PCColor;
  opacity?: number;
  metalness?: number;
  gloss?: number;
}

// ============================================================================
// Options and Configuration
// ============================================================================

export interface Village3DOptions {
  lobbyMode?: boolean;
  onPlayerClick?: (playerId: number) => void;
}

// ============================================================================
// UI Overlay Types
// ============================================================================

export interface UIButtonData {
  label?: string;
  text?: string; // Alternative to label
  action: string | (() => void);
  icon?: string;
  color?: string;
  onClick?: () => void;
  disabled?: boolean;
  title?: string;
}

// ============================================================================
// API Response Types
// ============================================================================

export interface RolesAPIResponse {
  success: boolean;
  roles: RoleData[];
  grouped_by_extension?: Record<string, RoleData[]>;
  total_count?: number;
}
