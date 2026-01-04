"""
Zentrales Phasen-Management für das Werwolf-Spiel.

Dieser Modul definiert alle Spielphasen als Enums und stellt
Hilfsfunktionen für die Phasenlogik bereit.
"""

from enum import Enum
from typing import List, Dict, Optional


class PhaseType(Enum):
    """Typ der Phase (für Logik-Gruppierung)"""
    SETUP = "setup"  # Lobby, Rollenzuweisung
    NACHT = "nacht"  # Nachtphasen
    TAG = "tag"  # Tagphasen
    ABSTIMMUNG = "abstimmung"  # Abstimmungsphasen
    INFO = "info"  # Informationsphasen
    SPECIAL = "special"  # Spezielle Phasen


class Phase(Enum):
    """Alle Spielphasen als Enum."""
    
    # Setup-Phasen
    LOBBY = "lobby"
    ROLLEN_VERTEILT = "rollen_verteilt"
    
    # Nacht-Start
    NACHT_START = "nacht_start"
    
    # Erste-Nacht-Phasen (nur Runde 1)
    DIEB_PHASE = "dieb_phase"
    DOPPELGAENGER_PHASE = "doppelgaenger_phase"
    AMOR_PHASE = "amor_phase"
    DUNKLER_PRIESTER_PHASE = "dunkler_priester_phase"
    WILDES_KIND_PHASE = "wildes_kind_phase"
    HUND_PHASE = "hund_phase"
    ZWEI_SCHWESTERN_PHASE = "zwei_schwestern_phase"
    DREI_BRUEDER_PHASE = "drei_brueder_phase"
    FREIMAURER_PHASE = "freimaurer_phase"
    FLUECHTLINGE_PHASE = "fluechtlinge_phase"
    VERLIEBTE_INFO = "verliebte_info"
    
    # Reguläre Nacht-Phasen
    SANDMANN_PHASE = "sandmann_phase"
    SEHERIN_PHASE = "seherin_phase"
    SEHERLEHRLING_PHASE = "seherlehrling_phase"
    AURENSEHERIN_PHASE = "aurenseherin_phase"
    MEDIUM_PHASE = "medium_phase"
    TRATSCHWEIB_PHASE = "tratschweib_phase"
    PARANORMAL_BILLIG_PHASE = "paranormal_billig_phase"
    WERWOLFSEHERIN_PHASE = "werwolfseherin_phase"
    HEILER_PHASE = "heiler_phase"
    LEIBWAECHTER_PHASE = "leibwaechter_phase"
    HURE_PHASE = "hure_phase"
    PROSTITUIERTE_PHASE = "prostituierte_phase"
    NUTTE_PHASE = "nutte_phase"
    WERWOLF_PHASE = "werwolf_phase"
    EINSAMER_WOLF_PHASE = "einsamer_wolf_phase"
    URWOLF_PHASE = "urwolf_phase"
    WEISSER_WOLF_PHASE = "weisser_wolf_phase"
    MORDLUSTIGER_PHASE = "mordlustiger_phase"
    HEXE_PHASE = "hexe_phase"
    HEXENMEISTER_PHASE = "hexenmeister_phase"
    GIFTMISCHERIN_PHASE = "giftmischerin_phase"
    KRAEUTERWEIB_PHASE = "kraeuterweib_phase"
    ZAUBERER_PHASE = "zauberer_phase"
    HAHN_PHASE = "hahn_phase"
    JAEGER_PHASE = "jaeger_phase"
    KAMIKAZE_PHASE = "kamikaze_phase"
    PYROMANE_PHASE = "pyromane_phase"
    FLAMMENMANN_PHASE = "flammenmann_phase"
    KOENIG_PHASE = "koenig_phase"
    PRINZ_PHASE = "prinz_phase"
    INQUISITOR_PHASE = "inquisitor_phase"
    DRACHENBAENDIGER_PHASE = "drachenbaendiger_phase"
    GAUKLER_PHASE = "gaukler_phase"
    BUDDLER_PHASE = "buddler_phase"
    TANKLASTWAGENFAHRER_PHASE = "tanklastwagenfahrer_phase"
    BAERENBAENDIGER_PHASE = "baerenbaendiger_phase"
    DEMOSKOPIN_PHASE = "demoskopin_phase"
    HENKER_PHASE = "henker_phase"
    OMA_PHASE = "oma_phase"
    ERGEBENE_MAGD_PHASE = "ergebene_magd_phase"
    
    # Sonstige/Spezial Nacht-Phasen
    FLOETENSPIELER_PHASE = "floetenspieler_phase"
    VAMPIR_PHASE = "vampir_phase"
    ZOMBIE_PHASE = "zombie_phase"
    KLEINES_MAEDCHEN_PHASE = "kleines_maedchen_phase"
    GERBER_PHASE = "gerber_phase"
    PUTZFRAU_PHASE = "putzfrau_phase"
    BUERGERMEISTER_PHASE = "buergermeister_phase"
    DIEB_PHASE_NACHT = "dieb_phase_nacht"
    ENGEL_PHASE = "engel_phase"
    SUENDENBOCK_PHASE = "suendenbock_phase"
    CHEMIELABORANT_PHASE = "chemielaborant_phase"
    PSYCHIATER_PHASE = "psychiater_phase"
    ADVOKAT_PHASE = "advokat_phase"
    HYPNOTISEUR_PHASE = "hypnotiseur_phase"
    BOTIN_PHASE = "botin_phase"
    
    # Nacht-Ende
    NACHT_ENDE = "nacht_ende"
    
    # Tag-Phasen
    TAG_START = "tag_start"
    DISKUSSION = "diskussion"
    DISKUSSION_ABSTIMMUNG = "diskussion_abstimmung"
    ABSTIMMUNG = "abstimmung"
    LETZTES_WORT = "letztes_wort"
    AUFDECKUNG = "aufdeckung"
    HINRICHTUNG = "hinrichtung"
    TAG_ENDE = "tag_ende"
    
    # Spiel-Ende
    SPIEL_ENDE = "spiel_ende"


