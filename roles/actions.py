"""
Action Registry - Maps UI button actions to role handlers.

This module provides the mapping between frontend action types
(like "hexe_heilen") and the actual role methods that execute them.
"""

from typing import Callable, Dict, Optional, Any, TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from .base import AktionsErgebnis, SpielKontext
    from models import Spieler


# Action type normalization map - maps frontend action names to canonical forms
ACTION_TYPE_ALIASES: Dict[str, str] = {
    # Hexe actions
    "hexe_heilen": "heilen",
    "hexe_vergiften": "vergiften",
    "hexe_toeten": "vergiften",
    # Werwolf actions
    "werwolf_toeten": "toeten",
    "werwolf_angreifen": "toeten",
    # Seherin actions
    "seherin_sehen": "sehen",
    # Heiler actions
    "heiler_heilen": "heilen",
    "heiler_schuetzen": "schuetzen",
    # Jäger actions
    "jaeger_schiessen": "schiessen",
    "jaeger_toeten": "schiessen",
    # Amor actions
    "amor_verlieben": "verlieben",
    "amor_waehlen": "waehlen",
    # Common patterns
    "nichts": "skip",
    "ueberspringen": "skip",
    "keine_aktion": "skip",
}


def normalize_action_type(action_type: str) -> str:
    """
    Normalize an action type to its canonical form.
    
    This handles various naming conventions used by the frontend.
    
    Args:
        action_type: The raw action type string
        
    Returns:
        Normalized action type
    """
    if not action_type:
        return "skip"
    
    # Check direct alias
    if action_type in ACTION_TYPE_ALIASES:
        return ACTION_TYPE_ALIASES[action_type]
    
    # Try lowercase version
    lower = action_type.lower()
    if lower in ACTION_TYPE_ALIASES:
        return ACTION_TYPE_ALIASES[lower]
    
    # If action has role prefix (e.g., "hexe_heilen"), extract the action part
    if "_" in action_type:
        parts = action_type.split("_", 1)
        if len(parts) == 2:
            action_part = parts[1]
            # Check if the action part is in aliases
            if action_part in ACTION_TYPE_ALIASES:
                return ACTION_TYPE_ALIASES[action_part]
            return action_part
    
    return action_type


@dataclass
class ActionHandler:
    """Describes an action handler."""

    action_type: str
    role_name: str
    method_name: str
    description: str


