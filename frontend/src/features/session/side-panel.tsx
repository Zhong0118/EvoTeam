import type { Run, TraceEvent } from "../../data/schema";
import { formatDuration, formatTokens, type AgentSpan } from "./session-data";

export type SidePanel =
  | { type: "none" }
  | { type: "artifact" }
  | { type: "event"; event: TraceEvent }
  | { type: "agent"; nodeId: string }
  | {
      type: "diff";
      evolutionId: string;
      target: string;
      metrics: {
        label: string;
        current: number | null;
        candidate: number | null;
        goodWhenDown: boolean;
      }[];
      gate: { decision: string; reasons: string[] } | null;
    };

const EVENT_NAMES: Record<string, string> = {
  task_created: "提交任务",
  team_created: "组装团队",
  agent_started: "开始执行",
  agent_completed: "交付结果",
  agent_failed: "执行失败",
  agent_message: "协作消息",
  run_finished: "运行结束",
  evaluation_completed: "独立评价",
  run_sealed: "证据封存",
};

export function SidePanelView({
  panel,
  detail,
  events,
  spans,
  onClose,
  notify,
  onFilterTrace,
}: {
  panel: SidePanel;
  detail: Run;
  events: TraceEvent[];
  spans: AgentSpan[];
  onClose: () => void;
  notify: (message: string) => void;
  onFilterTrace: (query: string) => void;
}) {
  if (panel.type === "none") return null;
  const eyebrow =
    panel.type === "artifact"
      ? "ARTIFACT · PLAN"
      : panel.type === "event"
        ? "TRACE EVENT"
        : panel.type === "agent"
          ? "TEAM · AGENT"
          : "EVOLUTION · DIFF";
  const title =
    panel.type === "artifact"
      ? "项目计划"
      : panel.type === "event"
        ? (EVENT_NAMES[panel.event.event_type] ?? panel.event.event_type)
        : panel.type === "agent"
          ? panel.nodeId
          : `${panel.target} · 配置差异`;
  return (
    <aside className="ws-side-panel" aria-hidden="false" aria-label="上下文面板">
      <div className="ws-side-panel-header">
        <div>
          <span className="ws-eyebrow">{eyebrow}</span>
          <h2>{title}</h2>
        </div>
        <button
          type="button"
          className="ws-icon-button"
          aria-label="关闭面板"
          onClick={onClose}
        >
          ×
        </button>
      </div>
      <div className="ws-side-panel-body">
        {panel.type === "artifact" && <ArtifactBody detail={detail} />}
        {panel.type === "event" && (
          <EventBody
            event={panel.event}
            notify={notify}
            onClose={onClose}
          />
        )}
        {panel.type === "agent" && (
          <AgentBody
            nodeId={panel.nodeId}
            detail={detail}
            events={events}
            spans={spans}
            notify={notify}
            onFilterTrace={onFilterTrace}
          />
        )}
        {panel.type === "diff" && <DiffBody panel={panel} />}
      </div>
    </aside>
  );
}

