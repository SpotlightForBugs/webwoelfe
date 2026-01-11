"""
Narrator Event System - Dynamic narrator text management.

Core phase events are defined here. Role-specific events come from
each Role's get_erzaehler_events() method via the RoleRegistry.

This replaces the deprecated ERZAEHLER_EVENTS dict in models.py.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from logger import logger


@dataclass
class NarratorEvent:
    """A narrator event that can be triggered."""

    event_id: str
    text: str
    anweisung: str = ""
    bedingung: Dict[str, Any] = field(default_factory=dict)
    einmalig: bool = True
    rolle: Optional[str] = None  # If role-specific


# ============================================================================
# CORE PHASE EVENTS - Not role-specific
# ============================================================================

CORE_PHASE_EVENTS: Dict[str, NarratorEvent] = {
    # Setup
    "rollen_verteilt": NarratorEvent(
        event_id="rollen_verteilt",
        text="Die Rollen wurden verteilt. Schaut euch eure Rolle an.",
        anweisung="Die Spieler schauen sich ihre Rollen an.",
        bedingung={"phase": "rollen_verteilt"},
        einmalig=True,
    ),
    # Night transitions
    "nacht_start": NarratorEvent(
        event_id="nacht_start",
        text="Die Nacht bricht herein. Alle Spieler schließen die Augen.",
        anweisung="Alle Spieler schließen die Augen.",
        bedingung={"phase": "nacht_start"},
        einmalig=False,
    ),
    "nacht_ende": NarratorEvent(
        event_id="nacht_ende",
        text="Die Nacht ist vorbei. Der Morgen graut.",
        anweisung="Die Nacht endet.",
        bedingung={"phase": "nacht_ende"},
        einmalig=False,
    ),
    "erste_nacht_intro": NarratorEvent(
        event_id="erste_nacht_intro",
        text="Willkommen in Düsterwald! Die erste Nacht bricht herein. In diesem Dorf verbergen sich Werwölfe unter den friedlichen Bewohnern.",
        anweisung="Lies diesen Text atmosphärisch vor. Dann beginne mit den Rollen.",
        bedingung={"runde": 1, "phase": "nacht_start"},
        einmalig=True,
    ),
    # Day transitions
    "tag_start": NarratorEvent(
        event_id="tag_start",
        text="Das Dorf erwacht. Die Sonne geht auf und alle öffnen die Augen.",
        anweisung="Alle Spieler öffnen die Augen.",
        bedingung={"phase": "tag_start"},
        einmalig=False,
    ),
    "tag_abstimmung": NarratorEvent(
        event_id="tag_abstimmung",
        text="Die Dorfbewohner versammeln sich zum Rat. Diskutiert und stimmt ab, wen ihr verdächtigt!",
        anweisung="Die Spieler diskutieren und stimmen ab.",
        bedingung={"phase": "tag_abstimmung"},
        einmalig=False,
    ),
    "tag_ende": NarratorEvent(
        event_id="tag_ende",
        text="Der Tag neigt sich dem Ende. Die Sonne geht unter.",
        anweisung="Der Tag endet.",
        bedingung={"phase": "tag_ende"},
        einmalig=False,
    ),
    # Game end
    "dorf_gewonnen": NarratorEvent(
        event_id="dorf_gewonnen",
        text="Das Dorf hat gewonnen! Alle Werwölfe wurden eliminiert. Die Dorfbewohner können wieder in Frieden leben.",
        anweisung="Gratuliere dem Dorf! Decke alle Rollen auf.",
        bedingung={"trigger": "spielende", "gewinner": "dorf"},
        einmalig=True,
    ),
    "werwolf_gewonnen": NarratorEvent(
        event_id="werwolf_gewonnen",
        text="Die Werwölfe haben gewonnen! Sie sind nun in der Überzahl und übernehmen das Dorf.",
        anweisung="Die Werwölfe haben gewonnen. Decke alle Rollen auf.",
        bedingung={"trigger": "spielende", "gewinner": "werwolf"},
        einmalig=True,
    ),
    "verliebte_gewonnen": NarratorEvent(
        event_id="verliebte_gewonnen",
        text="Die Verliebten haben gewonnen! Ihre Liebe hat alle Hindernisse überwunden. Sie sind die letzten Überlebenden.",
        anweisung="Die Verliebten sind die letzten Überlebenden. Romantisches Ende!",
        bedingung={"trigger": "spielende", "gewinner": "verliebte"},
        einmalig=True,
    ),
    "niemand_gewonnen": NarratorEvent(
        event_id="niemand_gewonnen",
        text="Niemand hat gewonnen. Das Dorf ist ausgelöscht.",
        anweisung="Alle sind tot. Trauriges Ende.",
        bedingung={"trigger": "spielende", "gewinner": "niemand"},
        einmalig=True,
    ),
}


def get_all_narrator_events() -> Dict[str, Dict[str, Any]]:
    """
    Get all narrator events from both core phases and roles.

    Returns:
        Dict of event_id -> event data
    """
    all_events = {}

    # Add core phase events
    for event_id, event in CORE_PHASE_EVENTS.items():
        all_events[event_id] = {
            "text": event.text,
            "anweisung": event.anweisung,
            "bedingung": event.bedingung,
            "einmalig": event.einmalig,
            "rolle": event.rolle,
        }

    # Add role-specific events from registry
    try:
        from roles import RoleRegistry

        role_events = RoleRegistry.get_all_erzaehler_events()
        all_events.update(role_events)
    except Exception as e:
        logger.warning(f"Could not load role narrator events: {e}")

    return all_events


def get_narrator_event(event_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific narrator event by ID."""
    all_events = get_all_narrator_events()
    return all_events.get(event_id)