# Phasen-Mapping: Phase -> Typ
PHASE_TYPES: Dict[Phase, PhaseType] = {
    # Setup
    Phase.LOBBY: PhaseType.SETUP,
    Phase.ROLLEN_VERTEILT: PhaseType.SETUP,
    
    # Nacht-Phasen
    Phase.NACHT_START: PhaseType.NACHT,
    **{phase: PhaseType.NACHT for phase in Phase if "_phase" in phase.value},
    
    # Info-Phasen
    Phase.VERLIEBTE_INFO: PhaseType.INFO,
    Phase.NACHT_ENDE: PhaseType.INFO,
    Phase.TAG_START: PhaseType.INFO,
    
    # Tag-Phasen
    Phase.DISKUSSION: PhaseType.TAG,
    Phase.LETZTES_WORT: PhaseType.TAG,
    Phase.AUFDECKUNG: PhaseType.TAG,
    Phase.TAG_ENDE: PhaseType.TAG,
    
    # Abstimmungs-Phasen
    Phase.DISKUSSION_ABSTIMMUNG: PhaseType.ABSTIMMUNG,
    Phase.ABSTIMMUNG: PhaseType.ABSTIMMUNG,
    Phase.HINRICHTUNG: PhaseType.ABSTIMMUNG,
    
    # Ende
    Phase.SPIEL_ENDE: PhaseType.SPECIAL,
}


# Erste-Nacht-Phasen (nur in Runde 1)
ERSTE_NACHT_PHASEN = [
    Phase.DIEB_PHASE,
    Phase.DOPPELGAENGER_PHASE,
    Phase.AMOR_PHASE,
    Phase.DUNKLER_PRIESTER_PHASE,
    Phase.WILDES_KIND_PHASE,
    Phase.HUND_PHASE,
    Phase.ZWEI_SCHWESTERN_PHASE,
    Phase.DREI_BRUEDER_PHASE,
    Phase.FREIMAURER_PHASE,
    Phase.FLUECHTLINGE_PHASE,
    Phase.VERLIEBTE_INFO,
]


