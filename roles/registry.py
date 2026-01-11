"""
Rollen-Registry mit automatischer Erkennung und Registrierung.

Die Registry sammelt alle Rollen-Klassen und stellt sie
über einen zentralen Zugriffspunkt zur Verfügung.
"""

import logging
from typing import Dict, Type, Optional, List, Iterator, Any
from .base import Role, RollenInfo
from .enums import Team, Kategorie
from logger import logger

# Logger konfigurieren
# logger = logging.getLogger(__name__) # Use centralized logger


class RollenRegistryMeta(type):
    """
    Metaklasse die automatisch alle Role-Unterklassen registriert.
    """

    _registry: Dict[str, Type[Role]] = {}
    _instances: Dict[str, Role] = {}

    def __new__(mcs, name: str, bases: tuple, namespace: dict):
        cls = super().__new__(mcs, name, bases, namespace)

        # Nur konkrete Klassen registrieren (nicht Role selbst)
        if bases and Role in bases[0].__mro__:
            # Rolle temporär instanziieren um den Namen zu bekommen
            try:
                instance = cls()
                rollen_name = instance.info.name
                mcs._registry[rollen_name] = cls
                mcs._instances[rollen_name] = instance
                logger.debug(f"Rolle registriert: {rollen_name}")
            except (TypeError, AttributeError) as e:
                # Abstrakte Klassen überspringen (erwartet)
                # Aber andere Fehler loggen
                if "abstract" not in str(e).lower():
                    logger.warning(f"Konnte Rolle {name} nicht registrieren: {e}")

        return cls