function ArtifactBody({ detail }: { detail: Run }) {
  const plan = detail.plan;
  if (!plan)
    return (
      <p style={{ color: "var(--ws-muted)", fontSize: 12 }}>
        该记录未提供完整计划产物。
      </p>
    );
  return (
    <div className="ws-preview-shell">
      <div className="ws-preview-toolbar">
        <span>project-plan@1</span>
        <span>只读投影 · 不重算评价</span>
      </div>
      <div className="ws-preview-doc">
        <div className="ws-preview-kicker">PROJECT PLAN</div>
        <h1>排期计划</h1>
        <p>
          目标：{detail.task?.instruction ?? "未提供"}
        </p>
        <h2>排期</h2>
        <table className="ws-preview-table">
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
        <h2>里程碑</h2>
        {(plan.milestones ?? []).length === 0 ? (
          <p>未提供</p>
        ) : (
          <ul>
            {(plan.milestones ?? []).map((m) => (
              <li key={m.milestone_id}>
                {m.milestone_id} · 完成时刻 {m.completion_hour}
              </li>
            ))}
          </ul>
        )}
        <h2>风险</h2>
        {plan.risks.length === 0 ? <p>无</p> : <ul>{plan.risks.map((r) => <li key={r}>{r}</li>)}</ul>}
        <h2>校验依据</h2>
        <ul>
          {plan.validation_notes.map((n) => (
            <li key={n}>{n}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function EventBody({
  event,
  notify,
  onClose,
}: {
  event: TraceEvent;
  notify: (message: string) => void;
  onClose: () => void;
}) {
  const summary =
    event.output !== null && event.output !== undefined
      ? "包含已保存的结构化产物（见下方 JSON）"
      : "—";
  return (
    <>
      <dl className="ws-inspector-grid">
        <dt>Type</dt>
        <dd>{event.event_type}</dd>
        <dt>Sequence</dt>
        <dd>#{String(event.sequence).padStart(2, "0")}</dd>
        <dt>Node</dt>
        <dd>{event.node_id ?? "—"}</dd>
        <dt>Instance</dt>
        <dd>{event.instance_id ?? "—"}</dd>
        <dt>Timestamp</dt>
        <dd>{event.timestamp}</dd>
        <dt>Caused by</dt>
        <dd>{event.caused_by.join("、") || "无"}</dd>
        <dt>Summary</dt>
        <dd>{summary}</dd>
      </dl>
      <div className="ws-inspector-code">
        {JSON.stringify(
          {
            event_id: event.event_id,
            event_type: event.event_type,
            node_id: event.node_id,
            instance_id: event.instance_id,
            caused_by: event.caused_by,
            node_state: event.node_state ?? undefined,
            output: event.output ?? undefined,
          },
          null,
          2,
        )}
      </div>
      <div className="ws-panel-actions">
        <button
          type="button"
          className="primary"
          onClick={() => {
            navigator.clipboard
              .writeText(event.event_id)
              .then(() => notify("已复制事件 ID"))
              .catch(() => notify("复制失败"));
          }}
        >
          复制事件 ID
        </button>
        <button type="button" onClick={onClose}>
          关闭
        </button>
      </div>
    </>
  );
}

function AgentBody({
  nodeId,
  detail,
  events,
  spans,
  notify,
  onFilterTrace,
}: {
  nodeId: string;
  detail: Run;
  events: TraceEvent[];
  spans: AgentSpan[];
  notify: (message: string) => void;
  onFilterTrace: (query: string) => void;
}) {
  const config = (detail.nodes ?? []).find((n) => n.node_id === nodeId);
  const own = spans.filter((s) => s.nodeId === nodeId);
  const ownEvents = events
    .filter((e) => e.node_id === nodeId)
    .sort((a, b) => a.sequence - b.sequence);
  const tokens = own.reduce(
    (acc, s) => ({
      input: s.tokens.input ?? acc.input,
      output: s.tokens.output ?? acc.output,
    }),
    { input: null as number | null, output: null as number | null },
  );
  const duration = own
    .map((s) => s.durationSeconds)
    .filter((d): d is number => d !== null)
    .reduce((a, b) => a + b, 0);
  return (
    <>
      <dl className="ws-inspector-grid">
        <dt>Status</dt>
        <dd>
          <span className="ws-metric-chip">
            {own.some((s) => s.status === "running")
              ? "running"
              : own.length > 0
                ? "completed"
                : "queued"}
          </span>
        </dd>
        <dt>Current step</dt>
        <dd>{own.find((s) => s.summary)?.summary ?? own[0]?.action ?? "—"}</dd>
        <dt>Prompt</dt>
        <dd>
          {config
            ? `${config.prompt_ref.id}@${config.prompt_ref.version}`
            : "—"}
        </dd>
        <dt>Model</dt>
        <dd>{config ? `${config.model_ref.id}@${config.model_ref.version}` : "—"}</dd>
        <dt>Metrics</dt>
        <dd>
          {formatTokens(tokens)} · {formatDuration(duration > 0 ? duration : null)}
        </dd>
        <dt>Instances</dt>
        <dd>{own.map((s) => s.instanceId).join("、") || "—"}</dd>
      </dl>
      <div className="ws-inspector-code">
        {"Latest activity\n\n"}
        {ownEvents
          .slice(-6)
          .map(
            (e) =>
              `${String(e.sequence).padStart(2, "0")}  ${EVENT_NAMES[e.event_type] ?? e.event_type}${e.output !== null && e.output !== undefined ? "  · 已保存产物" : ""}`,
          )
          .join("\n") || "无事件"}
      </div>
      <div className="ws-panel-actions">
        <button
          type="button"
          className="primary"
          onClick={() => {
            onFilterTrace(nodeId);
            notify(`轨迹已按 ${nodeId} 过滤`);
          }}
        >
          只看该 Agent 轨迹
        </button>
        <button
          type="button"
          onClick={() => {
            navigator.clipboard
              .writeText(own.map((s) => s.agentRunId).join("\n"))
              .then(() => notify("已复制 AgentRun ID"))
              .catch(() => notify("复制失败"));
          }}
        >
          复制 AgentRun ID
        </button>
      </div>
    </>
  );
}

function DiffBody({
  panel,
}: {
  panel: Extract<SidePanel, { type: "diff" }>;
}) {
  return (
    <>
      <dl className="ws-inspector-grid">
        <dt>Evolution</dt>
        <dd>{panel.evolutionId}</dd>
        <dt>Target</dt>
        <dd>{panel.target}</dd>
      </dl>
      <div className="ws-inspector-code">
        {(panel.metrics ?? [])
          .map(
            (m) =>
              `${m.label}: ${m.current ?? "—"} → ${m.candidate ?? "—"}`,
          )
          .join("\n") || "指标未提供"}
      </div>
      <div style={{ marginTop: 14 }}>
        {(panel.metrics ?? []).map((m) => {
          const delta =
            m.current !== null &&
            m.candidate !== null &&
            m.current !== 0
              ? ((m.candidate - m.current) / m.current) * 100
              : null;
          return (
            <span className="ws-metric-chip" key={m.label}>
              {m.label}{" "}
              {delta === null
                ? "—"
                : `${delta > 0 ? "+" : ""}${delta.toFixed(1)}%`}
            </span>
          );
        })}
      </div>
      {panel.gate && (
        <div className="ws-gate-card" style={{ marginTop: 16 }}>
          <strong>Gate · {panel.gate.decision}</strong>
          {panel.gate.reasons[0] && (
            <div
              style={{ marginTop: 6, color: "var(--ws-muted)", fontSize: 10 }}
            >
              {panel.gate.reasons[0]}
            </div>
          )}
        </div>
      )}
    </>
  );
}
