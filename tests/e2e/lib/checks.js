// The fixed list of 8 core checks (QA Tester, Sara).
//
// The ids are the ones Jood already uses in frontend/src/mocks/placeholders.js,
// so the dashboard does not need new names. The list is a PROPOSAL until the
// team agrees on it (frontend/README.md, open point F7).
//
// `criteria_categories` links a check to acceptance_criteria[].category in
// requirements.json. This is a category match only: it shows which criteria a
// check is related to, NOT that every one of those criteria is fully covered.

const CHECKS = [
  {
    id: 'create_item',
    description: 'Add a record through the form; it appears in the list and the row count grows by one.',
    criteria_categories: ['create'],
  },
  {
    id: 'list_items',
    description: 'Three records are listed, each row showing every column from crud.read.list_fields.',
    criteria_categories: ['read'],
  },
  {
    id: 'edit_item',
    description: 'Edit opens a pre-filled form; after saving, the list shows the new value and not the old one.',
    criteria_categories: ['update'],
  },
  {
    id: 'delete_item',
    description: 'Cancelling the delete keeps the record; confirming removes only that record.',
    criteria_categories: ['delete'],
  },
  {
    id: 'persist_after_refresh',
    description: 'A saved record is still listed after the page is reloaded (localStorage).',
    criteria_categories: ['persistence'],
  },
  {
    id: 'reject_incomplete_input',
    description: 'Saving with required fields empty does not add a record, before or after reload.',
    criteria_categories: ['validation'],
  },
  {
    id: 'empty_state',
    description: 'With no records the empty-state message is shown; it disappears after the first record.',
    criteria_categories: ['read'],
  },
  {
    id: 'error_message_visible',
    description: 'Saving with required fields empty shows a non-empty error next to each of those fields.',
    criteria_categories: ['validation'],
  },
];

module.exports = { CHECKS };
