from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, TYPE_CHECKING, Union, Callable
from enum import Enum
import json
from logger import logger

from .enums import Team, Kategorie, Phase, TriggerTyp, AktionsTyp, SichtTyp, Erweiterung

if TYPE_CHECKING:
    from models import Spieler, Raum

# Type alias for cleaner signatures
ConditionCheck = Callable[["Spieler", "SpielKontext"], bool]


# =============================================================================
# DYNAMIC STATE MANAGEMENT SYSTEM
# =============================================================================


class StateType(Enum):
    """Typen für Rollen-Zustandsfelder."""

    BOOL = "bool"
    INT = "int"
    FLOAT = "float"
    STRING = "string"
    PLAYER_ID = "player_id"  # Reference to another player
    PLAYER_IDS = "player_ids"  # List of player references
    JSON = "json"  # Arbitrary JSON data


class StateTarget(Enum):
    """Wer wird von einem State betroffen? Basis-Typen."""

    SELF = "self"  # Nur der eigene Spieler
    OTHER = "other"  # Anderer Spieler (z.B. Verliebt, Infiziert)
    GLOBAL = "global"  # Spielweite Auswirkung
    ALL_PLAYERS = "all_players"  # Alle Spieler
    TEAM = "team"  # Alle im selben Team
    CUSTOM = "custom"  # Custom lambda function


@dataclass
class VisualEffectConfig:
    """
    Dynamische Konfiguration für visuelle Effekte.

    Statt hardcoded Enum-Werte können Rollen ihre eigenen
    visuellen Effekte komplett definieren.

    Beispiel:
        VisualEffectConfig(
            css_class="kuh-milch",
            icon="🥛",
            icon_class="fa-solid fa-glass",
            animation="pulse",
            sound_on_show="moo.mp3",
            show_to=lambda viewer, target: True,  # Alle sehen es
        )
    """

    css_class: Optional[str] = None
    icon: Optional[str] = None  # Emoji or text
    icon_class: Optional[str] = None  # FontAwesome class
    animation: Optional[str] = None  # CSS animation name
    sound_on_show: Optional[str] = None  # Sound file to play
    tooltip: Optional[str] = None
    # Lambda: (viewer_spieler, target_spieler) -> bool
    # Determines who can see this effect
    show_to: Optional[Callable[["Spieler", "Spieler"], bool]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "css_class": self.css_class,
            "icon": self.icon,
            "icon_class": self.icon_class,
            "animation": self.animation,
            "sound_on_show": self.sound_on_show,
            "tooltip": self.tooltip,
        }


# Legacy enum for backward compatibility - prefer VisualEffectConfig
class StateVisualEffect(Enum):
    """Visuelle Effekte - DEPRECATED, use VisualEffectConfig instead."""

    NONE = "none"
    HEART = "heart"
    INFECTED = "infected"
    MARKED = "marked"
    ENCHANTED = "enchanted"
    PROTECTED = "protected"
    CURSED = "cursed"
    WOLF_ICON = "wolf"
    CUSTOM = "custom"


@dataclass
class TargetingConfig:
    """
    Dynamische Targeting-Konfiguration.

    Ermöglicht komplexe Targeting-Logik über Lambda-Funktionen.

    Beispiel:
        TargetingConfig(
            base_target=StateTarget.ALL_PLAYERS,
            filter_fn=lambda spieler, kontext: spieler.rolle != "Werwolf",
            description="Alle Dorfbewohner",
        )
    """

    base_target: StateTarget = StateTarget.SELF
    # Lambda: (target_spieler, kontext) -> bool
    filter_fn: Optional[Callable[["Spieler", "SpielKontext"], bool]] = None
    description: str = ""

    def get_targets(
        self, alle_spieler: List["Spieler"], kontext: "SpielKontext"
    ) -> List["Spieler"]:
        """Ermittelt alle gültigen Ziele."""
        if self.filter_fn:
            return [s for s in alle_spieler if self.filter_fn(s, kontext)]
        return alle_spieler


@dataclass
class StateField:
    """
    Definition eines Zustandsfeldes für eine Rolle.

    Beispiel:
        StateField("heiltrank", StateType.BOOL, True, "Hat noch Heiltrank")
        StateField("ziel_id", StateType.PLAYER_ID, None, "Gewähltes Ziel")
    """

    name: str
    typ: StateType
    default: Any
    beschreibung: str = ""
    persistent: bool = True  # Bleibt über Runden erhalten

    # Für States die auf ANDERE Spieler wirken
    target: StateTarget = StateTarget.SELF

    # Advanced targeting with lambda support
    targeting_config: Optional[TargetingConfig] = None

    # Legacy visual effect enum (deprecated)
    visual_effect: StateVisualEffect = StateVisualEffect.NONE

    # New: Dynamic visual effect config
    visual_config: Optional[VisualEffectConfig] = None

    # CSS-Klasse für Spielerkarte wenn State aktiv
    css_class: Optional[str] = None

    # Icon/Emoji für Anzeige
    icon: Optional[str] = None

    # Soll dieser State bei Spielabfragen berücksichtigt werden?
    queryable: bool = False

    # Query-Name für dynamische Abfragen (z.B. "verliebte", "infizierte")
    query_name: Optional[str] = None

    def validate(self, value: Any) -> bool:
        """Prüft, ob ein Wert dem Typ entspricht."""
        # TODO: ADD MORE TYPES (TEAM; EXPANSION; ALIVE_STATE;)
        if value is None:
            return True
        if self.typ == StateType.BOOL:
            return isinstance(value, bool)
        elif self.typ == StateType.INT:
            return isinstance(value, int)
        elif self.typ == StateType.FLOAT:
            return isinstance(value, (int, float))
        elif self.typ == StateType.STRING:
            return isinstance(value, str)
        elif self.typ == StateType.PLAYER_ID:
            return isinstance(value, int) or value is None
        elif self.typ == StateType.PLAYER_IDS:
            return isinstance(value, list)
        elif self.typ == StateType.JSON:
            return True
        return True

    def deserialize(self, value: Any) -> Any:
        """Konvertiert Werte aus JSON-Speicherung."""
        if value is None:
            return self.default
        if self.typ == StateType.BOOL:
            return bool(value)
        elif self.typ == StateType.INT:
            return int(value) if value is not None else self.default
        elif self.typ == StateType.FLOAT:
            return float(value) if value is not None else self.default
        return value


@dataclass
class GlobalStateDefinition:
    """
    Definition eines globalen States der auf ANDERE Spieler gesetzt werden kann.

    Wird von Rollen definiert und beim Registry-Laden gesammelt.
    Ermöglicht dynamische Queries statt hardcoded Checks.
    """

    key: str  # Voller Key inkl. "global." prefix
    name: str  # Anzeigename
    typ: StateType = StateType.BOOL
    beschreibung: str = ""
    default: Any = None

    # Legacy visual effect (deprecated)
    visual_effect: StateVisualEffect = StateVisualEffect.NONE

    # New: Dynamic visual config
    visual_config: Optional[VisualEffectConfig] = None

    css_class: Optional[str] = None
    icon: Optional[str] = None
    query_name: Optional[str] = None
    defined_by: str = ""

    # Targeting config for complex targeting
    targeting_config: Optional[TargetingConfig] = None


@dataclass
class NachtEvent:
    """
    Definition eines Nacht-Events das für ALLE Spieler sichtbar/hörbar ist.

    Ermöglicht Rollen, globale Events zu triggern (z.B. Kuh muht).
    """

    event_id: str
    sound_file: Optional[str] = None  # z.B. "moo.mp3"
    text: Optional[str] = None  # Text der angezeigt wird
    animation: Optional[str] = None  # CSS animation
    # Lambda: (kontext) -> bool - Wann soll Event triggern
    trigger_condition: Optional[Callable[["SpielKontext"], bool]] = None
    # Für welche Phasen
    phases: List[str] = field(default_factory=lambda: ["nacht"])


@dataclass
class UIButtonDefinition:
    """
    Dynamische Button-Definition die Rollen für andere Spieler hinzufügen können.

    Beispiel: Kuh fügt "Milch trinken" Button für alle Dorfbewohner hinzu.
    """

    button_id: str
    label: str
    action_type: str
    icon: Optional[str] = None
    css_class: str = "btn-primary"
    # Lambda: (spieler, kontext) -> bool - Wer sieht diesen Button
    show_to: Optional[Callable[["Spieler", "SpielKontext"], bool]] = None
    # Lambda: (spieler, kontext) -> AktionsErgebnis - Was passiert bei Klick
    on_click: Optional[Callable[["Spieler", "SpielKontext"], "AktionsErgebnis"]] = None
    requires_confirmation: bool = False
    tooltip: Optional[str] = None


@dataclass
class AppearanceFeature:
    """
    A single 3D appearance feature (ears, claws, accessories, etc.).

    This defines what gets rendered in Village3D programmatically.
    All 3D models are built from these primitives - no external model files needed.

    Geometry Types:
        - "cone": Pointed shapes (ears, horns, hats, claws)
        - "box": Rectangular shapes (weapons, shields, books)
        - "sphere": Round shapes (orbs, potions, heads)
        - "cylinder": Tube shapes (staffs, bottles, trunks)
        - "torus": Ring shapes (halos, crowns, collars)
        - "capsule": Rounded cylinders (bodies, limbs)
        - "plane": Flat shapes (wings, capes, signs)

    Attachment Points (relative to humanoid base):
        - Head top: y=2.2
        - Head center: y=1.9
        - Shoulders: y=1.4, x=±0.35
        - Hands: y=0.6, x=±0.45
        - Back: z=-0.25
        - Belt/Waist: y=0.9
        - Feet: y=0.1
    """

    feature_type: str  # "ears", "claws", "hat", "weapon", "wings", "aura", etc.
    geometry: str  # "cone", "box", "sphere", "cylinder", "torus", "capsule", "plane"

    # Positioning
    position: Optional[Dict[str, float]] = None  # {x, y, z} relative position
    scale: Optional[Dict[str, float]] = None  # {x, y, z} scale
    rotation: Optional[Dict[str, float]] = None  # {x, y, z} euler angles in degrees

    # For mirrored features (ears, hands, etc.)
    mirror_x: bool = False  # Create mirrored copy on opposite X side
    mirror_offset: float = 0.0  # Additional X offset for mirrored version

    # Coloring
    color_source: str = "role"  # "role", "custom", "skin", "emissive", "gradient"
    custom_color: Optional[str] = None  # Hex color if color_source is "custom"
    secondary_color: Optional[str] = None  # For gradients or accents
    opacity: float = 1.0  # 0.0 to 1.0

    # Material Properties
    emissive: bool = False  # Self-illuminating (for magical effects)
    emissive_intensity: float = 0.5  # How bright the glow is
    metallic: bool = False  # Metal-like reflections
    roughness: float = 0.5  # 0=shiny, 1=matte

    # Animation
    animation: Optional[str] = None  # "rotate", "pulse", "float", "flicker", "sway"
    animation_speed: float = 1.0
    animation_amplitude: float = 1.0

    # Particle Effects (for auras, magic, fire, etc.)
    particle_effect: Optional[str] = None  # "sparks", "smoke", "fire", "magic", "hearts"
    particle_color: Optional[str] = None
    particle_rate: float = 10.0  # Particles per second

    # Light emission (for glowing eyes, auras, etc.)
    light_source: bool = False
    light_color: Optional[str] = None
    light_intensity: float = 0.5
    light_range: float = 2.0

    # Multiple instances
    count: int = 1  # How many of this feature
    count_arrangement: str = "linear"  # "linear", "radial", "random"
    count_spacing: float = 0.1  # Spacing between instances

    # Visibility conditions
    visible_to_self: bool = True
    visible_to_others: bool = True
    visible_to_seher: bool = True
    visible_when_dead: bool = False

    # Description for debugging/tooltips
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feature_type": self.feature_type,
            "geometry": self.geometry,
            "position": self.position or {},
            "scale": self.scale or {},
            "rotation": self.rotation or {},
            "mirror_x": self.mirror_x,
            "mirror_offset": self.mirror_offset,
            "color_source": self.color_source,
            "custom_color": self.custom_color,
            "secondary_color": self.secondary_color,
            "opacity": self.opacity,
            "emissive": self.emissive,
            "emissive_intensity": self.emissive_intensity,
            "metallic": self.metallic,
            "roughness": self.roughness,
            "animation": self.animation,
            "animation_speed": self.animation_speed,
            "animation_amplitude": self.animation_amplitude,
            "particle_effect": self.particle_effect,
            "particle_color": self.particle_color,
            "particle_rate": self.particle_rate,
            "light_source": self.light_source,
            "light_color": self.light_color,
            "light_intensity": self.light_intensity,
            "light_range": self.light_range,
            "count": self.count,
            "count_arrangement": self.count_arrangement,
            "count_spacing": self.count_spacing,
            "visible_to_self": self.visible_to_self,
            "visible_to_others": self.visible_to_others,
            "visible_to_seher": self.visible_to_seher,
            "visible_when_dead": self.visible_when_dead,
            "description": self.description,
        }


