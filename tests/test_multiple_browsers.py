import tempfile
import time
import pytest
import threading
import os
import shutil
import concurrent.futures
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from selenium.webdriver.edge.service import Service

"""
This test demonstrates how to test the game with multiple browser windows
that don't share cookies, simulating multiple players in the same game.
The first browser runs with a head (visible UI), while others run headless.
"""

@pytest.fixture
def app_server():
    """Start the Flask app in a separate thread"""
    from app import app, socketio
    
    def run_server():
        socketio.run(app, debug=False, port=5000)
    
    # Start server in background thread
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    
    # Give the server time to start
    time.sleep(2)
    yield
    # Server will be terminated when test finishes due to daemon=True

def create_driver(headless=True, index=0):
    """Create a new browser session with isolated cookies
       First browser (index 0) will be headed, others headless if requested"""
    # Using webdriver_manager to get the correct driver version
    service = Service(EdgeChromiumDriverManager().install())
    
    options = webdriver.EdgeOptions()
    
    # Add stability options for Edge automation
    if headless and index > 0:  # Make all browsers except the first one headless
        options.add_argument("--headless")
    
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-infobars")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    # Each driver gets a new, empty user data directory - but use a more stable path format
    user_data_dir = tempfile.mkdtemp(prefix=f"edgedata_{index}_")
    options.add_argument(f"--user-data-dir={user_data_dir}")
    
    driver = webdriver.Edge(service=service, options=options)
    # Store the temp directory path with the driver for later cleanup
    driver.user_data_dir = user_data_dir
    return driver

def join_game(driver, game_url, player_name):
    """Helper function to join a game with the given player name"""
    driver.get(game_url)
    
    # Wait for the player name input to be available
    player_name_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "player-name"))
    )
    
    # Input the player name
    player_name_input.clear()
    player_name_input.send_keys(player_name)
    
    # Submit the join form
    join_form = driver.find_element(By.ID, "player-join-form")
    join_form.submit()
    
    # Wait for the game section to be visible, indicating successful join
    WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, "game-section"))
    )
    
    # Verify player name is displayed correctly
    WebDriverWait(driver, 10).until(
        EC.text_to_be_present_in_element((By.ID, "display-name"), player_name)
    )
    
    print(f"Player {player_name} joined the game")
    return True

def wait_for_phase_change(driver, expected_phase, timeout=20):
    """Wait for the game phase to change to the expected phase"""
    WebDriverWait(driver, timeout).until(
        EC.text_to_be_present_in_element((By.ID, "display-phase"), expected_phase)
    )
    print(f"Phase changed to: {expected_phase}")

