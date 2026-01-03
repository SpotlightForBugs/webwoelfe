"""
Hund - Der treue Begleiter mit dunkler Seite.

Der Hund wählt in der ersten Nacht sein Herrchen.
Stirbt das Herrchen, wird der Hund zum Werwolf!
"""
from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, SichtTyp, AktionsTyp
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Hund(Role):
    """
    Hund - Bedingte Verwandlungs-Rolle.
    
    Fähigkeiten:
    - Wählt in der ersten Nacht sein Herrchen
    - Stirbt das Herrchen: Wird zum Werwolf
    - Solange Herrchen lebt: Teil des Dorfes
    
    Besonderheiten:
    - Nur EINMAL aktiv (erste Nacht für Herrchen-Wahl)
    - Danach keine Nacht-Aktion mehr
    - Seherin sieht ihn als Dorf, bis Verwandlung
    
    Gewinnbedingung: Abhängig von Verwandlung.
    - Vor Verwandlung: Dorf gewinnt
    - Nach Verwandlung: Werwölfe gewinnen
    """
    
    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=19,
            name='Hund',
            team=Team.DORF,  # Startet als Dorf
            kategorie=Kategorie.DORFBEWOHNER,
            beschreibung=(
                'Du bist der treue Hund. Du wählst in der ersten Nacht ein '
                'Herrchen. Solange dein Herrchen lebt, gehörst du zum Dorf. '
                'Stirbt dein Herrchen, wechselst du zum Team der Werwölfe über!'
            ),
            icon='fa-solid fa-dog',
            farbe='#a16207',
            nacht_aktiv=True,
            prioritaet=7,  # Früh in der Nacht, ähnlich wie Amor/Wildes Kind
            erzaehler_nacht='Der Hund erwacht (nur erste Nacht) und wählt sein Herrchen.',
            erzaehler_tag=None,
            hinweis_config=None,
        )
    
    @property
    def sichtbar_als(self) -> SichtTyp:
        """
        Der Hund sieht für die Seherin als Dorf aus.
        
        Auch nach der Verwandlung sieht er als Dorf aus,
        da er technisch immer noch ein Hund ist - nur sein
        Loyalitäts-Team hat sich geändert.
        """
        return SichtTyp.DORF
    
    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.WAEHLEN
    
    @property
    def erlaubte_ziele(self) -> str:
        """Kann jeden anderen lebenden Spieler als Herrchen wählen."""
        return "andere"
    
    def ist_nacht_aktiv(self, spieler: 'Spieler', kontext: SpielKontext) -> bool:
        """
        Der Hund ist NUR in der ersten Nacht aktiv.
        
        Nach der Herrchen-Wahl hat er keine weitere Nacht-Aktion.
        """
        # Nur Runde 1 und noch kein Herrchen gewählt
        herrchen_gewaehlt = getattr(spieler, 'hund_herrchen_gewaehlt', False)
        return kontext.runde == 1 and not herrchen_gewaehlt
    
    def on_spiel_start(self, spieler: 'Spieler', kontext: SpielKontext) -> Optional[AktionsErgebnis]:
        """
        Der Hund bereitet sich auf die Herrchen-Wahl vor.
        """
        return AktionsErgebnis(
            erfolg=True,
            nachricht="Wähle in der ersten Nacht dein Herrchen.",
            effekte={"warte_auf_herrchen_wahl": True},
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )
    
    def on_nacht_aktion(self, spieler: 'Spieler', ziel: Optional['Spieler'],
                        kontext: SpielKontext) -> Optional[AktionsErgebnis]:
        """
        Hauptaktion: Herrchen wählen (nur erste Nacht).
        """
        # Prüfe ob noch aktiv
        if not self.ist_nacht_aktiv(spieler, kontext):
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Du hast bereits dein Herrchen gewählt.",
                effekte={"keine_aktion": True},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )
        
        # Wenn kein Ziel, warten auf Wahl
        if ziel is None:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Wähle dein Herrchen für dieses Spiel.",
                effekte={"warte_auf_herrchen_wahl": True},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )
        
        # Herrchen wählen
        return self.herrchen_waehlen(spieler, ziel, kontext)
    
    def herrchen_waehlen(self, spieler: 'Spieler', herrchen: 'Spieler',
                         kontext: SpielKontext) -> AktionsErgebnis:
        """
        Setzt das gewählte Herrchen.
        
        Args:
            spieler: Der Hund
            herrchen: Das gewählte Herrchen
            kontext: Spielkontext
            
        Returns:
            Ergebnis der Aktion
        """
        # Validierung: Kann sich nicht selbst wählen
        if herrchen.id == spieler.id:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du kannst dich nicht selbst als Herrchen wählen.",
            )
        
        # Validierung: Herrchen muss leben
        if herrchen.id not in kontext.lebende_spieler:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Das Herrchen muss am Leben sein.",
            )
        
        # Erfolg!
        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"{herrchen.name} ist nun dein Herrchen. Beschütze es mit deinem Leben!",
            ziel_spieler_id=herrchen.id,
            effekte={
                "herrchen_id": herrchen.id,
                "herrchen_gewaehlt": True,
                "event_typ": "hund_herrchen",
            },
            log_sichtbar_fuer="erzaehler",
        )
    
    def on_spieler_stirbt(self, spieler: 'Spieler', opfer: 'Spieler',
                          todesursache: str, kontext: SpielKontext) -> Optional[AktionsErgebnis]:
        """
        Prüft ob das Herrchen stirbt und löst Verwandlung aus.
        
        Wenn das Herrchen des Hundes stirbt:
        - Der Hund wechselt zum Werwolf-Team
        - Er nimmt an Werwolf-Beratungen teil
        - Er stimmt über Opfer mit ab
        - Die Seherin sieht ihn weiterhin als Dorf (da SichtTyp.DORF)
        
        Args:
            spieler: Der Hund
            opfer: Der sterbende Spieler
            todesursache: Art des Todes
            kontext: Spielkontext
        """
        herrchen_id = getattr(spieler, 'herrchen_id', None)
        
        # Kein Herrchen gesetzt (sollte nicht passieren)
        if herrchen_id is None:
            return None
        
        # Nicht das Herrchen
        if opfer.id != herrchen_id:
            return None
        
        # Hund selbst ist bereits tot
        if spieler.id not in kontext.lebende_spieler:
            return None
        
        # Das Herrchen stirbt! Verwandlung auslösen!
        return AktionsErgebnis(
            erfolg=True,
            nachricht=(
                f"Das Herrchen des Hundes ({opfer.name}) ist gestorben! "
                f"{spieler.name} der treue Hund verwandelt sich vor Trauer "
                f"in einen Werwolf!"
            ),
            effekte={
                "verwandlung": True,
                "neues_team": Team.WERWOLF.value,
                "ist_jetzt_werwolf": True,
                "event_typ": "hund_verwandelt",
                # Der Hund behält seinen Rollennamen, wechselt aber das Team
                # Dies erlaubt der Seherin weiterhin "Dorf" zu sehen
            },
            log_sichtbar_fuer="erzaehler",
        )
    
    def berechne_aktuelles_team(self, spieler: 'Spieler') -> Team:
        """
        Berechnet das aktuelle Team des Hundes.
        
        Nützlich für Gewinnbedingung-Prüfungen.
        """
        # Prüfe ob Herrchen noch lebt
        herrchen_id = getattr(spieler, 'herrchen_id', None)
        
        if herrchen_id is None:
            # Noch kein Herrchen gewählt, gehört zum Dorf
            return Team.DORF
        
        # Wenn Hund verwandelt ist (über Effekt gesetzt)
        ist_werwolf = getattr(spieler, 'ist_verflucht', False)  # Wiederverwendung des Flags
        if ist_werwolf:
            return Team.WERWOLF
        
        return Team.DORF
    
    def on_spiel_ende(self, spieler: 'Spieler', gewinner_team: Team, 
                      kontext: SpielKontext) -> bool:
        """
        Prüft ob der Hund gewonnen hat.
        
        Der Hund gewinnt mit dem Team, zu dem er aktuell gehört:
        - Vor Verwandlung: Dorf
        - Nach Verwandlung: Werwölfe
        """
        aktuelles_team = self.berechne_aktuelles_team(spieler)
        return aktuelles_team == gewinner_team
