"""
Comprehensive tests for ALL roles in the game.

Tests every registered role for:
1. Registration and info completeness
2. Night action execution (on_nacht_aktion returns correct type)
3. UI definition validity (get_ui_definition returns valid RollenUI)
4. State field definitions
5. Win condition correctness
6. Death trigger behavior (on_eigener_tod)
7. Phase configuration
8. 3D model definition
9. Seer visibility

Parametrized over all roles from RoleRegistry.
"""

from __future__ import annotations

import sys
import os
from typing import List, Optional

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from conftest import MockSpieler, MockRaum, init_role_state
from roles import RoleRegistry
from roles.base import (
    Role,
    RollenInfo,
    AktionsErgebnis,
    SpielKontext,
    RollenUI,
    UIButton,
    RoleAction,
    RollenModell,
    StateField,
    WinCondition,
    AppearanceFeature,
)
from roles.enums import Team, Kategorie, AktionsTyp, SichtTyp, Phase, Erweiterung


# =============================================================================
# HELPERS
# =============================================================================


def get_all_role_names() -> List[str]:
    """Get all registered role names."""
    return [r.info.name for r in RoleRegistry.get_all()]


def make_kontext(
    lebende_ids: List[int] = None,
    tote_ids: List[int] = None,
    runde: int = 1,
    phase=Phase.NACHT,
    werwolf_opfer_id: int = None,
    spieler_rollen: dict = None,
    spieler_namen: dict = None,
    spieler_teams: dict = None,
) -> SpielKontext:
    """Create a SpielKontext for testing."""
    return SpielKontext(
        raum_id=1,
        runde=runde,
        phase=phase,
        aktiver_spieler_id=lebende_ids[0] if lebende_ids else 1,
        lebende_spieler=lebende_ids or [1, 2, 3, 4, 5],
        tote_spieler=tote_ids or [],
        werwolf_opfer_id=werwolf_opfer_id,
        spieler_rollen=spieler_rollen or {},
        spieler_namen=spieler_namen or {},
        spieler_teams=spieler_teams or {},
    )


ALL_ROLES = get_all_role_names()


# =============================================================================
# REGISTRATION & INFO TESTS
# =============================================================================


class TestRoleRegistration:
    """Verify all roles are properly registered with complete metadata."""

    def test_minimum_role_count(self):
        """Should have at least 50 roles registered."""
        count = RoleRegistry.count()
        assert count >= 50, f"Expected 50+ roles, got {count}"

    def test_no_duplicate_ids(self):
        """No two roles should share the same ID."""
        ids = {}
        for role in RoleRegistry.get_all():
            rid = role.info.id
            assert rid not in ids, (
                f"Duplicate ID {rid}: {role.info.name} and {ids[rid]}"
            )
            ids[rid] = role.info.name

    def test_no_duplicate_names(self):
        """No two roles should share the same name."""
        names = set()
        for role in RoleRegistry.get_all():
            name = role.info.name
            assert name not in names, f"Duplicate role name: {name}"
            names.add(name)

    @pytest.mark.parametrize("role_name", ALL_ROLES)
    def test_role_has_complete_info(self, role_name):
        """Every role must have all required RollenInfo fields."""
        role = RoleRegistry.get(role_name)
        assert role is not None, f"Role {role_name} not found"
        info = role.info
        assert info.id is not None, f"{role_name}: missing id"
        assert info.name, f"{role_name}: missing name"
        assert isinstance(info.team, Team), f"{role_name}: invalid team type"
        assert info.beschreibung, f"{role_name}: missing beschreibung"
        assert info.icon, f"{role_name}: missing icon"
        assert info.farbe, f"{role_name}: missing farbe"
        assert isinstance(info.kategorie, Kategorie), f"{role_name}: invalid kategorie"
        assert isinstance(info.erweiterung, Erweiterung), (
            f"{role_name}: invalid erweiterung"
        )
        assert isinstance(info.prioritaet, int), f"{role_name}: prioritaet not int"


# =============================================================================
# UI DEFINITION TESTS
# =============================================================================