@dataclass
class BodyModification:
    """
    Modifications to the base humanoid body shape.

    Allows roles to have different body proportions, animal features, etc.
    """

    # Body scaling
    height_multiplier: float = 1.0  # Tall/short
    width_multiplier: float = 1.0  # Fat/thin
    head_scale: float = 1.0  # Big/small head

    # Posture
    slouch_angle: float = 0.0  # Forward lean (0-45 degrees)
    hunch_back: bool = False

    # Skin/fur
    skin_texture: str = "smooth"  # "smooth", "fur", "scales", "bark", "stone"
    skin_color_override: Optional[str] = None  # Hex color

    # Face modifications
    snout_length: float = 0.0  # For animal faces (0-1)
    jaw_width: float = 1.0
    brow_ridge: float = 0.0  # Prominent brow (0-1)

    # Limb modifications
    arm_length: float = 1.0
    leg_length: float = 1.0
    claw_hands: bool = False
    paw_feet: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "height_multiplier": self.height_multiplier,
            "width_multiplier": self.width_multiplier,
            "head_scale": self.head_scale,
            "slouch_angle": self.slouch_angle,
            "hunch_back": self.hunch_back,
            "skin_texture": self.skin_texture,
            "skin_color_override": self.skin_color_override,
            "snout_length": self.snout_length,
            "jaw_width": self.jaw_width,
            "brow_ridge": self.brow_ridge,
            "arm_length": self.arm_length,
            "leg_length": self.leg_length,
            "claw_hands": self.claw_hands,
            "paw_feet": self.paw_feet,
        }


@dataclass
class AnimationState:
    """
    Definition of an animation state for a role.

    Roles can define custom idle, action, and death animations.
    """

    state_name: str  # "idle", "action", "death", "celebrate", "vote", etc.

    # Body movement
    sway_amplitude: float = 0.0  # Side-to-side body sway
    sway_speed: float = 1.0
    bob_amplitude: float = 0.0  # Up-down bobbing
    bob_speed: float = 1.0

    # Head movement
    head_tilt_range: float = 10.0  # Random head tilting (degrees)
    look_around: bool = True  # Random looking around
    blink_rate: float = 3.0  # Blinks per second

    # Arm movement
    arm_swing: float = 0.0  # Arm swinging amplitude
    gesture_chance: float = 0.0  # Chance of random gestures

    # Special movements
    breathing_visible: bool = True
    tail_wag: bool = False  # For roles with tails
    wing_flutter: bool = False  # For roles with wings

    # Transition
    transition_duration: float = 0.3  # Seconds to blend into this state

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state_name": self.state_name,
            "sway_amplitude": self.sway_amplitude,
            "sway_speed": self.sway_speed,
            "bob_amplitude": self.bob_amplitude,
            "bob_speed": self.bob_speed,
            "head_tilt_range": self.head_tilt_range,
            "look_around": self.look_around,
            "blink_rate": self.blink_rate,
            "arm_swing": self.arm_swing,
            "gesture_chance": self.gesture_chance,
            "breathing_visible": self.breathing_visible,
            "tail_wag": self.tail_wag,
            "wing_flutter": self.wing_flutter,
            "transition_duration": self.transition_duration,
        }


@dataclass
class HintEffect3D:
    """
    3D visual effect for the hint system.

    Defines how a hint manifests in Village3D.
    """

    effect_id: str  # Unique identifier

    # Visual effect type
    effect_type: str  # "particle", "glow", "shake", "transform", "overlay"

    # For particle effects
    particle_type: Optional[str] = None  # "sparks", "smoke", "shadow", "light"
    particle_count: int = 20
    particle_color: Optional[str] = None
    particle_duration: float = 1.0  # Seconds

    # For glow effects
    glow_color: Optional[str] = None
    glow_intensity: float = 1.0
    glow_pulse: bool = False

    # For shake effects
    shake_intensity: float = 0.1
    shake_duration: float = 0.5

    # For transform effects
    scale_to: Optional[Dict[str, float]] = None
    rotate_to: Optional[Dict[str, float]] = None

    # Sound
    sound_file: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "effect_id": self.effect_id,
            "effect_type": self.effect_type,
            "particle_type": self.particle_type,
            "particle_count": self.particle_count,
            "particle_color": self.particle_color,
            "particle_duration": self.particle_duration,
            "glow_color": self.glow_color,
            "glow_intensity": self.glow_intensity,
            "glow_pulse": self.glow_pulse,
            "shake_intensity": self.shake_intensity,
            "shake_duration": self.shake_duration,
            "scale_to": self.scale_to or {},
            "rotate_to": self.rotate_to or {},
            "sound_file": self.sound_file,
        }


@dataclass
class SpecialPhaseConfig:
    """
    Configuration for roles that trigger out-of-order phases.

    For example, Jäger triggers a phase when he dies, not during normal night order.
    """

    phase_name: str  # The phase to trigger (e.g., "jaeger_phase")
    trigger_event: str  # When to trigger: "on_death", "on_lynch", "on_attack", etc.

    # Condition for triggering (lambda or None for always)
    trigger_condition: Optional[Callable[["Spieler", "SpielKontext"], bool]] = None

    # What phase to go to after this special phase
    next_phase_override: Optional[str] = None  # None = return to normal flow

    # Priority when multiple special phases trigger
    priority: int = 50  # Higher = happens first

    # Is this phase interruptible by other special phases?
    interruptible: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase_name": self.phase_name,
            "trigger_event": self.trigger_event,
            "next_phase_override": self.next_phase_override,
            "priority": self.priority,
            "interruptible": self.interruptible,
        }


@dataclass
class RollenModell:
    """
    Complete 3D model definition for a role.

    All visual aspects of how a role appears in Village3D are defined here.
    This is the primary class that roles override in get_modell_definition().
    """

    modell_id: str  # Unique identifier (e.g., "werwolf", "hexe", "jaeger")
    anzeige_name: str  # Display name in UI
    beschreibung: str = ""

    # Base body modifications
    body: Optional[BodyModification] = None

    # Appearance features for different contexts
    # Features visible when the player views themselves
    appearance_self_alive: List[AppearanceFeature] = field(default_factory=list)
    # Features visible to other players (may hide role-revealing features)
    appearance_others_alive: List[AppearanceFeature] = field(default_factory=list)
    # Features shown when dead
    appearance_dead: List[AppearanceFeature] = field(default_factory=list)
    # Features that only Seher-type roles can see
    appearance_seher_view: List[AppearanceFeature] = field(default_factory=list)

    # Animation states
    animations: Dict[str, AnimationState] = field(default_factory=dict)

    # Hint effects this role can trigger
    hint_effects: List[HintEffect3D] = field(default_factory=list)

    # What Seher-type roles see
    seher_sicht: str = "good"  # "good", "bad", "neutral", or specific role name

    # Dynamic model selection based on state
    # Lambda: (spieler, kontext) -> str (alternative modell_id)
    modell_selector: Optional[Callable[["Spieler", "SpielKontext"], str]] = None

    # Sound effects
    sound_on_action: Optional[str] = None  # Played when role acts
    sound_on_death: Optional[str] = None  # Played when role dies
    sound_ambient: Optional[str] = None  # Ambient loop while role is active

    def to_dict(self) -> Dict[str, Any]:
        return {
            "modell_id": self.modell_id,
            "anzeige_name": self.anzeige_name,
            "beschreibung": self.beschreibung,
            "body": self.body.to_dict() if self.body else None,
            "appearance_self_alive": [f.to_dict() for f in self.appearance_self_alive],
            "appearance_others_alive": [f.to_dict() for f in self.appearance_others_alive],
            "appearance_dead": [f.to_dict() for f in self.appearance_dead],
            "appearance_seher_view": [f.to_dict() for f in self.appearance_seher_view],
            "animations": {k: v.to_dict() for k, v in self.animations.items()},
            "hint_effects": [e.to_dict() for e in self.hint_effects],
            "seher_sicht": self.seher_sicht,
            "sound_on_action": self.sound_on_action,
            "sound_on_death": self.sound_on_death,
            "sound_ambient": self.sound_ambient,
        }


# =============================================================================
# FACTORY FUNCTIONS FOR COMMON 3D APPEARANCE FEATURES
# These make it easy to create standard appearance elements in role files
# =============================================================================

def create_wolf_ears(color: str = None, scale: float = 1.0) -> List[AppearanceFeature]:
    """Create wolf ear features (pair of pointed ears on head)."""
    return [
        AppearanceFeature(
            feature_type="ear_left",
            geometry="cone",
            position={"x": -0.18, "y": 2.25, "z": -0.05},
            scale={"x": 0.12 * scale, "y": 0.22 * scale, "z": 0.1 * scale},
            rotation={"x": 0, "y": 0, "z": -15},
            color_source="custom" if color else "role",
            custom_color=color,
            description="Left wolf ear",
        ),
        AppearanceFeature(
            feature_type="ear_right",
            geometry="cone",
            position={"x": 0.18, "y": 2.25, "z": -0.05},
            scale={"x": 0.12 * scale, "y": 0.22 * scale, "z": 0.1 * scale},
            rotation={"x": 0, "y": 0, "z": 15},
            color_source="custom" if color else "role",
            custom_color=color,
            description="Right wolf ear",
        ),
    ]


def create_claws(color: str = "#333333", count_per_hand: int = 3) -> List[AppearanceFeature]:
    """Create claw features on both hands."""
    claws = []
    for hand in ["left", "right"]:
        base_x = -0.45 if hand == "left" else 0.45
        for i in range(count_per_hand):
            offset_x = (i - (count_per_hand - 1) / 2) * 0.025
            claws.append(AppearanceFeature(
                feature_type=f"claw_{hand}_{i}",
                geometry="cone",
                position={"x": base_x + offset_x, "y": 0.52, "z": 0.08},
                scale={"x": 0.025, "y": 0.08, "z": 0.025},
                rotation={"x": 60, "y": 0, "z": 0},
                color_source="custom",
                custom_color=color,
                metallic=True,
                roughness=0.3,
                description=f"{hand.title()} hand claw {i+1}",
            ))
    return claws


def create_fangs(color: str = "#FFFEF0") -> List[AppearanceFeature]:
    """Create vampire/wolf fang features."""
    return [
        AppearanceFeature(
            feature_type="fang_left",
            geometry="cone",
            position={"x": -0.04, "y": 1.68, "z": 0.2},
            scale={"x": 0.02, "y": 0.06, "z": 0.02},
            rotation={"x": 180, "y": 0, "z": 0},
            color_source="custom",
            custom_color=color,
            metallic=True,
            roughness=0.2,
            description="Left fang",
        ),
        AppearanceFeature(
            feature_type="fang_right",
            geometry="cone",
            position={"x": 0.04, "y": 1.68, "z": 0.2},
            scale={"x": 0.02, "y": 0.06, "z": 0.02},
            rotation={"x": 180, "y": 0, "z": 0},
            color_source="custom",
            custom_color=color,
            metallic=True,
            roughness=0.2,
            description="Right fang",
        ),
    ]


def create_glowing_eyes(color: str = "#FF3333", intensity: float = 0.6) -> AppearanceFeature:
    """Create glowing eyes effect."""
    return AppearanceFeature(
        feature_type="eye_glow",
        geometry="sphere",
        position={"x": 0, "y": 1.9, "z": 0.35},
        scale={"x": 0.1, "y": 0.1, "z": 0.1},
        color_source="custom",
        custom_color=color,
        emissive=True,
        emissive_intensity=intensity,
        light_source=True,
        light_color=color,
        light_intensity=intensity,
        light_range=1.5,
        opacity=0.0,  # Invisible geometry, just light
        description="Glowing eyes light source",
    )


