// What the screens say about testing. The source is project.qa.status from the
// backend (passed | failed | blocked | not_run), never the numbers alone, and a
// repair is mentioned only when the backend reports one (repair_attempt > 0).
import { qaOutcome } from '../constants/stages.js';

export const QA_NOTES = {
  failed: 'الاختبار وجد عيوباً في التطبيق. التفاصيل في تقرير الاختبار.',
  blocked: 'تعذّر اختبار التطبيق، فالجودة غير مؤكدة. التطبيق المولَّد متاح للمعاينة والتحميل.',
  not_run: 'لم يُشغَّل الاختبار على هذا التطبيق.',
};

/** Number of repairs the backend actually made. */
export function repairCount(project) {
  const n = Number(project?.repair_attempt ?? 0);
  return Number.isFinite(n) && n > 0 ? n : 0;
}

/**
 * Short QA text and tone for headers, lists and tiles.
 * tone: done | failed | waiting | neutral (maps to .status-{tone} and colors).
 */
export function qaSummary(project) {
  const qa = qaOutcome(project);
  const m = project?.metrics ?? null;
  const skipped = m?.checks_skipped ?? qa.skippedChecks.length;
  switch (qa.status) {
    case 'passed':
      return {
        ...qa,
        tone: 'done',
        text: m ? `اجتاز ${m.checks_passed} من ${m.checks_total} فحوصات${skipped ? ` · تخطّى ${skipped}` : ''}` : 'اجتاز الاختبار',
        note: null,
      };
    case 'failed': {
      const failed = m?.checks_failed ?? qa.failedChecks.length;
      return {
        ...qa,
        tone: 'failed',
        text: m ? `فشل ${failed || m.checks_total - m.checks_passed} من ${m.checks_total} فحوصات` : 'وجد الاختبار عيوباً',
        note: QA_NOTES.failed,
      };
    }
    case 'blocked':
      return { ...qa, tone: 'waiting', text: 'تعذّر الاختبار', note: QA_NOTES.blocked };
    case 'not_run':
      return { ...qa, tone: 'neutral', text: 'لم يُختبر', note: QA_NOTES.not_run };
    default:
      return { ...qa, tone: 'neutral', text: '—', note: null };
  }
}
