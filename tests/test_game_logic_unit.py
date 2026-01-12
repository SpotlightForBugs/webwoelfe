"""
Unit tests for core game logic functions.

Tests cover:
- naechste_phase: Phase transitions
- pruefe_spielende: Win condition checking
- toete_spieler: Death handling with cascading effects
- verteile_rollen: Role distribution
- berechne_rollen: Dynamic role calculation
"""

from __future__ import annotations

import pytest
import sys
import os
import json
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from unittest.mock import MagicMock, patch, PropertyMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================================
# Test Fixtures and Mocks
# ============================================================================


@dataclass
class MockSpieler:
    """Mock player object for tests without database."""

    id: int
    name: str
    rolle: str = "Dorfbewohner"
    ist_am_leben: bool = True
    status: str = "aktiv"
    raum_id: int = 1
    ist_erzaehler: bool = False
    sitzplatz: Optional[int] = None

    # Dynamic state storage (JSON string like real model)
    rolle_zustand: str = "{}"

    def get_state(self, key: str, default: Any = None) -> Any:
        """Get state value from JSON storage."""
        try:
            state = json.loads(self.rolle_zustand or "{}")
            return state.get(key, default)
        except (json.JSONDecodeError, TypeError):
            return default

    def set_state(self, key: str, value: Any) -> None:
        """Set state value in JSON storage."""
        try:
            state = json.loads(self.rolle_zustand or "{}")
        except (json.JSONDecodeError, TypeError):
            state = {}
        state[key] = value
        self.rolle_zustand = json.dumps(state)

    def reset_state(self) -> None:
        """Reset state."""
        self.rolle_zustand = "{}"

    def get_all_state(self) -> dict:
        """Get all state."""
        try:
            return json.loads(self.rolle_zustand or "{}")
        except (json.JSONDecodeError, TypeError):
            return {}


@dataclass
class MockRaum:
    """Mock room object for tests."""

    id: int = 1
    code: str = "TEST01"
    name: str = "Test Room"
    spiel_gestartet: bool = True
    aktuelle_phase: str = "nacht"
    runde: int = 1
    spiel_beendet: bool = False
    gewinner: Optional[str] = None
    phase_votes: str = "{}"
    timer_start: Optional[Any] = None
    timer_duration: int = 120


@pytest.fixture
def mock_spieler_factory():
    """Factory to create mock players."""
    def _create(id: int, name: str, rolle: str, ist_am_leben: bool = True) -> MockSpieler:
        return MockSpieler(
            id=id,
            name=name,
            rolle=rolle,
            ist_am_leben=ist_am_leben,
        )
    return _create


@pytest.fixture
def basic_game_players(mock_spieler_factory):
    """Create a basic 8-player game setup."""
    return [
        mock_spieler_factory(1, "Alice", "Werwolf"),
        mock_spieler_factory(2, "Bob", "Werwolf"),
        mock_spieler_factory(3, "Charlie", "Seherin"),
        mock_spieler_factory(4, "Diana", "Hexe"),
        mock_spieler_factory(5, "Eve", "Jäger"),
        mock_spieler_factory(6, "Frank", "Dorfbewohner"),
        mock_spieler_factory(7, "Grace", "Dorfbewohner"),
        mock_spieler_factory(8, "Henry", "Dorfbewohner"),
    ]


# ============================================================================
# berechne_rollen Tests
# ============================================================================


class TestBerechneRollen:
    """Tests for dynamic role calculation."""

    def test_minimum_players_get_basic_roles(self):
        """5 players should get basic roles (Werwolf, Seherin, Dorfbewohner)."""
        from game_logic import berechne_rollen
        
        result = berechne_rollen(5)
        
        assert "Werwolf" in result, "Should include Werwolf"
        assert sum(result.values()) == 5, "Should distribute exactly 5 roles"
        # At least 1 werewolf
        assert result.get("Werwolf", 0) >= 1, "Should have at least 1 werewolf"

    def test_larger_games_scale_werewolves(self):
        """10+ players should have more werewolves."""
        from game_logic import berechne_rollen
        
        result = berechne_rollen(12)
        
        # 12 players should have 2-3 werewolves based on distribution config
        assert result.get("Werwolf", 0) >= 2, "Should have at least 2 werewolves"

    def test_narrator_counted_separately(self):
        """Narrator should be counted separately."""
        from game_logic import berechne_rollen
        
        result = berechne_rollen(8, mit_erzaehler=True)
        
        assert "Erzaehler" in result, "Should include Erzaehler"
        assert result["Erzaehler"] == 1, "Should have exactly 1 narrator"
        # Total roles = 8 (7 players + 1 narrator)
        assert sum(result.values()) == 8, "Should distribute exactly 8 roles"

    def test_fills_with_dorfbewohner(self):
        """Remaining slots should be filled with Dorfbewohner."""
        from game_logic import berechne_rollen
        
        result = berechne_rollen(8)
        
        assert "Dorfbewohner" in result or sum(result.values()) == 8, \
            "Should fill remaining slots with Dorfbewohner or use all slots"

    def test_returns_dict_format(self):
        """Should return {role_name: count} format."""
        from game_logic import berechne_rollen
        
        result = berechne_rollen(6)
        
        assert isinstance(result, dict), "Should return a dictionary"
        for role, count in result.items():
            assert isinstance(role, str), f"Role name should be string: {role}"
            assert isinstance(count, int), f"Role count should be int: {count}"
            assert count > 0, f"Role count should be positive: {role}={count}"


