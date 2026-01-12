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
from logger import logger

# logger = logging.getLogger(__name__) # Use centralized logger


@dataclass
class PhaseState:
    phase: str
    active_role: Optional[str] = None
    display_info: Optional[Dict[str, Any]] = None


def get_next_phase_state(raum: "Raum") -> PhaseState:
    """
    Ermittelt den nächsten Spielzustand (Phase + Aktive Rolle).
    """
    logger.debug(
        f"Scheduler: Calculating next phase state for room {raum.code} (Current: {raum.aktuelle_phase})"
    )
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
    logger.debug(f"Scheduler: Calculating next night step for room {raum.code}")
    # 1. Hole alle aktiven Rollen für diese Nacht (sortiert)
    active_roles = get_active_roles_ordered(raum)

    # 2. Prüfe wer schon fertig ist
    for role_obj, spieler_liste in active_roles:
        if not is_role_done(raum, role_obj, spieler_liste):
            # Diese Rolle ist dran!
            logger.info(f"Scheduler: Next active role is {role_obj.info.name}")
            return PhaseState(
                phase="nacht",
                active_role=role_obj.info.name,
                display_info=role_obj.get_phase_display_info()
                if hasattr(role_obj, "get_phase_display_info")
                else None,
            )

    # Alle fertig -> Tag
    logger.info("Scheduler: Night finished, transitioning to day")
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

    # Sort by priority and respect dependencies (topological sort)
    # Roles with dependencies must come after their required roles
    sorted_roles = _topological_sort_roles(role_map)
    return sorted_roles


def _topological_sort_roles(role_map: Dict[str, tuple]) -> List[Any]:
    """
    Sorts roles respecting dependencies using topological sort.
    Falls back to priority-based sort if no dependencies or circular deps detected.

    Args:
        role_map: Dict of role_name -> (role_obj, [players])

    Returns:
        List of (role_obj, [players]) tuples sorted by dependencies then priority
    """
    from collections import defaultdict, deque

    # Build dependency graph
    # in_degree[role_name] = number of roles it depends on (that must come before)
    in_degree = defaultdict(int)
    graph = defaultdict(list)  # role_name -> [roles that depend on it]
    role_priorities = {}  # for secondary sorting

    # Initialize all roles
    for role_name, (role_obj, players) in role_map.items():
        in_degree[role_name] = 0
        role_priorities[role_name] = role_obj.info.prioritaet

    # Build the graph based on requires_roles
    for role_name, (role_obj, players) in role_map.items():
        required_roles = getattr(role_obj.info, "requires_roles", [])
        for required in required_roles:
            # Only consider dependencies if the required role is active in this game
            if required in role_map:
                graph[required].append(role_name)
                in_degree[role_name] += 1

    # Topological sort using Kahn's algorithm
    # Start with roles that have no dependencies
    queue = deque()
    for role_name in role_map.keys():
        if in_degree[role_name] == 0:
            queue.append(role_name)

    # Sort queue by priority for consistent ordering
    queue = deque(sorted(queue, key=lambda r: role_priorities[r]))

    sorted_names = []
    while queue:
        # Pop role with highest priority (lowest priority number)
        current = queue.popleft()
        sorted_names.append(current)

        # Process roles that depend on current role
        dependents = sorted(graph[current], key=lambda r: role_priorities[r])
        for dependent in dependents:
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)

        # Re-sort queue by priority
        queue = deque(sorted(queue, key=lambda r: role_priorities[r]))

    # Check for circular dependencies
    if len(sorted_names) != len(role_map):
        logger.warning(
            f"Circular dependency detected in role dependencies! "
            f"Sorted: {len(sorted_names)}, Total: {len(role_map)}. "
            f"Falling back to priority-based sort."
        )
        # Fallback to simple priority sort
        sorted_names = sorted(role_map.keys(), key=lambda r: role_priorities[r])

    # Convert back to (role_obj, players) format
    return [role_map[name] for name in sorted_names]


def is_role_done(raum: "Raum", role: Any, spieler_liste: List["Spieler"]) -> bool:
    """
    Prüft ob eine Rolle für diese Runde fertig ist.
    """
    # Checke Aktionen in DB
    # Wir suchen Aktionen in raum, runde, phase='nacht' (oder generic), rolle=...
    # Aber Aktionen speichern 'von_spieler_id'.

    player_ids = [s.id for s in spieler_liste]

    aktionen = (
        SpielAktion.query.filter_by(raum_id=raum.id, runde=raum.runde)
        .filter(SpielAktion.von_spieler_id.in_(player_ids))
        .all()
    )

    # Dynamically check if role acts as a group using the role's property
    is_group_action = getattr(role, "is_group_action", False)

    if is_group_action:
        # Group voting logic (e.g., Werewolves)
        # Two scenarios:
        # 1. Voting phase: Wait until timer expires or all voted
        # 2. Direct kill: One action is enough (consensus reached)

        ui_def = role.get_ui_definition()
        action_type = getattr(ui_def, "action_type", "kill")  # Default to 'kill'

        if action_type == "vote":
            # Voting: Need all members to vote OR timer to expire
            # For now, require all members (timer handled elsewhere)
            acted_ids = {a.von_spieler_id for a in aktionen}
            needed_count = len(spieler_liste)

            is_done = len(acted_ids) >= needed_count
            if not is_done:
                logger.debug(
                    f"Role {role.info.name} voting: {len(acted_ids)}/{needed_count} voted"
                )
            return is_done
        else:
            # Direct action (kill/select): One action represents group consensus
            # Check if ANY action exists (indicating the group decided)
            if aktionen:
                logger.debug(f"Role {role.info.name} group action completed")
                return True
            logger.debug(f"Role {role.info.name} waiting for group consensus")
            return False

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
                    logger.debug(
                        f"Role {role.info.name} waiting for player {s.name} (can skip: {ui_def.can_skip})"
                    )
                    return False
                logger.debug(f"Role {role.info.name} waiting for player {s.name}")
                return False

    return True