def get_phase_list() -> List[str]:
    """
    Gibt die komplette Phasenliste in korrekter Reihenfolge zurück.
    
    Returns:
        Liste aller Phasen-Werte (strings)
    """
    return [phase.value for phase in Phase]


def get_phase_type(phase: str) -> Optional[PhaseType]:
    """
    Gibt den Typ einer Phase zurück.
    
    Args:
        phase: Phase-String (z.B. "werwolf_phase")
        
    Returns:
        PhaseType oder None falls unbekannt
    """
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
    return phase_type in (PhaseType.TAG, PhaseType.ABSTIMMUNG)


def is_erste_nacht_phase(phase: str) -> bool:
    """Prüft ob eine Phase nur in der ersten Nacht vorkommt."""
    try:
        phase_enum = Phase(phase)
        return phase_enum in ERSTE_NACHT_PHASEN
    except ValueError:
        return False


def normalize_phase_name(phase_name: str) -> str:
    """
    Normalisiert Phasennamen (Umlaute -> ASCII).
    
    Args:
        phase_name: Original-Phasenname
        
    Returns:
        Normalisierter Phasenname
    """
    replacements = {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "ß": "ss",
    }
    normalized = phase_name.lower()
    for old, new in replacements.items():
        normalized = normalized.replace(old, new)
    return normalized


def get_next_phase(current_phase: str, runde: int, active_roles: List[str]) -> Optional[str]:
    """
    Berechnet die nächste Phase basierend auf aktiven Rollen.
    
    Args:
        current_phase: Aktuelle Phase
        runde: Aktuelle Runde
        active_roles: Liste der aktiven Rollen-Namen
        
    Returns:
        Nächste Phase oder None wenn nicht gefunden
    """
    phase_list = get_phase_list()
    
    try:
        current_index = phase_list.index(current_phase)
    except ValueError:
        return None
    
    # Durchlaufe alle folgenden Phasen
    for phase in phase_list[current_index + 1:]:
        # Erste-Nacht-Phasen überspringen wenn nicht Runde 1
        if runde > 1 and is_erste_nacht_phase(phase):
            continue
        
        # Prüfe ob Phase aktiv ist (Rolle vorhanden)
        if "_phase" in phase:
            # Extrahiere Rollen-Name aus Phase
            role_name = phase.replace("_phase", "").replace("_", " ").title()
            
            # Wenn keine aktiven Rollen definiert, zeige alle Phasen
            if not active_roles:
                return phase
            
            # Prüfe ob Rolle aktiv
            # (vereinfachte Logik - sollte mit RoleRegistry erweitert werden)
            if any(role_name.lower() in r.lower() for r in active_roles):
                return phase
        else:
            # Nicht-Rollen-Phasen immer zurückgeben
            return phase
    
    return None


def get_phase_display_name(phase: str) -> str:
    """
    Gibt einen formatierten Anzeige-Namen für eine Phase zurück.
    
    Args:
        phase: Phase-String
        
    Returns:
        Formatierter Anzeige-Name
    """
    # Entferne "_phase" suffix
    display = phase.replace("_phase", "")
    
    # Ersetze Unterstriche mit Leerzeichen
    display = display.replace("_", " ")
    
    # Titel-Case
    display = display.title()
    
    # Spezielle Anpassungen
    display_map = {
        "Nacht Start": "Nacht beginnt",
        "Nacht Ende": "Nacht endet",
        "Tag Start": "Tag beginnt",
        "Tag Ende": "Tag endet",
        "Diskussion Abstimmung": "Diskussion & Abstimmung",
        "Verliebte Info": "Die Verliebten erwachen",
        "Rollen Verteilt": "Rollen wurden verteilt",
        "Spiel Ende": "Spiel beendet",
    }
    
    return display_map.get(display, display)