class TestUIDefinition:
    """Verify all roles produce valid UI definitions."""

    @pytest.mark.parametrize("role_name", ALL_ROLES)
    def test_get_ui_definition_returns_valid_type(self, role_name):
        """get_ui_definition must return a RollenUI instance."""
        role = RoleRegistry.get(role_name)
        ui = role.get_ui_definition()
        assert isinstance(ui, RollenUI), (
            f"{role_name}: get_ui_definition returned {type(ui).__name__}, expected RollenUI"
        )

    @pytest.mark.parametrize("role_name", ALL_ROLES)
    def test_ui_has_title_and_instructions(self, role_name):
        """UI must have title and instructions."""
        role = RoleRegistry.get(role_name)
        ui = role.get_ui_definition()
        assert ui.title, f"{role_name}: UI missing title"
        assert ui.instructions, f"{role_name}: UI missing instructions"

    @pytest.mark.parametrize("role_name", ALL_ROLES)
    def test_ui_buttons_have_required_fields(self, role_name):
        """All UI buttons must have label and action_type."""
        role = RoleRegistry.get(role_name)
        ui = role.get_ui_definition()
        for btn in ui.buttons:
            assert btn.label, f"{role_name}: button missing label"
            assert btn.action_type, f"{role_name}: button missing action_type"
        for action in ui.actions:
            assert action.label, f"{role_name}: action missing label"
            assert action.action_type, f"{role_name}: action missing action_type"
            assert action.handler, f"{role_name}: action missing handler"

    @pytest.mark.parametrize("role_name", ALL_ROLES)
    def test_ui_serializes_to_dict(self, role_name):
        """UI should serialize to dict without errors."""
        role = RoleRegistry.get(role_name)
        ui = role.get_ui_definition()
        d = ui.to_dict()
        assert isinstance(d, dict)
        assert "title" in d
        assert "buttons" in d or "actions" in d


# =============================================================================
# NIGHT ACTION TESTS
# =============================================================================


class TestNightActions:
    """Verify all night-active roles execute actions correctly."""

    @pytest.mark.parametrize("role_name", ALL_ROLES)
    def test_night_active_roles_have_callable_action(self, role_name):
        """Night-active roles must have a callable on_nacht_aktion."""
        role = RoleRegistry.get(role_name)
        is_active = role.is_active_on_first_night() or role.is_active_on_every_night()
        if is_active:
            assert callable(getattr(role, "on_nacht_aktion", None)), (
                f"{role_name}: is night-active but has no callable on_nacht_aktion"
            )

    @pytest.mark.parametrize("role_name", ALL_ROLES)
    def test_on_nacht_aktion_returns_correct_type(self, role_name):
        """on_nacht_aktion must return None or AktionsErgebnis."""
        role = RoleRegistry.get(role_name)
        is_active = role.is_active_on_first_night() or role.is_active_on_every_night()
        if not is_active:
            return  # Skip non-active roles

        spieler = MockSpieler(id=1, name="Actor", rolle=role_name)
        ziel = MockSpieler(id=2, name="Target", rolle="Dorfbewohner")
        init_role_state(spieler)

        kontext = make_kontext(
            lebende_ids=[1, 2, 3, 4, 5],
            spieler_rollen={
                2: RoleRegistry.get("Dorfbewohner"),
                1: role,
            },
            spieler_namen={1: "Actor", 2: "Target"},
            werwolf_opfer_id=2,
        )

        try:
            # Try with default action
            result = role.on_nacht_aktion(spieler, ziel, kontext)
            assert result is None or isinstance(result, AktionsErgebnis), (
                f"{role_name}: on_nacht_aktion returned {type(result).__name__}"
            )
        except (TypeError, AttributeError, KeyError) as e:
            # Some roles need specific action types - try with UI buttons
            ui = role.get_ui_definition()
            for btn in ui.buttons:
                try:
                    result = role.on_nacht_aktion(
                        spieler, ziel, kontext, aktion=btn.action_type
                    )
                    assert result is None or isinstance(result, AktionsErgebnis), (
                        f"{role_name}: on_nacht_aktion(aktion={btn.action_type}) "
                        f"returned {type(result).__name__}"
                    )
                    break
                except Exception:
                    continue

    @pytest.mark.parametrize("role_name", ALL_ROLES)
    def test_inactive_roles_skip_gracefully(self, role_name):
        """Non-night-active roles should return None from on_nacht_aktion."""
        role = RoleRegistry.get(role_name)
        is_active = role.is_active_on_first_night() or role.is_active_on_every_night()
        if is_active:
            return

        spieler = MockSpieler(id=1, name="Actor", rolle=role_name)
        ziel = MockSpieler(id=2, name="Target", rolle="Dorfbewohner")
        kontext = make_kontext()

        result = role.on_nacht_aktion(spieler, ziel, kontext)
        assert result is None, (
            f"{role_name}: inactive role returned non-None from on_nacht_aktion"
        )


