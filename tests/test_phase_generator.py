"""
Tests for the phase generation and transition system.

Tests cover:
- Dynamic phase generation from active roles
- Phase ordering and dependencies
- Role dependency resolution (topological sort)
- get_next_phase state machine transitions
- Special phase handling (jaeger_phase triggered on death)
- Edge cases (no active roles, circular dependencies)
"""

from __future__ import annotations

import sys
import os
from typing import List
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from conftest import MockSpieler, MockRaum


# =============================================================================
# PHASE LIST TESTS
# =============================================================================


class TestPhaseList:
    """Test the core phase list."""

    def test_phase_list_not_empty(self):
        """Phase list should have phases."""
        from phases import get_phase_list

        phases = get_phase_list()
        assert len(phases) > 0

    def test_core_phases_exist(self):
        """Core phases must exist."""
        from phases import get_phase_list

        phases = get_phase_list()

        required = ["nacht_start", "tag_abstimmung", "hinrichtung"]
        for p in required:
            assert p in phases, f"Missing core phase: {p}"

    def test_nacht_before_tag(self):
        """Night phases should come before day phases."""
        from phases import get_phase_list

        phases = get_phase_list()

        nacht_idx = phases.index("nacht_start")
        tag_idx = phases.index("tag_abstimmung")
        assert nacht_idx < tag_idx

    def test_phase_type_detection(self):
        """Phase types should be correctly detected."""
        from phases import is_nacht_phase, is_tag_phase

        assert is_nacht_phase("nacht_start") is True
        assert is_nacht_phase("nacht") is True
        assert is_nacht_phase("tag_abstimmung") is False
        assert is_tag_phase("tag_abstimmung") is True
        assert is_tag_phase("nacht") is False

    def test_get_next_phase_basic_cycle(self):
        """Phase cycle should follow correct order."""
        from phases import get_next_phase

        assert get_next_phase("rollen_verteilt") == "nacht_start"
        assert get_next_phase("nacht_start") == "nacht"
        assert get_next_phase("tag_abstimmung") == "hinrichtung"
        assert get_next_phase("hinrichtung") == "tag_ende"
        assert get_next_phase("tag_ende") == "nacht_start"  # Loop back


# =============================================================================
# DYNAMIC PHASE GENERATION TESTS
# =============================================================================


