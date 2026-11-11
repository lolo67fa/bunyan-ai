// The fixed QA suite: 8 checks, parameterised by requirements.json.
// No test is generated per app. Element names follow the data-testid rules in
// Naifah's architecture contract (0.2.0-proposal, §5):
//   btn-add, btn-save, btn-cancel, input-<field>, error-<field>,
//   records-table, record-row (data-id), cell-<field>, btn-edit, btn-delete,
//   btn-confirm-delete, btn-cancel-delete, empty-state, toast.

const { test, expect } = require('@playwright/test');
const { loadRequirements, buildPlan, recordValues } = require('../lib/requirements');

const APP_PATH = process.env.APP_PATH || '/';

let plan;

test.beforeAll(() => {
  const { entity } = loadRequirements();
  plan = buildPlan(entity);
});

test.beforeEach(() => {
  test.skip(plan.problems.length > 0, `Suite cannot build valid input: ${plan.problems.join('; ')}`);
});

// ---------- helpers ----------

const rows = (page) => page.getByTestId('record-row');

function escapeRegex(s) {
  return String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/** Rows whose display-field cell contains exactly `value`. */
function rowByDisplay(page, value) {
  const cell = page.getByTestId(`cell-${plan.display}`).filter({ hasText: new RegExp(`^\\s*${escapeRegex(value)}\\s*$`) });
  return rows(page).filter({ has: cell });
}

async function openApp(page) {
  await page.goto(APP_PATH);
  await expect(page.getByTestId('btn-add'), 'list screen with btn-add should load').toBeVisible();
}

async function setField(page, name, value) {
  const input = page.getByTestId(`input-${name}`);
  const tag = await input.evaluate((el) => el.tagName.toLowerCase());
  const type = (await input.getAttribute('type')) || '';
  if (tag === 'select') await input.selectOption(String(value));
  else if (type === 'checkbox') await input.setChecked(Boolean(value));
  else await input.fill(String(value));
}

async function createRecord(page, tag) {
  const values = recordValues(plan, tag);
  await page.getByTestId('btn-add').click();
  for (const [name, value] of Object.entries(values)) await setField(page, name, value);
  await page.getByTestId('btn-save').click();
  await expect(rowByDisplay(page, values[plan.display]), `record "${values[plan.display]}" should be listed after save`).toHaveCount(1);
  return values;
}

/** Leaves every required field empty that can be empty. Returns their names. */
async function emptyRequiredFields(page) {
  const emptied = [];
  for (const f of plan.required) {
    const input = page.getByTestId(`input-${f.name}`);
    const tag = await input.evaluate((el) => el.tagName.toLowerCase());
    if (tag === 'select') {
      const hasBlank = await input.evaluate((el) => [...el.options].some((o) => o.value === ''));
      if (!hasBlank) continue; // e.g. enum with a default: there is no empty choice
      await input.selectOption('');
    } else if ((await input.getAttribute('type')) === 'checkbox') {
      continue;
    } else {
      await input.fill('');
    }
    emptied.push(f.name);
  }
  return emptied;
}

// ---------- the 8 checks (titles are the check ids) ----------

test('create_item', async ({ page }) => {
  await openApp(page);
  const before = await rows(page).count();
  await createRecord(page, 'Create 1');
  await expect(rows(page)).toHaveCount(before + 1);
  await expect(page.getByTestId('btn-add'), 'should return to the list after save').toBeVisible();
});

test('list_items', async ({ page }) => {
  await openApp(page);
  const created = [];
  for (const n of [1, 2, 3]) created.push(await createRecord(page, `List ${n}`));
  await expect(rows(page)).toHaveCount(3);
  for (const values of created) {
    const row = rowByDisplay(page, values[plan.display]);
    for (const field of plan.listFields) {
      await expect(row.getByTestId(`cell-${field}`), `row "${values[plan.display]}" should show column ${field}`).toHaveCount(1);
    }
  }
});

test('edit_item', async ({ page }) => {
  await openApp(page);
  const original = await createRecord(page, 'Edit 1');
  const oldValue = original[plan.display];
  const newValue = recordValues(plan, 'Edited 1')[plan.display];
  const count = await rows(page).count();

  await rowByDisplay(page, oldValue).getByTestId('btn-edit').click();
  const input = page.getByTestId(`input-${plan.display}`);
  await expect(input, 'edit form should be pre-filled').toHaveValue(oldValue);
  await input.fill(newValue);
  await page.getByTestId('btn-save').click();

  await expect(rowByDisplay(page, newValue)).toHaveCount(1);
  await expect(rowByDisplay(page, oldValue)).toHaveCount(0);
  await expect(rows(page), 'editing must not add or remove records').toHaveCount(count);
});

test('delete_item', async ({ page }) => {
  await openApp(page);
  const target = (await createRecord(page, 'Delete 1'))[plan.display];
  const keep = (await createRecord(page, 'Keep 1'))[plan.display];
  await expect(rows(page)).toHaveCount(2);

  await rowByDisplay(page, target).getByTestId('btn-delete').click();
  await page.getByTestId('btn-cancel-delete').filter({ visible: true }).click();
  await expect(rowByDisplay(page, target), 'cancelling delete must keep the record').toHaveCount(1);

  await rowByDisplay(page, target).getByTestId('btn-delete').click();
  await page.getByTestId('btn-confirm-delete').filter({ visible: true }).click();
  await expect(rowByDisplay(page, target)).toHaveCount(0);
  await expect(rowByDisplay(page, keep), 'other records must stay').toHaveCount(1);
  await expect(rows(page)).toHaveCount(1);
});

test('persist_after_refresh', async ({ page }) => {
  await openApp(page);
  const values = await createRecord(page, 'Persist 1');
  const count = await rows(page).count();
  await page.reload();
  await expect(page.getByTestId('btn-add')).toBeVisible();
  await expect(rowByDisplay(page, values[plan.display]), 'record should survive a reload').toHaveCount(1);
  await expect(rows(page)).toHaveCount(count);
});

test('reject_incomplete_input', async ({ page }) => {
  test.skip(plan.emptiable.length === 0, 'No required field can be left empty (all required fields are selects with defaults or checkboxes)');
  await openApp(page);
  const before = await rows(page).count();
  await page.getByTestId('btn-add').click();
  const emptied = await emptyRequiredFields(page);
  test.skip(emptied.length === 0, 'No required field could be emptied in the form');
  await page.getByTestId('btn-save').click();

  await expect(page.getByTestId('btn-save'), 'form should stay open when input is incomplete').toBeVisible();
  await page.getByTestId('btn-cancel').click();
  await expect(rows(page), 'no record should be added').toHaveCount(before);
  await page.reload();
  await expect(page.getByTestId('btn-add')).toBeVisible();
  await expect(rows(page), 'no record should be stored').toHaveCount(before);
});

test('empty_state', async ({ page }) => {
  await openApp(page);
  await expect(rows(page)).toHaveCount(0);
  await expect(page.getByTestId('empty-state')).toBeVisible();
  await expect(page.getByTestId('empty-state')).toHaveText(/\S/);
  await createRecord(page, 'Empty 1');
  await expect(page.getByTestId('empty-state'), 'empty state should hide once a record exists').toBeHidden();
});

test('error_message_visible', async ({ page }) => {
  test.skip(plan.emptiable.length === 0, 'No required field can be left empty (all required fields are selects with defaults or checkboxes)');
  await openApp(page);
  await page.getByTestId('btn-add').click();
  const emptied = await emptyRequiredFields(page);
  test.skip(emptied.length === 0, 'No required field could be emptied in the form');
  await page.getByTestId('btn-save').click();
  for (const name of emptied) {
    const error = page.getByTestId(`error-${name}`);
    await expect(error, `error message for required field ${name}`).toBeVisible();
    await expect(error, `error message for ${name} should have text`).toHaveText(/\S/);
  }
});
