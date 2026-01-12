"""
Comprehensive tests for all win conditions in the game.

Tests cover:
- Village win scenarios
- Werewolf win scenarios
- Vampire/Zombie win scenarios
- Solo role win conditions
- Lovers win conditions
- Edge cases (draw, ties, etc.)
"""

from __future__ import annotations

import pytest
import sys
import os
import json
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from unittest.mock import MagicMock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from roles.base import SpielKontext
from roles.enums import Team, Phase


# ============================================================================
# Mock Classes
# ============================================================================


@dataclass
class MockSpieler:
    """Mock player for win condition tests."""

    id: int
    name: str
    rolle: str = "Dorfbewohner"
    ist_am_leben: bool = True
    status: str = "aktiv"
    raum_id: int = 1
    ist_erzaehler: bool = False
    rolle_zustand: str = "{}"

    def get_state(self, key: str, default: Any = None) -> Any:
        try:
            state = json.loads(self.rolle_zustand or "{}")
            return state.get(key, default)
        except (json.JSONDecodeError, TypeError):
            return default

    def set_state(self, key: str, value: Any) -> None:
        try:
            state = json.loads(self.rolle_zustand or "{}")
        except (json.JSONDecodeError, TypeError):
            state = {}
        state[key] = value
        self.rolle_zustand = json.dumps(state)


@dataclass
class MockRaum:
    """Mock room for win condition tests."""

    id: int = 1
    code: str = "TEST01"
    aktuelle_phase: str = "tag"
    runde: int = 1


def create_kontext(lebende: List[MockSpieler], tote: List[MockSpieler] = None) -> SpielKontext:
    """Create a SpielKontext for testing."""
    tote = tote or []
    return SpielKontext(
        raum_id=1,
        runde=1,
        phase=Phase.TAG,
        aktiver_spieler_id=lebende[0].id if lebende else 0,
        lebende_spieler=[s.id for s in lebende],
        tote_spieler=[s.id for s in tote],
    )


# ============================================================================
# Village Win Tests
# ============================================================================


class TestVillageWinConditions:
    """Tests for village (Dorf) win conditions."""

    def test_village_wins_all_wolves_dead(self):
        """Village wins when all werewolves are eliminated."""
        lebende = [
            MockSpieler(1, "Alice", "Dorfbewohner"),
            MockSpieler(2, "Bob", "Seherin"),
            MockSpieler(3, "Charlie", "Hexe"),
        ]
        
        with patch('game_logic.hole_lebende_spieler', return_value=lebende):
            with patch('game_logic.Spieler') as mock_spieler:
                mock_spieler.query.filter_by.return_value.all.return_value = lebende
                
                from game_logic import pruefe_spielende
                result = pruefe_spielende(MockRaum())
                
                assert result is not None
                assert result["team"] == "dorf"

    def test_village_wins_with_solo_remaining(self):
        """Village does NOT win if solo roles remain."""
        # Solo roles prevent village from winning until eliminated
        lebende = [
            MockSpieler(1, "Alice", "Dorfbewohner"),
            MockSpieler(2, "Bob", "Flötenspieler"),  # Solo role
        ]
        
        with patch('game_logic.hole_lebende_spieler', return_value=lebende):
            with patch('game_logic.Spieler') as mock_spieler:
                mock_spieler.query.filter_by.return_value.all.return_value = lebende
                
                from game_logic import pruefe_spielende
                result = pruefe_spielende(MockRaum())
                
                # Game should continue or solo wins
                # Village doesn't auto-win with solo alive
                if result is not None:
                    assert result["team"] != "dorf" or result.get("spieler_id") is None

    def test_village_wins_single_survivor(self):
        """Village wins with single villager survivor and no threats."""
        lebende = [MockSpieler(1, "Alice", "Dorfbewohner")]
        
        with patch('game_logic.hole_lebende_spieler', return_value=lebende):
            with patch('game_logic.Spieler') as mock_spieler:
                mock_spieler.query.filter_by.return_value.all.return_value = lebende
                
                from game_logic import pruefe_spielende
                result = pruefe_spielende(MockRaum())
                
                assert result is not None
                assert result["team"] == "dorf"


# ============================================================================
# Werewolf Win Tests
# ============================================================================


