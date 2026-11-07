// Real Business Analyst outputs (Ghala, PR #2, contract 0.1.0-proposal).
// Do not edit these JSON files by hand — run `npm run sync-samples` instead.
import taskManagerEn from './requirements/task_manager_en.requirements.json';
import inventoryDialectAr from './requirements/inventory_dialect_ar.requirements.json';
import inventoryManagerAr from './requirements/inventory_manager_ar.requirements.json';
import appointmentBookingEn from './requirements/appointment_booking_en.requirements.json';
import outOfScopeAr from './requirements/out_of_scope_ar.requirements.json';
import vagueIdeaEn from './requirements/vague_idea_en.requirements.json';

export const SAMPLES = {
  task_manager_en: taskManagerEn,
  inventory_dialect_ar: inventoryDialectAr,
  inventory_manager_ar: inventoryManagerAr,
  appointment_booking_en: appointmentBookingEn,
  out_of_scope_ar: outOfScopeAr,
  vague_idea_en: vagueIdeaEn,
};

// Sample ideas for quick testing (same texts as samples/inputs/*.json).
export const SAMPLE_IDEAS = [
  { label: 'مخزون (لهجة)', key: 'inventory_dialect_ar', idea: inventoryDialectAr.source_idea },
  { label: 'مخزون (فصحى)', key: 'inventory_manager_ar', idea: inventoryManagerAr.source_idea },
  { label: 'إدارة مهام', key: 'task_manager_en', idea: taskManagerEn.source_idea },
  { label: 'حجز مواعيد', key: 'appointment_booking_en', idea: appointmentBookingEn.source_idea },
  { label: 'فكرة ناقصة', key: 'vague_idea_en', idea: vagueIdeaEn.source_idea },
  { label: 'خارج النطاق', key: 'out_of_scope_ar', idea: outOfScopeAr.source_idea },
];

const normalize = (s) => s.trim().replace(/\s+/g, ' ').toLowerCase();

const KEYWORDS = [
  // checked first: anything that is clearly outside the CRUD MVP
  { key: 'out_of_scope_ar', re: /دفع|جوال|آيفون|اندرويد|أندرويد|دردشة|payment|iphone|android|mobile app|chat/i },
  { key: 'inventory_dialect_ar', re: /مخزون|منتج|بضاع|مستودع/ },
  { key: 'inventory_manager_ar', re: /inventory|stock|product/i },
  { key: 'appointment_booking_en', re: /موعد|مواعيد|حجز|appointment|booking|clinic/i },
  { key: 'task_manager_en', re: /مهام|مهمة|مهمات|task|to-?do/i },
];

/** Picks the sample whose idea matches the text; falls back to the vague-idea sample. */
export function pickSampleKey(text) {
  const n = normalize(text);
  const exact = SAMPLE_IDEAS.find((s) => normalize(s.idea) === n);
  if (exact) return exact.key;
  const hit = KEYWORDS.find((k) => k.re.test(text));
  return hit ? hit.key : 'vague_idea_en';
}

/**
 * After clarification answers: pick a ready sample from the answers.
 * Ghala's samples/answers/vague_idea_answers.json says "Tasks", which maps to task_manager_en.
 */
export function pickSampleAfterAnswers(answers) {
  const key = pickSampleKey(Object.values(answers).join(' '));
  return key === 'vague_idea_en' || key === 'out_of_scope_ar' ? 'task_manager_en' : key;
}
