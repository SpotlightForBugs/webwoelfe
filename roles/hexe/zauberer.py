"""
Zauberer - Der Meister der drei Zauber.

Der Zauberer hat drei einmalige Zauber:
Schutz, Sicht und Schweigen.
"""
from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp, SichtTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Zauberer(Role):
    """
    Zauberer - Multi-Fähigkeits-Rolle.
    
    Fähigkeiten (je 1x pro Spiel):
    - Schutz: Schützt einen Spieler vor dem Tod
    - Sicht: Sieht die Rolle eines Spielers
    - Schweigen: Macht einen Spieler stumm
    
    Besonderheiten:
    - Muss wählen welchen Zauber er einsetzt
    - Jeder Zauber nur einmal verwendbar
    - Sehr vielseitig aber begrenzt
    
    Gewinnbedingung: Dorf gewinnt.
    """
    
    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=43,
            name='Zauberer',
            team=Team.DORF,
            kategorie=Kategorie.HEXE,
            beschreibung=(
                'Du bist der Zauberer. Du hast 3 Zauber: Schutz (1x), '
                'Sicht (1x) und Schweigen (1x). Setze sie weise ein, '
                'denn jeder Zauber wirkt nur einmal!'
            ),
            icon='fa-solid fa-wand-magic-sparkles',
            farbe='#3b0764',
            prioritaet=63,
            erzaehler_nacht=(
                'Der Zauberer erwacht. Welchen Zauber möchte er einsetzen? '
                '(Schutz/Sicht/Schweigen) und auf wen?'
            ),
            erzaehler_tag=None,
            hinweis_config=None,
        erweiterung=Erweiterung.SONDEREDITION,
            )
    
    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.WAEHLEN
    
    @property
    def erlaubte_ziele(self) -> str:
        return "andere"
    
    def is_active_on_first_night(self) -> bool:
        """Zauberer acts on first night."""
        return True
    
    def is_active_on_every_night(self) -> bool:
        """Zauberer acts every night until all spells are used."""
        return True
    
    def get_ui_definition(self) -> 'RollenUI':
        """Returns the UI definition for Zauberer's action panel."""
        from ..base import RollenUI, UIButton
        return RollenUI(
            title="Zauberer - Zauber wählen",
            instructions="Wähle einen Zauber: Schutz (1x), Sicht (1x) oder Schweigen (1x).",
            buttons=[
                UIButton(
                    label="Schutz-Zauber",
                    action_type="schutz",
                    icon="fa-solid fa-shield",
                    css_class="btn-primary"
                ),
                UIButton(
                    label="Sicht-Zauber",
                    action_type="sicht",
                    icon="fa-solid fa-eye",
                    css_class="btn-info"
                ),
                UIButton(
                    label="Schweigen-Zauber",
                    action_type="schweigen",
                    icon="fa-solid fa-volume-xmark",
                    css_class="btn-warning"
                )
            ],
            requires_target=True,
            allow_multiple_targets=False,
            can_skip=True
        )
    
    def on_nacht_aktion(self, spieler: 'Spieler', ziel: Optional['Spieler'],
                        kontext: SpielKontext) -> Optional[AktionsErgebnis]:
        """
        Zauberer wählt Zauber und Ziel.
        
        Die Zauber-Auswahl erfolgt über die Effekte.
        """
        # Prüfe welche Zauber noch verfügbar sind
        hat_schutz = getattr(spieler, 'zauberer_schutz', True)
        hat_sicht = getattr(spieler, 'zauberer_sicht', True)
        hat_schweigen = getattr(spieler, 'zauberer_schweigen', True)
        
        verfuegbare_zauber = []
        if hat_schutz:
            verfuegbare_zauber.append("Schutz")
        if hat_sicht:
            verfuegbare_zauber.append("Sicht")
        if hat_schweigen:
            verfuegbare_zauber.append("Schweigen")
        
        if not verfuegbare_zauber:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Du hast alle deine Zauber verbraucht.",
                effekte={"keine_zauber_mehr": True},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )
        
        if ziel is None:
            return AktionsErgebnis(
                erfolg=True,
                nachricht=(
                    f"Wähle einen Zauber ({', '.join(verfuegbare_zauber)}) "
                    f"und ein Ziel."
                ),
                effekte={"warte_auf_zauber_wahl": True},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )
        
        # Zauber wird über zusätzliche Daten gewählt
        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Wähle einen Zauber für {ziel.name}.",
            ziel_spieler_id=ziel.id,
            effekte={
                "warte_auf_zauber_typ": True,
                "verfuegbare_zauber": verfuegbare_zauber,
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )
    
    def schutz_zauber(self, spieler: 'Spieler', ziel: 'Spieler',
                      kontext: SpielKontext) -> AktionsErgebnis:
        """Schützt einen Spieler vor dem Tod diese Nacht."""
        hat_schutz = getattr(spieler, 'zauberer_schutz', True)
        
        if not hat_schutz:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du hast deinen Schutz-Zauber bereits verwendet.",
            )
        
        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Du beschützt {ziel.name} mit deinem Zauber.",
            ziel_spieler_id=ziel.id,
            effekte={
                "geschuetzt": ziel.id,
                "zauberer_schutz_verbraucht": True,
            },
            log_sichtbar_fuer="erzaehler",
        )
    
    def sicht_zauber(self, spieler: 'Spieler', ziel: 'Spieler',
                     kontext: SpielKontext) -> AktionsErgebnis:
        """Sieht die Rolle eines Spielers."""
        hat_sicht = getattr(spieler, 'zauberer_sicht', True)
        
        if not hat_sicht:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du hast deinen Sicht-Zauber bereits verwendet.",
            )
        
        ziel_rolle = RoleRegistry.get(ziel.rolle)
        if ziel_rolle:
            rollen_name = ziel_rolle.info.name
            sicht = ziel_rolle.sichtbar_als
            ist_werwolf = sicht == SichtTyp.WERWOLF
        else:
            rollen_name = ziel.rolle or "Unbekannt"
            ist_werwolf = False
        
        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Deine Vision zeigt: {ziel.name} ist ein {rollen_name}!",
            ziel_spieler_id=ziel.id,
            effekte={
                "gesehen": ziel.id,
                "rolle": rollen_name,
                "ist_werwolf": ist_werwolf,
                "zauberer_sicht_verbraucht": True,
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )
    
    def schweigen_zauber(self, spieler: 'Spieler', ziel: 'Spieler',
                         kontext: SpielKontext) -> AktionsErgebnis:
        """Macht einen Spieler stumm."""
        hat_schweigen = getattr(spieler, 'zauberer_schweigen', True)
        
        if not hat_schweigen:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du hast deinen Schweigen-Zauber bereits verwendet.",
            )
        
        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"{ziel.name} wird morgen schweigen müssen!",
            ziel_spieler_id=ziel.id,
            effekte={
                "stumm_gemacht": ziel.id,
                "zauberer_schweigen_verbraucht": True,
            },
            log_sichtbar_fuer="erzaehler",
        )