def create_witch_hat(color: str = "#1a1a1a", brim: bool = True) -> List[AppearanceFeature]:
    """Create a pointed witch/wizard hat."""
    features = [
        AppearanceFeature(
            feature_type="hat_cone",
            geometry="cone",
            position={"x": 0, "y": 2.5, "z": -0.02},
            scale={"x": 0.3, "y": 0.7, "z": 0.3},
            color_source="custom",
            custom_color=color,
            description="Witch hat point",
        ),
    ]
    if brim:
        features.append(AppearanceFeature(
            feature_type="hat_brim",
            geometry="cylinder",
            position={"x": 0, "y": 2.15, "z": 0},
            scale={"x": 0.55, "y": 0.04, "z": 0.55},
            color_source="custom",
            custom_color=color,
            description="Witch hat brim",
        ))
    return features


def create_pointed_hat(color: str = "#4B0082") -> AppearanceFeature:
    """Create a simple pointed hat (no brim)."""
    return AppearanceFeature(
        feature_type="pointed_hat",
        geometry="cone",
        position={"x": 0, "y": 2.35, "z": -0.02},
        scale={"x": 0.35, "y": 0.55, "z": 0.35},
        color_source="custom",
        custom_color=color,
        description="Pointed mystic hat",
    )


def create_aura(color: str, intensity: float = 0.5, pulsing: bool = True) -> AppearanceFeature:
    """Create a magical aura around the character."""
    return AppearanceFeature(
        feature_type="aura",
        geometry="sphere",
        position={"x": 0, "y": 1.2, "z": 0},
        scale={"x": 0.8, "y": 1.5, "z": 0.8},
        color_source="custom",
        custom_color=color,
        opacity=0.15,
        emissive=True,
        emissive_intensity=intensity,
        animation="pulse" if pulsing else None,
        animation_speed=0.5,
        light_source=True,
        light_color=color,
        light_intensity=intensity * 0.5,
        light_range=3.0,
        description="Magical aura",
    )


def create_potion_bottles(positions: List[str] = None, colors: List[str] = None) -> List[AppearanceFeature]:
    """Create potion bottles on belt."""
    if positions is None:
        positions = ["left", "right"]
    if colors is None:
        colors = ["#00ff00", "#ff00ff"]  # Green heal, purple poison

    features = []
    for i, (pos, color) in enumerate(zip(positions, colors)):
        x = -0.35 if pos == "left" else 0.35
        features.append(AppearanceFeature(
            feature_type=f"potion_{pos}",
            geometry="cylinder",
            position={"x": x, "y": 0.7, "z": 0.2},
            scale={"x": 0.06, "y": 0.15, "z": 0.06},
            color_source="custom",
            custom_color=color,
            opacity=0.8,
            emissive=True,
            emissive_intensity=0.3,
            light_source=True,
            light_color=color,
            light_intensity=0.2,
            light_range=0.5,
            description=f"Potion bottle ({pos})",
        ))
    return features


def create_crystal_ball(color: str = "#9966ff") -> AppearanceFeature:
    """Create a crystal ball held in hand."""
    return AppearanceFeature(
        feature_type="crystal_ball",
        geometry="sphere",
        position={"x": 0.42, "y": 0.7, "z": 0.15},
        scale={"x": 0.18, "y": 0.18, "z": 0.18},
        color_source="custom",
        custom_color=color,
        opacity=0.7,
        emissive=True,
        emissive_intensity=0.6,
        light_source=True,
        light_color=color,
        light_intensity=0.8,
        light_range=2.5,
        animation="pulse",
        animation_speed=0.5,
        description="Crystal ball",
    )


def create_halo(color: str = "#FFD700") -> AppearanceFeature:
    """Create a glowing halo above the head."""
    return AppearanceFeature(
        feature_type="halo",
        geometry="torus",
        position={"x": 0, "y": 2.4, "z": 0},
        scale={"x": 0.25, "y": 0.03, "z": 0.25},
        color_source="custom",
        custom_color=color,
        emissive=True,
        emissive_intensity=1.0,
        light_source=True,
        light_color=color,
        light_intensity=0.5,
        light_range=2.0,
        animation="rotate",
        animation_speed=0.3,
        description="Golden halo",
    )


def create_wings(wing_type: str = "angel", color: str = "#FFFFFF") -> List[AppearanceFeature]:
    """Create wing pairs on the back."""
    wings = {
        "angel": [
            AppearanceFeature(
                feature_type="wing_left",
                geometry="plane",
                position={"x": -0.4, "y": 1.4, "z": -0.3},
                scale={"x": 0.8, "y": 1.0, "z": 0.1},
                rotation={"x": 0, "y": -30, "z": 10},
                color_source="custom",
                custom_color=color,
                opacity=0.9,
                animation="flutter",
                animation_speed=0.5,
                animation_amplitude=0.1,
                description="Left angel wing",
            ),
            AppearanceFeature(
                feature_type="wing_right",
                geometry="plane",
                position={"x": 0.4, "y": 1.4, "z": -0.3},
                scale={"x": 0.8, "y": 1.0, "z": 0.1},
                rotation={"x": 0, "y": 30, "z": -10},
                color_source="custom",
                custom_color=color,
                opacity=0.9,
                animation="flutter",
                animation_speed=0.5,
                animation_amplitude=0.1,
                description="Right angel wing",
            ),
        ],
        "bat": [
            AppearanceFeature(
                feature_type="wing_left",
                geometry="plane",
                position={"x": -0.5, "y": 1.3, "z": -0.25},
                scale={"x": 0.7, "y": 0.6, "z": 0.05},
                rotation={"x": 0, "y": -40, "z": 5},
                color_source="custom",
                custom_color="#1a1a1a",
                opacity=0.95,
                animation="flutter",
                animation_speed=0.8,
                description="Left bat wing",
            ),
            AppearanceFeature(
                feature_type="wing_right",
                geometry="plane",
                position={"x": 0.5, "y": 1.3, "z": -0.25},
                scale={"x": 0.7, "y": 0.6, "z": 0.05},
                rotation={"x": 0, "y": 40, "z": -5},
                color_source="custom",
                custom_color="#1a1a1a",
                opacity=0.95,
                animation="flutter",
                animation_speed=0.8,
                description="Right bat wing",
            ),
        ],
        "demon": [
            AppearanceFeature(
                feature_type="wing_left",
                geometry="plane",
                position={"x": -0.45, "y": 1.35, "z": -0.28},
                scale={"x": 0.75, "y": 0.7, "z": 0.05},
                rotation={"x": 0, "y": -35, "z": 8},
                color_source="custom",
                custom_color="#4a0000",
                opacity=0.95,
                animation="flutter",
                animation_speed=0.6,
                description="Left demon wing",
            ),
            AppearanceFeature(
                feature_type="wing_right",
                geometry="plane",
                position={"x": 0.45, "y": 1.35, "z": -0.28},
                scale={"x": 0.75, "y": 0.7, "z": 0.05},
                rotation={"x": 0, "y": 35, "z": -8},
                color_source="custom",
                custom_color="#4a0000",
                opacity=0.95,
                animation="flutter",
                animation_speed=0.6,
                description="Right demon wing",
            ),
        ],
    }
    return wings.get(wing_type, [])


def create_tail(tail_type: str = "wolf", color: str = None) -> AppearanceFeature:
    """Create animal tails."""
    tails = {
        "wolf": AppearanceFeature(
            feature_type="tail",
            geometry="capsule",
            position={"x": 0, "y": 0.8, "z": -0.35},
            scale={"x": 0.08, "y": 0.4, "z": 0.08},
            rotation={"x": -45, "y": 0, "z": 0},
            color_source="custom" if color else "role",
            custom_color=color,
            animation="sway",
            animation_speed=0.5,
            description="Wolf tail",
        ),
        "cat": AppearanceFeature(
            feature_type="tail",
            geometry="cylinder",
            position={"x": 0, "y": 0.85, "z": -0.3},
            scale={"x": 0.04, "y": 0.5, "z": 0.04},
            rotation={"x": -60, "y": 0, "z": 0},
            color_source="custom" if color else "role",
            custom_color=color,
            animation="sway",
            animation_speed=0.7,
            description="Cat tail",
        ),
        "devil": AppearanceFeature(
            feature_type="tail",
            geometry="cylinder",
            position={"x": 0, "y": 0.8, "z": -0.3},
            scale={"x": 0.03, "y": 0.6, "z": 0.03},
            rotation={"x": -50, "y": 0, "z": 0},
            color_source="custom",
            custom_color="#8B0000",
            animation="sway",
            description="Devil tail",
        ),
        "fluffy": AppearanceFeature(
            feature_type="tail",
            geometry="sphere",
            position={"x": 0, "y": 0.85, "z": -0.3},
            scale={"x": 0.15, "y": 0.12, "z": 0.1},
            color_source="custom" if color else "role",
            custom_color=color,
            description="Fluffy bunny tail",
        ),
    }
    return tails.get(tail_type)


def create_horns(horn_type: str = "demon", color: str = "#2a2a2a") -> List[AppearanceFeature]:
    """Create various horn types."""
    horns = {
        "demon": [
            AppearanceFeature(
                feature_type="horn_left",
                geometry="cone",
                position={"x": -0.15, "y": 2.2, "z": -0.05},
                scale={"x": 0.06, "y": 0.25, "z": 0.06},
                rotation={"x": -30, "y": 0, "z": -20},
                color_source="custom",
                custom_color=color,
                metallic=True,
                roughness=0.4,
                description="Left demon horn",
            ),
            AppearanceFeature(
                feature_type="horn_right",
                geometry="cone",
                position={"x": 0.15, "y": 2.2, "z": -0.05},
                scale={"x": 0.06, "y": 0.25, "z": 0.06},
                rotation={"x": -30, "y": 0, "z": 20},
                color_source="custom",
                custom_color=color,
                metallic=True,
                roughness=0.4,
                description="Right demon horn",
            ),
        ],
        "ram": [
            AppearanceFeature(
                feature_type="horn_left",
                geometry="torus",
                position={"x": -0.22, "y": 2.0, "z": 0},
                scale={"x": 0.15, "y": 0.15, "z": 0.08},
                rotation={"x": 90, "y": 0, "z": 0},
                color_source="custom",
                custom_color="#3d3d3d",
                roughness=0.6,
                description="Left ram horn",
            ),
            AppearanceFeature(
                feature_type="horn_right",
                geometry="torus",
                position={"x": 0.22, "y": 2.0, "z": 0},
                scale={"x": 0.15, "y": 0.15, "z": 0.08},
                rotation={"x": 90, "y": 180, "z": 0},
                color_source="custom",
                custom_color="#3d3d3d",
                roughness=0.6,
                description="Right ram horn",
            ),
        ],
        "unicorn": [
            AppearanceFeature(
                feature_type="horn_unicorn",
                geometry="cone",
                position={"x": 0, "y": 2.3, "z": 0.1},
                scale={"x": 0.05, "y": 0.35, "z": 0.05},
                rotation={"x": -15, "y": 0, "z": 0},
                color_source="custom",
                custom_color="#FFD700",
                emissive=True,
                emissive_intensity=0.3,
                metallic=True,
                roughness=0.1,
                description="Unicorn horn",
            ),
        ],
    }
    return horns.get(horn_type, [])


def create_heart_effect() -> AppearanceFeature:
    """Create a floating heart for lovers."""
    return AppearanceFeature(
        feature_type="love_heart",
        geometry="sphere",  # Simplified, heart shape via scale
        position={"x": 0, "y": 2.5, "z": 0},
        scale={"x": 0.15, "y": 0.15, "z": 0.08},
        color_source="custom",
        custom_color="#FF69B4",
        emissive=True,
        emissive_intensity=0.8,
        animation="float",
        animation_speed=0.5,
        particle_effect="hearts",
        particle_color="#FF69B4",
        particle_rate=3.0,
        description="Lover's heart",
    )