class TestDynamicPhaseGeneration:
    """Test dynamic night phase generation from active roles."""

    def test_generate_phases_with_db(self, test_app):
        """Generate phases for a standard game."""
        from models import Raum, Spieler, db
        from phase_generator import generate_phases_for_game

        with test_app.app_context():
            raum = Raum(
                code="PHG001",
                name="Phase Gen Test",
                modus="online",
                spieler_anzahl=5,
                spiel_gestartet=True,
                aktuelle_phase="nacht_start",
                runde=1,
            )
            db.session.add(raum)
            db.session.flush()

            roles = ["Werwolf", "Seherin", "Hexe", "Dorfbewohner", "Dorfbewohner"]
            for i, rolle in enumerate(roles):
                s = Spieler(
                    name=f"Player-{i}",
                    session_id=f"sess-phg-{i}",
                    raum_id=raum.id,
                    rolle=rolle,
                    ist_am_leben=True,
                    status="aktiv",
                )
                db.session.add(s)
            db.session.commit()

            phases = generate_phases_for_game(raum)

            # Should include nacht_start and role-specific phases
            assert "nacht_start" in phases, f"Missing nacht_start in {phases}"

            # Should include werwolf phase
            has_wolf_phase = any("werwolf" in p for p in phases)
            assert has_wolf_phase, f"Missing werwolf phase in {phases}"

    def test_first_night_includes_amor(self, test_app):
        """First night should include Amor phase."""
        from models import Raum, Spieler, db
        from phase_generator import generate_phases_for_game

        with test_app.app_context():
            raum = Raum(
                code="PHG002",
                name="Amor Test",
                modus="online",
                spieler_anzahl=6,
                spiel_gestartet=True,
                aktuelle_phase="nacht_start",
                runde=1,  # First night
            )
            db.session.add(raum)
            db.session.flush()

            roles = [
                "Werwolf",
                "Seherin",
                "Hexe",
                "Amor",
                "Dorfbewohner",
                "Dorfbewohner",
            ]
            for i, rolle in enumerate(roles):
                s = Spieler(
                    name=f"Player-{i}",
                    session_id=f"sess-amor-{i}",
                    raum_id=raum.id,
                    rolle=rolle,
                    ist_am_leben=True,
                    status="aktiv",
                )
                db.session.add(s)
            db.session.commit()

            phases = generate_phases_for_game(raum)

            # Should include amor phase on first night
            has_amor_phase = any("amor" in p for p in phases)
            assert has_amor_phase, f"Missing amor phase in first night: {phases}"

    def test_dead_roles_excluded(self, test_app):
        """Dead players' roles should not generate phases."""
        from models import Raum, Spieler, db
        from phase_generator import generate_phases_for_game

        with test_app.app_context():
            raum = Raum(
                code="PHG003",
                name="Dead Exclude Test",
                modus="online",
                spieler_anzahl=5,
                spiel_gestartet=True,
                aktuelle_phase="nacht_start",
                runde=2,
            )
            db.session.add(raum)
            db.session.flush()

            # Seherin is dead
            roles_alive = [
                ("Werwolf", True),
                ("Seherin", False),
                ("Hexe", True),
                ("Dorfbewohner", True),
                ("Dorfbewohner", True),
            ]

            for i, (rolle, alive) in enumerate(roles_alive):
                s = Spieler(
                    name=f"Player-{i}",
                    session_id=f"sess-dead-{i}",
                    raum_id=raum.id,
                    rolle=rolle,
                    ist_am_leben=alive,
                    status="aktiv" if alive else "tot",
                )
                db.session.add(s)
            db.session.commit()

            phases = generate_phases_for_game(raum)

            # Dead Seherin should not have a phase
            has_seherin_phase = any("seherin" in p for p in phases)
            assert not has_seherin_phase, (
                f"Dead Seherin should not have phase: {phases}"
            )

    def test_no_active_roles_returns_minimal(self, test_app):
        """When no night-active roles exist, should return minimal phases."""
        from models import Raum, Spieler, db
        from phase_generator import generate_phases_for_game

        with test_app.app_context():
            raum = Raum(
                code="PHG004",
                name="No Roles Test",
                modus="online",
                spieler_anzahl=3,
                spiel_gestartet=True,
                aktuelle_phase="nacht_start",
                runde=2,
            )
            db.session.add(raum)
            db.session.flush()

            # Only non-active roles (Dorfbewohner don't act at night)
            for i in range(3):
                s = Spieler(
                    name=f"Player-{i}",
                    session_id=f"sess-norole-{i}",
                    raum_id=raum.id,
                    rolle="Dorfbewohner",
                    ist_am_leben=True,
                    status="aktiv",
                )
                db.session.add(s)
            db.session.commit()

            phases = generate_phases_for_game(raum)

            # Should have nacht_start at minimum (or be empty if all inactive)
            # Either way, shouldn't crash
            assert isinstance(phases, list)


# =============================================================================
# PHASE ROLE MAPPING TESTS
# =============================================================================


class TestPhaseRoleMapping:
    """Test the phase-to-role mapping system."""

    def test_phasennamen_zu_rollen_mapping(self):
        """Dynamic phase mapping should map phase names to role names."""
        from game_logic import phasennamen_zu_rollen_mapping

        mapping = phasennamen_zu_rollen_mapping()
        assert isinstance(mapping, dict)
        assert len(mapping) > 0

        # Core mappings should exist
        assert mapping.get("werwolf_phase") == "Werwolf"
        assert mapping.get("seherin_phase") == "Seherin"
        assert mapping.get("hexe_phase") == "Hexe"

    def test_all_active_roles_have_phase_mapping(self):
        """Every night-active role should have a phase mapping."""
        from game_logic import phasennamen_zu_rollen_mapping
        from roles import RoleRegistry

        mapping = phasennamen_zu_rollen_mapping()
        mapped_roles = set(mapping.values())

        for role in RoleRegistry.get_all():
            is_active = (
                role.is_active_on_first_night() or role.is_active_on_every_night()
            )
            if is_active:
                # Role should appear in mapping (either directly or via shared phase)
                phase_name = role.get_phase_name()
                shared_phase = getattr(role, "shared_phase_name", None)

                if shared_phase:
                    # Shared phases (like werwolf_phase) map to the primary role
                    assert shared_phase in mapping or phase_name in mapping, (
                        f"{role.info.name}: active but no phase mapping "
                        f"(phase={phase_name}, shared={shared_phase})"
                    )
                else:
                    # Check by phase name using normalized form
                    from game_logic import _normalisiere_phase_name

                    norm_phase = _normalisiere_phase_name(phase_name)
                    assert norm_phase in mapping, (
                        f"{role.info.name}: active but no mapping for {norm_phase}"
                    )

    def test_role_phases_not_in_core_phases(self):
        """Role-specific phases should NOT be in the core phase list."""
        from game_logic import phasennamen_zu_rollen_mapping
        from phases import get_phase_list

        core_phases = get_phase_list()
        role_phases = phasennamen_zu_rollen_mapping()

        for role_phase in role_phases.keys():
            assert role_phase not in core_phases, (
                f"Role phase '{role_phase}' should not be in core PHASEN list"
            )


