// Keeps an unsent idea when the user goes back to edit it.
const KEY = 'bunyan.draft';
export function saveDraft(text) {
  try { sessionStorage.setItem(KEY, text); } catch { /* storage unavailable */ }
}
export function takeDraft() {
  try {
    const v = sessionStorage.getItem(KEY) ?? '';
    sessionStorage.removeItem(KEY);
    return v;
  } catch {
    return '';
  }
}
