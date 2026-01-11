/**
 * Village3D Module Entry Point
 * 
 * Export all public interfaces and classes
 */

export { default as Village3DPlayCanvas } from './Village3DPlayCanvas';
export { PlayerAvatarBuilder } from './PlayerAvatarBuilder';
export { AppearanceFeatureRenderer } from './AppearanceFeatureRenderer';

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
} from './types';
