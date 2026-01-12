"""
Game Constants für Webwölfe-Spiel

Enthält:
- Team-Definitionen
- Spielregeln und -modi
- Rollen-Empfehlungen nach Spielerzahl
"""

# ============================================================================
# TEAMS
# ============================================================================

TEAMS = {
    "dorf": {
        "name": "Das Dorf",
        "beschreibung": "Eliminiert alle Werwölfe und andere Bedrohungen!",
        "farbe": "#3b82f6",
    },
    "werwolf": {
        "name": "Die Werwölfe",
        "beschreibung": "Bringt das Dorf in die Minderheit!",
        "farbe": "#dc2626",
    },
    "vampir": {
        "name": "Die Vampire",
        "beschreibung": "Verwandelt alle lebenden Spieler in Vampire!",
        "farbe": "#7c2d12",
    },
    "zombie": {
        "name": "Die Zombies",
        "beschreibung": "Infiziert alle Spieler und erreicht die Mehrheit!",
        "farbe": "#4ade80",
    },
    "solo": {
        "name": "Einzelspieler",
        "beschreibung": "Erreiche dein persönliches Ziel!",
        "farbe": "#6b7280",
    },
    "verliebte": {
        "name": "Die Verliebten",
        "beschreibung": "Überlebt gemeinsam bis zum Ende!",
        "farbe": "#ec4899",
    },
}


# ============================================================================
# SPIELREGELN / MODI
# ============================================================================

SPIEL_REGELN = {
    "standard": {
        "name": "Standard-Regeln",
        "beschreibung": "Die klassischen Werwolf-Regeln.",
        "einstellungen": {
            "nacht_zeit_sekunden": 60,
            "tag_diskussion_minuten": 5,
            "abstimmung_zeit_sekunden": 30,
            "tote_duerfen_reden": False,
            "rolle_bei_tod_zeigen": True,
        },
    },
    "schnell": {
        "name": "Schnellspiel",
        "beschreibung": "Kürzere Zeiten für schnelle Runden.",
        "einstellungen": {
            "nacht_zeit_sekunden": 30,
            "tag_diskussion_minuten": 2,
            "abstimmung_zeit_sekunden": 15,
            "tote_duerfen_reden": False,
            "rolle_bei_tod_zeigen": True,
        },
    },
    "chaos": {
        "name": "Chaos-Modus",
        "beschreibung": "Mehr Zufallselemente und Überraschungen.",
        "einstellungen": {
            "nacht_zeit_sekunden": 45,
            "tag_diskussion_minuten": 3,
            "abstimmung_zeit_sekunden": 20,
            "tote_duerfen_reden": True,  # Geister dürfen flüstern
            "rolle_bei_tod_zeigen": False,  # Rollen bleiben geheim
            "zufalls_ereignisse": True,
        },
    },
    "profi": {
        "name": "Profi-Modus",
        "beschreibung": "Für erfahrene Spieler. Weniger Hinweise, mehr Strategie.",
        "einstellungen": {
            "nacht_zeit_sekunden": 90,
            "tag_diskussion_minuten": 7,
            "abstimmung_zeit_sekunden": 45,
            "tote_duerfen_reden": False,
            "rolle_bei_tod_zeigen": False,
            "hinweise_aktiviert": False,  # Keine visuellen Hinweise
        },
    },
    "party": {
        "name": "Party-Modus",
        "beschreibung": "Lockere Regeln für Partys und große Gruppen.",
        "einstellungen": {
            "nacht_zeit_sekunden": 45,
            "tag_diskussion_minuten": 4,
            "abstimmung_zeit_sekunden": 20,
            "tote_duerfen_reden": True,
            "rolle_bei_tod_zeigen": True,
            "mehrfach_stimmen_erlaubt": True,
        },
    },
}


# ============================================================================
# ROLLEN-EMPFEHLUNGEN
# ============================================================================
# Role recommendations are now generated dynamically from DistributionConfig
# in each role's definition. Use get_recommended_roles() which delegates to
# game_logic.berechne_rollen() for dynamic distribution.
#
# Legacy static recommendations removed - all roles define their own
# distribution rules via DistributionConfig in roles/base.py


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def get_recommended_roles(player_count: int, include_narrator: bool = False) -> list:
    """
    Gibt empfohlene Rollen für eine bestimmte Spieleranzahl zurück.
    
    Uses dynamic role distribution from DistributionConfig instead of 
    hardcoded lists. Each role defines its own distribution rules.

    Args:
        player_count: Anzahl der Spieler
        include_narrator: Ob ein Erzähler dabei ist

    Returns:
        Liste der empfohlenen Rollen-Namen
    """
    # Import here to avoid circular imports
    from game_logic import berechne_rollen
    
    role_distribution = berechne_rollen(player_count, mit_erzaehler=include_narrator)
    
    # Convert dict {role: count} to list [role, role, ...]
    roles = []
    for role_name, count in role_distribution.items():
        roles.extend([role_name] * count)
    
    return roles


def get_team_color(team_name: str) -> str:
    """
    Gibt die Farbe eines Teams zurück.

    Args:
        team_name: Name des Teams

    Returns:
        Hex-Farbcode oder Grau als Fallback
    """
    return TEAMS.get(team_name, {}).get("farbe", "#6b7280")
