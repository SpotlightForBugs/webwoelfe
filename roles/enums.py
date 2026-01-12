"""
Enums für das Rollensystem.
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional


@dataclass
class TeamConfig:
    """Configuration for a team's win condition behavior."""
    is_evil: bool = False  # True if this team opposes the village
    priority: int = 100  # Lower = higher priority for win checks (WERWOLF=1, VAMPIR=2, etc.)
    win_message: str = ""  # Custom win message
    sides_with_village: bool = False  # True if counted with village for majority


# Team configuration - defines how each team behaves in win conditions
TEAM_CONFIG: dict[str, "TeamConfig"] = {}


class Team(Enum):
    """Teams im Spiel."""

    DORF = "dorf"
    WERWOLF = "werwolf"
    SOLO = "solo"
    VERLIEBTE = "verliebte"
    VAMPIR = "vampir"
    ZOMBIE = "zombie"
    NEUTRAL = "neutral"

    def __str__(self) -> str:
        return self.value

    @property
    def config(self) -> TeamConfig:
        """Get the configuration for this team."""
        return TEAM_CONFIG.get(self.value, TeamConfig())
    
    @property
    def is_evil(self) -> bool:
        """Returns True if this team opposes the village."""
        return self.config.is_evil
    
    @property
    def priority(self) -> int:
        """Win check priority (lower = checked first)."""
        return self.config.priority
    
    @property
    def win_message(self) -> str:
        """Get the win message for this team."""
        return self.config.win_message or f"Team {self.value} hat gewonnen!"
    
    @property
    def sides_with_village(self) -> bool:
        """Returns True if this team is counted with village for majority calculations."""
        return self.config.sides_with_village


# Initialize team configurations
TEAM_CONFIG.update({
    Team.DORF.value: TeamConfig(
        is_evil=False,
        priority=100,
        win_message="Alle Bedrohungen wurden vernichtet. Das Dorf hat gewonnen!",
        sides_with_village=True,
    ),
    Team.WERWOLF.value: TeamConfig(
        is_evil=True,
        priority=1,  # Highest evil priority
        win_message="Die Werwölfe haben die Überhand gewonnen!",
    ),
    Team.VAMPIR.value: TeamConfig(
        is_evil=True,
        priority=2,
        win_message="Die Vampire haben das Dorf übernommen!",
    ),
    Team.ZOMBIE.value: TeamConfig(
        is_evil=True,
        priority=3,
        win_message="Die Zombies haben alle infiziert!",
    ),
    Team.SOLO.value: TeamConfig(
        is_evil=False,  # Solo roles have their own win conditions
        priority=50,
        win_message="",
    ),
    Team.VERLIEBTE.value: TeamConfig(
        is_evil=False,
        priority=0,  # Lovers checked very early
        win_message="Die Verliebten haben als einzige überlebt und gewinnen gemeinsam!",
    ),
    Team.NEUTRAL.value: TeamConfig(
        is_evil=False,
        priority=100,
        win_message="",
        sides_with_village=True,
    ),
})


class Kategorie(Enum):
    """Kategorien fuer UI-Gruppierung."""

    GRUNDROLLEN = "grundrollen"
    DORFBEWOHNER = "dorfbewohner"
    WERWOLF = "werwolf"
    SEHER = "seher"
    HEXE = "hexe"
    JAEGER = "jaeger"
    HEILER = "heiler"
    SPEZIAL = "spezial"
    BOESE = "boese"
    SOLO = "solo"
    SONSTIGE = "sonstige"

    def __str__(self) -> str:
        return self.value


class Erweiterung(Enum):
    """Erweiterungspakete fuer Rollen."""

    BASISSPIEL = "basisspiel"
    NEUMOND = "neumond"
    GEMEINDE = "gemeinde"
    CHARAKTERE = "charaktere"
    COMMUNITY = "community"  # Community-created roles

    def __str__(self) -> str:
        return self.value


class Phase(Enum):
    """
    Spielphasen.

    Note: Role-specific phases (like amor_phase, seherin_phase) are
    dynamically generated from role names, not listed here.
    """

    # Setup
    LOBBY = "lobby"
    ROLLEN_VERTEILT = "rollen_verteilt"

    # Night
    NACHT_START = "nacht_start"
    NACHT = "nacht"
    NACHT_ENDE = "nacht_ende"

    # Day
    TAG_START = "tag_start"
    TAG_ABSTIMMUNG = "tag_abstimmung"
    HINRICHTUNG = "hinrichtung"
    TAG_ENDE = "tag_ende"

    # Special (triggered by role effects)
    JAEGER_PHASE = "jaeger_phase"

    # End
    SPIEL_ENDE = "spiel_ende"

    def __str__(self) -> str:
        return self.value


