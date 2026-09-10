import { useEffect, useMemo, useState } from "react";
import { Link, NavLink, useParams, useSearchParams } from "react-router-dom";
import { Database, MessageSquare, Plus, ShieldCheck } from "lucide-react";
import { Badge, Empty, QueryState, SourceNote } from "../components/evidence/common";
import { defaultStrategy, source, useEvidence } from "../data/client";
import { eventsSchema, pageSchema, runSchema } from "../data/schema";
import {
  buildConversation,
} from "../features/runtime/projection";
import { Composer, ConversationView } from "../features/conversation/conversation-view";
import { ArtifactPanel } from "../features/artifacts/artifact-panel";
import { TeamView } from "../features/team/team-view";
import { Trace } from "./trace";

const sessionsSchema = pageSchema(runSchema);
const TABS = [
  { key: "chat", label: "对话" },
  { key: "trace", label: "轨迹" },
  { key: "team", label: "团队" },
  { key: "evolution", label: "演进" },
] as const;

function useCompact() {
  const [compact, setCompact] = useState(
    () => window.matchMedia("(max-width: 767px)").matches,
  );
  useEffect(() => {
    const media = window.matchMedia("(max-width: 767px)");
    const update = () => setCompact(media.matches);
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  return compact;
}

export function SessionShell() {
  const { sessionId } = useParams();
  const [params] = useSearchParams();
  const view = params.get("view") ?? "chat";
  const [artifactOpen, setArtifactOpen] = useState(false);
  const compact = useCompact();
  const sessions = useEvidence(
    `/runs?strategy_id=${encodeURIComponent(defaultStrategy)}`,
    sessionsSchema,
  );
  const detail = useEvidence(
    sessionId ? `/runs/${encodeURIComponent(sessionId)}` : null,
    runSchema,
  );
  const events = useEvidence(
    sessionId ? `/runs/${encodeURIComponent(sessionId)}/events` : null,
    eventsSchema,
  );
  const conversation = useMemo(() => {
    if (!detail.value?.data) return null;
    return buildConversation(detail.value.data, events.value?.data.items ?? []);
  }, [detail.value, events.value]);
  return (
    <div className="session-shell">
      <a href="#session-main" className="skip-link">
        跳到内容
      </a>
      <aside className="session-sidebar">
        <Link className="brand" to="/">
          <span className="brand-mark accent">
            <MessageSquare size={20} />
          </span>
          <span>
            Evo<span className="brand-accent">Team</span>
          </span>
        </Link>
        <button
          type="button"
          className="new-session"
          disabled
          title="实时提交任务依赖执行作业服务（契约 F1/F2），上线后开放"
        >
          <Plus size={15} /> 新会话
        </button>
        <div className="sidebar-caption">工作区</div>
        <p className="tiny workspace-name">{defaultStrategy || "默认工作区"}</p>
        <div className="sidebar-caption">会话</div>
        <nav aria-label="会话列表" className="session-list">
          {(sessions.value?.data.items ?? []).map((run) => (
            <NavLink
              key={run.run_id}
              to={`/sessions/${encodeURIComponent(run.run_id)}`}
              className={({ isActive }) =>
                `session-item ${isActive ? "active" : ""}`
              }
            >
              <span className={`run-dot ${run.evaluation.metrics.success === true ? "ok" : run.evaluation.metrics.success === false ? "bad" : ""}`} />
              <span className="session-title">
                {run.task_id}
                <small>{run.sealed_at.slice(0, 16).replace("T", " ")}</small>
              </span>
            </NavLink>
          ))}
        </nav>
        <div className="session-sidebar-bottom">
          <span className="tiny">
            <ShieldCheck size={12} /> 只读回放 · 不调用模型
          </span>
          <Link to="/dashboard/runs" className="tiny dash-link">
            <Database size={12} /> 后台工作台（运行/演进/版本证据）
          </Link>
        </div>
      </aside>
      <div className="session-main">
        <header className="session-header">
          <div className="session-title-row">
            <strong>
              {conversation?.instruction ?? sessionId ?? "EvoTeam 会话"}
            </strong>
            <span className="session-meta">
              {detail.value?.data && (
                <Badge>
                  Strategy v{detail.value.data.strategy.version}
                </Badge>
              )}
              <button
                type="button"
                className={`source-chip ${source === "fixture" ? "fixture" : ""}`}
                onClick={() => setArtifactOpen(false)}
              >
                <span className="dot" />
                {source === "fixture" ? "开发样例 · 非实测" : "当前数据库"}
              </button>
            </span>
          </div>
          <nav className="session-tabs" aria-label="会话视图">
            {TABS.map((tab) => (
              <NavLink
                key={tab.key}
                to={
                  sessionId
                    ? `/sessions/${encodeURIComponent(sessionId)}?view=${tab.key}`
                    : `?view=${tab.key}`
                }
                className={() => `session-tab ${view === tab.key ? "active" : ""}`}
              >
                {tab.label}
              </NavLink>
            ))}
          </nav>
        </header>
        <main id="session-main" className="session-body">
          {!sessionId ? (
            <Empty title="选择或新建会话">
              <p className="tiny">
                会话对应当前工作区的一次任务执行。新建会话将随实时执行服务开放；现有执行可在左侧列表回放。
              </p>
              <Link to="/dashboard/runs">前往后台工作台 →</Link>
            </Empty>
          ) : (
            <>
              <QueryState {...detail} retry={detail.refresh} />
              {view === "chat" && conversation && (
                <div className={`session-chat ${artifactOpen ? "with-panel" : ""}`}>
                  <div className="chat-column">
                    <ConversationView
                      conversation={conversation}
                      onOpenArtifact={() => setArtifactOpen(true)}
                    />
                    <Composer />
                  </div>
                  <ArtifactPanel
                    plan={conversation.plan}
                    open={artifactOpen && !!conversation.plan}
                    onClose={() => setArtifactOpen(false)}
                  />
                </div>
              )}
              {view === "trace" && sessionId && (
                <Trace runId={sessionId} embedded />
              )}
              {view === "team" && detail.value?.data && (
                <TeamView
                  detail={detail.value.data}
                  events={events.value?.data.items ?? []}
                  compact={compact}
                />
              )}
              {view === "evolution" && (
                <Empty title="演进证据在后台工作台">
                  <p className="tiny">
                    当前数据模型中演进记录挂在策略版本上，尚未与单次会话直接关联；查看该策略的全部演进证据：
                  </p>
                  <Link
                    to={`/dashboard/evolutions?strategy_id=${encodeURIComponent(
                      defaultStrategy || "",
                    )}`}
                  >
                    打开演进证据 →
                  </Link>
                </Empty>
              )}
            </>
          )}
        </main>
        {(() => {
          const envelope = detail.value ?? sessions.value;
          return envelope ? <SourceNote envelope={envelope} /> : null;
        })()}
      </div>
    </div>
  );
}
