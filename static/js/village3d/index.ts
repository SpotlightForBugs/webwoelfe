/**
 * Village3D Module Entry Point
 * 
 * Export all public interfaces and classes
 */

export { default as Village3DThree } from './Village3DThree.js';
export { PlayerAvatarBuilder } from './PlayerAvatarBuilder.js';
export { AppearanceFeatureRenderer } from './AppearanceFeatureRenderer.js';
export { PlayerHouseBuilder } from './PlayerHouseBuilder.js';
export { VillageEnhancementManager } from './VillageEnhancements.js';
export { VillageIntegration } from './VillageIntegration.js';

// Export types
export type {
  PlayerData,
  PlayerEntity,
  RoleModel,
  RoleData,
  AppearanceFeature,
  Village3DOptions,
  ViewMode,
  VisualEffect,
  BodyModification,
  AnimationState,
  RolesAPIResponse,
} from './types';

export type {
  PlayerHouseConfig,
  PlayerHouseEntity,
} from './PlayerHouseBuilder.js';

export type {
  CharacterMovementState,
  PhaseTransition,
  PhaseEffect,
  VotingMarker3D,
  PhaseDisplayInfo,
  EliminationEvent,
  GameEndEvent,
  HouseConfig,
} from './VillageEnhancements.js';
