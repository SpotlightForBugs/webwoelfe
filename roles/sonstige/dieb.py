"""
Dieb - Wählt zwischen zwei Rollen.

Der Dieb sieht zu Beginn zwei übrige Rollen
und muss eine davon wählen.
"""
from typing import Optional, List, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Dieb(Role):
    """
    Dieb - Rollenwahl zu Beginn.
    
    Fähigkeiten:
    - Sieht zu Beginn 2 übrige Rollen
    - Muss eine davon wählen
    - Muss Werwolf wählen wenn einer dabei ist
    
    Besonderheiten:
    - Erste Aktion im Spiel
    - Zwingende Werwolf-Wahl
    - Übernimmt dann die neue Rolle
    
    Gewinnbedingung: Abhängig von gewählter Rolle.
    """
    
    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=96,
            name='Dieb',
            team=Team.DORF,  # Startet neutral
            kategorie=Kategorie.SONSTIGE,
            beschreibung=(
                'Du bist der Dieb. Zu Beginn siehst du zwei übrige Rollen '
                'und darfst dir eine aussuchen. Ist ein Werwolf dabei, '
                'musst du ihn wählen!'
            ),
            icon='fa-solid fa-mask',
            farbe='#1e293b',
            nacht_aktiv=True,
            prioritaet=1,  # Erste Rolle!
            erzaehler_nacht=(
                'Der Dieb erwacht zuerst und sieht zwei Rollen. '
                'Er muss eine wählen.'
            ),
            erzaehler_tag=None,
            hinweis_config=None,
        )
    
    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.WAEHLEN
    
    def ist_nacht_aktiv(self, spieler: 'Spieler', kontext: SpielKontext) -> bool:
        """Nur in der ersten Nacht aktiv."""
        hat_gewaehlt = getattr(spieler, 'dieb_hat_gewaehlt', False)
        return kontext.aktuelle_runde == 1 and not hat_gewaehlt
    
    def zeige_rollen(self, spieler: 'Spieler',
                     kontext: SpielKontext) -> AktionsErgebnis:
        """
        Zeigt dem Dieb die zwei verfügbaren Rollen.
        """
        # Die übrigen Rollen werden vom Spielleiter bestimmt
        uebrige_rollen: List[str] = getattr(kontext, 'dieb_optionen', [])
        
        if len(uebrige_rollen) < 2:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Es gibt keine Rollen zur Auswahl!",
            )
        
        hat_werwolf = any('werwolf' in rolle.lower() for rolle in uebrige_rollen)
        
        hinweis = ""
        if hat_werwolf:
            hinweis = " ACHTUNG: Ein Werwolf ist dabei - du MUSST ihn wählen!"
        
        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Du siehst zwei Rollen: {uebrige_rollen[0]} und {uebrige_rollen[1]}.{hinweis}",
            effekte={
                "dieb_optionen": uebrige_rollen,
                "werwolf_pflicht": hat_werwolf,
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )
    
    def rolle_waehlen(self, spieler: 'Spieler', wahl: int,
                      kontext: SpielKontext) -> AktionsErgebnis:
        """
        Dieb wählt eine der beiden Rollen (0 oder 1).
        """
        uebrige_rollen: List[str] = getattr(kontext, 'dieb_optionen', [])
        
        if wahl not in [0, 1] or len(uebrige_rollen) < 2:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Ungültige Wahl!",
            )
        
        gewaehlte_rolle = uebrige_rollen[wahl]
        andere_rolle = uebrige_rollen[1 - wahl]
        
        # Prüfen ob Werwolf dabei ist
        hat_werwolf = any('werwolf' in rolle.lower() for rolle in uebrige_rollen)
        ist_werwolf_wahl = 'werwolf' in gewaehlte_rolle.lower()
        
        if hat_werwolf and not ist_werwolf_wahl:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du MUSST den Werwolf wählen!",
            )
        
        spieler.dieb_hat_gewaehlt = True
        
        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Du wirst zum {gewaehlte_rolle}!",
            effekte={
                "rolle_wechsel": gewaehlte_rolle,
                "dieb_hat_gewaehlt": True,
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )
