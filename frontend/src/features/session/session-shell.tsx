import { useEffect, useMemo, useState } from "react";
import { NavLink, useParams, useSearchParams } from "react-router-dom";
import { MessageSquare, Plus } from "lucide-react";
import { defaultStrategy, source, useEvidence } from "../../data/client";
import {
  eventsSchema,
  pageSchema,
  runSchema,
  evolutionSchema,
  type Evolution,
  type Run,
  type TraceEvent,
} from "../../data/schema";
import { buildAgentSpans } from "./session-data";
import { ChatView } from "./chat-view";
import { TraceView } from "./trace-view";
import { TeamView } from "./team-view";
import { EvolutionView } from "./evolution-view";
import { SidePanelView, type SidePanel } from "./side-panel";

const sessionsSchema = pageSchema(runSchema);
const evolutionsSchema = pageSchema(evolutionSchema);

const TABS = [
  { key: "chat", label: "对话" },
  { key: "trace", label: "轨迹" },
  { key: "team", label: "团队" },
  { key: "evolution", label: "演进" },
] as const;

type ViewKey = (typeof TABS)[number]["key"];

export function SessionShell() {
  const { sessionId } = useParams();
  const [params, setParams] = useSearchParams();
  const [view, setView] = useState<ViewKey>(() => {
    const initial = params.get("view");
    return TABS.some((t) => t.key === initial) ? (initial as ViewKey) : "chat";
  });
  function switchView(next: ViewKey) {
    setView(next);
    const p = new URLSearchParams(params);
    p.set("view", next);
    setParams(p, { replace: true });
  }
  const [panel, setPanel] = useState<SidePanel>({ type: "none" });
  const [traceFilter, setTraceFilter] = useState("");
  const [replayToken, setReplayToken] = useState(0);
  const [toast, setToast] = useState<{ message: string; at: number } | null>(
    null,
  );
  const sessions = useEvidence(
    `/runs?strategy_id=${encodeURIComponent(defaultStrategy)}`,
    sessionsSchema,
  );
  const evolutions = useEvidence(
    `/evolutions?strategy_id=${encodeURIComponent(defaultStrategy)}`,
    evolutionsSchema,
  );
  const detail = useEvidence(
    sessionId ? `/runs/${encodeURIComponent(sessionId)}` : null,
    runSchema,
  );
  const events = useEvidence(
    sessionId ? `/runs/${encodeURIComponent(sessionId)}/events` : null,
    eventsSchema,
  );
  const d = detail.value?.data as Run | undefined;
  const ev: TraceEvent[] = useMemo(
    () => events.value?.data.items ?? [],
    [events.value],
  );
  const spans = useMemo(
    () => (d ? buildAgentSpans(d, ev) : []),
    [d, ev],
  );
  const notify = (message: string) => setToast({ message, at: Date.now() });
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(null), 1900);
    return () => clearTimeout(timer);
  }, [toast]);
  useEffect(() => {
    setPanel({ type: "none" });
  }, [sessionId]);
  const selectedEventId = panel.type === "event" ? panel.event.event_id : null;
  return (
    <div className="ws-shell">
      <aside className="ws-sidebar">
        <div className="ws-brand-row">
          <NavLink className="ws-brand" to="/">
            <span className="ws-brand-logo">
              <MessageSquare size={16} />
            </span>
            <span>EvoTeam</span>
          </NavLink>
        </div>
        <button
          type="button"
          className="ws-new-session"
          disabled
          title="实时提交任务依赖执行作业服务（契约 F1/F2），上线后开放"
        >
          <Plus size={14} />
          <strong>新会话</strong>
        </button>
        <section className="ws-sidebar-section">
          <div className="ws-sidebar-heading">
            <span>工作区</span>
          </div>
          <div className="ws-workspace-chip">
            <span className="ws-folder-icon">▱</span>
            <div>
              <strong>LOCAL › EvoTeam</strong>
              <small>openJiuwen multi-agent</small>
            </div>
          </div>
        </section>
        <section className="ws-sidebar-section ws-sessions-section">
          <div className="ws-sidebar-heading">
            <span>会话</span>
          </div>
          <div className="ws-session-list">
            {(sessions.value?.data.items ?? []).map((run) => (
              <NavLink
                key={run.run_id}
                to={`/sessions/${encodeURIComponent(run.run_id)}`}
                className={({ isActive }) =>
                  `ws-session-item ${isActive ? "active" : ""}`
                }
              >
                <span className="ws-session-main">
                  <span className="ws-session-name">{run.task_id}</span>
                  <span className="ws-session-sub">
                    {run.evaluation.metrics.success === true
                      ? "已完成"
                      : run.evaluation.metrics.success === false
                        ? "评价未通过"
                        : "状态未知"}
                    {" · "}
                    Strategy v{run.strategy.version}
                  </span>
                </span>
                <span className="ws-session-time">
                  {run.sealed_at.slice(5, 10)}
                </span>
              </NavLink>
            ))}
          </div>
        </section>
        <div className="ws-sidebar-bottom">
          <NavLink className="ws-bottom-link" to="/dashboard/strategies">
            ◈ <span>策略与能力</span>
          </NavLink>
          <NavLink className="ws-bottom-link" to="/dashboard/runs">
            ⚙ <span>后台工作台</span>
          </NavLink>
        </div>
      </aside>

      <section className="ws-main-shell">
        <header className="ws-session-header">
          <div className="ws-session-title-group">
            <h1>{d?.task?.instruction ?? sessionId ?? "EvoTeam"}</h1>
            <div className="ws-header-meta">
              <span className="ws-mode-chip">只读回放</span>
              <a
                className="ws-header-link"
                href={
                  sessionId
                    ? `/v1/runs/${encodeURIComponent(sessionId)}/export`
                    : undefined
                }
                download
              >
                ⇩ 导出
              </a>
            </div>
          </div>
          <div className="ws-header-actions">
            <span className="ws-source-chip">
              <span className="dot" />
              {source === "fixture" ? "开发样例 · 非实测" : "当前数据库"}
            </span>
            {d && (
              <span className="ws-strategy-chip">
                <i />
                Strategy v{d.strategy.version}
              </span>
            )}
            <button
              type="button"
              className="ws-secondary-button"
              onClick={() => {
                if (!sessionId) return notify("请先选择会话");
                setReplayToken((n) => n + 1);
                setView("chat");
              }}
            >
              ↻ 重放流程
            </button>
          </div>
        </header>

        <div className="ws-view-tabs-row">
          <nav className="ws-view-tabs" aria-label="会话视图">
            {TABS.map((tab) => (
              <button
                key={tab.key}
                type="button"
                className={`ws-view-tab ${
                  view === tab.key ? "active" : ""
                } ${tab.key === "evolution" ? "evolution-tab" : ""}`}
                onClick={() => switchView(tab.key)}
              >
                {tab.label}
                {tab.key === "evolution" &&
                  (evolutions.value?.data.items.length ?? 0) > 0 && (
                    <span className="ws-tiny-badge">
                      {evolutions.value!.data.items.length}
                    </span>
                  )}
              </button>
            ))}
          </nav>
          <button
            type="button"
            className={`ws-artifact-toggle ${
              panel.type === "artifact" ? "active" : ""
            }`}
            onClick={() => {
              if (!d?.plan) return notify("该会话没有可预览的计划产物");
              setPanel(panel.type === "artifact" ? { type: "none" } : { type: "artifact" });
            }}
          >
            <span>▤</span>
            <span>产物</span>
            <span>{panel.type === "artifact" ? "‹" : "›"}</span>
          </button>
        </div>

        <div
          className={`ws-content-frame ${panel.type !== "none" ? "side-open" : ""}`}
        >
          <main className="ws-main-content">
            <section
              id="ws-view-chat"
              className={`ws-view-panel ${view === "chat" ? "active" : ""}`}
            >
              {d ? (
                <ChatView
                  detail={d}
                  spans={spans}
                  replayToken={replayToken}
                  notify={notify}
                  onOpenArtifact={() => setPanel({ type: "artifact" })}
                  onOpenEvents={() => setView("trace")}
                />
              ) : (
                <div className="ws-empty-state">选择左侧会话查看对话。</div>
              )}
            </section>
            <section
              id="ws-view-trace"
              className={`ws-view-panel ${view === "trace" ? "active" : ""}`}
            >
              {d && (
                <TraceView
                  detail={d}
                  events={ev}
                  selectedEventId={selectedEventId}
                  traceFilter={traceFilter}
                  onInspectEvent={(event) => setPanel({ type: "event", event })}
                />
              )}
            </section>
            <section
              id="ws-view-team"
              className={`ws-view-panel ${view === "team" ? "active" : ""}`}
            >
              {d && (
                <TeamView
                  detail={d}
                  events={ev}
                  activeNodeId={panel.type === "agent" ? panel.nodeId : null}
                  onSelectNode={(nodeId) => setPanel({ type: "agent", nodeId })}
                />
              )}
            </section>
            <section
              id="ws-view-evolution"
              className={`ws-view-panel ${view === "evolution" ? "active" : ""}`}
            >
              <EvolutionView
                strategyId={defaultStrategy}
                records={(evolutions.value?.data.items ?? []) as Evolution[]}
                onOpenDiff={(payload) => setPanel({ type: "diff", ...payload })}
              />
            </section>
          </main>

          <SidePanelView
            panel={panel}
            detail={d as Run}
            events={ev}
            spans={spans}
            onClose={() => setPanel({ type: "none" })}
            notify={notify}
            onFilterTrace={(query) => {
              setTraceFilter(query);
              setView("trace");
            }}
          />
        </div>

        <div
          className={`ws-toast ${toast ? "show" : ""}`}
          role="status"
          aria-live="polite"
        >
          {toast?.message}
        </div>
      </section>
    </div>
  );
}
