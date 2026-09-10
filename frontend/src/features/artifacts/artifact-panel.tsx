import type { Run } from "../../data/schema";

export function ArtifactPanel({
  plan,
  open,
  onClose,
}: {
  plan: Run["plan"];
  open: boolean;
  onClose: () => void;
}) {
  if (!open || !plan) return null;
  return (
    <aside className="artifact-panel" aria-label="产物预览">
      <header className="artifact-head">
        <strong>产物 · 项目计划</strong>
        <button type="button" className="artifact-close" onClick={onClose}>
          关闭
        </button>
      </header>
      <div className="artifact-body">
        <h4>排期</h4>
        <table className="plan-table">
          <thead>
            <tr>
              <th>工作项</th>
              <th>负责人</th>
              <th>起止（小时）</th>
            </tr>
          </thead>
          <tbody>
            {plan.schedule.map((s) => (
              <tr key={`${s.work_id}-${s.start_hour}`}>
                <td>{s.work_id}</td>
                <td>{s.person_id}</td>
                <td>
                  [{s.start_hour}, {s.end_hour})
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <h4>里程碑</h4>
        {(plan.milestones ?? []).length === 0 ? (
          <p className="tiny">未提供</p>
        ) : (
          <ul className="plain-list">
            {(plan.milestones ?? []).map((m) => (
              <li key={m.milestone_id}>
                {m.milestone_id} · 完成时刻 {m.completion_hour}
              </li>
            ))}
          </ul>
        )}
        <h4>风险</h4>
        {plan.risks.length === 0 ? (
          <p className="tiny">无</p>
        ) : (
          <ul className="plain-list">
            {plan.risks.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        )}
        <h4>校验依据</h4>
        <ul className="plain-list">
          {plan.validation_notes.map((n) => (
            <li key={n}>{n}</li>
          ))}
        </ul>
        <p className="tiny">产物为已封存记录的只读投影，不重新计算。</p>
      </div>
    </aside>
  );
}
