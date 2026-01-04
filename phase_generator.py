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
import logging

logger = logging.getLogger(__name__)


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
    from game_logic import hole_lebende_spieler
    
    active_roles = []
    lebende_spieler = hole_lebende_spieler(raum)
    is_first_night = raum.runde == 1
    
    # Collect all roles that should act this night
    for spieler in lebende_spieler:
        role = RoleRegistry.get(spieler.rolle)
        if not role:
            continue
        
        # Check if role is active this night
        try:
            if is_first_night:
                aktiv = role.is_active_on_first_night() or role.is_active_on_every_night()
            else:
                aktiv = role.is_active_on_every_night()
            
            if aktiv:
                active_roles.append((role, spieler))
        except AttributeError:
            pass
    
    # Sort by dependencies and priority
    sorted_roles = _sort_roles_by_dependencies(active_roles)
    
    # Build phase list
    phases = []
    
    # Special phases that always happen
    if raum.aktuelle_phase == "nacht" or "nacht" in str(raum.aktuelle_phase):
        phases.append("nacht_start")
    
    # Add role-specific phases
    for role, spieler in sorted_roles:
        phase_name = role.get_phase_name()
        if phase_name and phase_name not in phases:
            phases.append(phase_name)
    
    # Night end transition
    if phases and phases[0].startswith("nacht"):
        phases.append("nacht_ende")
    
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
            logger.warning("Could not resolve all dependencies, using priority fallback")
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
        }
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
    lebende_spieler = hole_lebende_spieler(raum)
    is_first_night = raum.runde == 1
    
    for spieler in lebende_spieler:
        role = RoleRegistry.get(spieler.rolle)
        if not role:
            continue
        
        try:
            if is_first_night:
                aktiv = role.is_active_on_first_night() or role.is_active_on_every_night()
            else:
                aktiv = role.is_active_on_every_night()
            
            if aktiv:
                phase_name = role.get_phase_name()
                if phase_name:
                    mapping[phase_name] = role.info.name
        except AttributeError:
            pass
    
    # Special case: Werwolf phase is for all werewolves
    mapping["werwolf_phase"] = "Werwolf"
    
    return mapping
