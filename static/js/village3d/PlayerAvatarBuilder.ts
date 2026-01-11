/**
 * PlayerAvatarBuilder - Builds 3D player avatars with role-specific appearances
 */

import "./pc_shim.js";

import type {
  PlayerData,
  PlayerEntity,
  RoleModel,
  PCEntity,
  PCColor,
  PCMaterial,
  PCModel,
} from "./types.js";
import { AppearanceFeatureRenderer } from "./AppearanceFeatureRenderer.js";

export class PlayerAvatarBuilder {
  private materialCache: Map<string, PCMaterial>;
  private roleColors: Record<string, PCColor>;
  private roleModels: Record<string, RoleModel>;
  private appearanceRenderer: AppearanceFeatureRenderer;

  constructor(
    materialCache: Map<string, PCMaterial>,
    roleColors: Record<string, PCColor>,
    roleModels: Record<string, RoleModel>,
  ) {
    this.materialCache = materialCache;
    this.roleColors = roleColors;
    this.roleModels = roleModels;
    this.appearanceRenderer = new AppearanceFeatureRenderer(materialCache);
  }

  /**
   * Create a complete 3D avatar for a player
   */
  createPlayerAvatar(
    player: PlayerData,
    x: number,
    z: number,
    angle: number,
  ): PlayerEntity {
    const pc = window.pc;
    const playerEntity = new pc.Entity(`Player-${player.id}`) as PlayerEntity;
    playerEntity.playerData = player;

    // Determine player color and model based on role
    const roleName = player.rolle || "default";
    const roleColor =
      this.roleColors[roleName] ||
      this.roleColors["default"] ||
      new pc.Color(0.3, 0.5, 0.8);
    const roleModel = this.roleModels[roleName];

    // Initialize parts container
    playerEntity.parts = {};

    // Create base body
    this.createBodyParts(playerEntity, player, roleColor);

    // Apply custom role model appearance features if available
    if (roleModel?.appearance_self_alive) {
      this.appearanceRenderer.applyAppearanceFeatures(
        playerEntity,
        roleModel.appearance_self_alive,
        roleColor,
        player,
      );
    }

    // Apply death effect if player is dead
    if (!player.ist_am_leben) {
      this.applyDeadEffect(playerEntity);
    }

    // Create name label
    const label = this.createPlayerLabel(player.name, player.ist_am_leben);
    label.setLocalPosition(0, 3.2, 0);
    playerEntity.addChild(label);

    // Position and rotation
    playerEntity.setPosition(x, 0, z);
    playerEntity.setLocalEulerAngles(0, -((angle * 180) / Math.PI) + 180, 0);

    // Animation state
    playerEntity.animState = {
      time: Math.random() * 10,
      idleSpeed: 0.8 + Math.random() * 0.4,
    };

    return playerEntity;
  }

