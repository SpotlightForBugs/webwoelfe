"""
Abstrakte Basisklasse fuer alle Rollen.

Jede Rolle erbt von dieser Klasse und implementiert
ihre spezifischen Faehigkeiten ueber die Trigger-Methoden.

Design-Prinzipien:
- Single Responsibility: Jede Rolle ist fuer ihre eigene Logik verantwortlich
- Open/Closed: Neue Rollen durch Vererbung, keine Aenderung der Basis
- DRY: Gemeinsame Logik in der Basisklasse
- Dependency Injection: Spielkontext wird per Parameter uebergeben
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from .enums import Team, Kategorie, Phase, TriggerTyp, AktionsTyp, SichtTyp, Erweiterung

if TYPE_CHECKING:
    from models import Spieler, Raum


@dataclass
class RollenInfo:
    """Statische Informationen ueber eine Rolle (fuer UI/Dokumentation)."""

    id: int
    name: str
    team: Team
    kategorie: Kategorie
    beschreibung: str
    icon: str  # FontAwesome class (e.g., "fa-solid fa-eye")
    farbe: str  # Hex color code (e.g., "#7c3aed")
    prioritaet: int = 100  # Lower = earlier in night order (e.g., Amor=5, Werwolf=50, Hexe=90)
    erzaehler_nacht: Optional[str] = None
    erzaehler_tag: Optional[str] = None
    hinweis_config: Optional[str] = None
    erweiterung: Erweiterung = Erweiterung.BASISSPIEL
    
    # Phase ordering and dependencies
    requires_roles: List[str] = field(default_factory=list)  # Roles that must act before this one
    requires_phases: List[str] = field(default_factory=list)  # Generic phases that must happen first
    
    # Extension pack for UI filtering
    @property
    def extension_pack(self) -> str:
        """Returns extension pack identifier for frontend filtering."""
        pack_map = {
            Erweiterung.BASISSPIEL: "base",
            Erweiterung.NEUMOND: "neumond",
            Erweiterung.GEMEINDE: "gemeinde",
            Erweiterung.CHARAKTERE: "charaktere",
            Erweiterung.SONDEREDITION: "sonderedition",
        }
        return pack_map.get(self.erweiterung, "base")


@dataclass
class AktionsErgebnis:
    """Ergebnis einer Rollen-Aktion."""

    erfolg: bool
    nachricht: Optional[str] = None
    ziel_spieler_id: Optional[int] = None
    effekte: Dict[str, Any] = field(default_factory=dict)
    log_sichtbar_fuer: str = "alle"  # alle, erzaehler, werwolf, spieler_id


@dataclass
class SpielKontext:
    """Kontext für Rollen-Aktionen (Dependency Injection)."""

    raum_id: int
    runde: int
    phase: Phase
    aktiver_spieler_id: int
    lebende_spieler: List[int]
    tote_spieler: List[int]
    werwolf_opfer_id: Optional[int] = None
    aktionen_diese_runde: List[Dict[str, Any]] = field(default_factory=list)
    # Dynamically added attributes
    spieler_rollen: Dict[int, Any] = field(default_factory=dict)
    spieler_namen: Dict[int, str] = field(default_factory=dict)
    spieler_teams: Dict[int, Any] = field(default_factory=dict)

    def hat_spieler_rolle(self, spieler_id: int, rolle: str) -> bool:
        """Prüft ob ein Spieler eine bestimmte Rolle hat."""
        # Wird von der Registry implementiert
        return False


@dataclass
class UIButton:
    """Definition for a UI button in the action panel."""
    label: str
    action_type: str
    icon: Optional[str] = None
    css_class: str = "btn-primary"
    requires_confirmation: bool = False


@dataclass
class RollenUI:
    """UI definition for a role's action panel."""
    title: str
    instructions: str
    buttons: List[UIButton] = field(default_factory=list)
    requires_target: bool = True
    allow_multiple_targets: bool = False
    can_skip: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "title": self.title,
            "instructions": self.instructions,
            "buttons": [
                {
                    "label": btn.label,
                    "action_type": btn.action_type,
                    "icon": btn.icon,
                    "css_class": btn.css_class,
                    "requires_confirmation": btn.requires_confirmation,
                }
                for btn in self.buttons
            ],
            "requires_target": self.requires_target,
            "allow_multiple_targets": self.allow_multiple_targets,
            "can_skip": self.can_skip,
        }


