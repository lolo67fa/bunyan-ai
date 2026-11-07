// Workflow states: docs/architecture.md §6 plus the two the backend uses in PR #5
// ("rejected" for out-of-scope ideas, "approved" until the Architect is wired in).
export const STATUS = {
  CREATED: 'created',
  ANALYZING: 'analyzing',
  AWAITING_CLARIFICATION: 'awaiting_clarification',
  AWAITING_APPROVAL: 'awaiting_approval',
  APPROVED: 'approved',
  REJECTED: 'rejected',
  DESIGNING: 'designing',
  DEVELOPING: 'developing',
  TESTING: 'testing',
  REPAIRING: 'repairing',
  DOCUMENTING: 'documenting',
  COMPLETED: 'completed',
  FAILED: 'failed',
};

export const STATUS_LABELS = {
  created: 'تم الإنشاء',
  analyzing: 'تحليل الفكرة',
  awaiting_clarification: 'بانتظار إجاباتك',
  awaiting_approval: 'بانتظار موافقتك',
  approved: 'تمت الموافقة',
  rejected: 'خارج النطاق',
  designing: 'تصميم الهيكلة',
  developing: 'توليد الكود',
  testing: 'اختبار التطبيق',
  repairing: 'إصلاح الأخطاء',
  documenting: 'إعداد خطة المشروع',
  completed: 'اكتمل',
  failed: 'فشل',
};

// The five agents in pipeline order, and the workflow states each one owns.
export const AGENTS = [
  {
    key: 'business_analyst',
    name: 'محلل الأعمال',
    role: 'Business Analyst',
    output: 'requirements.json',
    states: ['created', 'analyzing', 'awaiting_clarification', 'awaiting_approval'],
  },
  {
    key: 'software_architect',
    name: 'مهندس البرمجيات',
    role: 'Software Architect',
    output: 'architecture.json',
    states: ['designing'],
  },
  {
    key: 'developer',
    name: 'المطوّر',
    role: 'Developer',
    output: 'index.html · style.css · app.js',
    states: ['developing', 'repairing'],
  },
  {
    key: 'qa_tester',
    name: 'مختبر الجودة',
    role: 'QA Tester',
    output: 'test_report.json',
    states: ['testing'],
  },
  {
    key: 'project_manager',
    name: 'مدير المشروع',
    role: 'Project Manager',
    output: 'project_plan.md · risks.md',
    states: ['documenting'],
  },
];

// States where the run is waiting for the user — polling can stop.
export const WAITING_STATES = ['awaiting_clarification', 'awaiting_approval'];
// States where the run is over — polling stops.
export const TERMINAL_STATES = ['completed', 'failed', 'rejected'];

/**
 * Returns 'done' | 'active' | 'waiting' | 'failed' | 'pending' for one agent,
 * given the project status and the agent the backend reports as current.
 */
export function agentState(agentIndex, project) {
  const { status, current_agent: currentAgent } = project;
  if (status === 'completed') return 'done';
  // Analyst finished and the user approved; the next agent has not started yet.
  if (status === 'approved') return agentIndex === 0 ? 'done' : 'pending';
  // Out of scope: the analyst stopped the run.
  if (status === 'rejected') return agentIndex === 0 ? 'failed' : 'pending';

  const activeIndex = AGENTS.findIndex((a) =>
    currentAgent ? a.key === currentAgent : a.states.includes(status),
  );

  if (status === 'failed') {
    if (activeIndex === -1) return agentIndex === 0 ? 'failed' : 'pending';
    if (agentIndex < activeIndex) return 'done';
    return agentIndex === activeIndex ? 'failed' : 'pending';
  }
  if (activeIndex === -1) return 'pending';
  if (agentIndex < activeIndex) return 'done';
  if (agentIndex > activeIndex) return 'pending';
  return WAITING_STATES.includes(status) ? 'waiting' : 'active';
}