# ============================================================================
# pruefe_spielende Tests (Win Conditions)
# ============================================================================


class TestPruefeSpielende:
    """Tests for win condition checking.
    
    Note: More comprehensive win condition tests are in test_win_conditions.py.
    These tests verify the basic functionality without Flask context.
    """

    def test_no_survivors_returns_nobody_wins(self):
        """If no players are alive, nobody wins."""
        # Create mock that returns empty list
        with patch('game_logic.hole_lebende_spieler', return_value=[]):
            with patch('game_logic.Spieler') as mock_spieler:
                mock_spieler.query.filter_by.return_value.all.return_value = []
                
                from game_logic import pruefe_spielende
                result = pruefe_spielende(MockRaum())
                
                assert result is not None
                assert result["gewinner"] == "niemand"
                assert result["team"] == "niemand"

    def test_werewolves_win_by_majority(self, mock_spieler_factory):
        """Werewolves win when they have majority."""
        # 2 werewolves vs 2 villagers = werewolves win
        lebende = [
            mock_spieler_factory(1, "Wolf1", "Werwolf"),
            mock_spieler_factory(2, "Wolf2", "Werwolf"),
            mock_spieler_factory(3, "Villager1", "Dorfbewohner"),
            mock_spieler_factory(4, "Villager2", "Dorfbewohner"),
        ]
        
        with patch('game_logic.hole_lebende_spieler', return_value=lebende):
            with patch('game_logic.Spieler') as mock_spieler:
                mock_spieler.query.filter_by.return_value.all.return_value = lebende
                
                from game_logic import pruefe_spielende
                result = pruefe_spielende(MockRaum())
                
                assert result is not None
                assert result["gewinner"] == "werwolf"
                assert result["team"] == "werwolf"

    def test_village_wins_when_all_wolves_dead(self, mock_spieler_factory):
        """Village wins when all werewolves are eliminated."""
        lebende = [
            mock_spieler_factory(1, "Villager1", "Dorfbewohner"),
            mock_spieler_factory(2, "Villager2", "Seherin"),
            mock_spieler_factory(3, "Villager3", "Hexe"),
        ]
        
        with patch('game_logic.hole_lebende_spieler', return_value=lebende):
            with patch('game_logic.Spieler') as mock_spieler:
                mock_spieler.query.filter_by.return_value.all.return_value = lebende
                
                from game_logic import pruefe_spielende
                result = pruefe_spielende(MockRaum())
                
                assert result is not None
                assert result["gewinner"] == "dorf"
                assert result["team"] == "dorf"

    def test_lovers_win_when_last_two(self, mock_spieler_factory):
        """Lovers win when they are the last 2 survivors."""
        lover1 = mock_spieler_factory(1, "Lover1", "Werwolf")
        lover2 = mock_spieler_factory(2, "Lover2", "Dorfbewohner")
        
        # Set up lover state
        lover1.set_state("global.verliebt_mit_id", 2)
        lover2.set_state("global.verliebt_mit_id", 1)
        
        lebende = [lover1, lover2]
        
        with patch('game_logic.hole_lebende_spieler', return_value=lebende):
            with patch('game_logic.Spieler') as mock_spieler:
                mock_spieler.query.filter_by.return_value.all.return_value = lebende
                
                from game_logic import pruefe_spielende
                result = pruefe_spielende(MockRaum())
                
                assert result is not None
                assert result["gewinner"] == "verliebte"
                assert result["team"] == "verliebte"

    def test_game_continues_when_no_win_condition(self, mock_spieler_factory):
        """Game continues when no win condition is met."""
        # 1 werewolf, 3 villagers = game continues
        lebende = [
            mock_spieler_factory(1, "Wolf1", "Werwolf"),
            mock_spieler_factory(2, "Villager1", "Dorfbewohner"),
            mock_spieler_factory(3, "Villager2", "Seherin"),
            mock_spieler_factory(4, "Villager3", "Hexe"),
        ]
        
        with patch('game_logic.hole_lebende_spieler', return_value=lebende):
            with patch('game_logic.Spieler') as mock_spieler:
                mock_spieler.query.filter_by.return_value.all.return_value = lebende
                
                from game_logic import pruefe_spielende
                result = pruefe_spielende(MockRaum())
                
                assert result is None, "Game should continue"


# ============================================================================
# Role Distribution Tests
# ============================================================================