class Role(ABC):
    """
    Abstrakte Basisklasse für alle Rollen.

    Jede Rolle muss die abstrakten Methoden implementieren
    und kann optionale Trigger-Methoden überschreiben.
    """

    # === ABSTRAKTE EIGENSCHAFTEN (müssen in jeder Rolle definiert sein) ===

    @property
    @abstractmethod
    def info(self) -> RollenInfo:
        """Gibt die statischen Informationen der Rolle zurück."""
        pass

    # === STANDARD-EIGENSCHAFTEN (können überschrieben werden) ===

    @property
    def kann_hinweis_senden(self) -> bool:
        """Kann diese Rolle aktiv Hinweise auf sich ziehen?"""
        return False

    @property
    def verfuegbare_hinweise(self) -> List[str]:
        """Welche Hinweise kann die Rolle senden?"""
        return []

    @property
    def hinweise_pro_tag(self) -> int:
        """Wie viele Hinweise pro Tag?"""
        return 0

    @property
    def basis_hinweis_chance(self) -> float:
        """Basis-Wahrscheinlichkeit für automatische Hinweise."""
        team = self.info.team
        if team == Team.WERWOLF:
            return 0.15
        elif team == Team.DORF:
            return 0.05
        elif team == Team.SOLO:
            return 0.10
        return 0.08

    @property
    def sichtbar_als(self) -> SichtTyp:
        """Wie erscheint diese Rolle der Seherin?"""
        if self.info.team == Team.WERWOLF:
            return SichtTyp.WERWOLF
        return SichtTyp.DORF

    def sichtbar_als_fuer(self, seher_rolle: str) -> SichtTyp:
        """Wie erscheint diese Rolle einer bestimmten Seher-Rolle?"""
        return self.sichtbar_als

    def sichtbare_rolle_fuer(self, seher_rolle: str) -> str:
        """Welche Rollenbezeichnung sieht eine bestimmte Seher-Rolle?"""
        return self.info.name

    @property
    def aktions_typ(self) -> AktionsTyp:
        """Welche Aktion führt diese Rolle aus?"""
        return AktionsTyp.KEINE

    @abstractmethod
    def is_active_on_first_night(self) -> bool:
        """Determines if the role acts on the first night."""
        pass
    
    @abstractmethod
    def is_active_on_every_night(self) -> bool:
        """Determines if the role acts on subsequent nights."""
        pass
    
    @abstractmethod
    def get_ui_definition(self) -> 'RollenUI':
        """Defines the UI for the role's action phase."""
        pass

    @property
    def kann_ziel_waehlen(self) -> bool:
        """Muss ein Ziel für die Aktion gewählt werden?"""
        # Derived from UI definition implicitly or lifecycle
        # We keep this for backward compatibility or logic that uses it
        # Default behavior: active roles usually select targets unless specified otherwise
        return self.is_active_on_first_night() or self.is_active_on_every_night()
    
    @property
    def erlaubte_ziele(self) -> str:
        """Welche Spieler können als Ziel gewählt werden?"""
        return "lebende"  # lebende, tote, alle, andere, nachbarn, werwolf

    # === TRIGGER-METHODEN (werden bei Events aufgerufen) ===

    def on_spiel_start(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Wird beim Spielstart aufgerufen.

        Nützlich für:
        - Amor: Verliebte wählen
        - Wildes Kind: Vorbild wählen
        - Freimaurer: Sich erkennen
        """
        return None

    def on_nacht_start(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Wird zu Beginn jeder Nacht aufgerufen.

        Nützlich für:
        - Status-Resets
        - Bedingte Aktivierungen
        """
        return None

    def on_nacht_aktion(
        self, spieler: "Spieler", ziel: Optional["Spieler"], kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Hauptaktion während der Nacht.

        Wird aufgerufen wenn die Phase dieser Rolle aktiv ist.
        """
        return None

    def on_nacht_ende(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Wird am Ende jeder Nacht aufgerufen.

        Nützlich für:
        - Berechnungen nach allen Aktionen
        - Infektionen auswerten
        """
        return None

    def on_tag_start(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Wird zu Beginn jedes Tages aufgerufen.

        Nützlich für:
        - Gift-Countdown
        - Auferstehungen
        """
        return None

    def on_spieler_stirbt(
        self,
        spieler: "Spieler",
        opfer: "Spieler",
        todesursache: str,
        kontext: SpielKontext,
    ) -> Optional[AktionsErgebnis]:
        """
        Wird aufgerufen wenn irgendein Spieler stirbt.

        Parameter:
            spieler: Der Spieler mit dieser Rolle
            opfer: Der sterbende Spieler
            todesursache: werwolf, hexe, jäger, hinrichtung, etc.
            kontext: Spielkontext

        Nützlich für:
        - Jäger: Letzter Schuss wenn selbst gestorben
        - Wildes Kind: Vorbild-Check
        - Verliebte: Mit-Sterben
        """
        return None

    def on_eigener_tod(
        self, spieler: "Spieler", todesursache: str, kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Wird aufgerufen wenn der Spieler mit dieser Rolle stirbt.

        Nützlich für:
        - Jäger: Letzter Schuss
        - Jesus: Auferstehungs-Timer
        - Gerber: Gewinn-Check
        """
        return None

    def on_angegriffen(
        self, spieler: "Spieler", angreifer: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Wird aufgerufen wenn der Spieler angegriffen wird (vor dem Tod).

        Nützlich für:
        - Alter Mann: Erstes Leben verlieren
        - Leibwächter: Sich opfern

        Return AktionsErgebnis mit erfolg=False um Angriff zu blocken.
        """
        return None

    def on_geheilt(
        self, spieler: "Spieler", heiler: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Wird aufgerufen wenn der Spieler geheilt wird.
        """
        return None

    def on_abstimmung(
        self, spieler: "Spieler", ziel: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Wird bei der Tagesabstimmung aufgerufen.

        Nützlich für:
        - Bürgermeister: Doppelstimme
        - Prinz: Immunität gegen Hinrichtung
        """
        return None

    def on_hinrichtung(
        self, spieler: "Spieler", opfer: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Wird bei einer Hinrichtung aufgerufen.

        Nützlich für:
        - Prinz: Hinrichtung verhindern (einmalig)
        - Alter Mann: Dorf verfluchen
        """
        return None

    def on_spiel_ende(
        self, spieler: "Spieler", gewinner_team: Team, kontext: SpielKontext
    ) -> bool:
        """
        Wird am Spielende aufgerufen.

        Return True wenn dieser Spieler auch gewonnen hat.

        Nützlich für:
        - Solo-Rollen mit speziellen Gewinnbedingungen
        - Verliebte
        """
        return (
            self.info.team == gewinner_team
            or self.info.team.value == gewinner_team.value
        )

    def berechne_gewinn(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> Optional[Team]:
        """
        Prüft ob diese Rolle gewonnen hat (für Solo-Rollen).

        Return None wenn kein Gewinn, sonst das gewinnende Team.
        """
        return None

    # === HILFSMETHODEN ===

    def get_phase_name(self) -> str:
        """Gibt den Namen der Nacht-Phase zurueck."""
        return f"{self.info.name.lower().replace(' ', '_')}_phase"

    def validate_ziel(
        self, spieler: "Spieler", ziel: "Spieler", kontext: SpielKontext
    ) -> bool:
        """Prueft ob das Ziel gueltig ist."""
        if ziel is None and self.kann_ziel_waehlen:
            return False

        if self.erlaubte_ziele == "lebende":
            return ziel.id in kontext.lebende_spieler
        elif self.erlaubte_ziele == "tote":
            return ziel.id in kontext.tote_spieler
        elif self.erlaubte_ziele == "andere":
            return ziel.id != spieler.id and ziel.id in kontext.lebende_spieler
        elif self.erlaubte_ziele == "werwolf":
            return kontext.hat_spieler_rolle(ziel.id, "Werwolf")

        return True

    def has_voted_this_phase(self, spieler: "Spieler", kontext: SpielKontext) -> bool:
        """Prueft ob der Spieler bereits in dieser Phase gewaehlt hat."""
        # Check aktionen_diese_runde for existing vote from this player
        for aktion in kontext.aktionen_diese_runde:
            if aktion.get("von_spieler_id") == spieler.id:
                return True
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert role to dictionary for API/JSON."""
        return {
            'id': self.info.id,
            'team': self.info.team.value,
            'kategorie': self.info.kategorie.value,
            'beschreibung': self.info.beschreibung,
            'nacht_aktiv': self.is_active_on_first_night() or self.is_active_on_every_night(), # Derived
            'prioritaet': self.info.prioritaet,
            'icon': self.info.icon,
            'farbe': self.info.farbe,
            'erzaehler_nacht': self.info.erzaehler_nacht,
            'erzaehler_tag': self.info.erzaehler_tag,
            'hinweis_config': self.info.hinweis_config,
            'erweiterung': self.info.erweiterung.value,
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(team={self.info.team.value})>"