class RoleRegistry:
    """
    Singleton-Registry für alle Rollen.

    Verwendung:
        registry = RoleRegistry()
        werwolf = registry.get("Werwolf")
        alle_woelfe = registry.get_by_team(Team.WERWOLF)
    """

    _registry: Dict[str, Type[Role]] = {}
    _instances: Dict[str, Role] = {}
    _initialized: bool = False

    @classmethod
    def register(cls, role_class: Type[Role]) -> Type[Role]:
        """
        Decorator zum manuellen Registrieren einer Rolle.

        @RoleRegistry.register
        class MeineRolle(Role):
            ...
        """
        try:
            instance = role_class()
            name = instance.info.name
            cls._registry[name] = role_class
            cls._instances[name] = instance
            logger.info(f"Rolle via Decorator registriert: {name}")
        except Exception as e:
            logger.error(
                f"Fehler beim Registrieren der Rolle {role_class.__name__}: {e}"
            )
        return role_class

    @classmethod
    def get(cls, name: str) -> Optional[Role]:
        """
        Gibt eine Rollen-Instanz zurück.

        Args:
            name: Name der Rolle (z.B. "Werwolf", "Seherin")

        Returns:
            Role-Instanz oder None wenn nicht gefunden
        """
        # logger.debug(f"Fetching role instance: {name}") # Too verbose
        return cls._instances.get(name)

    @classmethod
    def get_class(cls, name: str) -> Optional[Type[Role]]:
        """Gibt die Rollen-Klasse zurück."""
        return cls._registry.get(name)

    @classmethod
    def create(cls, name: str) -> Optional[Role]:
        """Erstellt eine neue Instanz der Rolle."""
        role_class = cls._registry.get(name)
        if role_class:
            return role_class()
        return None

    @classmethod
    def get_all(cls) -> List[Role]:
        """Gibt alle registrierten Rollen zurück."""
        return list(cls._instances.values())

    @classmethod
    def get_all_names(cls) -> List[str]:
        """Gibt alle Rollen-Namen zurück."""
        return list(cls._registry.keys())

    @classmethod
    def get_by_team(cls, team: Team) -> List[Role]:
        """Gibt alle Rollen eines Teams zurück."""
        return [role for role in cls._instances.values() if role.info.team == team]

    @classmethod
    def get_by_kategorie(cls, kategorie: Kategorie) -> List[Role]:
        """Gibt alle Rollen einer Kategorie zurück."""
        return [
            role for role in cls._instances.values() if role.info.kategorie == kategorie
        ]

    @classmethod
    def get_nacht_aktive(cls) -> List[Role]:
        """Gibt alle nachtaktiven Rollen sortiert nach Priorität zurück."""
        aktive = [
            role
            for role in cls._instances.values()
            if role.is_active_on_first_night() or role.is_active_on_every_night()
        ]
        return sorted(aktive, key=lambda r: r.info.prioritaet)

    @classmethod
    def get_by_id(cls, role_id: int) -> Optional[Role]:
        """Gibt eine Rolle anhand ihrer ID zurück."""
        for role in cls._instances.values():
            if role.info.id == role_id:
                return role
        return None

    @classmethod
    def exists(cls, name: str) -> bool:
        """Prüft ob eine Rolle existiert."""
        return name in cls._registry

    @classmethod
    def count(cls) -> int:
        """Gibt die Anzahl registrierter Rollen zurück."""
        return len(cls._registry)

    @classmethod
    def to_legacy_dict(cls) -> Dict[str, Dict[str, Any]]:
        """
        Konvertiert alle Rollen zum Legacy-ROLLEN-Dict-Format.

        Für Abwärtskompatibilität mit bestehendem Code.
        """
        return {name: role.to_dict() for name, role in cls._instances.items()}

    @classmethod
    def get_phase_role_mapping(cls) -> Dict[str, str]:
        """
        Gibt ein Mapping von Phase-Namen zu Rollen-Namen zurück.

        Für die Nacht-Phasen-Logik.
        """
        mapping = {}
        for name, role in cls._instances.items():
            if role.is_active_on_first_night() or role.is_active_on_every_night():
                phase_name = role.get_phase_name()
                mapping[phase_name] = name
        return mapping

    @classmethod
    def get_role_for_phase(cls, phase_name: str) -> Optional[Role]:
        """
        Gibt die Rolle zurück, die für eine bestimmte Phase zuständig ist.

        Args:
            phase_name: Name der Phase (z.B. "werwolf_phase")

        Returns:
            Role-Instanz oder None
        """
        # logger.debug(f"Finding role for phase: {phase_name}") # Too verbose
        # Normalisiere Phasen-Name (entferne _phase suffix)
        normalized = phase_name.replace("_phase", "").replace("_", " ").title()

        # Suche nach passender Rolle
        for role in cls._instances.values():
            if role.get_phase_name() == phase_name:
                return role
            # Fallback: Prüfe Rollen-Namen
            if role.info.name.lower().replace(" ", "_") in phase_name.lower():
                return role

        return None

    # === AGGREGATION FUNCTIONS ===

    @classmethod
    def get_all_erzaehler_events(cls) -> Dict[str, Any]:
        """
        Sammelt alle Erzähler-Events aus allen registrierten Rollen.

        Returns:
            Dict von event_id -> ErzaehlerEvent
        """
        from .base import ErzaehlerEvent

        all_events = {}
        for role in cls._instances.values():
            try:
                events = role.get_erzaehler_events()
                for event in events:
                    all_events[event.event_id] = {
                        "text": event.text,
                        "anweisung": event.anweisung,
                        "bedingung": event.bedingung,
                        "einmalig": event.einmalig,
                        "rolle": role.info.name,
                    }
            except Exception as e:
                logger.warning(
                    f"Fehler beim Laden der Events von {role.info.name}: {e}"
                )

        return all_events

    @classmethod
    def get_all_hinweis_configs(cls) -> Dict[str, Any]:
        """
        Sammelt alle Hinweis-Konfigurationen aus allen registrierten Rollen.

        Returns:
            Dict von rolle_name -> HinweisConfig
        """
        configs = {}
        for name, role in cls._instances.items():
            try:
                config = role.get_hinweis_config()
                if config.kann_senden or config.basis_chance > 0:
                    configs[name] = {
                        "kann_senden": config.kann_senden,
                        "verfuegbare_hinweise": config.verfuegbare_hinweise,
                        "hinweise_pro_tag": config.hinweise_pro_tag,
                        "basis_chance": config.basis_chance,
                        "beschreibung": config.beschreibung,
                    }
            except Exception as e:
                logger.warning(f"Fehler beim Laden der Hint-Config von {name}: {e}")

        return configs

    @classmethod
    def init_player_state(cls, spieler: "Spieler") -> None:
        """
        Initialisiert den Zustand für die Rolle eines Spielers.

        Ruft init_state() auf der entsprechenden Rolle auf.

        Args:
            spieler: Der Spieler dessen Zustand initialisiert werden soll
        """
        from .base import reset_spieler_state

        if not spieler.rolle:
            return

        logger.debug(
            f"Initializing state for player {spieler.name} (Role: {spieler.rolle})"
        )
        role = cls.get(spieler.rolle)
        if role:
            role.init_state(spieler)

    @classmethod
    def init_all_players_state(cls, spieler_liste: List["Spieler"]) -> None:
        """
        Initialisiert den Zustand für alle Spieler.

        Args:
            spieler_liste: Liste aller Spieler
        """
        from .base import reset_spieler_state

        for spieler in spieler_liste:
            reset_spieler_state(spieler)
            cls.init_player_state(spieler)

    @classmethod
    def get_all_state_fields(cls) -> Dict[str, List[Dict[str, Any]]]:
        """
        Sammelt alle State-Field-Definitionen aus allen Rollen.

        Returns:
            Dict von rolle_name -> Liste von StateField-Dicts
        """
        result = {}
        for name, role in cls._instances.items():
            fields = role.state_fields()
            if fields:
                result[name] = [
                    {
                        "name": sf.name,
                        "typ": sf.typ.value,
                        "default": sf.default,
                        "beschreibung": sf.beschreibung,
                        "persistent": sf.persistent,
                    }
                    for sf in fields
                ]
        return result

    @classmethod
    def get_all_global_state_definitions(cls) -> Dict[str, Any]:
        """
        Sammelt alle GlobalStateDefinitions aus allen Rollen.

        Diese definieren States die Rollen auf ANDERE Spieler setzen können
        (z.B. Amor setzt verliebt_mit_id, Urwolf setzt ist_infiziert).

        Returns:
            Dict von state_key -> GlobalStateDefinition-Dict
        """
        from .base import GlobalStateDefinition

        result = {}
        for name, role in cls._instances.items():
            try:
                defs = role.global_state_definitions()
                for gsd in defs:
                    result[gsd.key] = {
                        "key": gsd.key,
                        "name": gsd.name,
                        "typ": gsd.typ.value,
                        "beschreibung": gsd.beschreibung,
                        "default": gsd.default,
                        "visual_effect": (
                            gsd.visual_effect.value if gsd.visual_effect else None
                        ),
                        "css_class": gsd.css_class,
                        "icon": gsd.icon,
                        "query_name": gsd.query_name,
                        "defined_by": gsd.defined_by or name,
                    }
            except Exception as e:
                logger.warning(
                    f"Fehler beim Laden der GlobalStateDefinitions von {name}: {e}"
                )

        return result

    @classmethod
    def get_all_global_state_definitions_objects(
        cls,
    ) -> Dict[str, "GlobalStateDefinition"]:
        """
        Sammelt alle GlobalStateDefinitions als Objekte (nicht Dicts).

        Für Verwendung durch get_player_visual_effects() die Zugriff auf
        die vollständigen Objekte inkl. Visibility-Felder benötigt.

        Returns:
            Dict von state_key -> GlobalStateDefinition-Objekt
        """
        from .base import GlobalStateDefinition

        result = {}
        for name, role in cls._instances.items():
            try:
                defs = role.global_state_definitions()
                for gsd in defs:
                    result[gsd.key] = gsd
            except Exception as e:
                logger.warning(
                    f"Fehler beim Laden der GlobalStateDefinitions von {name}: {e}"
                )

        return result

    @classmethod
    def get_players_by_query(
        cls, spieler_liste: List["Spieler"], query_name: str
    ) -> List["Spieler"]:
        """
        Findet Spieler basierend auf einem Query-Namen.

        Args:
            spieler_liste: Liste aller Spieler
            query_name: Der Query-Name (z.B. "verliebte", "infizierte")

        Returns:
            Liste der passenden Spieler
        """
        from .base import get_spieler_state

        all_defs = cls.get_all_global_state_definitions()

        # Finde den State-Key für den Query-Namen
        target_key = None
        for key, gsd in all_defs.items():
            if gsd.get("query_name") == query_name:
                target_key = key
                break

        if not target_key:
            return []

        # Finde Spieler mit diesem State
        result = []
        for s in spieler_liste:
            value = get_spieler_state(s, target_key)
            if value is not None and value is not False and value != 0:
                result.append(s)

        return result

    @classmethod
    def get_all_nacht_events(
        cls, aktive_rollen: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Sammelt alle Nacht-Events von allen (oder spezifizierten) Rollen.

        Args:
            aktive_rollen: Optional - Liste der aktiven Rollennamen im Spiel

        Returns:
            Liste von NachtEvent-Dicts
        """
        result = []
        for name, role in cls._instances.items():
            if aktive_rollen and name not in aktive_rollen:
                continue
            try:
                events = role.get_nacht_events()
                for event in events:
                    result.append(
                        {
                            "event_id": event.event_id,
                            "sound_file": event.sound_file,
                            "text": event.text,
                            "animation": event.animation,
                            "phases": event.phases,
                            "defined_by": name,
                        }
                    )
            except Exception as e:
                logger.warning(f"Fehler beim Laden der NachtEvents von {name}: {e}")
        return result

    @classmethod
    def get_all_ui_buttons_for_others(
        cls, spieler: "Spieler", kontext: Any, aktive_rollen: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Sammelt alle UI-Buttons die andere Rollen für diesen Spieler definiert haben.

        Args:
            spieler: Der Spieler für den Buttons gesammelt werden
            kontext: SpielKontext
            aktive_rollen: Optional - Liste der aktiven Rollennamen im Spiel

        Returns:
            Liste von UIButtonDefinition-Dicts
        """
        result = []
        for name, role in cls._instances.items():
            if aktive_rollen and name not in aktive_rollen:
                continue
            try:
                buttons = role.get_ui_buttons_for_others()
                for btn in buttons:
                    # Prüfe ob dieser Spieler den Button sehen soll
                    if btn.show_to and not btn.show_to(spieler, kontext):
                        continue
                    result.append(
                        {
                            "button_id": btn.button_id,
                            "label": btn.label,
                            "action_type": btn.action_type,
                            "icon": btn.icon,
                            "css_class": btn.css_class,
                            "requires_confirmation": btn.requires_confirmation,
                            "tooltip": btn.tooltip,
                            "defined_by": name,
                        }
                    )
            except Exception as e:
                logger.warning(f"Fehler beim Laden der UIButtons von {name}: {e}")
        return result

    @classmethod
    def get_modell_for_player(cls, spieler: "Spieler") -> Optional[Dict[str, Any]]:
        """
        Ermittelt das 3D/2D Modell für einen Spieler basierend auf seiner Rolle.

        Args:
            spieler: Der Spieler

        Returns:
            RollenModell-Dict oder None
        """
        if not spieler.rolle:
            return None

        role = cls.get(spieler.rolle)
        if not role:
            return None

        try:
            modell = role.get_modell_definition(spieler)
            return {
                "modell_id": modell.modell_id,
                "anzeige_name": modell.anzeige_name,
                "beschreibung": modell.beschreibung,
            }
        except Exception as e:
            logger.warning(f"Fehler beim Laden des Modells für {spieler.rolle}: {e}")
            return None

    @classmethod
    def clear(cls) -> None:
        """Löscht alle registrierten Rollen (für Tests)."""
        cls._registry.clear()
        cls._instances.clear()

    def __iter__(self) -> Iterator[Role]:
        """Ermöglicht Iteration über alle Rollen."""
        return iter(self._instances.values())

    def __len__(self) -> int:
        return len(self._registry)

    def __contains__(self, name: str) -> bool:
        return name in self._registry


# Globale Registry-Instanz
registry = RoleRegistry()