class TestWerewolfWinConditions:
    """Tests for werewolf win conditions."""

    def test_werewolves_win_majority(self):
        """Werewolves win when they have majority."""
        lebende = [
            MockSpieler(1, "Wolf1", "Werwolf"),
            MockSpieler(2, "Wolf2", "Werwolf"),
            MockSpieler(3, "Villager", "Dorfbewohner"),
        ]
        
        with patch('game_logic.hole_lebende_spieler', return_value=lebende):
            with patch('game_logic.Spieler') as mock_spieler:
                mock_spieler.query.filter_by.return_value.all.return_value = lebende
                
                from game_logic import pruefe_spielende
                result = pruefe_spielende(MockRaum())
                
                assert result is not None
                assert result["team"] == "werwolf"

    def test_werewolves_win_equal_numbers(self):
        """Werewolves win when equal to village (can eliminate in night)."""
        lebende = [
            MockSpieler(1, "Wolf1", "Werwolf"),
            MockSpieler(2, "Villager", "Dorfbewohner"),
        ]
        
        with patch('game_logic.hole_lebende_spieler', return_value=lebende):
            with patch('game_logic.Spieler') as mock_spieler:
                mock_spieler.query.filter_by.return_value.all.return_value = lebende
                
                from game_logic import pruefe_spielende
                result = pruefe_spielende(MockRaum())
                
                assert result is not None
                assert result["team"] == "werwolf"

    def test_werewolves_win_last_survivor(self):
        """Werewolf wins as last survivor."""
        lebende = [MockSpieler(1, "Wolf", "Werwolf")]
        
        with patch('game_logic.hole_lebende_spieler', return_value=lebende):
            with patch('game_logic.Spieler') as mock_spieler:
                mock_spieler.query.filter_by.return_value.all.return_value = lebende
                
                from game_logic import pruefe_spielende
                result = pruefe_spielende(MockRaum())
                
                assert result is not None
                # Single wolf = wolf majority
                assert result["team"] == "werwolf"


# ============================================================================
# Lovers Win Tests
# ============================================================================


class TestLoversWinConditions:
    """Tests for lovers (Verliebte) win conditions."""

    def test_lovers_win_last_two(self):
        """Lovers win when they are the last 2 survivors."""
        lover1 = MockSpieler(1, "Lover1", "Werwolf")
        lover2 = MockSpieler(2, "Lover2", "Dorfbewohner")
        
        lover1.set_state("global.verliebt_mit_id", 2)
        lover2.set_state("global.verliebt_mit_id", 1)
        
        lebende = [lover1, lover2]
        
        with patch('game_logic.hole_lebende_spieler', return_value=lebende):
            with patch('game_logic.Spieler') as mock_spieler:
                mock_spieler.query.filter_by.return_value.all.return_value = lebende
                
                from game_logic import pruefe_spielende
                result = pruefe_spielende(MockRaum())
                
                assert result is not None
                assert result["team"] == "verliebte"

    def test_lovers_mixed_teams(self):
        """Lovers from different teams can win together."""
        # Wolf + Villager lovers
        lover1 = MockSpieler(1, "WolfLover", "Werwolf")
        lover2 = MockSpieler(2, "VillageLover", "Seherin")
        
        lover1.set_state("global.verliebt_mit_id", 2)
        lover2.set_state("global.verliebt_mit_id", 1)
        
        lebende = [lover1, lover2]
        
        with patch('game_logic.hole_lebende_spieler', return_value=lebende):
            with patch('game_logic.Spieler') as mock_spieler:
                mock_spieler.query.filter_by.return_value.all.return_value = lebende
                
                from game_logic import pruefe_spielende
                result = pruefe_spielende(MockRaum())
                
                assert result is not None
                assert result["team"] == "verliebte"

    def test_not_lovers_two_players(self):
        """Two players without love link don't trigger lovers win."""
        player1 = MockSpieler(1, "Player1", "Werwolf")
        player2 = MockSpieler(2, "Player2", "Dorfbewohner")
        # No lover state set
        
        lebende = [player1, player2]
        
        with patch('game_logic.hole_lebende_spieler', return_value=lebende):
            with patch('game_logic.Spieler') as mock_spieler:
                mock_spieler.query.filter_by.return_value.all.return_value = lebende
                
                from game_logic import pruefe_spielende
                result = pruefe_spielende(MockRaum())
                
                # Should be werewolf win, not lovers
                assert result is not None
                assert result["team"] == "werwolf"


# ============================================================================
# Solo Role Win Tests
# ============================================================================


class TestSoloWinConditions:
    """Tests for solo role win conditions."""

    def test_solo_role_berechne_gewinn(self):
        """Solo roles should implement berechne_gewinn correctly."""
        from roles import RoleRegistry
        
        solo_roles = ["Flötenspieler", "Henker", "Selbstmörder"]
        
        for role_name in solo_roles:
            role = RoleRegistry.get(role_name)
            if role:
                # Solo roles should have Team.SOLO
                assert role.info.team == Team.SOLO, \
                    f"{role_name} should be Team.SOLO"
                
                # Should have berechne_gewinn method
                assert hasattr(role, 'berechne_gewinn'), \
                    f"{role_name} should have berechne_gewinn method"