class TriggerTyp(Enum):
    """Typen von Events die Rollen-Aktionen ausloesen."""

    # Spielstart
    SPIEL_START = auto()

    # Nacht-Phasen
    NACHT_START = auto()
    NACHT_AKTION = auto()
    NACHT_ENDE = auto()

    # Tag-Phasen
    TAG_START = auto()
    DISKUSSION_START = auto()
    ABSTIMMUNG_START = auto()
    ABSTIMMUNG_ENDE = auto()

    # Spieler-Events
    SPIELER_STIRBT = auto()
    SPIELER_GEHEILT = auto()
    SPIELER_GESCHUETZT = auto()
    SPIELER_GEWAEHLT = auto()
    SPIELER_ANGEGRIFFEN = auto()

    # Spezielle Trigger
    VORBILD_STIRBT = auto()
    VERLIEBTER_STIRBT = auto()
    LETZTE_WORTE = auto()
    AUFERSTEHUNG = auto()

    # Spiel-Ende
    SPIEL_ENDE = auto()
    GEWINNER_ERMITTELT = auto()


class AktionsTyp(Enum):
    """Typen von Aktionen die Spieler ausführen können."""

    SEHEN = "sehen"
    TOETEN = "toeten"
    HEILEN = "heilen"
    SCHUETZEN = "schuetzen"
    VERGIFTEN = "vergiften"
    VERLIEBEN = "verlieben"
    WAEHLEN = "waehlen"
    MARKIEREN = "markieren"
    INFIZIEREN = "infizieren"
    VERZAUBERN = "verzaubern"
    VERWANDELN = "verwandeln"
    AUFWECKEN = "aufwecken"
    STUMM_MACHEN = "stumm_machen"
    SCHIESSEN = "schiessen"
    OPFERN = "opfern"
    HINWEIS_SENDEN = "hinweis_senden"
    MANIPULIEREN = "manipulieren"
    BLOCKIEREN = "blockieren"
    BESUCHEN = "besuchen"
    PASSIV = "passiv"
    KEINE = "keine"


class SichtTyp(Enum):
    """Was die Seherin sieht."""

    WERWOLF = "werwolf"
    DORF = "dorf"
    NEUTRAL = "neutral"
    NICHTS = "nichts"  # Bei blockierten Rollen


class SeherFaehigkeit(Enum):
    """
    Capability types for seer-like roles.
    
    Used for capability-based visibility instead of hardcoded role name strings.
    Roles override get_visibility_for(capability) to define what seers see.
    """
    
    TEAM_AURA = "team_aura"       # Sees true good/evil aura (Aurenseherin)
    ACTUAL_ROLE = "actual_role"   # Sees exact role name (Rollenseherin)
    TEAM_BASIC = "team_basic"     # Sees team alignment, can be fooled (Seherin)
    PROTECTED = "protected"       # Cannot see anything (blocked roles)

class SichtbarkeitFuerWoelfe(Enum):
    """
    Visibility levels for werewolves (replaces hardcoded strings).
    Defines who can see whom during night phase.
    """
    
    ALLE = "alle"                 # Visible to all werewolves
    EIGENTEAM = "eigenteam"       # Only visible to own team
    NIEMAND = "niemand"           # Not visible to anyone
    RUDEL = "rudel"              # Visible only to werewolf pack


class EventName(Enum):
    """
    Standard event names (replaces hardcoded string literals).
    Used for database queries and phase transitions.
    """
    
    # Seer events
    SEHERIN_ERGEBNIS = "seherin_ergebnis"
    AURENSEHERIN_ERGEBNIS = "aurenseherin_ergebnis"
    
    # Win condition events
    WERWOLF_GEWONNEN = "werwolf_gewonnen"
    DORF_GEWONNEN = "dorf_gewonnen"
    VERLIEBTE_GEWONNEN = "verliebte_gewonnen"
    SOLO_GEWONNEN = "solo_gewonnen"
    VAMPIR_GEWONNEN = "vampir_gewonnen"
    
    # Phase events
    HEILER_PHASE = "heiler_phase"
    HEXE_PHASE = "hexe_phase"
    WERWOLF_PHASE = "werwolf_phase"
    JAEGER_PHASE = "jaeger_phase"
    
    # Death/damage events
    WERWOLF_OPFER = "werwolf_opfer"
    VERGIFTUNG = "vergiftung"
    HEILUNG = "heilung"
    
    def __str__(self) -> str:
        return self.value