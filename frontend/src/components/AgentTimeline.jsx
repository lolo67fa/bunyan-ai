import { AGENTS, STATUS_LABELS, agentState } from '../constants/stages.js';

const STATE_TEXT = {
  done: 'اكتمل',
  active: 'يعمل الآن',
  waiting: 'بانتظارك',
  failed: 'توقف',
  pending: 'لم يبدأ',
};

export default function AgentTimeline({ project }) {
  return (
    <section className="card" aria-label="حالة الوكلاء" data-testid="agent-timeline">
      <div className="card-head">
        <h2>حالة الوكلاء</h2>
        <span className={`status-pill status-${project.status}`} data-testid="project-status">
          {STATUS_LABELS[project.status] ?? project.status}
        </span>
      </div>

      <ol className="agents">
        {AGENTS.map((agent, i) => {
          const state = agentState(i, project);
          const isRepair = agent.key === 'developer' && project.status === 'repairing';
          return (
            <li key={agent.key} className={`agent agent-${state}`} data-testid={`agent-${agent.key}`}>
              <span className="agent-dot" aria-hidden="true">
                {state === 'done' ? '✓' : state === 'failed' ? '!' : i + 1}
              </span>
              <div className="agent-body">
                <div className="agent-title">
                  <strong>{agent.name}</strong>
                  <span className="muted ltr">{agent.role}</span>
                </div>
                <code className="ltr">{agent.output}</code>
              </div>
              <span className="agent-state">
                {isRepair ? `إصلاح ${project.repair_attempt} من 2` : STATE_TEXT[state]}
              </span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
