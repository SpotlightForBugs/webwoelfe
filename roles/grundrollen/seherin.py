"""
Seherin - Die wichtigste Informationsrolle des Dorfes.

Die Seherin kann jede Nacht die wahre Identität
eines Spielers erfahren.
"""

from typing import Optional, TYPE_CHECKING, List
from ..base import (
    AppearanceFeature,
    RollenModell,
    BodyModification,
    AnimationState,
    HintEffect3D,
    Role,
    RollenInfo,
    AktionsErgebnis,
    SpielKontext,
    DistributionConfig,
    # Factory functions
    create_crystal_ball,
    create_pointed_hat,
    create_aura,
    create_death_marker,
)
from ..enums import Team, Kategorie, AktionsTyp, SichtTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Seherin(Role):
    """
    Die Seherin - Informationsrolle.

    Fähigkeiten:
    - Kann jede Nacht einen Spieler "sehen"
    - Erfährt ob das Ziel Werwolf oder Dorf ist

    Gewinnbedingung: Dorf gewinnt.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=3,
            name="Seherin",
            team=Team.DORF,
            kategorie=Kategorie.GRUNDROLLEN,
            beschreibung=(
                "Du bist die Seherin. Jede Nacht kannst du die wahre Identität "
                "eines Spielers erfahren - ob er ein Werwolf ist oder nicht."
            ),
            icon="fa-solid fa-eye",
            farbe="#7c3aed",
            prioritaet=20,
            erzaehler_nacht=(
                "Die Seherin erwacht und zeigt auf einen Spieler. "
                "Du zeigst ihr mit Daumen hoch (Dorf) oder runter (Werwolf) "
                "die Zugehörigkeit."
            ),
            erweiterung=Erweiterung.BASISSPIEL,
            # Visual Styling
            avatar_gradient_from="#7c3aed",
            avatar_gradient_to="#5b21b6",
            avatar_border_color="#a78bfa",
            badge_emoji="fa-solid fa-eye",
            distribution=DistributionConfig(
                min_players=5,
                # 1 Seherin ab 5 Spielern
                count_func=lambda n: max(1, n // 50),
                priority=20,
                exclusive_with=[],
            ),
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.SEHEN

    @property
    def erlaubte_ziele(self) -> str:
        return "andere"  # Kann sich nicht selbst sehen

    def is_active_on_first_night(self) -> bool:
        """Seherin acts on first night."""
        return True

    def is_active_on_every_night(self) -> bool:
        """Seherin acts every night."""
        return True

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Seherin's action panel."""
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Seherin - Spieler sehen",
            instructions="Wähle einen Spieler, dessen wahre Identität du erfahren möchtest.",
            buttons=[
                UIButton(
                    label="Sehen",
                    action_type="sehen",
                    icon="fa-solid fa-eye",
                    css_class="btn-primary",
                    requires_confirmation=False,
                )
            ],
            requires_target=True,
            allow_multiple_targets=False,
            allow_self_target=False,
            can_skip=False,  # Must act
        )

    def on_nacht_aktion(
        self, spieler: "Spieler", ziel: Optional["Spieler"], kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Seherin sieht die vollständige Rolle eines Spielers.

        Die Seherin erfährt:
        - Den genauen Rollennamen (z.B. "Hexe", "Werwolf", "Hund")
        - Das Team der Rolle (basierend auf sichtbar_als)

        Einige Rollen können sich tarnen (sichtbar_als != tatsächliches Team).

        WICHTIG: Das Ergebnis wird als SNAPSHOT gespeichert.
        Auch wenn sich die Rolle später ändert (z.B. Infektion),
        sieht die Seherin weiterhin das ursprüngliche Ergebnis.
        """
        if ziel is None:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du musst einen Spieler wählen.",
            )

        if not self.validate_ziel(spieler, ziel, kontext):
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Ungültiges Ziel.",
            )

        # Hole die Rolle des Ziels
        from ..registry import RoleRegistry

        ziel_rolle = RoleRegistry.get(ziel.rolle)

        if ziel_rolle:
            sicht = ziel_rolle.sichtbar_als_fuer(self.info.name)
            rollen_name = ziel_rolle.sichtbare_rolle_fuer(self.info.name)
            team = ziel_rolle.info.team
        else:
            # Fallback für unbekannte Rollen
            sicht = SichtTyp.DORF
            rollen_name = ziel.rolle or "Unbekannt"
            team = Team.DORF

        ist_werwolf = sicht == SichtTyp.WERWOLF
        enthuellung_typ = "boese" if ist_werwolf else "gut"

        # Speichere als SNAPSHOT - wichtig für spätere Rollenänderungen
        try:
            from models import SeherinEnthuellung, Raum

            raum = Raum.query.get(spieler.raum_id)
            if raum:
                SeherinEnthuellung.speichere_enthuellung(
                    seherin_id=spieler.id,
                    ziel_id=ziel.id,
                    raum_id=raum.id,
                    enthuellung_typ=enthuellung_typ,
                    rolle=rollen_name,
                    runde=raum.runde,
                )
        except Exception as e:
            # Fehler beim Speichern sollte die Aktion nicht blockieren
            print(f"Warnung: Konnte Seherin-Enthüllung nicht speichern: {e}")

        # Nachricht mit vollständiger Rolleninformation
        if ist_werwolf:
            nachricht = f"{ziel.name} ist ein {rollen_name}! (Werwolf-Team)"
        else:
            nachricht = f"{ziel.name} ist ein {rollen_name}. (Dorf-Team)"

        return AktionsErgebnis(
            erfolg=True,
            nachricht=nachricht,
            ziel_spieler_id=ziel.id,
            effekte={
                "gesehen": ziel.id,
                "rolle": rollen_name,
                "ist_werwolf": ist_werwolf,
                "sicht_typ": sicht.value,
                "team": team.value,
                "snapshot": True,
            },
            private_infos={
                spieler.id: {
                    # Generic format - no hardcoded type needed
                    "nachricht": nachricht,
                    "alert_type": "error" if ist_werwolf else "success",
                }
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """
        Comprehensive 3D appearance for Seherin.

        Features:
        - Mystical third eye on forehead
        - Crystal ball held in hand
        - Pointed mystic hat
        - Purple glowing aura
        - Flowing robes effect
        """
        seherin_features = [
            # Third eye on forehead
            AppearanceFeature(
                feature_type="third_eye",
                geometry="sphere",
                position={"x": 0, "y": 2.05, "z": 0.22},
                scale={"x": 0.08, "y": 0.08, "z": 0.04},
                color_source="custom",
                custom_color="#9933FF",
                emissive=True,
                emissive_intensity=0.8,
                light_source=True,
                light_color="#9933FF",
                light_intensity=0.4,
                light_range=1.5,
                animation="pulse",
                animation_speed=0.5,
                description="Mystical third eye",
            ),
            # Crystal ball
            create_crystal_ball(color="#9966ff"),
            # Pointed mystic hat
            create_pointed_hat(color="#4B0082"),
            # Mystical aura
            create_aura(color="#9966ff", intensity=0.4, pulsing=True),
            # Flowing robe indicator
            AppearanceFeature(
                feature_type="robe",
                geometry="cone",
                position={"x": 0, "y": 0.7, "z": 0},
                scale={"x": 0.4, "y": 1.1, "z": 0.35},
                color_source="custom",
                custom_color="#2E1A47",
                roughness=0.8,
                description="Mystic robes",
            ),
            # Star patterns on robe
            AppearanceFeature(
                feature_type="star_pattern_1",
                geometry="sphere",
                position={"x": 0.15, "y": 0.6, "z": 0.2},
                scale={"x": 0.03, "y": 0.03, "z": 0.01},
                color_source="custom",
                custom_color="#FFD700",
                emissive=True,
                emissive_intensity=0.5,
                description="Star decoration",
            ),
            AppearanceFeature(
                feature_type="star_pattern_2",
                geometry="sphere",
                position={"x": -0.12, "y": 0.75, "z": 0.18},
                scale={"x": 0.025, "y": 0.025, "z": 0.01},
                color_source="custom",
                custom_color="#FFD700",
                emissive=True,
                emissive_intensity=0.5,
                description="Star decoration",
            ),
        ]

        return RollenModell(
            modell_id="seherin",
            anzeige_name="Seherin",
            beschreibung="Eine mystische Seherin mit drittem Auge und Kristallkugel",
            body=BodyModification(
                height_multiplier=0.95,
                skin_texture="smooth",
            ),
            appearance_self_alive=seherin_features,
            appearance_others_alive=seherin_features,
            appearance_dead=create_death_marker(),
            seher_sicht="good",
            animations={
                "idle": AnimationState(
                    state_name="idle",
                    sway_amplitude=0.01,
                    sway_speed=0.5,
                    head_tilt_range=20,
                    look_around=True,
                    blink_rate=2.5,
                    breathing_visible=True,
                ),
                "seeing": AnimationState(
                    state_name="seeing",
                    sway_amplitude=0.0,
                    head_tilt_range=5,
                    look_around=False,
                    blink_rate=0.5,  # Rarely blinks while seeing
                    gesture_chance=0.0,
                ),
            },
            hint_effects=[
                HintEffect3D(
                    effect_id="moonbeam",
                    effect_type="glow",
                    glow_color="#9966FF",
                    glow_intensity=1.0,
                    glow_pulse=True,
                ),
            ],
            sound_on_action="crystal_chime.mp3",
        )