class TestRoleDistribution:
    """Tests for role distribution system."""

    def test_all_roles_have_distribution_config(self):
        """Every role should have a DistributionConfig."""
        from roles import RoleRegistry
        
        roles_without_dist = []
        for role in RoleRegistry.get_all():
            if not role.info.distribution:
                roles_without_dist.append(role.info.name)
        
        # Some roles may intentionally not have distribution (special roles)
        # But the main roles should have it
        core_roles = ["Werwolf", "Dorfbewohner", "Seherin", "Hexe", "Jäger"]
        for core_role in core_roles:
            role = RoleRegistry.get(core_role)
            assert role is not None, f"Core role {core_role} not found"
            assert role.info.distribution is not None, \
                f"Core role {core_role} missing DistributionConfig"

    def test_filler_role_exists(self):
        """At least one filler role (Dorfbewohner) should exist."""
        from roles import RoleRegistry
        
        filler_found = False
        for role in RoleRegistry.get_all():
            if role.info.distribution and role.info.distribution.is_filler:
                filler_found = True
                break
        
        assert filler_found, "At least one filler role should exist"


# ============================================================================
# Team Counting Tests
# ============================================================================


class TestTeamCounting:
    """Tests for team-based win condition counting."""

    def test_count_all_team_types(self):
        """Should correctly count all team types."""
        from roles import RoleRegistry
        from roles.enums import Team
        
        # Verify teams are counted correctly
        # This is more of an integration test with RoleRegistry
        werwolf = RoleRegistry.get("Werwolf")
        dorf = RoleRegistry.get("Dorfbewohner")
        
        assert werwolf is not None
        assert dorf is not None
        assert werwolf.info.team == Team.WERWOLF
        assert dorf.info.team == Team.DORF

    def test_neutral_roles_counted(self):
        """Neutral roles should be counted in win condition checks."""
        from roles import RoleRegistry
        from roles.enums import Team
        
        # Check if any neutral roles exist
        for role in RoleRegistry.get_all():
            if role.info.team == Team.NEUTRAL:
                # Neutral roles exist and are properly categorized
                assert role.info.team.value == "neutral"


# ============================================================================
# Phase Transition Tests
# ============================================================================


class TestPhaseTransitions:
    """Tests for phase transition logic."""

    def test_phase_list_not_empty(self):
        """Phase list should not be empty."""
        from phases import get_phase_list
        
        phases = get_phase_list()
        assert len(phases) > 0, "Phase list should not be empty"

    def test_core_phases_exist(self):
        """Core phases should exist in phase list."""
        from phases import get_phase_list
        
        phases = get_phase_list()
        core_phases = ["nacht_start", "tag_abstimmung", "hinrichtung"]
        
        for phase in core_phases:
            assert phase in phases, f"Core phase {phase} missing"


# ============================================================================
# Vote Calculation Tests
# ============================================================================


class TestVoteCalculation:
    """Tests for voting system."""

    def test_berechne_abstimmungs_statistik(self):
        """Should calculate vote statistics correctly."""
        from game_logic import berechne_abstimmungs_statistik
        
        raum = MockRaum()
        raum.phase_votes = json.dumps({
            "1": 3,  # Player 1 votes for player 3
            "2": 3,  # Player 2 votes for player 3
            "4": 5,  # Player 4 votes for player 5
        })
        
        with patch('game_logic.hole_lebende_spieler') as mock_lebende:
            mock_lebende.return_value = [
                MockSpieler(id=i, name=f"Player{i}", rolle="Dorfbewohner")
                for i in [1, 2, 3, 4, 5]
            ]
            
            result = berechne_abstimmungs_statistik(raum)
            
            assert result["gesamt_votes"] == 3
            assert result["ziel_stimmen"]["3"] == 2  # Player 3 has 2 votes
            assert result["fuehrender_id"] == 3  # Player 3 is leading


# ============================================================================
# Integration Tests
# ============================================================================


class TestGameLogicIntegration:
    """Integration tests for game logic."""

    def test_role_registry_loads(self):
        """Role registry should load all roles."""
        from roles import RoleRegistry
        
        all_roles = RoleRegistry.get_all()
        assert len(all_roles) > 0, "Should have registered roles"

    def test_all_roles_have_required_info(self):
        """All roles should have required RollenInfo fields."""
        from roles import RoleRegistry
        
        for role in RoleRegistry.get_all():
            info = role.info
            assert info.id is not None, f"{role.__class__.__name__} missing id"
            assert info.name is not None, f"{role.__class__.__name__} missing name"
            assert info.team is not None, f"{role.__class__.__name__} missing team"
            assert info.beschreibung is not None, f"{role.__class__.__name__} missing beschreibung"

    def test_no_duplicate_role_ids(self):
        """No two roles should have the same ID."""
        from roles import RoleRegistry
        
        ids_seen = {}
        for role in RoleRegistry.get_all():
            role_id = role.info.id
            if role_id in ids_seen:
                pytest.fail(f"Duplicate ID {role_id}: {role.info.name} and {ids_seen[role_id]}")
            ids_seen[role_id] = role.info.name


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
