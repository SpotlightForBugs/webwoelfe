"""
Action Registry - Dynamic action routing for role handlers.

This module provides dynamic action routing between frontend actions
and role handlers. NO HARDCODED MAPPINGS - everything is discovered
dynamically from role definitions.
"""

from typing import Callable, Dict, Optional, Any, Set, TYPE_CHECKING
from dataclasses import dataclass
from logger import logger

if TYPE_CHECKING:
    from .base import AktionsErgebnis, SpielKontext
    from models import Spieler


def extract_action_parts(action_type: str) -> tuple:
    """
    Extract role prefix and action from an action type string.

    Examples:
        "hexe_heilen" -> ("hexe", "heilen")
        "heilen" -> (None, "heilen")
        "amor_verlieben" -> ("amor", "verlieben")
        "jaeger_schuss" -> ("jaeger", "schuss")
        "skip" -> (None, "skip")

    Returns:
        Tuple of (role_prefix, action_name)
    """
    if not action_type:
        return (None, "skip")

    if "_" in action_type:
        parts = action_type.split("_", 1)
        return (parts[0].lower(), parts[1])

    return (None, action_type)


def normalize_action_type(action_type: str) -> str:
    """
    Normalize an action type to its base form.

    This handles role prefixes and common variations dynamically,
    without hardcoded mappings.

    Args:
        action_type: The raw action type string (e.g., "hexe_heilen", "heilen")

    Returns:
        Normalized action type (e.g., "heilen")
    """
    if not action_type:
        return "skip"

    # Handle explicit skip variations
    skip_variations = {
        "nichts",
        "ueberspringen",
        "keine_aktion",
        "skip",
        "überspringen",
    }
    if action_type.lower() in skip_variations:
        return "skip"

    # Extract action part (handles "hexe_heilen" -> "heilen")
    _, action = extract_action_parts(action_type)

    return action


def find_matching_action(role, action_type: str) -> Optional[str]:
    """
    Find a matching action in the role's UI definition.

    Checks both the original action_type and its normalized form
    against the role's buttons and actions.

    Args:
        role: The role instance
        action_type: The action type from frontend

    Returns:
        The matched action_type from the role's definition, or None
    """
    try:
        ui = role.get_ui_definition()
        if not ui:
            return None

        _, normalized = extract_action_parts(action_type)

        # Check RoleAction entries first
        for action in ui.actions:
            if (
                action.action_id == action_type
                or action.action_type == action_type
                or action.action_id == normalized
                or action.action_type == normalized
            ):
                return action.action_id

        # Check legacy UIButton entries
        for button in ui.buttons:
            btn_type = button.action_type
            if btn_type == action_type or btn_type == normalized:
                return btn_type
            # Also check if button's action matches our normalized form
            _, btn_normalized = extract_action_parts(btn_type)
            if btn_normalized == normalized:
                return btn_type

        return None
    except Exception:
        return None


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
                            return role.on_nacht_aktion(
                                spieler, ziel, kontext, aktion=normalized_action
                            )
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
