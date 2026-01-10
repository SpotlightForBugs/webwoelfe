"""
Phase Generator - Dynamic phase ordering based on role dependencies.

This module generates the night phase sequence by:
1. Collecting all active roles for the current night
2. Resolving role dependencies (requires_roles, requires_phases)
3. Sorting by priority while respecting dependencies
4. Building phase-to-role mappings for the frontend
"""

from typing import List, Dict, Optional, Set, Tuple
from models import Raum, Spieler
from roles import RoleRegistry
from logger import logger


def generate_phases_for_game(raum: Raum) -> List[str]:
    """
    Generate the complete phase list for the current game night.

    This determines which roles act this night and in what order,
    respecting role dependencies and priorities.

    Args:
        raum: The game room

    Returns:
        List of phase names (e.g., ["werwolf_phase", "seherin_phase", "hexe_phase"])
    """
    logger.debug(f"Generating phases for room {raum.code} (Round {raum.runde})")
    from game_logic import hole_lebende_spieler

    active_roles = []
    lebende_spieler = hole_lebende_spieler(raum)
    is_first_night = raum.runde == 1

    logger.info(
        f"[PhaseGen] Generating phases. Players: {len(lebende_spieler)}, Round: {raum.runde}, First Night: {is_first_night}"
    )

    # Collect all roles that should act this night
    for spieler in lebende_spieler:
        role = RoleRegistry.get(spieler.rolle)
        if not role:
            logger.warning(
                f"[PhaseGen] Role not found in registry for player {spieler.name}: {spieler.rolle}"
            )
            continue

        # Check if role is active this night
        try:
            if is_first_night:
                aktiv = (
                    role.is_active_on_first_night() or role.is_active_on_every_night()
                )
            else:
                aktiv = role.is_active_on_every_night()

            if aktiv:
                logger.debug(
                    f"[PhaseGen] Role active: {role.info.name} (Player: {spieler.name})"
                )
                active_roles.append((role, spieler))
            else:
                logger.debug(
                    f"[PhaseGen] Role INACTIVE: {role.info.name} (Player: {spieler.name})"
                )

        except AttributeError as e:
            logger.error(
                f"[PhaseGen] Error checking activity for {role.info.name}: {e}"
            )
            pass

    logger.info(f"[PhaseGen] Found {len(active_roles)} active roles")

    # Sort by dependencies and priority
    sorted_roles = _sort_roles_by_dependencies(active_roles)
    logger.debug(f"Sorted active roles: {[r[0].info.name for r in sorted_roles]}")

    # Build phase list
    phases = []

    # Special phases that always happen
    # Always include start/end markers if we are in a night cycle (including role phases)
    current_phase_str = str(raum.aktuelle_phase)
    is_night_cycle = "nacht" in current_phase_str

    if not is_night_cycle and current_phase_str.endswith("_phase"):
        # Dynamic check: Does this phase belong to a night-active role?
        for role in RoleRegistry.get_all():
            if role.get_phase_name() == current_phase_str:
                # If role is active at night, treat as night cycle (handles exceptions like Jaeger dynamically)
                if role.is_active_on_first_night() or role.is_active_on_every_night():
                    is_night_cycle = True
                break

    if is_night_cycle:
        phases.append("nacht_start")

    # Add role-specific phases
    for role, spieler in sorted_roles:
        phase_name = role.get_phase_name()
        if phase_name and phase_name not in phases:
            phases.append(phase_name)

    # Night end transition
    if phases and phases[0].startswith("nacht"):
        phases.append("nacht_ende")

    logger.info(f"Generated phases: {phases}")
    return phases


