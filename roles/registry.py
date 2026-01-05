"""
Rollen-Registry mit automatischer Erkennung und Registrierung.

Die Registry sammelt alle Rollen-Klassen und stellt sie
über einen zentralen Zugriffspunkt zur Verfügung.
"""

import logging
from typing import Dict, Type, Optional, List, Iterator, Any
from .base import Role, RollenInfo
from .enums import Team, Kategorie

# Logger konfigurieren
logger = logging.getLogger(__name__)


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
            logger.info(f"Rolle manuell registriert: {name}")
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
