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
    SONDEREDITION = "sonderedition" # THIS MEANS COMMUNITY EDITION

    def __str__(self) -> str:
        return self.value


class Phase(Enum):
    """Spielphasen."""

    LOBBY = "lobby"
    NACHT_START = "nacht_start"
    AMOR_PHASE = "amor_phase"
    VERLIEBTE_PHASE = "verliebte_phase"
    WERWOLF_PHASE = "werwolf_phase"
    SEHERIN_PHASE = "seherin_phase"
    HEXE_PHASE = "hexe_phase"
    HEILER_PHASE = "heiler_phase"
    WEISSER_WOLF_PHASE = "weisser_wolf_phase"
    TAG_START = "tag_start"
    DISKUSSION = "diskussion"
    ABSTIMMUNG = "abstimmung"
    HINRICHTUNG = "hinrichtung"
    JAEGER_PHASE = "jaeger_phase"
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