def create_weapon(weapon_type: str) -> List[AppearanceFeature]:
    """Create various weapon types held in hand."""
    weapons = {
        "crossbow": [
            AppearanceFeature(
                feature_type="crossbow_body",
                geometry="box",
                position={"x": 0.45, "y": 0.7, "z": 0.15},
                scale={"x": 0.08, "y": 0.25, "z": 0.04},
                rotation={"x": -20, "y": 0, "z": 0},
                color_source="custom",
                custom_color="#3d2817",
                description="Crossbow body",
            ),
            AppearanceFeature(
                feature_type="crossbow_bow",
                geometry="box",
                position={"x": 0.45, "y": 0.8, "z": 0.18},
                scale={"x": 0.35, "y": 0.03, "z": 0.02},
                color_source="custom",
                custom_color="#3d2817",
                description="Crossbow bow",
            ),
        ],
        "staff": [
            AppearanceFeature(
                feature_type="staff",
                geometry="cylinder",
                position={"x": 0.5, "y": 0.9, "z": 0.1},
                scale={"x": 0.04, "y": 1.4, "z": 0.04},
                rotation={"x": 0, "y": 0, "z": -15},
                color_source="custom",
                custom_color="#4a3728",
                description="Wooden staff",
            ),
            AppearanceFeature(
                feature_type="staff_orb",
                geometry="sphere",
                position={"x": 0.42, "y": 2.2, "z": 0.05},
                scale={"x": 0.12, "y": 0.12, "z": 0.12},
                color_source="custom",
                custom_color="#9966ff",
                emissive=True,
                emissive_intensity=0.8,
                light_source=True,
                light_color="#9966ff",
                light_intensity=0.6,
                light_range=2.0,
                animation="pulse",
                description="Staff magical orb",
            ),
        ],
        "healing_staff": [
            AppearanceFeature(
                feature_type="staff",
                geometry="cylinder",
                position={"x": 0.5, "y": 0.9, "z": 0.1},
                scale={"x": 0.04, "y": 1.4, "z": 0.04},
                rotation={"x": 0, "y": 0, "z": -15},
                color_source="custom",
                custom_color="#2d5a27",
                description="Healing staff",
            ),
            AppearanceFeature(
                feature_type="staff_orb",
                geometry="sphere",
                position={"x": 0.42, "y": 2.2, "z": 0.05},
                scale={"x": 0.12, "y": 0.12, "z": 0.12},
                color_source="custom",
                custom_color="#00ff88",
                emissive=True,
                emissive_intensity=0.8,
                light_source=True,
                light_color="#00ff88",
                light_intensity=0.6,
                light_range=2.0,
                animation="pulse",
                particle_effect="magic",
                particle_color="#00ff88",
                particle_rate=5.0,
                description="Healing orb",
            ),
        ],
        "scythe": [
            AppearanceFeature(
                feature_type="scythe_handle",
                geometry="cylinder",
                position={"x": -0.4, "y": 1.2, "z": -0.15},
                scale={"x": 0.03, "y": 1.8, "z": 0.03},
                rotation={"x": -20, "y": 0, "z": 10},
                color_source="custom",
                custom_color="#2a1a0a",
                description="Scythe handle",
            ),
            AppearanceFeature(
                feature_type="scythe_blade",
                geometry="box",
                position={"x": -0.5, "y": 2.4, "z": -0.1},
                scale={"x": 0.5, "y": 0.02, "z": 0.15},
                rotation={"x": 0, "y": 0, "z": -30},
                color_source="custom",
                custom_color="#888888",
                metallic=True,
                roughness=0.1,
                description="Scythe blade",
            ),
        ],
        "axe": [
            AppearanceFeature(
                feature_type="axe_handle",
                geometry="cylinder",
                position={"x": 0.5, "y": 0.8, "z": 0.1},
                scale={"x": 0.035, "y": 0.7, "z": 0.035},
                rotation={"x": 0, "y": 0, "z": -20},
                color_source="custom",
                custom_color="#4a3020",
                description="Axe handle",
            ),
            AppearanceFeature(
                feature_type="axe_head",
                geometry="box",
                position={"x": 0.55, "y": 1.4, "z": 0.15},
                scale={"x": 0.25, "y": 0.15, "z": 0.04},
                rotation={"x": 0, "y": 0, "z": -20},
                color_source="custom",
                custom_color="#555555",
                metallic=True,
                roughness=0.2,
                description="Axe head",
            ),
        ],
        "dagger": [
            AppearanceFeature(
                feature_type="dagger_blade",
                geometry="box",
                position={"x": 0.45, "y": 0.65, "z": 0.12},
                scale={"x": 0.02, "y": 0.18, "z": 0.06},
                rotation={"x": 45, "y": 0, "z": 0},
                color_source="custom",
                custom_color="#aaaaaa",
                metallic=True,
                roughness=0.1,
                description="Dagger blade",
            ),
            AppearanceFeature(
                feature_type="dagger_handle",
                geometry="cylinder",
                position={"x": 0.45, "y": 0.55, "z": 0.08},
                scale={"x": 0.025, "y": 0.08, "z": 0.025},
                color_source="custom",
                custom_color="#3d2817",
                description="Dagger handle",
            ),
        ],
        "bow": [
            AppearanceFeature(
                feature_type="bow_body",
                geometry="torus",
                position={"x": -0.4, "y": 1.0, "z": 0.1},
                scale={"x": 0.3, "y": 0.5, "z": 0.05},
                rotation={"x": 0, "y": 90, "z": 0},
                color_source="custom",
                custom_color="#8B4513",
                description="Bow body",
            ),
            AppearanceFeature(
                feature_type="bow_string",
                geometry="cylinder",
                position={"x": -0.4, "y": 1.0, "z": 0.1},
                scale={"x": 0.005, "y": 0.9, "z": 0.005},
                color_source="custom",
                custom_color="#DDD",
                description="Bow string",
            ),
        ],
        "sword": [
            AppearanceFeature(
                feature_type="sword_blade",
                geometry="box",
                position={"x": 0.5, "y": 0.9, "z": 0.12},
                scale={"x": 0.03, "y": 0.6, "z": 0.08},
                color_source="custom",
                custom_color="#C0C0C0",
                metallic=True,
                roughness=0.1,
                description="Sword blade",
            ),
            AppearanceFeature(
                feature_type="sword_handle",
                geometry="cylinder",
                position={"x": 0.5, "y": 0.55, "z": 0.12},
                scale={"x": 0.03, "y": 0.12, "z": 0.03},
                color_source="custom",
                custom_color="#3d2817",
                description="Sword handle",
            ),
            AppearanceFeature(
                feature_type="sword_guard",
                geometry="box",
                position={"x": 0.5, "y": 0.62, "z": 0.12},
                scale={"x": 0.12, "y": 0.02, "z": 0.02},
                color_source="custom",
                custom_color="#8B7355",
                metallic=True,
                description="Sword guard",
            ),
        ],
        "shield": [
            AppearanceFeature(
                feature_type="shield",
                geometry="box",
                position={"x": -0.45, "y": 0.9, "z": 0.2},
                scale={"x": 0.35, "y": 0.5, "z": 0.04},
                rotation={"x": 0, "y": 15, "z": 0},
                color_source="custom",
                custom_color="#8B4513",
                roughness=0.7,
                description="Wooden shield",
            ),
            AppearanceFeature(
                feature_type="shield_boss",
                geometry="sphere",
                position={"x": -0.42, "y": 0.9, "z": 0.24},
                scale={"x": 0.08, "y": 0.08, "z": 0.04},
                color_source="custom",
                custom_color="#888888",
                metallic=True,
                roughness=0.2,
                description="Shield boss",
            ),
        ],
        "torch": [
            AppearanceFeature(
                feature_type="torch_handle",
                geometry="cylinder",
                position={"x": 0.45, "y": 0.75, "z": 0.12},
                scale={"x": 0.035, "y": 0.4, "z": 0.035},
                color_source="custom",
                custom_color="#4a3020",
                description="Torch handle",
            ),
            AppearanceFeature(
                feature_type="torch_flame",
                geometry="cone",
                position={"x": 0.45, "y": 1.05, "z": 0.12},
                scale={"x": 0.08, "y": 0.15, "z": 0.08},
                color_source="custom",
                custom_color="#FF6600",
                emissive=True,
                emissive_intensity=1.0,
                light_source=True,
                light_color="#FF8800",
                light_intensity=1.0,
                light_range=4.0,
                animation="flicker",
                particle_effect="fire",
                particle_color="#FF6600",
                particle_rate=15.0,
                description="Torch flame",
            ),
        ],
        "lantern": [
            AppearanceFeature(
                feature_type="lantern_frame",
                geometry="box",
                position={"x": 0.45, "y": 0.7, "z": 0.15},
                scale={"x": 0.1, "y": 0.15, "z": 0.1},
                color_source="custom",
                custom_color="#444444",
                metallic=True,
                opacity=0.8,
                description="Lantern frame",
            ),
            AppearanceFeature(
                feature_type="lantern_light",
                geometry="sphere",
                position={"x": 0.45, "y": 0.7, "z": 0.15},
                scale={"x": 0.06, "y": 0.08, "z": 0.06},
                color_source="custom",
                custom_color="#FFDD66",
                emissive=True,
                emissive_intensity=0.8,
                light_source=True,
                light_color="#FFDD66",
                light_intensity=0.7,
                light_range=3.0,
                animation="flicker",
                animation_speed=0.3,
                description="Lantern light",
            ),
        ],
    }
    return weapons.get(weapon_type, [])


def create_crown(style: str = "gold") -> List[AppearanceFeature]:
    """Create a crown on the head."""
    colors = {
        "gold": "#FFD700",
        "silver": "#C0C0C0",
        "iron": "#555555",
        "dark": "#2a2a2a",
    }
    color = colors.get(style, "#FFD700")

    features = [
        AppearanceFeature(
            feature_type="crown_base",
            geometry="cylinder",
            position={"x": 0, "y": 2.1, "z": 0},
            scale={"x": 0.22, "y": 0.08, "z": 0.22},
            color_source="custom",
            custom_color=color,
            metallic=True,
            roughness=0.2,
            description="Crown base",
        ),
    ]
    # Add crown points
    for i in range(5):
        angle = (i / 5) * 360
        import math
        rad = math.radians(angle)
        x = math.sin(rad) * 0.15
        z = math.cos(rad) * 0.15
        features.append(AppearanceFeature(
            feature_type=f"crown_point_{i}",
            geometry="cone",
            position={"x": x, "y": 2.2, "z": z},
            scale={"x": 0.04, "y": 0.12, "z": 0.04},
            color_source="custom",
            custom_color=color,
            metallic=True,
            roughness=0.2,
            description=f"Crown point {i+1}",
        ))
    return features


def create_mask(mask_type: str = "plain") -> AppearanceFeature:
    """Create a face mask."""
    masks = {
        "plain": AppearanceFeature(
            feature_type="mask",
            geometry="box",
            position={"x": 0, "y": 1.85, "z": 0.22},
            scale={"x": 0.28, "y": 0.18, "z": 0.02},
            color_source="custom",
            custom_color="#F5F5DC",
            roughness=0.8,
            description="Plain mask",
        ),
        "wolf": AppearanceFeature(
            feature_type="mask",
            geometry="box",
            position={"x": 0, "y": 1.85, "z": 0.22},
            scale={"x": 0.3, "y": 0.2, "z": 0.08},
            color_source="custom",
            custom_color="#4a4a4a",
            roughness=0.6,
            description="Wolf mask",
        ),
        "bird": AppearanceFeature(
            feature_type="mask",
            geometry="cone",
            position={"x": 0, "y": 1.82, "z": 0.25},
            scale={"x": 0.1, "y": 0.2, "z": 0.25},
            rotation={"x": 90, "y": 0, "z": 0},
            color_source="custom",
            custom_color="#1a1a1a",
            roughness=0.4,
            description="Plague doctor mask",
        ),
    }
    return masks.get(mask_type, masks["plain"])


def create_cape(color: str = "#8B0000", length: str = "long") -> AppearanceFeature:
    """Create a flowing cape on the back."""
    lengths = {
        "short": {"y": 0.5, "scale_y": 0.4},
        "medium": {"y": 0.8, "scale_y": 0.7},
        "long": {"y": 0.6, "scale_y": 1.0},
    }
    cfg = lengths.get(length, lengths["long"])

    return AppearanceFeature(
        feature_type="cape",
        geometry="plane",
        position={"x": 0, "y": cfg["y"], "z": -0.25},
        scale={"x": 0.6, "y": cfg["scale_y"], "z": 0.1},
        rotation={"x": 10, "y": 0, "z": 0},
        color_source="custom",
        custom_color=color,
        opacity=0.95,
        animation="sway",
        animation_speed=0.3,
        animation_amplitude=0.05,
        description="Flowing cape",
    )


def create_robe(color: str = "#2F1B0C") -> AppearanceFeature:
    """Create a long robe covering the body."""
    return AppearanceFeature(
        feature_type="robe",
        geometry="cone",
        position={"x": 0, "y": 0.7, "z": 0},
        scale={"x": 0.45, "y": 1.2, "z": 0.35},
        color_source="custom",
        custom_color=color,
        roughness=0.8,
        description="Long robe",
    )


