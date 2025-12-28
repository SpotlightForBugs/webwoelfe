import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright Configuration for Webwoelfe Game Tests
 * 
 * These tests simulate complete games with multiple browser instances
 * acting as different players.
 */
export default defineConfig({
  testDir: './tests',
  
  // Run tests in parallel - but be careful with shared game state
  fullyParallel: false,
  
  // Fail the build on CI if you accidentally left test.only in the source code
  forbidOnly: !!process.env.CI,
  
  // Retry on CI only
  retries: process.env.CI ? 2 : 0,
  
  // Opt out of parallel tests on CI
  workers: 1,
  
  // Reporter to use
  reporter: [
    ['html', { open: 'never' }],
    ['list']
  ],
  
  // Shared settings for all the projects below
  use: {
    // Base URL for all tests
    baseURL: 'http://localhost:5001',
    
    // Show browser during test execution
    headless: false,
    
    // Collect trace when retrying the failed test
    trace: 'on-first-retry',
    
    // Screenshot on failure
    screenshot: 'only-on-failure',
    
    // Video on failure
    video: 'on-first-retry',
    
    // Default timeout for actions
    actionTimeout: 10000,
    
    // Default navigation timeout
    navigationTimeout: 30000,
  },

  // Configure projects for major browsers
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  // Launch options for window positioning
  webServer: {
    command: './venv/bin/python app.py',
    url: 'http://localhost:5001',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  },
  
  // Global timeout for each test
  timeout: 120000,
  
  // Expect timeout
  expect: {
    timeout: 10000,
  },
});
