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
class RollenModell:
    """
    Definition des 3D/2D Modells für eine Rolle.

    Ermöglicht dynamische Modell-Definitionen pro Rolle.
    """

    modell_id: str  # z.B. "hund", "werhund", "kuh"
    anzeige_name: str  # Was im UI angezeigt wird
    # Lambda: (spieler, kontext) -> str - Dynamische Modell-Auswahl
    modell_selector: Optional[Callable[["Spieler", "SpielKontext"], str]] = None
    beschreibung: str = ""


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
    erweiterung: Erweiterung = Erweiterung.BASISSPIEL  # TODO: MAKE REQUIRED

    # Phase ordering and dependencies
    requires_roles: List[str] = field(
        default_factory=list
    )  # Roles that must act before this one
    requires_phases: List[str] = field(
        default_factory=list
    )  # Generic phases that must happen first

    css_class: str = ""  # Frontend CSS class name override

    # NEW: Visual styling fields TODO: MAKE THE VISUAL STYLING FIELDS REQUIRED!
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
            Erweiterung.SONDEREDITION: "sonderedition",  # TODO: RENAME TO "COMMUNITY"
        }
        if self.erweiterung is None:
            raise ValueError(
                "RollenInfo.erweiterung darf nicht None sein"
            )  # TODO: LET IT ACTUALLY RAISE AN ERROR
        return pack_map.get(self.erweiterung, "unbekannt")

    # Auto-generate css_class from name if not set
    # TODO: this replace stuff really has to stop for good!
    @property
    def computed_css_class(self) -> str:
        if self.css_class:
            return self.css_class
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
    buttons: List[UIButton] = field(default_factory=list)
    requires_target: bool = True
    allow_multiple_targets: bool = False
    can_skip: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "title": self.title,
            "instructions": self.instructions,
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
            "can_skip": self.can_skip,
        }


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
        self, spieler: "Spieler", ziel: Optional["Spieler"], kontext: "SpielKontext"
    ) -> Optional[AktionsErgebnis]:
        """
        Wird aufgerufen, wenn der Spieler seine Nacht-Aktion ausführt.

        Args:
            spieler: Der handelnde Spieler
            ziel: Das gewählte Ziel (oder None)
            kontext: Der aktuelle Spielkontext

        Returns:
            AktionsErgebnis oder None (wenn Aktion ungültig)
        """
        logger.debug(
            f"Executing night action for {self.info.name} (Player: {spieler.name})"
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
        """
        # logger.debug(f"Trigger: Player died for {self.info.name}") # Too verbose
        return None

    def on_spiel_start(self, spieler: "Spieler", kontext: "SpielKontext"):
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
        return {
            "id": self.info.id,
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