def _sort_roles_by_dependencies(roles: List[Tuple]) -> List[Tuple]:
    """
    Sort roles by dependencies and priority.

    Uses topological sort to ensure roles with dependencies come after
    their prerequisites, then sorts by priority within each level.

    Args:
        roles: List of (role, spieler) tuples

    Returns:
        Sorted list of (role, spieler) tuples
    """
    if not roles:
        return []

    # Build dependency graph
    role_map = {role.info.name: (role, spieler) for role, spieler in roles}
    role_names = set(role_map.keys())

    # Track dependencies that actually exist in this game
    dependencies: Dict[str, Set[str]] = {}
    for role, _ in roles:
        deps = set()
        for required in role.info.requires_roles:
            if required in role_names:
                deps.add(required)
        dependencies[role.info.name] = deps

    # Topological sort with priority
    sorted_names = []
    visited = set()
    temp_mark = set()

    def visit(name: str):
        if name in temp_mark:
            logger.warning(f"Circular dependency detected involving role: {name}")
            return
        if name in visited:
            return

        temp_mark.add(name)

        # Visit dependencies first
        for dep in dependencies.get(name, set()):
            if dep in role_names:
                visit(dep)

        temp_mark.remove(name)
        visited.add(name)
        sorted_names.append(name)

    # Visit all roles
    for role_name in role_names:
        if role_name not in visited:
            visit(role_name)

    # Now sort by priority within dependency levels
    # Build result maintaining dependency order but sorting by priority where possible
    result = []
    remaining = sorted_names.copy()

    while remaining:
        # Find all roles whose dependencies are satisfied
        ready = []
        for name in remaining:
            deps_satisfied = all(
                dep in [r.info.name for r, _ in result]
                for dep in dependencies.get(name, set())
            )
            if deps_satisfied:
                role, spieler = role_map[name]
                ready.append((role.info.prioritaet, name, role, spieler))

        if not ready:
            # Circular dependency or error - just add remaining by priority
            logger.warning(
                "Could not resolve all dependencies, using priority fallback"
            )
            for name in remaining:
                role, spieler = role_map[name]
                ready.append((role.info.prioritaet, name, role, spieler))

        # Sort ready roles by priority
        ready.sort(key=lambda x: x[0])

        # Add them to result
        for priority, name, role, spieler in ready:
            result.append((role, spieler))
            if name in remaining:
                remaining.remove(name)

    return result


def get_phase_display_info(phase_name: str) -> Dict:
    """
    Get display information for a phase.

    Args:
        phase_name: Name of the phase (e.g., "werwolf_phase")

    Returns:
        Dict with display info (title, icon, description, etc.)
    """
    # Try to match phase to a role
    role_name = phase_name.replace("_phase", "").replace("_", " ").title()
    role = RoleRegistry.get(role_name)

    if role:
        return {
            "name": phase_name,
            "display_name": role.info.name,
            "icon": role.info.icon,
            "color": role.info.farbe,
            "description": f"{role.info.name} ist an der Reihe",
        }

    # Generic phase info for non-role phases
    generic_phases = {
        "nacht_start": {
            "name": "nacht_start",
            "display_name": "Nacht beginnt",
            "icon": "fa-solid fa-moon",
            "color": "#1e293b",
            "description": "Das Dorf schläft ein...",
        },
        "nacht_ende": {
            "name": "nacht_ende",
            "display_name": "Nacht endet",
            "icon": "fa-solid fa-moon",
            "color": "#475569",
            "description": "Die Nacht geht zu Ende",
        },
        "tag_start": {
            "name": "tag_start",
            "display_name": "Tag beginnt",
            "icon": "fa-solid fa-sun",
            "color": "#f59e0b",
            "description": "Das Dorf erwacht",
        },
        "diskussion": {
            "name": "diskussion",
            "display_name": "Diskussion",
            "icon": "fa-solid fa-comments",
            "color": "#3b82f6",
            "description": "Zeit für Diskussion",
        },
        "abstimmung": {
            "name": "abstimmung",
            "display_name": "Abstimmung",
            "icon": "fa-solid fa-gavel",
            "color": "#dc2626",
            "description": "Wählt einen Spieler",
        },
    }

    return generic_phases.get(
        phase_name,
        {
            "name": phase_name,
            "display_name": phase_name.replace("_", " ").title(),
            "icon": "fa-solid fa-circle",
            "color": "#64748b",
            "description": "",
        },
    )