  /**
   * Create basic body parts for humanoid avatar
   */
  private createBodyParts(
    playerEntity: PlayerEntity,
    player: PlayerData,
    roleColor: PCColor,
  ): void {
    const pc = window.pc;
    const isDorfbewohner = player.rolle === "Dorfbewohner";

    // Torso
    const torso = new pc.Entity("Torso");
    torso.addComponent("model", { type: "box" });
    torso.setLocalScale(0.6, 0.8, 0.35);
    torso.setLocalPosition(0, 1.3, 0);

    const torsoColor = isDorfbewohner
      ? new pc.Color(0.55, 0.4, 0.25)
      : roleColor;
    const torsoMat = this.getMaterial({
      name: `PlayerTorso-${player.id}`,
      diffuse: torsoColor,
      specular: new pc.Color(0.1, 0.1, 0.1),
    });
    (torso.model as PCModel).material = torsoMat;
    playerEntity.addChild(torso);
    playerEntity.parts.torso = torso;

    // Add white shirt layer for Dorfbewohner
    if (isDorfbewohner) {
      const shirt = new pc.Entity("Shirt");
      shirt.addComponent("model", { type: "box" });
      shirt.setLocalScale(0.58, 0.5, 0.33);
      shirt.setLocalPosition(0, -0.15, 0);

      const shirtMat = this.getMaterial({
        name: `PlayerShirt-${player.id}`,
        diffuse: new pc.Color(0.9, 0.88, 0.82),
        specular: new pc.Color(0.05, 0.05, 0.05),
      });
      (shirt.model as PCModel).material = shirtMat;
      torso.addChild(shirt);
    }

    // Head
    const head = new pc.Entity("Head");
    head.addComponent("model", { type: "sphere" });
    head.setLocalScale(0.45, 0.45, 0.45);
    head.setLocalPosition(0, 2.0, 0);

    const headMat = this.getMaterial({
      name: `PlayerHead-${player.id}`,
      diffuse: new pc.Color(0.95, 0.8, 0.7),
      specular: new pc.Color(0.05, 0.05, 0.05),
    });
    (head.model as PCModel).material = headMat;
    playerEntity.addChild(head);
    playerEntity.parts.head = head;

    // Add straw hat for Dorfbewohner
    if (isDorfbewohner) {
      this.addDorfbewohnerHat(head, player);
    }

    // Arms
    this.createArms(playerEntity, player, torsoMat, isDorfbewohner);

    // Legs
    this.createLegs(playerEntity, player, isDorfbewohner);

    // Add farming tool for Dorfbewohner
    if (isDorfbewohner) {
      this.addFarmingTool(playerEntity, player);
    }
  }

  /**
   * Create arms for avatar
   */
  private createArms(
    playerEntity: PlayerEntity,
    player: PlayerData,
    torsoMat: PCMaterial,
    isDorfbewohner: boolean,
  ): void {
    const pc = window.pc;
    playerEntity.parts.arms = [];

    for (let i = 0; i < 2; i++) {
      const side = i === 0 ? -1 : 1;
      const armPivot = new pc.Entity(`Arm-${i}`);
      armPivot.setLocalPosition(side * 0.4, 1.6, 0);

      const arm = new pc.Entity("ArmPart");
      arm.addComponent("model", { type: "box" });
      arm.setLocalScale(0.15, 0.6, 0.15);
      arm.setLocalPosition(0, -0.3, 0);

      if (isDorfbewohner) {
        const sleeveMat = this.getMaterial({
          name: `PlayerSleeve-${player.id}-${i}`,
          diffuse: new pc.Color(0.9, 0.88, 0.82),
          specular: new pc.Color(0.05, 0.05, 0.05),
        });
        (arm.model as PCModel).material = sleeveMat;
      } else {
        (arm.model as PCModel).material = torsoMat;
      }

      armPivot.addChild(arm);
      playerEntity.addChild(armPivot);
      playerEntity.parts.arms.push(armPivot);
    }
  }

  /**
   * Create legs for avatar
   */
  private createLegs(
    playerEntity: PlayerEntity,
    player: PlayerData,
    isDorfbewohner: boolean,
  ): void {
    const pc = window.pc;
    playerEntity.parts.legs = [];

    for (let i = 0; i < 2; i++) {
      const side = i === 0 ? -0.15 : 0.15;
      const leg = new pc.Entity(`Leg-${i}`);
      leg.addComponent("model", { type: "box" });
      leg.setLocalScale(0.2, 0.7, 0.2);
      leg.setLocalPosition(side, 0.55, 0);

      const legColor = isDorfbewohner
        ? new pc.Color(0.4, 0.3, 0.2)
        : new pc.Color(0.2, 0.2, 0.3);
      const legMat = this.getMaterial({
        name: `PlayerLeg-${player.id}-${i}`,
        diffuse: legColor,
        specular: new pc.Color(0.05, 0.05, 0.05),
      });
      (leg.model as PCModel).material = legMat;
      playerEntity.addChild(leg);
      playerEntity.parts.legs.push(leg);
    }
  }