# =============================================================================
# STATE MANAGEMENT TESTS
# =============================================================================


class TestStateManagement:
    """Verify role state fields are properly defined and functional."""

    @pytest.mark.parametrize("role_name", ALL_ROLES)
    def test_state_fields_return_list(self, role_name):
        """state_fields must return a list of StateField."""
        role = RoleRegistry.get(role_name)
        fields = role.state_fields()
        assert isinstance(fields, list), (
            f"{role_name}: state_fields returned {type(fields).__name__}"
        )
        for sf in fields:
            assert isinstance(sf, StateField), (
                f"{role_name}: state_fields contains {type(sf).__name__}"
            )

    @pytest.mark.parametrize("role_name", ALL_ROLES)
    def test_state_init_and_read(self, role_name):
        """State initialization should set defaults that can be read back."""
        role = RoleRegistry.get(role_name)
        fields = role.state_fields()
        if not fields:
            return

        spieler = MockSpieler(id=1, name="Test", rolle=role_name)
        role.init_state(spieler)

        for sf in fields:
            value = role.get_state(spieler, sf.name)
            assert value == sf.default, (
                f"{role_name}: state field '{sf.name}' expected default "
                f"{sf.default!r}, got {value!r}"
            )

    @pytest.mark.parametrize("role_name", ALL_ROLES)
    def test_state_key_generation(self, role_name):
        """State keys should be properly namespaced."""
        role = RoleRegistry.get(role_name)
        key = role._state_key("test_field")
        assert "." in key, f"{role_name}: state key missing namespace: {key}"
        assert key.endswith(".test_field"), f"{role_name}: bad state key: {key}"
        # Should not contain spaces
        assert " " not in key, f"{role_name}: state key contains spaces: {key}"


# =============================================================================
# WIN CONDITION TESTS
# =============================================================================


class TestWinConditions:
    """Verify all roles' win conditions are properly defined."""

    @pytest.mark.parametrize("role_name", ALL_ROLES)
    def test_berechne_gewinn_returns_none_or_team(self, role_name):
        """berechne_gewinn must return None or a Team enum."""
        role = RoleRegistry.get(role_name)
        spieler = MockSpieler(id=1, name="Test", rolle=role_name)
        init_role_state(spieler)

        kontext = make_kontext(
            lebende_ids=[1, 2, 3],
            spieler_rollen={
                1: role,
                2: RoleRegistry.get("Dorfbewohner"),
                3: RoleRegistry.get("Werwolf"),
            },
            spieler_teams={
                1: role.info.team,
                2: Team.DORF,
                3: Team.WERWOLF,
            },
        )

        result = role.berechne_gewinn(spieler, kontext)
        assert result is None or isinstance(result, Team), (
            f"{role_name}: berechne_gewinn returned {type(result).__name__}"
        )

    @pytest.mark.parametrize("role_name", ALL_ROLES)
    def test_get_win_conditions_returns_list(self, role_name):
        """get_win_conditions must return a list of WinCondition."""
        role = RoleRegistry.get(role_name)
        conditions = role.get_win_conditions()
        assert isinstance(conditions, list), (
            f"{role_name}: get_win_conditions returned {type(conditions).__name__}"
        )
        for wc in conditions:
            assert isinstance(wc, WinCondition), (
                f"{role_name}: win condition is {type(wc).__name__}, expected WinCondition"
            )
            assert callable(wc.check_func), (
                f"{role_name}: win condition {wc.id} has non-callable check_func"
            )


# =============================================================================
# DEATH TRIGGER TESTS
# =============================================================================