def build_phase_role_mapping(raum: Raum) -> Dict[str, str]:
    """
    Build a mapping from phase names to role names for this game.

    This is used by the frontend to determine which players should
    see action buttons during each phase.

    Args:
        raum: The game room

    Returns:
        Dict mapping phase_name -> role_name (e.g., {"seherin_phase": "Seherin"})
    """
    from game_logic import hole_lebende_spieler

    mapping = {}
    shared_phase_roles = {}  # Track shared phases and their primary role
    lebende_spieler = hole_lebende_spieler(raum)
    is_first_night = raum.runde == 1

    for spieler in lebende_spieler:
        role = RoleRegistry.get(spieler.rolle)
        if not role:
            continue

        try:
            if is_first_night:
                aktiv = (
                    role.is_active_on_first_night() or role.is_active_on_every_night()
                )
            else:
                aktiv = role.is_active_on_every_night()

            if aktiv:
                # Check for shared phase name (e.g., all werewolf variants share werwolf_phase)
                shared_phase = getattr(role, "shared_phase_name", None)
                if shared_phase:
                    # Track shared phases, use the first role found as primary
                    if shared_phase not in shared_phase_roles:
                        shared_phase_roles[shared_phase] = role.info.name
                    mapping[shared_phase] = shared_phase_roles[shared_phase]
                else:
                    phase_name = role.get_phase_name()
                    if phase_name:
                        mapping[phase_name] = role.info.name
        except AttributeError:
            pass

    return mapping


def initialize_game_phases(raum: Raum):
    """
    Initializes the phase generator for a new game.
    """
    logger.info(f"Initializing game phases for room {raum.code}")
    # Currently stateless, but could store cached phases in raum.zusatz_daten if needed
    pass


def get_next_phase(raum: Raum) -> str:
    """
    Determines the next phase for the given room.
    Uses dynamic role-based night phases and fixed day phases.

    Special phases (like jaeger_phase) are now handled dynamically
    based on role's get_triggered_phases() method.
    """
    logger.info(
        f"Getting next phase for room {raum.code} (Current: {raum.aktuelle_phase})"
    )

    current_phase = raum.aktuelle_phase

    # 1. Setup -> Night
    if current_phase == "rollen_verteilt":
        return "nacht_start"

    # 2. Day Cycle (Fixed Order)
    if current_phase == "tag_start":
        return "tag_abstimmung"

    if current_phase == "tag_abstimmung":
        return "hinrichtung"

    if current_phase == "hinrichtung":
        return "tag_ende"

    if current_phase == "tag_ende":
        return "nacht_start"

    # 3. Special phases triggered by role effects (DYNAMIC - no more hardcoding!)
    # Check if current phase is a role-triggered special phase
    special_phase_next = _get_special_phase_next_phase(raum, current_phase)
    if special_phase_next:
        return special_phase_next

    # 4. Night Cycle (Dynamic based on active roles)
    if (
        current_phase == "nacht_start"
        or "nacht" in current_phase
        or "_phase" in current_phase
    ):
        night_phases = generate_phases_for_game(raum)

        if not night_phases:
            logger.warning("No night phases generated! Skipping to day.")
            return "nacht_ende"

        try:
            idx = night_phases.index(current_phase)
            if idx + 1 < len(night_phases):
                return night_phases[idx + 1]
            else:
                return "nacht_ende"
        except ValueError:
            if current_phase == "nacht_start":
                return night_phases[0] if night_phases else "nacht_ende"
            logger.warning(
                f"Phase {current_phase} not in night phases, going to nacht_ende"
            )
            return "nacht_ende"

    if current_phase == "nacht_ende":
        return "tag_start"

    # Fallback
    logger.warning(f"Unknown phase {current_phase}, defaulting to tag_start")
    return "tag_start"


def _get_special_phase_next_phase(raum: Raum, current_phase: str) -> Optional[str]:
    """
    Check if the current phase is a role-triggered special phase and return
    the next phase based on the role's configuration.

    This replaces hardcoded logic like 'if current_phase == "jaeger_phase": return "tag_ende"'
    """
    from roles import RoleRegistry

    # Check all roles for special phase configurations
    for role in RoleRegistry.get_all():
        try:
            triggered_phases = role.get_triggered_phases()
            for phase_config in triggered_phases:
                if phase_config.phase_name == current_phase:
                    # Found the role that owns this special phase
                    if phase_config.next_phase_override:
                        logger.info(
                            f"Special phase {current_phase} -> {phase_config.next_phase_override}"
                        )
                        return phase_config.next_phase_override
                    else:
                        # Default: return to normal day/night flow
                        # If it was triggered during day, go back to day_end
                        # If during night, continue to nacht_ende
                        logger.info(
                            f"Special phase {current_phase} -> returning to normal flow (tag_ende)"
                        )
                        return "tag_ende"
        except Exception as e:
            logger.debug(f"Error checking triggered phases for {role.info.name}: {e}")
            continue

    return None
