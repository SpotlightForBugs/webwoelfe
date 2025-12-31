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
      // Exclude massive tests from default project
      testIgnore: ['**/massive-*.spec.ts'],
    },
    {
      // Special project for 500-player tests - runs HEADLESS
      name: 'massive',
      use: { 
        ...devices['Desktop Chrome'],
        headless: true,  // Override: 499 players run headless
      },
      testMatch: ['**/massive-*.spec.ts'],
    },
  ],

  // Launch options for window positioning
  webServer: {
    // Use the local virtual environment: on Windows we use .venv (as used by run-tests.sh),
    // on Unix-like systems we use venv
    command: process.platform === 'win32' ? '.venv\\Scripts\\python.exe app.py' : './venv/bin/python app.py',
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