class ActionRegistry:
    """
    Maps UI button actions to role handlers.

    Usage:
        # Register an action
        @ActionRegistry.register("hexe_heilen", "Hexe", "heilen")
        def hexe_heilen_handler(spieler, ziel, kontext):
            ...

        # Execute an action
        result = ActionRegistry.execute("hexe_heilen", spieler, ziel, kontext)
    """

    _handlers: Dict[str, Callable] = {}
    _metadata: Dict[str, ActionHandler] = {}

    @classmethod
    def register(
        cls,
        action_type: str,
        role_name: str = "",
        method_name: str = "",
        description: str = "",
    ):
        """
        Decorator to register an action handler.

        Args:
            action_type: The action string from the UI (e.g., "hexe_heilen")
            role_name: Name of the associated role
            method_name: Name of the method on the role
            description: Human-readable description
        """

        def decorator(func: Callable) -> Callable:
            cls._handlers[action_type] = func
            cls._metadata[action_type] = ActionHandler(
                action_type=action_type,
                role_name=role_name,
                method_name=method_name,
                description=description,
            )
            return func

        return decorator

    @classmethod
    def register_role_action(cls, action_type: str, role_name: str, method_name: str):
        """
        Register a role's method as an action handler.

        This creates a handler that looks up the role and calls the method.
        """
        from .registry import RoleRegistry

        def handler(
            spieler: "Spieler", ziel: Optional["Spieler"], kontext: "SpielKontext"
        ) -> "AktionsErgebnis":
            from .base import AktionsErgebnis

            role = RoleRegistry.get(role_name)
            if not role:
                return AktionsErgebnis(
                    erfolg=False,
                    nachricht=f"Rolle {role_name} nicht gefunden.",
                )

            method = getattr(role, method_name, None)
            if not method:
                return AktionsErgebnis(
                    erfolg=False,
                    nachricht=f"Methode {method_name} nicht gefunden.",
                )

            return method(spieler, ziel, kontext)

        cls._handlers[action_type] = handler
        cls._metadata[action_type] = ActionHandler(
            action_type=action_type,
            role_name=role_name,
            method_name=method_name,
            description=f"{role_name}.{method_name}()",
        )

    @classmethod
    def execute(
        cls,
        action_type: str,
        spieler: "Spieler",
        ziel: Optional["Spieler"],
        kontext: "SpielKontext",
    ) -> "AktionsErgebnis":
        """
        Execute an action by type.

        Args:
            action_type: The action string (e.g., "hexe_heilen")
            spieler: The player performing the action
            ziel: The target player (if any)
            kontext: Game context

        Returns:
            AktionsErgebnis from the action
        """
        from .base import AktionsErgebnis

        # Normalize the action type first
        original_action = action_type
        normalized_action = normalize_action_type(action_type)
        
        # Try exact match first
        handler = cls._handlers.get(action_type)
        if not handler:
            # Try normalized version
            handler = cls._handlers.get(normalized_action)
        
        if handler:
            try:
                return handler(spieler, ziel, kontext)
            except Exception as e:
                return AktionsErgebnis(
                    erfolg=False,
                    nachricht=f"Fehler bei Aktion: {str(e)}",
                )

        # Try to infer role and method from action_type
        # e.g., "hexe_heilen" -> role="Hexe", method="heilen"
        parts = action_type.split("_", 1)
        if len(parts) == 2:
            role_guess = parts[0].title()
            method_guess = parts[1]
            
            # Also try normalized version
            normalized_method = normalize_action_type(method_guess)

            from .registry import RoleRegistry

            role = RoleRegistry.get(role_guess)
            if role:
                # Try exact method name first
                method = getattr(role, method_guess, None)
                if not method:
                    # Try normalized method name
                    method = getattr(role, normalized_method, None)
                if not method:
                    # Try on_nacht_aktion with action parameter
                    if hasattr(role, "on_nacht_aktion"):
                        try:
                            return role.on_nacht_aktion(spieler, ziel, kontext, aktion=normalized_action)
                        except Exception as e:
                            return AktionsErgebnis(
                                erfolg=False,
                                nachricht=f"Fehler bei Aktion: {str(e)}",
                            )
                            
                if method:
                    try:
                        return method(spieler, ziel, kontext)
                    except Exception as e:
                        return AktionsErgebnis(
                            erfolg=False,
                            nachricht=f"Fehler bei Aktion: {str(e)}",
                        )

        return AktionsErgebnis(
            erfolg=False,
            nachricht=f"Unbekannte Aktion: {action_type} (normalisiert: {normalized_action})",
        )

    @classmethod
    def get_all_actions(cls) -> Dict[str, ActionHandler]:
        """Get all registered actions with metadata."""
        return cls._metadata.copy()

    @classmethod
    def has_action(cls, action_type: str) -> bool:
        """Check if an action is registered."""
        return action_type in cls._handlers


# Auto-register common role actions based on their UI definitions
def _auto_register_from_roles():
    """
    Automatically register actions from role UI definitions.

    This scans all roles and registers handlers for their UI buttons.
    """
    from .registry import RoleRegistry

    for role in RoleRegistry.get_all():
        try:
            ui = role.get_ui_definition()
            if not ui or not ui.buttons:
                continue

            for button in ui.buttons:
                action_type = button.action_type
                if action_type and not ActionRegistry.has_action(action_type):
                    # Try to find a matching method
                    # e.g., "hexe_heilen" might map to "heilen" method
                    method_name = (
                        action_type.split("_", 1)[-1]
                        if "_" in action_type
                        else action_type
                    )

                    if hasattr(role, method_name):
                        ActionRegistry.register_role_action(
                            action_type=action_type,
                            role_name=role.info.name,
                            method_name=method_name,
                        )
                    elif hasattr(role, "on_nacht_aktion"):
                        # Default to on_nacht_aktion if specific method not found
                        ActionRegistry.register_role_action(
                            action_type=action_type,
                            role_name=role.info.name,
                            method_name="on_nacht_aktion",
                        )
        except Exception:
            pass  # Skip roles that don't have UI definitions


# Note: Auto-registration happens when roles are accessed, not at import time
# to avoid circular import issues
