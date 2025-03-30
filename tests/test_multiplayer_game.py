import pytest
import json
from app import app, db, Game, Player, Vote, Action, GameLog, process_night_actions
from flask import url_for, current_app
import random
import time
from unittest.mock import patch

class TestMultiPlayerGame:
    """Test a complete game cycle with multiple users."""
    
    def test_full_game_simulation(self, client, game_with_players, socket_clients, app_instance):
        """
        Simulate a complete game with 8 players:
        - Create game and join all players
        - Each player connects via Socket.IO
        - Night phase: Werewolves vote, special roles take actions
        - Day phase: All players vote
        - Continue until game ends
        """
        # Step 1: Create game and add players
        game_id, players = game_with_players(num_players=8)
        
        # Step 2: Get player roles to know who is who
        with app_instance.app_context():
            all_players = Player.query.filter_by(game_id=game_id).all()
            werewolves = [p for p in all_players if p.role == 'Werwolf']
            villagers = [p for p in all_players if p.role == 'Dorfbewohner']
            witch = next((p for p in all_players if p.role == 'Hexe'), None)
            seer = next((p for p in all_players if p.role == 'Seherin'), None)
            storyteller = next((p for p in all_players if p.role == 'Erzaehler'), None)
            
            # Map player tokens to roles for testing
            player_roles = {p.token: p.role for p in all_players}
            player_ids = {p.token: p.id for p in all_players}
            
            # Ensure we have the right roles
            assert len(werewolves) >= 2, "Should have at least 2 werewolves"
            assert witch is not None, "Should have a witch"
            assert seer is not None, "Should have a seer"
        
        # Step 3: Connect all players to Socket.IO
        for i, player in enumerate(players):
            # Use the socket clients we created for each player
            socket_clients[i].emit('join_game', {
                'game_id': game_id,
                'token': player['token']
            })
            # Check the response
            received = socket_clients[i].get_received()
            assert len(received) > 0
            assert received[0]['name'] == 'joined'
            
        # Step 4: Simulate night phase - Werewolf votes
        werewolf_tokens = [token for token, role in player_roles.items() if role == 'Werwolf']
        villager_tokens = [token for token, role in player_roles.items() if role == 'Dorfbewohner']
        
        # Pick a villager to kill
        target_token = random.choice(villager_tokens)
        target_id = player_ids[target_token]
        
        # Make werewolves vote for the same target
        for werewolf_token in werewolves:
            werewolf_index = next(i for i, p in enumerate(players) if p['token'] == werewolf_token.token)
            socket_clients[werewolf_index].emit('vote', {
                'token': werewolf_token.token,
                'target_id': target_id
            })
        
        # Step 5: Simulate night phase - Special role actions
        if witch:
            witch_index = next(i for i, p in enumerate(players) if p['token'] == witch.token)
            
            # Witch decides not to save but to kill a random werewolf
            werewolf_id = werewolves[0].id
            socket_clients[witch_index].emit('action', {
                'token': witch.token,
                'action_type': 'kill',
                'target_id': werewolf_id
            })
        
        if seer:
            seer_index = next(i for i, p in enumerate(players) if p['token'] == seer.token)
            
            # Seer looks at a random player
            random_player = random.choice(all_players)
            random_player_id = random_player.id
            socket_clients[seer_index].emit('action', {
                'token': seer.token,
                'action_type': 'see',
                'target_id': random_player_id
            })
            
            # Check that seer got a result
            received = socket_clients[seer_index].get_received()
            seer_results = [msg for msg in received if msg['name'] == 'seer_result']
            assert len(seer_results) > 0
        
        # Directly call process_night_actions to ensure phase changes
        with app_instance.app_context():
            process_night_actions(game_id)
            
            # Verify the phase has changed
            game = Game.query.get(game_id)
            assert game.phase == 'day', "Game should move to day phase after night actions"
        
        # Step 6: Simulate day phase - All players vote
        # Find remaining alive players 
        with app_instance.app_context():
            alive_players = Player.query.filter_by(game_id=game_id, status='alive').all()
            alive_tokens = [p.token for p in alive_players]
            alive_ids = [p.id for p in alive_players]
        
        # Each living player votes for someone (randomly)
        for alive_player in alive_players:
            player_index = next(i for i, p in enumerate(players) if p['token'] == alive_player.token)
            # Don't vote for yourself
            possible_targets = [p.id for p in alive_players if p.id != alive_player.id]
            if possible_targets:  # Check if there are any targets available
                vote_target_id = random.choice(possible_targets)
                
                socket_clients[player_index].emit('vote', {
                    'token': alive_player.token,
                    'target_id': vote_target_id
                })
        
        # Step 7: Check game status and logs
        with app_instance.app_context():
            # Directly check logs
            logs = GameLog.query.filter_by(game_id=game_id).order_by(GameLog.timestamp.desc()).all()
            log_messages = [log.message for log in logs]
            
            # Check for expected log messages
            assert any("roles assigned" in msg for msg in log_messages), "Should have role assignment log"
            
            # Game might end in this cycle if conditions are met
            game = Game.query.get(game_id)
            if game.status == 'ended':
                assert game.phase in ['villagers_win', 'werewolves_win'], "Game should end with a winner"

    def test_werewolves_win_scenario(self, client, game_with_players, socket_clients, app_instance):
        """
        Test to ensure werewolves can win the game when they outnumber villagers.
        This test patches the kill_player function to simulate werewolves killing villagers
        until they win.
        """
        # Create a game with 8 players
        game_id, players = game_with_players(num_players=8)
        
        # Connect all players to Socket.IO
        for i, player in enumerate(players):
            socket_clients[i].emit('join_game', {
                'game_id': game_id,
                'token': player['token']
            })
        
        # Get player information
        with app_instance.app_context():
            all_players = Player.query.filter_by(game_id=game_id).all()
            werewolves = [p for p in all_players if p.role == 'Werwolf']
            non_werewolves = [p for p in all_players if p.role != 'Werwolf']
            
            werewolf_ids = [w.id for w in werewolves]
            non_werewolf_ids = [p.id for p in non_werewolves]
            
            # Patch to skip over the night/day process and just kill players
            # Kill all non-werewolves except one (to trigger werewolf win condition)
            for i, player_id in enumerate(non_werewolf_ids[:-1]):
                player = Player.query.get(player_id)
                player.status = 'dead'
            
            db.session.commit()
            
            # Check if game ended with werewolves winning
            from app import check_game_end
            check_game_end(game_id)
            
            game = Game.query.get(game_id)
            assert game.status == 'ended'
            assert game.phase == 'werewolves_win'
            
            # Verify logs indicate werewolves won
            logs = GameLog.query.filter_by(game_id=game_id).order_by(GameLog.timestamp.desc()).all()
            assert any("Werewolves win" in log.message for log in logs)

    def test_villagers_win_scenario(self, client, game_with_players, socket_clients, app_instance):
        """
        Test to ensure villagers can win the game when all werewolves are dead.
        """
        # Create a game with 8 players
        game_id, players = game_with_players(num_players=8)
        
        # Connect all players to Socket.IO
        for i, player in enumerate(players):
            socket_clients[i].emit('join_game', {
                'game_id': game_id,
                'token': player['token']
            })
        
        # Get player information
        with app_instance.app_context():
            all_players = Player.query.filter_by(game_id=game_id).all()
            werewolves = [p for p in all_players if p.role == 'Werwolf']
            
            # Kill all werewolves to trigger villager win condition
            for werewolf in werewolves:
                werewolf.status = 'dead'
            
            db.session.commit()
            
            # Check if game ended with villagers winning
            from app import check_game_end
            check_game_end(game_id)
            
            game = Game.query.get(game_id)
            assert game.status == 'ended'
            assert game.phase == 'villagers_win'
            
            # Verify logs indicate villagers won
            logs = GameLog.query.filter_by(game_id=game_id).order_by(GameLog.timestamp.desc()).all()
            assert any("Villagers win" in log.message for log in logs)