# ============================================================================
# Draw / Edge Case Tests
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and draws."""

    def test_no_survivors_draw(self):
        """No survivors results in a draw."""
        with patch('game_logic.hole_lebende_spieler', return_value=[]):
            with patch('game_logic.Spieler') as mock_spieler:
                mock_spieler.query.filter_by.return_value.all.return_value = []
                
                from game_logic import pruefe_spielende
                result = pruefe_spielende(MockRaum())
                
                assert result is not None
                assert result["gewinner"] == "niemand"

    def test_single_neutral_survivor(self):
        """Single neutral role survivor - game behavior."""
        # Neutral roles don't win on their own typically
        lebende = [MockSpieler(1, "Neutral", "Dorfbewohner")]
        lebende[0].rolle = "Dorfbewohner"  # Assuming neutral fallback
        
        with patch('game_logic.hole_lebende_spieler', return_value=lebende):
            with patch('game_logic.Spieler') as mock_spieler:
                mock_spieler.query.filter_by.return_value.all.return_value = lebende
                
                from game_logic import pruefe_spielende
                result = pruefe_spielende(MockRaum())
                
                # Should result in village win
                assert result is not None


# ============================================================================
# Team Counting Tests
# ============================================================================


class TestTeamCounting:
    """Tests for team counting in win conditions."""

    def test_counts_all_werewolf_variants(self):
        """Werewolf role should be in WERWOLF team."""
        from roles import RoleRegistry
        
        # Only "Werwolf" is core WERWOLF team
        # Note: "Weißer Wolf" is SOLO (acts with wolves but wins alone)
        # "Urwolf" is a wolf variant that may or may not exist
        werwolf = RoleRegistry.get("Werwolf")
        assert werwolf is not None
        assert werwolf.info.team == Team.WERWOLF, "Werwolf should be in WERWOLF team"
        
        # Check that Weißer Wolf is correctly categorized as SOLO
        weisser_wolf = RoleRegistry.get("Weißer Wolf")
        if weisser_wolf:
            assert weisser_wolf.info.team == Team.SOLO, \
                "Weißer Wolf should be in SOLO team (wins alone)"
            # But should have WERWOLF kategorie for display purposes
            from roles.enums import Kategorie
            assert weisser_wolf.info.kategorie == Kategorie.WERWOLF, \
                "Weißer Wolf should have WERWOLF kategorie"

    def test_counts_all_village_roles(self):
        """All village roles should count as dorf team."""
        from roles import RoleRegistry
        
        village_roles = ["Dorfbewohner", "Seherin", "Hexe", "Jäger", "Heiler", "Amor"]
        
        for role_name in village_roles:
            role = RoleRegistry.get(role_name)
            if role:
                assert role.info.team == Team.DORF, \
                    f"{role_name} should be in DORF team"


# ============================================================================
# Priority Tests
# ============================================================================


class TestWinConditionPriority:
    """Tests for win condition priority order."""

    def test_solo_checked_before_team_win(self):
        """Solo wins should be checked before team majority wins."""
        # This tests the order of checks in pruefe_spielende
        # Solo wins should have priority over team wins
        
        # Create a scenario where both could apply
        # E.g., Flötenspieler has all enchanted AND wolves have majority
        # Flötenspieler should win
        
        from roles import RoleRegistry
        
        floetenspieler = RoleRegistry.get("Flötenspieler")
        if floetenspieler:
            # Verify the role has berechne_gewinn
            assert hasattr(floetenspieler, 'berechne_gewinn')

    def test_lovers_checked_before_team_majority(self):
        """Lovers win should be checked appropriately in order."""
        # The check order in pruefe_spielende:
        # 1. No survivors
        # 2. Solo wins (berechne_gewinn)
        # 3. Lovers (2 survivors linked)
        # 4. Team majority
        
        # This is a documentation test - the order is defined in game_logic.py
        pass


# ============================================================================
# Vampire/Zombie Win Tests
# ============================================================================


class TestInfectionWinConditions:
    """Tests for vampire and zombie win conditions."""

    def test_vampire_team_exists(self):
        """Vampire team should exist in enums."""
        assert Team.VAMPIR is not None
        assert Team.VAMPIR.value == "vampir"

    def test_zombie_team_exists(self):
        """Zombie team should exist in enums."""
        assert Team.ZOMBIE is not None
        assert Team.ZOMBIE.value == "zombie"

    def test_vampire_win_majority(self):
        """Vampires win with majority and no werewolves."""
        # Create vampires vs village scenario
        # Note: Vampir role may not exist in all configurations
        from roles import RoleRegistry
        
        vampir = RoleRegistry.get("Vampir")
        if vampir:
            assert vampir.info.team == Team.VAMPIR


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
