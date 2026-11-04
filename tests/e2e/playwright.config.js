// Playwright configuration for the fixed QA suite.
//
// Environment variables (all optional):
//   REQUIREMENTS  path to requirements.json   (default: Ghala's task_manager_en sample)
//   APP_DIR       folder with the app's index.html (default: fixtures/task-manager)
//   APP_PATH      page to open                (default: /)
//   QA_ATTEMPT    0 = first run, 1-2 = re-test after a repair
//   REPORT_PATH   where to write test_report.json (default: reports/test_report.json)
//   PORT          port of the local server     (default: 4317)

const { defineConfig, devices } = require('@playwright/test');

const PORT = Number(process.env.PORT || 4317);

module.exports = defineConfig({
  testDir: './specs',
  timeout: 30_000,
  expect: { timeout: 5_000 },
  retries: 0, // a flaky pass must not hide a real failure
  workers: 1,
  fullyParallel: false,
  outputDir: 'reports/artifacts',
  reporter: [['list'], ['./lib/report.js']],
  use: {
    ...devices['Desktop Chrome'],
    baseURL: `http://127.0.0.1:${PORT}`,
    actionTimeout: 5_000, // a missing data-testid fails in 5 s instead of the 30 s test timeout
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
  webServer: {
    command: 'node lib/serve.js',
    url: `http://127.0.0.1:${PORT}/`,
    reuseExistingServer: false,
    timeout: 15_000,
  },
});
