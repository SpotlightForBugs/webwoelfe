import pytest
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

@pytest.fixture
def browser_setup():
    """Setup and teardown browsers for testing."""
    browsers = []
    
    # Setup multiple browsers
    for _ in range(8):  # Create 8 browsers for 8 players
        browser = webdriver.Chrome()
        browser.implicitly_wait(10)
        browsers.append(browser)
    
    yield browsers
    
    # Teardown browsers
    for browser in browsers:
        browser.quit()

def test_multiplayer_browser_game(browser_setup, client, app_instance):
    """
    Simulate a complete game using real browser interactions.
    This tests all phases with multiple players in different browsers.
    """
    browsers = browser_setup
    
    # 1. First browser creates the game
    browsers[0].get('http://localhost:5000')
    
    # Create new game with 8 players
    browsers[0].find_element(By.ID, 'player-count').clear()
    browsers[0].find_element(By.ID, 'player-count').send_keys('8')
    browsers[0].find_element(By.ID, 'create-game').click()
    
    # Get the game URL
    game_url = browsers[0].current_url
    
    # Extract game ID from URL
    game_id = game_url.split('/')[-1]
    
    # 2. Each browser joins the game
    player_info = []
    for i, browser in enumerate(browsers):
        browser.get(game_url)
        
        # Enter player name and join
        player_name = f"Player{i+1}"
        browser.find_element(By.ID, 'player-name').clear()
        browser.find_element(By.ID, 'player-name').send_keys(player_name)
        browser.find_element(By.ID, 'join-game').click()
        
        # Wait for role to be assigned
        WebDriverWait(browser, 10).until(
            EC.visibility_of_element_located((By.ID, 'player-role'))
        )
        
        # Get player role and store info
        role = browser.find_element(By.ID, 'player-role').text
        player_info.append({
            'browser': browser,
            'name': player_name,
            'role': role
        })
    
    # Wait for game to start
    time.sleep(2)
    
    # 3. Find Amor and have them select lovers
    amor_player = next(p for p in player_info if 'Amor' in p['role'])
    amor_browser = amor_player['browser']
    
    # Wait for waiting phase UI to appear
    WebDriverWait(amor_browser, 10).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, '.lover-selection'))
    )
    
    # Select two players to be lovers
    lover_options = amor_browser.find_elements(By.CSS_SELECTOR, '.lover-option')
    # Choose first two selectable players
    lover_options[0].click()
    lover_options[1].click()
    
    # Confirm selection
    amor_browser.find_element(By.ID, 'confirm-lovers').click()
    
    # Wait for night phase to begin
    time.sleep(2)
    
    # 4. Night Phase: Werewolves vote
    werewolf_players = [p for p in player_info if 'Werwolf' in p['role']]
    victim_name = player_info[2]['name']  # Select a victim
    
    for werewolf in werewolf_players:
        werewolf_browser = werewolf['browser']
        
        # Wait for werewolf UI to appear
        WebDriverWait(werewolf_browser, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, '.werewolf-vote'))
        )
        
        # Find and vote for the victim
        player_options = werewolf_browser.find_elements(By.CSS_SELECTOR, '.player-option')
        for option in player_options:
            if victim_name in option.text:
                option.click()
                break
    
    # 5. Witch selects an action
    witch_player = next(p for p in player_info if 'Hexe' in p['role'])
    witch_browser = witch_player['browser']
    
    # Wait for witch UI to appear
    WebDriverWait(witch_browser, 10).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, '.witch-actions'))
    )
    
    # Select poison option
    witch_browser.find_element(By.ID, 'poison-potion').click()
    
    # Select a victim for poison
    poison_options = witch_browser.find_elements(By.CSS_SELECTOR, '.poison-target')
    # Choose the first available player
    poison_victim = poison_options[0]
    poison_victim.click()
    
    # Confirm witch action
    witch_browser.find_element(By.ID, 'confirm-witch-action').click()
    
    # 6. Seer checks someone's role
    seer_player = next(p for p in player_info if 'Seherin' in p['role'])
    seer_browser = seer_player['browser']
    
    # Wait for seer UI to appear
    WebDriverWait(seer_browser, 10).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, '.seer-action'))
    )
    
    # Select a player to check
    seer_options = seer_browser.find_elements(By.CSS_SELECTOR, '.seer-target')
    seer_target = seer_options[0]
    seer_target.click()
    
    # Confirm seer action
    seer_browser.find_element(By.ID, 'confirm-seer-action').click()
    
    # Wait for all players to submit night actions
    time.sleep(3)
    
    # 7. Day Phase: All players vote
    for player in player_info:
        browser = player['browser']
        
        # Skip dead players if any
        try:
            # Check if player status shows "dead"
            status_element = browser.find_element(By.ID, 'player-status')
            if "dead" in status_element.text.lower():
                continue
        except:
            # If we can't find the status or there's another error, try to vote anyway
            pass
        
        # Wait for day voting UI to appear
        try:
            WebDriverWait(browser, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, '.day-vote'))
            )
            
            # Select a player to vote for
            vote_options = browser.find_elements(By.CSS_SELECTOR, '.vote-option')
            if vote_options:
                # Try to find a werewolf if visible, otherwise pick the first option
                vote_target = vote_options[0]
                vote_target.click()
                
                # Confirm vote
                browser.find_element(By.ID, 'confirm-vote').click()
        except:
            # Skip if voting UI doesn't appear (could be dead)
            continue
    
    # Wait for votes to be processed
    time.sleep(3)
    
    # 8. Check if the game has ended or another night has begun
    # We'll check the first browser for game status
    main_browser = browsers[0]
    
    # Check for game over message or night phase message
    game_status_text = main_browser.find_element(By.ID, 'game-status').text.lower()
    
    if "ended" in game_status_text or "win" in game_status_text:
        assert "game over" in game_status_text or "win" in game_status_text
    else:
        assert "night" in game_status_text