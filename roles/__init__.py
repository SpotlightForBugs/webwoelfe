"""
Webwoelfe - Modulares Rollensystem

Dieses Paket enthält alle Rollen als separate Klassen.
Jede Rolle erbt von der Basisklasse Role und implementiert
ihre spezifischen Fähigkeiten über Trigger-Methoden.

WICHTIG: Neue Rollen hinzufügen
==============================
Um eine neue Rolle hinzuzufügen, erstelle einfach eine .py-Datei
im passenden Unterverzeichnis (z.B. roles/dorfbewohner/neue_rolle.py).
Die Rolle wird automatisch erkannt und registriert - KEINE weiteren
Änderungen in __init__.py oder models.py nötig!

Architektur:
- base.py: Abstrakte Basisklasse Role
- registry.py: Automatische Rollenregistrierung
- enums.py: Team, Kategorie und Phasen-Enums
- triggers.py: Event-System für Rollen-Aktionen

Rollen-Verzeichnisse:
- grundrollen/: Basis-Rollen (Dorfbewohner, Werwolf, Seherin, etc.)
- dorfbewohner/: Dorf-Varianten
- werwolf/: Werwolf-Varianten
- seher/: Seher-Varianten
- hexe/: Hexen-Varianten
- jaeger/: Jäger-Varianten
- heiler/: Heiler-Varianten
- spezial/: Spezialrollen
- solo/: Solo-Gewinner-Rollen
"""

import os
import importlib
import pkgutil
from pathlib import Path

from .base import (
    Role,
    StateType,
    StateTarget,
    StateVisualEffect,
    VisualEffectConfig,
    TargetingConfig,
    StateField,
    GlobalStateDefinition,
    NachtEvent,
    UIButtonDefinition,
    RollenModell,
    AppearanceFeature,
    ErzaehlerEvent,
    HinweisConfig,
    RollenInfo,
    AktionsErgebnis,
    SpielKontext,
    UIButton,
    RollenUI,
    get_spieler_state,
    set_spieler_state,
    get_all_spieler_state,
    init_spieler_state,
    reset_spieler_state,
    has_global_state,
    get_players_with_state,
    get_player_visual_effects,
    get_role_state_display,
)
from .registry import RoleRegistry
from .enums import Team, Kategorie, Phase, TriggerTyp, Erweiterung

__all__ = [
    # Base classes
    "Role",
    "RollenInfo",
    "AktionsErgebnis",
    "SpielKontext",
    "UIButton",
    "RollenUI",
    # State management
    "StateType",
    "StateTarget",
    "StateVisualEffect",
    "VisualEffectConfig",
    "TargetingConfig",
    "StateField",
    "GlobalStateDefinition",
    "NachtEvent",
    "UIButtonDefinition",
    "RollenModell",
    "AppearanceFeature",
    "ErzaehlerEvent",
    "HinweisConfig",
    "get_spieler_state",
    "set_spieler_state",
    "get_all_spieler_state",
    "init_spieler_state",
    "reset_spieler_state",
    "get_role_state_display",
    # Registry
    "RoleRegistry",
    # Enums
    "Team",
    "Kategorie",
    "Phase",
    "TriggerTyp",
    "Erweiterung",
    # Legacy functions
    "get_alle_rollen",
    "get_rollen_nach_kategorie",
    "get_rollen_nach_kategorie_liste",
    "get_rollen_nach_erweiterung",
    "get_rollen_anzahl",
    "ROLLEN",
    "ERWEITERUNG_INFO",
    "KATEGORIE_INFO",
]


def _auto_discover_roles():
    """
    Automatische Erkennung und Registrierung aller Rollen.

    Durchsucht alle Unterverzeichnisse nach Python-Dateien
    und importiert sie automatisch. Der @RoleRegistry.register
    Decorator in jeder Rolle-Klasse erledigt die Registrierung.
    """
    roles_dir = Path(__file__).parent

    # Alle Unterverzeichnisse durchsuchen
    for subdir in roles_dir.iterdir():
        if not subdir.is_dir():
            continue
        if subdir.name.startswith("_") or subdir.name.startswith("."):
            continue

        # Alle .py Dateien im Unterverzeichnis importieren
        for py_file in subdir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue

            # Modul-Name: roles.unterverzeichnis.dateiname
            module_name = f"roles.{subdir.name}.{py_file.stem}"
            try:
                importlib.import_module(module_name)
            except Exception as e:
                print(f"[Rollen] Warnung: Konnte {module_name} nicht laden: {e}")