def create_book(color: str = "#4a3020", glowing: bool = False) -> List[AppearanceFeature]:
    """Create a book held in hand or floating."""
    features = [
        AppearanceFeature(
            feature_type="book_cover",
            geometry="box",
            position={"x": -0.4, "y": 0.75, "z": 0.15},
            scale={"x": 0.15, "y": 0.02, "z": 0.2},
            rotation={"x": 15, "y": 0, "z": -10},
            color_source="custom",
            custom_color=color,
            roughness=0.7,
            description="Book cover",
        ),
        AppearanceFeature(
            feature_type="book_pages",
            geometry="box",
            position={"x": -0.4, "y": 0.73, "z": 0.15},
            scale={"x": 0.13, "y": 0.04, "z": 0.18},
            rotation={"x": 15, "y": 0, "z": -10},
            color_source="custom",
            custom_color="#F5F5DC",
            roughness=0.9,
            description="Book pages",
        ),
    ]
    if glowing:
        features.append(AppearanceFeature(
            feature_type="book_glow",
            geometry="sphere",
            position={"x": -0.4, "y": 0.8, "z": 0.15},
            scale={"x": 0.2, "y": 0.1, "z": 0.25},
            color_source="custom",
            custom_color="#9966ff",
            opacity=0.3,
            emissive=True,
            emissive_intensity=0.5,
            light_source=True,
            light_color="#9966ff",
            light_intensity=0.3,
            light_range=1.5,
            description="Book magical glow",
        ))
    return features


def create_death_marker() -> List[AppearanceFeature]:
    """Create death visual effects."""
    return [
        AppearanceFeature(
            feature_type="death_pool",
            geometry="cylinder",
            position={"x": 0, "y": 0.02, "z": 0},
            scale={"x": 0.6, "y": 0.02, "z": 0.6},
            color_source="custom",
            custom_color="#330000",
            opacity=0.6,
            visible_when_dead=True,
            visible_to_self=False,
            description="Blood pool",
        ),
        AppearanceFeature(
            feature_type="death_x_left",
            geometry="box",
            position={"x": 0, "y": 1.9, "z": 0.23},
            scale={"x": 0.15, "y": 0.02, "z": 0.02},
            rotation={"x": 0, "y": 0, "z": 45},
            color_source="custom",
            custom_color="#1a1a1a",
            visible_when_dead=True,
            description="Dead eye X left",
        ),
        AppearanceFeature(
            feature_type="death_x_right",
            geometry="box",
            position={"x": 0, "y": 1.9, "z": 0.23},
            scale={"x": 0.15, "y": 0.02, "z": 0.02},
            rotation={"x": 0, "y": 0, "z": -45},
            color_source="custom",
            custom_color="#1a1a1a",
            visible_when_dead=True,
            description="Dead eye X right",
        ),
    ]


@dataclass
class ErzaehlerEvent:
    """Definition eines Erzähler-Events für eine Rolle."""

    event_id: str
    text: str
    anweisung: str
    bedingung: Dict[str, Any] = field(default_factory=dict)
    einmalig: bool = True


@dataclass
class HinweisConfig:
    """Hinweis-Konfiguration für eine Rolle."""

    kann_senden: bool = False
    verfuegbare_hinweise: List[str] = field(default_factory=list)
    hinweise_pro_tag: int = 0
    basis_chance: float = 0.0
    beschreibung: str = ""


# =============================================================================
# STATE ACCESS HELPERS (Module-level for use without Role instance)
# =============================================================================


def get_spieler_state(spieler: "Spieler", key: str, default: Any = None) -> Any:
    """
    Liest einen Zustandswert vom Spieler.

    Args:
        spieler: Der Spieler
        key: Der Schlüssel (z.B. "hexe.heiltrank" oder "global.verliebt_mit_id")
        default: Standardwert wenn nicht gefunden

    Returns:
        Der Zustandswert oder default
    """
    try:
        state_json = getattr(spieler, "rolle_zustand", None) or "{}"
        state = json.loads(state_json) if isinstance(state_json, str) else state_json
        return state.get(key, default)
    except (json.JSONDecodeError, AttributeError):
        return default


def set_spieler_state(spieler: "Spieler", key: str, value: Any) -> None:
    """
    Setzt einen Zustandswert auf dem Spieler.

    Args:
        spieler: Der Spieler
        key: Der Schlüssel (z.B. "hexe.heiltrank")
        value: Der zu speichernde Wert
    """
    try:
        state_json = getattr(spieler, "rolle_zustand", None) or "{}"
        state = json.loads(state_json) if isinstance(state_json, str) else {}
        state[key] = value
        spieler.rolle_zustand = json.dumps(state)
    except (json.JSONDecodeError, AttributeError):
        spieler.rolle_zustand = json.dumps({key: value})


def get_all_spieler_state(spieler: "Spieler") -> Dict[str, Any]:
    """Liest alle Zustandswerte eines Spielers."""
    try:
        state_json = getattr(spieler, "rolle_zustand", None) or "{}"
        return json.loads(state_json) if isinstance(state_json, str) else {}
    except (json.JSONDecodeError, AttributeError):
        return {}


def init_spieler_state(spieler: "Spieler", defaults: Dict[str, Any]) -> None:
    """Initialisiert den Spieler-Zustand mit Standardwerten (überschreibt nicht)."""
    current = get_all_spieler_state(spieler)
    for key, value in defaults.items():
        if key not in current:
            current[key] = value
    spieler.rolle_zustand = json.dumps(current)


def reset_spieler_state(spieler: "Spieler") -> None:
    """Setzt den kompletten Spieler-Zustand zurück."""
    spieler.rolle_zustand = "{}"


def has_global_state(spieler: "Spieler", state_key: str) -> bool:
    """Prüft ob ein Spieler einen bestimmten globalen State hat (truthy)."""
    value = get_spieler_state(spieler, state_key)
    return value is not None and value is not False and value != 0


def get_players_with_state(
    spieler_liste: List["Spieler"], state_key: str, value: Any = None
) -> List["Spieler"]:
    """
    Findet alle Spieler die einen bestimmten State haben.

    Args:
        spieler_liste: Liste aller Spieler
        state_key: Der State-Key (z.B. "global.verliebt_mit_id")
        value: Optional - wenn gesetzt, nur Spieler mit diesem Wert

    Returns:
        Liste der Spieler mit dem State
    """
    result = []
    for s in spieler_liste:
        state_value = get_spieler_state(s, state_key)
        if value is not None:
            if state_value == value:
                result.append(s)
        elif state_value is not None and state_value is not False and state_value != 0:
            result.append(s)
    return result


