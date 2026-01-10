"""
Enums für das Rollensystem.
"""

from enum import Enum, auto


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