# Führe Auto-Discovery beim Import aus
_auto_discover_roles()

# Registriere automatisch alle Actions aus den Rollen-UI-Definitionen
# Dies muss NACH _auto_discover_roles() passieren!
try:
    from .actions import _auto_register_from_roles
    _auto_register_from_roles()
    print("[Rollen] Action-Registry automatisch gefüllt")
except Exception as e:
    print(f"[Rollen] Warnung: Konnte Actions nicht automatisch registrieren: {e}")


# ============================================================================
# DYNAMISCHE ROLLEN-ZUGRIFFSFUNKTIONEN
# Diese ersetzen die statischen Funktionen aus models.py
# ============================================================================


def get_alle_rollen():
    """
    Gibt alle registrierten Rollen als Legacy-Dict zurück.
    Ersetzt das statische ROLLEN-Dict aus models.py.
    """
    return RoleRegistry.to_legacy_dict()


def get_rollen_nach_kategorie():
    """
    Gibt alle Rollen gruppiert nach Kategorie zurück.
    Format: dict[kategorie][rolle_name] = rolle_data
    """
    kategorien = {}
    for rolle in RoleRegistry.get_all():
        kat = rolle.info.kategorie.value
        if kat not in kategorien:
            kategorien[kat] = {}
        kategorien[kat][rolle.info.name] = rolle.to_dict()
    return kategorien


def get_rollen_nach_kategorie_liste():
    """
    Gibt alle Rollen gruppiert nach Kategorie als Liste zurück.
    Format: dict[kategorie] = [rolle_data, ...]
    Sortiert nach ID innerhalb jeder Kategorie.
    """
    kategorien = {}
    for rolle in RoleRegistry.get_all():
        kat = rolle.info.kategorie.value
        if kat not in kategorien:
            kategorien[kat] = []
        rolle_dict = rolle.to_dict()
        rolle_dict["name"] = rolle.info.name
        kategorien[kat].append(rolle_dict)

    # Sortiere nach ID innerhalb jeder Kategorie
    for kat in kategorien:
        kategorien[kat].sort(key=lambda x: x.get("id", 999))

    return kategorien


def get_rollen_anzahl():
    """Gibt die Anzahl aller verfuegbaren Rollen zurueck."""
    return RoleRegistry.count()


def get_rollen_nach_erweiterung():
    """
    Gibt alle Rollen gruppiert nach Erweiterungspaket zurueck.
    Format: dict[erweiterung] = [rolle_data, ...]
    Sortiert nach ID innerhalb jeder Erweiterung.
    """
    erweiterungen = {}
    for rolle in RoleRegistry.get_all():
        erw = rolle.info.erweiterung.value
        if erw not in erweiterungen:
            erweiterungen[erw] = []
        rolle_dict = rolle.to_dict()
        rolle_dict["name"] = rolle.info.name
        erweiterungen[erw].append(rolle_dict)

    # Sortiere nach ID innerhalb jeder Erweiterung
    for erw in erweiterungen:
        erweiterungen[erw].sort(key=lambda x: x.get("id", 999))

    return erweiterungen


# Metadaten fuer Erweiterungspakete (fuer UI)
ERWEITERUNG_INFO = {
    "basisspiel": {
        "name": "Basisspiel",
        "icon": "fa-solid fa-box",
        "beschreibung": "Die klassischen Grundrollen",
        "badge": "Basis",
        "badge_class": "base",
    },
    "neumond": {
        "name": "Neumond",
        "icon": "fa-solid fa-moon",
        "beschreibung": "Heiler, Alter, Suendenbock, Floetenspieler & mehr",
        "badge": "Erw. 1",
        "badge_class": "exp1",
    },
    "gemeinde": {
        "name": "Die Gemeinde",
        "icon": "fa-solid fa-city",
        "beschreibung": "Gebaeude & Berufe: Brandstifter, Rabe & mehr",
        "badge": "Erw. 2",
        "badge_class": "exp2",
    },
    "charaktere": {
        "name": "Charaktere",
        "icon": "fa-solid fa-users",
        "beschreibung": "Neue Charaktere: Wolfsrudel, Gruppen & mehr!",
        "badge": "Erw. 3",
        "badge_class": "exp3",
    },
    "community": {
        "name": "Community",
        "icon": "fa-solid fa-star",
        "beschreibung": "Community-erstellte Rollen",
        "badge": "Community",
        "badge_class": "community",
    },
}


