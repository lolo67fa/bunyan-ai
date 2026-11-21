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

const STOPPED = {
  passed: 'انتهت المحاولات بنجاح الفحوصات.',
  no_change: 'لم يجد الإصلاح التلقائي ما يغيّره في الكود، فلم تُعَد الفحوصات ولم يُحسب إصلاحاً.',
  budget_used: 'استُنفدت محاولتا الإصلاح.',
  invalid_repair_output: 'أنتج الإصلاح ملفات غير صالحة، فتوقف دون إعادة الفحوصات.',
  repair_error: 'تعذّر تنفيذ الإصلاح، فتوقف دون إعادة الفحوصات.',
  qa_blocked: 'تعذّر إعادة الاختبار بعد الإصلاح.',
  repair_unavailable: 'لم يُطلب إصلاح بالذكاء الاصطناعي (لا رمز وصول صالح، أو انتهت الحصة أو الميزانية).',
};

/**
 * The repair history the backend recorded (project.repair, repair_history.json), as rows for the
 * Tests screen. Nothing is inferred: a row exists only for a step the backend reports.
 */
export function repairSteps(project) {
  const repair = project?.repair;
  if (!repair || !Array.isArray(repair.history)) return null;
  const rows = repair.history.map((h) => {
    if (h.step === 'test') {
      const qa = h.qa ?? {};
      const label = h.attempt === 0 ? 'الاختبار الأول' : `إعادة الاختبار ${h.attempt}`;
      const result = qa.status === 'passed' ? `نجح ${qa.passed} من ${qa.total}`
        : qa.status === 'failed' ? `فشل ${(qa.failed ?? []).length} من ${qa.total}` : 'تعذّر الاختبار';
      return { key: `t${h.attempt}`, label, result, tone: qa.status === 'passed' ? 'done' : qa.status === 'failed' ? 'failed' : 'waiting' };
    }
    const files = (h.changed_files ?? []).map((c) => c.file).join('، ');
    const ai = h.strategy === 'llm_repair' ? ' (ذكاء اصطناعي)' : '';
    const result = h.result === 'changed' ? `غيّر المطوّر${ai}: ${files}`
      : h.result === 'no_change' ? 'لم يتغير أي ملف'
        : h.result === 'rejected' ? 'رُفض اقتراح الإصلاح ولم يُطبَّق'
          : h.result === 'unavailable' ? 'لم يُطلب إصلاح بالذكاء الاصطناعي' : `فشل الإصلاح${h.reason ? `: ${h.reason}` : ''}`;
    return { key: `r${h.attempt}`, label: `محاولة الإصلاح ${h.attempt} من ${repair.max_repairs ?? 2}`, result,
      tone: h.result === 'changed' ? 'neutral' : 'failed' };
  });
  return { rows, stopped: repair.stopped ? STOPPED[repair.stopped] ?? null : null };
}
