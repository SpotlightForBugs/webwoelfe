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
# ROLLEN-EMPFEHLUNGEN NACH SPIELERZAHL
# ============================================================================
# Für Spiele mit mehr Spielern als hier definiert, verwende berechne_rollen()
# aus game_logic.py

ROLLEN_EMPFEHLUNG = {
    5: ["Werwolf", "Werwolf", "Seherin", "Dorfbewohner", "Dorfbewohner"],
    6: ["Werwolf", "Werwolf", "Seherin", "Hexe", "Dorfbewohner", "Dorfbewohner"],
    7: [
        "Werwolf",
        "Werwolf",
        "Seherin",
        "Hexe",
        "Jaeger",
        "Dorfbewohner",
        "Dorfbewohner",
    ],
    8: [
        "Werwolf",
        "Werwolf",
        "Seherin",
        "Hexe",
        "Jaeger",
        "Amor",
        "Dorfbewohner",
        "Dorfbewohner",
    ],
    9: [
        "Werwolf",
        "Werwolf",
        "Seherin",
        "Hexe",
        "Jaeger",
        "Amor",
        "Heiler",
        "Dorfbewohner",
        "Dorfbewohner",
    ],
    10: [
        "Werwolf",
        "Werwolf",
        "Werwolf",
        "Seherin",
        "Hexe",
        "Jaeger",
        "Amor",
        "Heiler",
        "Dorfbewohner",
        "Dorfbewohner",
    ],
    11: [
        "Werwolf",
        "Werwolf",
        "Werwolf",
        "Seherin",
        "Hexe",
        "Jaeger",
        "Amor",
        "Heiler",
        "Alter Mann",
        "Dorfbewohner",
        "Dorfbewohner",
    ],
    12: [
        "Werwolf",
        "Werwolf",
        "Werwolf",
        "Seherin",
        "Hexe",
        "Jaeger",
        "Amor",
        "Heiler",
        "Alter Mann",
        "Zwei Schwestern",
        "Zwei Schwestern",
        "Dorfbewohner",
    ],
    14: [
        "Werwolf",
        "Werwolf",
        "Werwolf",
        "Werwolf",
        "Seherin",
        "Hexe",
        "Jaeger",
        "Amor",
        "Heiler",
        "Alter Mann",
        "Medium",
        "Rabe",
        "Dorfbewohner",
        "Dorfbewohner",
    ],
    16: [
        "Werwolf",
        "Werwolf",
        "Werwolf",
        "Werwolf",
        "Seherin",
        "Hexe",
        "Jaeger",
        "Amor",
        "Heiler",
        "Alter Mann",
        "Medium",
        "Rabe",
        "Dorfbewohner",
        "Dorfbewohner",
        "Dorfbewohner",
        "Dorfbewohner",
    ],
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def get_recommended_roles(player_count: int, include_narrator: bool = False) -> list:
    """
    Gibt empfohlene Rollen für eine bestimmte Spieleranzahl zurück.

    Args:
        player_count: Anzahl der Spieler
        include_narrator: Ob ein Erzähler dabei ist

    Returns:
        Liste der empfohlenen Rollen-Namen
    """
    effective_count = player_count - (1 if include_narrator else 0)

    # Suche nächste passende Konfiguration
    if effective_count in ROLLEN_EMPFEHLUNG:
        roles = ROLLEN_EMPFEHLUNG[effective_count].copy()
    else:
        # Nehme nächst kleinere Konfiguration oder use game_logic
        available = [k for k in ROLLEN_EMPFEHLUNG.keys() if k <= effective_count]
        if available:
            closest = max(available)
            roles = ROLLEN_EMPFEHLUNG[closest].copy()
        else:
            # Fallback für sehr kleine Spiele
            roles = ROLLEN_EMPFEHLUNG[5].copy()

    if include_narrator:
        roles.insert(0, "Erzaehler")

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