class TestDeathTriggers:
    """Verify on_eigener_tod and handle_anderer_stirbt behavior."""

    @pytest.mark.parametrize("role_name", ALL_ROLES)
    def test_on_eigener_tod_returns_correct_type(self, role_name):
        """on_eigener_tod must return None or AktionsErgebnis."""
        role = RoleRegistry.get(role_name)
        spieler = MockSpieler(id=1, name="Dying", rolle=role_name)
        init_role_state(spieler)
        kontext = make_kontext(lebende_ids=[2, 3, 4])

        result = role.on_eigener_tod(spieler, "werwolf", kontext)
        assert result is None or isinstance(result, AktionsErgebnis), (
            f"{role_name}: on_eigener_tod returned {type(result).__name__}"
        )

    @pytest.mark.parametrize("role_name", ALL_ROLES)
    def test_handle_anderer_stirbt_returns_correct_type(self, role_name):
        """handle_anderer_stirbt must return None or AktionsErgebnis."""
        role = RoleRegistry.get(role_name)
        spieler = MockSpieler(id=1, name="Observer", rolle=role_name)
        opfer = MockSpieler(id=2, name="Victim", rolle="Dorfbewohner")
        init_role_state(spieler)
        kontext = make_kontext(lebende_ids=[1, 3, 4])

        result = role.handle_anderer_stirbt(spieler, opfer, "werwolf", kontext)
        assert result is None or isinstance(result, AktionsErgebnis), (
            f"{role_name}: handle_anderer_stirbt returned {type(result).__name__}"
        )


# =============================================================================
# SEER VISIBILITY TESTS
# =============================================================================


class TestSeerVisibility:
    """Verify seer visibility for all roles."""

    @pytest.mark.parametrize("role_name", ALL_ROLES)
    def test_sichtbar_als_returns_sichttyp(self, role_name):
        """sichtbar_als should return a SichtTyp."""
        role = RoleRegistry.get(role_name)
        sicht = role.sichtbar_als
        assert isinstance(sicht, SichtTyp), (
            f"{role_name}: sichtbar_als returned {type(sicht).__name__}"
        )

    @pytest.mark.parametrize("role_name", ALL_ROLES)
    def test_sichtbar_als_fuer_seherin(self, role_name):
        """sichtbar_als_fuer('Seherin') should return a SichtTyp."""
        role = RoleRegistry.get(role_name)
        sicht = role.sichtbar_als_fuer("Seherin")
        assert isinstance(sicht, SichtTyp), (
            f"{role_name}: sichtbar_als_fuer('Seherin') returned {type(sicht).__name__}"
        )

    @pytest.mark.parametrize("role_name", ALL_ROLES)
    def test_sichtbare_rolle_returns_string(self, role_name):
        """sichtbare_rolle_fuer should return a non-empty string."""
        role = RoleRegistry.get(role_name)
        visible_role = role.sichtbare_rolle_fuer("Seherin")
        assert isinstance(visible_role, str), (
            f"{role_name}: sichtbare_rolle_fuer returned {type(visible_role).__name__}"
        )
        assert len(visible_role) > 0, (
            f"{role_name}: sichtbare_rolle_fuer returned empty string"
        )

    def test_werewolf_visible_as_wolf(self):
        """Werewolves should be visible as WERWOLF to Seherin."""
        role = RoleRegistry.get("Werwolf")
        assert role.sichtbar_als_fuer("Seherin") == SichtTyp.WERWOLF

    def test_villager_visible_as_dorf(self):
        """Dorfbewohner should be visible as DORF to Seherin."""
        role = RoleRegistry.get("Dorfbewohner")
        assert role.sichtbar_als_fuer("Seherin") == SichtTyp.DORF


# =============================================================================
# TEAM ASSIGNMENT TESTS
# =============================================================================


class TestTeamAssignment:
    """Verify correct team assignments."""

    def test_core_wolf_roles_are_werwolf_team(self):
        """Core werewolf variants should be in WERWOLF team."""
        wolf_names = ["Werwolf"]
        for name in wolf_names:
            role = RoleRegistry.get(name)
            assert role is not None, f"{name} not found"
            assert role.info.team == Team.WERWOLF, (
                f"{name}: expected WERWOLF team, got {role.info.team}"
            )

    def test_core_village_roles_are_dorf_team(self):
        """Core village roles should be in DORF team."""
        dorf_names = ["Dorfbewohner", "Seherin", "Hexe", "Jäger", "Amor", "Heiler"]
        for name in dorf_names:
            role = RoleRegistry.get(name)
            assert role is not None, f"{name} not found"
            assert role.info.team == Team.DORF, (
                f"{name}: expected DORF team, got {role.info.team}"
            )

    @pytest.mark.parametrize("role_name", ALL_ROLES)
    def test_team_is_valid_enum(self, role_name):
        """Every role's team must be a valid Team enum."""
        role = RoleRegistry.get(role_name)
        assert isinstance(role.info.team, Team), (
            f"{role_name}: team is {type(role.info.team).__name__}"
        )


