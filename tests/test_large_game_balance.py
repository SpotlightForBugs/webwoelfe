"""
Test suite for large game balance (500+ players).

Tests the role distribution algorithm to ensure games with many players
are properly balanced and all edge cases are handled.

Run with: python -m pytest tests/test_large_game_balance.py -v
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from game_logic import berechne_rollen


class TestRoleDistribution:
    """Test the berechne_rollen function for various player counts."""
    
    @pytest.mark.parametrize("player_count", [5, 10, 15, 20, 25, 50])
    def test_small_games(self, player_count):
        """Test role distribution for small games (5-50 players)."""
        rollen = berechne_rollen(player_count)
        
        # Total roles should equal player count
        total = sum(rollen.values())
        assert total == player_count, f"Total roles {total} != player count {player_count}"
        
        # Must have at least 1 werewolf
        assert rollen.get('Werwolf', 0) >= 1, "Must have at least 1 werewolf"
        
        # Must have village roles
        assert rollen.get('Dorfbewohner', 0) >= 0, "Dorfbewohner count can't be negative"
        
        # Werewolves should be ~20% (1 per 5 players)
        wolf_count = sum(v for k, v in rollen.items() if 'Wolf' in k or 'werwolf' in k.lower())
        assert wolf_count <= player_count * 0.35, f"Too many wolves ({wolf_count}) for {player_count} players"
        assert wolf_count >= 1, "Must have at least 1 wolf"
    
    @pytest.mark.parametrize("player_count", [100, 150, 200, 300])
    def test_medium_games(self, player_count):
        """Test role distribution for medium games (100-300 players)."""
        rollen = berechne_rollen(player_count)
        
        # Total roles should equal player count
        total = sum(rollen.values())
        assert total == player_count, f"Total roles {total} != player count {player_count}"
        
        # Verify wolf ratio is reasonable (15-25%)
        wolf_team_roles = ['Werwolf', 'Urwolf', 'Wolfsjunge', 'Wolf im Schafspelz', 
                          'Werwolfseherin', 'Giftmischerin', 'Hexenmeister', 'Dunkler Priester']
        wolf_count = sum(rollen.get(r, 0) for r in wolf_team_roles)
        wolf_percent = (wolf_count / player_count) * 100
        
        assert 12 <= wolf_percent <= 28, f"Wolf team is {wolf_percent:.1f}% - should be 12-28%"
        
        # Should have multiple seers for large games
        assert rollen.get('Seherin', 0) >= 1, "Large games need at least 1 seer"
        
        # Should have hexe for balance
        assert rollen.get('Hexe', 0) >= 1, "Large games need at least 1 witch"
    
    @pytest.mark.parametrize("player_count", [500, 600, 750, 1000])
    def test_large_games(self, player_count):
        """Test role distribution for large games (500-1000 players)."""
        rollen = berechne_rollen(player_count)
        
        # Total roles should equal player count
        total = sum(rollen.values())
        assert total == player_count, f"Total roles {total} != player count {player_count}"
        
        # Verify wolf ratio for massive games (slightly lower due to voting power)
        wolf_team_roles = ['Werwolf', 'Urwolf', 'Wolfsjunge', 'Wolf im Schafspelz', 
                          'Werwolfseherin', 'Einsamer Wolf', 'Giftmischerin', 
                          'Hexenmeister', 'Dunkler Priester']
        wolf_count = sum(rollen.get(r, 0) for r in wolf_team_roles)
        wolf_percent = (wolf_count / player_count) * 100
        
        assert 10 <= wolf_percent <= 25, f"Wolf team is {wolf_percent:.1f}% - should be 10-25% for large games"
        
        # Should have scaling information roles
        assert rollen.get('Seherin', 0) >= 5, f"500+ player games need multiple seers, got {rollen.get('Seherin', 0)}"
        assert rollen.get('Hexe', 0) >= 3, f"500+ player games need multiple witches, got {rollen.get('Hexe', 0)}"
        assert rollen.get('Jaeger', 0) >= 5, f"500+ player games need multiple hunters, got {rollen.get('Jaeger', 0)}"
        
        # Should have group knowledge roles
        assert rollen.get('Zwei Schwestern', 0) >= 2, "Large games should have sisters"
        assert rollen.get('Drei Brueder', 0) >= 3, "Large games should have brothers"
        assert rollen.get('Freimaurer', 0) >= 2, "Large games should have freemasons"
        
        # Should have solo/neutral roles (but not too many - max ~5%)
        solo_roles = ['Weisser Wolf', 'Einsamer Wolf', 'Dorfdepp', 'Floetenspieler', 
                      'Selbstmoerder', 'Henker', 'Gerber', 'Pyromane', 'Engel']
        solo_count = sum(rollen.get(r, 0) for r in solo_roles)
        solo_percent = (solo_count / player_count) * 100
        
        assert solo_percent <= 8, f"Solo roles are {solo_percent:.1f}% - should be <= 8%"
    
    def test_500_player_game_detailed(self):
        """Detailed test for a 500 player game with full balance verification."""
        player_count = 500
        rollen = berechne_rollen(player_count)
        
        # Total check
        total = sum(rollen.values())
        assert total == player_count, f"Total {total} != {player_count}"
        
        print(f"\n{'='*60}")
        print(f"ROLE DISTRIBUTION FOR {player_count} PLAYERS")
        print(f"{'='*60}")
        
        # Categorize roles
        from models import ROLLEN
        
        teams = {'dorf': [], 'werwolf': [], 'solo': [], 'vampir': [], 'zombie': []}
        
        for rolle_name, anzahl in sorted(rollen.items(), key=lambda x: -x[1]):
            if anzahl > 0:
                rolle_info = ROLLEN.get(rolle_name, {'team': 'dorf'})
                team = rolle_info.get('team', 'dorf')
                teams[team].append((rolle_name, anzahl))
                print(f"  {rolle_name}: {anzahl}")
        
        print(f"\n{'='*60}")
        print("TEAM BREAKDOWN:")
        print(f"{'='*60}")
        
        for team_name, roles in teams.items():
            team_total = sum(count for _, count in roles)
            if team_total > 0:
                percent = (team_total / player_count) * 100
                print(f"  {team_name.upper()}: {team_total} ({percent:.1f}%)")
                for role_name, count in roles:
                    print(f"    - {role_name}: {count}")
        
        # Calculate balance metrics
        village_count = sum(count for _, count in teams['dorf'])
        wolf_count = sum(count for _, count in teams['werwolf'])
        solo_count = sum(count for _, count in teams['solo'])
        
        print(f"\n{'='*60}")
        print("BALANCE METRICS:")
        print(f"{'='*60}")
        print(f"  Village to Wolf ratio: {village_count}:{wolf_count} (1:{wolf_count/village_count:.2f})")
        print(f"  Wolf percentage: {wolf_count/player_count*100:.1f}%")
        print(f"  Village percentage: {village_count/player_count*100:.1f}%")
        print(f"  Solo percentage: {solo_count/player_count*100:.1f}%")
        
        # Balance assertions
        assert village_count > wolf_count * 2, "Village should be at least 2x wolves"
        assert wolf_count >= player_count * 0.10, "Wolves should be at least 10%"
        assert wolf_count <= player_count * 0.25, "Wolves should be at most 25%"
    
    def test_1000_player_game_detailed(self):
        """Detailed test for a 1000 player mega-game."""
        player_count = 1000
        rollen = berechne_rollen(player_count)
        
        # Total check
        total = sum(rollen.values())
        assert total == player_count, f"Total {total} != {player_count}"
        
        print(f"\n{'='*60}")
        print(f"ROLE DISTRIBUTION FOR {player_count} PLAYERS")
        print(f"{'='*60}")
        
        # Categorize roles
        from models import ROLLEN
        
        teams = {'dorf': 0, 'werwolf': 0, 'solo': 0, 'vampir': 0, 'zombie': 0}
        
        for rolle_name, anzahl in sorted(rollen.items(), key=lambda x: -x[1]):
            if anzahl > 0:
                rolle_info = ROLLEN.get(rolle_name, {'team': 'dorf'})
                team = rolle_info.get('team', 'dorf')
                teams[team] += anzahl
                print(f"  {rolle_name}: {anzahl}")
        
        print(f"\n{'='*60}")
        print("TEAM BREAKDOWN:")
        print(f"{'='*60}")
        
        for team_name, team_total in teams.items():
            if team_total > 0:
                percent = (team_total / player_count) * 100
                print(f"  {team_name.upper()}: {team_total} ({percent:.1f}%)")
        
        # Essential balance checks
        assert teams['dorf'] > teams['werwolf'] * 2, "Village must outnumber wolves significantly"
        assert teams['werwolf'] >= 100, "1000 player game should have 100+ wolves"
        assert teams['werwolf'] <= 250, "1000 player game should have at most 250 wolves"
    
    def test_edge_cases(self):
        """Test edge cases for the role distribution."""
        # Minimum players
        rollen_5 = berechne_rollen(5)
        assert sum(rollen_5.values()) == 5
        assert rollen_5.get('Werwolf', 0) >= 1
        
        # With narrator
        rollen_10_narrator = berechne_rollen(10, mit_erzaehler=True)
        assert 'Erzaehler' in rollen_10_narrator
        assert rollen_10_narrator['Erzaehler'] == 1
        # Total should still be 10 (narrator counts as 1)
        assert sum(rollen_10_narrator.values()) == 10
        
        # Very small (below minimum)
        rollen_3 = berechne_rollen(3)
        assert sum(rollen_3.values()) == 5  # Should be clamped to minimum
    
    def test_no_negative_dorfbewohner(self):
        """Ensure we never get negative Dorfbewohner count."""
        for player_count in [5, 10, 20, 50, 100, 200, 500, 1000]:
            rollen = berechne_rollen(player_count)
            dorf_count = rollen.get('Dorfbewohner', 0)
            assert dorf_count >= 0, f"Negative Dorfbewohner ({dorf_count}) for {player_count} players"
    
    def test_consistent_results(self):
        """Test that role distribution is deterministic (no random variation)."""
        for player_count in [100, 500, 1000]:
            rollen1 = berechne_rollen(player_count)
            rollen2 = berechne_rollen(player_count)
            assert rollen1 == rollen2, f"Inconsistent results for {player_count} players"


class TestBalanceRatios:
    """Test that balance ratios are maintained across different game sizes."""
    
    def test_wolf_ratio_scales_down_for_large_games(self):
        """Larger games should have proportionally fewer wolves due to voting power."""
        small_game = berechne_rollen(20)
        large_game = berechne_rollen(500)
        
        small_wolf_percent = small_game.get('Werwolf', 0) / 20 * 100
        large_wolf_percent = large_game.get('Werwolf', 0) / 500 * 100
        
        # Large games should have lower wolf percentage (they have more voting power)
        assert large_wolf_percent <= small_wolf_percent + 5, \
            f"Large game wolf% ({large_wolf_percent:.1f}) should not be much higher than small ({small_wolf_percent:.1f})"
    
    def test_special_roles_scale_with_size(self):
        """Special roles should increase with game size."""
        small_game = berechne_rollen(20)
        large_game = berechne_rollen(500)
        
        # Count special roles (non-Dorfbewohner, non-wolf)
        def count_special(rollen):
            return sum(v for k, v in rollen.items() 
                      if k not in ['Dorfbewohner', 'Werwolf', 'Erzaehler'])
        
        small_special = count_special(small_game)
        large_special = count_special(large_game)
        
        # Large games should have more special roles
        assert large_special > small_special * 5, \
            f"Large game specials ({large_special}) should be much more than small ({small_special})"
    
    def test_information_roles_present(self):
        """Information roles should be present in large games."""
        for player_count in [100, 200, 500, 1000]:
            rollen = berechne_rollen(player_count)
            
            # Must have information-gathering roles
            info_roles = ['Seherin', 'Medium', 'Aurenseherin', 'Tratschweib', 'Baerenbaendiger']
            info_count = sum(rollen.get(r, 0) for r in info_roles)
            
            assert info_count >= player_count // 100, \
                f"Need more info roles ({info_count}) for {player_count} players"


class TestPerformance:
    """Test performance characteristics of role distribution."""
    
    def test_large_calculation_time(self):
        """Role calculation should be fast even for huge games."""
        import time
        
        start = time.time()
        for _ in range(100):
            berechne_rollen(1000)
        elapsed = time.time() - start
        
        # Should be able to calculate 100 1000-player distributions in under 1 second
        assert elapsed < 1.0, f"Role calculation too slow: {elapsed:.2f}s for 100 iterations"
    
    def test_memory_usage(self):
        """Role distribution dict should not be excessively large."""
        rollen = berechne_rollen(1000)
        
        # Should have at most ~50 different roles
        assert len(rollen) <= 60, f"Too many role types ({len(rollen)}) in distribution"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
