"""
Wolf im Schafspelz - Erscheint als Dorfbewohner.

Der Wolf im Schafspelz erscheint für die normale
Seherin als Dorfbewohner, nur die Aurenseherin erkennt ihn.
"""

from typing import Optional, List, TYPE_CHECKING
from roles.base import (
    Role,
    RollenInfo,
    AktionsErgebnis,
    SpielKontext,
    RollenModell,
    AppearanceFeature,
    BodyModification,
    AnimationState,
    HintEffect3D,
    create_wolf_ears,
    create_claws,
    create_fangs,
    create_glowing_eyes,
    create_death_marker,
)
from roles.enums import Team, Kategorie, SichtTyp, Erweiterung
from roles.registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler
    from roles.enums import AktionsTyp
    from roles.base import RollenUI


@RoleRegistry.register
class WolfimSchafspelz(Role):
    """
    Wolf im Schafspelz - Getarnter Werwolf.

    Fähigkeiten:
    - Jagt mit den Wölfen
    - Erscheint der Seherin als Dorfbewohner
    - Nur die Aurenseherin erkennt seine böse Aura

    Besonderheiten:
    - Perfekte Tarnung gegen normale Seherin
    - Aurenseherin sieht Böse Aura
    - Gefährlich für das Dorf

    Gewinnbedingung: Werwölfe gewinnen.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=23,
            name="Wolf im Schafspelz",
            team=Team.WERWOLF,
            kategorie=Kategorie.WERWOLF,
            beschreibung=(
                "Du bist der Wolf im Schafspelz. Für die Seherin erscheinst "
                "du als harmloser Dorfbewohner! Nur die Aurenseherin erkennt "
                "dein böses Herz."
            ),
            icon="fa-brands fa-bluesky",
            farbe="#fef3c7",
            prioritaet=50,
            erzaehler_nacht=(
                "Der Wolf im Schafspelz jagt mit dem Rudel. "
                "Er erscheint der Seherin als Dorfbewohner."
            ),
            erweiterung=Erweiterung.COMMUNITY,
            avatar_gradient_from="#fef3c7",
            avatar_gradient_to="#d97706",
            avatar_border_color="#fcd34d",
            badge_emoji="🐑",
        )

    @property
    def aktions_typ(self) -> "AktionsTyp":
        from roles.enums import AktionsTyp
        return AktionsTyp.KEINE

    @property
    def sichtbar_als(self) -> SichtTyp:
        return SichtTyp.DORF  # The trick!

    def sichtbar_als_fuer(self, seher_rolle: str) -> SichtTyp:
        if seher_rolle == "Aurenseherin":
            return SichtTyp.WERWOLF
        return SichtTyp.DORF

    def sichtbare_rolle_fuer(self, seher_rolle: str) -> str:
        if seher_rolle == "Seherin":
            return "Dorfbewohner"
        return self.info.name

    def is_active_on_first_night(self) -> bool:
        return False

    def is_active_on_every_night(self) -> bool:
        return False

    def get_ui_definition(self) -> "RollenUI":
        from roles.base import RollenUI
        return RollenUI(
            title="Wolf im Schafspelz - Passive Rolle",
            instructions="Du jagst mit den Wölfen. Die Seherin sieht dich als Dorfbewohner.",
            buttons=[],
            requires_target=False,
            can_skip=True,
        )

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """
        Comprehensive 3D appearance for Wolf im Schafspelz.

        OTHERS SEE: A fluffy sheep/innocent villager
        SELF SEES: The wolf hiding under sheep wool costume

        Subtle hints: Slightly visible wolf snout, claws peeking out,
        red eyes occasionally visible through wool.
        """
        # What OTHERS see - innocent sheep villager
        sheep_disguise = [
            # Fluffy wool body costume
            AppearanceFeature(
                feature_type="wool_body",
                geometry="sphere",
                position={"x": 0, "y": 1.1, "z": 0},
                scale={"x": 0.55, "y": 0.65, "z": 0.5},
                color_source="custom",
                custom_color="#FFFEF5",  # Cream white wool
                roughness=1.0,
                description="Fluffy wool body",
            ),
            # Wool hood/head covering
            AppearanceFeature(
                feature_type="wool_hood",
                geometry="sphere",
                position={"x": 0, "y": 1.95, "z": 0},
                scale={"x": 0.35, "y": 0.32, "z": 0.32},
                color_source="custom",
                custom_color="#FFFEF5",
                roughness=1.0,
                description="Wool hood disguise",
            ),
            # Sheep ears (floppy, cute)
            AppearanceFeature(
                feature_type="sheep_ear_left",
                geometry="box",
                position={"x": -0.25, "y": 2.0, "z": 0},
                scale={"x": 0.12, "y": 0.08, "z": 0.04},
                rotation={"x": 0, "y": 0, "z": -25},
                color_source="custom",
                custom_color="#FFE4E1",  # Pink sheep ear
                description="Sheep ear left",
            ),
            AppearanceFeature(
                feature_type="sheep_ear_right",
                geometry="box",
                position={"x": 0.25, "y": 2.0, "z": 0},
                scale={"x": 0.12, "y": 0.08, "z": 0.04},
                rotation={"x": 0, "y": 0, "z": 25},
                color_source="custom",
                custom_color="#FFE4E1",
                description="Sheep ear right",
            ),
            # Innocent black eyes (fake)
            AppearanceFeature(
                feature_type="fake_eye_left",
                geometry="sphere",
                position={"x": -0.08, "y": 1.92, "z": 0.28},
                scale={"x": 0.04, "y": 0.04, "z": 0.02},
                color_source="custom",
                custom_color="#1a1a1a",
                description="Fake innocent eye",
            ),
            AppearanceFeature(
                feature_type="fake_eye_right",
                geometry="sphere",
                position={"x": 0.08, "y": 1.92, "z": 0.28},
                scale={"x": 0.04, "y": 0.04, "z": 0.02},
                color_source="custom",
                custom_color="#1a1a1a",
                description="Fake innocent eye",
            ),
            # Little wool puffs
            AppearanceFeature(
                feature_type="wool_puff_1",
                geometry="sphere",
                position={"x": -0.3, "y": 1.0, "z": 0.2},
                scale={"x": 0.12, "y": 0.1, "z": 0.1},
                color_source="custom",
                custom_color="#FFFEF5",
                roughness=1.0,
                description="Wool puff",
            ),
            AppearanceFeature(
                feature_type="wool_puff_2",
                geometry="sphere",
                position={"x": 0.28, "y": 0.9, "z": 0.15},
                scale={"x": 0.1, "y": 0.1, "z": 0.08},
                color_source="custom",
                custom_color="#FFFEF5",
                roughness=1.0,
                description="Wool puff",
            ),
        ]

        # What SELF sees - the wolf beneath
        wolf_true_form = [
            # Wool costume (torn, revealing)
            AppearanceFeature(
                feature_type="torn_wool_body",
                geometry="sphere",
                position={"x": 0, "y": 1.1, "z": 0},
                scale={"x": 0.5, "y": 0.6, "z": 0.45},
                color_source="custom",
                custom_color="#F5F5DC",  # Slightly dirty wool
                roughness=1.0,
                description="Torn wool costume",
            ),
            # Visible wolf snout poking out
            AppearanceFeature(
                feature_type="wolf_snout",
                geometry="box",
                position={"x": 0, "y": 1.75, "z": 0.32},
                scale={"x": 0.08, "y": 0.06, "z": 0.12},
                color_source="custom",
                custom_color="#4a3020",
                description="Wolf snout showing",
            ),
            # Real wolf ears hidden under hood
            *create_wolf_ears(color="#4a3020", scale=0.7),
            # Glowing red eyes visible through costume
            create_glowing_eyes(color="#FF0000", intensity=0.7),
            # Claws peeking out from wool
            AppearanceFeature(
                feature_type="claw_peek_left",
                geometry="cone",
                position={"x": -0.35, "y": 0.6, "z": 0.15},
                scale={"x": 0.02, "y": 0.06, "z": 0.02},
                rotation={"x": 30, "y": 0, "z": 0},
                color_source="custom",
                custom_color="#2a2a2a",
                description="Claw peeking out",
            ),
            AppearanceFeature(
                feature_type="claw_peek_right",
                geometry="cone",
                position={"x": 0.35, "y": 0.6, "z": 0.15},
                scale={"x": 0.02, "y": 0.06, "z": 0.02},
                rotation={"x": 30, "y": 0, "z": 0},
                color_source="custom",
                custom_color="#2a2a2a",
                description="Claw peeking out",
            ),
            # Wolf tail hidden under costume (slight bulge)
            AppearanceFeature(
                feature_type="hidden_tail_bulge",
                geometry="capsule",
                position={"x": 0, "y": 0.8, "z": -0.35},
                scale={"x": 0.12, "y": 0.25, "z": 0.12},
                rotation={"x": -40, "y": 0, "z": 0},
                color_source="custom",
                custom_color="#F0F0E0",
                description="Tail bulge under costume",
            ),
            # Subtle evil glow
            AppearanceFeature(
                feature_type="evil_aura",
                geometry="sphere",
                position={"x": 0, "y": 1.0, "z": 0},
                scale={"x": 0.6, "y": 0.8, "z": 0.5},
                color_source="custom",
                custom_color="#FF0000",
                opacity=0.08,
                emissive=True,
                emissive_intensity=0.15,
                description="Hidden evil aura",
            ),
        ]

        return RollenModell(
            modell_id="wolf_im_schafspelz",
            anzeige_name="Wolf im Schafspelz",
            beschreibung="Ein Wolf versteckt in einem Schafskostüm",
            body=BodyModification(
                height_multiplier=0.98,
                width_multiplier=1.1,  # Bulky costume
                skin_texture="smooth",
            ),
            appearance_self_alive=wolf_true_form,
            appearance_others_alive=sheep_disguise,  # Others see innocent sheep!
            appearance_dead=create_death_marker(),
            seher_sicht="good",  # Appears good to Seherin
            animations={
                "idle": AnimationState(
                    state_name="idle",
                    sway_amplitude=0.015,
                    sway_speed=0.5,
                    head_tilt_range=15,
                    breathing_visible=True,
                ),
            },
            hint_effects=[
                HintEffect3D(
                    effect_id="suspicious_glint",
                    effect_type="glow",
                    glow_color="#FF4444",
                    glow_intensity=0.3,
                    glow_pulse=True,
                ),
            ],
            sound_on_action="sheep_bleat_growl.mp3",
        )
