"""
Zentrales Phasen-Management für das Werwolf-Spiel.

ARCHITEKTUR: Nur Kern-Phasen werden definiert.
Rollen-spezifische Aktionen passieren WÄHREND der Phasen,
nicht als eigene Phasen. Jede Rolle definiert selbst wann sie agiert.
"""

from enum import Enum
from typing import List, Optional, Dict, Any


class PhaseType(Enum):
    """Typ der Phase (für Logik-Gruppierung)"""

    SETUP = "setup"
    NACHT = "nacht"
    TAG = "tag"
    ENDE = "ende"


class Phase(Enum):
    """
    Kern-Spielphasen.

    KEINE rollen-spezifischen Phasen! Rollen agieren WÄHREND
    der entsprechenden Phase basierend auf ihrem TriggerType.
    """

    # Setup
    LOBBY = "lobby"
    ROLLEN_VERTEILT = "rollen_verteilt"

    # Nacht - Rollen agieren nach Priorität
    NACHT_START = "nacht_start"
    NACHT = "nacht"  # Dynamic role phases happen here
    NACHT_ENDE = "nacht_ende"

    # Tag
    TAG_START = "tag_start"
    TAG_ABSTIMMUNG = "tag_abstimmung"  # Combined discussion + voting
    HINRICHTUNG = "hinrichtung"
    TAG_ENDE = "tag_ende"

    # Ende
    SPIEL_ENDE = "spiel_ende"


# Phasen-Mapping: Phase -> Typ
PHASE_TYPES: Dict[Phase, PhaseType] = {
    Phase.LOBBY: PhaseType.SETUP,
    Phase.ROLLEN_VERTEILT: PhaseType.SETUP,
    Phase.NACHT_START: PhaseType.NACHT,
    Phase.NACHT: PhaseType.NACHT,
    Phase.NACHT_ENDE: PhaseType.NACHT,
    Phase.TAG_START: PhaseType.TAG,
    Phase.TAG_ABSTIMMUNG: PhaseType.TAG,
    Phase.HINRICHTUNG: PhaseType.TAG,
    Phase.TAG_ENDE: PhaseType.TAG,
    Phase.SPIEL_ENDE: PhaseType.ENDE,
}


# Standard day-night cycle order
PHASE_ORDER: List[Phase] = [
    Phase.LOBBY,
    Phase.ROLLEN_VERTEILT,
    Phase.NACHT_START,
    Phase.NACHT,
    Phase.NACHT_ENDE,
    Phase.TAG_START,
    Phase.TAG_ABSTIMMUNG,
    Phase.HINRICHTUNG,
    Phase.TAG_ENDE,
    # Then back to NACHT_START...
]


# Phase display configuration
PHASE_DISPLAY: Dict[str, Dict[str, Any]] = {
    "lobby": {
        "name": "Lobby",
        "icon": "fa-solid fa-door-open",
        "description": "Warte auf Spieler...",
    },
    "rollen_verteilt": {
        "name": "Rollen verteilt",
        "icon": "fa-solid fa-id-card",
        "description": "Die Rollen wurden verteilt.",
    },
    "nacht_start": {
        "name": "Nacht beginnt",
        "icon": "fa-solid fa-moon",
        "description": "Das Dorf schläft ein...",
    },
    "nacht": {
        "name": "Nacht",
        "icon": "fa-solid fa-moon",
        "description": "Die Nacht ist dunkel und voller Schrecken.",
    },
    "nacht_ende": {
        "name": "Nacht endet",
        "icon": "fa-solid fa-cloud-moon",
        "description": "Die Nacht geht zu Ende.",
    },
    "tag_start": {
        "name": "Tag bricht an",
        "icon": "fa-solid fa-sun",
        "description": "Das Dorf erwacht.",
    },
    "tag_abstimmung": {
        "name": "Diskussion & Abstimmung",
        "icon": "fa-solid fa-gavel",
        "description": "Diskutiert und stimmt ab!",
    },
    "hinrichtung": {
        "name": "Hinrichtung",
        "icon": "fa-solid fa-skull",
        "description": "Das Urteil wird vollstreckt.",
    },
    "tag_ende": {
        "name": "Tag endet",
        "icon": "fa-solid fa-sun",
        "description": "Der Tag neigt sich dem Ende.",
    },
    "spiel_ende": {
        "name": "Spiel beendet",
        "icon": "fa-solid fa-trophy",
        "description": "Das Spiel ist vorbei.",
    },
}


def get_phase_list() -> List[str]:
    """Gibt die Phasenliste in korrekter Reihenfolge zurück."""
    return [phase.value for phase in PHASE_ORDER]


def get_phase_type(phase: str) -> Optional[PhaseType]:
    """Gibt den Typ einer Phase zurück."""
    try:
        phase_enum = Phase(phase)
        return PHASE_TYPES.get(phase_enum)
    except ValueError:
        return None


def is_nacht_phase(phase: str) -> bool:
    """Prüft ob eine Phase eine Nachtphase ist."""
    phase_type = get_phase_type(phase)
    return phase_type == PhaseType.NACHT


def is_tag_phase(phase: str) -> bool:
    """Prüft ob eine Phase eine Tagphase ist."""
    phase_type = get_phase_type(phase)
    return phase_type == PhaseType.TAG


def get_next_phase(current_phase: str, runde: int = 1) -> str:
    """
    Gibt die nächste Phase zurück.

    Args:
        current_phase: Aktuelle Phase
        runde: Aktuelle Runde
    """
    try:
        phase_enum = Phase(current_phase)
        current_idx = PHASE_ORDER.index(phase_enum)

        # Nach TAG_ENDE -> zurück zu NACHT_START
        if phase_enum == Phase.TAG_ENDE:
            return Phase.NACHT_START.value

        # Sonst nächste Phase
        if current_idx + 1 < len(PHASE_ORDER):
            return PHASE_ORDER[current_idx + 1].value

        return Phase.NACHT_START.value

    except (ValueError, IndexError):
        return Phase.NACHT_START.value


def get_phase_display_name(phase: str) -> str:
    """Gibt einen benutzerfreundlichen Namen für die Phase zurück."""
    display = PHASE_DISPLAY.get(phase, {})
    return display.get("name", phase.replace("_", " ").title())


def get_phase_display_info(phase: str) -> Dict[str, Any]:
    """Gibt vollständige Display-Infos für eine Phase zurück."""
    return PHASE_DISPLAY.get(
        phase,
        {
            "name": phase.replace("_", " ").title(),
            "icon": "fa-solid fa-circle",
            "description": "",
        },
    )


# Export phase list for imports
PHASEN = get_phase_list()