# Metadaten fuer Kategorien (fuer UI)
KATEGORIE_INFO = {
    "grundrollen": {
        "name": "Grundrollen",
        "icon": "fa-solid fa-users",
        "beschreibung": "Die klassischen Rollen, die in jedem Spiel vorkommen.",
    },
    "dorfbewohner": {
        "name": "Dorfbewohner-Varianten",
        "icon": "fa-solid fa-user",
        "beschreibung": "Spezielle Dorfbewohner mit einzigartigen Faehigkeiten.",
    },
    "werwolf": {
        "name": "Werwolf-Varianten",
        "icon": "fa-solid fa-paw",
        "beschreibung": "Verschiedene Arten von Werwoelfen mit speziellen Kraeften.",
    },
    "seher": {
        "name": "Sehende Rollen",
        "icon": "fa-solid fa-eye",
        "beschreibung": "Rollen mit der Faehigkeit, verborgene Informationen zu enthuellen.",
    },
    "hexe": {
        "name": "Hexen & Zauberer",
        "icon": "fa-solid fa-hat-wizard",
        "beschreibung": "Magische Rollen mit Traenken und Zaubern.",
    },
    "jaeger": {
        "name": "Jaeger & Kaempfer",
        "icon": "fa-solid fa-crosshairs",
        "beschreibung": "Aggressive Rollen, die andere Spieler eliminieren koennen.",
    },
    "heiler": {
        "name": "Heiler & Beschuetzer",
        "icon": "fa-solid fa-heart-pulse",
        "beschreibung": "Rollen, die andere Spieler vor dem Tod bewahren koennen.",
    },
    "spezial": {
        "name": "Spezialrollen",
        "icon": "fa-solid fa-star",
        "beschreibung": "Einzigartige Rollen mit besonderen Gewinnbedingungen.",
    },
    "boese": {
        "name": "Vampire & andere Boese",
        "icon": "fa-solid fa-skull",
        "beschreibung": "Weitere antagonistische Rollen neben den Werwoelfen.",
    },
    "solo": {
        "name": "Einzelkaempfer",
        "icon": "fa-solid fa-user-secret",
        "beschreibung": "Solo-Rollen mit eigenen Gewinnbedingungen.",
    },
    "sonstige": {
        "name": "Sonstige Rollen",
        "icon": "fa-solid fa-masks-theater",
        "beschreibung": "Weitere interessante Rollen, die das Spiel bereichern.",
    },
}


# ============================================================================
# ROLLEN DICT
# Simple wrapper around RoleRegistry.to_legacy_dict() for backwards compat
# ============================================================================


def _get_rollen_dict():
    """Get all roles as a dict. Called lazily to avoid circular imports."""
    return RoleRegistry.to_legacy_dict()


# For backwards compatibility - this is a function call, not a class
class _LazyRollenDict(dict):
    """Lazily loads roles on first access."""

    _loaded = False

    def _ensure_loaded(self):
        if not self._loaded:
            self.update(RoleRegistry.to_legacy_dict())
            self._loaded = True

    def __getitem__(self, key):
        self._ensure_loaded()
        return super().__getitem__(key)

    def get(self, key, default=None):
        self._ensure_loaded()
        return super().get(key, default)

    def __contains__(self, key):
        self._ensure_loaded()
        return super().__contains__(key)

    def items(self):
        self._ensure_loaded()
        return super().items()

    def keys(self):
        self._ensure_loaded()
        return super().keys()

    def values(self):
        self._ensure_loaded()
        return super().values()

    def __len__(self):
        self._ensure_loaded()
        return super().__len__()


ROLLEN = _LazyRollenDict()