def get_narrator_text_for_phase(phase: str) -> Optional[Dict[str, Any]]:
    """Get the narrator text for a specific phase."""
    all_events = get_all_narrator_events()
    return all_events.get(phase)


def hole_erzaehler_text(
    raum_id: int, event_typ: str, kontext: Optional[Dict] = None
) -> Optional[Dict[str, Any]]:
    """
    Get narrator text for an event, checking if it was already played.

    Args:
        raum_id: Room ID
        event_typ: Event type/ID
        kontext: Optional context dict for placeholder replacement

    Returns:
        Dict with text, anweisung, einmalig or None if already played
    """
    from models import ErzaehlerEvent

    event = get_narrator_event(event_typ)
    if not event:
        logger.warning(f"Narrator event not found: {event_typ}")
        return None

    # Check if one-time event was already played
    if event.get("einmalig", True):
        if ErzaehlerEvent.event_bereits_gespielt(raum_id, event_typ):
            return None

    text = event["text"]
    anweisung = event.get("anweisung", "")

    # Replace placeholders if context provided
    if kontext:
        for key, value in kontext.items():
            text = text.replace("{" + key + "}", str(value))
            anweisung = anweisung.replace("{" + key + "}", str(value))

    return {
        "text": text,
        "anweisung": anweisung,
        "einmalig": event.get("einmalig", False),
    }


# Backwards compatibility alias
ERZAEHLER_EVENTS = None  # Will be populated on first access


class _DynamicErzaehlerEvents(dict):
    """Dynamic dict that loads narrator events on access."""

    _loaded = False

    def _ensure_loaded(self):
        if not self._loaded:
            self.clear()
            self.update(get_all_narrator_events())
            self._loaded = True

    def __getitem__(self, key):
        self._ensure_loaded()
        return super().__getitem__(key)

    def __contains__(self, key):
        self._ensure_loaded()
        return super().__contains__(key)

    def get(self, key, default=None):
        self._ensure_loaded()
        return super().get(key, default)

    def items(self):
        self._ensure_loaded()
        return super().items()

    def keys(self):
        self._ensure_loaded()
        return super().keys()

    def values(self):
        self._ensure_loaded()
        return super().values()


# Dynamic events dict for backwards compatibility
ERZAEHLER_EVENTS = _DynamicErzaehlerEvents()
