// Error and waiting states (from the approved "حالات الخطأ والانتظار" table).
// Every message says what happened and what to do next. No blank screens, no endless waits.

export const MSG = {
  noProjects: 'لم تبدأ أي مشروع بعد. ابدأ بفكرة بسيطة لإدارة بيانات.',
  unclearIdea: 'الوصف قصير جداً. اكتب ما البيانات التي تريد حفظها وما الذي تريد فعله بها.',
  outOfScope: 'لا يبني بُنيان الألعاب أو تطبيقات الجوال حالياً. جرّب فكرة لإدارة بيانات.',
  clarification: 'يحتاج المحلّل 3 تفاصيل قبل كتابة المتطلبات. المشروع متوقف حتى تجيب.',
  awaitingApproval: 'المتطلبات جاهزة للمراجعة. لن نبدأ البناء قبل قرارك.',
  feedbackSent: 'وصلت ملاحظاتك ويعمل المحلّل على نسخة جديدة. سنبلغك عند جاهزيتها.',
  serverDown: 'تعذّر الاتصال بخادم بُنيان. بياناتك محفوظة. حاول بعد قليل.',
  agentWorking: (agent) => `يعمل ${agent} الآن. يمكنك مغادرة الصفحة.`,
  slow: 'يستغرق وقتاً أطول من المعتاد.',
  verySlow: (agent) => `مرّت أكثر من 5 دقائق على ${agent}. هذا أطول من المعتاد.`,
  agentFailed: 'تعذّر على الوكيل الإكمال بسبب خطأ في خدمة الذكاء الاصطناعي. المراحل السابقة محفوظة.',
  checksFailed: (n, total) => `فشل ${n} من ${total} فحوصات. أُرسل العيب للمطوّر لإصلاحه.`,
  repairing: (n) => `المحاولة ${n} من 2. ستُعاد الفحوصات الثمانية بعدها.`,
  repairsExhausted: 'ما زال فحص واحد يفشل بعد محاولتين. يمكنك تحميل الكود مع تقرير العيوب.',
  previewUnavailable: 'تتوفر المعاينة بعد أن ينتهي المطوّر من الملفات الثلاثة.',
  downloadNotReady: 'تجهيز ملف ZIP الآن.',
  notFound: 'الرابط قديم أو حُذف المشروع من هذا الجهاز.',
  timeout: 'لم يصل رد خلال 15 ثانية. قد يكون الاتصال ضعيفاً أو الخادم مشغولاً.',
};

/** Thresholds for long waits (ms). Polling stops after 3 errors in a row. */
export const WAIT = { slow: 30_000, verySlow: 5 * 60_000 };
export const POLL_MS = 3000;
export const MAX_POLL_ERRORS = 3;
export const REQUEST_TIMEOUT_MS = 15_000;