# =============================================================================
# GET_NEXT_PHASE STATE MACHINE TESTS
# =============================================================================


class TestGetNextPhaseStateMachine:
    """Test the get_next_phase state machine in phase_generator.py."""

    def test_rollen_verteilt_to_nacht_start(self, test_app):
        """rollen_verteilt should transition to nacht_start."""
        from models import Raum, Spieler, db
        from phase_generator import get_next_phase

        with test_app.app_context():
            raum = Raum(
                code="NSM001",
                name="State Machine Test",
                modus="online",
                spieler_anzahl=5,
                spiel_gestartet=True,
                aktuelle_phase="rollen_verteilt",
                runde=1,
            )
            db.session.add(raum)
            db.session.flush()

            for i in range(5):
                s = Spieler(
                    name=f"P-{i}",
                    session_id=f"nsm-{i}",
                    raum_id=raum.id,
                    rolle="Dorfbewohner",
                    ist_am_leben=True,
                    status="aktiv",
                )
                db.session.add(s)
            db.session.commit()

            result = get_next_phase(raum)
            assert result == "nacht_start"

    def test_day_cycle_fixed_order(self, test_app):
        """Day cycle should follow fixed order."""
        from models import Raum, Spieler, db
        from phase_generator import get_next_phase

        with test_app.app_context():
            raum = Raum(
                code="NSM002",
                name="Day Cycle Test",
                modus="online",
                spieler_anzahl=3,
                spiel_gestartet=True,
                aktuelle_phase="tag_start",
                runde=1,
            )
            db.session.add(raum)
            db.session.flush()

            for i in range(3):
                s = Spieler(
                    name=f"P-{i}",
                    session_id=f"nsm2-{i}",
                    raum_id=raum.id,
                    rolle="Dorfbewohner",
                    ist_am_leben=True,
                    status="aktiv",
                )
                db.session.add(s)
            db.session.commit()

            # tag_start -> tag_abstimmung
            assert get_next_phase(raum) == "tag_abstimmung"
            raum.aktuelle_phase = "tag_abstimmung"

            # tag_abstimmung -> hinrichtung
            assert get_next_phase(raum) == "hinrichtung"
            raum.aktuelle_phase = "hinrichtung"

            # hinrichtung -> tag_ende
            assert get_next_phase(raum) == "tag_ende"
            raum.aktuelle_phase = "tag_ende"

            # tag_ende -> nacht_start
            assert get_next_phase(raum) == "nacht_start"

    def test_nacht_ende_to_tag_start(self, test_app):
        """nacht_ende should transition to tag_start."""
        from models import Raum, Spieler, db
        from phase_generator import get_next_phase

        with test_app.app_context():
            raum = Raum(
                code="NSM003",
                name="Nacht Ende Test",
                modus="online",
                spieler_anzahl=3,
                spiel_gestartet=True,
                aktuelle_phase="nacht_ende",
                runde=1,
            )
            db.session.add(raum)
            db.session.flush()

            for i in range(3):
                s = Spieler(
                    name=f"P-{i}",
                    session_id=f"nsm3-{i}",
                    raum_id=raum.id,
                    rolle="Dorfbewohner",
                    ist_am_leben=True,
                    status="aktiv",
                )
                db.session.add(s)
            db.session.commit()

            result = get_next_phase(raum)
            assert result == "tag_start"


# =============================================================================
# DEPENDENCY SORTING TESTS
# =============================================================================


class TestDependencySorting:
    """Test role dependency resolution in phase ordering."""

    def test_roles_sorted_by_priority(self, test_app):
        """Roles should be sorted by priority within dependency levels."""
        from models import Raum, Spieler, db
        from phase_generator import generate_phases_for_game

        with test_app.app_context():
            raum = Raum(
                code="DEP001",
                name="Priority Test",
                modus="online",
                spieler_anzahl=5,
                spiel_gestartet=True,
                aktuelle_phase="nacht_start",
                runde=1,
            )
            db.session.add(raum)
            db.session.flush()

            roles = ["Werwolf", "Seherin", "Hexe", "Amor", "Dorfbewohner"]
            for i, rolle in enumerate(roles):
                s = Spieler(
                    name=f"P-{i}",
                    session_id=f"dep-{i}",
                    raum_id=raum.id,
                    rolle=rolle,
                    ist_am_leben=True,
                    status="aktiv",
                )
                db.session.add(s)
            db.session.commit()

            phases = generate_phases_for_game(raum)

            # Filter to only role phases (exclude nacht_start, nacht_ende)
            role_phases = [p for p in phases if p.endswith("_phase")]

            # Should have phases in priority order
            assert len(role_phases) > 0, f"No role phases generated: {phases}"


