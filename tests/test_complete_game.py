import pytest
import time
from app import Game, Player, Vote, Action, db

def test_complete_game_simulation(client, socket_client, game_with_players, app_instance):
    """
    Simulate a complete game from start to finish with all phases:
    1. Setup phase: Create game and add players
    2. Waiting phase: Cupid selects lovers
    3. Night phase: Werewolves vote, Witch and Seer take actions
    4. Day phase: Village votes
    5. Check for win conditions
    """
    # Create a game with 8 players
    game_id, players = game_with_players(8)
    
    # Get player details including roles
    with app_instance.app_context():
        game = Game.query.get(game_id)
        assert game.status == 'running'
        assert game.phase == 'waiting'
        
        # Find players with specific roles
        all_db_players = Player.query.filter_by(game_id=game_id).all()
        
        # Map roles to players
        role_map = {}
        for db_player in all_db_players:
            role_map[db_player.role] = db_player
            
            # Update our players list with roles
            for player in players:
                if player['player_id'] == db_player.id:
                    player['role'] = db_player.role
        
        # Check that we have necessary roles
        assert 'Amor' in role_map
        assert 'Werwolf' in role_map
        assert 'Seherin' in role_map
        assert 'Hexe' in role_map
        
        # Get a list of werewolves
        werewolves = [p for p in all_db_players if p.role == 'Werwolf']
        assert len(werewolves) >= 2
        
        # Get villagers (non-special roles)
        villagers = [p for p in all_db_players if p.role == 'Dorfbewohner']
        
        # Connect socket clients for each player
        socket_client.connect()
        socket_client.emit('join_game', {'game_id': game_id, 'token': players[0]['token']})
        received = socket_client.get_received()
        assert len(received) > 0
        assert received[0]['name'] == 'joined'
        
        # 1. WAITING PHASE: Amor selects lovers
        amor = role_map['Amor']
        amor_player = next(p for p in players if p['player_id'] == amor.id)
        
        # Find two players to make lovers (not Amor or same person)
        lover1 = next(p for p in all_db_players if p.role != 'Amor')
        lover2 = next(p for p in all_db_players if p.id != lover1.id and p.role != 'Amor')
        
        # Emit amor's action to create lovers
        socket_client.emit('action', {
            'token': amor_player['token'],
            'action_type': 'create_lovers',
            'target_id': lover1.id,
            'second_target': lover2.id
        })
        
        # Wait for the action to be processed
        time.sleep(0.5)
        
        # Check that game phase changed to night
        game = Game.query.get(game_id)
        assert game.phase == 'night'
        assert game.lover1_id is not None
        assert game.lover2_id is not None
        
        # 2. NIGHT PHASE: Werewolves vote, Witch and Seer take actions
        
        # First, get all living players
        living_players = Player.query.filter_by(game_id=game_id, status='alive').all()
        
        # Choose a victim (not another werewolf)
        victim = next(p for p in all_db_players if p.role != 'Werwolf')
        
        # Have ALL werewolves vote for the victim
        for werewolf in werewolves:
            werewolf_player = next(p for p in players if p['player_id'] == werewolf.id)
            
            socket_client.emit('vote', {
                'token': werewolf_player['token'],
                'target_id': victim.id
            })
        
        # Seer checks a player's role
        seer = role_map['Seherin']
        seer_player = next(p for p in players if p['player_id'] == seer.id)
        
        # Choosing a random player to check
        player_to_check = next(p for p in all_db_players if p.id != seer.id)
        
        socket_client.emit('action', {
            'token': seer_player['token'],
            'action_type': 'see',
            'target_id': player_to_check.id
        })
        
        # Witch may use a potion (kill or heal)
        witch = role_map['Hexe']
        witch_player = next(p for p in players if p['player_id'] == witch.id)
        
        # For this test, let's have the witch kill someone
        witch_victim = next(p for p in all_db_players if p.id != witch.id and p.id != victim.id)
        
        socket_client.emit('action', {
            'token': witch_player['token'],
            'action_type': 'kill',
            'target_id': witch_victim.id
        })
        
        # IMPORTANT: Make sure all remaining living players vote during night phase
        # This is necessary for the phase to change from night to day
        for player in living_players:
            # Skip werewolves, witch and seer who have already voted/acted
            if player.role not in ['Werwolf', 'Seherin', 'Hexe']:
                player_data = next(p for p in players if p['player_id'] == player.id)
                
                # The regular villagers and other roles also need to vote during night phase
                socket_client.emit('vote', {
                    'token': player_data['token'],
                    'target_id': victim.id  # Everyone votes for the same person
                })
        
        # Wait for the night phase to complete
        time.sleep(1.0)
        
        # Check that phase changed to day
        game = Game.query.get(game_id)
        assert game.phase == 'day'
        
        # Check that the victim is dead
        victim_db = Player.query.get(victim.id)
        assert victim_db.status == 'dead'
        
        # 3. DAY PHASE: Village votes
        
        # Update living players list after the night phase
        living_players = Player.query.filter_by(game_id=game_id, status='alive').all()
        
        # Everyone votes for a werewolf to be eliminated
        werewolf_to_kill = next(w for w in werewolves if Player.query.get(w.id).status == 'alive')
        
        for living_player in living_players:
            player_data = next(p for p in players if p['player_id'] == living_player.id)
            socket_client.emit('vote', {
                'token': player_data['token'],
                'target_id': werewolf_to_kill.id
            })
        
        # Wait for day phase to complete
        time.sleep(1.0)
        
        # Verify the werewolf is dead
        werewolf_db = Player.query.get(werewolf_to_kill.id)
        assert werewolf_db.status == 'dead'
        
        # Game should go back to night phase or end depending on win conditions
        game = Game.query.get(game_id)
        
        # Count living werewolves and villagers
        living_werewolves = Player.query.filter_by(game_id=game_id, role='Werwolf', status='alive').count()
        living_villagers = Player.query.filter_by(game_id=game_id, status='alive').filter(Player.role != 'Werwolf').count()
        
        # Check if game ended or went to next night phase
        if living_werewolves == 0:
            assert game.status == 'ended'
            assert game.phase == 'villagers_win'
        elif living_werewolves >= living_villagers:
            assert game.status == 'ended'
            assert game.phase == 'werewolves_win'
        else:
            assert game.phase == 'night'
            
        # Clean up
        socket_client.disconnect()