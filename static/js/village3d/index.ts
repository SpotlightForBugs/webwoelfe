/**
 * Village3D Module Entry Point
 *
 * Export all public interfaces and classes
 */

export { default as Village3DPlayCanvas } from "./Village3DPlayCanvas.js";
export { PlayerAvatarBuilder } from "./PlayerAvatarBuilder.js";
export { AppearanceFeatureRenderer } from "./AppearanceFeatureRenderer.js";

// Export types
export type {
  PlayerData,
  PlayerEntity,
  RoleModel,
  RoleData,
  AppearanceFeature,
  Village3DOptions,
  VisualEffect,
  BodyModification,
  AnimationState,
  RolesAPIResponse,
} from "./types";