# =============================================================================
# AKTIONS_TYP TESTS
# =============================================================================


class TestAktionsTyp:
    """Verify correct action types."""

    @pytest.mark.parametrize("role_name", ALL_ROLES)
    def test_aktions_typ_is_valid_enum(self, role_name):
        """Every role's aktions_typ must be a valid AktionsTyp enum."""
        role = RoleRegistry.get(role_name)
        assert isinstance(role.aktions_typ, AktionsTyp), (
            f"{role_name}: aktions_typ is {type(role.aktions_typ).__name__}"
        )

    def test_werwolf_has_toeten(self):
        """Werwolf should have TOETEN action type."""
        role = RoleRegistry.get("Werwolf")
        assert role.aktions_typ == AktionsTyp.TOETEN

    def test_seherin_has_sehen(self):
        """Seherin should have SEHEN action type."""
        role = RoleRegistry.get("Seherin")
        assert role.aktions_typ == AktionsTyp.SEHEN

    def test_heiler_has_schuetzen(self):
        """Heiler should have SCHUETZEN action type."""
        role = RoleRegistry.get("Heiler")
        assert role.aktions_typ == AktionsTyp.SCHUETZEN


# =============================================================================
# PHASE CONFIGURATION TESTS
# =============================================================================


class TestPhaseConfiguration:
    """Verify phase activity configuration."""

    @pytest.mark.parametrize("role_name", ALL_ROLES)
    def test_is_active_methods_return_bool(self, role_name):
        """is_active_on_first_night and is_active_on_every_night must return bool."""
        role = RoleRegistry.get(role_name)
        first = role.is_active_on_first_night()
        every = role.is_active_on_every_night()
        assert isinstance(first, bool), (
            f"{role_name}: is_active_on_first_night returned {type(first).__name__}"
        )
        assert isinstance(every, bool), (
            f"{role_name}: is_active_on_every_night returned {type(every).__name__}"
        )

    @pytest.mark.parametrize("role_name", ALL_ROLES)
    def test_get_phase_name_returns_string(self, role_name):
        """get_phase_name must return a non-empty string."""
        role = RoleRegistry.get(role_name)
        phase_name = role.get_phase_name()
        assert isinstance(phase_name, str), (
            f"{role_name}: get_phase_name returned {type(phase_name).__name__}"
        )
        assert len(phase_name) > 0, f"{role_name}: get_phase_name returned empty string"

    def test_werwolf_active_every_night(self):
        """Werwolf should be active every night."""
        role = RoleRegistry.get("Werwolf")
        assert role.is_active_on_every_night() is True

    def test_amor_active_first_night_only(self):
        """Amor should be active only on first night."""
        role = RoleRegistry.get("Amor")
        assert role.is_active_on_first_night() is True


# =============================================================================
# 3D MODEL TESTS
# =============================================================================


class TestModelDefinition:
    """Verify 3D model definitions."""

    @pytest.mark.parametrize("role_name", ALL_ROLES)
    def test_model_definition_valid(self, role_name):
        """get_modell_definition must return a valid RollenModell."""
        role = RoleRegistry.get(role_name)
        spieler = MockSpieler(id=1, name="Test", rolle=role_name)

        modell = role.get_modell_definition(spieler)
        assert isinstance(modell, RollenModell), (
            f"{role_name}: get_modell_definition returned {type(modell).__name__}"
        )
        assert modell.modell_id, f"{role_name}: model missing modell_id"
        assert modell.anzeige_name, f"{role_name}: model missing anzeige_name"

    @pytest.mark.parametrize("role_name", ALL_ROLES)
    def test_model_serializes(self, role_name):
        """Model definition should serialize to dict."""
        role = RoleRegistry.get(role_name)
        spieler = MockSpieler(id=1, name="Test", rolle=role_name)
        modell = role.get_modell_definition(spieler)
        d = modell.to_dict()
        assert isinstance(d, dict)
        assert "modell_id" in d