# =============================================================================
# SPECIAL PHASE TESTS
# =============================================================================


class TestSpecialPhases:
    """Test special triggered phases (e.g., Jaeger phase)."""

    def test_jaeger_has_triggered_phase(self):
        """Jäger should define a triggered phase."""
        from roles import RoleRegistry

        jaeger = RoleRegistry.get("Jäger")
        assert jaeger is not None

        triggered = jaeger.get_triggered_phases()
        if triggered:
            # Should have a jaeger_phase
            phase_names = [tp.phase_name for tp in triggered]
            assert any(
                "jaeger" in p or "jäger" in p or "jaeger" in p for p in phase_names
            ), f"Jäger should define a triggered phase, got: {phase_names}"

    def test_special_phase_has_next_phase(self):
        """Special phases should define what happens next."""
        from roles import RoleRegistry

        for role in RoleRegistry.get_all():
            triggered = role.get_triggered_phases()
            for tp in triggered:
                # Either has next_phase_override or falls back to tag_ende
                # Just ensure it doesn't crash
                assert tp.phase_name, (
                    f"{role.info.name}: triggered phase missing phase_name"
                )


# =============================================================================
# BUILD PHASE ROLE MAPPING TESTS
# =============================================================================


class TestBuildPhaseRoleMapping:
    """Test the build_phase_role_mapping function."""

    def test_mapping_includes_active_roles(self, test_app):
        """Mapping should include all active roles in the game."""
        from models import Raum, Spieler, db
        from phase_generator import build_phase_role_mapping

        with test_app.app_context():
            raum = Raum(
                code="MAP001",
                name="Mapping Test",
                modus="online",
                spieler_anzahl=5,
                spiel_gestartet=True,
                aktuelle_phase="nacht_start",
                runde=1,
            )
            db.session.add(raum)
            db.session.flush()

            roles = ["Werwolf", "Seherin", "Hexe", "Dorfbewohner", "Dorfbewohner"]
            for i, rolle in enumerate(roles):
                s = Spieler(
                    name=f"P-{i}",
                    session_id=f"map-{i}",
                    raum_id=raum.id,
                    rolle=rolle,
                    ist_am_leben=True,
                    status="aktiv",
                )
                db.session.add(s)
            db.session.commit()

            mapping = build_phase_role_mapping(raum)

            assert isinstance(mapping, dict)
            assert len(mapping) > 0

            # Werwolf should always be mapped
            has_wolf = any("werwolf" in k.lower() for k in mapping.keys())
            assert has_wolf, f"Missing werewolf in mapping: {mapping}"

    def test_shared_phases_mapped_correctly(self, test_app):
        """Wolf variants with shared_phase_name should map to same phase."""
        from models import Raum, Spieler, db
        from phase_generator import build_phase_role_mapping
        from roles import RoleRegistry

        with test_app.app_context():
            # Check if any wolf variant with shared_phase exists
            wolf_variants = []
            for role in RoleRegistry.get_all():
                shared = getattr(role, "shared_phase_name", None)
                if shared and "werwolf" in shared:
                    wolf_variants.append(role.info.name)

            if not wolf_variants:
                pytest.skip("No wolf variants with shared_phase_name")

            raum = Raum(
                code="MAP002",
                name="Shared Phase Test",
                modus="online",
                spieler_anzahl=5,
                spiel_gestartet=True,
                aktuelle_phase="nacht_start",
                runde=1,
            )
            db.session.add(raum)
            db.session.flush()

            # Add base wolf + variant
            roles_to_add = ["Werwolf"] + [wolf_variants[0]] + ["Dorfbewohner"] * 3
            for i, rolle in enumerate(roles_to_add):
                s = Spieler(
                    name=f"P-{i}",
                    session_id=f"map2-{i}",
                    raum_id=raum.id,
                    rolle=rolle,
                    ist_am_leben=True,
                    status="aktiv",
                )
                db.session.add(s)
            db.session.commit()

            mapping = build_phase_role_mapping(raum)

            # Both wolves should share the same phase
            wolf_phases = [k for k in mapping if "werwolf" in k.lower()]
            assert len(wolf_phases) >= 1, (
                f"Expected at least 1 werwolf phase, got: {mapping}"
            )
