#!/usr/bin/env python3
"""Quick test script for role balance verification."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game_logic import berechne_rollen
from models import ROLLEN

def test_game(player_count):
    """Test role distribution for a given player count."""
    rollen = berechne_rollen(player_count)
    
    print(f"\n{'='*60}")
    print(f"ROLE DISTRIBUTION FOR {player_count} PLAYERS")
    print(f"{'='*60}")
    
    # Total check
    total = sum(rollen.values())
    print(f"Total roles: {total} (should be {player_count})")
    
    # Categorize by team
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
    
    # Balance check
    village = teams['dorf']
    wolves = teams['werwolf']
    
    print(f"\n{'='*60}")
    print("BALANCE METRICS:")
    print(f"{'='*60}")
    print(f"  Village to Wolf ratio: {village}:{wolves} (1:{wolves/village:.2f})" if village > 0 else "  No village")
    print(f"  Wolf percentage: {wolves/player_count*100:.1f}%")
    print(f"  Village percentage: {village/player_count*100:.1f}%")
    
    # Assertions
    assert total == player_count, f"Total mismatch: {total} != {player_count}"
    assert wolves > 0, "Must have wolves"
    assert village > wolves, "Village must outnumber wolves"
    assert wolves/player_count <= 0.30, f"Too many wolves: {wolves/player_count*100:.1f}%"
    
    print("\n✓ Balance check PASSED!")
    return True

if __name__ == "__main__":
    player_counts = [5, 10, 20, 50, 100, 200, 500, 1000]
    
    if len(sys.argv) > 1:
        player_counts = [int(sys.argv[1])]
    
    all_passed = True
    for count in player_counts:
        try:
            test_game(count)
        except AssertionError as e:
            print(f"\n✗ FAILED for {count} players: {e}")
            all_passed = False
    
    if all_passed:
        print(f"\n{'='*60}")
        print("ALL BALANCE TESTS PASSED!")
        print(f"{'='*60}")
    else:
        print(f"\n{'='*60}")
        print("SOME TESTS FAILED!")
        print(f"{'='*60}")
        sys.exit(1)