def get_player_visual_effects(
    spieler: "Spieler",
    global_state_defs: Dict[str, "GlobalStateDefinition"],
    viewer_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Ermittelt alle visuellen Effekte die für einen Spieler angezeigt werden sollen.

    Args:
        spieler: Der Spieler dessen Effekte ermittelt werden
        global_state_defs: Dict aller GlobalStateDefinitions
        viewer_id: ID des betrachtenden Spielers (für Sichtbarkeit)

    Returns:
        Liste von Effekt-Dicts mit css_class, icon, etc.
    """
    effects = []
    all_state = get_all_spieler_state(spieler)

    for key, value in all_state.items():
        if not key.startswith("global."):
            continue
        if value is None or value is False or value == 0:
            continue

        # Suche GlobalStateDefinition
        if key in global_state_defs:
            gsd = global_state_defs[key]
            effects.append(
                {
                    "key": key,
                    "value": value,
                    "css_class": gsd.css_class,
                    "icon": gsd.icon,
                    "visual_effect": (
                        gsd.visual_effect.value if gsd.visual_effect else None
                    ),
                    "name": gsd.name,
                }
            )

    return effects


def get_role_state_display(spieler: "Spieler") -> List[Dict[str, Any]]:
    """
    Ermittelt alle anzeigbaren Zustandsfelder für einen Spieler basierend auf
    seiner Rolle und den state_fields() der Rolle.

    Verwendet für die dynamische Sidebar-Anzeige statt hardcoded Hexe/Jäger checks.

    Args:
        spieler: Der Spieler dessen Status angezeigt werden soll

    Returns:
        Liste von Dicts mit {name, icon, label, value, display_value}
    """
    from . import RoleRegistry

    if not spieler.rolle:
        return []

    role = RoleRegistry.get(spieler.rolle)
    if not role:
        return []

    state_items = []
    all_state = get_all_spieler_state(spieler)

    # Hole State-Präfix für diese Rolle (z.B. "hexe", "jaeger")
    role_prefix = (
        spieler.rolle.lower()
        .replace(" ", "_")
        .replace("ä", "a")
        .replace("ü", "u")
        .replace("ö", "o")
    )

    for field in role.state_fields():
        # Suche State mit vollem Key
        full_key = f"{role_prefix}.{field.name}"
        value = all_state.get(full_key, field.default)

        # Nur Felder mit Icon/Beschreibung sind für Anzeige gedacht
        if not field.icon and not field.beschreibung:
            continue

        # Bestimme Anzeigewert für Bool-Typen
        if field.typ == StateType.BOOL:
            display_value = "Vorhanden" if value else "Verbraucht"
            if field.name == "schuss":
                display_value = "Bereit" if value else "Abgefeuert"
        else:
            display_value = str(value) if value is not None else "Unbekannt"

        state_items.append(
            {
                "name": field.name,
                "icon": field.icon,
                "label": field.beschreibung or field.name,
                "value": value,
                "display_value": display_value,
                "css_class": field.css_class,
            }
        )

    return state_items


# =============================================================================
# DATACLASSES
# =============================================================================


@dataclass
class DistributionConfig:
    """Konfiguration für die dynamische Rollenverteilung."""

    min_players: int = 0
    # Lambda function: (player_count) -> role_count
    # Standard: 1 wenn min_players erreicht
    count_func: Callable[[int], int] = field(default=lambda n: 1)
    priority: int = 50  # Höher = wird zuerst verteilt
    # Muss zusammen mit mind. einer dieser Rollen im Spiel sein
    requires_roles: List[str] = field(default_factory=list)
    # Darf NICHT mit diesen Rollen zusammen sein (z.B. Werwolf vs Weißer Wolf Varianten)
    exclusive_with: List[str] = field(default_factory=list)
    # True = füllt verbleibende Plätze auf (z.B. Dorfbewohner)
    is_filler: bool = False


@dataclass
class WinCondition:
    """Eine dynamische Gewinnbedingung (z.B. für Verliebte)."""

    id: str  # Eindeutige ID (z.B. "verliebte_win")
    # (spieler, kontext) -> bool
    check_func: Callable[["Spieler", "SpielKontext"], bool]
    team_override: Optional[Team] = None
    description: str = ""
    priority: int = 0


@dataclass
class LoseCondition:
    """Eine dynamische Niederlagen-/Todesbedingung (z.B. Partner stirbt)."""

    id: str
    trigger: str  # Event trigger (z.B. "on_spieler_stirbt")
    # (spieler, kontext, trigger_data) -> bool (True = condition met)
    check_func: Callable[["Spieler", "SpielKontext", Any], bool]
    effect: str = "death"  # "death", "convert", "custom"
    description: str = ""


@dataclass
class RollenInfo:
    """Statische Informationen ueber eine Rolle (fuer UI/Dokumentation)."""

    id: int
    name: str
    team: Team
    kategorie: Kategorie
    beschreibung: str
    icon: str  # FontAwesome class (e.g., "fa-solid fa-eye")
    farbe: str  # Hex color code (e.g., "#7c3aed")
    prioritaet: int = (
        100  # Lower = earlier in night order (e.g., Amor=5, Werwolf=50, Hexe=90)
    )
    erzaehler_nacht: Optional[str] = None
    erzaehler_tag: Optional[str] = None
    hinweis_config: Optional[str] = None
    erweiterung: Erweiterung = Erweiterung.BASISSPIEL

    # Phase ordering and dependencies
    requires_roles: List[str] = field(
        default_factory=list
    )  # Roles that must act before this one
    requires_phases: List[str] = field(
        default_factory=list
    )  # Generic phases that must happen first

    css_class: str = ""  # Frontend CSS class name override

    # Visual styling fields for UI
    avatar_gradient_from: str = ""  # e.g., "#b91c1c"
    avatar_gradient_to: str = ""  # e.g., "#7f1d1d"
    avatar_border_color: str = ""  # e.g., "#ef4444"
    badge_emoji: str = ""  # e.g., "🐺"
    # Dynamic Distribution Configuration
    distribution: Optional[DistributionConfig] = None

    # Extension pack for UI filtering
    @property
    def extension_pack(self) -> str:
        """Returns extension pack identifier for frontend filtering."""
        pack_map = {
            Erweiterung.BASISSPIEL: "base",
            Erweiterung.NEUMOND: "neumond",
            Erweiterung.GEMEINDE: "gemeinde",
            Erweiterung.CHARAKTERE: "charaktere",
            Erweiterung.COMMUNITY: "community",
        }
        if self.erweiterung is None:
            raise ValueError("RollenInfo.erweiterung is required")
        return pack_map.get(self.erweiterung, "community")

    @property
    def computed_css_class(self) -> str:
        """Auto-generate CSS class from name if not set."""
        if self.css_class:
            return self.css_class
        # Normalize German characters for CSS class names
        return (
            self.name.lower()
            .replace(" ", "-")
            .replace("ä", "ae")
            .replace("ö", "oe")
            .replace("ü", "ue")
            .replace("ß", "ss")
        )


@dataclass
class AktionsErgebnis:
    """Ergebnis einer Rollen-Aktion."""

    erfolg: bool
    nachricht: Optional[str] = None
    ziel_spieler_id: Optional[int] = None
    effekte: Dict[str, Any] = field(default_factory=dict)
    log_sichtbar_fuer: str = "alle"  # alle, erzaehler, werwolf, spieler_id
    # State changes to apply after action (key -> value)
    state_updates: Dict[str, Any] = field(default_factory=dict)
    # Private structured info for specific players (player_id -> data dict)
    private_infos: Dict[int, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class SpielKontext:
    """Kontext für Rollen-Aktionen (Dependency Injection)."""

    raum_id: int
    runde: int
    phase: Phase
    aktiver_spieler_id: int
    lebende_spieler: List[int]
    tote_spieler: List[int]
    werwolf_opfer_id: Optional[int] = None
    aktionen_diese_runde: List[Dict[str, Any]] = field(default_factory=list)
    # Dynamically added attributes
    spieler_rollen: Dict[int, Any] = field(default_factory=dict)
    spieler_namen: Dict[int, str] = field(default_factory=dict)
    spieler_teams: Dict[int, Any] = field(default_factory=dict)

    @property
    def aktuelle_runde(self) -> int:
        """Alias für Runde (wird von einigen Rollen verwendet)."""
        return self.runde

    def hat_spieler_rolle(self, spieler_id: int, rolle: str) -> bool:
        """Prüft, ob ein Spieler eine bestimmte Rolle hat."""
        return self.spieler_rollen.get(spieler_id) == rolle


@dataclass
class RoleAction:
    """
    A role action tied to a handler method.
    
    Every RoleAction maps directly to a handler method on the Role class.
    This enables fully dynamic action handling without hardcoded switches.
    
    Example:
        RoleAction(
            action_id="heilen",
            label="Heilen",
            icon="fa-heart",
            handler="handle_heilen",  # Calls self.handle_heilen()
            action_type="heilen"
        )
    """
    action_id: str              # Unique identifier
    label: str                  # UI button text
    handler: str                # Method name on Role to call
    action_type: str            # AktionsTyp value (for compatibility)
    icon: str = ""              # FontAwesome icon class
    css_class: str = "btn-primary"
    requires_target: bool = True
    target_filter: str = "lebende"  # lebende, tote, alle, andere, nachbarn
    requires_confirmation: bool = False
    tooltip: Optional[str] = None
    # Condition function (spieler, kontext) -> bool
    enabled_condition: Optional[Callable[["Spieler", SpielKontext], bool]] = None
    
    def is_enabled(self, spieler: "Spieler", kontext: "SpielKontext") -> bool:
        """Check if this action is currently enabled."""
        if self.enabled_condition is not None:
            return self.enabled_condition(spieler, kontext)
        return True
    
    def to_dict(self, spieler: Optional["Spieler"] = None, 
                kontext: Optional["SpielKontext"] = None) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "action_id": self.action_id,
            "label": self.label,
            "handler": self.handler,
            "action_type": self.action_type,
            "icon": self.icon,
            "css_class": self.css_class,
            "requires_target": self.requires_target,
            "target_filter": self.target_filter,
            "requires_confirmation": self.requires_confirmation,
            "tooltip": self.tooltip,
        }
        # Include enabled state if context available
        if spieler is not None and kontext is not None:
            result["enabled"] = self.is_enabled(spieler, kontext)
        return result


@dataclass
class UIButton:
    """Definition for a UI button in the action panel."""

    label: str
    action_type: str
    icon: Optional[str] = None
    css_class: str = "btn-primary"
    requires_confirmation: bool = False


@dataclass
class RollenUI:
    """UI definition for a role's action panel."""

    title: str
    instructions: str
    # NEW: Action-driven architecture - each action tied to handler
    actions: List[RoleAction] = field(default_factory=list)
    # Legacy button support (deprecated, use actions instead)
    buttons: List[UIButton] = field(default_factory=list)
    requires_target: bool = True
    allow_multiple_targets: bool = False
    min_targets: int = 1
    max_targets: int = 1
    allow_self_target: bool = False
    can_skip: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization (legacy compatibility)."""
        return {
            "title": self.title,
            "instructions": self.instructions,
            "actions": [a.to_dict() for a in self.actions],
            "buttons": [
                {
                    "label": btn.label,
                    "action_type": btn.action_type,
                    "icon": btn.icon,
                    "css_class": btn.css_class,
                    "requires_confirmation": btn.requires_confirmation,
                }
                for btn in self.buttons
            ],
            "requires_target": self.requires_target,
            "allow_multiple_targets": self.allow_multiple_targets,
            "min_targets": self.min_targets,
            "max_targets": self.max_targets,
            "allow_self_target": self.allow_self_target,
            "can_skip": self.can_skip,
        }

    def to_dict_with_context(
        self, spieler: "Spieler", kontext: "SpielKontext"
    ) -> Dict[str, Any]:
        """Convert to dict with context-aware action states."""
        result = self.to_dict()
        # Replace actions with context-aware versions
        result["actions"] = [
            a.to_dict(spieler, kontext) 
            for a in self.actions 
            if a.is_enabled(spieler, kontext)
        ]
        return result


class Role(ABC):
    """
    Abstrakte Basisklasse für alle Rollen.

    Jede Rolle muss die abstrakten Methoden implementieren
    und kann optionale Trigger-Methoden überschreiben.

    STATE MANAGEMENT:
    Rollen definieren ihre Zustandsfelder über state_fields().
    Der Zugriff erfolgt über get_state()/set_state() mit automatischer
    Namespace-Verwaltung (z. B. "hexe.heiltrank").
    """

    # === ABSTRAKTE EIGENSCHAFTEN (müssen in jeder Rolle definiert sein) ===

    @property
    @abstractmethod
    def info(self) -> RollenInfo:
        """Gibt die statischen Informationen der Rolle zurück."""
        pass

    # === PHASEN-LOGIK ===

    def get_phase_start_info(
        self, spieler: "Spieler", kontext: "SpielKontext"
    ) -> Optional[Dict[str, Any]]:
        """
        Gibt Informationen zurück, die dem Spieler zu Beginn seiner Phase angezeigt werden sollen.

        Zum Beispiel:
        - Die Hexe sieht das Werwolf-Opfer
        - Der Seher sieht wen er gewählt hat (falls Vorwahl-System)

        Returns:
            Dict mit Informationen für das Frontend oder None
        """
        # logger.debug(f"Getting phase start info for {self.info.name} (Player: {spieler.name})") # Too verbose
        return None

    # === STATE MANAGEMENT ===

    def state_fields(self) -> List[StateField]:
        """
        Definiert die Zustandsfelder dieser Rolle.

        Jede Rolle überschreibt diese Methode um ihre
        spezifischen Datenfelder zu definieren.

        Returns:
            Liste von StateField-Definitionen

        Beispiel:
            def state_fields(self):
                return [
                    StateField("heiltrank", StateType.BOOL, True),
                    StateField("gifttrank", StateType.BOOL, True),
                ]
        """
        return []

    def global_state_definitions(self) -> List[GlobalStateDefinition]:
        """
        Definiert globale States die diese Rolle auf ANDERE Spieler setzen kann.

        Diese werden beim Registry-Laden gesammelt und ermöglichen:
        - Dynamische Abfragen ("finde alle Verliebten")
        - Automatische UI-Effekte (Herz bei Verliebten)
        - Keine hardcoded Checks in game_logic

        Returns:
            Liste von GlobalStateDefinition

        Beispiel (Amor):
            def global_state_definitions(self):
                return [
                    GlobalStateDefinition(
                        key="global.verliebt_mit_id",
                        name="Verliebt",
                        typ=StateType.PLAYER_ID,
                        visual_effect=StateVisualEffect.HEART,
                        css_class="verliebt-partner",
                        icon="💕",
                        query_name="verliebte",
                        defined_by="Amor",
                    )
                ]
        """
        return []

    def get_sichtbare_rolle(self, spieler: "Spieler") -> str:
        """
        Gibt die Rolle zurück die der Spieler für SICH SELBST sieht.

        Wichtig für Rollen die ihre Identität ändern können (Hund, Wildes Kind).
        Kann überschrieben werden um dynamisch die sichtbare Rolle zu ändern.

        Args:
            spieler: Der Spieler mit dieser Rolle

        Returns:
            Der Rollenname der angezeigt werden soll
        """
        return self.info.name

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """
        Gibt die 3D/2D Modell-Definition für diese Rolle zurück.

        Kann überschrieben werden für dynamische Modell-Auswahl
        (z.B. Hund -> Werhund wenn verwandelt).

        Args:
            spieler: Der Spieler mit dieser Rolle

        Returns:
            RollenModell-Definition
        """
        return RollenModell(
            modell_id=self.info.name.lower().replace(" ", "_"),
            anzeige_name=self.info.name,
        )

    def get_nacht_events(self) -> List[NachtEvent]:
        """
        Gibt Nacht-Events zurück die diese Rolle triggert.

        Diese Events sind für ALLE Spieler sichtbar/hörbar.

        Beispiel (Kuh):
            def get_nacht_events(self):
                return [
                    NachtEvent(
                        event_id="kuh_muht",
                        sound_file="moo.mp3",
                        text="Die Kuh muht in der Nacht...",
                        phases=["nacht"],
                    )
                ]
        """
        return []

    def get_ui_buttons_for_others(self) -> List[UIButtonDefinition]:
        """
        Gibt UI-Buttons zurück die diese Rolle für ANDERE Spieler hinzufügt.

        Ermöglicht Rollen, Interaktions-Buttons für andere Spieler zu definieren.

        Beispiel (Kuh):
            def get_ui_buttons_for_others(self):
                return [
                    UIButtonDefinition(
                        button_id="milch_trinken",
                        label="Milch trinken",
                        action_type="milch_trinken",
                        icon="fa-solid fa-glass",
                        show_to=lambda s, k: s.rolle in ["Dorfbewohner", ...],
                        on_click=self.handle_milch_trinken,
                    )
                ]
        """
        return []

    def get_win_conditions(self) -> List[WinCondition]:
        """
        Gibt die Gewinnbedingungen dieser Rolle zurück.

        Diese werden in jeder Runde überprüft. Wenn eine Bedingung zutrifft,
        endet das Spiel.

        Returns:
            Liste von WinCondition-Objekten
        """
        return []

    def get_lose_conditions(self) -> List[LoseCondition]:
        """
        Gibt die Niederlagen-/Trigger-Bedingungen dieser Rolle zurück.

        Diese definieren wann ein Spieler durch Events (z.B. Tod eines anderen)
        stirbt oder seinen Status ändert.

        Beispiel:
            return [
                LoseCondition(
                    id="lover_dies",
                    trigger="on_spieler_stirbt",
                    check_func=self.check_lover_death,
                    effect="death"
                )
            ]
        """
        return []

    def _state_key(self, field_name: str) -> str:
        """Generiert den vollständigen State-Key mit Rollen-Namespace."""
        namespace = (
            self.info.name.lower()
            .replace(" ", "_")
            .replace("ä", "ae")
            .replace("ö", "oe")
            .replace("ü", "ue")
            .replace("ß", "ss")
        )
        return f"{namespace}.{field_name}"

    def get_state(
        self, spieler: "Spieler", field_name: str, default: Any = None
    ) -> Any:
        """
        Liest einen Zustandswert für diese Rolle.

        Args:
            spieler: Der Spieler
            field_name: Name des Feldes (ohne Namespace)
            default: Standardwert (überschreibt StateField.default)

        Returns:
            Der Zustandswert
        """
        key = self._state_key(field_name)

        # Finde StateField für korrekten Default
        if default is None:
            for sf in self.state_fields():
                if sf.name == field_name:
                    default = sf.default
                    break

        return get_spieler_state(spieler, key, default)

    def set_state(self, spieler: "Spieler", field_name: str, value: Any) -> None:
        """
        Setzt einen Zustandswert für diese Rolle.

        Args:
            spieler: Der Spieler
            field_name: Name des Feldes (ohne Namespace)
            value: Der zu speichernde Wert
        """
        key = self._state_key(field_name)
        set_spieler_state(spieler, key, value)

    def init_state(self, spieler: "Spieler") -> None:
        """
        Initialisiert den Zustand für diese Rolle mit Standardwerten.

        Wird beim Spielstart aufgerufen.
        """
        defaults = {}
        for sf in self.state_fields():
            key = self._state_key(sf.name)
            defaults[key] = sf.default

        if defaults:
            init_spieler_state(spieler, defaults)

    def get_all_state(self, spieler: "Spieler") -> Dict[str, Any]:
        """
        Liest alle Zustandswerte dieser Rolle.

        Returns:
            Dict mit field_name -> value (ohne Namespace)
        """
        all_state = get_all_spieler_state(spieler)
        namespace = self._state_key("")

        result = {}
        for key, value in all_state.items():
            if key.startswith(namespace):
                field_name = key[len(namespace) :]
                result[field_name] = value
        return result

    # === ERZÄHLER-EVENTS ===

    def get_erzaehler_events(self) -> List[ErzaehlerEvent]:
        """
        Gibt die Erzähler-Events dieser Rolle zurück.

        Überschreibe diese Methode um rollenspezifische
        Erzähler-Texte zu definieren.

        Returns:
            Liste von ErzaehlerEvent-Definitionen
        """
        events = []

        # Standard-Events aus RollenInfo
        if self.info.erzaehler_nacht:
            events.append(
                ErzaehlerEvent(
                    event_id=f"{self.info.name.lower().replace(' ', '_')}_nacht",
                    text=self.info.erzaehler_nacht,
                    anweisung=self.info.erzaehler_nacht,
                    einmalig=False,
                )
            )

        if self.info.erzaehler_tag:
            events.append(
                ErzaehlerEvent(
                    event_id=f"{self.info.name.lower().replace(' ', '_')}_tag",
                    text=self.info.erzaehler_tag,
                    anweisung=self.info.erzaehler_tag,
                    einmalig=False,
                )
            )

        return events

    # === HINWEIS-SYSTEM ===

    def get_hinweis_config(self) -> HinweisConfig:
        """
        Gibt die Hinweis-Konfiguration dieser Rolle zurück.

        Überschreibe diese Methode für Rollen die aktiv
        Hinweise senden können (z.B. Selbstmörder).
        """
        team = self.info.team
        if team == Team.WERWOLF:
            return HinweisConfig(basis_chance=0.15)
        elif team == Team.DORF:
            return HinweisConfig(basis_chance=0.05)
        elif team == Team.SOLO:
            return HinweisConfig(basis_chance=0.10)
        return HinweisConfig(basis_chance=0.08)

    # === STANDARD-EIGENSCHAFTEN (können überschrieben werden) ===

    @property
    def requires_victim_info(self) -> bool:
        """
        Gibt an ob diese Rolle Informationen über das Werwolf-Opfer benötigt.

        Überschreibe auf True für Rollen wie Hexe, die wissen müssen
        wer von den Werwölfen gewählt wurde.
        """
        return False

    @property
    def kann_hinweis_senden(self) -> bool:
        """Kann diese Rolle aktiv Hinweise auf sich ziehen?"""
        return self.get_hinweis_config().kann_senden

    @property
    def verfuegbare_hinweise(self) -> List[str]:
        """Welche Hinweise kann die Rolle senden?"""
        return self.get_hinweis_config().verfuegbare_hinweise

    @property
    def hinweise_pro_tag(self) -> int:
        """Wie viele Hinweise pro Tag?"""
        return self.get_hinweis_config().hinweise_pro_tag

    @property
    def basis_hinweis_chance(self) -> float:
        """Basis-Wahrscheinlichkeit für automatische Hinweise."""
        return self.get_hinweis_config().basis_chance

    @property
    def is_group_action(self) -> bool:
        """
        Gibt an ob diese Rolle als Gruppe agiert (alle müssen abstimmen).

        Überschreibe auf True für Rollen wie Werwolf, Drei Brüder, etc.
        wo alle Spieler der Rolle gemeinsam eine Entscheidung treffen.

        Returns:
            True wenn Gruppenabstimmung, False für Einzelaktionen
        """
        return False

    @property
    def shared_phase_name(self) -> Optional[str]:
        """
        Gibt einen gemeinsamen Phasennamen zurück falls mehrere Rollen
        in der gleichen Phase agieren.

        Überschreibe für Werwolf-Varianten die alle in 'werwolf_phase' agieren.

        Returns:
            Gemeinsamer Phasenname oder None für eigene Phase
        """
        return None

    @property
    def sichtbar_als(self) -> SichtTyp:
        """Wie erscheint diese Rolle der Seherin?"""
        if self.info.team == Team.WERWOLF:
            return SichtTyp.WERWOLF
        return SichtTyp.DORF

    def sichtbar_als_fuer(self, seher_rolle: str) -> SichtTyp:
        """Wie erscheint diese Rolle einer bestimmten Seher-Rolle?"""
        return self.sichtbar_als

    def sichtbare_rolle_fuer(self, seher_rolle: str) -> str:
        """Welche Rollenbezeichnung sieht eine bestimmte Seher-Rolle?"""
        return self.info.name

    @property
    def aktions_typ(self) -> AktionsTyp:
        """Welche Aktion führt diese Rolle aus?"""
        return AktionsTyp.KEINE

    @abstractmethod
    def is_active_on_first_night(self) -> bool:
        """Determines if the role acts on the first night."""
        pass

    @abstractmethod
    def is_active_on_every_night(self) -> bool:
        """Determines if the role acts on subsequent nights."""
        pass

    @abstractmethod
    def get_ui_definition(self) -> "RollenUI":
        """Defines the UI for the role's action phase."""
        pass

    @property
    def kann_ziel_waehlen(self) -> bool:
        """Muss ein Ziel für die Aktion gewählt werden?"""
        # Derived from UI definition implicitly or lifecycle
        # We keep this for backward compatibility or logic that uses it
        # Default behavior: active roles usually select targets unless specified otherwise
        return self.is_active_on_first_night() or self.is_active_on_every_night()

    @property
    def erlaubte_ziele(self) -> str:
        """Welche Spieler können als Ziel gewählt werden?"""
        return "lebende"  # lebende, tote, alle, andere, nachbarn, werwolf

    # === TRIGGER-METHODEN (werden bei Events aufgerufen) ===

    def on_spiel_start(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Wird beim Spielstart aufgerufen.

        Nützlich für:
        - Amor: Verliebte wählen
        - Wildes Kind: Vorbild wählen
        - Freimaurer: Sich erkennen
        """
        return None

    def on_nacht_start(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Wird zu Beginn jeder Nacht aufgerufen.

        Nützlich für:
        - Status-Resets
        - Bedingte Aktivierungen
        """
        return None

    def on_nacht_aktion(
        self,
        spieler: "Spieler",
        ziel: Optional["Spieler"],
        kontext: "SpielKontext",
        aktion: str = None,
    ) -> Optional[AktionsErgebnis]:
        """
        Wird aufgerufen, wenn der Spieler seine Nacht-Aktion ausführt.

        Args:
            spieler: Der handelnde Spieler
            ziel: Das gewählte Ziel (oder None)
            kontext: Der aktuelle Spielkontext
            aktion: Der Typ der Aktion (z.B. "heilen", "vergiften") - optional

        Returns:
            AktionsErgebnis oder None (wenn Aktion ungültig)
        """
        logger.debug(
            f"Executing night action for {self.info.name} (Player: {spieler.name}, Action: {aktion})"
        )
        return None

    def on_tag_aktion(
        self, spieler: "Spieler", ziel: Optional["Spieler"], kontext: "SpielKontext"
    ) -> Optional[AktionsErgebnis]:
        """
        Wird aufgerufen, wenn der Spieler seine Tag-Aktion ausführt.
        """
        logger.debug(
            f"Executing day action for {self.info.name} (Player: {spieler.name})"
        )
        return None

    def on_spieler_stirbt(
        self, spieler: "Spieler", opfer: "Spieler", kontext: "SpielKontext"
    ) -> Optional[AktionsErgebnis]:
        """
        Trigger: Ein Spieler stirbt.

        Args:
            spieler: Der Spieler mit dieser Rolle (Observer)
            opfer: Der gestorbene Spieler
            kontext: Spielkontext
        """
        return None

    def on_eigener_tod(
        self, spieler: "Spieler", todesursache: str, kontext: "SpielKontext"
    ) -> Optional[AktionsErgebnis]:
        """
        Trigger: Diese Rolle stirbt.

        Wird aufgerufen wenn der Spieler mit dieser Rolle stirbt.
        Ermöglicht letzte Aktionen (z.B. Jäger schießt).

        Args:
            spieler: Der sterbende Spieler
            todesursache: Art des Todes ("werwolf", "hexe", "hinrichtung", "liebeskummer", etc.)
            kontext: Spielkontext

        Returns:
            AktionsErgebnis mit möglichen Effekten (z.B. trigger_jaeger_phase)
        """
        return None

    def on_hinrichtung(
        self, spieler: "Spieler", verurteilter: "Spieler", kontext: "SpielKontext"
    ) -> Optional[AktionsErgebnis]:
        """
        Trigger: Ein Spieler wird durch Abstimmung hingerichtet.

        Args:
            spieler: Der Spieler mit dieser Rolle (Observer)
            verurteilter: Der hingerichtete Spieler
            kontext: Spielkontext
        """
        return None

    def on_angriff(
        self, spieler: "Spieler", angreifer: "Spieler", kontext: "SpielKontext"
    ) -> Optional[AktionsErgebnis]:
        """
        Trigger: Diese Rolle wird angegriffen (aber lebt noch).

        Ermöglicht Rollen, auf Angriffe zu reagieren bevor sie sterben.
        Z.B. Alte Vettel überlebt ersten Angriff.

        Args:
            spieler: Der angegriffene Spieler mit dieser Rolle
            angreifer: Der angreifende Spieler
            kontext: Spielkontext
        """
        return None

    def on_geheilt(
        self, spieler: "Spieler", heiler: "Spieler", kontext: "SpielKontext"
    ) -> Optional[AktionsErgebnis]:
        """
        Trigger: Diese Rolle wird geheilt.

        Args:
            spieler: Der geheilte Spieler
            heiler: Der heilende Spieler
            kontext: Spielkontext
        """
        return None

    def on_geschuetzt(
        self, spieler: "Spieler", beschuetzer: "Spieler", kontext: "SpielKontext"
    ) -> Optional[AktionsErgebnis]:
        """
        Trigger: Diese Rolle wird beschützt.

        Args:
            spieler: Der beschützte Spieler
            beschuetzer: Der beschützende Spieler (z.B. Leibwächter)
            kontext: Spielkontext
        """
        return None

    def on_verwandlung(
        self, spieler: "Spieler", neue_rolle: str, kontext: "SpielKontext"
    ) -> Optional[AktionsErgebnis]:
        """
        Trigger: Diese Rolle verwandelt sich.

        Für Rollen wie Wildes Kind, Wolfshund, die ihre Rolle wechseln können.

        Args:
            spieler: Der sich verwandelnde Spieler
            neue_rolle: Name der neuen Rolle
            kontext: Spielkontext
        """
        return None

    def on_infektion(
        self, spieler: "Spieler", infiziert_von: "Spieler", kontext: "SpielKontext"
    ) -> Optional[AktionsErgebnis]:
        """
        Trigger: Diese Rolle wird infiziert (z.B. durch Urwolf).

        Args:
            spieler: Der infizierte Spieler
            infiziert_von: Der infizierende Spieler
            kontext: Spielkontext
        """
        return None

    def on_verzaubert(
        self, spieler: "Spieler", verzaubert_von: "Spieler", kontext: "SpielKontext"
    ) -> Optional[AktionsErgebnis]:
        """
        Trigger: Diese Rolle wird verzaubert (z.B. durch Flötenspieler).

        Args:
            spieler: Der verzauberte Spieler
            verzaubert_von: Der verzaubernde Spieler
            kontext: Spielkontext
        """
        return None

    def on_abstimmung(
        self, spieler: "Spieler", ziel: "Spieler", stimmen: int, kontext: "SpielKontext"
    ) -> Optional[AktionsErgebnis]:
        """
        Trigger: Eine Abstimmung findet statt.

        Args:
            spieler: Der Spieler mit dieser Rolle
            ziel: Der Spieler mit den meisten Stimmen
            stimmen: Anzahl der Stimmen gegen das Ziel
            kontext: Spielkontext
        """
        return None

    def on_phase_start(
        self, spieler: "Spieler", phase: str, kontext: "SpielKontext"
    ) -> Optional[AktionsErgebnis]:
        """
        Trigger: Eine Phase beginnt.

        Args:
            spieler: Der Spieler mit dieser Rolle
            phase: Name der beginnenden Phase
            kontext: Spielkontext
        """
        return None

    def on_phase_end(
        self, spieler: "Spieler", phase: str, kontext: "SpielKontext"
    ) -> Optional[AktionsErgebnis]:
        """
        Trigger: Eine Phase endet.

        Args:
            spieler: Der Spieler mit dieser Rolle
            phase: Name der endenden Phase
            kontext: Spielkontext
        """
        return None

    def on_runde_start(
        self, spieler: "Spieler", runde: int, kontext: "SpielKontext"
    ) -> Optional[AktionsErgebnis]:
        """
        Trigger: Eine neue Runde beginnt.

        Args:
            spieler: Der Spieler mit dieser Rolle
            runde: Die Rundennummer
            kontext: Spielkontext
        """
        return None

    def on_runde_end(
        self, spieler: "Spieler", runde: int, kontext: "SpielKontext"
    ) -> Optional[AktionsErgebnis]:
        """
        Trigger: Eine Runde endet.

        Args:
            spieler: Der Spieler mit dieser Rolle
            runde: Die Rundennummer
            kontext: Spielkontext
        """
        return None

    # === MISSING HOOK METHODS (found in roles, added to base) ===

    def on_angegriffen(
        self, spieler: "Spieler", angreifer: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Trigger: Dieser Spieler wird angegriffen (VOR Todesauflösung).

        Anders als on_angriff (Observer-Pattern) wird diese Methode
        AUF dem angegriffenen Spieler aufgerufen.

        Return AktionsErgebnis mit erfolg=False um den Angriff zu BLOCKIEREN.

        Beispiel: Oma blockiert Werwolf-Angriffe.

        Args:
            spieler: Der angegriffene Spieler mit dieser Rolle
            angreifer: Der angreifende Spieler
            kontext: Spielkontext

        Returns:
            AktionsErgebnis mit erfolg=False zum Blockieren, None sonst
        """
        return None

    def ist_einmal_faehigkeit(self) -> bool:
        """
        Gibt True zurück wenn die Fähigkeit nur einmal pro Spiel nutzbar ist.

        Überschreiben für Rollen wie Inquisitor, Tanklastwagenfahrer, etc.

        Returns:
            True wenn einmalige Fähigkeit, False sonst (default)
        """
        return False

    def ist_immun_gegen(self, angriffs_typ: str) -> bool:
        """
        Prüft ob diese Rolle gegen einen bestimmten Angriffstyp immun ist.

        Args:
            angriffs_typ: Typ des Angriffs (z.B. "werwolf", "hexe", "jaeger")

        Returns:
            True wenn immun, False sonst
        """
        return False

    def kann_abstimmung_aendern(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> bool:
        """
        Prüft ob diese Rolle Abstimmungen modifizieren kann.

        Überschreiben für Rollen mit Stimm-Manipulation.

        Returns:
            True wenn Stimmen geändert werden können
        """
        return False

    def name_fuer(self, anfragender_spieler: "Spieler") -> str:
        """
        Gibt den Rollennamen zurück, wie er von einem anderen Spieler gesehen wird.

        Ermöglicht dynamische Namensanzeige (z.B. getarnte Rollen).

        Args:
            anfragender_spieler: Der Spieler der den Namen sehen möchte

        Returns:
            Rollenname aus Sicht des anfragenden Spielers
        """
        return self.info.name

    def on_tag_start(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Trigger: Der Tag beginnt.

        Wird zu Beginn der Tag-Phase aufgerufen.
        Nützlich für Tag-aktive Rollen.

        Args:
            spieler: Der Spieler mit dieser Rolle
            kontext: Spielkontext
        """
        return None

    # === DYNAMIC ACTION EXECUTION ===

    def execute_action(
        self,
        action_type: str,
        spieler: "Spieler",
        targets: List["Spieler"],
        kontext: "SpielKontext",
    ) -> Optional[AktionsErgebnis]:
        """
        Execute an action dynamically based on action_type.

        This is the main entry point for all role actions, replacing
        hardcoded action handlers in app.py.

        NEW: First looks up RoleAction by action_id/action_type and calls
        the handler method. Falls back to on_nacht_aktion for legacy.

        Args:
            action_type: The action identifier (e.g., "heilen", "vergiften")
            spieler: The player performing the action
            targets: List of target players (may be empty, single, or multiple)
            kontext: Game context

        Returns:
            AktionsErgebnis or None if action not handled
        """
        # Handle generic "skip" action
        if action_type == "skip":
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Du hast die Aktion übersprungen.",
                effekte={"skip": True, "aktion_ausgefuehrt": True},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )

        # NEW: Look up RoleAction by action_id and call handler
        ui_def = self.get_ui_definition()
        for action in ui_def.actions:
            if action.action_id == action_type or action.action_type == action_type:
                handler_name = action.handler
                if hasattr(self, handler_name):
                    handler = getattr(self, handler_name)
                    # Determine target based on targets list
                    ziel = targets[0] if len(targets) == 1 else None
                    # Call handler with appropriate args
                    try:
                        return handler(spieler, ziel, kontext)
                    except TypeError:
                        # Handler might have different signature, try without ziel
                        return handler(spieler, kontext)
                else:
                    logger.warning(
                        f"Role {self.info.name} action {action_type} has handler "
                        f"'{handler_name}' but method not found"
                    )

        # LEGACY: route to on_nacht_aktion for backwards compatibility
        import inspect

        kwargs = {}
        try:
            sig = inspect.signature(self.on_nacht_aktion)
            if "aktion" in sig.parameters:
                kwargs["aktion"] = action_type
        except Exception:
            # Fallback if signature inspection fails (e.g. on some decorated methods)
            pass

        if len(targets) == 1:
            return self.on_nacht_aktion(spieler, targets[0], kontext, **kwargs)
        elif len(targets) == 0:
            return self.on_nacht_aktion(spieler, None, kontext, **kwargs)
        else:
            # Multi-target: roles should override to handle this
            logger.warning(
                f"Role {self.info.name} received multi-target action but doesn't handle it"
            )
            return None

    def get_triggered_phases(self) -> List[SpecialPhaseConfig]:
        """
        Return special phases this role can trigger.

        For roles like Jäger that trigger out-of-order phases on death.
        Override this to define when and how special phases are triggered.

        Returns:
            List of SpecialPhaseConfig defining triggerable phases
        """
        return []

    def get_spiel_start(self, spieler: "Spieler", kontext: "SpielKontext"):
        """
        Trigger: Spiel startet.
        """
        logger.info(f"Game start trigger for {self.info.name} (Player: {spieler.name})")
        pass

    def get_erzaehler_nacht_text(self, kontext: "SpielKontext") -> str:
        """
        Gibt den Text zurück, den der Erzähler in der Nacht vorlesen soll.
        Kann dynamisch basierend auf dem Kontext sein.
        """
        # logger.debug(f"Getting narrator text for {self.info.name}") # Too verbose
        return self.info.erzaehler_nacht or ""

    def berechne_gewinn(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> Optional[Team]:
        """
        Prüft ob diese Rolle gewonnen hat (für Solo-Rollen).

        Return None wenn kein Gewinn, sonst das gewinnende Team.
        """
        return None

    # === HILFSMETHODEN ===

    def get_phase_name(self) -> str:
        """Gibt den Namen der Nacht-Phase zurueck."""
        return f"{self.info.name.lower().replace(' ', '_')}_phase"

    def validate_ziel(
        self, spieler: "Spieler", ziel: "Spieler", kontext: SpielKontext
    ) -> bool:
        """Prueft ob das Ziel gueltig ist."""
        if ziel is None and self.kann_ziel_waehlen:
            return False

        if self.erlaubte_ziele == "lebende":
            return ziel.id in kontext.lebende_spieler
        elif self.erlaubte_ziele == "tote":
            return ziel.id in kontext.tote_spieler
        elif self.erlaubte_ziele == "andere":
            return ziel.id != spieler.id and ziel.id in kontext.lebende_spieler
        elif self.erlaubte_ziele == "werwolf":
            return kontext.hat_spieler_rolle(ziel.id, "Werwolf")

        return True

    def has_voted_this_phase(self, spieler: "Spieler", kontext: SpielKontext) -> bool:
        """Prueft ob der Spieler bereits in dieser Phase gewaehlt hat."""
        # Check aktionen_diese_runde for existing vote from this player
        for aktion in kontext.aktionen_diese_runde:
            if aktion.get("von_spieler_id") == spieler.id:
                return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert role to dictionary for API/JSON."""
        # Get model definition - try to get actual model, use default if not available
        try:
            # Call get_modell_definition with None - roles should handle this gracefully
            raw_model = self.get_modell_definition(None)

            # Convert to dict format for JSON serialization
            model_def = {
                "modell_id": raw_model.modell_id,
                "anzeige_name": raw_model.anzeige_name,
                "beschreibung": raw_model.beschreibung,
                "seher_sicht": raw_model.seher_sicht,
                "appearance_self_alive": [f.to_dict() if hasattr(f, 'to_dict') else f.__dict__ for f in raw_model.appearance_self_alive] if raw_model.appearance_self_alive else [],
                "appearance_others_alive": [f.to_dict() if hasattr(f, 'to_dict') else f.__dict__ for f in raw_model.appearance_others_alive] if raw_model.appearance_others_alive else [],
                "appearance_dead": [f.to_dict() if hasattr(f, 'to_dict') else f.__dict__ for f in raw_model.appearance_dead] if raw_model.appearance_dead else [],
            }

            # Include body modifications if present
            if raw_model.body:
                model_def["body"] = raw_model.body.to_dict() if hasattr(raw_model.body, 'to_dict') else raw_model.body.__dict__

            # Include animations if present
            if raw_model.animations:
                model_def["animations"] = {
                    k: (v.to_dict() if hasattr(v, 'to_dict') else v.__dict__)
                    for k, v in raw_model.animations.items()
                }

            # Include hint effects if present
            if raw_model.hint_effects:
                model_def["hint_effects"] = [
                    (e.to_dict() if hasattr(e, 'to_dict') else e.__dict__)
                    for e in raw_model.hint_effects
                ]

            # Include sounds
            if raw_model.sound_on_action:
                model_def["sound_on_action"] = raw_model.sound_on_action
            if raw_model.sound_ambient:
                model_def["sound_ambient"] = raw_model.sound_ambient

        except Exception as e:
            # Fallback to basic model definition if get_modell_definition fails
            logger.debug(f"Could not get model definition for {self.info.name}: {e}")
            model_def = {
                "modell_id": self.info.name.lower().replace(" ", "_").replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss"),
                "anzeige_name": self.info.name,
                "beschreibung": f"{self.info.name} appearance",
                "appearance_self_alive": [],
                "appearance_others_alive": [],
                "appearance_dead": [],
                "seher_sicht": "good" if self.info.team == Team.DORF else "bad",
            }

        return {
            "id": self.info.id,
            "name": self.info.name,
            "team": self.info.team.value,
            "kategorie": self.info.kategorie.value,
            "beschreibung": self.info.beschreibung,
            "nacht_aktiv": self.is_active_on_first_night()
            or self.is_active_on_every_night(),  # Derived
            "prioritaet": self.info.prioritaet,
            "icon": self.info.icon,
            "farbe": self.info.farbe,
            "erzaehler_nacht": self.info.erzaehler_nacht,
            "erzaehler_tag": self.info.erzaehler_tag,
            "hinweis_config": self.info.hinweis_config,
            "erweiterung": self.info.erweiterung.value,
            # Visual Styling
            "avatar_gradient_from": self.info.avatar_gradient_from,
            "avatar_gradient_to": self.info.avatar_gradient_to,
            "avatar_border_color": self.info.avatar_border_color,
            "badge_emoji": self.info.badge_emoji,
            # Village 3D Model Definition with full appearance data
            "model": model_def,
            "state_fields": [
                {
                    "name": sf.name,
                    "typ": sf.typ.value,
                    "default": sf.default,
                    "beschreibung": sf.beschreibung,
                }
                for sf in self.state_fields()
            ],
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(team={self.info.team.value})>"
