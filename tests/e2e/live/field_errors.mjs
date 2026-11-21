// Types values into a generated app's form and prints the error shown under each field.
// Used by tests/test_integer_message_browser.py. Usage:
//   node tests/e2e/live/field_errors.mjs <app_dir> '<json: {"field": "value", ...}>'
import { pathToFileURL } from 'node:url';
import { join } from 'node:path';
import { chromium } from '@playwright/test';

const [appDir, valuesJson] = process.argv.slice(2);
const values = JSON.parse(valuesJson);
const browser = await chromium.launch();
try {
  const page = await browser.newPage();
  await page.goto(pathToFileURL(join(appDir, 'index.html')).href);
  await page.getByTestId('btn-add').click();
  for (const [field, value] of Object.entries(values)) await page.getByTestId(`input-${field}`).fill(String(value));
  await page.getByTestId('btn-save').click();
  const out = { errors: {}, rows: await page.getByTestId('record-row').count() };
  for (const field of Object.keys(values)) {
    const el = page.getByTestId(`error-${field}`);
    out.errors[field] = (await el.count()) ? (await el.textContent()).trim() : null;
  }
  console.log(JSON.stringify(out));
} finally {
  await browser.close();
}