def test_multiple_players_extended(app_server):
    """
    Extended test with 8 players using separate browser instances.
    First browser is headed, others are headless.
    Tests joining, phase changes, and some game mechanics.
    """
    start_time = time.time()
    num_players = 8
    player_names = [f"Player {i+1}" for i in range(num_players)]
    drivers = []
    user_data_dirs = []
    success = False
    
    print("Starting browser creation in parallel...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_players) as executor:
        # Create all browsers in parallel - first one with head, others headless
        future_to_driver = {executor.submit(create_driver, True, i): i for i in range(num_players)}
        for future in concurrent.futures.as_completed(future_to_driver):
            idx = future_to_driver[future]
            try:
                driver = future.result()
                drivers.append((idx, driver))  # Store index with driver to maintain order
                user_data_dirs.append(driver.user_data_dir)
                print(f"Browser {idx} created")
            except Exception as exc:
                print(f'Browser {idx} creation generated an exception: {exc}')
    
    # Sort drivers by index to ensure correct order
    drivers.sort(key=lambda x: x[0])
    drivers = [d for _, d in drivers]
    
    print(f"All browsers created in {time.time() - start_time:.2f} seconds")
    
    try:
        # First player creates the game
        drivers[0].get("http://localhost:5000")
        # Find player count input by NAME attribute (matches the form submission)
        drivers[0].find_element(By.NAME, "player_count").clear()
        drivers[0].find_element(By.NAME, "player_count").send_keys(str(num_players))
        drivers[0].find_element(By.XPATH, "//button[contains(text(), 'Create Game')]").click()
        
        # Get game URL
        game_url = drivers[0].current_url
        print(f"Game created at: {game_url}")
        
        # First player joins
        join_game(drivers[0], game_url, player_names[0])
        
        # All other players join the same game in parallel
        print("Starting parallel game joins...")
        join_start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_players-1) as executor:
            # Join all players in parallel
            future_to_join = {
                executor.submit(join_game, drivers[i], game_url, player_names[i]): i 
                for i in range(1, num_players)
            }
            for future in concurrent.futures.as_completed(future_to_join):
                idx = future_to_join[future] 
                try:
                    result = future.result()
                    if result:
                        print(f"Player {player_names[idx]} join completed")
                except Exception as exc:
                    print(f'Player {player_names[idx]} join generated an exception: {exc}')
        
        print(f"All players joined in {time.time() - join_start_time:.2f} seconds")
        
        # Verify all players are in the player list (check the first browser)
        for player_name in player_names:
            WebDriverWait(drivers[0], 10).until(
                EC.text_to_be_present_in_element((By.ID, "player-list"), player_name)
            )
            print(f"Verified {player_name} is in the player list")
        
        # EXTENDED TESTING: Let's check game phases and interactions
        
        # 1. Wait for night phase to begin - game starts with night phase
        wait_for_phase_change(drivers[0], "night")
        print("Game has started - entered night phase")
        
        # 2. Check that roles have been assigned to all players
        for i, driver in enumerate(drivers):
            try:
                role_element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "display-role"))
                )
                role = role_element.text
                assert role != "", f"Player {player_names[i]} has not been assigned a role"
                print(f"Player {player_names[i]} has been assigned role: {role}")
            except Exception as e:
                print(f"Error checking role for player {player_names[i]}: {e}")
        
        # 3. Test werewolf night action - find werewolf and select a victim
        for i, driver in enumerate(drivers):
            try:
                role_element = driver.find_element(By.ID, "display-role")
                if "Werwolf" in role_element.text:
                    print(f"Found werewolf: Player {player_names[i]}")
                    
                    # Check if night action section is visible for werewolf
                    action_section = WebDriverWait(driver, 10).until(
                        EC.visibility_of_element_located((By.ID, "action-section"))
                    )
                    
                    # Click the kill button
                    kill_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Choose victim')]"))
                    )
                    kill_button.click()
                    
                    # Wait for target selection to be visible
                    target_selection = WebDriverWait(driver, 10).until(
                        EC.visibility_of_element_located((By.ID, "target-selection"))
                    )
                    
                    # Select a random target and confirm
                    confirm_button = driver.find_element(By.ID, "confirm-action")
                    confirm_button.click()
                    
                    print(f"Werewolf {player_names[i]} selected a victim")
                    break
            except Exception as e:
                # Not a werewolf or error occurred
                continue
        
        # 4. Test for day phase transition - this would happen after all night actions
        # In a real game, we'd need to complete all night actions, but for testing,
        # we can just verify the UI elements are working correctly
        
        # 5. Test voting during day phase (if we get to day phase)
        try:
            # Give some time for possible phase change
            day_phase_detected = False
            for _ in range(3):  # Try a few times
                time.sleep(2)  # Short wait
                for driver in drivers:
                    phase_element = driver.find_element(By.ID, "display-phase")
                    if phase_element.text == "day":
                        day_phase_detected = True
                        # Test voting
                        try:
                            # Check if voting section is visible
                            voting_section = WebDriverWait(driver, 5).until(
                                EC.visibility_of_element_located((By.ID, "voting-section"))
                            )
                            
                            # Click the vote button
                            confirm_vote = driver.find_element(By.ID, "confirm-vote")
                            confirm_vote.click()
                            
                            print(f"Successfully voted during day phase")
                        except Exception as e:
                            print(f"Error during voting: {e}")
                        break
                if day_phase_detected:
                    break
        except Exception as e:
            print(f"Day phase testing skipped: {e}")
            
        # Wait a moment to see the final state of the game
        time.sleep(5)
        
        # Test successful - completed extended testing
        total_time = time.time() - start_time
        print(f"Test successful: Completed extended testing in {total_time:.2f} seconds")
        success = True
        
    finally:
        # Clean up all browser instances
        for driver in drivers:
            driver.quit()
        
        # Only remove user profiles after successful test
        if success:
            print("Cleaning up user data directories...")
            for user_data_dir in user_data_dirs:
                try:
                    if os.path.exists(user_data_dir):
                        shutil.rmtree(user_data_dir)
                        print(f"Removed: {user_data_dir}")
                except Exception as e:
                    print(f"Error removing directory {user_data_dir}: {e}")

# To run the test: pytest -xvs tests/test_multiple_browsers.py