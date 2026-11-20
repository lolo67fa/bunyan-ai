// What the review and clarification screens say about the Business Analyst's last run.
// The source is the backend: project.error (a failed re-analysis keeps the reviewed
// version), project.revision (what really changed after "request changes") and
// project.compatibility (whether the Architect can build these requirements).
// Nothing here says a change was applied unless revision lists it.

const REVIEW_STATES = ['awaiting_approval', 'awaiting_clarification'];

const quote = (text) => {
  const t = String(text ?? '').trim();
  return t.length > 80 ? `${t.slice(0, 80)}…` : t;
};

const names = (fields) => fields.map((f) => f.label || f.field).join('، ');

/** Sentence for an applied revision, or null when nothing changed. */
export function revisionSummary(revision) {
  if (!revision?.changed) return null;
  const parts = [];
  if (revision.added_fields?.length) parts.push(`أضاف: ${names(revision.added_fields)}`);
  if (revision.removed_fields?.length) parts.push(`حذف: ${names(revision.removed_fields)}`);
  if (revision.changed_fields?.length) parts.push(`عدّل: ${names(revision.changed_fields)}`);
  if (revision.added_entities?.length) parts.push(`أضاف نوع سجل: ${revision.added_entities.join('، ')}`);
  if (!parts.length) parts.push('غيّر المتطلبات أو المعايير دون تغيير الحقول');
  return parts.join(' · ');
}

/**
 * Notices for the screen, most important first: [{ tone, text, testId }].
 * tone is a Notice tone: error | waiting | neutral.
 */
export function analysisNotices(project) {
  if (!project || !REVIEW_STATES.includes(project.status)) return [];
  const notices = [];

  if (project.error?.message) {
    notices.push({
      tone: 'error',
      testId: 'analysis-error',
      text: project.requirements
        ? `${project.error.message} المعروض هو آخر نسخة من المتطلبات.`
        : project.error.message,
    });
  }

  const revision = project.revision;
  if (revision && project.status === 'awaiting_approval') {
    const asked = `طلبك: «${quote(revision.feedback)}».`;
    const summary = revisionSummary(revision);
    if (summary) {
      notices.push({
        tone: 'neutral',
        testId: 'revision-applied',
        text: `${asked} ما تغيّر في المتطلبات: ${summary}. تأكّد أنه ما طلبته قبل الموافقة.`,
      });
    } else if (revision.mode === 'mock') {
      notices.push({
        tone: 'waiting',
        testId: 'revision-unchanged',
        text: `${asked} المحلّل يعمل في الوضع التجريبي ولا يطبّق التعديلات، فالمتطلبات لم تتغير.`,
      });
    } else {
      notices.push({
        tone: 'waiting',
        testId: 'revision-unchanged',
        text: `${asked} لم تتغير المتطلبات بعد المراجعة. أعد صياغة الطلب، أو وافق على النسخة الحالية.`,
      });
    }
  }

  if (project.compatibility?.supported === false && project.status === 'awaiting_approval') {
    notices.push({ tone: 'error', testId: 'compatibility-warning', text: project.compatibility.message });
  }
  return notices;
}
