"""
Zentrales Phasen-Management für das Werwolf-Spiel.

ARCHITEKTUR: Nur Kern-Phasen werden definiert.
Rollen-spezifische Aktionen passieren WÄHREND der Phasen,
nicht als eigene Phasen. Jede Rolle definiert selbst wann sie agiert.
"""

from enum import Enum
from typing import List, Optional


class PhaseType(Enum):
    """Typ der Phase (für Logik-Gruppierung)"""
    SETUP = "setup"       # Lobby, Rollenzuweisung
    NACHT = "nacht"       # Nacht - Rollen agieren nach Priorität
    TAG = "tag"           # Tag-Phasen
    ABSTIMMUNG = "abstimmung"  # Abstimmungsphasen
    ENDE = "ende"         # Spielende


class Phase(Enum):
    """
    Kern-Spielphasen.
    
    KEINE rollen-spezifischen Phasen! Rollen agieren WÄHREND
    der entsprechenden Phase basierend auf ihrem TriggerType.
    """
    
    # Setup
    LOBBY = "lobby"
    ROLLEN_VERTEILT = "rollen_verteilt"
    
    # Nacht - EINE Phase, Rollen agieren nach Priorität
    NACHT = "nacht"
    
    # Tag
    TAG_START = "tag_start"
    DISKUSSION = "diskussion"
    ABSTIMMUNG = "abstimmung"
    HINRICHTUNG = "hinrichtung"
    TAG_ENDE = "tag_ende"
    
    # Ende
    SPIEL_ENDE = "spiel_ende"


# Phasen-Mapping: Phase -> Typ
PHASE_TYPES = {
    Phase.LOBBY: PhaseType.SETUP,
    Phase.ROLLEN_VERTEILT: PhaseType.SETUP,
    Phase.NACHT: PhaseType.NACHT,
    Phase.TAG_START: PhaseType.TAG,
    Phase.DISKUSSION: PhaseType.TAG,
    Phase.ABSTIMMUNG: PhaseType.ABSTIMMUNG,
    Phase.HINRICHTUNG: PhaseType.ABSTIMMUNG,
    Phase.TAG_ENDE: PhaseType.TAG,
    Phase.SPIEL_ENDE: PhaseType.ENDE,
}


# Phasen-Reihenfolge für einen Tag-Nacht-Zyklus
PHASE_ORDER = [
    Phase.LOBBY,
    Phase.ROLLEN_VERTEILT,
    Phase.NACHT,
    Phase.TAG_START,
    Phase.DISKUSSION,
    Phase.ABSTIMMUNG,
    Phase.HINRICHTUNG,
    Phase.TAG_ENDE,
    # Dann wieder NACHT...
]


def get_phase_list() -> List[str]:
    """
    Gibt die Phasenliste in korrekter Reihenfolge zurück.
    """
    return [phase.value for phase in PHASE_ORDER]


def get_phase_type(phase: str) -> Optional[PhaseType]:
    """
    Gibt den Typ einer Phase zurück.
    """
    try:
        phase_enum = Phase(phase)
        return PHASE_TYPES.get(phase_enum)
    except ValueError:
        return None


def is_nacht_phase(phase: str) -> bool:
    """Prüft ob eine Phase die Nachtphase ist."""
    return phase == Phase.NACHT.value


def is_tag_phase(phase: str) -> bool:
    """Prüft ob eine Phase eine Tagphase ist."""
    return str(get_phase_type(phase)) in [str(PhaseType.TAG), str(PhaseType.ABSTIMMUNG)]


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
        
        # Nach TAG_ENDE -> zurück zu NACHT
        if phase_enum == Phase.TAG_ENDE:
            return Phase.NACHT.value
        
        # Sonst nächste Phase
        if current_idx + 1 < len(PHASE_ORDER):
            return PHASE_ORDER[current_idx + 1].value
        
        return Phase.NACHT.value
        
    except (ValueError, IndexError):
        return Phase.NACHT.value


def get_phase_display_name(phase: str) -> str:
    """
    Gibt einen benutzerfreundlichen Namen für die Phase zurück.
    """
    display_names = {
        "lobby": "Lobby",
        "rollen_verteilt": "Rollen wurden verteilt",
        "nacht": "Nacht",
        "tag_start": "Der Tag bricht an",
        "diskussion": "Diskussion",
        "abstimmung": "Abstimmung",
        "hinrichtung": "Hinrichtung",
        "tag_ende": "Der Tag endet",
        "spiel_ende": "Spiel beendet",
    }
    return display_names.get(phase, phase)


# Legacy-Kompatibilität: PHASEN als Liste von Strings
PHASEN = get_phase_list()