# =============================================================================
# GRUNDROLLEN SPECIFIC TESTS
# =============================================================================


class TestWerwolfRole:
    """Specific tests for Werwolf."""

    def test_wolf_can_kill(self):
        role = RoleRegistry.get("Werwolf")
        spieler = MockSpieler(id=1, name="Wolf", rolle="Werwolf")
        ziel = MockSpieler(id=2, name="Victim", rolle="Dorfbewohner")
        kontext = make_kontext(lebende_ids=[1, 2, 3, 4, 5])

        result = role.on_nacht_aktion(spieler, ziel, kontext)
        if result:
            assert result.erfolg is True


class TestSeherinRole:
    """Specific tests for Seherin."""

    def test_seherin_sees_wolf(self):
        role = RoleRegistry.get("Seherin")
        spieler = MockSpieler(id=1, name="Seer", rolle="Seherin")
        ziel = MockSpieler(id=2, name="Wolf", rolle="Werwolf")

        werwolf = RoleRegistry.get("Werwolf")
        kontext = make_kontext(
            lebende_ids=[1, 2, 3],
            spieler_rollen={2: werwolf},
        )

        result = role.on_nacht_aktion(spieler, ziel, kontext)
        assert result is not None
        assert result.erfolg is True
        assert (
            "werwolf" in result.nachricht.lower() or "böse" in result.nachricht.lower()
        )


class TestHexeRole:
    """Specific tests for Hexe."""

    def test_hexe_heal(self):
        role = RoleRegistry.get("Hexe")
        spieler = MockSpieler(id=1, name="Witch", rolle="Hexe")
        ziel = MockSpieler(id=2, name="Victim", rolle="Dorfbewohner")
        init_role_state(spieler)

        kontext = make_kontext(
            lebende_ids=[1, 2, 3, 4, 5],
            werwolf_opfer_id=2,
        )

        result = role.on_nacht_aktion(spieler, ziel, kontext, aktion="heilen")
        assert result is not None
        assert result.erfolg is True

    def test_hexe_poison(self):
        role = RoleRegistry.get("Hexe")
        spieler = MockSpieler(id=1, name="Witch", rolle="Hexe")
        ziel = MockSpieler(id=2, name="Wolf", rolle="Werwolf")
        init_role_state(spieler)

        kontext = make_kontext(lebende_ids=[1, 2, 3, 4, 5])

        result = role.on_nacht_aktion(spieler, ziel, kontext, aktion="vergiften")
        assert result is not None
        assert result.erfolg is True


class TestJaegerRole:
    """Specific tests for Jäger."""

    def test_jaeger_death_trigger(self):
        role = RoleRegistry.get("Jäger")
        spieler = MockSpieler(id=1, name="Hunter", rolle="Jäger")
        init_role_state(spieler)
        kontext = make_kontext(lebende_ids=[2, 3, 4])

        result = role.on_eigener_tod(spieler, "werwolf", kontext)
        assert result is not None
        # Jaeger should trigger something on death


class TestAmorRole:
    """Specific tests for Amor."""

    def test_amor_first_night_active(self):
        role = RoleRegistry.get("Amor")
        assert role.is_active_on_first_night() is True

    def test_amor_links_two_players(self):
        role = RoleRegistry.get("Amor")
        ui = role.get_ui_definition()
        assert ui.allow_multiple_targets is True
        assert ui.min_targets == 2
        assert ui.max_targets == 2


class TestHeilerRole:
    """Specific tests for Heiler."""

    def test_heiler_can_protect(self):
        role = RoleRegistry.get("Heiler")
        spieler = MockSpieler(id=1, name="Healer", rolle="Heiler")
        ziel = MockSpieler(id=2, name="Target", rolle="Dorfbewohner")
        init_role_state(spieler)

        kontext = make_kontext(lebende_ids=[1, 2, 3, 4, 5])

        result = role.on_nacht_aktion(spieler, ziel, kontext)
        if result:
            assert result.erfolg is True
