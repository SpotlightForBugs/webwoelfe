"""
Stateless Phase Scheduler.

Bestimmt die nächste Spielphase basierend auf dem aktuellen Zustand.
Ersetzt die alte phasenbasierte Logik durch eine dynamische Rollen-Abfolge.
"""

from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from models import Raum, SpielAktion, Spieler
from roles import RoleRegistry
from roles.enums import Phase
import logging

logger = logging.getLogger(__name__)


@dataclass
class PhaseState:
    phase: str
    active_role: Optional[str] = None
    display_info: Optional[Dict[str, Any]] = None


def get_next_phase_state(raum: "Raum") -> PhaseState:
    """
    Ermittelt den nächsten Spielzustand (Phase + Aktive Rolle).
    """
    current_phase = raum.aktuelle_phase

    # 1. Start -> Rollen Verteilung
    if current_phase == "lobby":
        return PhaseState("rollen_verteilt")

    # 2. Rollen Verteilung -> Nacht Start
    if current_phase == "rollen_verteilt":
        return get_next_night_step(raum)

    # 3. Nacht-Zyklus
    if current_phase == "nacht" or current_phase == "nacht_start":
        return get_next_night_step(raum)

    # 4. Tag-Zyklus
    # (Hier könnte man auch eine Tag-Queue implementieren,
    # aber Tag-Phasen sind meist statisch: Diskussion -> Abstimmung -> Hinrichtung)
    if current_phase == "tag_start":
        return PhaseState("diskussion")
    if current_phase == "diskussion":
        return PhaseState("abstimmung")
    if current_phase == "abstimmung":
        return PhaseState("hinrichtung")
    if current_phase == "hinrichtung":
        return PhaseState("tag_ende")
    if current_phase == "tag_ende":
        return get_next_night_step(raum)

    # Fallback
    return PhaseState("nacht")


def get_next_night_step(raum: "Raum") -> PhaseState:
    """
    Iteriert durch alle Rollen und prüft, wer noch agieren muss.
    """
    # 1. Hole alle aktiven Rollen für diese Nacht (sortiert)
    active_roles = get_active_roles_ordered(raum)

    # 2. Prüfe wer schon fertig ist
    for role_obj, spieler_liste in active_roles:
        if not is_role_done(raum, role_obj, spieler_liste):
            # Diese Rolle ist dran!
            return PhaseState(
                phase="nacht",
                active_role=role_obj.info.name,
                display_info=(
                    role_obj.get_phase_display_info()
                    if hasattr(role_obj, "get_phase_display_info")
                    else None
                ),
            )

    # Alle fertig -> Tag
    return PhaseState("tag_start")


def get_active_roles_ordered(raum: "Raum") -> List[Any]:
    """
    Gibt Liste von (Role, [Spieler]) zurück, sortiert nach Priorität.
    """
    # Hole lebende Spieler
    # (Optimierung: Könnte man cachen oder via Query optimieren)
    lebende = Spieler.query.filter_by(
        raum_id=raum.id, ist_am_leben=True, ist_erzaehler=False
    ).all()

    role_map = {}  # RoleName -> (RoleObj, [Spieler])

    is_first_night = raum.runde == 1

    for s in lebende:
        role = RoleRegistry.get(s.rolle)
        if not role:
            continue

        # Check night activity
        active = False
        if is_first_night:
            if role.is_active_on_first_night() or role.is_active_on_every_night():
                active = True
        else:
            if role.is_active_on_every_night():
                active = True

        if active:
            if role.info.name not in role_map:
                role_map[role.info.name] = (role, [])
            role_map[role.info.name][1].append(s)

    # Sortiere nach Priorität (aufsteigend = früher)
    # TODO: Dependencies (requires_roles) berücksichtigen?
    # Current phase_generator did topo sort.
    # For now, simple priority sort is usually enough if priorities are well set.
    # If dependencies are needed, we can port the topo sort logic.

    sorted_roles = sorted(role_map.values(), key=lambda x: x[0].info.prioritaet)
    return sorted_roles


def is_role_done(raum: "Raum", role: Any, spieler_liste: List["Spieler"]) -> bool:
    """
    Prüft ob eine Rolle für diese Runde fertig ist.
    """
    # Checke Aktionen in DB
    # Wir suchen Aktionen in raum, runde, phase='nacht' (oder generic), rolle=...
    # Aber Aktionen speichern 'von_spieler_id'.

    player_ids = [s.id for s in spieler_liste]

    aktionen = (
        SpielAktion.query.filter_by(
            raum_id=raum.id,
            runde=raum.runde,
            # phase filter weg lassen oder 'nacht'?
            # Da wir generic 'nacht' nutzen, filtern wir danach.
        )
        .filter(SpielAktion.von_spieler_id.in_(player_ids))
        .all()
    )

    # 1. Gruppen-Rollen (Werwolf): EINE Aktion reicht (gewöhnlich) oder Mehrheit?
    # Werwolf logic: Alle müssen voten oder Einer 'finalisiert'?
    # Vereinfachung: Wenn 1 Aktion existiert (Targets chosen), ist Rolle fertig.
    # TODO: Abstimmungs-Logik für Werwölfe (ActionType 'vote' vs 'kill').
    # Wenn AktionsTyp 'abstimmung' -> warten bis timer oder alle gestimmt.
    # Wenn AktionsTyp 'kill' -> fertig.

    if role.info.team == "werwolf":  # Hacky check for group role
        # Werwolf special: Check if kill action exists OR Timer?
        # Wir nehmen an: Wenn eine VALID action existiert, ist es getan.
        # Aber Werwölfe stimmen ab.
        # Wir brauchen evtl. einen Status im Raum "werwolf_done".
        pass

    # Generic check: Hat JEDER Spieler dieser Rolle eine Aktion gemacht?
    # (Für Seherin, Hexe, Amor (1 Spieler) -> Ja)
    # (Für Werwölfe (Gruppe) -> Nein, sie agieren als Gruppe)

    # Gruppen-Check Flag in Role?
    is_group_action = (
        role.info.name == "Werwolf" or role.info.name == "Drei Brüder"
    )  # Todo: Better dynamic check

    if is_group_action:
        # Check if ALL members acted
        # (Assuming every wolf must vote/ack)
        acted_ids = {a.von_spieler_id for a in aktionen}
        needed_count = len(spieler_liste)

        # If any player acted "skip" (if wolves can skip?), logic might differ.
        # But for Wernerwolf, usually all vote.
        return len(acted_ids) >= needed_count

    else:
        # Individual Actions: Check if ALL players acted
        acted_ids = {a.von_spieler_id for a in aktionen}
        for s in spieler_liste:
            if s.id not in acted_ids:
                # Can skip?
                ui_def = role.get_ui_definition()
                if ui_def.can_skip:
                    # If can skip, we might need explicit "skip" action in DB?
                    # Yes, "skip" action should be recorded.
                    return False
                return False

    return True