  /**
   * Add straw hat for Dorfbewohner
   */
  private addDorfbewohnerHat(head: PCEntity, player: PlayerData): void {
    const pc = window.pc;

    const hat = new pc.Entity("StrawHat");
    hat.addComponent("model", { type: "cylinder" });
    hat.setLocalScale(0.6, 0.08, 0.6);
    hat.setLocalPosition(0, 0.4, 0);

    const hatMat = this.getMaterial({
      name: `PlayerHat-${player.id}`,
      diffuse: new pc.Color(0.8, 0.7, 0.4),
      specular: new pc.Color(0.05, 0.05, 0.05),
    });
    (hat.model as PCModel).material = hatMat;
    head.addChild(hat);

    const hatTop = new pc.Entity("HatTop");
    hatTop.addComponent("model", { type: "cone" });
    hatTop.setLocalScale(0.5, 0.25, 0.5);
    hatTop.setLocalPosition(0, 0.55, 0);
    (hatTop.model as PCModel).material = hatMat;
    head.addChild(hatTop);
  }

  /**
   * Add farming tool for Dorfbewohner
   */
  private addFarmingTool(playerEntity: PlayerEntity, player: PlayerData): void {
    const pc = window.pc;

    const handle = new pc.Entity("ToolHandle");
    handle.addComponent("model", { type: "cylinder" });
    handle.setLocalScale(0.05, 1.2, 0.05);
    handle.setLocalPosition(0.5, 1.2, 0);
    handle.setLocalEulerAngles(0, 0, -20);

    const handleMat = this.getMaterial({
      name: `ToolHandle-${player.id}`,
      diffuse: new pc.Color(0.4, 0.3, 0.2),
      specular: new pc.Color(0.05, 0.05, 0.05),
    });
    (handle.model as PCModel).material = handleMat;
    playerEntity.addChild(handle);

    const blade = new pc.Entity("ToolBlade");
    blade.addComponent("model", { type: "box" });
    blade.setLocalScale(0.3, 0.08, 0.08);
    blade.setLocalPosition(0.2, 0.5, 0);
    blade.setLocalEulerAngles(0, 0, 70);

    const bladeMat = this.getMaterial({
      name: `ToolBlade-${player.id}`,
      diffuse: new pc.Color(0.5, 0.5, 0.55),
      specular: new pc.Color(0.3, 0.3, 0.3),
    });
    (blade.model as PCModel).material = bladeMat;
    handle.addChild(blade);
  }

  /**
   * Create name label for player
   */
  private createPlayerLabel(name: string, isAlive: boolean): PCEntity {
    const pc = window.pc;

    const label = new pc.Entity("Label");
    label.addComponent("element", {
      type: "text",
      text: name,
      fontSize: 0.5,
      color: isAlive ? new pc.Color(1, 1, 1) : new pc.Color(0.5, 0.5, 0.5),
      anchor: [0.5, 0.5, 0.5, 0.5],
      pivot: [0.5, 0.5],
    });

    return label;
  }

  /**
   * Apply death effect to player entity
   */
  private applyDeadEffect(entity: PlayerEntity): void {
    const pc = window.pc;

    if (!this.materialCache.has("deadMaterial")) {
      const deadMat = new pc.StandardMaterial();
      deadMat.diffuse = new pc.Color(0.3, 0.3, 0.3);
      deadMat.opacity = 0.6;
      deadMat.blendType = pc.BLEND_NORMAL;
      deadMat.update();
      this.materialCache.set("deadMaterial", deadMat);
    }

    const deadMat = this.materialCache.get("deadMaterial");
    if (!deadMat) return;

    const applyToChildren = (parent: PCEntity) => {
      if ((parent as unknown as { model?: unknown }).model) {
        (parent.model as unknown as { material: PCMaterial }).material =
          deadMat;
      }
      parent.children.forEach((child) => {
        applyToChildren(child as unknown as PCEntity);
      });
    };

    applyToChildren(entity);
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
