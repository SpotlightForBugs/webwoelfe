/**
 * AppearanceFeatureRenderer - Renders role-specific appearance features
 * Handles custom accessories, body modifications, and visual effects from role definitions
 */

import './pc_shim.js';

import type { AppearanceFeature, PlayerData, PlayerEntity, PCColor, PCMaterial, PCEntity, PCModel } from './types.js';

export class AppearanceFeatureRenderer {
  private materialCache: Map<string, PCMaterial>;

  constructor(materialCache: Map<string, PCMaterial>) {
    this.materialCache = materialCache;
  }

  /**
   * Apply appearance features from role model definition to player entity
   */
  applyAppearanceFeatures(
    playerEntity: PlayerEntity,
    appearanceFeatures: AppearanceFeature[],
    baseColor: PCColor,
    playerData: PlayerData
  ): void {
    if (!appearanceFeatures || !Array.isArray(appearanceFeatures)) {
      return;
    }

    console.log(`[Village3D] Applying ${appearanceFeatures.length} appearance features for ${playerData.rolle}`);

    appearanceFeatures.forEach((feature, index) => {
      try {
        this.renderFeature(playerEntity, feature, index, baseColor, playerData);
      } catch (error) {
        console.error(`[Village3D] Failed to apply appearance feature:`, error, feature);
      }
    });
  }

  /**
   * Render a single appearance feature
   */
  private renderFeature(
    playerEntity: PlayerEntity,
    feature: AppearanceFeature,
    index: number,
    baseColor: PCColor,
    playerData: PlayerData
  ): void {
    const pc = window.pc;
    const featureEntity = new pc.Entity(`Feature-${feature.feature_type}-${index}`);
    
    // Determine geometry type
    const geometryType = this.validateGeometryType(feature.geometry);
    featureEntity.addComponent('model', { type: geometryType });
    
    // Apply transformations
    this.applyPosition(featureEntity, feature);
    this.applyScale(featureEntity, feature);
    this.applyRotation(featureEntity, feature);
    
    // Apply material
    const featureColor = this.determineColor(feature, baseColor);
    const material = this.createMaterial(feature, featureColor, playerData, index);
    (featureEntity.model as PCModel).material = material;
    
    // Add to player entity
    playerEntity.addChild(featureEntity);
    
    console.log(`[Village3D] Added ${feature.feature_type} feature: ${feature.description || 'no description'}`);
  }

  /**
   * Validate and normalize geometry type
   */
  private validateGeometryType(geometry: string): string {
    const validTypes = ['box', 'sphere', 'cylinder', 'cone', 'capsule'];
    if (!validTypes.includes(geometry)) {
      console.warn(`[Village3D] Unknown geometry type: ${geometry}, using box`);
      return 'box';
    }
    return geometry;
  }

  /**
   * Apply position to feature entity
   */
  private applyPosition(entity: PCEntity, feature: AppearanceFeature): void {
    if (feature.position) {
      entity.setLocalPosition(
        feature.position.x || 0,
        feature.position.y || 0,
        feature.position.z || 0
      );
    }
  }

  /**
   * Apply scale to feature entity
   */
  private applyScale(entity: PCEntity, feature: AppearanceFeature): void {
    if (feature.scale) {
      entity.setLocalScale(
        feature.scale.x || 1,
        feature.scale.y || 1,
        feature.scale.z || 1
      );
    }
  }

  /**
   * Apply rotation to feature entity
   */
  private applyRotation(entity: PCEntity, feature: AppearanceFeature): void {
    if (feature.rotation) {
      entity.setLocalEulerAngles(
        feature.rotation.x || 0,
        feature.rotation.y || 0,
        feature.rotation.z || 0
      );
    }
  }

  /**
   * Determine color based on color source
   */
  private determineColor(feature: AppearanceFeature, baseColor: PCColor): PCColor {
    const pc = window.pc;
    
    switch (feature.color_source) {
      case 'role':
        return baseColor;
      
      case 'custom':
        if (feature.custom_color) {
          return this.parseColor(feature.custom_color);
        }
        return baseColor;
      
      case 'skin':
        return new pc.Color(0.95, 0.8, 0.7);
      
      case 'dark':
        return new pc.Color(0.2, 0.2, 0.2);
      
      default:
        return baseColor;
    }
  }

  /**
   * Parse color from string or object
   */
  private parseColor(color: string | { r: number; g: number; b: number }): PCColor {
    const pc = window.pc;
    
    if (typeof color === 'string' && color.startsWith('#')) {
      const r = parseInt(color.slice(1, 3), 16) / 255;
      const g = parseInt(color.slice(3, 5), 16) / 255;
      const b = parseInt(color.slice(5, 7), 16) / 255;
      return new pc.Color(r, g, b);
    } else if (typeof color === 'object' && color.r !== undefined) {
      return new pc.Color(color.r, color.g, color.b);
    }
    
    return new pc.Color(0.5, 0.5, 0.5);
  }

  /**
   * Create material for feature
   */
  private createMaterial(
    feature: AppearanceFeature,
    featureColor: PCColor,
    playerData: PlayerData,
    index: number
  ): PCMaterial {
    const pc = window.pc;
    
    // Calculate emissive color
    const emissiveColor = feature.emissive && (feature.emissive_intensity ?? 0) > 0
      ? new pc.Color(
          featureColor.r * (feature.emissive_intensity ?? 0.5),
          featureColor.g * (feature.emissive_intensity ?? 0.5),
          featureColor.b * (feature.emissive_intensity ?? 0.5)
        )
      : new pc.Color(0, 0, 0);
    
    return this.getMaterial({
      name: `Feature-${playerData.id}-${feature.feature_type}-${index}`,
      diffuse: featureColor,
      specular: new pc.Color(0.1, 0.1, 0.1),
      emissive: emissiveColor,
    });
  }

  /**
   * Get or create cached material
   */
  private getMaterial(options: {
    name: string;
    diffuse: PCColor;
    specular?: PCColor;
    emissive?: PCColor;
    opacity?: number;
  }): PCMaterial {
    const cacheKey = `${options.name}-${options.diffuse.r}-${options.diffuse.g}-${options.diffuse.b}`;
    
    const cached = this.materialCache.get(cacheKey);
    if (cached) {
      return cached;
    }

    const pc = window.pc;
    const material = new pc.StandardMaterial();
    
    material.diffuse = options.diffuse;
    material.specular = options.specular || new pc.Color(0.1, 0.1, 0.1);
    material.emissive = options.emissive || new pc.Color(0, 0, 0);
    material.shininess = 30;
    
    if (options.opacity !== undefined && options.opacity < 1) {
      material.opacity = options.opacity;
      material.blendType = pc.BLEND_NORMAL;
    }
    
    material.update();
    this.materialCache.set(cacheKey, material);
    
    return material;
  }
}
