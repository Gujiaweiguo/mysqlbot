import { defineConfig, devices } from '@playwright/test'

const devServerPort = 4173

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? 'blob' : 'html',
  use: {
    baseURL: `http://127.0.0.1:${devServerPort}`,
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
      },
    },
  ],
  webServer: {
    command: process.env.CI
      ? `npm run build && npm run preview -- --host 127.0.0.1 --port ${devServerPort}`
      : `npm run dev -- --host 127.0.0.1 --port ${devServerPort}`,
    url: `http://127.0.0.1:${devServerPort}`,
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  },
})
